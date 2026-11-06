"""Audit retention and pre-election measurement in BES without a vote model.

Compare observable pre-wave composition of the whole wave, repeat responders
and respondents with the required items. Weights are the same pre-wave weights
in every comparison, not post-vote weights and not invented longitudinal weights.
"""
from pathlib import Path
import io
import json
import zipfile
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/audit_20261106'
OUT = ROOT / 'data/processed/audit_20261106'
ALLOWED = {
    'econGenRetro': list(range(1, 6)), 'econPersonalRetro': list(range(1, 6)),
    'trustMPs': list(range(1, 8)), 'approveUKGovt': list(range(1, 6)),
    'small_mii_cat': [1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13],
    'bestOnMII': [0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 12],
    'generalElectionVote': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 9999],
    'partyId': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 9999],
    'EUIntegrationSelf': list(range(11)), 'immigSelf': list(range(11)),
    'redistSelf': list(range(11)), 'immigEcon': list(range(1, 8)),
    'enviroGrowth': list(range(11)), 'efficacyPolCare': list(range(1, 6)),
}
NAMED = [1, 2, 3, 4, 5, 6, 7, 8, 11, 12]
TRIPLE = ['econGenRetro', 'small_mii_cat', 'trustMPs']


def kish(w):
    return float(w.sum() ** 2 / w.pow(2).sum()) if len(w) else None


def main():
    with zipfile.ZipFile(RAW / 'bes_teaching_long_v1.zip') as z:
        with pd.io.stata.StataReader(io.BytesIO(z.read('BESIP_teaching_long.dta')),
                                    convert_categoricals=False) as reader:
            d = reader.read(columns=['id', 'wave', 'weight', 'turnoutUKGeneral', *ALLOWED])
    d = d[d.wave.le(19)].copy()
    assert not d.duplicated(['id', 'wave']).any()
    summary, distributions, repeated, routing = [], [], [], []
    for pre, post, year in [(4, 6, 2015), (10, 13, 2017), (17, 19, 2019)]:
        before = d[d.wave.eq(pre)].set_index('id')
        after = d[d.wave.eq(post)].set_index('id').reindex(before.index)
        returned = after.wave.notna()
        complete_pre = pd.concat([before[v].isin(ALLOWED[v]) for v in TRIPLE], axis=1).all(axis=1)
        named = after.generalElectionVote.isin(NAMED)
        abstained = after.turnoutUKGeneral.eq(0)
        assert not (named & abstained).any()
        assert after.loc[named, 'turnoutUKGeneral'].eq(1).all()
        assert after.loc[abstained, 'generalElectionVote'].isna().all()
        routing.append({'year': year, 'matched_n': int(returned.sum()),
                        'named_party': int(named.sum()), 'reported_abstention': int(abstained.sum()),
                        'post_vote_missing_but_abstention_known': int((after.generalElectionVote.isna() & abstained).sum()),
                        'post_generalElectionVote_zero': int(after.generalElectionVote.eq(0).sum())})
        groups = {
            'all_pre_wave': pd.Series(True, index=before.index),
            'returned_post_wave': returned,
            'complete_pre_three_plus_post_named_vote': returned & complete_pre & named,
            'complete_pre_three_plus_post_named_or_abstention':
                returned & complete_pre & (named | abstained),
        }
        for group, mask in groups.items():
            w = before.loc[mask, 'weight']
            assert w.gt(0).all() and np.isfinite(w).all()
            summary.append({'year': year, 'pre_wave': pre, 'post_wave': post, 'group': group,
                            'n': int(mask.sum()), 'fraction_of_pre_wave': float(mask.mean()),
                            'pre_weight_fraction': float(w.sum() / before.weight.sum()),
                            'weight_min': w.min(), 'weight_max': w.max(),
                            'kish_n_weight_dispersion_only': kish(w),
                            'weight_type': 'producer_pre_wave_cross_sectional'})
            for var, codes in ALLOWED.items():
                values = before[var].where(before[var].isin(codes), -999)
                # Explicit missing category prevents composition checks from silently
                # ignoring people without a substantive response.
                for code in sorted(set(codes) | {-999}):
                    selected = mask & values.eq(code)
                    distributions.append({'year': year, 'group': group, 'variable': var,
                                          'code': code, 'n': int(selected.sum()),
                                          'pre_weight_share': float(before.loc[selected, 'weight'].sum() / w.sum())})
        # Three-wave case tests whether earlier measurements actually exist. It
        # does not measure a political change or assume crisis exposure.
        for early_wave in {2015: [1, 2, 3], 2017: [7, 8, 9], 2019: [10, 14, 15, 16]}[year]:
            early = d[d.wave.eq(early_wave)].set_index('id').reindex(before.index)
            mask = groups['complete_pre_three_plus_post_named_or_abstention'].copy()
            early_valid = pd.concat([early[v].isin(ALLOWED[v]) for v in TRIPLE], axis=1).all(axis=1)
            requirements = [('early_same_three', early_valid)]
            for variable in ['bestOnMII', 'immigSelf', 'immigEcon', 'redistSelf']:
                requirements.append(('early_same_three_plus_' + variable + '_both',
                                     early_valid & early[variable].isin(ALLOWED[variable]) & before[variable].isin(ALLOWED[variable])))
            for requirement, extra in requirements:
                repeated.append({'year': year, 'early_wave': early_wave, 'pre_wave': pre,
                                 'post_wave': post, 'requirement': requirement,
                                 'n': int((mask & extra).sum())})
    dist = pd.DataFrame(distributions)
    changes = []
    for (year, var), q in dist.groupby(['year', 'variable']):
        wide = q.pivot(index='code', columns='group', values='pre_weight_share')
        for group in wide.columns.drop('all_pre_wave'):
            diff = wide[group] - wide.all_pre_wave
            changes.append({'year': year, 'variable': var, 'group': group,
                            'total_variation_distance': float(diff.abs().sum() / 2),
                            'largest_category_change_pp': float(diff.abs().max() * 100),
                            'code_largest_change': int(diff.abs().idxmax())})
    for name, rows in [('bes_selection_summary', summary), ('bes_pre_wave_composition', distributions),
                       ('bes_selection_composition_changes', changes), ('bes_three_wave_availability', repeated),
                       ('bes_post_vote_routing', routing)]:
        pd.DataFrame(rows).to_csv(OUT / f'{name}.csv', index=False)
    notes = {
        'weight_source': 'https://www.britishelectionstudy.com/wp-content/uploads/2025/10/besip_teaching_documentation_v30.0.pdf',
        'page': 2,
        'verified': 'The teaching documentation describes weights for each wave, old format waves 1-4 and new format thereafter; it does not identify the single teaching weight as a longitudinal weight.',
        'release_warning': 'Documentation is later than pinned v1; longitudinal weights in the full BES file have not been shown to exist in this teaching file.',
        'cautions': [
            'This is selection on observables, not a test of missing at random.',
            'Pre-wave cross-sectional weights do not correct subsequent panel attrition.',
            'Kish n reflects weight dispersion only, not full complex survey design.',
            'Retaining undecided pre-voters differs from selecting only those with a named pre-election intention.',
            'Future outcome models should separate abstention, other party and unknown vote.',
            'In post-election waves abstention is turnoutUKGeneral=0, while generalElectionVote is missing by routing; absence of a party answer is not automatically nonresponse.',
            'Do not infer national representativeness from a large number of online respondents.',
        ],
    }
    (OUT / 'bes_weight_audit.json').write_text(json.dumps(notes, indent=2) + '\n')
    print(pd.DataFrame(summary)[['year', 'group', 'n', 'fraction_of_pre_wave', 'pre_weight_fraction']].to_string(index=False))
    print(pd.DataFrame(repeated).to_string(index=False))


if __name__ == '__main__':
    main()
