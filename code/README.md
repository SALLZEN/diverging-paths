# Code routes

The preferred route for version 3.1.0 is code/01-reproduce.py, called by ./run.sh. It shares code/modules/workflow.py with notebooks/01-reproduce-diverging-paths.ipynb.

Readable stages:
1. code/materialize_inputs.py restores exact large tables from transport parts.
2. workflow.input_checks verifies retained data and both frozen network archives.
3. workflow.corpus_checks reconstructs primary-class totals.
4. workflow.candidate_checks reconstructs field-year shares and log ratios.
5. workflow.network_checks recalculates 57 frozen graph/window combinations.
6. code/02-main-figures-stepwise.R and code/03-si-figures-stepwise.R render the statistical companions; modules/network_graphics.py retains network geometry with STIX labels.
7. The workflow records verification and output reports.

Use ./run.sh --analysis-only or ./run.sh --notebook --analysis-only to omit graphics. Default graphical export uses macOS Quartz and bundled fonts.

The earlier upstream sources 001, 001a, 002, 003, 004, 005, 006, 006a and 006b remain historical/research-maintenance routes. Their dependencies are code/requirements.txt, code/requirements.lock.txt and renv.lock. They acquire/rebuild different upstream products and are not exercised by the normalized frozen-input route. In particular, current raw-abstract network extraction does not have an exact-recreation claim for historical network events.

The retained candidate ontology and network tests remain at their original paths. Seven tests of the added reconstruction can be run with:

    .runtime/venv/bin/python -m unittest discover -s code/network-reconstruction/tests -v

Unused holdout answers are not part of the default workflow.
