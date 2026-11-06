"""Validate completed BES snapshot aggregates without respondent records."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/three_explanations'


def main():
    run = json.loads((OUT / 'bes_models_run.json').read_text())
    assert hashlib.sha256((ROOT / 'analysis/59_bes_pre_election_models.py').read_bytes()).hexdigest() == run['script_sha256']
    assert hashlib.sha256((OUT / 'bes_input_contract.json').read_bytes()).hexdigest() == run['contract_sha256']
    contract = json.loads((OUT / 'bes_input_contract.json').read_text())
    for p, sha in contract['fixed_input_hashes'].items():
        assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == sha
    point = pd.read_csv(OUT / 'bes_model_margins.csv')
    assert len(point) == 120
    assert point.successful_draws.eq(1000).all()
    assert point.ci_low.le(point.ci_high).all()
    assert point[['ci_low', 'ci_high']].ge(-1).all().all() and point[['ci_low', 'ci_high']].le(1).all().all()
    assert len(point[['year', 'target']].drop_duplicates()) == 12
    for (year, target), g in point.groupby(['year', 'target']):
        assert g.n.nunique() == 1 and g.n.iloc[0] == contract['sample_totals'][f'{year}:{target}']
    sens = pd.read_csv(OUT / 'bes_model_sensitivity.csv')
    assert len(sens[['year', 'target', 'scenario', 'fit']].drop_duplicates()) == 288
    assert sens.groupby(['year', 'target', 'scenario']).n.nunique().eq(1).all()
    for d, keys in [(point, ['year', 'target']), (sens, ['year', 'target', 'scenario', 'fit'])]:
        assert not d.duplicated(keys + ['variable', 'outcome']).any()
        assert np.isfinite(d[['probability_difference', 'probability_at_low', 'probability_at_high']]).all().all()
        assert d[['probability_at_low', 'probability_at_high']].ge(0).all().all()
        assert d[['probability_at_low', 'probability_at_high']].le(1).all().all()
        assert np.allclose(d.probability_difference, d.probability_at_high - d.probability_at_low)
        grouped = d.groupby(keys + ['variable'])
        assert np.allclose(grouped.probability_difference.sum(), 0)
        assert np.allclose(grouped.probability_at_low.sum(), 1)
        assert np.allclose(grouped.probability_at_high.sum(), 1)
    cv = pd.read_csv(OUT / 'bes_model_validation.csv')
    assert len(cv) == 96 and not cv.duplicated(['year', 'target', 'block', 'validation']).any()
    assert np.isfinite(cv[['log_loss', 'brier_sum_over_classes']]).all().all()
    assert cv.log_loss.gt(0).all() and cv.brier_sum_over_classes.between(0, 2).all()
    incremental = pd.read_csv(OUT / 'bes_model_incremental_validation.csv')
    assert len(incremental) == 96 and incremental.bootstrap_draws.eq(2000).all()
    loss = cv.set_index(['year', 'target', 'block']).log_loss
    for r in incremental.itertuples():
        a, b = loss.loc[(r.year, r.target, r.baseline_block)], loss.loc[(r.year, r.target, r.expanded_block)]
        assert np.isclose(r.log_loss_reduction, a - b)
        assert np.isclose(r.relative_improvement_percent, 100 * (a - b) / a)
        assert r.passes_1pct_and_positive_interval == (r.relative_improvement_percent >= 1 and r.relative_ci_low > 0)
        assert r.participant_clusters == contract['sample_totals'][f'{r.year}:{r.target}']
    calibration = pd.read_csv(OUT / 'bes_model_calibration.csv')
    assert calibration.n.gt(0).all()
    assert calibration.small_bin_means_suppressed.equals(calibration.n.lt(20))
    for col in ['mean_probability', 'observed_fraction']:
        assert calibration[col].isna().equals(calibration.n.lt(20))
        assert calibration[col].dropna().between(0, 1).all()
    for (year, target, block, outcome), g in calibration.groupby(['year', 'target', 'block', 'outcome']):
        assert g.n.sum() == contract['sample_totals'][f'{year}:{target}']
    readable = point[['year', 'target', 'variable', 'outcome', 'n']].copy()
    for col in ['probability_difference', 'ci_low', 'ci_high']:
        readable[col + '_pp'] = 100 * point[col]
    readable.to_csv(OUT / 'bes_main_results_percentage_points.csv', index=False)
    report = {'fixed_input_hashes_match': True, 'marginal_estimates': 120,
              'completed_year_target_models': 12, 'bootstrap_draws_per_estimate': 1000,
              'validation_combinations': 96, 'paired_validation_comparisons': 96,
              'matched_sensitivity_specifications': 288,
              'probabilities_and_calibration_counts_passed': True,
              'raw_records_read_by_this_check': False,
              'validation_intervals_refit_training': False,
              'remaining': run['remaining_declared_analyses']}
    (OUT / 'bes_result_checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
