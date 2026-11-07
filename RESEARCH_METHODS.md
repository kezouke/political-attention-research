# Programmes and votes after banking crises

This note documents the [preserved programme essay](https://kezouke.github.io/political-attention-research/programme-baseline.html?lang=ru).
The [protocol](RESEARCH_PROTOCOL.md) records the sequence of analytical choices.
The [claim audit](RESEARCH_AUDIT_2026.md) distinguishes supported findings from
interpretations. This is an exploratory study assisted by AI, without an
independent human peer review. It is not a preregistered causal analysis.

## Preservation and source versions

The first-election study remains reproducible at commit
`7f380831a4b4c66a75ec6b29e80fea3cbab2a1a9`. Its page is preserved in
`docs/crisis-baseline.html`, and its processed data and scripts 21–22 remain
unchanged. New scripts 23–31 write separate outputs. Earlier opinion, media and
country research also remains in the repository; it is not evidence for every
claim in this new essay.

The election inputs are the frozen World Populism Dataset dashboard file,
PPEG 2025v1, V-Dem Regimes of the World, Laeven–Valencia 2020 and World Bank
real GDP growth. Their acquisition and calendar rules are documented in
[CRISIS_METHODS.md](CRISIS_METHODS.md) and [the raw-input guide](data/raw/README.md).
Programme data are Manifesto Project **2023a**, not the latest 2026 release:
the reproducible snapshot is already available locally and its SHA-256 is in
`programme_provenance.json`. Later coverage must not be implied.

The separate [2026a release comparison](MANIFESTO_REFRESH.md), completed on
7 November 2026, preserves this baseline and reports revisions under the same
selection rules. It leaves all 16 primary crisis cases and their change signs
unchanged, while altering the composition of the calm sample. The methods below
continue to describe the frozen 2023a analysis.

The [2026 Laeven–Valencia update](https://www.imf.org/-/media/files/publications/wp/2026/english/wpiea2026094-source-pdf.pdf)
was checked during the final source audit. Its Table 1 lists 13 newly identified
episodes. None occurs in a country contributing to our banking or two-interval
calm trajectories. The official ZIP URL returned HTTP 404; script 31 instead
extracts the table from PDF page 9, checks all 13 country names and retains the
PDF checksum. This verifies the added onsets, without silently replacing the
historical baseline with a new edition. The additions and check are in
`banking_2026_additions.csv` and `banking_source_refresh.json`.

## 1. The election horizon

Script 23 starts with exactly the previous primary set: 29 non-borderline,
unambiguously timed banking episodes, democratic parliamentary endpoints,
crisis starts in 1991–2008. It fixes the last pre-onset election and counts the
first and second actual post-onset elections in the existing calendar. Missing
classifications are never skipped. The second must be within ten years of the
latest possible onset date, democratic, and before a subsequent recorded banking
onset. Annual dates are treated conservatively when screening subsequent crises.
All 29 pass. Second elections span 1997–2018. Observed regime classifications
are annual; democracy between endpoints is not continuously verified.

The outcome is the sum of vote shares of campaigns classified as populist by
WPD, minus its value at the fixed baseline. WPD classifies campaigns, not an
unchanging party essence. Its approximate 5% inclusion threshold and changes
in campaign classification affect this outcome. The dataset mixes list and
alliance figures in some systems; see the original methods for date corrections
and the Argentine staggered-election caveat. We did not infer individual vote
switching from aggregate results.

`crisis_dynamics_episodes.csv` retains ranks −1, 0, 1, 2 and 3 with explicit
statuses. The article's first/second comparison uses `crisis_dynamics_balanced.csv`.
The balanced median changes are +0.18 and +5.48 pp; means +5.352 and +9.540 pp.
The difference of the medians is not the median individual-episode increment:
the latter is +3.91 pp. Fifteen episodes gain further between the two elections.
The median follow-up times are 1.925 and 5.878 years. Election order therefore
does not represent equal time intervals or a fixed-year event-study coefficient.

Script 26 builds 50 calm trajectories in 21 of the banking-sample countries by
joining two consecutive **eligible** calm intervals from the original data.
Every calendar year in both intervals must have nonnegative observed GDP growth
and no banking crisis. Total duration may not exceed ten years. These are not
the same 128 one-interval controls in the old article. Some sequences overlap.

The descriptive within-country contrast averages each country's banking and
calm changes separately, subtracts them, then weights countries equally. The
second-election contrast is +5.411 pp. A percentile interval resampling the 21
country means 4,000 times is [−1.189, 12.039]. Resampling handles repeated
observations within a country but not common international shocks. Differences
in era, elapsed time, countries, crises, institutions and selection remain. These
intervals are not confidence intervals for an identified causal effect.

## 2. Programme measurement and coverage

Script 24 matches country and exact election **month** to the existing calendar.
It requires positive `pervote`, positive document length, and available topic
codes. Parliamentary weights are never replaced with presidential votes to
fill a missing match. Duplicate country/month/party records fail an assertion.

Following the [Manifesto Project codebook](https://manifesto-project.wzb.eu/down/data/2023a/codebooks/codebook_MPDataset_MPDS2023a.pdf),
the main sample includes document types 1, 2 and 8: single-party programmes,
joint programmes assigned to members, and bloc programmes. Source-provided
nonmissing vote weights avoid counting a bloc and all its members twice.
Observed coverage above 101% fails the rule; the extra point allows rounding.
Type 3 estimates, generic programmes, other substitutes and missing documents
are excluded. A sensitivity includes type 3; another retains single-party texts.

At least 75% of votes must be represented at each endpoint. Among the 29 original
banking episodes, 16 pass (15 countries), ten have no usable endpoint, and three
have insufficient coverage. This is a selected, predominantly European sample.
Country and election details, exclusions, document counts, coding changes and
common-party coverage are in `programme_coverage.csv`. The analysis also covers
23 recession, 75 calm, 15 pre-crisis and 14 second-election intervals under the
same programme criteria. These are not mutually independent samples.

Topic definitions are fixed sets of original three-digit codes:

| Measure | Codes | Interpretation limit |
|---|---|---|
| Core economy | 401–415 | Excludes welfare, education and environmental anti-growth rhetoric |
| Broad material provision | 401–415, 503–507, 701–704 | Includes equality, education, welfare and group claims; not a universal definition of economics |
| Anticorruption | 304 | Not a general measure of populism or institutional reform |
| Environment | 501 | Environmental protection; not all climate/energy discussion |
| Cultural sensitivity | 601, 603–608, 705 | Includes nationalism, morality, order, civic-mindedness and minorities; not a complete identity measure |
| Market | 401, 414 | Market and economic-orthodoxy categories |
| Planning | 403, 404, 412 | Regulation, planning and controlled economy |
| Demand | 409 | Demand-management references |
| Orthodoxy | 414 | Source economic-orthodoxy category |
| Welfare expansion | 504 | Favourable welfare-expansion references |

These constructs overlap and must not be summed. Each source-coded statement
has its source category; our NLP discussion of genuinely overlapping meanings
does not turn MARPOR into a multilabel dataset. Shares describe coded text,
not media reach, citizen preferences or vote motives. A theme's relative share
can fall while its absolute number of statements rises.

## 3. The accounting decomposition

Let `s_pt` be topic percentage in party p's programme and `w_pt` its vote share
normalised over covered programmes at election t. The aggregate is
`A_t = sum(w_pt × s_pt)`. A party observed at both elections contributes:

`within = sum(mean(w_p0, w_p1) × (s_p1 − s_p0))`

`reweight = sum(mean(s_p0, s_p1) × (w_p1 − w_p0))`.

The roster component adds `w_p1 × s_p1` for post-only records and subtracts
`w_p0 × s_p0` for pre-only records. These three terms add exactly to `A_1 − A_0`.
The midpoint rule allocates interactions symmetrically, equivalent to averaging
the two possible orders of changing weights and shares. It is an accounting
identity, not a behavioural model or causal mediation analysis.

An unmatched ID can reflect a genuinely new party, a merger, an alliance, a
source-identifier change or a missing programme. No aggregate roster term is
labelled verified party birth/death. We additionally repeat the calculation
entirely within the matched-party set, renormalising its weights. Eleven main
banking episodes have matched-party coverage of at least 75% on both sides;
nine have a larger absolute within-programme than vote-weight contribution.
The summary file also reports a less restrictive 50% matched-coverage check.

The 16-episode economic means are +2.997 within, −0.613 reweighting and −0.787
roster, giving +1.596 pp net. These are means of episode components, not the
decomposition of one pooled world manifesto. Absolute-component comparisons
are not percentages of a net change when components offset one another.
Country weighting differs from episode weighting because Latvia occurs twice.

`programme_decomposition.csv` retains both conditional-weight results and raw
vote contributions (vote percentage divided by 100), plus worst-case bounds
assigning missing programmes 0% or 100% topic shares. These are scenario bounds,
not sampling confidence intervals. No source party-level dataset is republished.

## 4. Alternative explanations and measurement sensitivity

All primary topic definitions and seven coverage/document specifications are
published. They include 60%, 75% and 90% coverage, single-party documents,
unchanged known coding manual, unestimated vote weights, and inclusion of
estimated programmes. Further checks remove the 2007–2009 crisis wave, hold
common-party coverage high, remove manual/coder changes, and omit one country
at a time. They were not selected as independent confirmatory tests.

Eight main episodes include matched-party manual changes. Requiring unchanged
known manuals and 75% coverage leaves four episodes. Three retain a larger text
than reweighting contribution. This does not validate all observed text changes:
coder interpretation, document selection and segmentation remain. Both genuine
revision and measurement error load on the within-programme component.

For 14 episodes with eligible earlier programmes, script 26 compares the crisis
interval with the preceding interval. The economic-change difference averages
+1.365 pp, with a country-resampling interval [−3.579, 6.552]. This is a single
preceding interval, not a pre-trend validation. Calm-period dominance of the text
component (51/75 pairs) further prevents attributing that pattern to crises alone.
Without 2007–2009 starts there are only four banking programme pairs and the mean
economic shift is negative. This limits any universal economic-turn claim.

Script 27 checks V-Party v2's continuous, expert-coded populism index with the
same coverage threshold and exact election dates. It is scaled to **index points
from 0 to 100**, not percentage points of populist votes. Twenty first-election
pairs qualify. Their WPD/continuous-change rank correlation is only 0.209, so the
measures are not interchangeable. On 17 episodes observed through both elections,
the median cumulative index change rises from 1.149 to 4.239 points; this supports
the descriptive horizon distinction within that smaller sample, not equality of
the two populism measures. Expert measurement uncertainty is not propagated into
the accounting decomposition.

## 5. Historical prediction check

This exploratory check was added after inspecting the programme decomposition.
Script 28 uses main-eligible banking, recession and calm intervals, deduplicates
identical country/election pairs, and keeps only parties with programmes at both
elections. Its target is the change in unnormalised parliamentary vote percentage.

Training elections precede each test block: 2000–2004, 2005–2009, 2010–2014 and
2015–2019. The four tests contain 112, 135, 119 and 97 party observations in 24,
26, 22 and 17 election pairs. Overall: 463 observations, 89 pairs, 27 countries.
The training samples grow from 112 to 478 observations. It is a retrospective
temporal evaluation using later-compiled research data, not a real-time vintage
backtest. Election-type and data-coverage selection are inherited from the study.

Models are: no vote change; ridge using previous vote share, interval duration,
year and party family; the baseline plus prior economic/material/anticorruption/
environment shares; and the baseline plus those shares and their changes.
Programmes correspond to the coming election, but their exact release date is
not audited. No test-election vote share is used as an input feature.

Numeric features are standardised within training folds; party family is one-hot
encoded. Ridge strength is selected from 1, 10, 100, 1000 using five country-grouped
folds within each historical training window. Training weights equalise election
pairs. Model selection minimises the mean of within-election absolute errors.
All chosen penalties are 1000, indicating strong shrinkage. Models are linear
and omit incumbency, leaders, polling and campaign reach. They exclude entrants.

Election-balanced MAE is 4.151 pp for baseline and 4.167 for programme changes.
The paired mean error increase is +0.016 pp; equal-country increase +0.035 pp,
with country-resampling interval [−0.008, 0.082]. This does not show predictive
improvement, nor prove that programmes are irrelevant. Full fold results and
election-level errors are published, including the no-change comparator.

## 6. NLP benchmark

The [Spanish Comparative Agendas Project](https://www.comparativeagendas.net/project/spain/datasets)
provides independent topic annotations. Valid nonempty text with a substantive
major-topic code is retained. CAP's topic scheme is not MARPOR's; core economy
here maps to CAP 1, 5, 15. The broader material set is 1, 3, 5, 6, 13, 14, 15;
environment is 7, civil rights 2 and government operations 20. Government is
not an anticorruption label, and civil rights is not an LGBTQ-specific label.

Training uses 8,992 statements from 1982–2000, validation 3,193 from 2004, test
3,636 from 2008. The last document is PSOE; earlier documents represent PSOE
and PP at different elections, not a representative sample of all campaigns.
Sixty-two exact normalised cross-period repetitions were removed from training
or validation. Other near-duplicates and encoder-pretraining contamination were
not audited. Test labels are excluded from tuning.

The lexical baseline uses word unigram/bigram TF–IDF (40,000 features, minimum
document frequency 2) and unweighted multiclass logistic regression. The semantic
model uses frozen `intfloat/multilingual-e5-small`, revision
`614241f622f53c4eeff9890bdc4f31cfecc418b3`, 384-dimensional normalised embeddings,
`query: ` prefix, maximum 256 tokens and a trained logistic classifier. No remote
model code is enabled. Embeddings ran on Apple MPS with batch size 32. The
encoder is not fine-tuned. Regularisation is selected by validation macro-F1.

Test accuracy is 0.500 versus 0.602; macro-F1 0.482 versus 0.588. These are
classification results on one document, not multilingual deployment scores.
Topic-share estimates are reported both from hard labels and averaged predicted
probabilities. The latter do not imply externally validated calibration. E5's
economic-share error is +1.162 pp, civil-rights error −3.929 pp. These errors
preclude treating all model counts as accurate political trends. Predictions
are not used in the primary historical estimates or vote-prediction features.

Model/source hashes, parameter choices, class-group precision/recall and errors
are published. Source text, embeddings and downloaded weights remain local.
Error lists contain source IDs and hashes, not copied passages. No assistant
inspection is described as an independent human annotation exercise.

## Reproduce

The light rebuild uses committed aggregates:

```sh
python -m pip install -r requirements.txt
python analysis/29_research_figures.py
python analysis/30_build_research_page.py
python -m unittest discover -s tests
node tests/site.test.js
```

For the full analysis, obtain the original inputs from the raw-input guide,
generate the local calendar with script 21, then run 23, 24, 26, 27 and 28 in
that order. Script 25 requires the additional packages in
`requirements-research.lock`, downloaded model weights and the CAP raw text.
Script 31 requires the linked 2026 PDF. Then regenerate figures and the page.
The full environment lock records the actual analysis environment; it includes
optional NLP and visual-QA packages. Numerical MPS results can vary slightly
across devices and library versions. No model output is required to render the
published page, which works offline and includes static SVG figures.
