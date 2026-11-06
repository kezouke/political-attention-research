"""Audit primary Dutch election files, including questionnaire timing and mode.

This is an availability audit. It does not estimate political associations.
Use the repository's TAB plus DDI exports; independently check observed values
against the original portable SPSS files where the reader supports the format.
Never join respondent IDs across election years without a producer linkage.
"""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/audit_20261106'
OUT = ROOT / 'data/processed/audit_20261106'
FILES = {2006: ('144350', '144356', 2806), 2010: ('152271', '152284', 2621),
         2012: ('168672', None, 1677)}
# Timing follows the producer questionnaires, not variable number alone.
SPECS = {
    2006: {
        'V041': ('first_national_problem', 'pre_election', 'coded_problem'),
        'V070': ('government_policy_effect_on_economy', 'pre_election', [1, 2, 3]),
        'V073': ('government_satisfaction', 'pre_election', list(range(1, 6))),
        'V081': ('named_party_intention', 'pre_election', list(range(1, 10)) + [11, 12, 13, 14]),
        'V512': ('named_party_vote', 'post_election', list(range(1, 10)) + [11, 12, 13, 14]),
        'V740': ('mps_do_not_care', 'post_election', [1, 2]),
        'V741': ('parties_only_want_vote', 'post_election', [1, 2]),
        'V751': ('ministers_self_interested', 'post_election', [1, 2, 3, 4]),
        'V895': ('trust_parliament', 'post_election_dropoff', [1, 2, 3, 4]),
        'V930': ('politicians_honest', 'post_election_dropoff', list(range(1, 6))),
        'V931': ('politicians_profiteers', 'post_election_dropoff', list(range(1, 6))),
    },
    2010: {
        'V041': ('first_national_problem', 'pre_election', list(range(1, 17))),
        'V070': ('government_policy_effect_on_economy', 'pre_election', [1, 2, 3]),
        'V073': ('government_satisfaction', 'pre_election', list(range(1, 6))),
        'V081': ('named_party_intention', 'pre_election', list(range(1, 12))),
        'V512': ('named_party_vote', 'post_election', list(range(1, 12))),
        'V741': ('parties_only_want_vote', 'post_election', [1, 2]),
        'V753': ('politicians_honest', 'post_election', list(range(1, 6))),
        'V754': ('politicians_profiteers', 'post_election', list(range(1, 6))),
        'V806': ('trust_parliament', 'post_election', [1, 2, 3, 4]),
        'V811': ('trust_parties', 'post_election', [1, 2, 3, 4]),
        'V820': ('national_economy_past_12_months', 'post_election', [1, 2, 3]),
        'V823': ('household_economy_past_12_months', 'post_election', [1, 2, 3]),
    },
    2012: {
        'V071': ('first_national_problem', 'post_election', list(range(1, 17))),
        'V090': ('government_policy_effect_on_economy', 'post_election', [1, 2, 3]),
        'V093': ('government_satisfaction', 'post_election', list(range(1, 6))),
        'V212': ('named_party_vote', 'post_election', list(range(1, 13))),
        'V241': ('parties_only_want_vote', 'post_election', [1, 2]),
        'V311': ('national_economy_past_12_months', 'post_election', [1, 2, 3]),
        'V446': ('trust_parliament', 'post_election_dropoff', [1, 2, 3, 4]),
        'V451': ('trust_parties', 'post_election_dropoff', [1, 2, 3, 4]),
    },
}


def ddi(path):
    variables = {}
    for var in ET.parse(path).getroot().findall('.//{*}var'):
        cats = {}
        for c in var.findall('{*}catgry'):
            value = c.findtext('{*}catValu')
            cats[float(value)] = {'label': c.findtext('{*}labl'),
                                 'n': int(float(c.findtext('{*}catStat')))}
        variables[var.attrib['name'].upper()] = {
            'label': var.findtext('{*}labl'), 'categories': cats}
    return variables


def main():
    coverage, joint, inventory, weight_rows = [], [], [], []
    summary = {}
    manifest = json.loads((OUT / 'acquisition_manifest.json').read_text())
    # Acquisition manifest is keyed by source name.
    for year, (fileid, porid, expected_n) in FILES.items():
        path = RAW / f'dpes_{year}_file_{fileid}.tab'
        entry = manifest[f'dpes_{year}_file_{fileid}']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']
        d = pd.read_csv(path, sep='\t', low_memory=False, na_values=['.'])
        d.columns = d.columns.str.upper()
        assert len(d) == expected_n and d.RNR.is_unique
        meta = ddi(RAW / f'dpes_{year}_ddi.xml')
        assert set(d.columns) == set(meta)
        for v, description in meta.items():
            inventory.append({'year': year, 'variable': v, 'label': description['label']})
        original = None
        if porid:
            original, _ = pyreadstat.read_por(RAW / f'dpes_{year}_file_{porid}.por')
            original = original.set_index('RNR').sort_index()
            assert original.index.equals(d.set_index('RNR').sort_index().index)
        masks = {}
        selected_labels = {}
        for v, (concept, timing, valid_codes) in SPECS[year].items():
            s = pd.to_numeric(d[v], errors='raise')
            cats = meta[v]['categories']
            # DDI frequencies are a separate producer checksum of interpretation.
            for code, cat in cats.items():
                assert int(s.eq(code).sum()) == cat['n'], (year, v, code)
            if valid_codes == 'coded_problem':
                valid_codes = [code for code in cats if 10100 <= code < 11700]
            assert set(valid_codes) <= set(cats), (year, v, valid_codes)
            valid = s.isin(valid_codes)
            masks[concept] = valid
            if original is not None:
                a = original[v]
                b = d.set_index('RNR')[v].reindex(original.index)
                assert np.array_equal(a.dropna().to_numpy(), b[a.notna()].to_numpy()), (year, v)
            coverage.append({'year': year, 'variable': v, 'concept': concept,
                             'timing': timing, 'n': len(d), 'valid_n': int(valid.sum()),
                             'source_label': meta[v]['label']})
            selected_labels[v] = cats
        sets = {
            'policy_economy_priority_post_trust_parliament_named_vote':
                ['government_policy_effect_on_economy', 'first_national_problem',
                 'trust_parliament', 'named_party_vote'],
            'policy_economy_priority_post_parties_only_want_vote_named_vote':
                ['government_policy_effect_on_economy', 'first_national_problem',
                 'parties_only_want_vote', 'named_party_vote'],
        }
        if year != 2006:
            sets['retrospective_economy_priority_post_trust_parties_named_vote'] = [
                'national_economy_past_12_months', 'first_national_problem',
                'trust_parties', 'named_party_vote']
        for name, concepts in sets.items():
            mask = pd.concat([masks[x] for x in concepts], axis=1).all(axis=1)
            joint.append({'year': year, 'comparison': name, 'joint_n': int(mask.sum()),
                          'trust_measured_before_vote': False,
                          'same_people_across_election_years_verified': False})
        for v in d.columns:
            if not v.startswith('WGT'):
                continue
            w = pd.to_numeric(d[v], errors='raise')
            w = w[w.gt(0)]
            weight_rows.append({'year': year, 'variable': v, 'label': meta[v]['label'],
                                'n_positive': len(w), 'min': w.min(), 'max': w.max(),
                                'kish_n_weight_dispersion_only': w.sum()**2 / w.pow(2).sum()})
        summary[str(year)] = {
            'n_rows': len(d), 'n_columns': len(d.columns), 'id_unique_within_file': True,
            'joint_all_three_before_vote': 0,
            'portable_file_observed_values_match': original is not None,
            'pre_election_interview': year != 2012,
            'special_missing_codes_excluded_explicitly': True,
            'selected_value_labels': selected_labels,
        }
    summary['limitations'] = [
        '2006 and 2010 policy-effect item mixes perceived economic change and government responsibility.',
        'No pre-vote general political trust in the audited variables; 2012 interviews all follow election day.',
        '2006 institutional trust is in the later drop-off; 2010 institutional trust is in the second interview.',
        '2012 generic economy coding reverses the meanings of codes 2 and 3 relative to 2010.',
        '2006 first national problem has detailed codes; 2010 and 2012 use broader categories.',
        '2012 .por cannot be parsed by installed readstat; official TAB and DDI used and frequencies checked.',
        'Weights calibrated to party choice cannot independently validate recovered party shares.',
        'No producer link between respondents across 2006, 2010 and 2012 has been verified.',
        'Availability is not statistical power; dropout and item-missingness remain relevant.',
    ]
    for name, rows in [('dpes_variable_coverage', coverage), ('dpes_joint_coverage', joint),
                       ('dpes_variable_inventory', inventory), ('dpes_weights', weight_rows)]:
        # DDI labels sometimes end in padding spaces; omit padding in CSVs.
        pd.DataFrame(rows).map(lambda x: x.rstrip() if isinstance(x, str) else x).to_csv(
            OUT / f'{name}.csv', index=False)
    (OUT / 'dpes_audit.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(pd.DataFrame(joint).to_string(index=False))


if __name__ == '__main__':
    main()
