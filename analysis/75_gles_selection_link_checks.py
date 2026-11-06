"""Check German selection and linked-person aggregate results."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/three_explanations'


def main():
    for filename in ['gles_selection_run.json', 'gles_linked_changes_run.json']:
        for p, sha in json.loads((OUT / filename).read_text())['hashes'].items():
            assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == sha
    d = pd.read_csv(OUT / 'gles_selection_diagnostics.csv')
    w = pd.read_csv(OUT / 'gles_selection_weights.csv')
    m = pd.read_csv(OUT / 'gles_selection_margins.csv')
    assert len(d) == 8 and len(w) == 36 and len(m) == 516
    assert d.observed_n.le(d.n).all() and d.probability_q0.gt(0).all() and d.probability_q100.lt(1).all()
    assert w.effective_n.le(w.n).all() and w.weight_q0.gt(0).all()
    for analysis, keys in [('snapshot', ['year', 'target', 'variable']),
                           ('importance', ['model_topics', 'topic', 'position_scenario'])]:
        a = m[m.analysis.eq(analysis)]
        assert not a.duplicated(keys + ['weighting', 'outcome']).any()
        assert np.allclose(a.groupby(keys + ['weighting']).probability_difference.sum(), 0)
        assert np.allclose(a.groupby(keys + ['weighting']).probability_at_low.sum(), 1)
        assert np.allclose(a.groupby(keys + ['weighting']).probability_at_high.sum(), 1)
        baseline_file = 'gles_model_margins.csv' if analysis == 'snapshot' else 'gles_importance_model_margins.csv'
        b = pd.read_csv(OUT / baseline_file)
        pair = a[a.weighting.eq('reference')].merge(b, on=keys + ['outcome'], suffixes=('_new', '_base'), validate='one_to_one')
        assert len(pair) == len(b)
        assert np.allclose(pair.probability_difference_new, pair.probability_difference_base, atol=1e-5)
        if d.below_floor_n.eq(0).all():
            q = a.pivot(index=keys + ['outcome'], columns='weighting', values='probability_difference')
            assert np.allclose(q['ipw_floor_0.05'], q.ipw_unbounded)
    link = pd.read_csv(OUT / 'gles_linked_paired_changes.csv')
    assert len(link) == 13 and link.bootstrap_draws.eq(2000).all()
    assert link.ci_low.le(link.ci_high).all()
    assert np.allclose(link.mean_2013 - link.mean_2009, link.mean_change)
    assert np.allclose(link.decreased_share + link.same_share + link.increased_share, 1)
    assert not link.variable.str.contains('climate').any()
    selection = pd.read_csv(OUT / 'gles_linked_selection_description.csv')
    assert len(selection) == 14
    assert set(selection.n) == {360, 1955}
    report = {'input_hashes_match': True, 'selection_models': 8, 'weighted_vote_models': 36,
              'selection_margin_rows': 516, 'reference_reproduces_primary': True,
              'reference_numerical_tolerance_probability': 1e-5,
              'probability_checks_passed': True, 'paired_linked_estimates': 13,
              'linked_sample_n': 360, 'paired_bootstrap_draws': 2000, 'raw_records_read': False,
              'selection_correction_removes_unobserved_bias': False}
    (OUT / 'gles_selection_link_checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
