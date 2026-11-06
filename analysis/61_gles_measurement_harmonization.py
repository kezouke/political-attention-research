"""Harmonize GLES problem codes and check pre-election controls, no models."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import numpy as np
import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/audit_20261106'
spec = importlib.util.spec_from_file_location('panel', ROOT / 'analysis/46_gles_panel_audit.py')
panel = importlib.util.module_from_spec(spec); spec.loader.exec_module(panel)


def problem_group(code, year):
    if code in ({4020, 4021} if year == 2009 else {4330, 4331, 4332, 4333}):
        return 'euro_currency'
    if code == 3521 or 3800 <= code <= 4099:
        return 'domestic_economy_labour_prices'
    if 4300 <= code <= 4399:
        return 'public_finance_tax'
    if 3720 <= code <= 3725:
        return 'distribution_poverty_security'
    if 3750 <= code <= 3759:
        return 'immigration'
    if 3600 <= code <= 3699:
        return 'environment_climate'
    if 3520 <= code <= 3529:
        return 'energy_other_than_prices'
    if code in ({3416, 3417, 3418} if year == 2009 else {3417, 3418, 3419}):
        return 'corruption'
    return 'other_substantive'


def main():
    problems, controls, metadata, summaries = [], [], [], []
    manifest = json.loads((OUT / 'authenticated_downloads.json').read_text())
    for year, fn, att in [(2009, 'ZA5305_en_v5-0-0.dta', 2), (2013, 'ZA5704_en_v3-2-0.dta', 3)]:
        d, meta = panel.read_selected(fn)
        rec = next(e for e in manifest['files'] if e['filename'] == fn)
        path = ROOT / rec['local_path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == rec['sha256']
        mapping = ({'age': 'kp1_2290a', 'gender': 'kp1_2280', 'education': 'kp1_2320',
                    'employment': 'kp1_2340', 'left_right': 'kp1_1500',
                    'party_identity': 'kp1_2090ac', 'party_identity_strength': 'kp1_2100',
                    'pre_intention': 'kp2_190bc', 'region_archival': 'fedstate', 'settlement_pre': 'kp2_2600'}
                   if year == 2009 else
                   {'birth_year_for_local_age_derivation': 'kpx_2290', 'gender': 'kpx_2280', 'education': 'kpx_2320',
                    'employment': 'kpx_2340', 'left_right': 'kp1_1500',
                    'party_identity': 'kp1_2090b', 'party_identity_strength': 'kp1_2100',
                    'pre_intention': 'kp3_190bb', 'region_pre': 'kpx_2601', 'settlement_pre': 'kpx_2600'})
        additional = ['lfdn'] + [v for v in mapping.values() if v not in d]
        extra, _ = pyreadstat.read_dta(path, usecols=additional)
        d = d.merge(extra, on='lfdn', validate='one_to_one')
        issue = f'kp{att}_840_c1'
        labels = meta.variable_value_labels[issue]
        issue_map = {int(k): problem_group(int(k), year) for k in labels if 1000 <= k <= 5000}
        for code, group in issue_map.items():
            problems.append({'year': year, 'variable': issue, 'code': code, 'label': labels[code],
                             'topic_group': group,
                             'economic_domestic_primary_candidate': group == 'domestic_economy_labour_prices',
                             'economic_broad_sensitivity_candidate': group in ['domestic_economy_labour_prices',
                                                                              'euro_currency', 'public_finance_tax',
                                                                              'distribution_poverty_security']})
        # The code is reused with a different substantive meaning across years.
        assert issue_map[3911] == 'domestic_economy_labour_prices'
        assert issue_map[4020 if year == 2009 else 4331] == 'euro_currency'
        base = (d.kp1_800.between(1, 5) & d[issue].isin(issue_map)
                & d[f'kp{att}_040a'].between(1, 5) & d[f'kp{att}_040c'].between(1, 5)
                & d[f'kp{att}_170'].between(1, 5))
        clean = d['mutant' if year == 2009 else 'mut09'].eq(0)
        gov_trust = d[f'kp{att}_160c'].between(1, 5)
        mask = base & clean & gov_trust
        age = d[mapping['age']] if year == 2009 else year - d[mapping['birth_year_for_local_age_derivation']]
        requirements = {'age': age.between(18, 100), 'gender': d[mapping['gender']].isin([1, 2]),
                        'education': d[mapping['education']].isin([1, 2, 3, 4, 5, 6 if year == 2009 else 9]),
                        'employment': d[mapping['employment']].between(1, 14 if year == 2009 else 12),
                        'left_right': d[mapping['left_right']].between(1, 11),
                        'party_identity_nonmissing_code': d[mapping['party_identity']].gt(0),
                        'pre_intention_named_code': d[mapping['pre_intention']].between(1, 799)}
        for name, valid in requirements.items():
            controls.append({'year': year, 'concept': name, 'core_before_controls_n': int(mask.sum()),
                             'valid_n': int((mask & valid).sum()),
                             'valid_fraction': float(valid[mask].mean())})
        for concept, v in mapping.items():
            vals = meta.variable_value_labels.get(v, {})
            # No birth-date/year observations or identifiers are exported.
            metadata.append({'year': year, 'concept': concept, 'variable': v,
                             'label': meta.column_names_to_labels.get(v),
                             'value_labels': {} if 'birth' in concept or concept == 'age' else vals})
        summaries.append({'year': year, 'parent_n': len(d), 'core_economy_priority_two_distrust_n': int(base.sum()),
                          'plus_clean_identity_n': int((base & clean).sum()),
                          'plus_government_trust_n': int(mask.sum()),
                          'plus_valid_age_n': int((mask & requirements['age']).sum()),
                          'already_postal_at_attitude_wave_n': int(d[f'kp{att}_170'].eq(6).sum()),
                          'age_2013_is_year_based_approximation': year == 2013})
    pd.DataFrame(problems).to_csv(OUT / 'gles_problem_topic_crosswalk.csv', index=False)
    pd.DataFrame(controls).to_csv(OUT / 'gles_pre_control_availability.csv', index=False)
    pd.DataFrame(summaries).to_csv(OUT / 'gles_pre_measurement_summary.csv', index=False)
    (OUT / 'gles_pre_control_metadata.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + '\n')
    report = {
        'vote_models_fitted': False, 'raw_records_or_identifiers_exported': False,
        'problem_code_warning': 'Euro codes move from 4020/4021 in 2009 to 4331 etc. in 2013; same numeric range is not invariant meaning',
        'corruption_code_warning': 'Corruption codes shift from 3416..3418 to 3417..3419; retained separately',
        'economic_primary_candidate': 'Domestic economy, labour and energy prices; currency/Euro, public finance and redistribution kept separate',
        'first_code_only': 'The producer may assign multiple codes to one most-important-problem answer; any-code variant remains required',
        'government_measure': 'Government trust 1..5 exists in both years; 2009 party performance and 2013 whole-government performance are distinct alternatives',
        'left_right_scale': '1..11 in both parent files; not the 7/11 split used for separate policy positions',
        'demographics_2013': 'Questionnaire identifies gender/year of birth, education, employment and federal state as wave1 items renamed kpx because treated as time invariant',
        'dependent_interviewing': 'Some other variables stored under an early wave include later answers; measurement flags must be used for any such extra controls',
        'region_2009': 'Archived fedstate timing still needs verification before use as a strictly pre-election predictor',
        'method_documents': ['https://access.gesis.org/dbk/59599', 'https://access.gesis.org/dbk/59597'],
    }
    (OUT / 'gles_measurement_harmonization.json').write_text(json.dumps(report, indent=2) + '\n')
    print(pd.DataFrame(summaries).to_string(index=False))
    print(pd.DataFrame(controls).round(4).to_string(index=False))


if __name__ == '__main__':
    main()
