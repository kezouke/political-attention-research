"""Audit an author-deposited CNEP replication, not the entire CNEP archive."""
from pathlib import Path
import hashlib
import json
import re
import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/audit_20261106'
OUT = ROOT / 'data/processed/audit_20261106'
SELECTED = {
    'A_EconSit': ('national_economy_CURRENT_OR_CHANGE_mixed', list(range(1, 6))),
    'A_RespSit': ('personal_economy_CURRENT_OR_CHANGE_mixed', list(range(1, 6))),
    'A_GovPerf': ('government_performance', list(range(1, 6))),
    'B_DontCare': ('politicians_do_not_care', list(range(1, 6))),
    'B_PolsDefendRich': ('politicians_defend_rich', list(range(1, 6))),
    'B_OfficialsListen': ('officials_listen', list(range(1, 6))),
    'B_TrustGov': ('trust_government_NOT_general_elite', list(range(1, 5))),
    'B_DemSat': ('democracy_satisfaction_NOT_elite_trust', list(range(4))),
    'H_VoteWhichRecent': ('party_slot_vote_mapping_pending',
                         list(range(1, 7)) + list(range(10, 17)) + list(range(20, 25))),
}
# Producer country labels, not country-year abbreviation guesses. IR16 is Iran,
# UK19 is Ukraine. Keep geographic Europe separate from the crisis core.
EUROPE = {2, 5, 6, 8, 10, 14, 16, 18, 24, 26, 27, 28}


def main():
    path = RAW / 'cnep_replication_merge57.dta'
    manifest = json.loads((OUT / 'acquisition_manifest.json').read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest['cnep_replication_merge57']['sha256']
    d, m = pyreadstat.read_dta(path)
    assert d.shape == (99401, 539)
    inventory = pd.DataFrame([{'variable': v, 'label': l} for v, l in m.column_names_to_labels.items()])
    inventory.to_csv(OUT / 'cnep_replication_inventory.csv', index=False)
    priority_candidates = inventory[inventory.label.fillna('').str.contains(
        'priorit|salien|important|problem', case=False)]
    # Manual review of these labels: organisations or policy positions, no MIP.
    assert set(priority_candidates.variable) == {'F_Aso1', 'F_Aso2', 'F_Aso3', 'J_Climate', 'J_TimeResolves_F'}
    coverage, studies, joint = [], [], []
    for cy, g in d.groupby('A_A_CountryYear'):
        assert g.A_A_Country.nunique() == 1
        country = int(g.A_A_Country.iloc[0])
        country_label = m.variable_value_labels['A_A_Country'][country]
        study_label = m.variable_value_labels['A_A_CountryYear'][int(cy)]
        suffix = re.search(r'([0-9]{2})$', study_label).group(1)
        year = 2000 + int(suffix) if int(suffix) <= 30 else 1900 + int(suffix)
        relevant = country in EUROPE and 2004 <= year <= 2019
        base = {'study': study_label, 'country': country_label, 'year': year,
                'geographic_europe_2004_2019': relevant, 'n': len(g)}
        studies.append(base)
        masks = {}
        for v, (concept, valid) in SELECTED.items():
            s = g[v]
            masks[v] = s.isin(valid)
            coverage.append({**base, 'variable': v, 'concept': concept,
                             'valid_n': int(masks[v].sum()),
                             'explicit_not_asked_n': int(s.eq(-999).sum()),
                             'system_missing_n': int(s.isna().sum())})
        cols = ['A_EconSit', 'A_GovPerf', 'B_DontCare', 'H_VoteWhichRecent']
        joint.append({**base, 'economy_government_dont_care_vote_n': int(
            pd.concat([masks[v] for v in cols], axis=1).all(axis=1).sum()),
            'economy_priority_elite_vote_n': 0,
            'reason_for_zero': 'No respondent issue-priority question in this replication file'})
    for name, rows in [('cnep_replication_studies', studies),
                       ('cnep_replication_coverage', coverage),
                       ('cnep_replication_joint', joint)]:
        pd.DataFrame(rows).to_csv(OUT / f'{name}.csv', index=False)
    summary = {
        'source': 'https://osf.io/d6jvw/',
        'n': len(d), 'columns': len(d.columns),
        'observed_studies': len(studies), 'observed_countries': int(d.A_A_Country.nunique()),
        'geographic_europe_2004_2019_studies': int(sum(x['geographic_europe_2004_2019'] for x in studies)),
        'selected_labels': {v: m.variable_value_labels[v] for v in SELECTED},
        'limitations': [
            'This is a published author replication, not the full current CNEP archive or national extensions.',
            'A_EconSit and A_RespSit pool current condition and retrospective change. National questionnaires needed before treating them as comparable.',
            'H_Turnout code 0 combines no and do-not-know; it is not verified abstention.',
            'H_VoteWhichRecent has country-specific government/opposition slots. Party names and incumbent timing require source mapping.',
            'No issue-priority variable found. Joint test of all three explanations is structurally unavailable here.',
            'Existing author filter__ and r-prefixed derived measures are not automatically applied.',
            'OSF node is public but node_license is null. No blanket raw-data redistribution licence inferred.',
            'Country-year shorthand IR16 means Iran; UK19 means Ukraine, not Ireland or Britain.',
        ],
    }
    (OUT / 'cnep_replication_audit.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    out = pd.DataFrame(joint)
    print(out[out.geographic_europe_2004_2019].drop(columns=['reason_for_zero']).to_string(index=False))


if __name__ == '__main__':
    main()
