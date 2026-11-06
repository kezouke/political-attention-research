"""Audit Belgian PartiRep panels without executing supplied statistical code.

Only numeric fields with explicit SPSS byte positions are read. The 2009 deposit
lacks the Stata dictionary required to interpret its fixed-width data safely.
No respondent records or free-text answers are written to public outputs.
"""
from pathlib import Path
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/audit_20261106'
OUT = ROOT / 'data/processed/audit_20261106'
NS = {'t': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0'}


def verified_file(key, suffix, manifest):
    path = RAW / (key + suffix)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest[key]['sha256']
    return path


def english_inventory(path, year):
    result = []
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read('content.xml'))
    for sheet in root.findall('.//t:table', NS):
        name = sheet.get('{' + NS['t'] + '}name')
        for row in sheet.findall('t:table-row', NS):
            cells = [' '.join(c.itertext()).strip() for c in row.findall('t:table-cell', NS)]
            if len(cells) >= 2 and cells[0]:
                result.append({'year': year, 'sheet': name, 'variable': cells[0],
                               'question': cells[1]})
    return result


def read_2014(manifest):
    setup = verified_file('partirep_2014_setup', '.sps', manifest).read_text(encoding='cp1252')
    block = setup.split('DATA LIST FILE=DATA/', 1)[1].split('FORMATS', 1)[0].strip().rstrip('.')
    pattern = re.compile(r'(\w+)\s+(\d+)(?:-(\d+))?(?:\s+\(([^)]*)\))?')
    fields = list(pattern.finditer(block))
    assert not pattern.sub('', block).strip(), 'Unsupported data-layout syntax'
    assert len(fields) == 741
    layout = {m[1]: (int(m[2]) - 1, int(m[3] or m[2]), m[4]) for m in fields}
    assert len(layout) == len(fields)
    previous_end = 0
    for start, end, _ in layout.values():
        assert start == previous_end and end > start
        previous_end = end
    assert previous_end == 5613
    path = verified_file('partirep_2014_data', '.dat', manifest)
    lines = path.read_bytes().splitlines()
    assert len(lines) == 2019 and {len(line) for line in lines} == {5613}
    numeric = {v: (a, b) for v, (a, b, fmt) in layout.items() if fmt is None}
    d = pd.read_fwf(path, colspecs=list(numeric.values()), names=list(numeric),
                    encoding='cp1252', keep_default_na=False, na_values=['', '.'])
    for v in d:
        d[v] = pd.to_numeric(d[v], errors='raise')
    assert d.shape == (2019, 673) and d.INTNR.is_unique
    # Independent direct byte extraction checks offsets and decimal parsing.
    for v in ['V25', 'V54', 'V59_4', 'V59_10', 'V40B', 'V60B', 'V400', 'WEIGHT1']:
        a, b = numeric[v]
        direct = pd.to_numeric(pd.Series([line[a:b].decode('cp1252').strip() for line in lines])
                               .replace({'': None, '.': None}), errors='raise')
        pd.testing.assert_series_equal(d[v], direct, check_names=False, check_dtype=False)
    value_block = setup.split('VALUE LABELS', 1)[1]
    labels = {}
    for v in d:
        match = re.search(r'^ ' + re.escape(v) + r'\s*\n(.*?)(?=^ \w+\s*\n|\Z)',
                          value_block, re.M | re.S)
        if match:
            pairs = re.findall(r"^\s+(-?\d+)\s+'((?:[^']|'')*)'", match[1], re.M)
            labels[v] = {int(k): val.replace("''", "'") for k, val in pairs}
    assert 'geen vertrouwen' in labels['V59_10'][11]
    assert labels['V60B'][27] == 'PP (Parti Populaire)'
    return d, labels


def main():
    manifest = json.loads((OUT / 'acquisition_manifest.json').read_text())
    inventory = []
    for year in [2009, 2014]:
        inventory += english_inventory(verified_file(f'partirep_{year}_codebook', '.ods', manifest), year)
    d, labels = read_2014(manifest)
    named_codes = list(range(1, 9)) + list(range(20, 28))
    specs = {
        'V25': ('top_priority_from_eight_item_list', list(range(1, 9)), 'pre'),
        'V54': ('federal_government_satisfaction', list(range(1, 6)), 'pre'),
        'V59_4': ('trust_political_parties', list(range(1, 12)), 'pre'),
        'V59_10': ('trust_politicians', list(range(1, 12)), 'pre'),
        'V400': ('national_economy_past_twelve_months', [1, 2, 3], 'post'),
        'V40B': ('reported_turnout', [1, 2], 'post'),
        'V60B': ('named_federal_party_vote', named_codes, 'post'),
    }
    for i in range(1, 9):
        specs[f'V24_{i}'] = (f'issue_importance_{i}', list(range(1, 6)), 'pre')
    masks, coverage = {}, []
    for v, (concept, valid, timing) in specs.items():
        assert set(valid) <= set(labels[v])
        masks[v] = d[v].isin(valid)
        coverage.append({'year': 2014, 'variable': v, 'concept': concept,
                         'timing': timing, 'n_rows': len(d), 'valid_n': int(masks[v].sum())})
    retained = masks['V40B']
    assert retained.sum() == 1532  # Independent archive wave-size metadata.
    assert d.V400.notna().equals(retained)
    assert not ((d.V40B.eq(2)) & masks['V60B']).any()
    named = masks['V60B'] & d.V40B.eq(1)
    nonvote = d.V40B.eq(2) | d.V60B.eq(12)
    # One person reports turnout but then uses the party question's nonvote
    # category. Keep separate routing alternatives, not a silent overwrite.
    conflict = d.V40B.eq(1) & d.V60B.eq(12)
    assert conflict.sum() == 1
    base = masks['V25'] & masks['V54'] & masks['V59_10']
    joint = []
    for scenario, outcome in {
        'named_vote': named,
        'named_vote_or_explicit_nonvote_in_either_item': named | nonvote,
        'named_vote_or_turnout_item_nonvote': named | d.V40B.eq(2),
    }.items():
        joint.append({'year': 2014, 'scenario': scenario, 'pre_wave_n': len(d),
                      'post_wave_n': int(retained.sum()),
                      'pre_priority_gov_trust_outcome_n': int((base & outcome).sum()),
                      'same_plus_post_economy_n': int((base & outcome & masks['V400']).sum()),
                      'all_three_with_economy_measured_before_vote': False})
    weights = []
    for v in ['WEIGHT1', 'WEIGHT2', 'WEIGHT3', 'WEIGHT4']:
        w = d[v].where(d[v].gt(0)).dropna()
        weights.append({'variable': v, 'positive_n': len(w), 'min': w.min(), 'max': w.max(),
                        'kish_n_weight_dispersion_only': w.sum() ** 2 / w.pow(2).sum(),
                        'construction_verified': False})
    selection = []
    # Availability/selection audit only. No association with party choice.
    for v in ['V25', 'V54', 'V59_10']:
        for code in sorted(d.loc[masks[v], v].unique()):
            group = d[v].eq(code)
            selection.append({'variable': v, 'response_code': int(code), 'pre_n': int(group.sum()),
                              'retained_n': int((group & retained).sum()),
                              'retained_fraction': float(retained[group].mean())})
    setup_2009 = verified_file('partirep_2009_setup', '.do', manifest).read_text(errors='replace')
    assert not re.search(r'^\s*(infile|infix|dictionary)\b', setup_2009, re.M | re.I)
    raw_2009 = verified_file('partirep_2009_data', '.dat', manifest)
    summary = {
        '2014': {'pre_n': len(d), 'post_n': int(retained.sum()),
                 'retained_fraction': float(retained.mean()), 'layout_columns': 741,
                 'numeric_columns_read': len(d.columns), 'unique_ids': True,
                 'pre_fieldwork': ['2014-03-20', '2014-05-17'],
                 'election_date': '2014-05-25', 'post_fieldwork': ['2014-05-26', '2014-07-01'],
                 'turnout_vote_item_disagreements': int(conflict.sum()),
                 'trust_code_11_means': '0: no trust, not above maximum trust',
                 'selected_value_labels': {v: labels[v] for v in specs}},
        '2009': {'raw_lines': len(raw_2009.read_bytes().splitlines()), 'microdata_parsed': False,
                 'blocker': 'Missing fixed-width Stata dictionary; .do contains labels but no field positions',
                 'archive_wave_sizes': [2331, 1845, 1698], 'election_level': 'regional and European, not federal'},
        'limitations': [
            '2014 trust, issue priority and government satisfaction are pre-election; economic assessment is post-election.',
            'The 2014 sample covers eligible Flanders and Wallonia residents aged at most 85, excluding Brussels.',
            '2014 government satisfaction raw codes 1..5 run from very satisfied to very dissatisfied.',
            '2014 trust raw code 11 means zero trust. Use 11->0; raw codes 1..10 retain their values.',
            '2014 SPSS labels add federal party code 27 (PP), absent from English ODS; keep producer data labels.',
            'Weight construction is not verified. None is assumed to be a longitudinal or purely demographic weight.',
            '2009 questionnaires contain household economy, government satisfaction, politician trust and priorities, but no joint counts are claimed.',
            '2009 and 2014 are separate panels; no cross-election respondent linkage has been established.',
            'Changing issue lists and election levels prevent direct unqualified 2009/2014 comparisons.',
            'Both current DANS deposits specify CC-BY-4.0. No raw respondent data or free text redistributed.',
        ]}
    for name, rows in [('partirep_inventory', inventory), ('partirep_variable_coverage', coverage),
                       ('partirep_joint_coverage', joint), ('partirep_weights', weights),
                       ('partirep_selection', selection)]:
        pd.DataFrame(rows).to_csv(OUT / (name + '.csv'), index=False)
    (OUT / 'partirep_audit.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(pd.DataFrame(joint).to_string(index=False))


if __name__ == '__main__':
    main()
