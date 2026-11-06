# Political Attention Research

[After a crisis: new programmes or new winners?](https://kezouke.github.io/political-attention-research/?lang=en) · [После кризиса: новые программы или новые победители?](https://kezouke.github.io/political-attention-research/?lang=ru)

A bilingual research essay follows 29 banking crises through two parliamentary elections and decomposes programme-agenda changes in the 16 episodes with sufficient manifesto coverage. It separates revisions within continuing parties, vote reweighting and changes in the observed record roster. Calm periods, preceding intervals, coding changes and coverage rules test alternative interpretations. A historical prediction check and a local multilingual BERT benchmark constrain what the text measures can establish.

The calculations are descriptive and do not identify a causal effect of programme changes. The current essay uses one connected question rather than combining unrelated country vignettes. See [methods](RESEARCH_METHODS.md), [protocol and exploratory additions](RESEARCH_PROTOCOL.md), and [claim and editorial audit](RESEARCH_AUDIT_2026.md).

The previous first-election study is preserved at commit `7f380831a4b4c66a75ec6b29e80fea3cbab2a1a9`, with its original outputs unchanged and a local page at `docs/crisis-baseline.html`. The earlier priorities research remains in the repository. Neither archive is a required continuation of the current post.

## Build the current essay

The page and static publication figures can be rebuilt without restricted raw data:

```sh
python -m pip install -r requirements.txt
python analysis/29_research_figures.py
python analysis/30_build_research_page.py
python -m unittest discover -s tests
node tests/site.test.js
```

For the full source-based analysis, generate the local election calendar with script 21, then run scripts 23, 24, 26, 27 and 28. Script 25 is the optional NLP experiment and requires `requirements-research.lock`, the CAP raw text and a download of the pinned E5-small model. Script 31 verifies newly listed crisis onsets in the 2026 IMF update. Exact ordering, inputs and limitations are in [RESEARCH_METHODS.md](RESEARCH_METHODS.md). All raw texts, respondent records, model weights and embeddings remain local.

## Repository map

| Location | Contents |
| --- | --- |
| `docs/` | Bilingual research essays, interactive figures and static data bundles. |
| `analysis/` | Reproducible analyses, source notes and page-data build. |
| `data/processed/` | Reproducible country, election and media aggregates, plus model results. |
| `data/raw/README.md` | Versions, sources, checksums and instructions for obtaining raw inputs. Raw inputs are deliberately excluded. |
| `analysis/baseline/` | Earlier research scripts, quantitative models, model validation, figures, output tables and the previous Russian article. |
| `tests/` | Data-contract and result checks. |
| `RESEARCH.md` | Research questions, evidence map, findings and open limitations. |
| `research_audit.md` | Claim-to-evidence audit, independent computational checks and sensitivity bounds. |
| `RESEARCH_CHANGELOG.md` | New findings, changed conclusions and unresolved gaps. |
| `CAUSAL_DESIGN.md` | Rival mechanisms, required data and tests that could falsify the proposed causal chain. |
| `CRISIS_METHODS.md` | Election pairing, coverage, benchmarks, sensitivities and case evidence. |
| `METHODS.md` | Definitions, sample, modelling choices, scope and data limitations. |

The baseline analysis is retained as a snapshot, not silently replaced. Some original inputs require registration or separate downloads and cannot be redistributed here. See [the baseline guide](analysis/baseline/README.md). Do not interpret a historical snapshot limitation as the current status of the updated ESS analysis.

## Reproduce the preserved first-election comparison

Place the ten named inputs from [the source guide](data/raw/README.md#crisis-and-elections) in `data/raw/`. Then run:

```sh
python -m pip install -r requirements.txt
python analysis/21_crisis_elections.py
python analysis/22_build_crisis_page.py
python -m unittest discover -s tests
node tests/site.test.js
```

The page builder uses committed aggregates, so it can also run from a checkout without raw data.

## Reproduce the archived priorities analysis

Python 3.12 is recommended. The lockfile records the actual analysis environment. Download or place the named source files described in [data/raw/README.md](data/raw/README.md) into `data/raw/`; the ESS download requires a free account. Do not commit an ESS user ID, password, token or raw respondent files.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python analysis/01_households_climate.py
python analysis/02_manifesto_shares.py
python analysis/03_media_and_priorities.py
python analysis/04_media_climate.py
python analysis/06_spain_text_pilot.py
python analysis/07_us_media_public.py
python analysis/08_brazil_and_six_country_opinion.py
python analysis/09_manifesto_benchmark.py
python analysis/09b_manifesto_longitudinal.py
python analysis/10_spanish_frontpages.py
python analysis/11_ess_routing.py
python analysis/12_mecco_sensitivity.py
python analysis/13_thailand_longitudinal.py
python analysis/14_identity_spain_cis.py
python analysis/16_macro_conditions.py
python analysis/17_insecurity_trust.py
python analysis/18_structural_exposure.py
python analysis/90_claim_audit.py
python analysis/19_common_shock.py
python analysis/05_build_site_data.py
python -m unittest discover -s tests
node tests/site.test.js
```

Scripts 01–04, 06–11 and 13–18 are independent once inputs are in place. Script 12 requires the MeCCO aggregates from script 04; script 90 requires manifesto aggregates from script 02. Run script 05 last to assemble the article bundle. `analysis/baseline/outputs/` is a versioned snapshot used for some earlier figures and historical model results in the article. If upstream releases change, source checksums help distinguish an updated dataset from a calculation change.

## Important limits

- The 22-country ESS comparison uses two independent cross-sectional waves. Six countries changed to self-completion; standard errors clustered by country do not reproduce the complete survey design.
- The manifesto percentages cover only coded documents with electoral weights. The latest election varies by country, and Thailand is absent in the 2023a source. The two category definitions are explicit proxies, not the author's undefined “80%”.
- The Spanish programme dictionary is not a validated measure of agenda shares. Its 48-item inspection was performed by the assistant with predicted labels visible; a separate external CAP benchmark highlights disagreement but is not human peer review of this study.
- US Gallup issue-mention shares and NYT Index-entry shares use different denominators; neither describes an individual social-media feed.
- MeCCO records article counts in selected newspapers, not all news output, individual feeds or audience exposure. The NYT Index sample ends in 2016.
- Environment, climate and energy security are merged in one SPES category, so that category must not be interpreted as pure climate concern.
- This research does not identify the causal effect of financial difficulty, media exposure or elite behaviour. It was not preregistered or externally peer reviewed.

## Data and rights

Code is provided under the [MIT License](LICENSE). Third-party data and source texts remain subject to their respective providers' terms; this repository does not assert rights over them. See [data/raw/README.md](data/raw/README.md) for source citations and redistribution notes. Do not place personal identifiers or credentials in the public repository.
