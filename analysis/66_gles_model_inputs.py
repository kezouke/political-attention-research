"""Define German campaign-panel inputs and party labels before vote models.

Read locally authorized GESIS records. Export only aggregate coverage,
measurement rules, source metadata and hashes, never people or their answers.
"""
from pathlib import Path
import importlib.util
import hashlib
import json
import numpy as np
import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/three_explanations'
AUDIT = ROOT / 'data/processed/audit_20261106'


def module(name, filename):
    s = importlib.util.spec_from_file_location(name, ROOT / 'analysis' / filename)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


source = module('source', '47_party_classification_audit.py')
panel = module('panel', '46_gles_panel_audit.py')
topics = module('topics', '61_gles_measurement_harmonization.py')
ELECTIONS = {2009: {'date': '2009-09-27', 'pre': 2, 'government': {1, 2, 3, 4}, 'file': 'ZA5305_en_v5-0-0.dta'},
             2013: {'date': '2013-09-22', 'pre': 3, 'government': {1, 2, 3, 5}, 'file': 'ZA5704_en_v3-2-0.dta'}}
PARTIES = {1: ('CDU/CSU', 'Christian Democratic Union', None),
           2: ('CDU', 'Christian Democratic Union', None), 3: ('CSU', 'Christian Democratic Union', None),
           4: ('SPD', 'Social Democratic Party of Germany', None),
           5: ('FDP', 'Free Democratic Party', None), 6: ('Greens', 'Alliance 90/Greens', None),
           7: ('The Left', 'The Left', 791), 215: ('Pirates', 'Pirate Party Germany', None),
           225: ('Republicans', 'The Republicans', 524), 322: ('AfD', 'Alternative for Germany', 2253),
           180: ('Free Voters', None, None), 206: ('NPD', 'National Democratic Party of Germany', None),
           209: ('OeDP', 'Ecological Democratic Party', None)}
CONTROLS = ['age_scaled', 'age_squared', 'left_right', 'left_right_squared', 'left_right_missing']
CATEGORICAL = ['gender_category', 'region_category', 'education_category', 'employment_category',
               'community_category', 'party_identity', 'party_identity_strength', 'pre_intention_group']
CORE = ['economy_bad', 'government_distrust', 'economic_priority', 'politicians_dishonest', 'parties_only_votes']
BLOCKS = {'baseline': [], 'economy_government': CORE[:2], 'plus_priority': CORE[:3], 'full': CORE,
          'without_economy': CORE[1:], 'without_government': [v for v in CORE if v != 'government_distrust'],
          'without_priority': [v for v in CORE if v != 'economic_priority'], 'without_trust': CORE[:3]}
CONTRASTS = {v: ((0., 1.) if v == 'economic_priority' else (.25, .75)) for v in CORE}
TARGETS = ['government_vs_opposition', 'opposition_type', 'nonvote_vs_vote', 'four_outcomes']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_crosswalk():
    national = source.ppeg('parl')
    national = national[national.iso3c.eq('DEU') & national.edate.ge('1989-01-01') & national.edate.le('2022-12-31')]
    lists = {'3': pd.read_excel(source.audit_file('populist3_release'), header=1),
             '4': pd.read_csv(source.audit_file('populist4_current'), sep=';')}
    rows, cabinets = [], []
    for year, cfg in ELECTIONS.items():
        cabinet = source.cabinet_record(source.ppeg('comb'), 'DEU', pd.Timestamp(cfg['date']), 'GLES_national')
        expected = ' | '.join(sorted({PARTIES[c][1] for c in cfg['government']}))
        assert cabinet['government_parties'] == expected
        cabinet['status'] = 'PPEG groups CDU/CSU under Christian Democratic Union; all CDU/CSU survey variants mapped to cabinet'
        cabinets.append(cabinet)
        election = national[national.edate.eq(cfg['date'])]
        for code, (label, name, plid) in PARTIES.items():
            present = name is not None and name in set(election.pname_en)
            history = national[national.pname_en.eq(name)]
            eligible = bool((history.v_share_wgt.ge(.02) | history.seats.ge(1)).any())
            r = {'year': year, 'election_date': cfg['date'], 'gles_code': code, 'survey_label': label,
                 'ppeg_name': name or '', 'national_participation_verified': present,
                 'eligible_national_history': eligible, 'incumbent_cabinet_party': code in cfg['government']}
            for version, pl in lists.items():
                match = pl[pl.country_name.eq('Germany') & pl.parlgov_id.eq(plid)] if plid else pl.iloc[:0]
                assert len(match) <= 1
                if present and len(match):
                    q = match.iloc[0]
                    values = {'inclusive': int(q['populist'] == 1 and q.populist_start <= year <= q.populist_end),
                              'strict': int(q['populist'] == 1 and q.populist_startnobl <= year <= q.populist_endnobl)}
                    basis = 'explicit_PopuList_row'
                elif present and eligible:
                    assert not (pl.country_name.eq('Germany') & pl.party_name_english.eq(name)).any()
                    values, basis = {'inclusive': 0, 'strict': 0}, 'eligible_party_not_listed'
                else:
                    values, basis = {'inclusive': np.nan, 'strict': np.nan}, 'unresolved_scope_or_participation'
                r[f'populist_v{version}_basis'] = basis
                for rule, value in values.items():
                    r[f'populist_v{version}_{rule}'] = value
                    r[f'outcome_v{version}_{rule}'] = (0 if code in cfg['government'] else
                                                          -1 if pd.isna(value) else 2 if value else 1)
            rows.append(r)
    return pd.DataFrame(rows), pd.DataFrame(cabinets)


def classify(party, voted, nonvote, year, crosswalk, version='4', rule='inclusive'):
    result = pd.Series(-1, index=party.index, dtype=int)
    lookup = crosswalk[crosswalk.year.eq(year)].set_index('gles_code')[f'outcome_v{version}_{rule}']
    result.loc[voted] = party.loc[voted].map(lookup).fillna(-1).astype(int)
    assert not (voted & nonvote).any()
    result.loc[nonvote] = 3
    return result


def category(s, codes):
    return s.where(s.isin(codes), -999).fillna(-999).astype(int).astype(str)


def scale(s, reverse=False):
    q = (s.where(s.between(1, 5)) - 1) / 4
    return 1 - q if reverse else q


def read_year(year):
    cfg = ELECTIONS[year]
    manifest = json.loads((AUDIT / 'authenticated_downloads.json').read_text())
    entry = next(e for e in manifest['files'] if e['filename'] == cfg['file'])
    path = ROOT / entry['local_path']; assert digest(path) == entry['sha256']
    d, meta = panel.read_selected(cfg['file'])
    mapping = ({'age': 'kp1_2290a', 'gender': 'kp1_2280', 'education': 'kp1_2320', 'employment': 'kp1_2340',
                'lr': 'kp1_1500', 'identity': 'kp1_2090ac', 'strength': 'kp1_2100', 'region': 'fedstate', 'community': 'kp2_2600'}
               if year == 2009 else
               {'birth': 'kpx_2290', 'gender': 'kpx_2280', 'education': 'kpx_2320', 'employment': 'kpx_2340',
                'lr': 'kp1_1500', 'identity': 'kp1_2090b', 'strength': 'kp1_2100', 'region': 'kpx_2601', 'community': 'kpx_2600'})
    extra, _ = pyreadstat.read_dta(path, usecols=['lfdn', *[v for v in mapping.values() if v not in d]])
    return d.merge(extra, on='lfdn', validate='one_to_one'), meta, mapping


def load_data():
    cw, _ = make_crosswalk()
    output, routing = [], []
    for year, cfg in ELECTIONS.items():
        d, meta, names = read_year(year)
        att = cfg['pre']
        z = pd.DataFrame(index=d.index)
        z['person_id'] = d.lfdn  # only unique within year; cross-year linkage is separate
        z['year'] = year
        age = d[names['age']] if year == 2009 else year - d[names['birth']]
        z['eligible'] = age.between(18, 100) & d['mutant' if year == 2009 else 'mut09'].eq(0) & d[f'kp{att}_170'].between(1, 5)
        z['age_scaled'] = (age.where(age.between(18, 100), 50) - 50) / 20
        z['age_squared'] = z.age_scaled.pow(2)
        lr = d[names['lr']].where(d[names['lr']].between(1, 11))
        z['left_right'] = (lr.fillna(6) - 6) / 5
        z['left_right_squared'] = z.left_right.pow(2)
        z['left_right_missing'] = lr.isna().astype(float)
        for target, source_name, codes in [('gender_category', 'gender', [1, 2]), ('region_category', 'region', list(range(1, 17))),
                                          ('community_category', 'community', list(range(1, 6))),
                                          ('party_identity_strength', 'strength', list(range(1, 6)))]:
            z[target] = category(d[names[source_name]], codes)
        education = d[names['education']].replace({6: 9}) if year == 2009 else d[names['education']]
        z['education_category'] = category(education, [1, 2, 3, 4, 5, 9])
        employment = {2009: {1:'full',2:'part',3:'training',4:'hourly',5:'unemployed',6:'short_time',7:'retraining',
                             8:'leave',9:'home',10:'retired',11:'service',12:'school',13:'college',14:'incapacitated'},
                      2013: {1:'full',2:'part',3:'training',4:'school',5:'college',6:'retraining',7:'unemployed',
                             8:'short_time',9:'service',10:'retired',11:'leave',12:'home'}}
        z['employment_category'] = d[names['employment']].map(employment[year]).fillna('missing')
        # Route school students' structural employment skip into the known school category.
        z.loc[education.eq(9), 'employment_category'] = 'school'
        identity = d[names['identity']].replace({2: 1, 3: 1})
        z['party_identity'] = category(identity, [1, 4, 5, 6, 7, 215, 225, 322, 808])
        z['economy_bad'] = scale(d.kp1_800)
        z['household_bad'] = scale(d.kp1_760)
        z['government_responsibility'] = scale(d.kp1_810, reverse=True)
        z['government_distrust'] = scale(d[f'kp{att}_160c'], reverse=True)
        z['parliament_distrust'] = scale(d[f'kp{att}_160a'], reverse=True)
        z['politicians_dishonest'] = scale(d[f'kp{att}_040c'], reverse=True)
        z['parties_only_votes'] = scale(d[f'kp{att}_040a'])
        issue = f'kp{att}_840_c1'
        mapping = {int(k): topics.problem_group(int(k), year) for k in meta.variable_value_labels[issue] if 1000 <= k <= 5000}
        first = d[issue].map(mapping)
        broad = ['domestic_economy_labour_prices', 'euro_currency', 'public_finance_tax', 'distribution_poverty_security']
        z['issue_category'] = first
        z['economic_priority'] = first.eq('domestic_economy_labour_prices').astype(float).where(first.notna())
        z['economic_priority_broad'] = first.isin(broad).astype(float).where(first.notna())
        issue_columns = [f'kp{att}_840_c{k}' for k in range(1, 6) if f'kp{att}_840_c{k}' in d]
        codes = pd.DataFrame({v: d[v].map(mapping) for v in issue_columns})
        z['economic_priority_anycode'] = codes.eq('domestic_economy_labour_prices').any(axis=1).astype(float).where(codes.notna().any(axis=1))
        z['core_complete'] = z[CORE].notna().all(axis=1)
        z['weight'] = d['gew_q1_w1' if year == 2009 else 'wei_mz']
        assert z.loc[z.eligible & z.core_complete, 'weight'].gt(0).all()
        preparty = d['kp2_190bc' if year == 2009 else 'kp3_190bb'].replace({2: 1, 3: 1})
        z['pre_intention_group'] = classify(preparty, pd.Series(True, index=d.index), pd.Series(False, index=d.index), year, cw).astype(str)
        z.loc[d[f'kp{att}_170'].eq(5), 'pre_intention_group'] = 'certain_nonvote'
        z.loc[preparty.isin([998, -98, -81]), 'pre_intention_group'] = 'undecided'
        z['pre_intention'] = category(preparty, [1, 4, 5, 6, 7, 215, 225, 322, 801, 998, -98, -81, -85])
        z['pre_turnout_intention'] = category(d[f'kp{att}_170'], list(range(1, 6)))
        postparty = panel.named_series(d, meta, 'kp7_200bc' if year == 2009 else 'kp7_200bb').where(d.kp7_180.eq(1))
        reports = [postparty.rename('post')]
        postal = pd.Series(False, index=d.index)
        if year == 2013:
            for wave in range(3, 8):
                flag = d[f'kp{wave}_170'].eq(6) if wave < 7 else d.kp7_180.eq(6)
                postal |= flag
                reports.append(panel.named_series(d, meta, f'kp{wave}_191bb').where(flag).rename(str(wave)))
        combined = pd.concat(reports, axis=1)
        conflict = combined.nunique(axis=1).gt(1)
        voted, nonvote = d.kp7_180.eq(1) | postal, d.kp7_180.eq(2)
        contradiction = voted & nonvote
        voted &= ~contradiction; nonvote &= ~contradiction
        party = combined.bfill(axis=1).iloc[:, 0].where(~conflict)
        z['reported_voted'], z['reported_nonvote'] = voted, nonvote
        for version in ['3', '4']:
            for rule in ['inclusive', 'strict']:
                z[f'outcome_v{version}_{rule}'] = classify(party, voted, nonvote, year, cw, version, rule)
        routing.append({'year': year, 'parent_n': len(d), 'post_voted_n': int(d.kp7_180.eq(1).sum()),
                        'postal_reported_n': int(postal.sum()), 'party_report_conflicts': int(conflict.sum()),
                        'turnout_contradictions': int(contradiction.sum()),
                        'already_postal_at_pre_n': int(d[f'kp{att}_170'].eq(6).sum()),
                        'available_codes_for_one_problem_answer': issue_columns})
        output.append(z)
    return pd.concat(output, ignore_index=True), routing


def analytic_sample(d, target, outcome='outcome_v4_inclusive', year=None):
    x = d[d.eligible & d.core_complete].copy()
    if year is not None: x = x[x.year.eq(year)].copy()
    if target == 'government_vs_opposition':
        x = x[x[outcome].isin([0, 1, 2])].copy(); x['y'] = x[outcome].eq(0).astype(int)
    elif target == 'opposition_type':
        x = x[x[outcome].isin([1, 2])].copy(); x['y'] = x[outcome].eq(2).astype(int)
    elif target == 'nonvote_vs_vote':
        x = x[x.reported_voted | x.reported_nonvote].copy(); x['y'] = x.reported_nonvote.astype(int)
    elif target == 'four_outcomes':
        x = x[x[outcome].ge(0)].copy(); x['y'] = x[outcome].astype(int)
    else: raise ValueError(target)
    return x


def normalized_weights(x, column='weight'):
    return x[column] / x.groupby('year')[column].transform('sum') * (len(x) / x.year.nunique())


def main():
    crosswalk, cabinets = make_crosswalk()
    crosswalk.to_csv(OUT / 'gles_party_crosswalk.csv', index=False)
    cabinets.to_csv(OUT / 'gles_incumbent_cabinets.csv', index=False)
    d, routing = load_data()
    counts, selection = [], []
    for year in ELECTIONS:
        pre = d[d.year.eq(year)]
        selection.append({'year': year, 'parent_n': len(pre), 'eligible_pre_n': int(pre.eligible.sum()),
                          'core_eligible_pre_n': int((pre.eligible & pre.core_complete).sum())})
        for version, rule in [('4', 'inclusive'), ('4', 'strict'), ('3', 'inclusive'), ('3', 'strict')]:
            for target in TARGETS:
                x = analytic_sample(d, target, f'outcome_v{version}_{rule}', year)
                for k, n in x.y.value_counts().sort_index().items():
                    counts.append({'year': year, 'version': version, 'rule': rule, 'target': target,
                                   'n': len(x), 'outcome': int(k), 'outcome_n': int(n)})
    pd.DataFrame(counts).to_csv(OUT / 'gles_locked_sample_counts.csv', index=False)
    pd.DataFrame(selection).to_csv(OUT / 'gles_locked_selection_counts.csv', index=False)
    (OUT / 'gles_outcome_routing.json').write_text(json.dumps(routing, indent=2) + '\n')
    paths = [Path(__file__), ROOT / 'analysis/46_gles_panel_audit.py', ROOT / 'analysis/47_party_classification_audit.py',
             ROOT / 'analysis/61_gles_measurement_harmonization.py', ROOT / 'planning/analysis-protocol-v1.md',
             ROOT / 'planning/gles-analysis-lock.md', OUT / 'gles_party_crosswalk.csv', OUT / 'gles_locked_sample_counts.csv']
    manifest = json.loads((AUDIT / 'authenticated_downloads.json').read_text())
    paths += [ROOT / e['local_path'] for e in manifest['files'] if e['filename'] in [v['file'] for v in ELECTIONS.values()]]
    config = {'fixed_input_hashes': {str(p.relative_to(ROOT)): digest(p) for p in paths},
              'sample_totals': {f"{r['year']}:{r['target']}": r['n'] for r in counts if r['version'] == '4' and r['rule'] == 'inclusive'},
              'blocks': BLOCKS, 'contrasts': CONTRASTS, 'numeric_controls': CONTROLS, 'categorical_controls': CATEGORICAL,
              'seed': 20261106, 'main_regularization_C': 1., 'bootstrap_respondent_draws': 1000,
              'classification_warning': 'The Left is a borderline populist case; strict excludes it in both years. AfD exists only in 2013.',
              'cross_year_person_link': 'lfdn is only unique within a parent file; use ZA5757 designed linkage for cross-year analysis',
              'microdata_exported': False}
    (OUT / 'gles_input_contract.json').write_text(json.dumps(config, indent=2) + '\n')
    print(pd.DataFrame(selection).to_string(index=False))
    print(pd.DataFrame(counts).query("version == '4'").to_string(index=False))


if __name__ == '__main__':
    main()
