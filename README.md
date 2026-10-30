# Political Attention, 2010–2026

A bilingual, reproducible research project on public priorities, financial difficulty and climate concern, party manifestos, media visibility, and policy outcomes. The project examines a claim that climate and identity displaced economic concerns before economic issues returned to politics. It separates what the available evidence can establish from questions the data cannot answer.

**Read the research post:** [English](docs/index.html?lang=en) · [Русский](docs/index.html?lang=ru). Open `docs/index.html` directly in a browser to read it offline. Interactive charts use the committed `docs/data.js` bundle and need no server.

**Кратко по-русски:** в репозитории собраны предыдущий этап исследования и новые проверки: пересечение финансовых трудностей и климатической тревоги, две операционализации тезиса о «80%», сравнение экономических приоритетов и анализ ограничений медийных данных. В статье указаны периоды, выборки, источники и ограничения.

## Repository map

| Location | Contents |
| --- | --- |
| `docs/` | Bilingual research post, responsive interactive figures and static data bundle. |
| `analysis/` | Scripts for the four new investigations and page-data build. |
| `data/processed/` | Reproducible country, election and media aggregates, plus model results. |
| `data/raw/README.md` | Versions, sources, checksums and instructions for obtaining raw inputs. Raw inputs are deliberately excluded. |
| `analysis/baseline/` | Earlier research scripts, quantitative models, model validation, figures, output tables and the previous Russian article. |
| `tests/` | Data-contract and result checks. |
| `RESEARCH.md` | Research questions, evidence map, findings and open limitations. |
| `METHODS.md` | Definitions, sample, modelling choices, scope and data limitations. |

The baseline analysis is retained as a snapshot, not silently replaced. Some original inputs require registration or separate downloads and cannot be redistributed here. See [the baseline guide](analysis/baseline/README.md). Do not interpret a historical snapshot limitation as the current status of the updated ESS analysis.

## Reproduce the new analysis

Python 3.12 is recommended. The lockfile records the actual analysis environment. Download or place the named source files described in [data/raw/README.md](data/raw/README.md) into `data/raw/`; the ESS download requires a free account. Do not commit an ESS user ID, password, token or raw respondent files.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python analysis/01_households_climate.py
python analysis/02_manifesto_shares.py
python analysis/03_media_and_priorities.py
python analysis/04_media_climate.py
python analysis/05_build_site_data.py
python -m unittest discover -s tests
node tests/site.test.js
```

Scripts 01–04 are independent once inputs are in place; script 05 assembles the outputs into the article bundle. `analysis/baseline/outputs/` is a versioned snapshot used for some earlier figures and historical model results in the article. If upstream releases change, source checksums help distinguish an updated dataset from a calculation change.

## Important limits

- The 22-country ESS comparison uses two independent cross-sectional waves. Six countries changed to self-completion; standard errors clustered by country do not reproduce the complete survey design.
- The manifesto percentages cover only coded documents with electoral weights. The latest election varies by country, and Thailand is absent in the 2023a source. The two category definitions are explicit proxies, not the author's undefined “80%”.
- MeCCO records article counts in selected newspapers, not all news output, individual feeds or audience exposure. The NYT Index sample ends in 2016.
- Environment, climate and energy security are merged in one SPES category, so that category must not be interpreted as pure climate concern.
- This research does not identify the causal effect of financial difficulty, media exposure or elite behaviour. It was not preregistered or externally peer reviewed.

## Data and rights

Code is provided under the [MIT License](LICENSE). Third-party data and source texts remain subject to their respective providers' terms; this repository does not assert rights over them. See [data/raw/README.md](data/raw/README.md) for source citations and redistribution notes. Do not place personal identifiers or credentials in the public repository.
