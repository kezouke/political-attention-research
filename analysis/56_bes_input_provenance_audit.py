"""Check BES v1 long values against official wave-specific wide variables.

Only availability, metadata and consistency counts are exported. No respondent
identifiers, rows or free text leave local memory. This is not an outcome model.
"""
from pathlib import Path
import hashlib
import io
import json
import zipfile
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/audit_20261106'
WAVES = [1, 4, 6, 7, 10, 11, 13, 14, 16, 17, 19]
VARS = ['weight', 'age', 'gender', 'gor', 'p_edlevel', 'p_work_stat', 'lr_scale',
        'partyId', 'partyIdStrength', 'generalElectionVote', 'turnoutUKGeneral',
        'econGenRetro', 'econPersonalRetro', 'approveUKGovt', 'trustMPs',
        'small_mii_cat', 'bestOnMII', 'redistSelf', 'immigSelf', 'immigEcon',
        'EUIntegrationSelf', 'enviroGrowth', 'polAttention']
MD5 = {'bes_teaching_long_v1': '6f491d68d877423201bd725c533fdd5e',
       'bes_teaching_wide_v1': '38e75eaa475958736b0f24370b897718'}


def verified(key):
    r = json.loads((OUT / 'acquisition_manifest.json').read_text())[key]
    p = ROOT / r['local_path']
    data = p.read_bytes()
    assert r['status'] == 200
    assert hashlib.sha256(data).hexdigest() == r['sha256']
    assert hashlib.md5(data).hexdigest() == MD5[key]
    return p


def main():
    with zipfile.ZipFile(verified('bes_teaching_long_v1')) as z:
        with pd.io.stata.StataReader(io.BytesIO(z.read('BESIP_teaching_long.dta')),
                                    convert_categoricals=False) as r:
            labels = r.variable_labels()
            sets = r.value_labels()
            mapping = dict(zip(r._varlist, r._lbllist))
            metadata = {v: {'label': labels[v], 'labelset': mapping[v],
                            'value_labels': {str(k): val for k, val in sets.get(mapping[v], {}).items()}}
                        for v in VARS}
            long = r.read(columns=['id', 'wave', *VARS])
    assert not long.duplicated(['id', 'wave']).any()
    long = long[long.wave.isin(WAVES)].copy()
    with zipfile.ZipFile(verified('bes_teaching_wide_v1')) as z:
        with pd.io.stata.StataReader(io.BytesIO(z.read('BESIP_teaching_wide.dta')),
                                    convert_categoricals=False) as r:
            wide_labels = r.variable_labels()
            cols = [f'{v}W{w}' for w in WAVES for v in VARS if f'{v}W{w}' in wide_labels]
            wide = r.read(columns=['id', *cols]).set_index('id')
    assert wide.index.is_unique
    checks, coverage, anomalies = [], [], []
    for w in WAVES:
        x = long[long.wave.eq(w)].set_index('id')
        assert x.index.isin(wide.index).all()
        for v in VARS:
            col = f'{v}W{w}'
            if col in wide:
                a, b = x[v], wide.loc[x.index, col]
                same = a.eq(b) | (a.isna() & b.isna())
                assert same.all(), (w, v, int((~same).sum()))
                matched = int(same.sum())
            else:
                assert x[v].isna().all(), (w, v, 'wide variable absent but long has values')
                matched = len(x)
            checks.append({'wave': w, 'variable': v, 'wide_variable': col,
                           'wide_variable_exists': col in wide,
                           'long_rows_checked': len(x), 'exact_matches_including_missing': matched})
            valid = x[v].notna() & x[v].ne(9999)
            coverage.append({'wave': w, 'variable': v, 'n': len(x),
                             'nonnull_n': int(x[v].notna().sum()),
                             'excluding_9999_n': int(valid.sum()),
                             'minimum_excluding_9999': float(x.loc[valid, v].min()),
                             'maximum_excluding_9999': float(x.loc[valid, v].max())})
    for early, pre, post, year in [(1, 4, 6, 2015), (7, 10, 13, 2017),
                                  (10, 11, 13, 2017), (16, 17, 19, 2019)]:
        a = long[long.wave.eq(early)].set_index('id')
        b = long[long.wave.eq(pre)].set_index('id')
        c = long[long.wave.eq(post)].set_index('id')
        ix = a.index.intersection(b.index)
        delta = b.loc[ix, 'age'] - a.loc[ix, 'age']
        # Broad prespecified audit flag, not an automatic correction. No later
        # age is used to repair an earlier record or determine the primary sample.
        elapsed = {2015: 2, 2017: 2, 2019: 3}[year]
        bad = delta.lt(0) | delta.gt(elapsed)
        anomalies.append({'year': year, 'early_wave': early, 'pre_wave': pre,
                          'post_wave': post, 'early_pre_matched': len(ix),
                          'age_change_valid_pairs': int(delta.notna().sum()),
                          'age_change_negative_or_above_broad_limit': int(bad.sum()),
                          'age_upper_change_limit': elapsed,
                          'pre_under_18': int(b.age.lt(18).sum()),
                          'pre_age_missing_or_over_100': int((b.age.isna() | b.age.gt(100)).sum()),
                          'pre_region_outside_1_to_11': int((~b.gor.between(1, 11)).sum()),
                          'pre_post_matched': len(b.index.intersection(c.index))})
    for name, rows in [('bes_long_wide_checks', checks), ('bes_model_variable_coverage', coverage),
                       ('bes_temporal_control_audit', anomalies)]:
        pd.DataFrame(rows).to_csv(OUT / (name + '.csv'), index=False)
    # These are metadata, not answers from any participant.
    (OUT / 'bes_model_variable_metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    report = {
        'source_doi': '10.48420/25460980.v1', 'official_md5_verified': MD5,
        'wave_variable_combinations_checked': len(checks),
        'all_long_values_match_wave_specific_wide_values': True,
        'controls_provenance': 'Use only the variable labelled with the selected pre-election wave; never use wave 25 values to fill earlier waves.',
        'profile_timing': 'Wave-specific profile values are the latest available at that wave, not necessarily a fresh interview response.',
        'left_right_timing': 'Top-up and carried measurements may predate the wave; do not treat every repeated value as a new measurement.',
        'codebook_version_warning': 'Teaching v30 codebook renumbers education and MII; use embedded value labels from pinned v1.',
        'education_codes_v1': '0..5; current teaching codebook shows 1..6',
        'mii_codes_v1': '1,2,3,4,5,7,8,9,10,11,12,13; current teaching codebook uses 1..12',
        'government_approval_scale': '1 strongly disapprove, 5 strongly approve, confirmed in wave19 codebook p167; v1 embedded labels absent',
        'post_turnout_scale': 'Actual post-election turnout is 0/1 despite shared long-file labels for pre-election likelihood; audit 40 verifies routing.',
        'microdata_exported': False,
        'sources': [
            'https://api.figshare.com/v2/articles/25460980/versions/1',
            'https://www.britishelectionstudy.com/wp-content/uploads/2020/05/Bes_wave19Documentation_V2.pdf',
            'https://www.britishelectionstudy.com/wp-content/uploads/2025/10/besip_teaching_documentation_v30.0.pdf'],
    }
    (OUT / 'bes_input_provenance_audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print(pd.DataFrame(anomalies).to_string(index=False))


if __name__ == '__main__':
    main()
