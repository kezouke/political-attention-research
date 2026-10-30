# Raw data inputs

Raw data and source documents are deliberately not committed. All results used by the article are included in `data/processed/` or in the previous analysis snapshot. To recompute, place the following files here. Source terms apply independently of this repository's code licence. Do not commit account identifiers or credentials.

| File | Source used | Access and citation |
| --- | --- | --- |
| `ess8e02_3.dta` | ESS Round 8 integrated file, edition 2.3 | [DOI](https://doi.org/10.21338/ess8e02_3), free ESS portal registration. |
| `ess10e03_3.dta` | ESS Round 10 integrated interview file, edition 3.3 | [DOI](https://doi.org/10.21338/ess10e03_3), free registration. |
| `ess10sce03_1.dta` | ESS Round 10 self-completion file, edition 3.1 | [DOI](https://doi.org/10.21338/ess10sce03_1), free registration. |
| `manifesto_2023a.csv` | Manifesto Project Main Dataset 2023a | [Dataset citation](https://doi.org/10.25522/manifesto.mpds.2023a), [codebook](https://manifesto-project.wzb.eu/down/data/2023a/codebooks/codebook_MPDataset_MPDS2023a.pdf). Snapshot used came from [Mendeley replication archive](https://data.mendeley.com/datasets/gfhvh745sp/1), file `MPDataset_MPDS2023a.csv`. |
| `spes_aggregate.csv` | SPES European Pressing Issues Dashboard, country-year aggregate export | [IIASA project and methods](https://iiasa.ac.at/models-tools-data/spes-explorer-european-pressing-issues-dashboard), [dashboard](https://spes-test.shinyapps.io/spes-release/). The 14-country observations used here are also stored in `data/processed/europe_priorities_country.csv`; an upstream export may change. |
| `nyt.csv` | Comparative Agendas Project, New York Times Index | [Direct CSV](https://minio.la.utexas.edu/compagendas/datasetfiles/US-Media_NYTimesIndex_16.1.csv) and [codebook](https://minio.la.utexas.edu/compagendas/codebookfiles/NY_Times_Index_Codebook.pdf). |
| `mecco_russia.html` | MeCCO Russia figure page | [Page](https://mecco.colorado.edu/russia/index.html), DOI 10.25810/gnet-gz66. |
| `mecco_spain.html` | MeCCO Spain figure page | [Page](https://mecco.colorado.edu/spain/index.html), DOI 10.25810/37f9-1j65. |
| `mecco_latin_america.html` | MeCCO Latin America figure page | [Page](https://mecco.colorado.edu/latin_america/index.html), DOI 10.25810/5dxz-xm93. |
| `mecco_asia.html` | MeCCO Asia figure page | [Page](https://mecco.colorado.edu/asia/index.html); Bangkok Post. |
| `mecco_middle_east.html` | MeCCO Middle East figure page | [Page](https://mecco.colorado.edu/middle_east/index.html); Jerusalem Post. |

The ESS API is documented at https://api.ess.sikt.no/docs. A user ID is required by ESS for data-usage statistics; use your own ID and do not put it in scripts or this repository. The three requested data file DOIs are `10.21338/ess8e02_3`, `10.21338/ess10e03_3`, `10.21338/ess10sce03_1` and `fileFormat=dta`. The official portal also supports manual downloads.

MeCCO source pages embed monthly arrays in their public Highcharts definitions. Save each original HTML response under the specified name. They update over time; the captured monthly and annual aggregates are included for audit. `analysis/04_media_climate.py` assumes each source's first array entry corresponds to January of its stated start year and validates complete years.

## SHA-256 of analysis snapshots

```text
d713488bd2b4523196ffbc1168e20da845e4a336965f477ad2a93d94ed80e989  ess10e03_3.dta
0c394a7de41d34c2f07860f48b142ed55949d319b9799e385047e270799c8216  ess10sce03_1.dta
bcb573c5f2919460a8d48c71028d182aa11b29e089d45944cd4893c62e662912  ess8e02_3.dta
0e5b5d7eebbda9a81519f316333dcf8a3960006dcbb8149f82e271e142599670  manifesto_2023a.csv
80d4fd3bd9fa3c465f3209d17beb5e9693a39ad85decd3cc943f0ad6b302cade  nyt.csv
5b83e72a21ba78f05d12a2e436f6a9446d9ebaf72e728ea4d7a2b18d96395ed8  spes_aggregate.csv
833637dac3d1b2527c655951f8619f6685a8f80a49d057544450bad0f11b3c64  mecco_asia.html
e8753139d724b38722406e6652d49260c6d702cfcd5d2846a194b9f1b3d3e2d4  mecco_latin_america.html
e3c1290181b76015eda1cf5f2f6295a7da56fc766ee10d31ccf925ddff61e7b5  mecco_middle_east.html
1fa77306200b3050fcb5354e5359a3f81d46ceb07e4afbfcc83872b2704b6095  mecco_russia.html
92dfcba90082de986029adf7d5fb152377fbd5b36803f6bdedf0d2e0ec79c861  mecco_spain.html
```

Manifesto Project's [terms of use](https://manifesto-project.wzb.eu/information/documents/terms_of_use) prohibit redistribution of provided data without written authorisation. This repository therefore excludes the original dataset and row-level document outputs. It publishes our election-level aggregates, methods and code. Obtain and use the source under the provider's terms.

## Inputs for the 2026 follow-up

- `spain_psoe_2023.pdf`: [PSOE 2023 national election programme](https://www.psoe.es/media-content/2023/07/PROGRAMA_ELECTORAL-GENERALES-2023.pdf), SHA-256 `367e49aef27593dc7052dd42ce79bbe3c36ce74316f730d969805557e33c7fe8`.
- `spain_pp_2023.pdf`: [PP 2023 national election programme](https://www.pp.es/storage/2023/07/programa_electoral_pp_23j_feijoo_2023.pdf), SHA-256 `c93baafc88bdcb33adcd7e8be9dc309b09056362183ad7b7767f3d5134313108`.
- `cap_gallup_mip.csv`: [Gallup MIP annual data from Policy Agendas](https://minio.la.utexas.edu/compagendas/datasetfiles/US-Public-Gallups_Most_Important_Problem-21.3.csv), SHA-256 `38885460d5338271c4586a39b6f09a3134c02568dcce6f2198e9a20721fef61b`. See [source page](https://www.comparativeagendas.net/project/us/datasets) for citation and the codebook.

The PSOE server denied automated retrieval during the follow-up; obtain the PDF manually if needed and verify the checksum. The Spanish PDF texts and locally generated audit passages are not included in the public repository. The audit-label file contains identifiers, hashes and decisions only.

## Brazil longitudinal most-important-problem surveys

Download the official Stata-format archives for 2010, 2011, 2013, 2015, 2016, 2017, 2018, 2020, 2023 and 2024 from each wave's source page `https://www.latinobarometro.org/latinobarometro-YYYY`. Save each archive as `lat_YYYY.zip`. The provider permits non-commercial research but forbids redistribution of raw datasets; keep the archives out of Git. The exact analyzed archive hashes and member names are recorded in `data/processed/brazil_mip_provenance.csv`. Then run `python analysis/08_brazil_and_six_country_opinion.py`. See `analysis/08_opinion_notes.md` for question wording, code comparability, fieldwork, methods and limits.

## Spanish Comparative Agendas source files

- `spain_elmundo.csv`: [El Mundo front-page dataset](https://minio.la.utexas.edu/compagendas/datasetfiles/Media_El_Mundo_Web_CAP_csv.csv), SHA-256 `0f2cb21feecffb13e11e24d375e69ccf0581e7e27a035c696bb497dd6a342c2e`.
- `spain_elpais.csv`: [El País front-page dataset](https://minio.la.utexas.edu/compagendas/datasetfiles/Media_El_Pas_Web_CAP_csv.csv), SHA-256 `f5d211c5497695168808f388adb95d824dd9ef7529f25f681afe24a34b473737`.
- `cap_spain_manifestos.csv`: [Spanish party manifesto coded quasi-sentences](https://minio.la.utexas.edu/compagendas/datasetfiles/Party_Manifestos_CAP_Web_csv.csv), SHA-256 `25404b088e8b49794e6a41d667d4295cffc46a4bb652c40a8c9899f4704875e7`.

Source citation: Chaqués Bonafont, L., Palau, A. and Baumgartner, F. R. (2015), *Agenda Dynamics in Spain*. The source [dataset list and codebooks](https://www.comparativeagendas.net/project/spain/datasets) describe provenance and coding. Source text and headlines are excluded from this repository; the checked-in outcomes are aggregates and hashed audit identifiers.

## Economic structure, unemployment and survey sources

- `wb_inflation_20261030.json` and `wb_unemployment_20261030.json`: World Bank API snapshots for indicators `FP.CPI.TOTL.ZG` and `SL.UEM.TOTL.ZS`; SHA-256 `93c9609665d67f9a95bc6385290084fdf80338da6c4d8b592a3ad3b7ba5644ab` and `638be09a5614df173105d7932822c0cee621c9ee438e11e76f2e6595aab65f65`. `analysis/16_macro_conditions.py` fetches them when absent.
- `eurostat_comp_es_20261030.json`: Eurostat `nama_10_lp_ulc`, compensation per employee, SHA-256 `7b62b269274b358b6222a7980a5316dfbfcebacae6749950a89d2f8e6866cfa1`.
- `eurostat_hicp_es_inx_20261030.json`: Eurostat `prc_hicp_aind`, annual all-items HICP index, SHA-256 `65276bd18ef14af155e940a155c002ee7a6d0f6a673d12ec5aa9e6dae96bce7a`. `analysis/16_macro_conditions.py` fetches Eurostat snapshots when absent.
- WDI structural indicator snapshots named `wdi_structure_<indicator>_20261030.json` are fetched by `analysis/18_structural_exposure.py`; the resulting `structural_wdi_provenance.csv` records source indicator URLs and exact hashes. API updates can revise historical values; compare hashes.
- `thailand_asia_foundation_2010.pdf`: original [Asia Foundation survey report](https://www.locjkt.or.id/application/docliblcjkt/upload/ThailandNationalSurvey2010.pdf), SHA-256 `4c1ebbc120d0d0bc2818b7618b64767e7e32845f0c1892e3582d78851b692c12`. The Thai election figures and source URLs are transcribed in `analysis/13_thailand_longitudinal.py` and documented in `analysis/13_thailand_notes.md`.
- `cis_september_YYYY.pdf`: primary Spain CIS barometers, downloaded with `python analysis/14_identity_spain_cis.py --download`. Exact URLs, hashes, pages, categories, field dates and respondent counts are recorded in `data/processed/identity_spain_cis_selected.csv`. Underlying PDF distribution is governed by CIS; raw files remain excluded from this repository.
The 2021–2022 common-shock comparison in `analysis/19_common_shock.py` uses the committed `data/processed/macro_issue_panel.csv`, itself derived from the SPES/Eurobarometer and World Bank series documented here. It introduces no new restricted raw dataset.
