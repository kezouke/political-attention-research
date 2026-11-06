"""Locked German pre-election associations, validation and sensitivities."""
from pathlib import Path
from datetime import datetime, timezone
import importlib.util
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]


def module(name, file):
    s = importlib.util.spec_from_file_location(name, ROOT / 'analysis' / file)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


inputs = module('gles_inputs', '66_gles_model_inputs.py')
model = module('shared_bes', '59_bes_pre_election_models.py')
model.inputs = inputs
OUT, helpers = inputs.OUT, model.helpers


def nested_validation(x, block):
    """Fixed secondary C grid, chosen on inner folds, never outer outcomes."""
    p = np.full((len(x), x.y.nunique()), np.nan)
    choices = []
    outer = StratifiedKFold(5, shuffle=True, random_state=20261106)
    for fold, (a, b) in enumerate(outer.split(np.zeros(len(x)), x.y)):
        train, test = x.iloc[a], x.iloc[b]
        inner = list(StratifiedKFold(3, shuffle=True, random_state=20261106 + fold).split(np.zeros(len(train)), train.y))
        scores = []
        for C in [.1, 1., 10.]:
            q = np.full((len(train), x.y.nunique()), np.nan)
            for c, e in inner:
                fit, val = train.iloc[c], train.iloc[e]
                X, Z, _ = model.design(fit, val, block)
                m = helpers.fitted(X, fit.y.to_numpy(), inputs.normalized_weights(fit).to_numpy(), C)
                q[e] = m.predict_proba(Z)
            scores.append(helpers.metrics(train.y.to_numpy(), q, inputs.normalized_weights(train).to_numpy())['log_loss'])
        best = [.1, 1., 10.][int(np.argmin(scores))]
        choices.extend([{'fold': fold, 'C': C, 'inner_log_loss': loss, 'chosen': C == best}
                        for C, loss in zip([.1, 1., 10.], scores)])
        X, Z, _ = model.design(train, test, block)
        m = helpers.fitted(X, train.y.to_numpy(), inputs.normalized_weights(train).to_numpy(), best)
        p[b] = m.predict_proba(Z)
    assert np.isfinite(p).all() and np.allclose(p.sum(axis=1), 1)
    loss = -np.log(np.clip(p[np.arange(len(x)), x.y.to_numpy()], np.finfo(float).eps, 1))
    return helpers.metrics(x.y.to_numpy(), p, inputs.normalized_weights(x).to_numpy()), choices, loss


def main():
    started = datetime.now(timezone.utc).isoformat()
    config = json.loads((OUT / 'gles_input_contract.json').read_text())
    for p, sha in config['fixed_input_hashes'].items():
        assert inputs.digest(ROOT / p) == sha
    d, _ = inputs.load_data()
    points, coefficients, validation, calibration, incremental, sensitivity, status, choices = [], [], [], [], [], [], [], []
    for yi, year in enumerate(inputs.ELECTIONS):
        for ti, target in enumerate(inputs.TARGETS):
            x = inputs.analytic_sample(d, target, year=year).reset_index(drop=True)
            assert len(x) == config['sample_totals'][f'{year}:{target}'] and x.person_id.is_unique
            X, _, names = model.design(x, x)
            w, y = inputs.normalized_weights(x).to_numpy(), x.y.to_numpy()
            m = helpers.fitted(X, y, w)
            print(f'GLES {year} {target}, n={len(x)}', flush=True)
            point = pd.DataFrame(helpers.margins(m, X, w, names, inputs.CONTRASTS))
            ci = model.bootstrap_margins(x, X, names, 1000, 20261106 + 10 * yi + ti)
            point = point.merge(ci, on=['variable', 'outcome'], validate='one_to_one')
            point['year'] = year; point['target'] = target; point['n'] = len(x)
            points.extend(point.to_dict('records'))
            for k, beta in enumerate(m.coef_):
                for feature, value in zip(names, beta):
                    coefficients.append({'year': year, 'target': target,
                                         'coefficient_class': int(m.classes_[k] if len(m.classes_) > 2 else 1),
                                         'feature': feature, 'coefficient': float(value), 'intercept': float(m.intercept_[k])})
            pd.DataFrame(points).to_csv(OUT / 'gles_model_margins.csv', index=False)
            pd.DataFrame(coefficients).to_csv(OUT / 'gles_model_coefficients.csv', index=False)
            losses = {}
            for block in inputs.BLOCKS:
                stats, cal, loss = model.cross_validate(x, block, 20261106)
                h = {'year': year, 'target': target, 'block': block, 'validation': 'fixed_C', 'n': len(x)}
                validation.append({**h, **stats}); calibration.extend([{**h, **r} for r in cal])
                losses[block] = loss
            for a, b in model.PAIRS:
                r = model.paired_loss_comparison(losses[a], losses[b], w, x.person_id.to_numpy(), 20261106)
                incremental.append({'year': year, 'target': target, 'validation': 'fixed_C',
                                    'baseline_block': a, 'expanded_block': b, **r})
            nested = {}
            for block in ['baseline', 'full']:
                stats, selection, loss = nested_validation(x, block)
                h = {'year': year, 'target': target, 'block': block, 'validation': 'nested_C', 'n': len(x)}
                validation.append({**h, **stats}); choices.extend([{**h, **r} for r in selection]); nested[block] = loss
            incremental.append({'year': year, 'target': target, 'validation': 'nested_C',
                                'baseline_block': 'baseline', 'expanded_block': 'full',
                                **model.paired_loss_comparison(nested['baseline'], nested['full'], w, x.person_id.to_numpy(), 20261106)})
            specs = [('C_0.1', .1, False, (), (), False), ('C_10', 10., False, (), (), False),
                     ('unweighted', 1., True, (), (), False),
                     ('without_pre_intention', 1., False, (), ('pre_intention_group',), False),
                     ('without_party_identity', 1., False, (), ('party_identity', 'party_identity_strength'), False),
                     ('without_both_prior_preferences', 1., False, (), ('pre_intention_group', 'party_identity', 'party_identity_strength'), False),
                     ('exact_party_intention', 1., False, (), (), True),
                     ('add_household', 1., False, ('household_bad',), (), False),
                     ('add_government_responsibility', 1., False, ('government_responsibility',), (), False),
                     ('honesty_only', 1., False, (), ('parties_only_votes',), False),
                     ('only_votes_only', 1., False, (), ('politicians_dishonest',), False)]
            for label, C, unweighted, extra, drop, exact in specs:
                z = x[x[list(extra)].notna().all(axis=1)].copy() if extra else x
                for kind in ['reference_same_subset', 'alternative']:
                    rows = model.fit_margins(z, C=C if kind == 'alternative' else 1.,
                                             unweighted=unweighted and kind == 'alternative',
                                             extra=extra if kind == 'alternative' else (), drop=drop if kind == 'alternative' else (),
                                             exact_intention=exact and kind == 'alternative')
                    sensitivity.extend([{'year': year, 'target': target, 'scenario': label, 'fit': kind, 'n': len(z), **r} for r in rows])
            for label in ['economic_priority_broad', 'economic_priority_anycode']:
                for kind in ['reference_same_subset', 'alternative']:
                    z = x.copy()
                    if kind == 'alternative': z['economic_priority'] = z[label]
                    sensitivity.extend([{'year': year, 'target': target, 'scenario': label, 'fit': kind, 'n': len(z), **r}
                                        for r in model.fit_margins(z)])
            for version, rule in [('3', 'inclusive'), ('4', 'strict'), ('3', 'strict')]:
                z = inputs.analytic_sample(d, target, outcome=f'outcome_v{version}_{rule}', year=year)
                label = f'v{version}_{rule}'
                estimable = set(z.y.unique()) == set(x.y.unique()) and z.y.value_counts().min() >= 5
                status.append({'year': year, 'target': target, 'scenario': label, 'n': len(z),
                               'same_classes_and_minimum_5': estimable,
                               'reason_if_skipped': '' if estimable else 'A primary class is absent or has fewer than five observed people'})
                if estimable:
                    sensitivity.extend([{'year': year, 'target': target, 'scenario': label, 'fit': 'alternative', 'n': len(z), **r}
                                        for r in model.fit_margins(z)])
            for name, rows in [('gles_model_validation', validation), ('gles_model_calibration', calibration),
                               ('gles_model_incremental_validation', incremental), ('gles_model_sensitivity', sensitivity),
                               ('gles_classification_sensitivity_status', status), ('gles_nested_C_choices', choices)]:
                pd.DataFrame(rows).to_csv(OUT / (name + '.csv'), index=False)
            print(f'GLES {year} {target}: validation and sensitivity completed', flush=True)
    run = {'start_utc': started, 'end_utc': datetime.now(timezone.utc).isoformat(),
           'script_sha256': inputs.digest(Path(__file__)), 'contract_sha256': inputs.digest(OUT / 'gles_input_contract.json'),
           'shared_BES_model_sha256': inputs.digest(ROOT / 'analysis/59_bes_pre_election_models.py'),
           'shared_logistic_helper_sha256': inputs.digest(ROOT / 'analysis/51_eurobarometer_models.py'),
           'bootstrap_draws_per_marginal_estimate': 1000, 'heldout_loss_bootstrap_draws': 2000,
           'nested_C_grid': [.1, 1., 10.], 'inner_folds': 3, 'outer_folds': 5,
           'nested_blocks': ['baseline', 'full'], 'validation_intervals_refit_training': False,
           'microdata_exported': False, 'interpretation': 'Pre-election conditional associations, not a causal crisis effect',
           'remaining': ['Within-person changes of issue importance and policy positions', 'Designed 2009/2013 linkage', 'Observed-selection sensitivity']}
    (OUT / 'gles_models_run.json').write_text(json.dumps(run, indent=2) + '\n')
    print('German pre-election snapshot models completed.', flush=True)


if __name__ == '__main__':
    with threadpool_limits(limits=1):
        main()
