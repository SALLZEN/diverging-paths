import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path

import networkx as nx

MODULE = Path(__file__).resolve().parents[1] / 'recompute_metrics.py'
spec = importlib.util.spec_from_file_location('recompute_metrics', MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CalculationTests(unittest.TestCase):
    def test_disconnected_pairs_keep_their_denominator(self):
        graph = nx.Graph()
        graph.add_edge('a1', 'h', **{m.DISTANCE: 4.0})
        graph.add_node('a2')
        efficiency, reachable = m.efficiency(graph, ['a1', 'a2'], ['h'])
        self.assertEqual(efficiency, 0.125)
        self.assertEqual(reachable, 0.5)

    def test_removing_unique_bridge_eliminates_efficiency(self):
        graph = nx.Graph()
        graph.add_edge('a', 'c', **{m.DISTANCE: 2.0})
        graph.add_edge('c', 'h', **{m.DISTANCE: 3.0})
        baseline, _ = m.efficiency(graph, ['a'], ['h'])
        self.assertEqual(baseline, 0.2)
        self.assertEqual(m.removal(graph, ['a'], ['h'], 'c', baseline), (0.0, 0.0, 1.0))

    def test_endpoint_removal_is_rejected(self):
        graph = nx.Graph()
        graph.add_edge('a', 'h', **{m.DISTANCE: 1.0})
        with self.assertRaisesRegex(ValueError, 'non-anchor'):
            m.removal(graph, ['a'], ['h'], 'a', 1.0)

    def test_known_spectral_ratio_and_tied_percentile(self):
        rows = [{'Source': c, 'Target': 'concept', 'paper_count': str(n),
                 'candidate_bearing_papers': '10', 'cooc_doc_prevalence_candidate_papers': str(n / 10)}
                for c, n in [('a', 3), ('b', 4)]]
        scores = m.spectral_scores(rows)
        self.assertAlmostEqual(scores['a'], 0.75)
        self.assertAlmostEqual(scores['b'], 1.0)
        self.assertEqual(m.percentile({'a': 0.5, 'b': 1.0, 'c': 1.0}, 'b'), 2.5 / 3)

    def test_altered_weight_fails(self):
        row = {'Source': 'a', 'Target': 'c', 'paper_count': '3',
               'candidate_bearing_papers': '10', 'cooc_doc_prevalence_candidate_papers': '0.4'}
        with self.assertRaisesRegex(ValueError, 'HITS weight'):
            m.spectral_scores([row])

    def test_nonfinite_results_fail(self):
        for value in [math.nan, math.inf]:
            with self.assertRaises(ValueError):
                m.check_close(value, value, 'nonfinite')

    def test_changed_release_manifest_fails_before_calculation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / 'release_manifest.json'
            manifest.write_text('{}')
            pins = root / 'pins.json'
            pins.write_text(json.dumps({'accepted_release_manifest_sha256': [m.sha256(manifest)]}))
            manifest.write_text('{"changed": true}')
            with self.assertRaisesRegex(ValueError, 'manifest does not match'):
                m.verify(root, pins)


if __name__ == '__main__':
    unittest.main()
