# Conditional reconstruction of frozen network metrics

This source recalculates network metrics from the retained count tables and graphs. It does not recreate historical raw-abstract extraction or Gephi layouts.

The default version 3.1.0 runner verifies and recalculates all 57 graph/window combinations automatically:

    ./run.sh --analysis-only

The same functions are used by the clean notebook. The root network/ directory retains the exact v3.0.0 ZIPs. Their historical manifests are preserved at provenance/v3.0.0/release_manifest.json. The verifier checks accepted manifest identities and archive/member hashes before calculations.

For a direct run, choose an output path outside the reference package:

    .runtime/venv/bin/python code/network-reconstruction/recompute_metrics.py --release-root . --output ../diverging-paths-network-check.json

Seven calculation tests:

    .runtime/venv/bin/python -m unittest discover -s code/network-reconstruction/tests -v

The [v3.0.0 Zenodo baseline](https://doi.org/10.5281/zenodo.23263996) provides the earlier frozen evidence. The manifest lookup also supports extracted predecessor releases. Input pins, graph distances, focal definitions, endpoint sets and numerical comparisons are unchanged.

These are discourse-network diagnostics. Removal effects are not historical counterfactuals, and centrality is not evidential or causal dependence.
