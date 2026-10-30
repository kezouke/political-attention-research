# Earlier study snapshot

This folder contains the baseline analysis from 30 October 2026: scripts, output tables, charts, diagnostics, model validation, and the earlier Russian HTML article. The current bilingual article is at `../../docs/index.html`. Follow-up analyses are in `../../analysis/`.

The initial scripts were kept at their original relative level and expect raw source files under this folder's `data/` directory and results under `outputs/`. Raw files are not published here. The original `REPRODUCIBILITY.txt` is a historical note and predates the later successful acquisition of full ESS8, ESS10 and ESS10SC data; use the main repository README and `METHODS.md` for current status. Historical data limitations are retained as part of that snapshot, not presented as current findings.

Key scripts:

- `analysis.py`, `sensitivity.py`: European issues, inflation fixed-effects regressions, country leave-one-out and sensitivity checks.
- `ess_full_analysis.py`: full round 8 versus rounds 10 / 10SC, country summaries, ideology interaction and design-weight sensitivity.
- `media_model.py`, `media_binary_model.py`: TF–IDF/logistic models and temporal evaluation. The model was not used for post-2016 claims after weak performance on rare topics.
- `platform_analysis.py`, `spain_platform_analysis.py`, `uk_platform_analysis.py`, `manifesto_expanded.py`: documented party-text and manifesto analyses.
- `gdelt_comparison.py`, `mecco_analysis.py`, `policy_content_analysis.py`, `expanded_indicators.py`: media, governmental documents and energy/legal indicators.
- Other scripts and their outputs are included unchanged for traceability.

`site/` contains the earlier rendered article and its static assets; links to the former large downloadable archives have been replaced with links to this repository's README. Those archives and raw third-party source files are excluded to respect data access, licensing and the public nature of the repository. Obtain the required source files from the providers listed in `REPRODUCIBILITY.txt`, the main `data/raw/README.md`, and the methods/citations in the article. Archived CSV and figure outputs do not depend on access to raw sources.

For public redistribution, text excerpts were removed from five derived audit tables (the three `*_matches.csv` tables, `huffpost_examples.csv` and `nyt_keyword_audit_sample.csv`). Category labels, match terms, dates and counts remain. Run the original scripts against source documents under their respective terms to reconstruct the text context locally.

Manifesto Project's original dataset and the row-level `manifesto_documents.csv` are excluded from this public snapshot under the provider's terms. Election-level aggregates, code and the earlier results remain available.
