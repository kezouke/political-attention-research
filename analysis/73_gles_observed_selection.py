"""Declared German observed-selection sensitivity; aggregates only."""
from pathlib import Path
from datetime import datetime, timezone
import importlib.util
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import OneHotEncoder
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
def module(name, file):
    s = importlib.util.spec_from_file_location(name, ROOT / 'analysis' / file)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m

snapshot = module('snapshot', '67_gles_pre_election_models.py')
importance = module('importance', '71_gles_importance_change_models.py')
inputs, model, helpers, OUT = snapshot.inputs, snapshot.model, snapshot.helpers, snapshot.OUT
SEED = 20261106


def snapshot_design(train, test):
    X, Z, _ = model.design(train, test)
    e = OneHotEncoder(handle_unknown='ignore', sparse_output=False, dtype=float)
    return (np.column_stack([X, e.fit_transform(train[['pre_turnout_intention']])]),
            np.column_stack([Z, e.transform(test[['pre_turnout_intention']])]))


def observation_probability(x, observed, design):
    p = np.full((len(x), 2), np.nan)
    y = observed.astype(int).to_numpy()
    for a, b in StratifiedKFold(5, shuffle=True, random_state=SEED).split(np.zeros(len(x)), y):
        train, test = x.iloc[a], x.iloc[b]
        X, Z = design(train, test)
        m = helpers.fitted(X, y[a], inputs.normalized_weights(train).to_numpy())
        p[b] = m.predict_proba(Z)
    assert np.isfinite(p).all() and np.allclose(p.sum(axis=1), 1)
    assert (p[:, 1] > 0).all() and (p[:, 1] < 1).all()
    stats = helpers.metrics(y, p, inputs.normalized_weights(x).to_numpy())
    stats.update({f'probability_q{q}': float(np.quantile(p[:, 1], q / 100)) for q in [0, 1, 5, 50, 95, 99, 100]})
    stats.update(n=len(x), observed_n=int(observed.sum()), below_floor_n=int((p[:, 1] < .05).sum()))
    return p[:, 1], stats


def versions(x):
    for name in ['reference', 'ipw_floor_0.05', 'ipw_unbounded']:
        if name == 'reference': w = inputs.normalized_weights(x).to_numpy()
        else:
            probability = x.observation_probability.clip(lower=.05) if name == 'ipw_floor_0.05' else x.observation_probability
            w = (x.weight / probability).to_numpy(copy=True); w *= len(x) / w.sum()
        yield name, w, {'effective_n': float(w.sum() ** 2 / np.square(w).sum()),
                        **{f'weight_q{q}': float(np.quantile(w, q / 100)) for q in [0, 1, 5, 50, 95, 99, 100]}}


def main():
    start = datetime.now(timezone.utc).isoformat()
    for contract in ['gles_input_contract.json', 'gles_importance_input_contract.json']:
        for p, sha in json.loads((OUT / contract).read_text())['fixed_input_hashes'].items():
            assert inputs.digest(ROOT / p) == sha
    d, _ = inputs.load_data()
    diagnostics, margins, weights = [], [], []
    for year in inputs.ELECTIONS:
        pre = d[d.eligible & d.core_complete & d.year.eq(year)].copy().reset_index(drop=True)
        for response in ['known_four', 'known_turnout']:
            observed = pre.outcome_v4_inclusive.ge(0) if response == 'known_four' else pre.reported_voted | pre.reported_nonvote
            prob, stats = observation_probability(pre, observed, snapshot_design)
            h = {'analysis': 'snapshot', 'year': year, 'response': response}
            diagnostics.append({**h, **stats}); pre['observation_probability'] = prob
            targets = ['nonvote_vs_vote'] if response == 'known_turnout' else ['government_vs_opposition', 'opposition_type', 'four_outcomes']
            for target in targets:
                x = inputs.analytic_sample(pre, target, year=year)
                X, _, names = model.design(x, x)
                for version, w, winfo in versions(x):
                    mm = helpers.fitted(X, x.y.to_numpy(), w)
                    header = {**h, 'target': target, 'weighting': version, 'n': len(x)}
                    margins.extend([{**header, **r} for r in helpers.margins(mm, X, w, names, inputs.CONTRASTS)])
                    weights.append({**header, **winfo})
        print(f'GLES selection {year}: completed', flush=True)
    d = importance.measure.load_data()
    for topics in [[t] for t in importance.measure.TOPICS] + [list(importance.measure.TOPICS)]:
        name = topics[0] if len(topics) == 1 else 'all_three'
        early = [t + '_early_' + v for t in topics for v in ['position', 'importance']]
        pre = d[d.eligible & d.core_complete & d[early].notna().all(axis=1)].copy().reset_index(drop=True)
        selected = importance.measure.analytic_sample(d, topics)
        observed = pre.person_id.isin(selected.person_id)
        assert observed.sum() == len(selected) and pre.person_id.is_unique
        def design(a, b):
            X, Z, _ = importance.design(a, b, topics, block='early')
            return X, Z
        prob, stats = observation_probability(pre, observed, design)
        h = {'analysis': 'importance', 'year': 2013, 'response': 'complete_repeated_and_outcome', 'model_topics': name}
        diagnostics.append({**h, **stats}); pre['observation_probability'] = prob
        x = importance.measure.analytic_sample(pre, topics)
        assert set(x.person_id) == set(selected.person_id)
        X, _, names = importance.design(x, x, topics)
        for version, w, winfo in versions(x):
            mm = helpers.fitted(X, x.y.to_numpy(), w)
            header = {**h, 'target': 'four_outcomes', 'weighting': version, 'n': len(x)}
            margins.extend([{**header, **r} for r in importance.margins(mm, X, w, names, topics)])
            weights.append({**header, **winfo})
        print(f'GLES importance selection {name}: completed', flush=True)
    for name, rows in [('gles_selection_diagnostics', diagnostics), ('gles_selection_margins', margins), ('gles_selection_weights', weights)]:
        pd.DataFrame(rows).to_csv(OUT / (name + '.csv'), index=False)
    report = {'start_utc': start, 'end_utc': datetime.now(timezone.utc).isoformat(),
              'hashes': {str(p.relative_to(ROOT)): inputs.digest(p) for p in [Path(__file__), ROOT / 'planning/gles-selection-specification.md',
                         OUT / 'gles_input_contract.json', OUT / 'gles_importance_input_contract.json',
                         ROOT / 'analysis/67_gles_pre_election_models.py', ROOT / 'analysis/71_gles_importance_change_models.py']},
              'selection_models': len(diagnostics), 'weighted_vote_fits': len(weights),
              'marginal_rows': len(margins), 'microdata_exported': False, 'new_marginal_intervals': False,
              'limitation': 'Correction for observed covariates only, conditional on complete pre-election core'}
    (OUT / 'gles_selection_run.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    with threadpool_limits(limits=1): main()
