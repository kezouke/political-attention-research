"""Locked importance-change associations, preserving position interactions."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import importlib.util
import json
import numpy as np
import pandas as pd
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import StratifiedKFold
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]


def module(name, file):
    s = importlib.util.spec_from_file_location(name, ROOT / 'analysis' / file)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


measure = module('measure', '70_gles_importance_change_inputs.py')
inputs, OUT = measure.inputs, measure.OUT
shared = module('shared', '59_bes_pre_election_models.py')
helpers = shared.helpers
BLOCKS = ['early', 'late_position', 'late_importance']


def design(train, test, topics, block='late_importance', intention='early', interactions=True, midtrust=False):
    numeric = inputs.CONTROLS + ['economy_bad']
    for t in topics:
        numeric += [t + '_early_position', t + '_early_importance']
        if interactions: numeric += [t + '_early_interaction']
        if block != 'early': numeric += [t + '_late_position']
        if block == 'late_importance':
            numeric += [t + '_late_importance']
            if interactions: numeric += [t + '_late_interaction']
    if midtrust: numeric += ['government_distrust', 'politicians_dishonest', 'parties_only_votes']
    categorical = [v for v in inputs.CATEGORICAL if v != 'pre_intention_group']
    if intention != 'none': categorical += ['late_pre_intention_group' if intention == 'late' else 'pre_intention_group']
    enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False, dtype=float)
    X = np.column_stack([train[numeric].to_numpy(float), enc.fit_transform(train[categorical])])
    Z = np.column_stack([test[numeric].to_numpy(float), enc.transform(test[categorical])])
    assert np.isfinite(X).all() and np.isfinite(Z).all()
    return X, Z, numeric + enc.get_feature_names_out(categorical).tolist()


def margins(m, X, w, names, topics):
    rows = []
    for t in topics:
        p = names.index(t + '_late_position')
        s = names.index(t + '_late_importance')
        interaction = names.index(t + '_late_interaction') if t + '_late_interaction' in names else None
        for scenario, position in [('observed', None), ('low_position', 1/6), ('high_position', 5/6)]:
            probabilities = []
            for value in [.5, .75]:
                xx = X.copy(); xx[:, s] = value
                if position is not None: xx[:, p] = position
                if interaction is not None: xx[:, interaction] = value * (xx[:, p] - .5)
                probabilities.append(np.average(m.predict_proba(xx), weights=w, axis=0))
            low, high = probabilities
            assert np.isclose((high - low).sum(), 0)
            for k in range(4):
                rows.append({'topic': t, 'position_scenario': scenario, 'outcome': k,
                             'importance_low': .5, 'importance_high': .75,
                             'probability_at_low': float(low[k]), 'probability_at_high': float(high[k]),
                             'probability_difference': float(high[k] - low[k])})
    return rows


def bootstrap(x, X, names, topics, seed):
    w = inputs.normalized_weights(x).to_numpy(); y = x.y.to_numpy()
    seeds = np.random.SeedSequence(seed).spawn(1000)
    def one(child):
        rng = np.random.default_rng(child)
        count = np.bincount(rng.integers(0, len(x), len(x)), minlength=len(x))
        ww = w * count; keep = ww > 0; ww = ww[keep] * len(x) / ww.sum()
        m = helpers.fitted(X[keep], y[keep], ww)
        assert np.array_equal(m.classes_, np.arange(4))
        return margins(m, X[keep], ww, names, topics)
    rows = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i, result in enumerate(pool.map(one, seeds), 1):
            rows.extend(result)
            if i % 100 == 0: print(f'Importance bootstrap {i}/1000', flush=True)
    frame = pd.DataFrame(rows)
    return frame.groupby(['topic', 'position_scenario', 'outcome']).probability_difference.agg(
        ci_low=lambda s: s.quantile(.025), ci_high=lambda s: s.quantile(.975),
        successful_draws='count', bootstrap_sd='std').reset_index()


def validate(x, topics, block):
    p = np.full((len(x), 4), np.nan)
    folds = StratifiedKFold(5, shuffle=True, random_state=20261106)
    for a, b in folds.split(np.zeros(len(x)), x.y):
        train, test = x.iloc[a], x.iloc[b]
        X, Z, _ = design(train, test, topics, block)
        m = helpers.fitted(X, train.y.to_numpy(), inputs.normalized_weights(train).to_numpy())
        p[b] = m.predict_proba(Z)
    assert np.isfinite(p).all() and np.allclose(p.sum(axis=1), 1)
    y, w = x.y.to_numpy(), inputs.normalized_weights(x).to_numpy()
    loss = -np.log(np.clip(p[np.arange(len(x)), y], np.finfo(float).eps, 1))
    return helpers.metrics(y, p, w), loss


def main():
    started = datetime.now(timezone.utc).isoformat()
    config = json.loads((OUT / 'gles_importance_input_contract.json').read_text())
    parent = json.loads((OUT / 'gles_input_contract.json').read_text())
    for contract in [config, parent]:
        for p, sha in contract['fixed_input_hashes'].items(): assert inputs.digest(ROOT / p) == sha
    d = measure.load_data()
    points, sensitivity, validation, incremental, transitions, simultaneous = [], [], [], [], [], []
    sets = [[t] for t in measure.TOPICS] + [list(measure.TOPICS)]
    for index, topics in enumerate(sets):
        name = topics[0] if len(topics) == 1 else 'all_three'
        x = measure.analytic_sample(d, topics).reset_index(drop=True)
        assert len(x) == config['sample_totals'][name] and x.person_id.is_unique
        X, _, names = design(x, x, topics)
        w, y = inputs.normalized_weights(x).to_numpy(), x.y.to_numpy()
        m = helpers.fitted(X, y, w)
        point = pd.DataFrame(margins(m, X, w, names, topics))
        print(f'Importance {name}, n={len(x)}', flush=True)
        ci = bootstrap(x, X, names, topics, 20261106 + index)
        point = point.merge(ci, on=['topic', 'position_scenario', 'outcome'], validate='one_to_one')
        point['model_topics'] = name; point['n'] = len(x)
        points.extend(point.to_dict('records'))
        pd.DataFrame(points).to_csv(OUT / 'gles_importance_model_margins.csv', index=False)
        losses = {}
        for block in BLOCKS:
            stats, loss = validate(x, topics, block)
            validation.append({'model_topics': name, 'n': len(x), 'block': block, **stats}); losses[block] = loss
        for old, new in [('early', 'late_position'), ('late_position', 'late_importance'), ('early', 'late_importance')]:
            result = shared.paired_loss_comparison(losses[old], losses[new], w, x.person_id.to_numpy(), 20261106)
            incremental.append({'model_topics': name, 'baseline_block': old, 'expanded_block': new, 'n': len(x), **result})
        scenarios = [('C_0.1', .1, False, 'early', True, False), ('C_10', 10., False, 'early', True, False),
                     ('unweighted', 1., True, 'early', True, False), ('without_intention', 1., False, 'none', True, False),
                     ('late_intention', 1., False, 'late', True, False), ('without_interactions', 1., False, 'early', False, False),
                     ('midwave_trust', 1., False, 'early', True, True)]
        for scenario, C, unweighted, intention, interactions, midtrust in scenarios:
            XX, _, nn = design(x, x, topics, intention=intention, interactions=interactions, midtrust=midtrust)
            ww = np.ones(len(x)) if unweighted else w
            mm = helpers.fitted(XX, y, ww, C)
            sensitivity.extend([{'model_topics': name, 'scenario': scenario, 'n': len(x), **r}
                                for r in margins(mm, XX, ww, nn, topics)])
        strict = measure.analytic_sample(d, topics, outcome='outcome_v4_strict').reset_index(drop=True)
        assert strict.person_id.equals(x.person_id)
        mm = helpers.fitted(X, strict.y.to_numpy(), w)
        sensitivity.extend([{'model_topics': name, 'scenario': 'v4_strict', 'n': len(x), **r}
                            for r in margins(mm, X, w, names, topics)])
        for t in topics:
            # These are answer transitions, not change inferred from a vote model.
            pos = np.sign(x[t + '_change_position']).astype(int)
            imp = np.sign(x[t + '_change_importance']).astype(int)
            for a in [-1, 0, 1]:
                for b in [-1, 0, 1]:
                    mask = pos.eq(a) & imp.eq(b)
                    transitions.append({'model_topics': name, 'topic': t, 'position_change_direction': a,
                                        'importance_change_direction': b, 'n': len(x), 'cell_n': int(mask.sum()),
                                        'weight_share': float(w[mask].sum() / w.sum())})
        if len(topics) == 3:
            changed = x[[t + '_change_importance' for t in topics]].gt(0).sum(axis=1)
            for k in range(4):
                mask = changed.eq(k)
                simultaneous.append({'topics_increasing': k, 'n': len(x), 'cell_n': int(mask.sum()),
                                     'weight_share': float(w[mask].sum() / w.sum())})
        for filename, rows in [('gles_importance_sensitivity', sensitivity), ('gles_importance_validation', validation),
                               ('gles_importance_incremental_validation', incremental), ('gles_importance_transitions', transitions),
                               ('gles_importance_simultaneous', simultaneous)]:
            pd.DataFrame(rows).to_csv(OUT / (filename + '.csv'), index=False)
        print(f'Importance {name}: complete', flush=True)
    run = {'start_utc': started, 'end_utc': datetime.now(timezone.utc).isoformat(),
           'script_sha256': inputs.digest(Path(__file__)), 'contract_sha256': inputs.digest(OUT / 'gles_importance_input_contract.json'),
           'bootstrap_draws_per_estimate': 1000, 'heldout_loss_bootstrap_draws': 2000,
           'validation_intervals_refit_training': False, 'individual_predictions_exported': False,
           'interpretation': 'Association of later importance conditional on earlier importance and both positions; no causal claim',
           'future_work': ['Designed 2009/2013 linkage', 'Observed-selection sensitivity', 'National survey comparisons']}
    (OUT / 'gles_importance_models_run.json').write_text(json.dumps(run, indent=2) + '\n')
    print('Importance-change models completed.', flush=True)


if __name__ == '__main__':
    with threadpool_limits(limits=1): main()
