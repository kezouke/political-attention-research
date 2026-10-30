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
