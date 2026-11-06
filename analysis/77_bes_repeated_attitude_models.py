"""Repeated BES attitudes conditional on initial levels and political choice."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
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

repeated = module('repeated', '76_bes_change_inputs.py')
shared = module('shared', '59_bes_pre_election_models.py')
inputs, helpers, OUT = repeated.inputs, shared.helpers, repeated.OUT
BLOCKS = {'early': [], **{k: v for k, v in inputs.BLOCKS.items() if k != 'baseline'}}
PAIRS = [('early', 'economy_government'), ('economy_government', 'plus_priority'),
         ('plus_priority', 'full'), ('early', 'full'), ('without_economy', 'full'),
         ('without_government', 'full'), ('without_priority', 'full'), ('without_trust', 'full')]


def design(train, test, block='full', intention='early', positions=False):
    numeric = inputs.CONTROLS + ['early_' + v for v in inputs.CORE] + BLOCKS[block]
    if positions: numeric += repeated.POSITION_VARS + ['early_' + v for v in repeated.POSITION_VARS]
    categories = [v for v in inputs.CATEGORICAL if v != 'pre_intention_group']
    if intention != 'none': categories += ['late_pre_intention_group' if intention == 'late' else 'pre_intention_group']
    e = OneHotEncoder(handle_unknown='ignore', sparse_output=False, dtype=float)
    X = np.column_stack([train[numeric].to_numpy(float), e.fit_transform(train[categories])])
    Z = np.column_stack([test[numeric].to_numpy(float), e.transform(test[categories])])
    assert np.isfinite(X).all() and np.isfinite(Z).all()
    return X, Z, numeric + e.get_feature_names_out(categories).tolist()


def bootstrap(x, X, names, seed):
    w, y = inputs.normalized_weights(x).to_numpy(), x.y.to_numpy()
    def one(child):
        rng = np.random.default_rng(child)
        counts = np.bincount(rng.integers(0, len(x), len(x)), minlength=len(x))
        ww = w * counts; keep = ww > 0; ww = ww[keep] * len(x) / ww.sum()
        m = helpers.fitted(X[keep], y[keep], ww)
        assert np.array_equal(m.classes_, np.unique(y))
        return helpers.margins(m, X[keep], ww, names, inputs.CONTRASTS)
    rows = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i, result in enumerate(pool.map(one, np.random.SeedSequence(seed).spawn(1000)), 1):
            rows.extend(result)
            if i % 100 == 0: print(f'Repeated BES bootstrap {i}/1000', flush=True)
    return pd.DataFrame(rows).groupby(['variable', 'outcome']).probability_difference.agg(
        ci_low=lambda s: s.quantile(.025), ci_high=lambda s: s.quantile(.975),
        bootstrap_sd='std', successful_draws='count').reset_index()


def validate(x, block):
    p = np.full((len(x), x.y.nunique()), np.nan)
    for a, b in StratifiedKFold(5, shuffle=True, random_state=20261106).split(np.zeros(len(x)), x.y):
        train, test = x.iloc[a], x.iloc[b]
        X, Z, _ = design(train, test, block)
        m = helpers.fitted(X, train.y.to_numpy(), inputs.normalized_weights(train).to_numpy())
        p[b] = m.predict_proba(Z)
    assert np.isfinite(p).all() and np.allclose(p.sum(axis=1), 1)
    loss = -np.log(np.clip(p[np.arange(len(x)), x.y.to_numpy()], np.finfo(float).eps, 1))
    return helpers.metrics(x.y.to_numpy(), p, inputs.normalized_weights(x).to_numpy()), loss


def fit_scenario(x, scenario, alternative):
    q = x.copy()
    if alternative and scenario == 'broad_priority':
        q['economic_priority'] = q.economic_priority_broad
        q['early_economic_priority'] = q.early_economic_priority_broad
    if alternative and scenario == 'late_weight': q['weight'] = q.late_weight
    intention = ('none' if scenario == 'without_early_intention' else 'late') if alternative and scenario in ['without_early_intention', 'late_intention'] else 'early'
    X, _, names = design(q, q, intention=intention, positions=alternative and scenario == 'positions')
    w = np.ones(len(q)) if alternative and scenario == 'unweighted' else inputs.normalized_weights(q).to_numpy()
    C = .1 if alternative and scenario == 'C_0.1' else 10. if alternative and scenario == 'C_10' else 1.
    m = helpers.fitted(X, q.y.to_numpy(), w, C)
    return helpers.margins(m, X, w, names, inputs.CONTRASTS)


def main():
    start = datetime.now(timezone.utc).isoformat()
    contract = json.loads((OUT / 'bes_change_input_contract.json').read_text())
    for filename in ['bes_input_contract.json', 'bes_change_input_contract.json']:
        for p, sha in json.loads((OUT / filename).read_text())['fixed_input_hashes'].items(): assert inputs.digest(ROOT / p) == sha
    d = repeated.load_data()
    points, validation, incremental, sensitivity, status, transitions = [], [], [], [], [], []
    for yi, year in enumerate(repeated.EARLY):
        for ti, target in enumerate(inputs.TARGETS):
            x = repeated.analytic_sample(d, target, year).reset_index(drop=True)
            assert x.person_id.is_unique and len(x) == contract['sample_totals'][f'{year}:{target}']
            X, _, names = design(x, x)
            w = inputs.normalized_weights(x).to_numpy()
            mm = helpers.fitted(X, x.y.to_numpy(), w)
            point = pd.DataFrame(helpers.margins(mm, X, w, names, inputs.CONTRASTS))
            print(f'Repeated BES {year} {target}, n={len(x)}', flush=True)
            ci = bootstrap(x, X, names, 20261106 + yi * 10 + ti)
            point = point.merge(ci, on=['variable', 'outcome'], validate='one_to_one')
            point['year'] = year; point['target'] = target; point['n'] = len(x)
            points.extend(point.to_dict('records'))
            pd.DataFrame(points).to_csv(OUT / 'bes_change_model_margins.csv', index=False)
            losses, cache = {}, {}
            for block, fields in BLOCKS.items():
                key = tuple(fields)
                if key not in cache: cache[key] = validate(x, block)
                stats, loss = cache[key]
                validation.append({'year': year, 'target': target, 'block': block, 'n': len(x), **stats})
                losses[block] = loss
            for a, b in PAIRS:
                incremental.append({'year': year, 'target': target, 'baseline_block': a, 'expanded_block': b,
                                    **shared.paired_loss_comparison(losses[a], losses[b], w, x.person_id.to_numpy(), 20261106)})
            for scenario in ['C_0.1', 'C_10', 'unweighted', 'late_weight', 'without_early_intention',
                             'late_intention', 'age_consistent', 'broad_priority', 'positions', 'v4_strict']:
                z = x.copy()
                if scenario == 'age_consistent': z = z[~z.age_change_flag].copy()
                if scenario == 'positions': z = z[z[repeated.POSITION_VARS + ['early_' + v for v in repeated.POSITION_VARS]].notna().all(axis=1)].copy()
                valid = len(z) > 0 and set(z.y) == set(x.y) and z.y.value_counts().min() >= 5
                status.append({'year': year, 'target': target, 'scenario': scenario, 'n': len(z), 'estimable': valid})
                if not valid: continue
                for fit in ['reference_same_subset', 'alternative']:
                    q = z
                    if scenario == 'v4_strict' and fit == 'alternative':
                        q = repeated.analytic_sample(d, target, year, outcome='outcome_v4_strict').reset_index(drop=True)
                        assert q.person_id.equals(x.person_id) and set(q.y) == set(x.y)
                    rows = fit_scenario(q, scenario, fit == 'alternative')
                    sensitivity.extend([{'year': year, 'target': target, 'scenario': scenario, 'fit': fit, 'n': len(q), **r} for r in rows])
            if target == 'four_outcomes':
                for a in [0, 1]:
                    for b in [0, 1]:
                        mask = x.early_economic_priority.eq(a) & x.economic_priority.eq(b)
                        transitions.append({'year': year, 'early_priority': a, 'late_priority': b, 'n': len(x),
                                            'cell_n': int(mask.sum()), 'weight_share': float(w[mask].sum() / w.sum())})
            for name, rows in [('bes_change_model_validation', validation), ('bes_change_incremental_validation', incremental),
                               ('bes_change_sensitivity', sensitivity), ('bes_change_sensitivity_status', status), ('bes_change_priority_transitions', transitions)]:
                pd.DataFrame(rows).to_csv(OUT / (name + '.csv'), index=False)
            print(f'Repeated BES {year} {target}: complete', flush=True)
    report = {'start_utc': start, 'end_utc': datetime.now(timezone.utc).isoformat(),
              'hashes': {str(p.relative_to(ROOT)): inputs.digest(p) for p in [Path(__file__), OUT / 'bes_change_input_contract.json',
                         ROOT / 'analysis/59_bes_pre_election_models.py', ROOT / 'analysis/51_eurobarometer_models.py']},
              'bootstrap_draws_per_estimate': 1000, 'heldout_loss_draws': 2000, 'training_refitted_for_validation_intervals': False,
              'early_waves': repeated.EARLY, 'microdata_exported': False,
              'interpretation': 'Late attitudes conditional on earlier levels and initial preferences; no causal claim'}
    (OUT / 'bes_change_models_run.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Repeated BES models completed.', flush=True)


if __name__ == '__main__':
    with threadpool_limits(limits=1): main()
