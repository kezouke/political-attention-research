"""Audit Danish election surveys from the National Archives' public downloads.

The archive removes identifying fields and free text. No respondent linkage is
attempted. Counts describe availability, not political effects or power.
"""
from pathlib import Path
import hashlib
import json
import zipfile
import numpy as np
import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/audit_20261106'
OUT = ROOT / 'data/processed/audit_20261106'
R5 = list(range(1, 6))
SPECS = {
    2007: {
        'V81': ('first_political_problem_detailed_coding_pending', 'problem'),
        'V174': ('household_economy_past_three_years', R5),
        'V175': ('national_economy_past_three_years', R5),
        'V182': ('government_economic_performance', R5),
        'V191': ('government_general_performance', R5),
        'V275': ('trust_politicians', [1, 2, 3, 4]),
        'V266': ('politicians_ignore_voters', R5),
        'V270': ('politicians_focus_reelection', R5),
        'V28': ('named_party_vote', [1, 2, 3, 5, 6, 7, 8, 9, 10]),
    },
    2011: {
        'V17': ('first_political_problem_detailed_coding_pending', 'problem'),
        'V18': ('first_political_problem_broad', list(range(1, 9)) + list(range(10, 18))),
        'V145': ('household_economy_past_three_years', R5),
        'V146': ('national_economy_past_three_years', R5),
        'V218': ('trust_politicians', [1, 2, 3, 4]),
        'V211': ('politicians_ignore_voters', R5),
        'V216': ('politicians_focus_reelection', R5),
        'V155': ('precrisis_danish_economic_policy_blame', [1, 2, 3]),
        'V158': ('danish_bank_risk_blame', [1, 2, 3]),
        'V63': ('named_party_vote', list(range(1, 10))),
    },
    2015: {
        'V15': ('first_political_problem_detailed_coding_pending', 'problem'),
        'V137': ('household_economy_past_three_years', R5),
        'V138': ('national_economy_past_three_years', R5),
        'V218': ('trust_politicians', [1, 2, 3, 4]),
        'V211': ('politicians_ignore_voters', R5),
        'V216': ('politicians_focus_reelection', R5),
        'V150': ('previous_government_economy_responsibility', list(range(11))),
        'V51': ('named_party_vote', list(range(1, 11))),
    },
}
EXPECTED = {2007: (4018, 493), 2011: (2078, 375), 2015: (4147, 379)}


def read_source(year, manifest):
    key = f'dnes_{year}_archive'
    path = RAW / f'{key}.zip'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest[key]['sha256']
    with zipfile.ZipFile(path) as z:
        # Extract only the two explicitly selected numeric survey formats.
        members = {}
        for ext in ['sav', 'dta']:
            names = [n for n in z.namelist() if n.lower().endswith('.' + ext)]
            assert len(names) == 1
            target = RAW / f'dnes_{year}.{ext}'
            target.write_bytes(z.read(names[0]))
            members[ext] = {'member': names[0], 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
    d, m = pyreadstat.read_sav(RAW / f'dnes_{year}.sav', user_missing=True)
    dta, _ = pyreadstat.read_dta(RAW / f'dnes_{year}.dta')
    assert d.shape == EXPECTED[year]
    assert len(dta) == len(d)
    # Archive conversions may have already made user-missing values system
    # missing. Compare all substantive observed values of selected fields.
    for v in SPECS[year]:
        a, b = d[v], dta[v]
        common = a.notna() & b.notna()
        assert np.array_equal(a[common].to_numpy(), b[common].to_numpy()), (year, v)
    return d, m, members


def main():
    manifest = json.loads((OUT / 'acquisition_manifest.json').read_text())
    rows, joint, weights, inventories, source_groups = [], [], [], [], []
    summary = {}
    for year in SPECS:
        d, m, members = read_source(year, manifest)
        for v, label in m.column_names_to_labels.items():
            inventories.append({'year': year, 'variable': v, 'label': label})
        masks, labels = {}, {}
        for v, (concept, valid) in SPECS[year].items():
            if valid == 'problem':
                # A detailed-code availability screen, not a topic crosswalk.
                # 1 diffuse; 3 DK; 9 missing; 10 none; 90 nonpolitical;
                # 8888 unlabelled special; 9999/10000 missing/irrelevant.
                mask = (d[v].between(20, 1200) & d[v].ne(90)) | d[v].eq(2)
            else:
                assert set(valid) <= set(m.variable_value_labels[v])
                mask = d[v].isin(valid)
            masks[concept] = mask
            rows.append({'year': year, 'variable': v, 'concept': concept,
                         'n_rows': len(d), 'valid_n': int(mask.sum()),
                         'post_election': True, 'source_label': m.column_names_to_labels[v]})
            labels[v] = m.variable_value_labels.get(v, {})
        # Producer codebooks independently report these substantive counts.
        assert int(masks['national_economy_past_three_years'].sum()) == {2007: 3901, 2011: 1958, 2015: 1935}[year]
        assert int(masks['trust_politicians'].sum()) == {2007: 3969, 2011: 1917, 2015: 1990}[year]
        votevar, nonvote = {2007: ('V28', 15), 2011: ('V63', 12), 2015: ('V51', 13)}[year]
        abstain = d[votevar].eq(nonvote)
        base = masks['national_economy_past_three_years'] & masks[
            'first_political_problem_detailed_coding_pending'] & masks['trust_politicians']
        scenarios = {'all_archive_rows': pd.Series(True, index=d.index)}
        if year == 2007:
            scenarios['excluding_webpanel_source_6'] = d.V4.ne(6)
            for code, group in d.groupby('V4'):
                source_groups.append({'year': year, 'source_code': code,
                                      'source_label': m.variable_value_labels['V4'][code], 'n': len(group)})
        if year == 2015:
            scenarios['producer_complete_interviews'] = d.V3.eq(1)
            assert scenarios['producer_complete_interviews'].sum() == 2001
        wvar = {2007: 'V523', 2011: 'V388', 2015: 'V389'}[year]
        for scenario, eligible in scenarios.items():
            named = base & masks['named_party_vote'] & eligible
            with_nonvote = base & (masks['named_party_vote'] | abstain) & eligible
            joint.append({'year': year, 'scenario': scenario,
                          'eligible_n': int(eligible.sum()),
                          'economy_priority_trust_named_vote_n': int(named.sum()),
                          'economy_priority_trust_named_vote_or_abstention_n': int(with_nonvote.sum()),
                          'same_with_positive_demographic_weight_n': int((with_nonvote & d[wvar].gt(0)).sum()),
                          'all_three_measured_before_vote': False,
                          'comparable_government_approval_across_years_verified': False})
        weightvars = [v for v, label in m.column_names_to_labels.items()
                      if 'WEIGHT' in (label or '') or 'WEIGTH' in (label or '')]
        for v in weightvars:
            w = d[v]; w = w[w.gt(0)]
            weights.append({'year': year, 'variable': v, 'label': m.column_names_to_labels[v],
                            'positive_n': len(w), 'min': w.min(), 'max': w.max(),
                            'kish_n_weight_dispersion_only': w.sum()**2 / w.pow(2).sum()})
        summary[str(year)] = {'n_rows': len(d), 'n_columns': len(d.columns),
                              'source_members': members, 'selected_labels': labels}
    summary['limitations'] = [
        'All three surveys are post-election repeated cross-sections. No cross-election respondent linkage.',
        'Economy question labels say today, but full wording compares today with three years earlier in all three surveys.',
        'A three-year retrospective economy item is not automatically comparable to a twelve-month item in another country.',
        'Direct politician trust repeats four substantive response levels across years.',
        'Detailed priority coding remains to be harmonised; availability screen excludes diffuse, nonpolitical and special responses.',
        '2007 combines probability-sample collection modes and a separate web panel (2576 of 4018 rows). Pooling needs sensitivity checks.',
        '2011 report states 2076 respondents, while downloaded archive file has 2078. Counts here follow the pinned file.',
        '2015 archive includes 4147 rows but only 2001 producer-flagged complete interviews with survey weights.',
        'Government performance in 2007, policy blame in 2011 and responsibility in 2015 are different constructs.',
        '2007 V521 abbreviated label omits education and party choice; weight note and its numerical range identify the vote-calibrated weight.',
        'Do not validate party shares with weights calibrated to those shares.',
        'Public archive has removed identifying fields and free text. No raw microdata redistributed.',
    ]
    for name, data in [('dnes_variable_coverage', rows), ('dnes_joint_coverage', joint),
                       ('dnes_weights', weights), ('dnes_inventory', inventories),
                       ('dnes_source_composition', source_groups)]:
        pd.DataFrame(data).to_csv(OUT / f'{name}.csv', index=False)
    (OUT / 'dnes_audit.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(pd.DataFrame(joint).to_string(index=False))


if __name__ == '__main__':
    main()
