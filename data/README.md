# Retained data

The active normalized route uses six local input tables and the retained analysis products. Their unchanged identities are recorded in checks/input-hashes.json. Statistical contracts in analysis_manifest.json are historical evidence and retain their original creation paths; those paths are not runtime dependencies.

papers.parquet and papers_with_dm_models.parquet are transported as two parts each. data/INPUT-STORAGE.json gives their original sizes/hashes and each part's identity. code/materialize_inputs.py restores them automatically and refuses to overwrite an existing table with a different identity.

The other four tables are supplied directly. Retained analysis tables, bootstrap intervals, sensitivity products and validation scaffolds remain unchanged. Verification is conditional on those frozen products; it does not resample intervals or evaluate unused holdout answers.

Restored large tables and new analysis products are ignored by Git. Keep all supplied data and frozen network ZIPs intact and write new results under reproduced/.
