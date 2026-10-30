# Research map

## Explanatory question and hypotheses

Why do similar shocks produce different political priorities and outcomes? Our working framework links exposure, interpretation and trust, political supply and media, then institutional constraints and policy feedback. It predicts neither a uniform reaction nor a proven causal sequence. The research compares competing mechanisms: re-ranking of coexisting concerns, changes in attitudes, institutional distrust, elite framing and distribution of policy costs. See `analysis/15_historical_context.md` for competing published findings and `METHODS.md` for the limits of our own observational tests.

The 2026 follow-up adds Brazilian and Spanish campaign evidence; Thai survey snapshots and election arithmetic; Spanish CIS identity-adjacent salience; World Bank and Eurostat structural and macroeconomic indicators; and new ESS models of financial difficulty, trust and immigration attitudes. Source evidence and limitations are explicit; these analyses do not establish a common causal chain.

## Question and unit of analysis

The project asks how shocks, economic structure, institutions and political actors interact to change political priorities. A public claim about a global shift away from climate and identity supplied the initial motivation; it combines distinct outcomes that cannot substitute for one another.

| Layer | Question | Evidence in this repository | Main limit |
| --- | --- | --- | --- |
| Public priorities | Which problems do people name as most important? | SPES for Spain, Serbia and Bulgaria; ten Brazil Latinobarómetro microdata waves; Pew results and WVS snapshots. | Different question wording, answer limits, countries and survey periods. SPES environment also includes energy security. |
| Individual attitudes | Can people report financial difficulty and climate worry at once? | Full ESS8, ESS10 and ESS10SC microdata processed into country summaries and exploratory models. | Independent waves, nonresponse, mode change; no individual causal effect. |
| Party programmes | How much of the coded document concerns selected economic and political categories? | Manifesto Project 2023a, election points and matched-party sensitivity; external CAP benchmark for the Spanish dictionary. | Coverage of parties and elections varies; no 2023a Thailand data. Two coding definitions are proxies, not universal interpretations of “80%”. |
| Media | What appears in selected outlets and what can a feed show? | CAP Spanish front pages through 2011; MeCCO counts and starting-year sensitivity; CAP NYT and Gallup sample. | Not a random sample of global media or the original author's feed; media counts are not public opinion. |
| Government and outcomes | What did governments do, and what happened in energy? | CAP documents for UK, US and Brazil; World Bank WBL legal index; Ember generation data; selected EU/US legislation. | Primary-topic counts have no direction or implementation measure; electricity output is an outcome, not a law. |
| Elections | Do parties' results move with issue attention? | Selected official election results and vote weights for coded manifestos. | Not a full election panel; electoral outcomes do not identify voting motives. |

## Reading order

1. Read `docs/index.html` in English or Russian for the integrated argument and figures.
2. Read `METHODS.md` for the new operational definitions, modelling and limitations.
3. Inspect `analysis/01_households_climate.py` through `analysis/12_mecco_sensitivity.py`, the claim audit, and their output tables in `data/processed/`.
4. Review `analysis/baseline/` for the prior models, source-specific analyses, sensitivity checks, figures and original article. The baseline is part of this research; it is retained separately so that changes and methodological decisions remain auditable.
5. Consult `data/raw/README.md` and the baseline source notes before obtaining raw data. Some source providers restrict redistribution.

## Four follow-up investigations

- **Two concerns in the same person:** weighted ESS cross-tabulations of `hincfel` and `wrclmch`, by country and wave, now including all four cells and their unweighted counts; adjusted linear probability model and mode sensitivity.
- **The 80% claim:** two non-overlapping sets of Manifesto Project categories with a stated denominator, actual election dates and vote-coverage disclosure; a separate dictionary pilot on two Spanish 2023 programmes and a 48-span non-independent audit.
- **News and personalised feeds:** MeCCO newspaper counts and NYT Index topic sample, with a matched-topic comparison against annual Gallup MIP response shares for 2010–2016 and a published exposure study. The data do not reveal an individual's feed; the project does not quantify that person's selection bias.
- **Change within the economic agenda:** 14-country SPES timelines of the share naming unemployment and prices. Country comparisons and missing years are visible.

## Findings that change the interpretation

In 2010, a mean of 47.9% named unemployment among the two main national problems across the fixed 14-country Western European sample. In 2024 that share was 8.1%; mentions of prices rose from 17.7% to 33.7%. Thus economic concerns were prominent at the beginning of the period, although their composition changed.

In matched ESS countries, severe climate worry coexisted with reported financial difficulty. The unadjusted 2020–2022 country-average shares worried about climate were 39.8% in the difficulty group and 39.6% in the comfortable/coping group. The exploratory adjusted round-10 association was +1.35 percentage points, 95% interval −0.98 to +3.69. It does not establish equivalence or causality.

At the latest elections covered for five of the six countries in Manifesto 2023a, the broad operationalisation of economic, welfare and institutional categories ranges from 53.8% to 63.6% of coded text, conditional on available weighted documents. Elections range from 2017 to 2022; Thailand is not in that dataset. A different category scheme or newer elections could yield different values.

In the selected Spanish MeCCO basket, counts rise 22.0% from 2010 to 2025 but fall 36.6% from 2021 to 2025. The basket contains no denominator for all articles and does not establish a national media share. A NYT classifier from the baseline missed most immigration cases on temporal testing; its predictions are retained for audit, not used to infer recent media trends.

## Country-focused follow-up

Ten Brazilian Latinobarómetro waves show corruption mentions rising to 31.2% in 2017 and falling to 4.4% in 2024, while narrow economic mentions are 17.2% in 2010 and 17.1% in 2024. The single open-ended question, changing codes, denominator sensitivity and quota-based sampling constrain interpretation. SPES series for Spain, Bulgaria and Serbia support declines in unemployment mentions and rises in price mentions at the stated endpoints. The six-country evidence remains incomplete, particularly for Thailand and identity salience. See [research_audit.md](research_audit.md), [RESEARCH_CHANGELOG.md](RESEARCH_CHANGELOG.md), [opinion methods](analysis/08_opinion_notes.md) and [manifesto methods](analysis/09_manifesto_notes.md).

## Open limitations

This is an exploratory synthesis, not a registered or externally peer-reviewed study. There is no complete comparable annual 2010–2026 panel of public opinion, media, programmes, electoral behaviour and policy for every country requested. The public repository does not redistribute ESS microdata, Manifesto Project source material or third-party corpora. No observed association alone establishes the mechanism suggested by the original claim.
