"""Validate saved robustness aggregates without reading respondent records."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/three_explanations'


def main():
    run = json.loads((OUT / 'eb_robustness_run.json').read_text())
    assert hashlib.sha256((ROOT / 'analysis/54_eurobarometer_robustness.py').read_bytes()).hexdigest() == run['script_sha256']
    groups = {
        'eb_leave_one_country_margins': ['target', 'omitted_country'],
        'eb_country_margins': ['target', 'country'],
        'eb_measurement_sensitivity': ['target', 'scenario', 'fit'],
        'eb_turnout_all_reported': ['scope'],
    }
    counts = {}
    for name, keys in groups.items():
        d = pd.read_csv(OUT / (name + '.csv'))
        assert not d.duplicated(keys + ['variable', 'outcome']).any()
        assert np.isfinite(d[['probability_at_low', 'probability_at_high', 'probability_difference']]).all().all()
        assert d[['probability_at_low', 'probability_at_high']].ge(0).all().all()
        assert d[['probability_at_low', 'probability_at_high']].le(1).all().all()
        assert np.allclose(d.probability_difference, d.probability_at_high - d.probability_at_low)
        g = d.groupby(keys + ['variable'])
        assert np.allclose(g.probability_difference.sum(), 0)
        assert np.allclose(g.probability_at_low.sum(), 1)
        assert np.allclose(g.probability_at_high.sum(), 1)
        assert g.n.nunique().eq(1).all()
        counts[name] = len(d[keys].drop_duplicates())
    assert counts['eb_leave_one_country_margins'] == 88
    m = pd.read_csv(OUT / 'eb_measurement_sensitivity.csv')
    assert counts['eb_measurement_sensitivity'] == 4 * 12 * 2
    assert m.groupby(['target', 'scenario']).n.nunique().eq(1).all()
    bounds = pd.read_csv(OUT / 'eb_unknown_party_bounds.csv')
    assert len(bounds) == 27 * 3
    assert bounds.lower_share.ge(0).all() and bounds.upper_share.le(1 + 1e-12).all()
    assert bounds.upper_share.ge(bounds.lower_share).all()
    bounds['width'] = bounds.upper_share - bounds.lower_share
    assert bounds.groupby('country').width.agg(lambda x: x.max() - x.min()).lt(1e-12).all()
    assert bounds.unresolved_voters_n.le(bounds.reported_voters_n).all()
    total = pd.read_csv(OUT / 'eb_nonlinear_validation.csv')
    country = pd.read_csv(OUT / 'eb_nonlinear_validation_by_country.csv')
    keys = ['target', 'validation', 'block']
    metrics = ['log_loss', 'brier_sum_over_classes']
    assert len(total) == 15 and not total.duplicated(keys).any()
    assert not country.duplicated(keys + ['country']).any()
    means = country.groupby(keys)[metrics].mean().reset_index()
    joined = total.merge(means, on=keys, suffixes=('_total', '_country'), validate='one_to_one')
    for metric in metrics:
        assert np.allclose(joined[metric + '_total'], joined[metric + '_country'])
    comparison = pd.read_csv(OUT / 'eb_nonlinear_comparisons.csv')
    assert len(comparison) == 15
    linear = pd.read_csv(OUT / 'eb_model_validation_by_country.csv')
    for r in comparison.itertuples():
        h = country[country.target.eq(r.target) & country.validation.eq(r.validation)]
        b = h[h.block.eq('full')].log_loss.mean()
        if r.comparison == 'hgb_full_vs_linear_full':
            a = linear[linear.target.eq(r.target) & linear.validation.eq(r.validation) & linear.block.eq('full')].log_loss.mean()
        else:
            block = 'baseline' if r.comparison.endswith('baseline') else 'plus_priority'
            a = h[h.block.eq(block)].log_loss.mean()
        assert np.isclose(r.relative_improvement_percent, 100 * (a - b) / a)
        assert r.passes_1pct_and_positive_interval == (r.relative_improvement_percent >= 1 and r.ci_low_percent > 0)
    report = {
        'robustness_script_hash_matches': True,
        'aggregate_specification_counts': counts,
        'probability_conservation_and_matched_samples_passed': True,
        'nonlinear_validation_combinations': len(total),
        'nonlinear_country_weighted_metrics_match': True,
        'unknown_party_bounds_countries': 27,
        'sensitivity_margins_have_confidence_intervals': False,
        'validation_intervals_refit_training': False,
        'remaining': ['Pre-election panels, temporal order, national elections, and party supply.',
                      'Measurement alternatives change the estimand; they are not interchangeable replications.',
                      'Unknown-party bounds describe vote shares, not bounds on regression coefficients.'],
    }
    (OUT / 'eb_robustness_checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
