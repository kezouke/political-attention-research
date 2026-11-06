"""Check BES transfer/selection/nonlinear aggregates and locked provenance."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/three_explanations'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    run = json.loads((OUT / 'bes_robustness_run.json').read_text())
    assert digest(ROOT / 'analysis/64_bes_transfer_selection_nonlinear.py') == run['script_sha256']
    assert digest(ROOT / 'planning/bes-robustness-specification.md') == run['specification_sha256']
    assert digest(OUT / 'bes_input_contract.json') == run['input_contract_sha256']
    contract = json.loads((OUT / 'bes_input_contract.json').read_text())
    for p, sha in contract['fixed_input_hashes'].items():
        assert digest(ROOT / p) == sha
    temporal = pd.read_csv(OUT / 'bes_temporal_validation.csv')
    assert len(temporal) == 2 * 4 * 2 * 11
    tkeys = ['train_years', 'test_year', 'target', 'subset', 'learner', 'block']
    assert not temporal.duplicated(tkeys).any()
    for r in temporal.itertuples():
        assert max(map(int, str(r.train_years).split('+'))) < r.test_year
        if r.subset == 'all':
            assert r.n == contract['sample_totals'][f'{r.test_year}:{r.target}']
    counts = pd.read_csv(OUT / 'bes_temporal_counts.csv')
    ck = ['train_years', 'test_year', 'target', 'subset']
    for _, g in counts.groupby(ck):
        assert g.outcome_n.sum() == g.n.iloc[0]
    a = counts.groupby(ck).n.first().unstack('subset')
    assert (a.unseen_people <= a['all']).all() and a.unseen_people.gt(0).all()
    nonlinear = pd.read_csv(OUT / 'bes_nonlinear_validation.csv')
    nkeys = ['year', 'target', 'learner', 'block']
    assert len(nonlinear) == 36 and not nonlinear.duplicated(nkeys).any()
    linear = pd.read_csv(OUT / 'bes_model_validation.csv')
    for frame in [temporal, nonlinear]:
        assert np.isfinite(frame[['log_loss', 'brier_sum_over_classes']]).all().all()
        assert frame.log_loss.gt(0).all() and frame.brier_sum_over_classes.between(0, 2).all()
    for file, performance, keys in [('bes_temporal_calibration', temporal, tkeys),
                                    ('bes_nonlinear_calibration', nonlinear, nkeys)]:
        cal = pd.read_csv(OUT / (file + '.csv'))
        assert cal.small_bin_means_suppressed.equals(cal.n.lt(20))
        assert cal.mean_probability.isna().equals(cal.n.lt(20))
        assert cal.observed_fraction.isna().equals(cal.n.lt(20))
        ref = performance.set_index(keys).n
        for key, g in cal.groupby(keys + ['outcome']):
            assert g.n.sum() == ref.loc[key[:-1]]
    tcomp = pd.read_csv(OUT / 'bes_temporal_comparisons.csv')
    ncomp = pd.read_csv(OUT / 'bes_nonlinear_comparisons.csv')
    assert len(tcomp) == 176 and len(ncomp) == 36
    for comparisons, kind in [(tcomp, 'temporal'), (ncomp, 'nonlinear')]:
        for r in comparisons.itertuples():
            values = []
            for key in [r.baseline, r.expanded]:
                learner, block = key.split(':')
                if kind == 'temporal':
                    row = temporal[temporal.train_years.astype(str).eq(str(r.train_years)) & temporal.test_year.eq(r.test_year)
                                   & temporal.target.eq(r.target) & temporal.subset.eq(r.subset)
                                   & temporal.learner.eq(learner) & temporal.block.eq(block)]
                else:
                    source = nonlinear if learner == 'hgb' else linear
                    row = source[source.year.eq(r.year) & source.target.eq(r.target) & source.block.eq(block)]
                assert len(row) == 1
                values.append(row.log_loss.iloc[0])
            a, b = values
            assert np.isclose(r.relative_improvement_percent, 100 * (a - b) / a)
            assert np.isclose(r.log_loss_reduction, a - b)
            assert r.bootstrap_draws == 2000
            assert r.passes_1pct_and_positive_interval == (r.relative_improvement_percent >= 1 and r.relative_ci_low > 0)
    sm = pd.read_csv(OUT / 'bes_selection_margins.csv')
    keys = ['year', 'target', 'weighting']
    assert len(sm[keys].drop_duplicates()) == 36
    for _, g in sm.groupby(keys + ['variable']):
        assert np.isclose(g.probability_difference.sum(), 0)
        assert np.isclose(g.probability_at_low.sum(), 1) and np.isclose(g.probability_at_high.sum(), 1)
    old = pd.read_csv(OUT / 'bes_model_margins.csv')
    j = sm[sm.weighting.eq('reference')].merge(old, on=['year', 'target', 'variable', 'outcome'], validate='one_to_one', suffixes=('_new', '_old'))
    # The reference uses mathematically identical weights with a different sum
    # order (groupby sum versus Series sum). A local input audit established
    # identical people, outcomes and design, with max weight difference 3.6e-15.
    # Finite optimizer tolerance can amplify that rounding. Require agreement
    # within .001 percentage point, much smaller than the reported precision.
    max_reference_difference = float((j.probability_difference_new - j.probability_difference_old).abs().max())
    assert len(j) == 120 and max_reference_difference < 1e-5
    sw = pd.read_csv(OUT / 'bes_selection_weights.csv')
    assert len(sw) == 36 and sw.effective_n.gt(0).all() and (sw.effective_n <= sw.n + 1e-8).all()
    sd = pd.read_csv(OUT / 'bes_selection_diagnostics.csv')
    assert len(sd) == 6 and sd.prob_q0.gt(0).all() and sd.prob_q100.lt(1).all()
    report = {'locked_hashes_match': True, 'temporal_validation_combinations': len(temporal),
              'temporal_paired_comparisons': len(tcomp), 'nonlinear_validation_combinations': len(nonlinear),
              'nonlinear_paired_comparisons': len(ncomp), 'selection_models': len(sd),
              'selection_sensitivity_fits': len(sw), 'unweighted_record_exports': False,
              'reference_margins_match_original_within_0_001pp': True,
              'max_reference_margin_difference_pp': 100 * max_reference_difference,
              'probability_and_calibration_checks_passed': True,
              'fixed_heldout_loss_bootstrap_draws': 2000, 'validation_intervals_refit_training': False}
    (OUT / 'bes_robustness_checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
