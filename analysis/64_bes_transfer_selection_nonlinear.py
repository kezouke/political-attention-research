"""Declared BES temporal, observed-selection and fixed nonlinear checks.

Individual predictions and participant identifiers remain only in local memory.
The locked snapshot functions and input definitions are not modified.
"""
from pathlib import Path
from datetime import datetime, timezone
import importlib.util
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import OneHotEncoder
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('snapshot', ROOT / 'analysis/59_bes_pre_election_models.py')
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)
inputs, helpers, OUT = model.inputs, model.helpers, model.OUT
SEED = 20261106
HGB = {'learning_rate': .05, 'max_iter': 200, 'max_leaf_nodes': 15,
       'min_samples_leaf': 40, 'l2_regularization': 1.,
       'early_stopping': False, 'random_state': SEED}
HGB_BLOCKS = ['baseline', 'plus_priority', 'full']


def prediction(train, test, block, learner):
    X, Z, _ = model.design(train, test, block)
    w = inputs.normalized_weights(train).to_numpy()
    m = helpers.fitted(X, train.y.to_numpy(), w) if learner == 'linear' else HistGradientBoostingClassifier(**HGB).fit(X, train.y.to_numpy(), sample_weight=w)
    assert np.array_equal(m.classes_, np.arange(train.y.nunique()))
    p = m.predict_proba(Z)
    assert np.isfinite(p).all() and np.allclose(p.sum(axis=1), 1)
    return p


def summarize(x, p):
    y, w = x.y.to_numpy(), inputs.normalized_weights(x).to_numpy()
    loss = -np.log(np.clip(p[np.arange(len(x)), y], np.finfo(float).eps, 1))
    stats = helpers.metrics(y, p, w)
    assert np.isclose(stats['log_loss'], np.average(loss, weights=w))
    calibration = []
    for k in range(p.shape[1]):
        bins = np.minimum((p[:, k] * 10).astype(int), 9)
        for b in range(10):
            keep = bins == b
            n = int(keep.sum())
            if n:
                calibration.append({'outcome': k, 'bin': b, 'n': n,
                                    'mean_probability': float(np.average(p[keep, k], weights=w[keep])) if n >= 20 else np.nan,
                                    'observed_fraction': float(np.average(y[keep] == k, weights=w[keep])) if n >= 20 else np.nan,
                                    'small_bin_means_suppressed': n < 20})
    return stats, calibration, loss


def compare(losses, x, pairs, header):
    w = inputs.normalized_weights(x).to_numpy()
    result = []
    for label, old, new in pairs:
        r = model.paired_loss_comparison(losses[old], losses[new], w, x.person_id.to_numpy(), SEED)
        result.append({**header, 'comparison': label, 'baseline': old, 'expanded': new, **r})
    return result


def temporal(d):
    performance, calibration, comparisons, counts = [], [], [], []
    for train_years, test_year in [([2015], 2017), ([2015, 2017], 2019)]:
        for target in inputs.TARGETS:
            full = inputs.analytic_sample(d, target)
            train = full[full.year.isin(train_years)].copy()
            test = full[full.year.eq(test_year)].copy()
            assert train.year.max() < test.year.min()
            unseen = ~test.person_id.isin(train.person_id)
            people = {'all': np.ones(len(test), bool), 'unseen_people': unseen.to_numpy()}
            losses = {k: {} for k in people}
            for subset, mask in people.items():
                x = test.iloc[np.flatnonzero(mask)]
                assert x.person_id.is_unique
                if subset == 'unseen_people':
                    assert not x.person_id.isin(train.person_id).any()
                for k, n in x.y.value_counts().sort_index().items():
                    counts.append({'train_years': '+'.join(map(str, train_years)), 'test_year': test_year,
                                   'target': target, 'subset': subset, 'n': len(x), 'train_n': len(train),
                                   'train_people': train.person_id.nunique(), 'outcome': int(k), 'outcome_n': int(n)})
            for learner, blocks in [('linear', list(inputs.BLOCKS)), ('hgb', HGB_BLOCKS)]:
                for block in blocks:
                    p = prediction(train, test, block, learner)
                    for subset, mask in people.items():
                        x = test.iloc[np.flatnonzero(mask)]
                        stats, cal, loss = summarize(x, p[mask])
                        h = {'train_years': '+'.join(map(str, train_years)), 'test_year': test_year,
                             'target': target, 'subset': subset, 'learner': learner, 'block': block,
                             'n': len(x), 'train_n': len(train)}
                        performance.append({**h, **stats})
                        calibration.extend([{**h, **r} for r in cal])
                        losses[subset][learner + ':' + block] = loss
            pairs = [('linear_' + a + '_to_' + b, 'linear:' + a, 'linear:' + b) for a, b in model.PAIRS]
            pairs += [('hgb_full_vs_hgb_baseline', 'hgb:baseline', 'hgb:full'),
                      ('hgb_trust_increment', 'hgb:plus_priority', 'hgb:full'),
                      ('hgb_full_vs_linear_full', 'linear:full', 'hgb:full')]
            for subset, mask in people.items():
                x = test.iloc[np.flatnonzero(mask)]
                h = {'train_years': '+'.join(map(str, train_years)), 'test_year': test_year,
                     'target': target, 'subset': subset, 'n': len(x)}
                comparisons.extend(compare(losses[subset], x, pairs, h))
            for name, rows in [('bes_temporal_validation', performance), ('bes_temporal_calibration', calibration),
                               ('bes_temporal_comparisons', comparisons), ('bes_temporal_counts', counts)]:
                pd.DataFrame(rows).to_csv(OUT / (name + '.csv'), index=False)
            print(f'Temporal {train_years} -> {test_year}, {target} completed', flush=True)


def nonlinear(d):
    performance, calibration, comparisons = [], [], []
    original = pd.read_csv(OUT / 'bes_model_validation.csv')
    for year in inputs.parties.ELECTIONS:
        for target in inputs.TARGETS:
            x = inputs.analytic_sample(d, target, year=year).reset_index(drop=True)
            losses = {}
            for block in HGB_BLOCKS:
                p = np.full((len(x), x.y.nunique()), np.nan)
                folds = StratifiedKFold(5, shuffle=True, random_state=SEED)
                for a, b in folds.split(np.zeros(len(x)), x.y):
                    p[b] = prediction(x.iloc[a], x.iloc[b], block, 'hgb')
                stats, cal, loss = summarize(x, p)
                h = {'year': year, 'target': target, 'learner': 'hgb', 'block': block, 'n': len(x)}
                performance.append({**h, **stats}); calibration.extend([{**h, **r} for r in cal])
                losses['hgb:' + block] = loss
            # Reconstruct only full linear held-out losses for a paired benchmark.
            stats, _, loss = model.cross_validate(x, 'full', SEED)
            old = original[original.year.eq(year) & original.target.eq(target) & original.block.eq('full')].iloc[0]
            assert np.isclose(stats['log_loss'], old.log_loss, atol=1e-12)
            losses['linear:full'] = loss
            pairs = [('hgb_full_vs_hgb_baseline', 'hgb:baseline', 'hgb:full'),
                     ('hgb_trust_increment', 'hgb:plus_priority', 'hgb:full'),
                     ('hgb_full_vs_linear_full', 'linear:full', 'hgb:full')]
            comparisons.extend(compare(losses, x, pairs, {'year': year, 'target': target, 'n': len(x)}))
            for name, rows in [('bes_nonlinear_validation', performance), ('bes_nonlinear_calibration', calibration),
                               ('bes_nonlinear_comparisons', comparisons)]:
                pd.DataFrame(rows).to_csv(OUT / (name + '.csv'), index=False)
            print(f'Nonlinear {year} {target} completed', flush=True)


def selection_design(train, test):
    X, Z, _ = model.design(train, test, 'full')
    enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False, dtype=float)
    a, b = enc.fit_transform(train[['pre_turnout_intention']]), enc.transform(test[['pre_turnout_intention']])
    def attention(x):
        return np.column_stack([x.political_attention.fillna(.5).to_numpy(), x.political_attention.isna().astype(float).to_numpy()])
    return np.column_stack([X, a, attention(train)]), np.column_stack([Z, b, attention(test)])


def selection(d):
    diagnostics, calibration, margins, weights = [], [], [], []
    for year in inputs.parties.ELECTIONS:
        pre = d[d.eligible & d.core_complete & d.year.eq(year)].copy().reset_index(drop=True)
        assert pre.person_id.is_unique
        for response in ['known_four', 'known_turnout']:
            observed = pre.outcome_v4_inclusive.ge(0) if response == 'known_four' else pre.reported_voted | pre.reported_nonvote
            pre['y'] = observed.astype(int)
            p = np.full((len(pre), 2), np.nan)
            folds = StratifiedKFold(5, shuffle=True, random_state=SEED)
            for a, b in folds.split(np.zeros(len(pre)), pre.y):
                train, test = pre.iloc[a], pre.iloc[b]
                X, Z = selection_design(train, test)
                m = helpers.fitted(X, train.y.to_numpy(), inputs.normalized_weights(train).to_numpy())
                p[b] = m.predict_proba(Z)
            assert np.isfinite(p).all() and np.allclose(p.sum(axis=1), 1)
            stats, cal, _ = summarize(pre, p)
            prob = p[:, 1]
            assert (prob > 0).all() and (prob < 1).all()
            h = {'year': year, 'response': response, 'n': len(pre), 'observed_n': int(observed.sum())}
            diagnostics.append({**h, **stats, **{f'prob_q{q}': float(np.quantile(prob, q / 100)) for q in [0, 1, 5, 25, 50, 75, 95, 99, 100]},
                                'below_floor_n': int((prob < .05).sum())})
            calibration.extend([{**h, **r} for r in cal])
            targets = ['nonvote_vs_vote'] if response == 'known_turnout' else ['government_vs_opposition', 'opposition_type', 'four_outcomes']
            pre['observation_probability'] = prob
            for target in targets:
                x = inputs.analytic_sample(pre, target, year=year)
                assert len(x) > 0 and x.observation_probability.notna().all()
                X, _, names = model.design(x, x)
                for version in ['reference', 'ipw_floor_0.05', 'ipw_unbounded']:
                    probability = x.observation_probability.clip(lower=.05) if version == 'ipw_floor_0.05' else x.observation_probability
                    w = x.weight if version == 'reference' else x.weight / probability
                    w = w.to_numpy() * len(x) / w.sum()
                    m = helpers.fitted(X, x.y.to_numpy(), w)
                    head = {'year': year, 'target': target, 'response': response, 'weighting': version, 'n': len(x)}
                    margins.extend([{**head, **r} for r in helpers.margins(m, X, w, names, inputs.CONTRASTS)])
                    weights.append({**head, 'effective_n': float(w.sum() ** 2 / np.square(w).sum()),
                                    **{f'weight_q{q}': float(np.quantile(w, q / 100)) for q in [0, 1, 5, 50, 95, 99, 100]}})
        for name, rows in [('bes_selection_diagnostics', diagnostics), ('bes_selection_calibration', calibration),
                           ('bes_selection_margins', margins), ('bes_selection_weights', weights)]:
            pd.DataFrame(rows).to_csv(OUT / (name + '.csv'), index=False)
        print(f'Selection sensitivity {year} completed', flush=True)


def main():
    start = datetime.now(timezone.utc).isoformat()
    contract = json.loads((OUT / 'bes_input_contract.json').read_text())
    for p, sha in contract['fixed_input_hashes'].items():
        assert inputs.digest(ROOT / p) == sha
    snapshot = json.loads((OUT / 'bes_models_run.json').read_text())
    assert inputs.digest(ROOT / 'analysis/59_bes_pre_election_models.py') == snapshot['script_sha256']
    d = inputs.load_data()
    selection(d)
    temporal(d)
    nonlinear(d)
    report = {'start_utc': start, 'end_utc': datetime.now(timezone.utc).isoformat(),
              'script_sha256': inputs.digest(Path(__file__)), 'input_contract_sha256': inputs.digest(OUT / 'bes_input_contract.json'),
              'specification_sha256': inputs.digest(ROOT / 'planning/bes-robustness-specification.md'),
              'nonlinear_parameters': HGB, 'hyperparameter_search': False,
              'heldout_loss_bootstrap_draws': 2000, 'validation_intervals_refit_training': False,
              'selection_estimation': 'Five-fold out-of-fold probabilities from pre-election complete core sample',
              'selection_margins_have_intervals': False, 'microdata_exported': False,
              'remaining': ['Within-person change analysis', 'Constituency party availability in 2019']}
    (OUT / 'bes_robustness_run.json').write_text(json.dumps(report, indent=2) + '\n')
    print('BES transfer, selection and nonlinear checks completed.', flush=True)


if __name__ == '__main__':
    with threadpool_limits(limits=1):
        main()
