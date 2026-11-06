"""Audit GLES timing, selection and joint availability, without fitting vote models.

Designed links supplied by GESIS are used only locally. Export metadata and
aggregate counts, never respondent IDs, rows, dates of birth or open responses.
"""
from pathlib import Path
import hashlib
import json
import re
from types import SimpleNamespace

import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/audit_20261106'


def read_selected(filename):
    manifest = json.loads((OUT / 'authenticated_downloads.json').read_text())
    entry = next(e for e in manifest['files'] if e['filename'] == filename)
    path = ROOT / entry['local_path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']
    _, meta = pyreadstat.read_dta(path, metadataonly=True)
    pattern = re.compile(r'^(lfdn(?:09|13)?|mut09|mut0913|mutant|wkp2009|w\d+[ab]?|wei_.*|gew_[pq].*|'
                         r'kp\d+_(?:datetime|170|180|190b[abc]?|191b[abc]?|200b[abc]?|'
                         r'760|780|800|810|820|730|740[abc]|040[ac]|160[achn]|840_c[1-5]))$')
    cols = [v for v in meta.column_names if pattern.match(v)]
    d, _ = pyreadstat.read_dta(path, usecols=cols)
    assert d.lfdn.is_unique
    return d, meta


def valid_scale(d, variable, n=5):
    return d[variable].isin(range(1, n + 1))


def issue_available(d, meta, wave):
    # The producer can assign several codes to the single most-important answer.
    # This audit checks the first code's availability; no topic crosswalk yet.
    v = f'kp{wave}_840_c1'
    valid = [k for k in meta.variable_value_labels[v] if 1000 <= k <= 5000]
    return d[v].isin(valid)


def named_series(d, meta, variable):
    valid = [code for code in meta.variable_value_labels[variable] if 0 < code < 800]
    return d[variable].where(d[variable].isin(valid)).replace({2: 1, 3: 1})


def outcome(d, meta, year):
    post = 7 if year == 2009 else 14
    election_vote = named_series(d, meta, f'kp{post}_200bb').where(d[f'kp{post}_180'].eq(1))
    if year == 2009:
        # Post-election turnout is asked of everyone in 2009. Do not recover
        # attriters' earlier postal answers until that year's routing is verified.
        postal = pd.DataFrame(index=d.index)
        named = election_vote.notna()
        conflict = pd.Series(False, index=d.index)
        pre_mail = pd.Series(False, index=d.index)
    else:
        # 2013 questionnaire pp.20-22,25-27 skips turnout and ordinary vote
        # when postal voting was already reported in waves 3..6 (global 10..13).
        postal = pd.DataFrame({str(w): named_series(d, meta, f'kp{w}_191bb')
                               .where(d[f'kp{w}_170'].eq(6) if w < 14 else d.kp14_180.eq(6))
                               for w in range(10, 15)})
        all_reports = pd.concat([postal, election_vote.rename('post')], axis=1)
        conflict = all_reports.nunique(axis=1).gt(1)
        pre_mail = d.kp10_170.eq(6)
        named = all_reports.notna().any(axis=1) & ~conflict
    nonvote = d[f'kp{post}_180'].eq(2)
    contradictory_nonvote = nonvote & named
    named &= ~contradictory_nonvote
    nonvote &= ~contradictory_nonvote
    return {'named_vote': named, 'named_vote_or_explicit_nonvote': named | nonvote,
            'post_only_named': election_vote.notna(), 'pre_attitude_already_postal': pre_mail}, {
                'year': year, 'post_only_named_n': int(election_vote.notna().sum()),
                'postal_named_n': int(postal.notna().any(axis=1).sum()) if len(postal.columns) else 0,
                'postal_or_post_conflicts': int(conflict.sum()),
                'named_nonvote_conflicts': int(contradictory_nonvote.sum()),
                'named_n': int(named.sum()), 'explicit_nonvote_n': int(nonvote.sum()),
                'already_postal_at_attitude_wave_n': int(pre_mail.sum()),
            }


def parent_campaign_availability(parent, meta, year):
    """Within-campaign panels include people absent from the 2009/2013 link."""
    if year == 2009:
        rename = {'kp7_200bc': 'kp7_200bb', 'kp7_200b': 'kp7_200ba'}
    else:
        rename = {v: re.sub(r'^kp(\d+)_', lambda x: f'kp{int(x[1]) + 7}_', v)
                  for v in parent if v.startswith('kp')}
    d = parent.rename(columns=rename)
    m = SimpleNamespace(variable_value_labels={rename.get(v, v): x
                                               for v, x in meta.variable_value_labels.items()})
    econ, att = (1, 2) if year == 2009 else (8, 10)
    base = (valid_scale(d, f'kp{econ}_800') & issue_available(d, m, att)
            & valid_scale(d, f'kp{att}_040a') & valid_scale(d, f'kp{att}_040c')
            & d[f'kp{att}_170'].isin(range(1, 6)))
    outcomes, routing = outcome(d, m, year)
    rows = []
    for label in ['named_vote', 'named_vote_or_explicit_nonvote']:
        complete = base & outcomes[label]
        rows.append({'year': year, 'parent_file_n': len(d), 'scenario': label,
                     'pre_attitudes_joint_n': int(base.sum()),
                     'pre_attitudes_and_outcome_n': int(complete.sum()),
                     'plus_government_responsibility_n': int((complete & valid_scale(d, f'kp{econ}_810')).sum())})
    return rows, routing


def main():
    linked, lm = read_selected('ZA5757_v1-1-0.dta')
    p09, m09 = read_selected('ZA5305_en_v5-0-0.dta')
    p13, m13 = read_selected('ZA5704_en_v3-2-0.dta')
    assert (lm.number_rows, lm.number_columns) == (1025, 5505)
    assert (m09.number_rows, m09.number_columns) == (4552, 3572)
    assert (m13.number_rows, m13.number_columns) == (5256, 2387)
    assert linked.lfdn09.is_unique and linked.lfdn13.is_unique
    assert linked.lfdn09.isin(p09.lfdn).all()
    assert linked.lfdn13.isin(p13.lfdn).all()
    assert p13.loc[p13.lfdn.isin(linked.lfdn13), 'lfdn09'].isin(linked.lfdn09).all()
    pair_check = linked[['lfdn09', 'lfdn13']].merge(p13[['lfdn', 'lfdn09']],
                                                  left_on='lfdn13', right_on='lfdn',
                                                  validate='one_to_one', suffixes=('_l', '_p'))
    assert pair_check.lfdn09_l.equals(pair_check.lfdn09_p)
    campaign_joint, campaign_routing = [], []
    for year, parent, meta in [(2009, p09, m09), (2013, p13, m13)]:
        rows, route = parent_campaign_availability(parent, meta, year)
        campaign_joint.extend(rows)
        campaign_routing.append(route)
    selection, linkage_checks = [], []
    for year, parent, pm, econ, att in [(2009, p09, m09, 1, 2), (2013, p13, m13, 1, 3)]:
        retained = parent.lfdn.isin(linked[f'lfdn{str(year)[-2:]}'])
        specs = {f'kp{econ}_800': 5, f'kp{econ}_810': 5,
                 f'kp{att}_040a': 5, f'kp{att}_040c': 5, f'kp{att}_160a': 5}
        for v, top in specs.items():
            for code in range(1, top + 1):
                eligible = parent[v].eq(code)
                selection.append({'parent_year': year, 'variable': v, 'response_code': code,
                                  'parent_n': int(eligible.sum()),
                                  'linked_n': int((retained & eligible).sum()),
                                  'linked_fraction': float(retained[eligible].mean())})
        # New parent releases can differ from older cumulation. Report actual
        # agreement on valid scales before treating the linkage as interchangeable.
        match = linked.merge(parent, left_on=f'lfdn{str(year)[-2:]}', right_on='lfdn',
                              validate='one_to_one', suffixes=('_l', '_p'))
        for v in specs:
            global_v = re.sub(r'^kp(\d+)_', lambda x: f'kp{int(x[1]) + (7 if year == 2013 else 0)}_', v)
            left = global_v + ('_l' if global_v in parent.columns else '')
            right = v + ('_p' if v in linked.columns else '')
            both = match[left].isin(range(1, 6)) & match[right].isin(range(1, 6))
            linkage_checks.append({'year': year, 'linked_variable': global_v, 'parent_variable': v,
                                   'both_valid_n': int(both.sum()),
                                   'substantive_value_disagreements': int((both & match[left].ne(match[right])).sum()),
                                   'validity_disagreements': int((match[left].isin(range(1, 6)) ^
                                                                match[right].isin(range(1, 6))).sum())})
    coverage, joint, routing = [], [], []
    year_complete = {}
    clean_identity = linked.mut09.eq(0) & linked.mut0913.eq(0)
    for year, econ, att in [(2009, 1, 2), (2013, 8, 10)]:
        masks = {
            'retrospective_national_economy': valid_scale(linked, f'kp{econ}_800'),
            'government_responsibility_for_economy': valid_scale(linked, f'kp{econ}_810'),
            'retrospective_household_economy': valid_scale(linked, f'kp{econ}_760'),
            'most_important_problem': issue_available(linked, lm, att),
            'parties_only_want_votes': valid_scale(linked, f'kp{att}_040a'),
            'politicians_trustworthy_honest': valid_scale(linked, f'kp{att}_040c'),
            'trust_parliament': valid_scale(linked, f'kp{att}_160a'),
            'trust_government': valid_scale(linked, f'kp{att}_160c'),
        }
        if year == 2009:
            masks['trust_parties'] = valid_scale(linked, 'kp2_160h')
            masks['all_three_governing_party_performance'] = pd.concat(
                [valid_scale(linked, f'kp2_740{x}', 11) for x in 'abc'], axis=1).all(axis=1)
        else:
            masks['government_performance'] = valid_scale(linked, 'kp10_730', 11)
        outcomes, route = outcome(linked, lm, year)
        routing.append(route)
        for concept, mask in {**masks, **outcomes}.items():
            coverage.append({'year': year, 'concept': concept, 'linked_total_n': len(linked),
                             'valid_n': int(mask.sum())})
        attitudes = (masks['retrospective_national_economy'] & masks['most_important_problem']
                     & masks['parties_only_want_votes'] & masks['politicians_trustworthy_honest'])
        # In 2013 wave 3 already asks whether the respondent mailed a ballot.
        # Requiring codes 1..5 also removes unknown turnout-status answers.
        pre_vote = linked[f'kp{att}_170'].isin(range(1, 6))
        for label in ['named_vote', 'named_vote_or_explicit_nonvote']:
            complete = attitudes & pre_vote & outcomes[label]
            joint.append({'year': year, 'scenario': label,
                          'joint_economy_priority_two_distrust_items_pre_vote_n': int(complete.sum()),
                          'plus_government_responsibility_n': int((complete & masks['government_responsibility_for_economy']).sum()),
                          'plus_household_economy_n': int((complete & masks['retrospective_household_economy']).sum()),
                          'plus_parliament_and_government_trust_n': int((complete & masks['trust_parliament'] & masks['trust_government']).sum()),
                          'identity_flags_excluded_n': int((complete & clean_identity).sum())})
            year_complete[(year, label)] = complete
    both_years = {}
    for label in ['named_vote', 'named_vote_or_explicit_nonvote']:
        both = year_complete[(2009, label)] & year_complete[(2013, label)]
        responsibility = valid_scale(linked, 'kp1_810') & valid_scale(linked, 'kp8_810')
        both_years[label] = {'joint_both_years_n': int(both.sum()),
                             'identity_flags_excluded_n': int((both & clean_identity).sum()),
                             'plus_both_responsibility_n': int((both & responsibility).sum()),
                             'identity_clean_plus_both_responsibility_n': int((both & responsibility & clean_identity).sum())}
    dates = []
    for w in [1, 2, 7, 8, 10, 14]:
        # Export only wave-level date bounds, no individual timestamps.
        values = pd.to_datetime(linked[f'kp{w}_datetime'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
        assert values.notna().equals(linked[f'w{w}'].eq(1))
        fieldwork = {1: ('2009-07-10', '2009-07-20'), 2: ('2009-07-24', '2009-08-02'),
                     7: ('2009-09-29', '2009-10-07'), 8: ('2013-06-20', '2013-07-07'),
                     10: ('2013-08-01', '2013-08-11'), 14: ('2013-09-24', '2013-10-04')}
        lo, hi = fieldwork[w]
        assert values.dropna().dt.normalize().between(pd.Timestamp(lo), pd.Timestamp(hi)).all()
        dates.append({'global_wave': w, 'date_n': int(values.notna().sum()),
                      'min_date': str(values.min().date()), 'max_date': str(values.max().date())})
    weights = []
    for v in linked:
        if v.startswith('wei_'):
            w = linked.loc[linked[v].gt(0), v]
            weights.append({'variable': v, 'positive_n': len(w), 'min': float(w.min()),
                            'max': float(w.max()), 'kish_n_weight_dispersion_only': float(w.sum() ** 2 / w.pow(2).sum())})
    summary = {
        'studies': ['ZA5305 v5.0.0', 'ZA5704 v3.2.0', 'ZA5757 v1.1.0'],
        'parent_2009_n': len(p09), 'parent_2013_n': len(p13), 'linked_n': len(linked),
        'linked_fraction_of_2009_file': len(linked) / len(p09),
        'parent_2013_has_2009_id_n': int(p13.lfdn09.gt(0).sum()),
        'designed_links_unique_and_matched': True,
        'mut09_flagged_n': int(linked.mut09.ne(0).sum()),
        'mut0913_flagged_n': int(linked.mut0913.ne(0).sum()),
        'both_years_complete': both_years, 'outcome_routing': routing,
        'full_campaign_joint': campaign_joint, 'full_campaign_routing': campaign_routing,
        'wave_dates': dates,
        'limitations': [
            'Quota sample from commercial online access panel, not a probability sample.',
            '2009 begins after the financial crisis; it is not a pre-crisis baseline.',
            '1025/4552 is coverage of the 2009 file, not a response rate: recontact eligibility was selective.',
            'Only 1527 were eligible for recontact; 1030 returned and five identity-inconsistent cases were removed by producer.',
            'Cross-campaign selection is not corrected by within-campaign panel weights.',
            'Economy in wave 1/8 precedes distrust and priority in wave 2/10, but this alone does not identify a causal path.',
            'Both party-interest and politician-honesty items repeat before each election; neither alone establishes populist ideology.',
            'Institutional party trust exists in 2009 but not the 2013 wave-3 battery; parliament trust is a separate institution.',
            'Government performance is party-specific CDU/CSU/SPD in 2009 versus a government scale in 2013; do not silently equate them.',
            '2013 actual postal votes can be reported in pre-election waves and then routed out of post-election turnout/vote questions.',
            'Exclude respondents already reporting a postal vote at the attitude wave; unknown status is excluded in strict joint counts.',
            'The 2009 post-only outcome is conservative; postal responses from later attriters are not recovered without verified routing.',
            'MIP coding availability is checked, but the changing detailed issue-code dictionary still needs a substantive crosswalk.',
            'Election-campaign classification, all governing coalition partners and party supply still need separate verification.',
            'Linked data derive from older parent releases; checked scale agreements are reported, not assumed for every variable.',
        ],
    }
    metadata = [{'variable': v, 'label': lm.column_names_to_labels[v],
                 'value_labels': lm.variable_value_labels.get(v, {})}
                for v in linked if not v.startswith('lfdn') and not v.endswith('datetime')]
    (OUT / 'gles_panel_audit.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')
    (OUT / 'gles_panel_metadata.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + '\n')
    for name, rows in [('coverage', coverage), ('joint', joint), ('selection', selection),
                       ('parent_agreement', linkage_checks), ('weights', weights),
                       ('campaign_joint', campaign_joint)]:
        pd.DataFrame(rows).to_csv(OUT / f'gles_panel_{name}.csv', index=False)
    print(json.dumps({k: summary[k] for k in ['linked_n', 'linked_fraction_of_2009_file',
                                            'both_years_complete', 'outcome_routing', 'wave_dates']}, indent=2))


if __name__ == '__main__':
    main()
