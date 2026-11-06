"""Check classification scope and cabinet availability before survey vote models.

No party labels are assigned to respondents here. WPD's national campaign
classification and PopuList's dated party classification remain distinct.
"""
from pathlib import Path
from zipfile import ZipFile
import hashlib
import json

import pandas as pd
import pyreadr

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw'
OUT = ROOT / 'data/processed/audit_20261106'
HASHES = {
    'world_populism_app.rds': 'e6dd3c7d26c4ac93a25bf7c1c45e17f46c245af5dd97f952009b921cbd1ff7a6',
    'ppeg_parl_2025v1.zip': '75384c4525349fe5640fd9b65adab8a5df19bd1370402a0f396de71eac393bbe',
    'ppeg_comb_2025v1.zip': '21e25b6ab0427e66a0dc6aec363245115ec59ce9a95b17a46a06b1b4f31a5492',
}


def legacy_file(name):
    p = RAW / name
    assert hashlib.sha256(p.read_bytes()).hexdigest() == HASHES[name]
    return p


def audit_file(key):
    record = json.loads((OUT / 'acquisition_manifest.json').read_text())[key]
    p = ROOT / record['local_path']
    assert hashlib.sha256(p.read_bytes()).hexdigest() == record['sha256']
    return p


def ppeg(component):
    name = f'ppeg_{component}_2025v1'
    with ZipFile(legacy_file(name + '.zip')) as z:
        d = pd.read_csv(z.open(name + '.csv'), low_memory=False)
    for v in ['edate', 'idate']:
        if v in d:
            d[v] = pd.to_datetime(d[v])
    return d


def cabinet_record(gov, iso, date, context):
    eligible = gov[gov.iso3c.eq(iso) & gov.idate.lt(date)]
    assert not eligible.empty, (iso, date)
    current = eligible[eligible.idate.eq(eligible.idate.max())]
    assert current.pm.nunique() == 1 and current.tog.nunique() == 1
    political = eligible[eligible.tog.ne('EC')]
    prior = political[political.idate.eq(political.idate.max())]
    def parties(x, column):
        return ' | '.join(sorted(x.loc[x[column].eq('yes'), 'pname_en'].dropna().unique()))
    return {'context': context, 'iso': iso, 'comparison_date': str(pd.Timestamp(date).date()),
            'cabinet_inauguration': str(current.idate.iloc[0].date()),
            'prime_minister': current.pm.iloc[0], 'government_type': current.tog.iloc[0],
            'government_parties': parties(current, 'gov_party'),
            'pm_party': parties(current, 'pm_party'),
            'formal_support_parties': parties(current, 'support_party'),
            'expert_or_caretaker': current.tog.iloc[0] == 'EC',
            'last_non_ec_inauguration': str(prior.idate.iloc[0].date()),
            'last_non_ec_government_parties': parties(prior, 'gov_party'),
            'status': 'PPEG-derived candidate; national verification and survey-label crosswalk pending'}


def main():
    wpd = next(iter(pyreadr.read_r(str(legacy_file('world_populism_app.rds'))).values()))
    parl, gov = ppeg('parl'), ppeg('comb')
    # PPEG stores proportions; WPD and the five-percent inclusion rule use percent.
    assert parl.v_share_wgt.dropna().between(0, 1).all()
    parl['v_share_pct'] = 100 * parl.v_share_wgt
    p3 = pd.read_excel(audit_file('populist3_release'), header=1)
    p4 = pd.read_csv(audit_file('populist4_current'), sep=';')
    key = ['country_name', 'party_name_short']
    assert not p3.duplicated(key).any() and not p4.duplicated(key).any()
    variables = ['populist', 'populist_start', 'populist_end', 'populist_startnobl',
                 'populist_endnobl', 'populist_bl']
    comparison = p3[key + variables].merge(p4[key + variables], on=key, how='outer',
                                          suffixes=('_v3', '_v4'), indicator=True,
                                          validate='one_to_one')
    common = comparison._merge.eq('both')
    changed = pd.Series(False, index=comparison.index)
    for v in variables:
        changed |= comparison[v + '_v3'].ne(comparison[v + '_v4']) & common
    # An unmatched abbreviation can be a rename, not necessarily a new party.
    comparison['populism_fields_changed'] = changed
    comparison['unmatched_name_requires_identity_review'] = ~common
    core = pd.read_csv(OUT / 'core_election_cses_match.csv')[['iso', 'country', 'date']].drop_duplicates()
    assert len(core) == 36
    national, cabinets = [], []
    wpd_dates = pd.to_datetime(wpd.Date)
    for row in core.itertuples(index=False):
        date = pd.Timestamp(row.date)
        election = parl[parl.iso3c.eq(row.iso) & parl.edate.eq(date)]
        assert not election.empty, (row.iso, date)
        classified = wpd[wpd.COUNTRY.eq(row.country) & wpd_dates.eq(date)
                         & wpd.TYPE_BROAD.eq('Legislative') & wpd.ROUND.eq(1)]
        classified = classified[classified.PARTY.notna() & classified.VOTE.notna()]
        national.append({'iso': row.iso, 'country': row.country, 'date': row.date,
                         'ppeg_party_rows': len(election),
                         'ppeg_rows_with_vote_share': int(election.v_share_wgt.notna().sum()),
                         'ppeg_rows_below_five_percent': int(election.v_share_pct.between(0, 5, inclusive='left').sum()),
                         'wpd_positive_campaign_names': ' | '.join(sorted(classified.PARTY.unique())),
                         'wpd_positive_campaign_count': classified.PARTY.nunique(),
                         'absence_below_threshold_means_nonpopulist': False,
                         'party_name_crosswalk_verified': False})
        cabinets.append(cabinet_record(gov, row.iso, date, 'core_national_election'))
    # Common snapshot before the first day of EP voting (4 June 2009), not an
    # assumption that every country voted on the same day.
    countries = pd.read_csv(OUT / 'eurobarometer713_joint.csv').country.unique()
    country_coverage = []
    for iso2 in countries:
        iso3 = gov.loc[gov.iso2c.eq(iso2), 'iso3c'].unique()
        assert len(iso3) == 1, iso2
        country_name = gov.loc[gov.iso2c.eq(iso2), 'cname_en'].unique()
        assert len(country_name) == 1
        wpd_name = {'Czech Republic': 'Czechia'}.get(country_name[0], country_name[0])
        country_coverage.append({'iso2': iso2, 'iso3': iso3[0], 'country': country_name[0],
                                 'wpd_country_present': wpd_name in set(wpd.COUNTRY),
                                 'wpd_ep_campaigns_present': False,
                                 'populist4_country_in_scope': country_name[0] in set(p4.country_name)})
        rec = cabinet_record(gov, iso3[0], pd.Timestamp('2009-06-04'), 'ep2009_eve_snapshot')
        between = gov[gov.iso3c.eq(iso3[0]) & gov.idate.between('2009-06-04', '2009-07-07')]
        rec['cabinet_changes_during_voting_or_fieldwork'] = between.idate.nunique()
        cabinets.append(rec)
    german = []
    for year in [2009, 2013]:
        date = f'{year}-09-' + ('27' if year == 2009 else '22')
        election = parl[parl.iso3c.eq('DEU') & parl.edate.eq(date)]
        for name, initials, wpd_name in [('The Left', 'L', 'The Left'),
                                        ('Alternative for Germany', 'AfD', 'Alternative for Germany')]:
            ppeg_row = election[election.pinitials.eq(initials)]
            # PPEG uses L-PDS in some earlier years; no fuzzy party-name join.
            if ppeg_row.empty and name == 'The Left':
                ppeg_row = election[election.pinitials.eq('L-PDS')]
            if ppeg_row.empty:
                continue
            assert len(ppeg_row) == 1
            for version, dataset in [('3.0', p3), ('4.0', p4)]:
                rec = dataset[dataset.country_name.eq('Germany') & dataset.party_name_english.eq(name)]
                assert len(rec) == 1
                rec = rec.iloc[0]
                positive_wpd = ((wpd.COUNTRY.eq('Germany')) & wpd_dates.eq(date)
                                & wpd.PARTY.eq(wpd_name)).any()
                german.append({'year': year, 'party': name, 'populist_version': version,
                               'ppeg_vote_share_pct': float(ppeg_row.v_share_pct.iloc[0]),
                               'wpd_positive_entry': bool(positive_wpd),
                               'wpd_absence_is_negative_label': bool(not positive_wpd and ppeg_row.v_share_pct.iloc[0] >= 5),
                               'populist_inclusive': bool(rec['populist'] == 1 and rec.populist_start <= year <= rec.populist_end),
                               'populist_excluding_borderline': bool(rec['populist'] == 1 and rec.populist_startnobl <= year <= rec.populist_endnobl)})
    assert all(4.6 < r['ppeg_vote_share_pct'] < 4.8 for r in german if r['party'] == 'Alternative for Germany')
    assert len([r for r in german if r['party'] == 'Alternative for Germany']) == 2
    summary = {
        'wpd_rows': len(wpd), 'wpd_election_types': sorted(wpd.TYPE_BROAD.unique().tolist()),
        'wpd_direct_ep2009_campaign_coverage': False,
        'populist3_parties': len(p3), 'populist4_parties': len(p4),
        'populist3_countries': p3.country_name.nunique(), 'populist4_countries': p4.country_name.nunique(),
        'common_country_short_name_pairs': int(common.sum()),
        'common_pairs_with_populism_field_changes': int(changed.sum()),
        'core_national_elections': len(core), 'ep2009_country_snapshots': len(countries),
        'ep2009_countries_in_wpd_national_scope': sum(r['wpd_country_present'] for r in country_coverage),
        'ep2009_countries_outside_wpd_national_scope': [r['country'] for r in country_coverage if not r['wpd_country_present']],
        'ep_voting_dates_source': 'https://commonslibrary.parliament.uk/research-briefings/rp09-53/',
        'cabinet_exceptions': [r for r in cabinets if r['expert_or_caretaker'] or r.get('cabinet_changes_during_voting_or_fieldwork', 0)],
        'german_definition_examples': german,
        'limitations': [
            'WPD covers national legislative/executive campaigns, usually at least five percent of votes; it is not a complete party-by-election binary matrix.',
            'No automatic nonpopulist label for an absent small party or an EP campaign.',
            'PopuList evaluates dated party-level ideologies, not each observed EP election campaign under the WPD definition.',
            'PopuList includes parties meeting a national seat/two-percent threshold; purely EP parties may remain outside coverage.',
            '1900/2100 endpoints are classification conventions, not party founding/dissolution dates.',
            'Borderline-inclusive and borderline-excluding classifications must remain separate sensitivities.',
            'Exact-name comparison across releases misses renames; unmatched names require identity checks.',
            'Full governing coalitions differ from the prime minister party; formal support parties are separate and incompletely recorded.',
            'Caretaker cabinets and within-fieldwork changes need explicit treatment; PPEG candidate records are not independently verified country histories.',
            'German PPEG CDU entries aggregate CDU/CSU; survey ballots must be mapped accordingly.',
            'No respondent vote was classified and no political association was estimated by this audit.',
        ],
    }
    (OUT / 'party_classification_audit.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    comparison.to_csv(OUT / 'populist_version_comparison.csv', index=False)
    pd.DataFrame(national).to_csv(OUT / 'core_party_classification_coverage.csv', index=False)
    pd.DataFrame(cabinets).to_csv(OUT / 'candidate_cabinet_registry.csv', index=False)
    pd.DataFrame(country_coverage).to_csv(OUT / 'ep2009_classification_country_coverage.csv', index=False)
    print(json.dumps({k: summary[k] for k in ['wpd_direct_ep2009_campaign_coverage',
                                            'common_pairs_with_populism_field_changes',
                                            'core_national_elections', 'ep2009_country_snapshots',
                                            'german_definition_examples']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
