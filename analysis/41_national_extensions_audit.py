"""Availability audit of Portuguese and Icelandic national election extensions.

No political associations are estimated. All outputs are metadata or aggregate
coverage counts. Keep source microdata and respondent answers out of Git.
"""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/audit_20261106'
OUT = ROOT / 'data/processed/audit_20261106'
R5, R4 = list(range(1, 6)), list(range(1, 5))
FILES = {
    'pes_2005': (9263, 2801, None), 'pes_2009': (9273, 1317, 'QUEST'),
    'pes_2011': (9279, 1000, 'INTNR'),
    'icenes_2007': (163, 1595, 'User_id'),
    'icenes_2009': (172, 1385, 'User_Id'),
    'icenes_2013': (179, 1479, 'User_Id'),
}
# Keep national problems and personal election priorities distinct.
SPECS = {
    'pes_2005': {
        'p1': ('national_problem_past_three_years', 'pes2005_problem'),
        'p60': ('current_national_economy', R5),
        'p61': ('retrospective_national_economy', R5),
        'p12.3': ('politicians_do_not_care', R5),
        'p68': ('extent_political_corruption', R4),
        'p4': ('government_performance_barroso', R4),
        'p5': ('government_performance_santana', R4),
        'p25': ('named_party_vote', R5),
        'p24': ('turnout', [1, 2]),
    },
    'pes_2009': {
        'P1': ('personal_election_priority', 'pes_later_problem'),
        'P3': ('current_national_problem', 'pes_later_problem'),
        'P68': ('current_national_economy', R5),
        'P69': ('retrospective_national_economy', R5),
        'P11_5': ('politicians_do_not_care', R5),
        'P36': ('government_economic_performance', R4),
        'P28': ('named_party_vote', list(range(1, 6)) + list(range(8, 21))),
        'P27': ('turnout', [1, 2]),
    },
    'pes_2011': {
        'P1': ('personal_election_priority', 'pes_later_problem'),
        'P2': ('current_national_economy', R5),
        'P3': ('retrospective_national_economy', R5),
        'P7_1': ('government_responsibility_for_economy', R5),
        'P16': ('democracy_satisfaction_NOT_elite_trust', R4),
        'P26': ('named_party_vote', list(range(1, 13))),
        'P25': ('turnout', R4),
        **{f'P9_{i}': (concept, [1, 2]) for i, concept in enumerate([
            'household_job_loss_since_2009', 'household_wage_freeze_since_2009',
            'household_wage_cut_since_2009', 'household_hours_cut_since_2009'], 1)},
    },
}
for year in [2007, 2009, 2013]:
    suffix = str(year)[2:]
    s = {
        'pltrust': ('trust_politicians', R5),
        f'issue1{year}': ('personal_election_priority', 'iceland_problem'),
        f'task1{year}': ('current_national_problem', 'iceland_problem'),
        f'prtvote{suffix}': ('named_party_vote',
                            list(range(1, 7)) if year == 2007 else
                            list(range(1, 8)) if year == 2009 else
                            list(range(1, 15))),
        f'vote{suffix}': ('turnout', [1, 2]),
    }
    # The 2013 DDI has no categories 9 or 11 for actual votes. Exclude absent
    # categories explicitly instead of importing party labels from intention.
    if year == 2013:
        s[f'prtvote{suffix}'] = ('named_party_vote', [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 13, 14])
    gov = {2007: 'govprfm', 2009: 'govprfmGHH', 2013: 'govprfmJS'}[year]
    s[gov] = ('government_performance', R4)
    if year == 2009:
        s['govprfmJH'] = ('government_performance_interim_2009', R4)
    if year in [2009, 2013]:
        for actor in ['G_GHH', 'bnk', 'CB', 'FME']:
            s[f'bnkclsfault_{actor}'] = (f'crisis_responsibility_{actor}', list(range(11)))
    if year == 2013:
        s['ecobettwors'] = ('retrospective_national_economy', [1, 3, 5])
        s['govprfmcris'] = ('government_crisis_recovery_performance', R5)
    SPECS[f'icenes_{year}'] = s


def read_ddi(path):
    variables = {}
    for var in ET.parse(path).getroot().findall('.//{*}var'):
        cats = {}
        for c in var.findall('{*}catgry'):
            val = float(c.findtext('{*}catValu'))
            frequency = c.findtext('{*}catStat')
            cats[val] = {'label': c.findtext('{*}labl'),
                         'n': int(float(frequency)) if frequency is not None else None}
        variables[var.attrib['name']] = {'label': var.findtext('{*}labl'), 'categories': cats}
    return variables


def main():
    manifest = json.loads((OUT / 'acquisition_manifest.json').read_text())
    coverage, joint, inventory, weight_rows = [], [], [], []
    summary = {}
    for stem, (fileid, expected_n, idvar) in FILES.items():
        path = RAW / f'{stem}_file_{fileid}.tab'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest[f'{stem}_file_{fileid}']['sha256']
        d = pd.read_csv(path, sep='\t', low_memory=False, na_values=['.'])
        assert len(d) == expected_n
        if idvar:
            assert d[idvar].notna().all(), stem
            if stem != 'pes_2009':
                assert d[idvar].is_unique, stem
            else:
                assert d[idvar].nunique() == 1315
        meta = read_ddi(RAW / f'{stem}_ddi.xml')
        assert set(meta) == set(d.columns), stem
        for v, info in meta.items():
            inventory.append({'dataset': stem, 'variable': v, 'label': info['label']})
        masks, selected = {}, {}
        for v, (concept, valid) in SPECS[stem].items():
            s = pd.to_numeric(d[v], errors='raise')
            cats = meta[v]['categories']
            for code, c in cats.items():
                if c['n'] is not None:
                    assert int(s.eq(code).sum()) == c['n'], (stem, v, code)
            if valid == 'pes2005_problem':
                # 99 is "do not know", 999 is refusal. Keep 98 "other topic".
                valid = [code for code in cats if 0 < code < 99]
            elif valid == 'pes_later_problem':
                valid = [code for code in cats if 0 < code < 97]
            elif valid == 'iceland_problem':
                valid = [code for code in cats if 0 < code <= 90 and code != 89]
            assert set(valid) <= set(cats), (stem, v, set(valid) - set(cats))
            masks[concept] = s.isin(valid)
            coverage.append({'dataset': stem, 'variable': v, 'concept': concept,
                             'timing': 'post_national_election', 'n': len(d),
                             'valid_n': int(masks[concept].sum()), 'label': meta[v]['label']})
            selected[v] = {'concept': concept, 'valid_codes': valid, 'categories': cats}
        sets = {}
        if stem.startswith('icenes'):
            sets['government_personal_priority_trust_named_vote'] = [
                'government_performance', 'personal_election_priority', 'trust_politicians', 'named_party_vote']
            sets['government_national_problem_trust_named_vote'] = [
                'government_performance', 'current_national_problem', 'trust_politicians', 'named_party_vote']
            if stem != 'icenes_2007':
                sets['government_and_bank_blame_personal_priority_trust_named_vote'] = [
                    'crisis_responsibility_G_GHH', 'crisis_responsibility_bnk',
                    'personal_election_priority', 'trust_politicians', 'named_party_vote']
            if stem == 'icenes_2013':
                sets['retrospective_economy_personal_priority_trust_government_named_vote'] = [
                    'retrospective_national_economy', 'personal_election_priority',
                    'trust_politicians', 'government_performance', 'named_party_vote']
            abstain = d[f'vote{stem[-2:]}'].eq(2)
        else:
            priority = 'national_problem_past_three_years' if stem == 'pes_2005' else 'personal_election_priority'
            if stem != 'pes_2011':
                sets['economy_priority_politicians_dont_care_named_vote'] = [
                    'retrospective_national_economy', priority, 'politicians_do_not_care', 'named_party_vote']
                gov = 'government_performance_santana' if stem == 'pes_2005' else 'government_economic_performance'
                sets['economy_priority_politicians_dont_care_government_named_vote'] = sets[
                    'economy_priority_politicians_dont_care_named_vote'] + [gov]
                if stem == 'pes_2009':
                    sets['economy_national_problem_politicians_dont_care_named_vote'] = [
                        'retrospective_national_economy', 'current_national_problem',
                        'politicians_do_not_care', 'named_party_vote']
            else:
                sets['economy_priority_democracy_satisfaction_named_vote_NOT_elite_trust'] = [
                    'retrospective_national_economy', priority,
                    'democracy_satisfaction_NOT_elite_trust', 'named_party_vote']
                sets['household_job_loss_priority_government_blame_named_vote'] = [
                    'household_job_loss_since_2009', priority,
                    'government_responsibility_for_economy', 'named_party_vote']
            abstain = d[{'pes_2005': 'p24', 'pes_2009': 'P27', 'pes_2011': 'P25'}[stem]].isin(
                [1, 2, 3] if stem == 'pes_2011' else [2])
        # Non-voters are observed through their turnout answer, not missing party.
        assert not (abstain & masks['named_party_vote']).any(), stem
        for name, concepts in sets.items():
            predictors = pd.concat([masks[c] for c in concepts if c != 'named_party_vote'], axis=1).all(axis=1)
            joint.append({'dataset': stem, 'comparison': name,
                          'named_vote_n': int((predictors & masks['named_party_vote']).sum()),
                          'named_vote_or_abstention_n': int((predictors & (masks['named_party_vote'] | abstain)).sum()),
                          'all_predictors_before_vote': False, 'cross_election_panel_verified': False})
        weightvars = []
        for v, info in meta.items():
            if not (v.lower().startswith(('pond', 'pons', 'wgt', 'weight')) or
                    'ponderador' in (info['label'] or '').lower()):
                continue
            w = pd.to_numeric(d[v], errors='raise')
            w = w[w.gt(0)]
            weightvars.append(v)
            weight_rows.append({'dataset': stem, 'variable': v, 'label': info['label'],
                                'n_positive': len(w), 'min': w.min(), 'max': w.max()})
        summary[stem] = {'n': len(d), 'n_columns': len(d.columns),
                         'id_unique_checked': idvar is not None, 'id_variable': idvar,
                         'id_is_unique': bool(d[idvar].is_unique) if idvar else None,
                         'id_distinct_values': int(d[idvar].nunique()) if idvar else None,
                         'weight_variables_found': weightvars,
                         'joint_all_three_before_vote': 0, 'selected_variables': selected}
    summary['limitations'] = [
        'All six surveys measure audited attitudes after their national election.',
        'Portugal 2005 asks about the national problem over three years; 2009/2011 personal election priority is a different question.',
        'Portugal 2005 and 2009 reverse the codes for economic evaluations and politicians not caring.',
        'Portugal 2011 has economic hardship but no direct politician trust or do-not-care item found in the audited questionnaire.',
        'Iceland 2007 and 2009 have government performance but no neutral retrospective economy item found.',
        'Iceland 2009 asks separately about two successive governments; never label both as one incumbent.',
        'Iceland 2013 collapses problem categories relative to 2007/2009; recoding requires a documented crosswalk.',
        'Iceland files have no survey weights found; the 2007 producer report explicitly says no weights are included.',
        'No respondent linkage across election years is established. Local IDs do not establish a panel.',
        'Portugal 2009 QUEST is not unique: 1315 distinct values for 1317 rows. Do not deduplicate or link rows using it alone.',
        'Named party codes are survey answers, not yet verified official party mappings or populism labels.',
        'Iceland microdata have custom research terms, not the CC BY licence applying to documentation. No raw redistribution; retention and archive obligations recorded separately.',
    ]
    for name, rows in [('national_extensions_variable_coverage', coverage),
                       ('national_extensions_joint_coverage', joint),
                       ('national_extensions_inventory', inventory),
                       ('national_extensions_weights', weight_rows)]:
        # DDI labels sometimes end in padding spaces; omit padding in CSVs.
        pd.DataFrame(rows).map(lambda x: x.rstrip() if isinstance(x, str) else x).to_csv(
            OUT / f'{name}.csv', index=False)
    (OUT / 'national_extensions_audit.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(pd.DataFrame(joint).to_string(index=False))


if __name__ == '__main__':
    main()
