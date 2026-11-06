"""Audit authenticated EB 71.3 data using metadata and aggregate outputs only.

This is an availability audit, not a test of political associations. Download
manually through GESIS under the recorded project-specific access permission.
No respondent rows, original IDs, interviewer IDs or free text are exported.
"""
from pathlib import Path
import hashlib
import json

import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/audit_20261106'
# Keep UK regional coding: code 701 is Plaid Cymru in GB but DUP in NI.
SAMPLES = {
    1: ('FR', 542), 2: ('BE', 543), 3: ('NL', 544), 4: ('DE', 546),
    5: ('IT', 548), 6: ('LU', 549), 7: ('DK', 550), 8: ('IE', 551),
    9: ('GB', 553), 10: ('GB', 554), 11: ('GR', 555), 12: ('ES', 556),
    13: ('PT', 557), 14: ('DE', 547), 16: ('FI', 558), 17: ('SE', 559),
    18: ('AT', 560), 19: ('CY', 561), 20: ('CZ', 562), 21: ('EE', 563),
    22: ('HU', 564), 23: ('LV', 565), 24: ('LT', 566), 25: ('MT', 567),
    26: ('PL', 568), 27: ('SK', 569), 28: ('SI', 570), 29: ('BG', 571),
    30: ('RO', 572),
}


def verified_download(filename):
    manifest = json.loads((OUT / 'authenticated_downloads.json').read_text())
    entry = next(e for e in manifest['files'] if e['filename'] == filename)
    path = ROOT / entry['local_path']
    assert path.stat().st_size == entry['bytes']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']
    return path


def priority_mask(d, start):
    """Two unranked choices; merge the questionnaire's environment wording split."""
    cols = [f'v{i}' for i in range(start, start + 18)]
    x = d[cols].copy()
    a, b = f'v{start + 12}', f'v{start + 13}'
    environment = x[a].where(d.v796.eq(1), x[b])
    items = x.drop(columns=[a, b, f'v{start + 16}', f'v{start + 17}'])
    items['environment'] = environment
    mentions = items.eq(1).sum(axis=1)
    none, dk = x[f'v{start + 16}'], x[f'v{start + 17}']
    answered = items.isin([0, 1]).all(axis=1) & none.isin([0, 1]) & dk.isin([0, 1])
    strict = answered & mentions.between(1, 2) & none.eq(0) & dk.eq(0)
    valid_none = answered & mentions.eq(0) & none.eq(1) & dk.eq(0)
    diagnostics = {
        'more_than_two_mentions': int((mentions.gt(2) & d.v37.eq(1)).sum()),
        'none_and_substantive': int((none.eq(1) & mentions.gt(0) & d.v37.eq(1)).sum()),
        'dk_and_substantive': int((dk.eq(1) & mentions.gt(0) & d.v37.eq(1)).sum()),
        'valid_explicit_none': int((valid_none & d.v37.eq(1)).sum()),
    }
    return strict, strict | valid_none, diagnostics


def main():
    path = verified_download('ZA4973_v3-0-0.sav')
    _, meta = pyreadstat.read_sav(path, metadataonly=True, user_missing=True)
    assert (meta.number_rows, meta.number_columns) == (30343, 798)
    cols = ['v6', 'v7', 'v8', 'v10', 'v12', 'v37', 'v54', 'v65', 'v105',
            'v109', 'v216', 'v217', 'v218', 'v541', 'v573', 'v666', 'v701', 'v796']
    cols += [f'v{i}' for i in range(133, 169)]
    cols += [f'v{i}' for i in range(542, 573)]
    d, _ = pyreadstat.read_sav(path, usecols=cols, user_missing=True)
    assert len(d) == 30343
    assert d.v37.eq(1).equals(d.v6.isin(SAMPLES))
    country = d.v6.map({k: v[0] for k, v in SAMPLES.items()})
    # Uniform adult sample, not a claim that every country's franchise starts at 18.
    adult = d.v37.eq(1) & d.v666.ge(18) & d.v666.le(98)
    named = pd.Series(False, index=d.index)
    party_inventory = []
    for sample, (iso, num) in SAMPLES.items():
        var = f'v{num}'
        labels = meta.variable_value_labels[var]
        valid = [c for c in labels if 0 < c < 990]
        if sample == 19:
            valid.remove(950)  # Unspecified independent candidates, not a named option.
        this_sample = d.v6.eq(sample)
        named |= this_sample & d.v541.eq(1) & d[var].isin(valid)
        assert (d.loc[this_sample, var] == d.loc[this_sample, 'v573']).all()
        for code, label in labels.items():
            party_inventory.append({'sample': sample, 'country': iso, 'variable': var,
                                    'code': int(code), 'label': label,
                                    'named_response_option': code in valid})
    nonvote = d.v541.eq(2)
    national, national_none, national_checks = priority_mask(d, 133)
    personal, personal_none, personal_checks = priority_mask(d, 151)
    masks = {
        'national_economy_current': d.v105.isin([1, 2, 3, 4]),
        'household_finances_current': d.v109.isin([1, 2, 3, 4]),
        'national_priority': national,
        'national_priority_or_explicit_none': national_none,
        'personal_priority': personal,
        'personal_priority_or_explicit_none': personal_none,
        'trust_parties': d.v216.isin([1, 2]),
        'trust_government': d.v217.isin([1, 2]),
        'trust_parliament': d.v218.isin([1, 2]),
        'named_vote': named,
        'named_vote_or_reported_nonvote': named | nonvote,
    }
    coverage, joint, weights = [], [], []
    for iso in sorted(country.dropna().unique()):
        base = adult & country.eq(iso)
        for concept, mask in masks.items():
            coverage.append({'country': iso, 'concept': concept,
                             'adult_sample_n': int(base.sum()),
                             'valid_n': int((base & mask).sum())})
        for priority in ['national_priority', 'personal_priority',
                         'national_priority_or_explicit_none', 'personal_priority_or_explicit_none']:
            complete = (base & masks['national_economy_current'] & masks[priority]
                        & masks['trust_parties'] & masks['trust_government'])
            for outcome in ['named_vote', 'named_vote_or_reported_nonvote']:
                included = complete & masks[outcome]
                w = d.loc[included, 'v54']
                joint.append({'country': iso, 'priority': priority, 'outcome': outcome,
                              'adult_sample_n': int(base.sum()), 'joint_n': int(included.sum()),
                              'plus_household_finances_n': int((included & masks['household_finances_current']).sum()),
                              'kish_n_weight_dispersion_only': float(w.sum() ** 2 / w.pow(2).sum()),
                              'w31_weighted_complete_fraction': float(w.sum() / d.loc[base, 'v54'].sum())})
        for var in ['v54', 'v65']:
            w = d.loc[base, var]
            assert w.notna().all() and w.gt(0).all()
            weights.append({'country': iso, 'variable': var, 'n': len(w),
                            'min': float(w.min()), 'max': float(w.max()),
                            'sum': float(w.sum())})
    selected = [r for r in joint if r['priority'] == 'national_priority']
    summary = {
        'study': 'ZA4973', 'version': '3.0.0', 'doi': '10.4232/1.11135',
        'raw_rows': len(d), 'raw_columns': meta.number_columns,
        'eu27_rows_all_ages': int(d.v37.eq(1).sum()), 'eu27_adult_rows': int(adult.sum()),
        'eu27_countries': int(country.nunique()),
        'national_priority_joint_totals': {
            o: sum(r['joint_n'] for r in selected if r['outcome'] == o)
            for o in ['named_vote', 'named_vote_or_reported_nonvote']},
        'national_priority_checks': national_checks, 'personal_priority_checks': personal_checks,
        'fieldwork_date_code_range': [int(d.v701.min()), int(d.v701.max())],
        'fieldwork_dates': [meta.variable_value_labels['v701'][d.v701.min()],
                           meta.variable_value_labels['v701'][d.v701.max()]],
        'limitations': [
            'All attitudes were measured after the June 2009 European Parliament election.',
            'Economy items measure current conditions, not retrospective change or crisis losses.',
            'Government trust is distinct from party trust but is not a direct government-performance rating.',
            'Two unranked priority mentions from a prompted list do not measure changing priorities within individuals.',
            'Environmental wording differs randomly between questionnaire A and B; retain split indicator.',
            '18+ is an explicit uniform adult restriction, not a verified national eligibility indicator; age is at interview.',
            'Explicit nonvote is retained separately; missing or other party is never silently counted as nonvote.',
            'Named response option does not imply successful WPD linkage; party/campaign and governing-coalition mapping remains required.',
            'UK region-specific party variables must be retained: the combined UK variable pools Plaid Cymru and DUP.',
            'W31 is demographic poststratification for voting-age populations, including DE/UK regional proportions; W52 also weights EU population sizes.',
            'Weight-dispersion effective n is not design-based precision and does not account for clustering.',
            'The 27-country joint cross-section does not establish a causal effect of crises or replace national election panels.',
        ],
    }
    metadata = [{'variable': v, 'label': meta.column_names_to_labels[v],
                 'value_labels': meta.variable_value_labels.get(v, {}),
                 'declared_missing_ranges': meta.missing_ranges.get(v, [])} for v in cols]
    (OUT / 'eurobarometer713_audit.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    (OUT / 'eurobarometer713_metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    for name, rows in [('coverage', coverage), ('joint', joint), ('weights', weights),
                       ('party_response_dictionary', party_inventory)]:
        pd.DataFrame(rows).to_csv(OUT / f'eurobarometer713_{name}.csv', index=False)
    print(json.dumps({k: summary[k] for k in ['eu27_adult_rows', 'eu27_countries',
                                            'national_priority_joint_totals',
                                            'national_priority_checks', 'personal_priority_checks']}, indent=2))


if __name__ == '__main__':
    main()
