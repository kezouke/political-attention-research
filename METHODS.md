# Methods, scope and interpretation

## 1. Financial difficulty and climate concern

ESS8 edition 2.3, ESS10 edition 3.3, and ESS10SC edition 3.1 were downloaded from the official ESS portal on 30 October 2026. Intersect the countries in round 8 and round 10, giving 22 countries. ESS rounds are independent cross sections. Six round-10 countries use a separate self-completion file, whereas the round-10 interview file includes in-person and some video interviews.

Use `wrclmch` 1–5; set the outcome to 1 for 4–5, 0 for 1–3. For `hincfel`, combine values 1–2 (comfortable or coping) and 3–4 (difficult or very difficult). Exclude missing, refusal and don't-know responses. Apply `pspwght` within countries. Country group means give each country the same weight; sample sizes are unweighted valid response counts. The analysis is descriptive, not an estimate of actual income or poverty.

For the exploratory linear probability model, restrict to valid age (15–100), gender (1 or 2 as recorded), education (eisced 1–7), ideology (lrscale 0–10), and both outcome variables. Normalise weights to sum to 1 per country-wave. Regress climate concern on financial difficulty, round, their interaction, age in decades, gender, education, ideology and country indicators. Use country-clustered SE and t inference. Repeat for the 16 countries with round-10 interviews. Clustered variance does not fully incorporate ESS stratification, primary sampling units, design effects or mode changes; 16 or 22 clusters are limited. The analysis is observational, exploratory and not preregistered. Do not call coefficients causal effects or interpret a nonsignificant result as evidence of equality.

## 2. Party documents and the “80%” proposition

Manifesto Project 2023a is analysed on elections from 2010 to 2022 for nine comparator countries and Russia. Percentages are source-coded shares of quasi-sentences, not shares of voters or speeches. A document's total may contain additional unspecified or uncoded categories. Two definitions are proxies, not a complete interpretation of the original post:

- Narrow: all main economy categories `per401`–`per416`, plus anti-corruption `per304`.
- Broad: the above plus welfare `per503`/`per504`, labour `per701`/`per702`, democracy and constitutional categories `per202`–`per204`, and administration/institutions `per301`–`per303`/`per305`.

Each three-digit category is counted once. Broad political and welfare categories can include statements outside the claim. Conversely relevant ideas may be coded elsewhere, so neither definition is an upper bound for every conceivable reading. Each country-election value is the mean across usable documents weighted by `pervote`; for Brazil use `presvote`, the first-round presidential vote. We report the sum of vote shares covered and document count. This is conditional on available documents and may include electoral coalitions and substitute texts. It is not representative of missing parties. No interpolation between elections. The source is a 2023 edition and does not include Thailand or current elections for many countries.

## 3. Media and selective exposure

MeCCO monthly chart arrays were captured on 30 October 2026. Sum the published 12 monthly entries for each year; the year index treats the first published value as January of its stated start year. The three-country Russian basket omits Izvestiya, whose entire 2025 sequence is zero in the captured source. Divide each selected basket's annual count by its own 2010 count and multiply by 100. These are counts of keyword-matching articles in a small set of newspapers. They are not a share of all articles, reach, a random national media sample, or a personalised feed. Changes in indexing and output may matter.

CAP NYT Index is a systematic sample of index entries, specifically the first entry on odd-numbered pages. Count the primary topic label among nonmissing topic records by year for 2010–2016. The civil-rights category is broader than gender and identity. It cannot establish how identity topics compare in recent social feeds. An earlier TF–IDF/logistic classifier was tested on 2010–2016 with an earlier training window and was not used to infer trends beyond its test period because of poor recall for rare classes.

## 4. Economic issue priorities

SPES annual Eurobarometer aggregates provide country-year percentages naming each of several issues among the most important problems facing the country. The 14-country series is an unweighted mean of country percentages, not a population-weighted EU statistic. There is no 2011 observation; the chart breaks the line rather than interpolating. Multiple responses are allowed and shares cannot be summed. The harmonised environment category combines climate, environment and energy security.

The earlier model joins the country-year inflation series with price-mention share and compares country-fixed-effect specifications with and without year indicators. Standard errors are clustered by country. A sharp coefficient change when adding year indicators is a warning about common time shocks, not proof that inflation has no effect.

## Provenance and precision

Read `data/raw/README.md` and the baseline source notes for dataset versions, original citations and access requirements. Published percentages are rounded for display; `data/processed/` contains unrounded calculations. Raw third-party files and ESS identifiers are excluded from the public repository. Missing observations are not interpolated; the site marks the period and denominator of each figure. Review findings for dataset release changes before generalising to 2026 or to a country not represented in a particular source.

## 5. Four-cell ESS table

`ess_four_groups.csv` gives all combinations of financial difficulty and severe climate worry for each matched country and wave. The denominator is everyone in that country-wave with valid answers to both questions and a positive post-stratification weight. Each cell includes its unweighted respondent count, the unweighted total, the weighted percentage and mode of the relevant file. The cell counts and percentages sum to the total and 100% within each country-wave. The ESS10 interview file includes some video interviews; the mode label is at the file level, not an individual interview-mode classification.

## 6. Independent text-analysis pilot on two Spanish programmes

The pilot uses the 2023 national election PDFs published by PP and PSOE. PyMuPDF 1.26.7 extracts text from page 9 onward for PP and page 11 onward for PSOE (one-based PDF page numbers), omitting initial contents pages. PDF layout can combine titles and distinct policy proposals. Text is split after sentence punctuation, then spans with fewer than eight word tokens are discarded. This is a mechanical unit, not a validated quasi-sentence or a representative sample of elections. Two parties in one country are not a proxy for six countries.

The dictionaries in `analysis/06_spain_text_pilot.py` identify exact Spanish word patterns for economy, institutions, climate/environment, identity and migration. Categories overlap. The economic/institutional indicator is the union of its two dictionaries. Counts are fractions of retained machine-defined spans containing an expression, not a fraction of all semantically relevant claims. The lexicon misses synonyms, implicit claims and meanings in context; inferences about the 80% proposition are not warranted.

For an error inspection, 12 matched and 12 unmatched spans were sampled within each party using random seed 42. The assistant conducting the analysis assigned provisional binary relevance labels with model results visible; this was not a blinded or independent human audit. For the economy/institution union, 20/24 matches were relevant and 9/24 non-matches were relevant. These intentionally stratified counts are not population accuracy or prevalence estimates, and only this union was audited. `spain_text_audit.csv` records the fixed sample identifiers, content hashes, model labels and provisional decisions without redistributing passages; the source text can be reconstructed locally to inspect individual errors. Examples of errors: employment surveys can match “empleo” without making an employment policy claim; discussion of labour reform or administrative procedures can be missed when dictionary terms are absent.

## 7. US newspaper index versus public issue mentions

`analysis/07_us_media_public.py` compares matching US Policy Agendas major codes for 2010–2016. Gallup's annual MIP data average poll-level issue shares after normalising all reported problem mentions to 100% within each poll. They are shares of mentions, not population proportions. NYT values are shares of the first index entry on odd-numbered pages, with a denominator of all entries with nonmissing major topic. The sample is not a news feed or audience exposure; NYT categories include foreign and local coverage. Although the topic scheme is aligned, coding and underlying units are not interchangeable. Differences do not identify media bias, causal influence or represent the original author's feed. Civil rights is broader than gender or LGBTQ topics. Data and [Gallup codebook](https://minio.la.utexas.edu/compagendas/codebookfiles/Gallups_Most_Important_Problem_Codebook.pdf) are available from [Policy Agendas](https://www.comparativeagendas.net/project/us/datasets).
