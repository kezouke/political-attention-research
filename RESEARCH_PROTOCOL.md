# Crisis, party programmes and electoral reweighting

## Starting point, 6 November 2026

The previous published essay and all its calculations are preserved at commit
`7f380831a4b4c66a75ec6b29e80fea3cbab2a1a9`. Its HTML is also retained as
`docs/crisis-baseline.html`. Existing output files are not overwritten by the
new analyses. This is an exploratory follow-up, not a preregistered study:
source coverage and selected Spanish rows were inspected before this protocol.

Question: after a banking crisis, how much of a change in the vote-weighted
programme agenda comes from changes within continuing parties, electoral
reweighting, and the observed party/document roster? These accounting terms
are not causal effects, and aggregate votes do not identify individual switches.

## Analysis decided before new outcome calculations

1. Extend the existing 29 main parliamentary banking episodes to the second
   post-onset election. Keep the original baseline, count actual elections
   rather than skipping missing classifications, require democratic endpoints,
   report elapsed years, use a ten-year maximum horizon, and flag/exclude a
   subsequent banking onset. Compare both post elections on a balanced sample.
   Report full distribution, medians, means, common-wave and country sensitivity.
2. Match Manifesto Project 2023a to the exact country and election month in the
   existing calendar. Keep valid positive parliamentary vote weights, coded
   document length and actual programmes. Exclude interpolated/carried-forward
   material, substitutes and missing documents from the primary text analysis.
   Document types 1, 2 and 8 are the initial candidates, subject to the codebook.
   Primary total coverage is 75% at both endpoints; repeat at 60%, 90%, with
   single-party programmes, unchanged known coding manuals and observed votes.
   Publish the exclusions and coverage, not just successful matches.
3. Fix topic definitions: core economy = 401–415, broad material provision =
   401–415 + 503–507 + 701–704; anticorruption = 304; environment = 501;
   broad cultural proxies = 601, 603–608, 705, reported as a sensitivity rather
   than a comprehensive measure of identity. No automated populism relabelling.
   These are shares of coded statements, not people, exposure or all campaign
   communication. Inspect narrower subcategories when broad totals conceal
   opposing policies. Do not sum overlapping topic constructs.
4. Use the symmetric exact decomposition for parties observed at both dates:
   mean vote weight × change in topic share, plus mean topic share × change in
   vote weight. Add the contribution of records present at only one endpoint.
   Call the latter roster change, not verified party births/deaths. Also compute
   the decomposition entirely within the common-party sample, renormalising
   weights there. Report common-party coverage. Use raw vote contributions as
   a sensitivity to conditional-weight normalisation and missing coverage.
5. Benchmarks are the existing other-recession and calm-period comparisons,
   supplemented by the previous election interval for eligible crisis cases.
   Compare the same coverage rules, duration, country composition and manual
   changes. Any regressions are exploratory associations; country clustering,
   limited clusters and global waves must remain explicit. No causal language
   based on before/after differences, a coefficient or a decomposition alone.
6. The NLP experiment must be evaluated before using predictions as evidence.
   Use externally coded Spanish CAP statements: earlier elections for training,
   2004 for model selection/calibration, 2008 as a held-out later document.
   Compare a lexical TF–IDF classifier with a multilingual transformer encoder
   and a supervised classifier. Report class-specific precision/recall and
   errors in document topic shares, not just overall accuracy. CAP and MARPOR
   are different coding schemes. A one-document test cannot validate a global
   multilingual deployment or a new frame/pledge-extraction task. Additional
   human-independent labels cannot be manufactured by the same assistant.
   Retain a failed model as a diagnostic, not a replacement for coded data.

## Publication criteria

The article must revolve around the best-supported substantive result, show
the scale and selection of its actual sample, explain why each comparison is
needed, and distinguish observations, accounting identities and causal
interpretations. Stronger results are not guaranteed. Do not restore unrelated
country vignettes merely because they already exist. Preserve a public methods
record, machine-readable aggregates, source hashes, tests of accounting and
sample construction, and a claim-to-evidence audit. Validate both languages
and the deployed page before reporting completion.

## Exploratory extension after the first programme results

The programme decomposition is also checked against V-Party's existing
continuous expert-coded populism index. This was added after seeing the initial
programme results: it tests whether the binary WPD outcome and programme-topic
shares describe the same change. Apply the same 75% coverage threshold and the
same symmetric decomposition to the continuous index. Report scores on a
0–100 index scale, never as percentage points of populist votes. This is a
measurement sensitivity, not a substitute definition chosen for significance.

A second exploratory check asks whether programme features improve a modest
forecast of continuing parties' vote-share changes. Use only main eligible
banking, recession and calm pairs; deduplicate identical country/election pairs.
Compare no-change, prior-vote/duration/year/party-family ridge, and the same
model with prior topic shares and programme changes. Train on earlier elections
and test in successive five-year blocks from 2000. Tune ridge strength by
country-grouped folds within the historical training data. Balance the error
by election, publish every test block and exclude no failure after inspection.
This cannot predict entrants and is not a comprehensive election forecast.
