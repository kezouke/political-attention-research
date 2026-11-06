"""Availability in the open EES 2009 deposit, with explicit construct boundaries."""
from pathlib import Path
import hashlib
import json
import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/audit_20261106'
OUT = ROOT / 'data/processed/audit_20261106'
SPECS = {
    'q1': ('first_national_problem', 'issue'),
    'q4': ('party_best_on_first_problem', 'party_or_none'),
    'q25': ('ep_named_party_vote', 'party'),
    'q27': ('recalled_last_national_named_party_vote', 'party'),
    'q28': ('hypothetical_national_named_party_intention', 'party'),
    'q29': ('national_government_economic_responsibility', list(range(11))),
    'q30': ('eu_economic_responsibility', list(range(11))),
    'q41': ('trust_eu_institutions', list(range(1, 6))),
    'q44': ('national_parliament_responsiveness', list(range(1, 6))),
    'q48': ('national_economy_retrospective', list(range(1, 6))),
    'q68': ('national_government_policy_economic_effect', [1, 2, 3]),
    'q84': ('satisfaction_national_democracy', [1, 2, 3, 4]),
    'q86': ('national_government_approval', [1, 2]),
}


def main():
    path = RAW / 'ees_2009_voter_data.sav'
    manifest = json.loads((OUT / 'acquisition_manifest.json').read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest['ees_2009_voter_data']['sha256']
    d, m = pyreadstat.read_sav(path, apply_value_formats=False)
    assert len(d) == 27069 and d.t100.is_unique
    assert d.t102.nunique() == 27
    date_parts = d[['t300', 't301', 't302']].rename(
        columns={'t300': 'year', 't301': 'month', 't302': 'day'})
    assert date_parts.day.isin(list(range(1, 32)) + [88]).all()
    dates = pd.to_datetime(date_parts.assign(day=date_parts.day.replace(88, float('nan'))), errors='coerce')
    assert dates.isna().sum() == d.t302.eq(88).sum()
    masks = {}
    for var, (concept, codes) in SPECS.items():
        if isinstance(codes, str):
            labels = m.variable_value_labels[var]
            if codes == 'issue':
                codes = [x for x in labels if x < 7700]
            else:
                codes = [x for x in labels if 1000000 <= x < 9000000]
                if SPECS[var][1] == 'party_or_none':
                    codes += [66]
        masks[var] = d[var].isin(codes)
    rows, joint = [], []
    for country, g in d.groupby('t102'):
        name = m.variable_value_labels['t102'][country]
        for var, (concept, _) in SPECS.items():
            rows.append({'country': name, 'country_code': int(country), 'variable': var,
                         'concept': concept, 'n': len(g),
                         'valid_n': int(masks[var].loc[g.index].sum())})
        common = pd.concat([masks[v] for v in ['q1', 'q48', 'q44', 'q86']], axis=1).all(axis=1)
        joint.append({'country': name, 'n': len(g),
                      'fieldwork_start': dates.loc[g.index].min().date().isoformat(),
                      'fieldwork_end': dates.loc[g.index].max().date().isoformat(),
                      'joint_economy_priority_responsiveness_govapproval_ep_vote':
                          int((common & masks['q25']).loc[g.index].sum()),
                      'joint_economy_priority_responsiveness_govapproval_national_intention':
                          int((common & masks['q28']).loc[g.index].sum()),
                      'joint_direct_national_elite_trust': 0,
                      'n_positive_sample_weight': int(g.v100.gt(0).sum()),
                      'n_unknown_interview_day': int(dates.loc[g.index].isna().sum()),
                      'n_face_to_face': int(g.t200.eq(1).sum())})
    pd.DataFrame(rows).to_csv(OUT / 'ees_2009_variable_coverage.csv', index=False)
    pd.DataFrame(joint).to_csv(OUT / 'ees_2009_joint_coverage.csv', index=False)
    pd.DataFrame([{'variable': v, 'label': label} for v, label in m.column_names_to_labels.items()]).to_csv(
        OUT / 'ees_2009_variable_inventory.csv', index=False)
    (OUT / 'ees_2009_value_labels.json').write_text(json.dumps(
        {v: m.variable_value_labels.get(v, {}) for v in [*SPECS, 't102', 't200']},
        ensure_ascii=False, indent=2) + '\n')
    summary = {
        'deposit_doi': '10.5255/UKDA-SN-852634', 'license': 'CC BY 4.0',
        'filename': path.name, 'n': len(d), 'countries': len(joint),
        'n_joint_ep_vote': sum(x['joint_economy_priority_responsiveness_govapproval_ep_vote'] for x in joint),
        'n_joint_national_intention': sum(x['joint_economy_priority_responsiveness_govapproval_national_intention'] for x in joint),
        'cautions': [
            'q44 is national parliamentary responsiveness, not direct national elite trust.',
            'q41 concerns EU institutions, not national political parties.',
            'All interviews follow EP elections; q28 is hypothetical national intention, not a later observed vote.',
            'One 2009 cross-section cannot establish a change caused by the crisis.',
            'EP and national elections must not be substituted in the original crisis calendar.',
            'v131/v132 calibrate to EP vote outcomes; v132 excludes nonvoters through zero weight.',
            'File called ees_2009_questionnaire.pdf in the acquisition log is actually advance release notes; final notes are in ees_2009_release_notes.doc.',
            'Questionnaire text is in separately acquired ees_2009_v7_questionnaire.pdf and national Maltese version.',
            'Primary deposit reports mixed mode in seven states but lists nine in its advance notes; use actual t200 by country.',
        ],
    }
    (OUT / 'ees_2009_audit.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
