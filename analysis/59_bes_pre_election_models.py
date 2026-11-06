"""First locked BES snapshot models; export only aggregate results.

These models condition on earlier political intention. They do not identify a
causal response to the 2008 crisis. Temporal transfer, selection adjustment and
within-person changes are subsequent declared analyses, not silently omitted.
"""
from pathlib import Path
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import importlib.util
import json
import platform
import numpy as np
import pandas as pd
import sklearn
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import OneHotEncoder
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'analysis' / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


inputs = module('bes_inputs', '58_bes_model_inputs.py')
helpers = module('eb_helpers', '51_eurobarometer_models.py')
OUT = inputs.OUT
PAIRS = [('baseline', 'economy_government'), ('economy_government', 'plus_priority'),
         ('plus_priority', 'full'), ('baseline', 'full'), ('without_economy', 'full'),
         ('without_government', 'full'), ('without_priority', 'full'), ('without_trust', 'full')]


def design(train, test, block='full', extra=(), drop=(), exact_intention=False):
    numeric = [v for v in inputs.CONTROLS + inputs.BLOCKS[block] if v not in drop] + list(extra)
    categories = [v for v in inputs.CATEGORICAL if v not in drop]
    if exact_intention:
        categories = ['pre_intention' if v == 'pre_intention_group' else v for v in categories]
    encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False, dtype=float)
    a, b = encoder.fit_transform(train[categories]), encoder.transform(test[categories])
    X = np.column_stack([train[numeric].to_numpy(float), a])
    Z = np.column_stack([test[numeric].to_numpy(float), b])
    assert np.isfinite(X).all() and np.isfinite(Z).all()
    return X, Z, numeric + encoder.get_feature_names_out(categories).tolist()


def fit_margins(x, C=1., unweighted=False, extra=(), drop=(), exact_intention=False):
    X, _, names = design(x, x, extra=extra, drop=drop, exact_intention=exact_intention)
    w = np.ones(len(x)) if unweighted else inputs.normalized_weights(x).to_numpy()
    m = helpers.fitted(X, x.y.to_numpy(), w, C)
    return helpers.margins(m, X, w, names, inputs.CONTRASTS)


def bootstrap_margins(x, X, names, draws, seed):
    assert x.person_id.is_unique and x.year.nunique() == 1
    y = x.y.to_numpy()
    w = inputs.normalized_weights(x).to_numpy()
    seeds = np.random.SeedSequence(seed).spawn(draws)

    def one(item):
        i, child = item
        rng = np.random.default_rng(child)
        count = np.bincount(rng.integers(0, len(x), len(x)), minlength=len(x))
        ww = w * count
        keep = ww > 0
        ww = ww[keep] * len(x) / ww.sum()
        m = helpers.fitted(X[keep], y[keep], ww)
        assert np.array_equal(m.classes_, np.unique(y))
        return [{**r, 'draw': i} for r in helpers.margins(m, X[keep], ww, names, inputs.CONTRASTS)]

    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i, rows in enumerate(pool.map(one, enumerate(seeds)), 1):
            results.extend(rows)
            if i % 100 == 0:
                print(f'bootstrap {i}/{draws}', flush=True)
    b = pd.DataFrame(results)
    ci = b.groupby(['variable', 'outcome']).probability_difference.agg(
        ci_low=lambda s: s.quantile(.025), ci_high=lambda s: s.quantile(.975),
        bootstrap_sd='std', successful_draws='count').reset_index()
    assert ci.successful_draws.eq(draws).all()
    return ci


def cross_validate(x, block, seed):
    assert x.person_id.is_unique and x.y.value_counts().min() >= 5
    p = np.full((len(x), x.y.nunique()), np.nan)
    folds = StratifiedKFold(5, shuffle=True, random_state=seed)
    for a, b in folds.split(np.zeros(len(x)), x.y):
        train, test = x.iloc[a], x.iloc[b]
        X, Z, _ = design(train, test, block)
        m = helpers.fitted(X, train.y.to_numpy(), inputs.normalized_weights(train).to_numpy())
        assert np.array_equal(m.classes_, np.arange(p.shape[1]))
        p[b] = m.predict_proba(Z)
    assert np.isfinite(p).all() and np.allclose(p.sum(axis=1), 1)
    y, w = x.y.to_numpy(), inputs.normalized_weights(x).to_numpy()
    loss = -np.log(np.clip(p[np.arange(len(x)), y], np.finfo(float).eps, 1))
    result = helpers.metrics(y, p, w)
    assert np.isclose(result['log_loss'], np.average(loss, weights=w))
    calibration = []
    for k in range(p.shape[1]):
        bins = np.minimum((p[:, k] * 10).astype(int), 9)
        for b in range(10):
            mask = bins == b
            n = int(mask.sum())
            if not n:
                continue
            # Suppress unstable small-bin means; counts remain aggregate.
            calibration.append({'outcome': k, 'bin': b, 'n': n,
                                'mean_probability': float(np.average(p[mask, k], weights=w[mask])) if n >= 20 else np.nan,
                                'observed_fraction': float(np.average(y[mask] == k, weights=w[mask])) if n >= 20 else np.nan,
                                'small_bin_means_suppressed': n < 20})
    return result, calibration, loss


def paired_loss_comparison(old, new, w, people, seed, draws=2000):
    # Cluster by participant if several observations are supplied. Current
    # within-year tests have one answer per participant. No IDs are exported.
    _, code = np.unique(people, return_inverse=True)
    nc = code.max() + 1
    a = np.bincount(code, weights=w * old, minlength=nc)
    b = np.bincount(code, weights=w * new, minlength=nc)
    ww = np.bincount(code, weights=w, minlength=nc)
    rng = np.random.default_rng(seed)
    absolute, relative = [], []
    for start in range(0, draws, 20):
        take = rng.integers(0, nc, (min(20, draws - start), nc))
        aa, bb = a[take].sum(axis=1), b[take].sum(axis=1)
        absolute.extend((aa - bb) / ww[take].sum(axis=1))
        relative.extend(100 * (aa - bb) / aa)
    point = float(100 * (a.sum() - b.sum()) / a.sum())
    low, high = np.quantile(relative, [.025, .975])
    return {'log_loss_reduction': float((a.sum() - b.sum()) / ww.sum()),
            'ci_low': float(np.quantile(absolute, .025)), 'ci_high': float(np.quantile(absolute, .975)),
            'relative_improvement_percent': point, 'relative_ci_low': float(low), 'relative_ci_high': float(high),
            'passes_1pct_and_positive_interval': bool(point >= 1 and low > 0),
            'bootstrap_draws': draws, 'participant_clusters': int(nc),
            'uncertainty_scope': 'Participant resampling of fixed held-out losses; training folds not refitted'}


def self_test():
    cw = pd.read_csv(OUT / 'bes_party_crosswalk.csv')
    party = pd.Series([3, 6, 7, 7, 9, np.nan])
    turnout = pd.Series([1, 1, 1, 1, 1, 0])
    region = pd.Series([1, 1, 1, 11, 1, 1])
    classify = inputs.parties.classify
    assert classify(party, turnout, region, 2015, cw).tolist() == [0, 2, 1, -1, -1, 3]
    assert classify(party, turnout, region, 2017, cw).tolist() == [1, 2, 1, -1, -1, 3]
    sample = pd.DataFrame({'eligible': [True, True], 'core_complete': [True, True], 'year': [2015, 2015],
                           'outcome_v4_inclusive': [-1, 3], 'reported_voted': [True, False], 'reported_nonvote': [False, True]})
    assert inputs.analytic_sample(sample, 'nonvote_vs_vote').y.tolist() == [0, 1]
    assert inputs.analytic_sample(sample, 'four_outcomes').y.tolist() == [3]
    old = np.array([1., 2., .3, 1.4])
    r = paired_loss_comparison(old, old * .8, np.array([1., 2., 3., 4.]), np.array([1, 1, 2, 3]), 19, draws=100)
    assert np.allclose([r['relative_improvement_percent'], r['relative_ci_low'], r['relative_ci_high']], 20)
    # Weighted multiplicities must reproduce a physically duplicated bootstrap.
    rng = np.random.default_rng(713)
    X = rng.normal(size=(300, 4)); y = rng.integers(0, 2, 300); w = rng.uniform(.5, 2, 300)
    idx = rng.integers(0, 300, 300); counts = np.bincount(idx, minlength=300)
    aa = helpers.fitted(X[idx], y[idx], w[idx] * 300 / w[idx].sum())
    keep = counts > 0; ww = w * counts
    bb = helpers.fitted(X[keep], y[keep], ww[keep] * 300 / ww.sum())
    assert np.allclose(aa.predict_proba(X), bb.predict_proba(X), atol=1e-6)
    print('Synthetic checks passed: coalition changes, unknown vote/abstention, paired losses and bootstrap multiplicities.', flush=True)


def main():
    start = datetime.now(timezone.utc).isoformat()
    config = json.loads((OUT / 'bes_input_contract.json').read_text())
    for path, sha in config['fixed_input_hashes'].items():
        assert inputs.digest(ROOT / path) == sha, ('Locked input changed', path)
    assert config['main_regularization_C'] == 1.
    d = inputs.load_data()
    point_rows, coefficients, validation, calibration, incremental, sensitivity = [], [], [], [], [], []
    for yi, year in enumerate(inputs.parties.ELECTIONS):
        for ti, target in enumerate(inputs.TARGETS):
            x = inputs.analytic_sample(d, target, year=year).reset_index(drop=True)
            assert len(x) == config['sample_totals'][f'{year}:{target}']
            assert x.person_id.is_unique
            print(f'{year} {target}: n={len(x)}', flush=True)
            X, _, names = design(x, x)
            w, y = inputs.normalized_weights(x).to_numpy(), x.y.to_numpy()
            m = helpers.fitted(X, y, w)
            point = pd.DataFrame(helpers.margins(m, X, w, names, inputs.CONTRASTS))
            ci = bootstrap_margins(x, X, names, config['bootstrap_respondent_draws'], config['seed'] + 10 * yi + ti)
            point = point.merge(ci, on=['variable', 'outcome'], validate='one_to_one')
            point['year'] = year; point['target'] = target; point['n'] = len(x)
            point_rows.extend(point.to_dict('records'))
            for k, beta in enumerate(m.coef_):
                for feature, value in zip(names, beta):
                    coefficients.append({'year': year, 'target': target,
                                         'coefficient_class': int(m.classes_[k] if len(m.classes_) > 2 else 1),
                                         'feature': feature, 'coefficient': float(value), 'intercept': float(m.intercept_[k])})
            pd.DataFrame(point_rows).to_csv(OUT / 'bes_model_margins.csv', index=False)
            pd.DataFrame(coefficients).to_csv(OUT / 'bes_model_coefficients.csv', index=False)
            losses = {}
            for block in inputs.BLOCKS:
                result, cal, loss = cross_validate(x, block, config['seed'])
                header = {'year': year, 'target': target, 'block': block, 'validation': 'within_year', 'n': len(x)}
                validation.append({**header, **result}); calibration.extend([{**header, **r} for r in cal])
                losses[block] = loss
            assert np.allclose(losses['plus_priority'], losses['without_trust'])
            for old, new in PAIRS:
                r = paired_loss_comparison(losses[old], losses[new], w, x.person_id.to_numpy(), config['seed'] + ti + yi * 10)
                incremental.append({'year': year, 'target': target, 'baseline_block': old,
                                    'expanded_block': new, 'validation': 'within_year', **r})
            print(f'{year} {target}: within-year validation complete', flush=True)
            # Point sensitivities; these never select the primary model.
            specs = [('C_0.1', .1, False, (), (), False), ('C_10', 10., False, (), (), False),
                     ('unweighted', 1., True, (), (), False),
                     ('without_pre_intention', 1., False, (), ('pre_intention_group',), False),
                     ('without_party_identity', 1., False, (), ('party_identity', 'party_identity_strength'), False),
                     ('without_both_prior_preferences', 1., False, (), ('pre_intention_group', 'party_identity', 'party_identity_strength'), False),
                     ('exact_party_intention', 1., False, (), (), True),
                     ('add_household_economy', 1., False, ('household_bad',), (), False),
                     ('add_policy_positions', 1., False, ('redistSelf', 'EUIntegrationSelf'), (), False),
                     ('add_immigration_economic_evaluation', 1., False, ('immigration_economy_bad',), (), False)]
            for label, C, unweighted, extra, drop, exact in specs:
                z = x.loc[x[list(extra)].notna().all(axis=1)].copy() if extra else x
                for kind in ['reference_same_subset', 'alternative']:
                    rows = fit_margins(z, C=C if kind == 'alternative' else 1.,
                                       unweighted=unweighted and kind == 'alternative',
                                       extra=extra if kind == 'alternative' else (),
                                       drop=drop if kind == 'alternative' else (),
                                       exact_intention=exact and kind == 'alternative')
                    sensitivity.extend([{'year': year, 'target': target, 'scenario': label, 'fit': kind, 'n': len(z), **r} for r in rows])
            for label in ['economic_priority_broad', 'exclude_age_flags']:
                z = x.loc[~x.age_change_flag].copy() if label == 'exclude_age_flags' else x.copy()
                for kind in ['reference_same_subset', 'alternative']:
                    q = z.copy()
                    if label == 'economic_priority_broad' and kind == 'alternative':
                        q['economic_priority'] = q.economic_priority_broad
                    sensitivity.extend([{'year': year, 'target': target, 'scenario': label, 'fit': kind, 'n': len(q), **r}
                                        for r in fit_margins(q)])
            for version, rule in [('3', 'inclusive'), ('4', 'strict'), ('3', 'strict')]:
                alt = inputs.analytic_sample(d, target, outcome=f'outcome_v{version}_{rule}', year=year)
                assert x.person_id.to_list() == alt.person_id.to_list() and x.y.to_list() == alt.y.to_list()
            for name, rows in [('bes_model_validation', validation), ('bes_model_calibration', calibration),
                               ('bes_model_incremental_validation', incremental), ('bes_model_sensitivity', sensitivity)]:
                pd.DataFrame(rows).to_csv(OUT / (name + '.csv'), index=False)
    run = {'start_utc': start, 'end_utc': datetime.now(timezone.utc).isoformat(),
           'input_lock_commit': '7e1eaa1', 'contract_sha256': inputs.digest(OUT / 'bes_input_contract.json'),
           'script_sha256': inputs.digest(Path(__file__).resolve()), 'python': platform.python_version(),
           'numpy': np.__version__, 'pandas': pd.__version__, 'sklearn': sklearn.__version__,
           'bootstrap_draws_per_marginal_estimate': config['bootstrap_respondent_draws'],
           'heldout_loss_bootstrap_draws': 2000, 'validation_intervals_refit_training': False,
           'classification_variants_identical_on_primary_samples': True,
           'microdata_exported': False, 'interpretation': 'Pre-election conditional associations in selected online-panel respondents',
           'remaining_declared_analyses': ['Temporal transfer', 'Selection adjustment', 'Within-person changes', 'Nonlinear benchmark']}
    (OUT / 'bes_models_run.json').write_text(json.dumps(run, indent=2) + '\n')
    print('All locked BES snapshot fits and within-year checks completed.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--self-test', action='store_true'); args = parser.parse_args()
    with threadpool_limits(limits=1):
        if args.self_test:
            self_test()
        else:
            main()
