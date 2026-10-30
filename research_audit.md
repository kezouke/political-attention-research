# Claim-to-evidence audit

This audit reviews the version at commit `39b5d3f` before the 2026 follow-up analyses. It is a separate computational and methodological pass by an AI collaborator with access to the same project. It is not independent human replication, peer review or preregistration. “Supported” below always means supported for the stated measure and sample, not necessarily for the question in the post. The follow-up analyses should be assessed on their own terms in addition to this baseline audit.

## Prioritisation

1. **Comparability and six-country coverage.** The central proposition concerns relative issue prominence in six named countries over roughly 15 years. A Western European average, or two questions from a European survey, cannot establish that proposition for the other countries. The most consequential task is to find repeated, comparable measures for those countries and to report missing periods explicitly.
2. **Construct validity.** Climate worry, a forced choice between environment and growth, share of responses naming a national problem, content of party documents, counts of newspaper articles and what a person sees in a feed are different variables. Correlation between them is a hypothesis, not a definitional identity. Gender/identity, ethnicity, civil rights and immigration are also distinct constructs.
3. **Sample selection and survey routing.** ESS estimates exclude missing answers to the climate-worry item. Respondents who deny climate change were routed past the question in the round-10 interview questionnaire. The missingness is therefore substantively related to the outcome. Spain and Israel have different denominators and changed mode in round 10; the sensitivity analysis below quantifies what this could change.
4. **Manifesto coverage and document selection.** Average shares apply to coded documents and the votes associated with them. Missing parties, non-programme source documents and coalitions can change the aggregate. The sample’s most recent available election is not necessarily the latest election that actually occurred.
5. **Time and sampling uncertainty.** A line joining two observations does not observe the intervening years. Country differences are not a probability sample of the world. Cluster-robust standard errors with 16–22 clusters are approximate and do not account for the entire ESS sampling design. Record both model uncertainty and measurement sensitivity.
6. **Media sample and exposure.** MeCCO baskets have few newspapers and changing indexing practices. No denominator for the total output of those newspapers is available in these data. The US NYT Index and Gallup refer to different universes. Neither is a measure of an individual's feed.
7. **Validation.** The 48-span Spanish audit was conducted with the classifier's predictions visible by the same assistant who developed the lexicon. It is useful for diagnosing errors, but cannot validate generalisation, inter-rater reliability or independent human agreement.

## Claim-to-evidence matrix

| Claim in or underlying the article | Status | Direct evidence | What could change the inference or remains untested |
| --- | --- | --- | --- |
| Economic problems were important in 2010 in the analysed Western European sample. | Directly supported, within sample | SPES Eurobarometer country-year data: the equal-country mean naming unemployment among up to two national problems was 47.9% in 14 countries. | It is not a population-weighted average, does not cover all six focus countries, and does not measure campaign, media or government priorities. |
| Across those 14 countries the type of economic problem shifted from unemployment towards prices between 2010 and 2024. | Directly supported as an endpoint comparison | Unemployment mentions fell from 47.9% to 8.1%; price mentions rose 17.7% to 33.7%, with both endpoint directions in all 14 countries. | One missing year, 2011; answers may select up to two issues. The contrast does not tell us why an individual changed answers or show what happened in the other focus countries. |
| High inflation caused a higher share of respondents to name prices. | Untested causally; association sensitive to model | 196 country-years; price-mention association was 4.71 pp per inflation point with country fixed effects and 0.40 pp (95% CI −0.75 to +1.56) after adding year indicators. | Time effects absorb common shocks and some inflation variation; few clusters, omitted covariates and measurement differences remain. A small or nonsignificant estimate does not prove no effect. |
| People in financial difficulty and strongly worried about climate exist in the same sample. | Directly supported as an overlap | ESS8 and ESS10/10SC weighted joint distributions with valid answers and positive weights in 22 matched countries. Mean country overlap in round 10 is 6.7%. | This is not a population-weighted European estimate, causal displacement test or measure of relative priority. Survey routing and other nonresponse matter. Only Spain and Israel are among the six named countries. |
| Mean severe climate worry rose in most countries between the two ESS rounds. | Directly supported descriptively for valid responses; causal interpretation weak | ESS8 vs ESS10/10SC, 21/22 matched country percentages increased; mean country change +10.86 pp. The leave-one-country-out mean ranges +10.18 to +11.46 pp. | Not a random sample of the world; question asks worry, not ranking of priorities. Sample selection, modes and pandemic-era fieldwork may contribute. Spain and Israel changed to self-completion. |
| Financial difficulty has no association with climate worry. | Untested as equivalence; model compatible with effects in both directions | Adjusted round-10 association +1.35 pp, 95% CI −0.98 to +3.69; p = 0.24, 22 country clusters. | Failure to reject zero does not establish equivalence. Complete-case selection, functional form, measurement error, cluster count and unmodelled sampling structure limit inference. |
| About 80% of current campaigns in the six countries concern the proposed economic and institutional subjects. | Untested | The 2023a Manifesto release contains usable documents for five countries, at elections dated 2017–2022. A broad preselected proxy ranges 53.8–63.6% among coded and vote-weighted documents. | “Campaigns” differ from documents, the categories neither exhaust nor perfectly represent the post's concepts, some parties are absent, Thailand is absent, and dates vary. No claim about every conceivable definition of 80% follows. |
| The PSOE and PP programme charts estimate their true topic distributions. | Weakly supported as dictionary-match rates only | Exact Spanish lexicon applied to PDF-extracted text spans. A single non-blind AI audit found obvious omissions and false positives. | Segmentation may join text; synonyms and context are missed. The stratified sample does not estimate accuracy at population prevalence. It cannot test 80% of meaning or establish independent manual validation. |
| Climate news increased or decreased in particular selected newspapers. | Directly supported as counts in those baskets | MeCCO monthly source arrays, e.g. Brazilian selected basket 991 articles in 2021 and 1,550 in 2025; Spanish basket 3,265 and 2,071. | No article-volume denominator or stable indexing guarantee. These are not media shares, audiences, national media trends or feeds. Selected languages and outlets matter. |
| Recent gender/identity stories displaced economics in news or social feeds. | Untested | The NYT Index civil-rights series ends in 2016; civil rights is broader than identity. Some climate coverage measured elsewhere. | No comparable recent economy/identity content panel for six countries, no exposure or personalized-feed data, no denominator for all items. |
| The social-media post's author encountered a biased or algorithmically curated feed. | Untested for the individual | External multi-country exposure research suggests selective exposure can occur. | The individual's followed accounts, source posts, interactions, impressions and counterfactual rankings are unknown. General research cannot establish this person's mechanism. |
| A party's votes show the priority a voter assigned to each issue. | Untested | Vote shares weight available manifestos. | Votes conflate many motives, candidate traits, party loyalties and electoral rules; no issue-specific vote attribution is identified. |
| Renewable electricity shares and selected legal indicators changed. | Directly supported as stated outcomes | Ember generation shares and World Bank Women, Business and the Law 1.0 legal scores. | Shares are not total energy use; weather, output, infrastructure and imports matter. The legal score does not measure enforcement or identity issues broadly. No causal attribution to a particular government. |
| Attention to climate/identity caused elites to divert resources, or corrupt elites caused all economic changes. | Untested causally | None of the present data identifies the counterfactual causal chain. | Requires a causal design and defined mechanisms, timing, outcomes and alternative explanations. Descriptive time trends or issue rankings cannot establish it. |

## New checks from the audit

### Climate-worry routing and exclusion

The round-10 interview [questionnaire](https://stessrelpubprodwe.blob.core.windows.net/data/round10/fieldwork/united_kingdom/ESS10_questionnaires_GB.pdf) instructs that respondents saying climate change is not happening skip the subsequent worry question. In the files, `ccnthum=55` and missing `wrclmch` identify this observed combination; in the self-completion file some other people marked 55 and still answered the worry question, and they retain their observed answers. The record does not establish that every missing case was skipped for the same procedural reason.

`analysis/11_ess_routing.py` independently re-reads the three raw files and reports the valid observed denominator and the number with `ccnthum=55` and missing `wrclmch`. It recomputes the observed percentage and two limiting scenarios: all such missing cases strongly worried, or none strongly worried. It holds all other missing values excluded. The scenarios are not assertions about the actual answers, do not correct all missing data, and are not sampling confidence intervals. Data and scripts must be obtained as described in `data/raw/README.md`.

| Country | Round | Valid worry n | `ccnthum=55` and worry missing n | Observed very/extremely worried | Scenario: none strongly worried | Scenario: all strongly worried |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Spain | ESS8 | 1,901 | 7 | 49.67% | 49.50% | 49.84% |
| Spain | ESS10SC | 2,235 | 20 | 55.19% | 54.60% | 55.66% |
| Israel | ESS8 | 2,303 | 50 | 20.53% | 20.00% | 22.60% |
| Israel | ESS10SC | 1,144 | 80 | 32.50% | 30.29% | 37.10% |

Allowing each wave to take opposite endpoints gives scenario ranges for the change of +4.76 to +6.16 pp in Spain and +7.68 to +17.10 pp in Israel. These ranges do not include sampling uncertainty or answer-mode effects. Both countries' positive direction survives these particular extremes, but that does not establish a causal trend. Files `audit_ess_skip_sensitivity.csv`, `audit_ess_changes_sensitivity.csv` and `audit_ess_country_sensitivity.csv` contain all 22 country results. Source weighting details: [ESS Round 8 weighting strategy](https://www.europeansocialsurvey.org/sites/default/files/2023-06/ESS8_weighting_strategy.pdf).

### Missing party documents

`analysis/90_claim_audit.py` computes transparent extreme bounds under a deliberately generous hypothetical: the coded vote coverage consists of non-overlapping valid votes, all the missing votes correspond to documents for which the same broad definition is meaningful, and the missing documents' broad shares could be anywhere from 0% to 100%. Even then, the result concerns this broad code set, not the author's undefined “80%” or campaigns. Rounding, coalitions and substitute texts complicate the assumed vote accounting. These are arithmetic identification bounds, not confidence intervals.

| Latest coded election | Coded-vote coverage | Conditional broad share | Hypothetical all-vote range |
| --- | ---: | ---: | ---: |
| Bulgaria 2017 | 82.1% | 53.8% | 44.1–62.1% |
| Brazil 2018 | 92.5% | 63.0% | 58.3–65.8% |
| Spain 2019 | 97.0% | 63.6% | 61.7–64.7% |
| Israel 2020 | 56.1% | 57.9% | 32.5–76.4% |
| Serbia 2022 | 86.1% | 63.4% | 54.6–68.5% |

The current article's vote-weighted values are conditional on available documents; they should not be silently presented as a full-electorate estimate. The written methods say election-year observations are not interpolated, but the existing figure connects them with straight lines. Use unconnected points, or make the connecting lines explicitly descriptive and do not infer annual values.

## Reproduce and verify

`python analysis/11_ess_routing.py` requires the three raw ESS files already described in `data/raw/README.md`. `python analysis/90_claim_audit.py` uses the versioned election aggregate. Run `python -m unittest tests/test_audit_sensitivity.py` after regeneration. These checks compare program outputs and arithmetic; they are not a substitute for external review or full survey-design variance estimation.
