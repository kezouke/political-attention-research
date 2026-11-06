"""Check completed German snapshot aggregates without respondent records."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/three_explanations'


def main():
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    run = json.loads((OUT / 'gles_models_run.json').read_text())
    for path, key in [('analysis/67_gles_pre_election_models.py', 'script_sha256'),
                      ('analysis/59_bes_pre_election_models.py', 'shared_BES_model_sha256'),
                      ('analysis/51_eurobarometer_models.py', 'shared_logistic_helper_sha256')]:
        assert digest(ROOT / path) == run[key]
    assert digest(OUT / 'gles_input_contract.json') == run['contract_sha256']
    contract = json.loads((OUT / 'gles_input_contract.json').read_text())
    for p, sha in contract['fixed_input_hashes'].items():
        assert digest(ROOT / p) == sha
    point = pd.read_csv(OUT / 'gles_model_margins.csv')
    assert len(point) == 100 and point.successful_draws.eq(1000).all()
    assert point.ci_low.le(point.ci_high).all()
    for (year, target), g in point.groupby(['year', 'target']):
        assert g.n.nunique() == 1 and g.n.iloc[0] == contract['sample_totals'][f'{year}:{target}']
    sensitivity = pd.read_csv(OUT / 'gles_model_sensitivity.csv')
    skeys = ['year', 'target', 'scenario', 'fit']
    assert len(sensitivity[skeys].drop_duplicates()) == 228
    for frame, keys in [(point, ['year', 'target']), (sensitivity, skeys)]:
        assert not frame.duplicated(keys + ['variable', 'outcome']).any()
        assert np.isfinite(frame[['probability_difference', 'probability_at_low', 'probability_at_high']]).all().all()
        assert frame[['probability_at_low', 'probability_at_high']].ge(0).all().all()
        assert frame[['probability_at_low', 'probability_at_high']].le(1).all().all()
        groups = frame.groupby(keys + ['variable'])
        assert np.allclose(groups.probability_difference.sum(), 0)
        assert np.allclose(groups.probability_at_low.sum(), 1) and np.allclose(groups.probability_at_high.sum(), 1)
    status = pd.read_csv(OUT / 'gles_classification_sensitivity_status.csv')
    assert len(status) == 24 and status.same_classes_and_minimum_5.sum() == 20
    skipped = status[~status.same_classes_and_minimum_5]
    assert skipped.year.eq(2009).all() and set(skipped.target) == {'opposition_type', 'four_outcomes'}
    assert skipped.scenario.str.endswith('strict').all()
    cv = pd.read_csv(OUT / 'gles_model_validation.csv')
    keys = ['year', 'target', 'validation', 'block']
    assert len(cv) == 80 and not cv.duplicated(keys).any()
    assert cv.log_loss.gt(0).all() and cv.brier_sum_over_classes.between(0, 2).all()
    incremental = pd.read_csv(OUT / 'gles_model_incremental_validation.csv')
    assert len(incremental) == 72 and incremental.bootstrap_draws.eq(2000).all()
    lookup = cv.set_index(keys).log_loss
    for r in incremental.itertuples():
        a = lookup.loc[(r.year, r.target, r.validation, r.baseline_block)]
        b = lookup.loc[(r.year, r.target, r.validation, r.expanded_block)]
        assert np.isclose(r.log_loss_reduction, a - b)
        assert np.isclose(r.relative_improvement_percent, 100 * (a - b) / a)
        assert r.passes_1pct_and_positive_interval == (r.relative_improvement_percent >= 1 and r.relative_ci_low > 0)
    choices = pd.read_csv(OUT / 'gles_nested_C_choices.csv')
    assert len(choices) == 240 and choices.chosen.sum() == 80
    for _, g in choices.groupby(['year', 'target', 'block', 'fold']):
        assert set(g.C) == {.1, 1., 10.} and g.chosen.sum() == 1
        assert np.isclose(g.loc[g.chosen, 'inner_log_loss'].iloc[0], g.inner_log_loss.min())
    calibration = pd.read_csv(OUT / 'gles_model_calibration.csv')
    assert calibration.small_bin_means_suppressed.equals(calibration.n.lt(20))
    assert calibration.mean_probability.isna().equals(calibration.n.lt(20))
    assert calibration.observed_fraction.isna().equals(calibration.n.lt(20))
    for (year, target, block, outcome), g in calibration.groupby(['year', 'target', 'block', 'outcome']):
        assert g.n.sum() == contract['sample_totals'][f'{year}:{target}']
    readable = point[['year', 'target', 'variable', 'outcome', 'n']].copy()
    for col in ['probability_difference', 'ci_low', 'ci_high']:
        readable[col + '_pp'] = 100 * point[col]
    readable.to_csv(OUT / 'gles_main_results_percentage_points.csv', index=False)
    report = {'locked_hashes_match': True, 'completed_year_target_models': 8, 'marginal_estimates': len(point),
              'bootstrap_draws_per_estimate': 1000, 'validation_combinations': len(cv),
              'paired_validation_comparisons': len(incremental), 'nested_inner_C_candidates': len(choices),
              'nested_outer_fits': 80, 'sensitivity_specifications': 228,
              'classification_checks_unestimable': skipped[['year', 'target', 'scenario']].to_dict('records'),
              'probability_and_calibration_checks_passed': True, 'raw_records_read_by_this_check': False,
              'validation_intervals_refit_training': False, 'remaining': run['remaining']}
    (OUT / 'gles_result_checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
