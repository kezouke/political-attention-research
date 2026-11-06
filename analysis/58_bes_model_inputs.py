"""Locked input definitions for pre-election BES models, no vote fitting."""
from pathlib import Path
import hashlib
import io
import json
import zipfile
import numpy as np
import pandas as pd
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/three_explanations'
AUDIT = ROOT / 'data/processed/audit_20261106'
spec = importlib.util.spec_from_file_location('parties', ROOT / 'analysis/57_bes_party_crosswalk.py')
parties = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parties)

CONTROLS = ['age_scaled', 'age_squared', 'age_missing', 'left_right', 'left_right_squared', 'left_right_missing']
CATEGORICAL = ['gender_category', 'region_category', 'education_category', 'employment_category',
               'party_identity', 'party_identity_strength', 'pre_intention_group']
CORE = ['economy_bad', 'government_disapproval', 'economic_priority', 'politician_distrust']
BLOCKS = {
    'baseline': [],
    'economy_government': ['economy_bad', 'government_disapproval'],
    'plus_priority': ['economy_bad', 'government_disapproval', 'economic_priority'],
    'full': CORE,
    'without_economy': ['government_disapproval', 'economic_priority', 'politician_distrust'],
    'without_government': ['economy_bad', 'economic_priority', 'politician_distrust'],
    'without_priority': ['economy_bad', 'government_disapproval', 'politician_distrust'],
    'without_trust': ['economy_bad', 'government_disapproval', 'economic_priority'],
}
CONTRASTS = {'economy_bad': (.25, .75), 'government_disapproval': (.25, .75),
             'economic_priority': (0., 1.), 'politician_distrust': (1/3, 2/3)}
TARGETS = ['government_vs_opposition', 'opposition_type', 'nonvote_vs_vote', 'four_outcomes']
EARLY = {2015: 1, 2017: 7, 2019: 16}
MII_CODES = [1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def category(s, codes):
    return s.where(s.isin(codes), -999).fillna(-999).astype(int).astype(str)


def bad(s, top):
    return ((top - s) / (top - 1)).where(s.between(1, top))


def attitude_frame(x):
    z = pd.DataFrame(index=x.index)
    z['economy_bad'] = bad(x.econGenRetro, 5)
    z['government_disapproval'] = bad(x.approveUKGovt, 5)
    z['politician_distrust'] = bad(x.trustMPs, 7)
    z['economic_priority'] = x.small_mii_cat.eq(3).astype(float).where(x.small_mii_cat.isin(MII_CODES))
    z['economic_priority_broad'] = x.small_mii_cat.isin([3, 7, 9]).astype(float).where(x.small_mii_cat.isin(MII_CODES))
    z['household_bad'] = bad(x.econPersonalRetro, 5)
    for v in ['redistSelf', 'immigSelf', 'EUIntegrationSelf', 'enviroGrowth']:
        z[v] = (x[v] / 10).where(x[v].between(0, 10))
    z['immigration_economy_bad'] = bad(x.immigEcon, 7)
    z['issue_category'] = category(x.small_mii_cat, MII_CODES)
    z['pre_intention'] = category(x.generalElectionVote, [0, *parties.PARTIES, 9999])
    z['best_on_issue'] = category(x.bestOnMII, [0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 9999])
    return z


def intention_group(x, year, crosswalk):
    # Incumbency changes between elections, notably for the Liberal Democrats.
    # Map the declared intended party using that election's cabinet, not its
    # outcome label in a previous training year. Preserve undecided respondents.
    group = parties.classify(x.generalElectionVote, pd.Series(1, index=x.index),
                             x.gor, year, crosswalk).astype(str)
    group.loc[x.generalElectionVote.eq(0)] = 'intends_nonvote'
    group.loc[x.generalElectionVote.eq(9999)] = 'undecided'
    group.loc[x.generalElectionVote.isna()] = 'missing'
    return group


def load_data():
    cols = ['id', 'wave', 'weight', 'age', 'gender', 'gor', 'p_edlevel', 'p_work_stat', 'lr_scale',
            'partyId', 'partyIdStrength', 'generalElectionVote', 'turnoutUKGeneral', 'econGenRetro',
            'econPersonalRetro', 'approveUKGovt', 'trustMPs', 'small_mii_cat', 'bestOnMII',
            'redistSelf', 'immigSelf', 'immigEcon', 'EUIntegrationSelf', 'enviroGrowth', 'polAttention']
    with zipfile.ZipFile(parties.bes.verified('bes_teaching_long_v1')) as z:
        d = pd.read_stata(io.BytesIO(z.read('BESIP_teaching_long.dta')), columns=cols, convert_categoricals=False)
    assert not d.duplicated(['id', 'wave']).any()
    crosswalk = pd.read_csv(OUT / 'bes_party_crosswalk.csv')
    result = []
    for year, cfg in parties.ELECTIONS.items():
        pre = d[d.wave.eq(cfg['pre'])].set_index('id')
        post = d[d.wave.eq(cfg['post'])].set_index('id').reindex(pre.index)
        early = d[d.wave.eq(EARLY[year])].set_index('id').reindex(pre.index)
        z = attitude_frame(pre)
        z['person_id'] = pre.index
        z['pre_intention_group'] = intention_group(pre, year, crosswalk)
        z['year'] = year
        z['weight'] = pre.weight
        z['eligible'] = pre.age.between(18, 100) & pre.gor.between(1, 11)
        z['age_missing'] = (~pre.age.between(18, 100)).astype(float)
        z['age_scaled'] = (pre.age.where(pre.age.between(18, 100), 50) - 50) / 20
        z['age_squared'] = z.age_scaled.pow(2)
        lr = pre.lr_scale.where(pre.lr_scale.between(0, 10))
        z['left_right_missing'] = lr.isna().astype(float)
        z['left_right'] = (lr.fillna(5) - 5) / 5
        z['left_right_squared'] = z.left_right.pow(2)
        for name, raw, codes in [('gender_category', 'gender', [1, 2]), ('region_category', 'gor', list(range(1, 12))),
                                  ('education_category', 'p_edlevel', list(range(6))),
                                  ('employment_category', 'p_work_stat', list(range(1, 9))),
                                  ('party_identity', 'partyId', [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 9999]),
                                  ('party_identity_strength', 'partyIdStrength', [1, 2, 3, 9999])]:
            z[name] = category(pre[raw], codes)
        z['political_attention'] = (pre.polAttention / 10).where(pre.polAttention.between(0, 10))
        z['pre_turnout_intention'] = category(pre.turnoutUKGeneral, [1, 2, 3, 4, 5, 9999])
        z['returned_post'] = post.wave.notna()
        z['reported_voted'] = post.turnoutUKGeneral.eq(1)
        z['reported_nonvote'] = post.turnoutUKGeneral.eq(0)
        z['reported_party_code'] = post.generalElectionVote
        for version in ['3', '4']:
            for rule in ['inclusive', 'strict']:
                z[f'outcome_v{version}_{rule}'] = parties.classify(post.generalElectionVote, post.turnoutUKGeneral,
                                                                  post.gor, year, crosswalk, version, rule)
        z['core_complete'] = z[CORE].notna().all(axis=1)
        assert np.isfinite(z.loc[z.eligible, 'weight']).all() and z.loc[z.eligible, 'weight'].gt(0).all()
        e = attitude_frame(early).add_prefix('early_')
        e['early_pre_intention_group'] = intention_group(early, year, crosswalk)
        z = pd.concat([z, e], axis=1)
        z['early_returned'] = early.wave.notna()
        z['early_weight'] = early.weight
        for variable in CORE + ['redistSelf', 'immigSelf', 'EUIntegrationSelf', 'enviroGrowth']:
            z['change_' + variable] = z[variable] - z['early_' + variable]
        z['early_core_complete'] = z[['early_' + v for v in CORE]].notna().all(axis=1)
        age_change = pre.age - early.age
        z['age_change_flag'] = age_change.lt(0) | age_change.gt({2015: 2, 2017: 2, 2019: 3}[year])
        result.append(z.reset_index(drop=True))
    out = pd.concat(result, ignore_index=True)
    assert not out.duplicated(['person_id', 'year']).any()
    return out


def analytic_sample(d, target, outcome='outcome_v4_inclusive', year=None):
    x = d[d.eligible & d.core_complete].copy()
    if year is not None:
        x = x[x.year.eq(year)].copy()
    if target == 'government_vs_opposition':
        x = x[x[outcome].isin([0, 1, 2])].copy()
        x['y'] = x[outcome].eq(0).astype(int)
    elif target == 'opposition_type':
        x = x[x[outcome].isin([1, 2])].copy()
        x['y'] = x[outcome].eq(2).astype(int)
    elif target == 'nonvote_vs_vote':
        # Turnout does not need a classified or named party.
        x = x[x.reported_voted | x.reported_nonvote].copy()
        x['y'] = x.reported_nonvote.astype(int)
    elif target == 'four_outcomes':
        x = x[x[outcome].isin([0, 1, 2, 3])].copy()
        x['y'] = x[outcome].astype(int)
    else:
        raise ValueError(target)
    return x


def normalized_weights(x, column='weight'):
    # Equal total weight per election in pooled training. A single-year fit
    # preserves the pre-wave producer weights, normalized to its sample size.
    return x[column] / x.groupby('year')[column].transform('sum') * (len(x) / x.year.nunique())


def main():
    d = load_data()
    counts, distributions, selection = [], [], []
    for year in parties.ELECTIONS:
        pre = d[d.year.eq(year) & d.eligible]
        for label, mask in [('eligible', pd.Series(True, index=pre.index)),
                            ('core_complete', pre.core_complete),
                            ('core_and_returned', pre.core_complete & pre.returned_post),
                            ('core_and_known_four_outcomes', pre.core_complete & pre.outcome_v4_inclusive.ge(0)),
                            ('both_pre_waves_core_and_known_outcome', pre.core_complete & pre.early_core_complete & pre.outcome_v4_inclusive.ge(0))]:
            selection.append({'year': year, 'group': label, 'n': int(mask.sum()),
                              'share_of_eligible_pre': float(mask.mean()),
                              'pre_weight_share': float(pre.loc[mask, 'weight'].sum() / pre.weight.sum())})
        for target in TARGETS:
            x = analytic_sample(d, target, year=year)
            for code, n in x.y.value_counts().sort_index().items():
                counts.append({'year': year, 'target': target, 'n': len(x), 'outcome': int(code), 'outcome_n': int(n)})
            for v in CORE:
                for value, g in x.groupby(v):
                    distributions.append({'year': year, 'target': target, 'variable': v, 'value': value,
                                          'n': len(g), 'pre_weight_share': float(g.weight.sum() / x.weight.sum())})
    for name, rows in [('bes_locked_sample_counts', counts), ('bes_locked_predictor_distributions', distributions),
                       ('bes_locked_selection_counts', selection)]:
        pd.DataFrame(rows).to_csv(OUT / (name + '.csv'), index=False)
    files = ['analysis/51_eurobarometer_models.py', 'analysis/56_bes_input_provenance_audit.py', 'analysis/57_bes_party_crosswalk.py',
             'analysis/58_bes_model_inputs.py', 'planning/analysis-protocol-v1.md',
             'planning/bes-measurement-notes.md', 'planning/bes-analysis-lock.md',
             'data/processed/three_explanations/bes_party_crosswalk.csv',
             'data/processed/three_explanations/bes_incumbent_cabinets.csv',
             'data/processed/three_explanations/bes_locked_sample_counts.csv']
    raw = parties.bes.verified('bes_teaching_long_v1')
    files.append(str(raw.relative_to(ROOT)))
    contract = {'fixed_input_hashes': {p: digest(ROOT / p) for p in files},
                'numeric_controls': CONTROLS, 'categorical_controls': CATEGORICAL,
                'blocks': BLOCKS, 'contrasts': CONTRASTS,
                'seed': 20261106, 'main_regularization_C': 1.0, 'bootstrap_respondent_draws': 1000,
                'sample_totals': {f"{r['year']}:{r['target']}": r['n'] for r in counts},
                'pre_post_waves': {str(k): {'pre': v['pre'], 'post': v['post'], 'election_date': v['date']} for k, v in parties.ELECTIONS.items()},
                'early_waves': EARLY, 'primary_priority': 'Economy, code 3 in pinned v1; broad codes 3,7,9 only a sensitivity',
                'primary_includes_pre_intention': True,
                'missing_pre_intention_excluded': False,
                'unknown_party_treated_as_nonvote': False,
                'turnout_requires_classified_party': False,
                'future_controls_used': False,
                'time_horizon_2017_longer': True,
                'raw_records_or_identifiers_exported': False}
    (OUT / 'bes_input_contract.json').write_text(json.dumps(contract, indent=2) + '\n')
    print(pd.DataFrame(counts).to_string(index=False))
    print(pd.DataFrame(selection).round(4).to_string(index=False))


if __name__ == '__main__':
    main()
