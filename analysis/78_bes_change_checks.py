"""Check repeated-attitude BES aggregates without exporting respondent records."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/three_explanations'


def main():
    for file, field in [('bes_input_contract.json', 'fixed_input_hashes'),
                        ('bes_change_input_contract.json', 'fixed_input_hashes'),
                        ('bes_change_models_run.json', 'hashes')]:
        for p, sha in json.loads((OUT / file).read_text())[field].items():
            assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == sha, p
    contract = json.loads((OUT / 'bes_change_input_contract.json').read_text())
    m = pd.read_csv(OUT / 'bes_change_model_margins.csv')
    v = pd.read_csv(OUT / 'bes_change_model_validation.csv')
    inc = pd.read_csv(OUT / 'bes_change_incremental_validation.csv')
    s = pd.read_csv(OUT / 'bes_change_sensitivity.csv')
    status = pd.read_csv(OUT / 'bes_change_sensitivity_status.csv')
    t = pd.read_csv(OUT / 'bes_change_priority_transitions.csv')
    assert [len(x) for x in [m, v, inc, s, status, t]] == [120, 96, 96, 2240, 120, 12]
    assert m.successful_draws.eq(1000).all() and inc.bootstrap_draws.eq(2000).all()
    assert m.ci_low.le(m.ci_high).all() and inc.ci_low.le(inc.ci_high).all()
    assert np.isfinite(m.select_dtypes('number')).all().all()
    for a, keys in [(m, ['year', 'target', 'variable']),
                    (s, ['year', 'target', 'scenario', 'fit', 'variable'])]:
        assert not a.duplicated(keys + ['outcome']).any()
        assert np.allclose(a.groupby(keys).probability_difference.sum(), 0)
        for c in ['probability_at_low', 'probability_at_high']:
            assert a[c].between(0, 1).all()
            assert np.allclose(a.groupby(keys)[c].sum(), 1)
        assert np.allclose(a.probability_difference, a.probability_at_high - a.probability_at_low)
    for (year, target), a in m.groupby(['year', 'target']):
        assert a.n.eq(contract['sample_totals'][f'{year}:{target}']).all()
    refs = s[s.fit.eq('reference_same_subset') & ~s.scenario.isin(['age_consistent', 'positions'])]
    q = refs.merge(m, on=['year', 'target', 'variable', 'outcome'], suffixes=('_ref', '_primary'), validate='many_to_one')
    assert np.allclose(q.probability_difference_ref, q.probability_difference_primary, atol=1e-10)
    assert status.estimable.sum() == 112
    skipped = status[~status.estimable]
    assert skipped.scenario.eq('positions').all() and set(skipped.year) == {2015, 2017}
    assert skipped.n.eq(0).all()
    for _, a in t.groupby('year'):
        assert len(a) == 4 and a.cell_n.sum() == a.n.iloc[0]
        assert np.isclose(a.weight_share.sum(), 1)
    for row in inc.itertuples():
        a = v[(v.year == row.year) & (v.target == row.target)].set_index('block')
        delta = a.loc[row.baseline_block, 'log_loss'] - a.loc[row.expanded_block, 'log_loss']
        assert np.isclose(delta, row.log_loss_reduction)
        assert np.isclose(100 * delta / a.loc[row.baseline_block, 'log_loss'], row.relative_improvement_percent)
        assert row.passes_1pct_and_positive_interval == (row.relative_improvement_percent >= 1 and row.ci_low > 0)
    report = {'input_hashes_match': True, 'full_models': 12, 'margin_rows': 120,
              'bootstrap_draws_per_margin': 1000, 'validation_comparisons': 96,
              'sensitivity_specifications_estimable': 112, 'sensitivity_fits': 224,
              'positions_specifications_unestimable': 8, 'reference_reproduces_primary': True,
              'probability_checks_passed': True, 'priority_transition_cells': 12,
              'raw_records_read': False, 'causal_interpretation_supported': False}
    (OUT / 'bes_change_checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
