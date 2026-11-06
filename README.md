# Political Attention Research

[After a crisis, who receives discontent?](https://kezouke.github.io/political-attention-research/?lang=en) · [После кризиса: кому достаётся недовольство?](https://kezouke.github.io/political-attention-research/?lang=ru)

One bilingual research essay distinguishes incumbent punishment, issue priorities
and general political distrust. It preserves 29 historical banking-crisis episodes
and programme decompositions, adds a common European survey, and tests timing,
repeated attitudes and transfer using British and German panels. National
comparisons cover eight countries without pretending their questions form one
balanced panel.

Government disapproval, populist voting and abstention have different conditional
relationships with distrust. Prior party preferences and the definition of populism
matter. The study retains weak predictive additions and negative importance/topic
results. It does not identify a common causal chain from the 2008 crisis to populism.

[Methods and reproduction](CHOICE_METHODS.md) · [Claim and editorial audit](CHOICE_AUDIT.md) ·
[Data audit, including Hugging Face](DATA_AUDIT_2026.md) ·
[Agreed six-page research plan](output/pdf/political-economy-research-six-pager-ru.pdf)

Detailed results: [Eurobarometer v2](EUROPEAN_RESULTS_V2.md),
[BES](FIRST_BES_RESULTS.md), [GLES](FIRST_GLES_RESULTS.md),
[national comparisons](NATIONAL_RESULTS.md). The common four-outcome European
sample includes 15,962 people in 19 countries. The 13 national cases span eight
countries; they serve different measurement and timing tests, not one pooled effect.

## Build the current essay

Python 3.12 is recommended. The article and checks below use committed aggregate
results, without licensed respondent records:

```sh
python -m pip install -r requirements-dev.txt
python analysis/83_national_results_report.py
python analysis/84_choice_publication_figures.py
python analysis/85_build_choice_essay.py
python analysis/86_choice_publication_checks.py
python -m pytest -q
node tests/choice.test.js
node tests/site.test.js
```

The full source-based estimation sequence, exact survey versions, measurement
contracts, uncertainty and data-access restrictions are in [CHOICE_METHODS.md](CHOICE_METHODS.md).
Raw respondent rows, identifiers, free text, credentials, model weights and
embeddings are excluded from the repository. Code and prose were developed with
AI assistance; the work has not undergone independent expert peer review.

## Preserved results

The original first-election study remains at commit
`7f380831a4b4c66a75ec6b29e80fea3cbab2a1a9` and `docs/crisis-baseline.html`.
The programme extension is preserved in `docs/programme-baseline.html`, scripts
23–30 and its aggregate tables. Its [methods](RESEARCH_METHODS.md) and
[original audit](RESEARCH_AUDIT_2026.md) remain available. Script 30 builds that
historical article and overwrites the main page if run; use script 85 for the
current essay. Earlier priority research remains in the repository and is not a
required continuation of the current post.

## Repository map

| Location | Contents |
| --- | --- |
| `docs/` | Bilingual research essays, interactive figures and static data bundles. |
| `analysis/` | Reproducible analyses, source notes and page-data build. |
| `data/processed/` | Reproducible country, election and media aggregates, plus model results. |
| `data/raw/README.md` | Versions, sources, checksums and instructions for obtaining raw inputs. Raw inputs are deliberately excluded. |
| `analysis/baseline/` | Earlier research scripts, quantitative models, model validation, figures, output tables and the previous Russian article. |
| `tests/` | Data-contract and result checks. |
| `CHOICE_METHODS.md` / `CHOICE_AUDIT.md` | Current methods, numerical claims, limitations and transition review. |
| `article/` | Current Russian and English prose, compiled into one page. |
| `RESEARCH.md` | Preserved earlier questions, evidence map and findings. |
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
