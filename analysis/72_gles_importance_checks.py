"""Verify importance-change aggregates, frozen inputs and probability arithmetic."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/three_explanations'


def main():
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    run = json.loads((OUT / 'gles_importance_models_run.json').read_text())
    assert digest(ROOT / 'analysis/71_gles_importance_change_models.py') == run['script_sha256']
    assert digest(OUT / 'gles_importance_input_contract.json') == run['contract_sha256']
    contract = json.loads((OUT / 'gles_importance_input_contract.json').read_text())
    for filename in ['gles_importance_input_contract.json', 'gles_input_contract.json']:
        for p, sha in json.loads((OUT / filename).read_text())['fixed_input_hashes'].items():
            assert digest(ROOT / p) == sha
    margins = pd.read_csv(OUT / 'gles_importance_model_margins.csv')
    sensitivity = pd.read_csv(OUT / 'gles_importance_sensitivity.csv')
    assert len(margins) == 72 and len(sensitivity) == 576
    assert margins.successful_draws.eq(1000).all() and margins.ci_low.le(margins.ci_high).all()
    keys = ['model_topics', 'topic', 'position_scenario']
    assert len(sensitivity[['model_topics', 'scenario']].drop_duplicates()) == 32
    for frame, groups in [(margins, keys), (sensitivity, keys + ['scenario'])]:
        assert not frame.duplicated(groups + ['outcome']).any()
        assert np.isfinite(frame[['probability_at_low', 'probability_at_high', 'probability_difference']]).all().all()
        assert frame.probability_at_low.between(0, 1).all() and frame.probability_at_high.between(0, 1).all()
        assert np.allclose(frame.probability_at_high - frame.probability_at_low, frame.probability_difference)
        assert np.allclose(frame.groupby(groups).probability_difference.sum(), 0)
        assert np.allclose(frame.groupby(groups).probability_at_low.sum(), 1)
        assert np.allclose(frame.groupby(groups).probability_at_high.sum(), 1)
        for model, g in frame.groupby('model_topics'):
            assert g.n.eq(contract['sample_totals'][model]).all()
    cv = pd.read_csv(OUT / 'gles_importance_validation.csv')
    incremental = pd.read_csv(OUT / 'gles_importance_incremental_validation.csv')
    assert len(cv) == len(incremental) == 12
    assert not cv.duplicated(['model_topics', 'block']).any()
    assert cv.log_loss.gt(0).all() and cv.brier_sum_over_classes.between(0, 2).all()
    assert incremental.bootstrap_draws.eq(2000).all()
    lookup = cv.set_index(['model_topics', 'block']).log_loss
    for r in incremental.itertuples():
        a = lookup.loc[(r.model_topics, r.baseline_block)]
        b = lookup.loc[(r.model_topics, r.expanded_block)]
        assert np.isclose(a - b, r.log_loss_reduction)
        assert np.isclose(100 * (a - b) / a, r.relative_improvement_percent)
        assert r.passes_1pct_and_positive_interval == (r.relative_improvement_percent >= 1 and r.relative_ci_low > 0)
    transitions = pd.read_csv(OUT / 'gles_importance_transitions.csv')
    simultaneous = pd.read_csv(OUT / 'gles_importance_simultaneous.csv')
    assert len(transitions) == 54 and len(simultaneous) == 4
    for _, g in transitions.groupby(['model_topics', 'topic']):
        assert len(g) == 9 and g.n.nunique() == 1
        assert g.cell_n.sum() == g.n.iloc[0] and np.isclose(g.weight_share.sum(), 1)
    assert simultaneous.cell_n.sum() == 2962 and np.isclose(simultaneous.weight_share.sum(), 1)
    report = {'locked_hashes_match': True, 'marginal_estimates': 72, 'bootstrap_draws_per_estimate': 1000,
              'sensitivity_specifications': 32, 'validation_blocks': 12, 'paired_comparisons': 12,
              'transition_cells': 54, 'simultaneous_importance_cells': 4,
              'probability_and_sample_checks_passed': True, 'raw_records_read': False,
              'validation_intervals_refit_training': False}
    (OUT / 'gles_importance_result_checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
