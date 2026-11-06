"""Freeze BES party/outcome definitions and report coverage before vote models."""
from pathlib import Path
import importlib.util
import io
import json
import zipfile
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/three_explanations'


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'analysis' / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


source = module('source', '47_party_classification_audit.py')
bes = module('bes', '56_bes_input_provenance_audit.py')
ELECTIONS = {2015: {'pre': 4, 'post': 6, 'date': '2015-05-07', 'government': {1, 3}},
             2017: {'pre': 10, 'post': 13, 'date': '2017-06-08', 'government': {1}},
             2019: {'pre': 17, 'post': 19, 'date': '2019-12-12', 'government': {1}}}
PARTIES = {
    1: ('Conservative', 'Conservative Party', None),
    2: ('Labour', 'Labour Party', None),
    3: ('Liberal Democrat', 'Liberal Democrats', None),
    4: ('SNP', 'Scottish National Party', None),
    5: ('Plaid Cymru', 'Party of Wales', None),
    6: ('UKIP', 'United Kingdom Independence Party', 1272),
    7: ('Green', 'Green Party of England and Wales', None),
    8: ('BNP', None, None), 9: ('Other', None, None),
    11: ('Change UK', None, None), 12: ('Brexit Party', 'Brexit Party', 2729),
    13: ('Independent', None, None),
}
OUTCOMES = {0: 'government', 1: 'other_opposition', 2: 'populist_opposition',
            3: 'nonvote', -1: 'unresolved'}


def make_crosswalk():
    parl, gov = source.ppeg('parl'), source.ppeg('comb')
    national = parl[parl.iso3c.eq('GBR') & parl.edate.ge('1989-01-01') & parl.edate.le('2022-12-31')]
    lists = {'3': pd.read_excel(source.audit_file('populist3_release'), header=1),
             '4': pd.read_csv(source.audit_file('populist4_current'), sep=';')}
    rows, cabinets = [], []
    for year, config in ELECTIONS.items():
        cabinet = source.cabinet_record(gov, 'GBR', pd.Timestamp(config['date']), 'BES_national')
        expected = ' | '.join(sorted(PARTIES[c][1] for c in config['government']))
        assert cabinet['government_parties'] == expected
        cabinet['status'] = 'Named incumbent parties verified; external DUP support is not cabinet membership'
        cabinets.append(cabinet)
        election = national[national.edate.eq(config['date'])]
        for code, (label, ppeg_name, pl_id) in PARTIES.items():
            present = ppeg_name is not None and ppeg_name in set(election.pname_en)
            history = national[national.pname_en.eq(ppeg_name)]
            eligible = bool((history.v_share_wgt.ge(.02) | history.seats.ge(1)).any())
            for region_scope in (['England_Wales', 'Scotland'] if code == 7 else ['Great_Britain']):
                resolved = present and (code != 7 or region_scope == 'England_Wales')
                reason = ('verified_national_participant' if resolved else
                          'Green label in Scotland does not identify the separately eligible England_Wales party'
                          if code == 7 else 'party_identity_or_PopuList_scope_unverified')
                r = {'year': year, 'election_date': config['date'], 'bes_code': code,
                     'survey_label': label, 'region_scope': region_scope, 'ppeg_name': ppeg_name or '',
                     'national_participation_verified': bool(present), 'eligible_in_national_history': eligible,
                     'incumbent_cabinet_party': code in config['government'], 'identity_note': reason}
                for version, pl in lists.items():
                    match = pl[pl.country_name.eq('United Kingdom') & pl.parlgov_id.eq(pl_id)] if pl_id else pl.iloc[:0]
                    assert len(match) <= 1
                    if resolved and len(match):
                        rr = match.iloc[0]
                        values = {'inclusive': int(rr['populist'] == 1 and rr.populist_start <= year <= rr.populist_end),
                                  'strict': int(rr['populist'] == 1 and rr.populist_startnobl <= year <= rr.populist_endnobl)}
                        basis = 'explicit_PopuList_row'
                    elif resolved and eligible:
                        assert not (pl.country_name.eq('United Kingdom') & pl.party_name_english.eq(ppeg_name)).any()
                        values = {'inclusive': 0, 'strict': 0}
                        basis = 'eligible_national_party_not_listed'
                    else:
                        values = {'inclusive': np.nan, 'strict': np.nan}
                        basis = 'unresolved'
                    r[f'populist_v{version}_basis'] = basis
                    for rule, value in values.items():
                        r[f'populist_v{version}_{rule}'] = value
                        r[f'outcome_v{version}_{rule}'] = (0 if code in config['government'] else
                                                              -1 if pd.isna(value) else 2 if value else 1)
                rows.append(r)
    return pd.DataFrame(rows), pd.DataFrame(cabinets)


def classify(party, turnout, region, year, crosswalk, version='4', rule='inclusive'):
    result = pd.Series(-1, index=party.index, dtype=int)
    cw = crosswalk[crosswalk.year.eq(year)]
    for r in cw.to_dict('records'):
        mask = party.eq(r['bes_code']) & turnout.eq(1)
        if r['region_scope'] == 'England_Wales':
            mask &= region.between(1, 10)
        elif r['region_scope'] == 'Scotland':
            mask &= region.eq(11)
        result.loc[mask] = r[f'outcome_v{version}_{rule}']
    named = party.isin(PARTIES)
    assert not (named & turnout.eq(0)).any()
    result.loc[turnout.eq(0)] = 3
    return result


def main():
    crosswalk, cabinets = make_crosswalk()
    crosswalk.to_csv(OUT / 'bes_party_crosswalk.csv', index=False)
    cabinets.to_csv(OUT / 'bes_incumbent_cabinets.csv', index=False)
    cols = ['id', 'wave', 'weight', 'age', 'gor', 'generalElectionVote', 'turnoutUKGeneral',
            'econGenRetro', 'approveUKGovt', 'trustMPs', 'small_mii_cat']
    with zipfile.ZipFile(bes.verified('bes_teaching_long_v1')) as z:
        d = pd.read_stata(io.BytesIO(z.read('BESIP_teaching_long.dta')), columns=cols, convert_categoricals=False)
    rows = []
    for year, cfg in ELECTIONS.items():
        pre = d[d.wave.eq(cfg['pre'])].set_index('id')
        post = d[d.wave.eq(cfg['post'])].set_index('id').reindex(pre.index)
        basic = pre.age.between(18, 100) & pre.gor.between(1, 11)
        core = basic & pre.econGenRetro.between(1, 5) & pre.approveUKGovt.between(1, 5)
        core &= pre.trustMPs.between(1, 7) & pre.small_mii_cat.isin([1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13])
        for version in ['3', '4']:
            for rule in ['inclusive', 'strict']:
                # Post-wave location identifies the reported party at the vote;
                # pre-wave location remains the only regional model predictor.
                y = classify(post.generalElectionVote, post.turnoutUKGeneral, post.gor, year, crosswalk, version, rule)
                for sample, mask in [('pre_wave_eligible', basic), ('pre_core_complete', core)]:
                    assert pre.loc[mask, 'weight'].gt(0).all()
                    for code, label in OUTCOMES.items():
                        selected = mask & y.eq(code)
                        rows.append({'year': year, 'version': version, 'rule': rule, 'sample': sample,
                                     'outcome': label, 'pre_n': int(mask.sum()), 'n': int(selected.sum()),
                                     'pre_weight_share': float(pre.loc[selected, 'weight'].sum() / pre.loc[mask, 'weight'].sum()),
                                     'unresolved_includes_post_attrition': True})
        named_green_scotland = core & post.generalElectionVote.eq(7) & post.gor.eq(11)
        print(year, 'core', int(core.sum()), 'Scottish Green label unresolved', int(named_green_scotland.sum()))
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT / 'bes_party_outcome_coverage.csv', index=False)
    notes = {
        'classification': 'PopuList 4.0 inclusive primary; 3.0 and strict variants preserved',
        'wpd_replaced': False,
        'local_ballot_availability_established': False,
        'national_presence_is_not_individual_choice_set': True,
        'minor_unresolved': ['BNP', 'Other', 'Change UK', 'Independent', 'Green label in Scotland'],
        'future_party_not_backdated': 'Brexit Party verified only in 2019; 1900/2100 classification boundaries are not founding dates',
        'cabinet_sources': [
            'https://doi.org/10.7910/DVN/5OAH7P',
            'https://commonslibrary.parliament.uk/research-briefings/sn06404/',
            'https://www.gov.uk/government/publications/conservative-and-dup-agreement-and-uk-government-financial-support-for-northern-ireland'],
        'vote_sources': ['https://commonslibrary.parliament.uk/research-briefings/CBP-7186/',
                         'https://commonslibrary.parliament.uk/research-briefings/cbp-7979/',
                         'https://commonslibrary.parliament.uk/research-briefings/cbp-8749/'],
        'primary_machine_readable_party_participation': 'Pinned PPEG 2025v1; Commons CSV download returned 403 and was not substituted with invented data',
        'microdata_exported': False,
    }
    (OUT / 'bes_party_crosswalk_notes.json').write_text(json.dumps(notes, indent=2) + '\n')
    print(summary[summary.version.eq('4') & summary.rule.eq('inclusive') & summary['sample'].eq('pre_core_complete')]
          [['year', 'outcome', 'pre_n', 'n', 'pre_weight_share']].round(4).to_string(index=False))


if __name__ == '__main__':
    main()
