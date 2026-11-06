"""Freeze within-campaign issue-position and importance inputs, no vote fits."""
from pathlib import Path
import importlib.util
import json
import numpy as np
import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('inputs', ROOT / 'analysis/66_gles_model_inputs.py')
inputs = importlib.util.module_from_spec(spec); spec.loader.exec_module(inputs)
OUT = inputs.OUT
TOPICS = {'tax_welfare': ('1090', '1100'), 'immigration': ('1130', '1140'), 'climate_growth': ('1290', '1300')}


def intention(d, wave, crosswalk):
    party = d[f'kp{wave}_190bb'].replace({2: 1, 3: 1})
    result = inputs.classify(party, pd.Series(True, index=d.index), pd.Series(False, index=d.index), 2013, crosswalk).astype(str)
    result.loc[d[f'kp{wave}_170'].eq(5)] = 'certain_nonvote'
    result.loc[party.isin([-98, -81])] = 'undecided'
    return result


def load_data():
    all_years, _ = inputs.load_data()
    z = all_years[all_years.year.eq(2013)].copy()
    manifest = json.loads((inputs.AUDIT / 'authenticated_downloads.json').read_text())
    record = next(e for e in manifest['files'] if e['filename'] == 'ZA5704_en_v3-2-0.dta')
    path = ROOT / record['local_path']; assert inputs.digest(path) == record['sha256']
    cols = ['lfdn'] + [f'kp{wave}_{code}' for wave in [2, 4] for code in ['170', '190bb', 'datetime', '1090', '1100', '1130', '1140', '1290', '1300']]
    d, meta = pyreadstat.read_dta(path, usecols=cols)
    z = z.merge(d, left_on='person_id', right_on='lfdn', validate='one_to_one')
    cw, _ = inputs.make_crosswalk()
    z['mid_pre_intention_group'] = z.pre_intention_group
    z['pre_intention_group'] = intention(z, 2, cw)
    z['late_pre_intention_group'] = intention(z, 4, cw)
    z['before_postal_late'] = z.kp4_170.between(1, 5)
    for topic, (position, importance) in TOPICS.items():
        for wave, stage in [(2, 'early'), (4, 'late')]:
            p, q = z[f'kp{wave}_{position}'], z[f'kp{wave}_{importance}']
            assert meta.variable_value_labels[f'kp{wave}_{importance}'][1] == 'very important'
            assert meta.variable_value_labels[f'kp{wave}_{importance}'][5] == 'completely unimportant'
            z[f'{topic}_{stage}_position'] = (p.where(p.between(1, 7)) - 1) / 6
            z[f'{topic}_{stage}_importance'] = (5 - q.where(q.between(1, 5))) / 4
            z[f'{topic}_{stage}_interaction'] = z[f'{topic}_{stage}_importance'] * (z[f'{topic}_{stage}_position'] - .5)
        for v in ['position', 'importance']:
            z[f'{topic}_change_{v}'] = z[f'{topic}_late_{v}'] - z[f'{topic}_early_{v}']
        z[f'{topic}_complete'] = z[[f'{topic}_{stage}_{v}' for stage in ['early', 'late'] for v in ['position', 'importance']]].notna().all(axis=1)
    # All repeated measurements used here must precede the election.
    for wave in [2, 4]:
        s = z[f'kp{wave}_datetime'].astype(str)
        date = pd.to_datetime(s.where(s.str.match(r'^2013-\d{2}-\d{2} ')), errors='coerce', format='%Y-%m-%d %H:%M:%S')
        assert date.dropna().lt(pd.Timestamp('2013-09-22')).all()
    return z


def analytic_sample(d, topics, outcome='outcome_v4_inclusive', require_core=True):
    x = d[d.eligible & d.before_postal_late & d[outcome].ge(0)].copy()
    if require_core: x = x[x.core_complete].copy()
    x = x[x[[t + '_complete' for t in topics]].all(axis=1)].copy()
    x['y'] = x[outcome].astype(int)
    return x


def main():
    d = load_data()
    counts, missing, dates = [], [], []
    for topics in [[t] for t in TOPICS] + [list(TOPICS)]:
        name = topics[0] if len(topics) == 1 else 'all_three'
        for core in [True, False]:
            x = analytic_sample(d, topics, require_core=core)
            for k, n in x.y.value_counts().sort_index().items():
                counts.append({'topic': name, 'require_core': core, 'n': len(x), 'outcome': int(k), 'outcome_n': int(n)})
            missing.append({'topic': name, 'require_core': core, 'n': len(x),
                            'early_intention_unresolved_n': int(x.pre_intention_group.eq('-1').sum()),
                            'late_intention_unresolved_n': int(x.late_pre_intention_group.eq('-1').sum())})
    for wave in [2, 4]:
        raw = d[f'kp{wave}_datetime'].astype(str)
        dt = pd.to_datetime(raw.where(raw.str.match(r'^2013-\d{2}-\d{2} ')), errors='coerce', format='%Y-%m-%d %H:%M:%S')
        dates.append({'wave': wave, 'valid_interview_dates_n': int(dt.notna().sum()),
                      'start': str(dt.min()), 'end': str(dt.max()),
                      'already_postal_n': int(d[f'kp{wave}_170'].eq(6).sum())})
    pd.DataFrame(counts).to_csv(OUT / 'gles_importance_locked_counts.csv', index=False)
    pd.DataFrame(missing).to_csv(OUT / 'gles_importance_intention_coverage.csv', index=False)
    files = [Path(__file__), ROOT / 'planning/gles-importance-change-lock.md',
             OUT / 'gles_input_contract.json', ROOT / 'analysis/66_gles_model_inputs.py',
             OUT / 'gles_importance_locked_counts.csv']
    contract = {'fixed_input_hashes': {str(p.relative_to(ROOT)): inputs.digest(p) for p in files},
                'parent_input_contract': 'gles_input_contract.json', 'topics': TOPICS,
                'interview_windows': dates, 'primary_intention_wave': 2, 'late_intention_wave': 4,
                'midwave_distrust_is_secondary_adjustment': True,
                'primary_late_importance_contrast': [.5, .75],
                'position_scenarios': {'observed': 'observed late positions', 'low_position': 1/6, 'high_position': 5/6},
                'sample_totals': {r['topic']: r['n'] for r in counts if r['require_core']},
                'primary_C': 1., 'seed': 20261106, 'bootstrap_person_draws': 1000,
                'microdata_exported': False, 'political_association_models_fitted': False}
    (OUT / 'gles_importance_input_contract.json').write_text(json.dumps(contract, indent=2) + '\n')
    print(pd.DataFrame(counts).to_string(index=False)); print(pd.DataFrame(dates).to_string(index=False))


if __name__ == '__main__': main()
