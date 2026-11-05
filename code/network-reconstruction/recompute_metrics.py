#!/usr/bin/env python3
"""Recalculate manuscript network metrics from the immutable v3.0.0 archive.

No imports from the evolving extraction pipeline, no corpus retrieval, and no
writes to the release. See README.md for the scope of this conditional check.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import platform
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np

PREFIX = 'outputs/wimp-role-networks/'
BROKERAGE = PREFIX + '03_cross_field_brokerage/canonical/'
IMPORTANCE = PREFIX + '02_area_wide_importance/canonical/'
FOCAL = {'explicit_generic': 'dm_model:generic_wimp',
         'published_umbrella': 'dm_model:wimp_related',
         'canonical_core': 'dm_model:wimp_core'}
GROUP = ('wimp_definition', 'window_kind', 'window')
DISTANCE = 'distance_mean_field_prevalence'


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def check_close(actual, expected, label):
    expected = float(expected)
    if not math.isfinite(actual) or not math.isfinite(expected):
        raise ValueError(f'{label}: nonfinite value {actual}, {expected}')
    if not math.isclose(actual, expected, rel_tol=1e-8, abs_tol=1e-10):
        raise ValueError(f'{label}: recalculated {actual!r}; archived {expected!r}')


def read_rows(archive, name):
    return list(csv.DictReader(io.StringIO(archive.read(name).decode('utf-8'))))


def grouped(rows):
    result = defaultdict(list)
    for row in rows:
        result[tuple(row[k] for k in GROUP)].append(row)
    return result


def efficiency(graph, sources, targets):
    """Mean reciprocal distance; disconnected pairs remain in the denominator."""
    sources, targets = sorted(sources), sorted(targets)
    if not sources or not targets or not set(sources + targets) <= set(graph):
        raise ValueError('Endpoint sets must be nonempty and present in the graph')
    total, reachable = 0.0, 0
    for source in sources:
        lengths = nx.single_source_dijkstra_path_length(graph, source, weight=DISTANCE)
        for target in targets:
            distance = lengths.get(target)
            if distance is not None and distance > 0:
                total += 1.0 / distance
                reachable += 1
    pairs = len(sources) * len(targets)
    return total / pairs, reachable / pairs


def removal(graph, sources, targets, node, baseline):
    if node in set(sources) | set(targets):
        raise ValueError('Removal requires a non-anchor node, keeping endpoints fixed')
    reduced = graph.copy()
    reduced.remove_node(node)
    after, reachability = efficiency(reduced, sources, targets)
    return after, reachability, max(0.0, (baseline - after) / baseline)


def spectral_scores(rows):
    """Role-specific HITS via the leading left singular vector, max scaled."""
    candidates = sorted({r['Source'] for r in rows})
    concepts = sorted({r['Target'] for r in rows})
    ci, ti = {v: i for i, v in enumerate(candidates)}, {v: i for i, v in enumerate(concepts)}
    matrix = np.zeros((len(candidates), len(concepts)))
    seen = set()
    for row in rows:
        edge = row['Source'], row['Target']
        if edge in seen:
            raise ValueError(f'Duplicate candidate-concept edge {edge}')
        seen.add(edge)
        weight = int(row['paper_count']) / int(row['candidate_bearing_papers'])
        check_close(weight, row['cooc_doc_prevalence_candidate_papers'], 'HITS weight')
        matrix[ci[edge[0]], ti[edge[1]]] = weight
    left, _, _ = np.linalg.svd(matrix, full_matrices=False)
    values = np.abs(left[:, 0])
    values /= values.max()
    return dict(zip(candidates, map(float, values)))


def percentile(scores, focal):
    # pandas rank(method='average', pct=True), as used in the archived pipeline.
    value = scores[focal]
    lower = sum(x < value for x in scores.values())
    equal = sum(x == value for x in scores.values())
    return (lower + (equal + 1) / 2) / len(scores)


def reconstruct_graph(nodes, edges):
    graph = nx.Graph()
    for row in edges:
        weight = 0.5 * (int(row['astrophysics_paper_count']) / int(row['astrophysics_all_dm_papers'])
                        + int(row['hep_paper_count']) / int(row['hep_all_dm_papers']))
        check_close(weight, row['mean_field_cooc_prevalence'], 'Equal-field edge weight')
        distance = float(row[DISTANCE])
        check_close(distance, 1 / weight, 'Inverse-prevalence distance')
        source, target = row['Source'], row['Target']
        if graph.has_edge(source, target) or source == target:
            raise ValueError('Duplicate edge or self-loop')
        graph.add_edge(source, target, **{DISTANCE: distance})
    if set(graph) != {row['Id'] for row in nodes}:
        raise ValueError('Canonical node and edge sets disagree')
    astro, hep = [], []
    for row in nodes:
        candidate = row['node_type'] == 'candidate'
        ratio = float(row['log10_astro_hep_prevalence_ratio'])
        for name, condition, endpoints in [
            ('is_astro_anchor', not candidate and ratio >= math.log10(2), astro),
            ('is_hep_anchor', not candidate and ratio <= -math.log10(2), hep),
        ]:
            if (row[name] == 'True') != condition:
                raise ValueError(f'Endpoint rule mismatch: {row["Id"]}, {name}')
            if condition:
                endpoints.append(row['Id'])
    if not astro or not hep:
        raise ValueError('No endpoints; archive fallback would require explicit treatment')
    return graph, astro, hep


def verify(release_root, pins_path):
    pins = json.loads(pins_path.read_text())
    manifest_path = release_root / 'provenance/v3.0.0/release_manifest.json'
    if not manifest_path.is_file():
        manifest_path = release_root / 'release_manifest.json'
    if sha256(manifest_path) not in pins['accepted_release_manifest_sha256']:
        raise ValueError('Release manifest does not match the pinned v3.0.0 input')
    manifest = json.loads(manifest_path.read_text())
    entry = next(x for x in manifest['network_archives'] if x['path'] == pins['archive_path'])
    archive_path = release_root / entry['path']
    digest = sha256(archive_path)
    if digest != pins['archive_sha256'] or digest != entry['sha256']:
        raise ValueError('Frozen archive SHA-256 mismatch')
    result = {'status': 'passed', 'python': platform.python_version(),
              'networkx': nx.__version__, 'numpy': np.__version__,
              'archive_sha256': digest, 'release_manifest_sha256': sha256(manifest_path),
              'scope': 'Conditional recalculation from frozen graphs and count tables; not extraction validation',
              'windows': [], 'common_endpoints': []}
    with zipfile.ZipFile(archive_path) as archive:
        if set(archive.namelist()) != set(entry['members']):
            raise ValueError('Archive member list differs from release manifest')
        for name, expected in entry['members'].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError(f'Archive member SHA-256 mismatch: {name}')
        result['archive_members_verified'] = len(entry['members'])
        nodes = grouped(read_rows(archive, BROKERAGE + 'nodes_by_window.csv'))
        edges = grouped(read_rows(archive, BROKERAGE + 'edges_by_window.csv'))
        trajectories = grouped(read_rows(archive, BROKERAGE + 'wimp_brokerage_trajectory.csv'))
        removals = grouped(read_rows(archive, BROKERAGE + 'node_removal_metrics.csv'))
        importance_edges = grouped([r for r in read_rows(archive, IMPORTANCE + 'edges_by_window.csv')
                                    if r['evidence_scope'] == 'abstract'])
        importance_nodes = grouped(read_rows(archive, IMPORTANCE + 'candidate_metrics_by_window.csv'))
        importance_trajectory = grouped(read_rows(archive, IMPORTANCE + 'wimp_importance_trajectory.csv'))
        if not (set(nodes) == set(edges) == set(trajectories) == set(importance_edges)
                == set(importance_nodes) == set(importance_trajectory)):
            raise ValueError('Window/definition groups differ across input tables')
        stable = {}
        removal_checks = 0
        for key in sorted(nodes):
            definition, kind, window = key
            graph, astro, hep = reconstruct_graph(nodes[key], edges[key])
            if kind == 'stable':
                suffix = '' if definition == 'published_umbrella' else 'robustness/'
                name = BROKERAGE + f'graphs/{suffix}{definition}--{window.replace("-", "_")}.graphml'
                saved = nx.read_graphml(io.BytesIO(archive.read(name)))
                if set(saved) != set(graph) or {frozenset(e) for e in saved.edges} != {frozenset(e) for e in graph.edges}:
                    raise ValueError(f'GraphML topology mismatch: {key}')
                for a, b, attrs in graph.edges(data=True):
                    check_close(attrs[DISTANCE], saved[a][b][DISTANCE], 'GraphML distance')
                # Keep the archived GraphML floats/order for exact shortest-path tie handling.
                graph = saved
            scores = nx.betweenness_centrality_subset(graph, sorted(astro), sorted(hep),
                                                      normalized=True, weight=DISTANCE)
            candidates = {r['Id']: scores[r['Id']] for r in nodes[key] if r['node_type'] == 'candidate'}
            for row in nodes[key]:
                check_close(scores[row['Id']], row['cross_field_betweenness_prevalence'], f'Betweenness {key} {row["Id"]}')
            focal = FOCAL[definition]
            archived = trajectories[key][0]
            baseline, reachable = efficiency(graph, astro, hep)
            after, after_reachable, loss = removal(graph, astro, hep, focal, baseline)
            check_close(loss, archived['removal_effect_efficiency_prevalence'], f'WIMP removal {key}')
            check_close(scores[focal], archived['cross_field_betweenness_prevalence'], f'WIMP trajectory {key}')
            for row in removals[key]:
                if kind != 'stable' and row['node_id'] != focal:
                    continue
                after_node, reach_node, loss_node = removal(graph, astro, hep, row['node_id'], baseline)
                for value, column in [(baseline, 'baseline_efficiency'), (after_node, 'removed_efficiency'),
                                      (reachable, 'baseline_reachable_share'), (reach_node, 'removed_reachable_share'),
                                      (loss_node, 'relative_efficiency_loss')]:
                    check_close(value, row[column], f'{column} {key} {row["node_id"]}')
                removal_checks += 1
            hits = spectral_scores(importance_edges[key])
            for row in importance_nodes[key]:
                check_close(hits[row['Id']], row['hits_score_prevalence'], f'HITS {key} {row["Id"]}')
            hits_pct = percentile(hits, focal)
            check_close(hits_pct, importance_trajectory[key][0]['hits_candidate_percentile'], f'HITS percentile {key}')
            result['windows'].append({'definition': definition, 'kind': kind, 'window': window,
                                      'nodes': len(graph), 'edges': graph.number_of_edges(),
                                      'astro_endpoints': len(astro), 'hep_endpoints': len(hep),
                                      'wimp_betweenness': scores[focal],
                                      'wimp_candidate_rank': 1 + sum(v > scores[focal] for v in candidates.values()),
                                      'candidate_count': len(candidates), 'wimp_removal_effect': loss,
                                      'wimp_hits_score': hits[focal], 'wimp_hits_percentile': hits_pct})
            if kind == 'stable' and definition == 'published_umbrella':
                stable[window] = graph, set(astro), set(hep), candidates
            print(f'Checked {definition} {kind} {window}', flush=True)
        common_astro = set.intersection(*(v[1] for v in stable.values()))
        common_hep = set.intersection(*(v[2] for v in stable.values()))
        for row in read_rows(archive, BROKERAGE + 'common_endpoint_sensitivity.csv'):
            graph, _, _, candidates = stable[row['window']]
            scores = nx.betweenness_centrality_subset(graph, sorted(common_astro), sorted(common_hep),
                                                      normalized=True, weight=DISTANCE)
            baseline, reachable = efficiency(graph, common_astro, common_hep)
            focal = FOCAL['published_umbrella']
            after, after_reachable, loss = removal(graph, common_astro, common_hep, focal, baseline)
            rank = 1 + sum(scores[n] > scores[focal] for n in candidates)
            for value, column in [(len(common_astro), 'common_astro_endpoint_count'),
                                  (len(common_hep), 'common_hep_endpoint_count'),
                                  (scores[focal], 'common_endpoint_betweenness'),
                                  (rank, 'common_endpoint_candidate_rank'),
                                  (baseline, 'common_endpoint_baseline_efficiency'),
                                  (after, 'common_endpoint_removed_efficiency'),
                                  (loss, 'common_endpoint_removal_effect'),
                                  (reachable, 'common_endpoint_baseline_reachable_share'),
                                  (after_reachable, 'common_endpoint_removed_reachable_share')]:
                check_close(value, row[column], f'Common endpoints {row["window"]} {column}')
            result['common_endpoints'].append({'window': row['window'], 'astro_endpoints': len(common_astro),
                                               'hep_endpoints': len(common_hep), 'betweenness': scores[focal],
                                               'candidate_rank': rank, 'removal_effect': loss})
        result['node_removal_rows_recalculated'] = removal_checks
        result['betweenness_nodes_checked'] = sum(map(len, nodes.values()))
        result['hits_candidates_checked'] = sum(map(len, importance_nodes.values()))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-root', type=Path, required=True,
                        help='Extracted v3.0.0 repository root containing release_manifest.json and network/')
    parser.add_argument('--output', type=Path, required=True, help='New JSON result path outside the release')
    args = parser.parse_args()
    release_root, output = args.release_root.resolve(), args.output.resolve()
    if output.is_relative_to(release_root):
        parser.error('Output must be outside the immutable release directory')
    if output.exists():
        parser.error('Output already exists; choose a new path')
    try:
        result = verify(release_root, Path(__file__).with_name('inputs.json'))
    except (ValueError, KeyError, OSError, zipfile.BadZipFile, nx.NetworkXException) as exc:
        print(f'VERIFICATION FAILED: {exc}', file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(f'PASS: {len(result["windows"])} graph windows/definitions; results: {output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
