"""Define time-verified repeated BES inputs, no new political models."""
from pathlib import Path
import importlib.util
import io
import json
import zipfile
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
s = importlib.util.spec_from_file_location('inputs', ROOT / 'analysis/58_bes_model_inputs.py')
inputs = importlib.util.module_from_spec(s); s.loader.exec_module(inputs)
OUT = inputs.OUT
EARLY = {2015: 1, 2017: 4, 2019: 16}
POSITION_VARS = ['redistSelf', 'immigSelf']


def load_data():
    late = inputs.load_data()
    cols = ['id', 'wave', 'weight', 'age', 'gender', 'gor', 'p_edlevel', 'p_work_stat', 'lr_scale',
            'partyId', 'partyIdStrength', 'generalElectionVote', 'turnoutUKGeneral', 'econGenRetro',
            'econPersonalRetro', 'approveUKGovt', 'trustMPs', 'small_mii_cat', 'bestOnMII',
            'redistSelf', 'immigSelf', 'immigEcon', 'EUIntegrationSelf', 'enviroGrowth', 'polAttention']
    with zipfile.ZipFile(inputs.parties.bes.verified('bes_teaching_long_v1')) as z:
        raw = pd.read_stata(io.BytesIO(z.read('BESIP_teaching_long.dta')), columns=cols, convert_categoricals=False)
    crosswalk = pd.read_csv(OUT / 'bes_party_crosswalk.csv')
    result = []
    for year, wave in EARLY.items():
        x = late[late.year.eq(year)].set_index('person_id').copy()
        early = raw[raw.wave.eq(wave)].set_index('id').reindex(x.index)
        later = raw[raw.wave.eq(inputs.parties.ELECTIONS[year]['pre'])].set_index('id').reindex(x.index)
        frame = inputs.attitude_frame(early)
        for v in frame: x['early_' + v] = frame[v]
        x['person_id'] = x.index
        x['both_eligible'] = x.eligible & early.age.between(18, 100) & early.gor.between(1, 11)
        x['early_core_complete'] = x[['early_' + v for v in inputs.CORE]].notna().all(axis=1)
        x['late_pre_intention_group'] = x.pre_intention_group
        x['pre_intention_group'] = inputs.intention_group(early, year, crosswalk)
        x['late_weight'] = x.weight; x['weight'] = early.weight
        x['age_scaled'] = (early.age.where(early.age.between(18, 100), 50) - 50) / 20
        x['age_squared'] = x.age_scaled.pow(2)
        x['age_missing'] = (~early.age.between(18, 100)).astype(float)
        lr = early.lr_scale.where(early.lr_scale.between(0, 10))
        x['left_right_missing'] = lr.isna().astype(float)
        x['left_right'] = (lr.fillna(5) - 5) / 5; x['left_right_squared'] = x.left_right.pow(2)
        for target, name, codes in [('gender_category', 'gender', [1, 2]), ('region_category', 'gor', list(range(1, 12))),
                                     ('education_category', 'p_edlevel', list(range(6))), ('employment_category', 'p_work_stat', list(range(1, 9))),
                                     ('party_identity', 'partyId', [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 9999]),
                                     ('party_identity_strength', 'partyIdStrength', [1, 2, 3, 9999])]:
            x[target] = inputs.category(early[name], codes)
        age_change = later.age - early.age
        x['age_change_flag'] = age_change.lt(0) | age_change.gt({2015: 2, 2017: 3, 2019: 1}[year])
        for v in inputs.CORE + POSITION_VARS: x['change_' + v] = x[v] - x['early_' + v]
        valid = x.both_eligible & x.core_complete & x.early_core_complete
        assert np.isfinite(x.loc[valid, 'weight']).all() and x.loc[valid, 'weight'].gt(0).all()
        result.append(x.reset_index(drop=True))
    return pd.concat(result, ignore_index=True)


def analytic_sample(d, target, year, outcome='outcome_v4_inclusive'):
    x = inputs.analytic_sample(d, target, outcome, year)
    return x[x.both_eligible & x.early_core_complete].copy()


def main():
    parent = json.loads((OUT / 'bes_input_contract.json').read_text())
    for p, sha in parent['fixed_input_hashes'].items(): assert inputs.digest(ROOT / p) == sha
    d = load_data(); counts, coverage = [], []
    for year in EARLY:
        pre = d[d.year.eq(year)]
        coverage.append({'year': year, 'early_wave': EARLY[year], 'late_wave': inputs.parties.ELECTIONS[year]['pre'],
                         'both_pre_core_and_eligible': int((pre.both_eligible & pre.core_complete & pre.early_core_complete).sum())})
        for target in inputs.TARGETS:
            x = analytic_sample(d, target, year)
            assert x.person_id.is_unique
            for k, n in x.y.value_counts().sort_index().items():
                counts.append({'year': year, 'target': target, 'n': len(x), 'outcome': int(k), 'outcome_n': int(n),
                               'age_change_flags': int(x.age_change_flag.sum()),
                               'both_positions_available': int(x[POSITION_VARS + ['early_' + v for v in POSITION_VARS]].notna().all(axis=1).sum())})
    pd.DataFrame(counts).to_csv(OUT / 'bes_change_locked_counts.csv', index=False)
    pd.DataFrame(coverage).to_csv(OUT / 'bes_change_locked_coverage.csv', index=False)
    paths = [Path(__file__), ROOT / 'planning/bes-change-specification.md', OUT / 'bes_input_contract.json', OUT / 'bes_change_locked_counts.csv']
    report = {'fixed_input_hashes': {str(p.relative_to(ROOT)): inputs.digest(p) for p in paths},
              'early_waves': EARLY, 'sample_totals': {f"{r['year']}:{r['target']}": r['n'] for r in counts},
              'new_vote_models_fitted': False, 'microdata_exported': False,
              'unresolved_wave7_timing_used': False, 'wave16_trust_assignment_assumed_random': False,
              '2017_interval_spans_government_change': True, 'primary_weight': 'early wave'}
    (OUT / 'bes_change_input_contract.json').write_text(json.dumps(report, indent=2) + '\n')
    print(pd.DataFrame(coverage).to_string(index=False)); print(pd.DataFrame(counts).to_string(index=False))


if __name__ == '__main__': main()
