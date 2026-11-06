# Economic discontent and political choice: methods and reproduction

This is the methods guide for the single bilingual essay published on 7 November
2026. It extends the preserved crisis and programme results with survey evidence.
The question is whether incumbent punishment, changing issue priorities and general
political distrust have different observable relationships with political choice.
It does not estimate a common causal effect of the 2008 crisis on those mechanisms.

## Evidence layers and populations

| Layer | Population used | What is compared |
|---|---|---|
| Historical elections | 29 banking-crisis episodes, 28 countries; identical sample at both horizons | Last pre-crisis election versus first and second subsequent elections |
| Programmes | 16 crisis episodes, 15 countries, at least 75% vote coverage at both endpoints | Last pre-crisis and first post-crisis programme topic shares and their decomposition |
| Eurobarometer 71.3 | 2009 European Parliament elections; 9,948 classified voters in 25 countries for cabinet voting; 15,962 people in 19 countries for four outcomes | Conditional associations under a common survey instrument, equal country weight |
| BES teaching v1 | Britain, 2015/2017/2019; primary joint samples 23,447/17,100/19,324 | Pre-election levels, prior party preferences, subsequently reported choice |
| BES repeated attitudes | Joint samples 15,613/8,758/3,111 | Later attitudes conditional on earlier attitudes and early intention |
| GLES campaign panels | Germany 2009/2013; primary joint samples 1,290/3,291 | Pre-election attitudes and subsequently reported choice |
| GLES repeated importance | 2,962 people with all three topics, July/August 2013 | Later importance conditional on earlier importance, early/late position and early intention |
| GLES designed long link | 360 people with core attitudes and classified outcome in both 2009 and 2013 | Paired descriptions with selection limitations, not a multivariable transition model |
| Additional national surveys | Eight surveys in six countries; with BES/GLES, 13 national election-survey cases in eight countries | Within-survey replication under different questions and party configurations |

The national extension uses ES2015, NL2010, NL2012, PT2005, PT2009, IS2013,
BE2014 and DK2007. Portugal 2005 and Denmark 2007 precede the 2008 crisis wave.
Belgium covers Flanders and Wallonia, excluding Brussels. These observations
are not pooled as a balanced European panel. Different conditional outcomes
have different sample sizes; their estimated differences must not be added.

The audit did not recover a common European panel measuring the same people
before the 2007–2009 crisis and afterwards with all required questions.
The common European cross-section and national panels answer distinct questions.
The user rejected narrowing the project to three countries, and the broader
European comparison was retained with these explicit limits.

## Definitions and measurement

The historical outcome remains the sum of national campaign vote shares classified
by the World Populism Dataset. Its usual threshold is 5%; absence is not a negative
label. WPD does not directly classify European Parliament campaigns.

Survey outcomes use The PopuList 4.0 with borderline cases, fixed before association
models. PopuList 3.0 and exclusion of borderline cases are mandatory alternatives.
PopuList covers parties with at least one national seat or 2% of national votes
since 1989. Unlisted parties receive a negative label only after coverage and
identity are verified. Party-period dates matter. Mixed lists, unclear regional
identities and unverified participation are not assigned to the largest component.

Cabinet membership is established for the whole coalition immediately before the
election. External parliamentary support is separate. Accordingly, “parties outside
the cabinet” is more precise than “opposition” in cases such as Denmark 2007.
Populist cabinet parties belong to the cabinet outcome. The four joint categories
are cabinet, other non-cabinet, populist non-cabinet and explicit abstention.
Unknown party and unknown turnout do not become abstention. Portugal’s national
models have only three observed, resolved categories; a populist class is not
fabricated. Strict classification removes the Icelandic populist category.

Economic assessments are subjective survey answers, not measured exogenous
financial losses. Eurobarometer asks about current national conditions; most
national surveys ask retrospective questions. Government trust in Eurobarometer
is not identical to performance approval in national surveys. General trust in
parties, trust in politicians, honesty and perceived responsiveness are also
distinct instruments. Their coefficients are not pooled across surveys.

The primary economic-priority definitions include the economy, employment,
income/prices as permitted by each codebook. Eurobarometer permits up to two
national problems; national surveys generally use the first problem or the
most important voting issue. Broad, personal and narrower alternatives are
separately recorded. No priority response is treated as observed attention time.
GLES supplies separate issue positions and absolute importance for taxation/social
spending, immigration and climate. Multiple issues can become more important.

Exact variable names, missing codes, directions, questionnaires, dates and
coalitions are frozen in the input definitions and their contracts. Particularly
important corrections include the Belgian trust code 11 meaning zero, different
directions of government ratings, the non-ordinal Dutch 2010 economy codes, and
German issue codes that differ across years. The chronological audit contains
earlier provisional interpretations; final contracts and result reports govern
the analysis.

## Models and interpretation

Binary and multinomial logistic models use L2 regularisation, primarily C=1.
Controls include age, gender, education, political orientation and verified
survey-specific variables. BES/GLES additionally account for party identity,
its strength and pre-election intention. Prior intention is available and verified
in the national extension only for Spain 2015, Netherlands 2010 and Belgium 2014.
Specifications without it answer a broader association question; attenuation
after its inclusion is not a causal mediation estimate.

Blocks add economy/government, priority and distrust. Each is also removed from
the full model, preventing all incremental comparisons from depending on one
addition order. Base and expanded predictions use identical people.

Results are average differences in predicted probabilities while other observed
features are retained. Most continuous attitudes are rescaled to 0–1 and compared
at 0.25 and 0.75. BES distrust instead compares trust 5 and 3 on its original 1–7
scale; binary trust and priority compare their two values. Discrete scales may
require interpolation. These contrasts are neither observed individual transitions
nor intervention effects, and their sizes are not directly comparable across
different instruments.

Primary uncertainty uses 1,000 country resamples for Eurobarometer and 1,000
participant resamples within national surveys. GLES paired descriptions use
2,000 participant resamples. These do not reconstruct every survey’s sampling
design or incorporate classification and measurement uncertainty. Multiple
comparisons are interpreted jointly, without selecting an isolated favourable
interval as the substantive conclusion.

Weights are chosen before fitting. Eurobarometer uses demographic voting-age
weights normalised within analytic countries and equal country totals. Vote-calibrated
weights are not the primary weights for the same vote outcome. National extension
models are unweighted for Portugal 2009, Iceland 2013 and Belgium 2014 because
suitable weight construction was not verified; four Belgian alternatives are
reported as sensitivity analyses. All alternative comparisons identify whether
they retain exactly the same people. Spanish coalition assumptions expand the
sample and are explicitly not a pure relabelling comparison.

## Timing, selection and prediction

BES level comparisons use waves 4/6 in 2015, 10/13 in 2017 and 17/19 in 2019.
Repeated comparisons use early/late/post waves 1/4/6, 4/10/13 and 16/17/19.
The 2017 early wave spans an intervening election, cabinet change and EU referendum.
The 2019 early trust subsample is not claimed to be randomly assigned. Cross-format
verification checked 253 variable-wave combinations in official teaching v1 files.

GLES 2009 economic measurements come from wave 1, other primary attitudes from
wave 2, and choice from wave 7. GLES 2013 primary attitudes use wave 3 and outcome
wave 7. Importance comparisons use waves 2 and 4. Known postal votes cast before
the relevant 2013 measurement are excluded. The 2009/2013 link uses the producer’s
designed identifiers and excludes reported identity inconsistencies. No arbitrary
national-survey IDs are joined across elections.

Observed panel selection is modelled with out-of-fold response probabilities and
inverse-probability weighting. This addresses selection on observed initial
characteristics conditional on core answers being available. It does not repair
unobserved attrition, initial nonresponse or all missing core answers.

Prediction is assessed using log loss and Brier loss on held-out observations.
Within-survey validation has five folds; British temporal checks train on earlier
elections and test later elections, including a separate new-person subset.
Eurobarometer additionally holds out countries. A fixed nonlinear histogram
gradient-boosting benchmark tests whether a linear baseline missed useful
nonlinearity in Eurobarometer and BES.

The declared useful-improvement criterion requires at least 1% lower log loss and
a positive interval lower bound. Loss intervals resample fixed held-out losses,
without refitting training folds. They are conditional on those fitted predictions.
Post-election predictors support statistical generalisation tests, not real-time
electoral forecasting. Significant conditional associations need not improve
prediction above existing intention. Predictive accuracy does not identify causes.

## Alternatives and unresolved explanations

Completed checks cover country influence, weights, party versions, borderline
cases, cabinet membership, mixed lists, priority wording, economic perceptions,
EU attitudes in the European-election comparison, prior party preferences,
selection, timing and nonlinear/temporal prediction. Programme analyses additionally
cover calm periods, preceding intervals, coverage bounds and coding-instruction
changes. All negative results are retained.

Not established: a common before-crisis individual panel, comparable exogenous
personal financial losses in all countries, a unified control for austerity or
corruption scandals, and a causal effect of changing party offers. The BES teaching
file does not provide a verified constituency for checking each respondent’s ballot
availability. National party participation does not guarantee a local candidate.
Post-crisis events may be mediators rather than appropriate controls; adding them
to one regression would not solve identification.

The Hungarian debt-shock result belongs to Gyöngyösi and Verner, not this repository.
Its postal-district exposure comparison illustrates the evidence required for a
more specific causal claim. The GLES importance test does not replicate or refute
the different long-run decomposition discussed by Gidron and Kikuchi.

Hugging Face and public-data searches did not establish a suitable independent
multilingual elite-blame benchmark. Existing E5 versus TF–IDF topic results remain
an experiment, not a validated replacement for expert party classifications.
See the [audit](DATA_AUDIT_2026.md) and preserved [programme methods](RESEARCH_METHODS.md).

## Rebuild the public article without microdata

Python 3.12 is the analysis environment. From the repository root:

```sh
python -m pip install -r requirements-dev.txt
python analysis/83_national_results_report.py
python analysis/84_choice_publication_figures.py
python analysis/85_build_choice_essay.py
python analysis/86_choice_publication_checks.py
python -m pytest -q
node tests/site.test.js
node tests/choice.test.js
```

Scripts 83–86 consume public aggregate tables and prose only. Script 84 exports
SVG figures in both languages and mobile layouts, with review PNGs under `output/`.
Script 85 builds `docs/index.html` from `article/essay.ru.md` and `article/essay.en.md`.
Script 86 checks the numerical claims, chart inputs, links and language structure.
It does not claim that checking saved aggregates independently reproduces model
estimation. The earlier page builder 30 belongs to the preserved programme essay
and must not be used to build the current main page.

## Re-estimate from licensed local inputs

Obtain the exact source versions under each provider’s conditions. Source URLs,
local filenames and SHA-256 hashes are in
`data/processed/audit_20261106/acquisition_manifest.json` and
`authenticated_downloads.json`. The latter records the user’s reported telephone
permission for the described GESIS workflow, not a written archive confirmation.
Files belong under `data/raw/audit_20261106/`; original historical inputs belong
under `data/raw/` as described in its README. Do not publish respondent rows,
identifiers, free-text responses, credentials or model-training copies of records.

| Source | Version or documentation |
|---|---|
| Eurobarometer 71.3 | [ZA4973 v3.0.0](https://doi.org/10.4232/1.11135), SAV plus producer missing-code script |
| GLES 2009 | [ZA5305 English v5.0.0](https://doi.org/10.4232/1.12198) |
| GLES 2013 | [ZA5704 English v3.2.0](https://doi.org/10.4232/1.12561) |
| GLES linked release | [ZA5757 v1.1.0](https://doi.org/10.4232/1.12536) |
| BES | [Teaching v1](https://doi.org/10.48420/25460980.v1), Figshare files 45212920 and 45212926 |
| Spain | CIS study 7715 merged pre/post-election file; acquisition manifest contains the official ZIP and documentation |
| Netherlands | DPES 2010/2012 DANS files 152271/168672 with their DDI metadata |
| Portugal | PES 2005/2009 POLEN files 9263/9273 with their DDI metadata |
| Iceland | [ICENES 2013](https://doi.org/10.34881/1.00009), GAGNÍS file 179 and DDI, custom research terms |
| Belgium | PartiRep 2014 DANS fixed-width data, SPS layout and ODS codebook, filenames in acquisition manifest |
| Denmark | [DNES 2007 archive](https://digidata.rigsarkivet.dk/download/37820), 2011 documentation explicitly supplying the 2007 issue key |

Icelandic source citations, including the earlier waves inspected in the audit:

- Harðarson, Ólafur Þórður; Önnudóttir, Eva Heiða; Þórðarson, Einar Már;
  Félagsvísindastofnun (2021). *Íslenska kosningarannsóknin 2007*. GAGNÍS,
  v1.0. [doi:10.34881/1.00007](https://doi.org/10.34881/1.00007).
- Harðarson, Ólafur Þórður; Önnudóttir, Eva Heiða; Þórðarsson, Einar Már;
  Félagsvísindastofnun (2021). *Íslenska kosningarannsóknin 2009*. GAGNÍS,
  v1.1. [doi:10.34881/1.00008](https://doi.org/10.34881/1.00008).
- Harðarson, Ólafur Þórður; Þórisdóttir, Hulda; Önnudóttir, Eva Heiða (2021).
  *Íslenska kosningarannsóknin 2013*. GAGNÍS, v1.0.
  [doi:10.34881/1.00009](https://doi.org/10.34881/1.00009).

The author spelling difference between the 2007 and 2009 records follows the
deposited metadata. Years above refer to archive publication, not fieldwork.

Committed contracts and crosswalks are the fixed definitions, not disposable
outputs to overwrite before comparing a replication. Model drivers import their
input modules directly. On a separate checkout with matching raw-file hashes,
the principal estimation sequence is:

```sh
python analysis/63_eurobarometer_corrected_replay.py
python analysis/59_bes_pre_election_models.py
python analysis/64_bes_transfer_selection_nonlinear.py
python analysis/67_gles_pre_election_models.py
python analysis/71_gles_importance_change_models.py
python analysis/73_gles_observed_selection.py
python analysis/74_gles_designed_long_link.py
python analysis/77_bes_repeated_attitude_models.py
python analysis/81_national_comparison_models.py
```

Some stages perform many bootstrap fits. The scripts save aggregate results, not
individual predictions or respondent extracts. Numerical results may vary slightly
across numerical-library versions. Checks 62/65, 69/72/75, 78 and 82 validate the
corresponding outputs and original input hashes. Script 63 runs checks 52/55 on
the corrected `eb_v2` destination and preserves v1 byte-for-byte. Do not substitute
v1 values when reproducing the article. Older audit counts describe availability
before final measurement and party restrictions, not final analytic samples.

Access conditions remain source-specific. Icelandic microdata require deletion
after the work and bibliographic notification to the archive; these obligations
are tracked separately from publishing permitted aggregate results. Permission
for one researcher’s workflow is not a blanket permission for others or for
redistribution. The public reconstruction path above does not require those files.

After the final source checks, the project's three downloaded ICENES microdata
files were deleted under clause 15 of the archive's terms. No respondent-level
derived dataset was saved. The [completion record](data/processed/three_explanations/archive_completion.json)
preserves file hashes, the scope of cleanup and the bibliographic-notice status.
A fresh model replication therefore requires acquiring those licensed source
files again; the public page and figures still rebuild from committed aggregates.

Full result reports: [Eurobarometer v2](EUROPEAN_RESULTS_V2.md),
[BES](FIRST_BES_RESULTS.md), [GLES](FIRST_GLES_RESULTS.md),
[national extension](NATIONAL_RESULTS.md). The exact specifications remain under
`planning/`. The project has not undergone independent expert peer review.
