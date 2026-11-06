"""Conservative EP-2009 party crosswalk and outcome-feasibility audit.

Only metadata and aggregate counts leave the local microdata step. No attitude
association is estimated. Names were reviewed against ParlGov election rows;
coalitions, reused identifiers and party continuity are never resolved by a
fuzzy string match. Unresolved rows are retained explicitly.
"""
from pathlib import Path
import importlib.util
import json

import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/audit_20261106'


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'analysis' / filename)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


source = module('classification', '47_party_classification_audit.py')
eb = module('eb', '45_eurobarometer_audit.py')

# Survey code -> ParlGov party ID. These are reviewed proposals, with additional
# identity/coalition exclusions below. Zero means unresolved, never nonpopulist.
# GB uses the GB and NI survey dictionaries separately below.
MATCHES = {
 'AT': {200:973,401:1013,600:50,601:1536,800:1429,950:669},
 'BE': {100:256,200:1378,201:1029,306:1110,310:915,401:723,404:1192,
        505:221,600:993,601:171,700:501,800:161,801:1594},
 'BG': {50:353,200:1160,300:544,500:1541,501:1254,502:566,503:636,600:535,700:1286},
 'CY': {100:572,200:945,201:851,305:491,500:1575,800:1621},
 'CZ': {100:1173,200:789,400:1245,500:829,501:1532,800:196},
 'DE': {105:791,200:558,300:543,400:1727,601:524,805:772,950:41},
 'DK': {101:1644,200:1629,203:749,300:1605,302:211,500:590,601:1418,950:1450},
 'EE': {200:1448,300:113,301:1137,501:1597,800:219,900:417,950:2029},
 'ES': {105:118,200:902,350:551,500:645,780:771,781:1657},
 'FI': {100:1292,200:395,500:1118,700:585,800:1062,900:94},
 'FR': {50:259,101:1176,102:442,103:686,200:1539,304:509,450:658,
        508:2399,600:270,801:873,803:2249},
 'GB': {200:1556,201:1023,301:659,500:773,600:1250,700:1284,701:311,800:467,951:1272},
 'GR': {101:614,107:1592,200:1338,400:47,602:1179,803:1280},
 'HU': {200:1591,300:1426,400:437,500:546,600:600},
 'IE': {100:2217,101:1014,200:318,400:1393,500:280,800:1573,950:1199,951:2329},
 'IT': {102:1321,150:465,205:1296,206:382,303:693,402:226,501:596,704:1436,709:1040},
 'LT': {100:1056,200:1277,300:581,301:983,303:482,305:887,306:676,400:709,
        500:1045,600:1421,701:28},
 'LU': {100:151,101:457,200:701,300:967,400:1234,803:310,950:1130,957:1582},
 'LV': {200:1656,201:1100,305:962,400:662,500:811,501:1518,502:445,600:521,
        602:801,700:1520,950:500},
 'MT': {200:1003,400:984,600:0,601:1400,800:360},
 'NL': {200:742,202:357,300:1409,301:345,400:235,411:1206,602:1501,800:756,951:990},
 'PL': {201:1104,202:629,400:512,500:528,601:1283,602:1549,900:664,901:207},
 'PT': {100:1295,105:557,154:281,200:725,201:251,300:1273},
 'RO': {50:1120,300:1015,302:958,401:888,600:713,700:948,950:761},
 'SE': {100:882,200:904,301:1461,302:892,400:282,501:657,600:1546,800:1154,950:404,951:721},
 'SI': {200:706,300:1252,301:326,400:1047,500:179,501:16,600:981,800:1512,950:1587},
 'SK': {100:44,200:220,301:1460,400:131,401:1432,402:752,501:1645,600:1072,602:1142,700:559},
}
NI_MATCHES = {50:1210,100:689,201:1023,500:773,701:319,800:467}
# A survey coalition cannot simply inherit the leading member's ideology or
# government status. These rows remain unresolved until a component crosswalk.
COALITIONS = {
 ('BG',50):'Napred coalition is represented by ZNS in ParlGov; full components pending',
 ('BG',501):'Blue Coalition contains SDS and DSB; full components pending',
 ('ES',105):'IU/ICV/EUiA/BA list: full component classification pending',
 ('ES',780):'Coalition for Europe: full component classification pending',
 ('ES',781):'Europe of the Peoples: full component classification pending',
 ('FI',50):'Survey pools Christian Democrats and Finns Party; distinct populism labels',
 ('FR',50):'Libertas pools MPF and CPNT; full component classification pending',
 ('FR',103):'Left Front is represented by PCF; full component classification pending',
 ('FR',801):'Europe Ecologie list contains parties and unaffiliated candidates',
 ('HU',400):'Fidesz/KDNP joint list; full component classification pending',
 ('IT',102):'PRC/PdCI/Socialismo2000/Consumatori list; components pending',
 ('IT',150):'Sinistra e Liberta list precedes SEL; component/time identity pending',
 ('IT',709):'Autonomy list combines parties with differing status; components pending',
 ('LV',201):'Harmony Centre alliance; full component classification pending',
 ('NL',411):'ChristenUnie is in government, SGP is not; mixed government status',
 ('PL',201):'Agreement for the Future/Centre Left; full components pending',
 ('PL',202):'SLD/UP joint list; full components pending',
 ('PT',100):'CDU joint list combines PCP/PEV; full components pending',
 ('SK',501):'KDS/OKS joint list; full components pending',
}
IDENTITY_FLAGS = {
 ('EE',417):'ParlGov ERL/EKRE continuity spans 2012 merger; do not backcast EKRE label',
 ('LT',887):'Earlier Centre Union ID differs from PopuList Centre Party ID 2635',
 ('LT',1056):'FRONTAS versus later Socialist Peoples Front continuity requires review',
 ('LV',521):'ParlGov combines TB/LNNK and later National Alliance, separately labelled by PopuList',
 ('RO',761):'ParlGov generic independent ID cannot classify Elena Basescu',
 ('SI',706):'PopuList ID 706 names United Left; ParlGov ID 706 names Social Democrats',
 ('IT',596):'ParlGov FI/PdL continuity; PopuList has separate FI1 and PdL rows',
}
# Verified government membership can still be used when ideology is unresolved.
# These are explicit composite survey labels, not a general dominant-member rule.
GOVERNMENT_LISTS = {('DE',400), ('FR',450), ('IT',501), ('RO',50)}


def classify_party(pl, pg_party, pg_nat, iso, party_id, year=2009):
    country_name = pg_party.loc[party_id, 'country_name']
    rows = pl[pl.country_name.eq(country_name) & pl.parlgov_id.eq(party_id)]
    if (iso, party_id) in IDENTITY_FLAGS:
        return None, None, 'identity_review', IDENTITY_FLAGS[iso, party_id]
    if len(rows) > 1:
        return None, None, 'duplicate_populist_id', 'Multiple PopuList rows share identifier'
    if len(rows) == 1:
        r = rows.iloc[0]
        return (int(r['populist'] == 1 and r.populist_start <= year <= r.populist_end),
                int(r['populist'] == 1 and r.populist_startnobl <= year <= r.populist_endnobl),
                'explicit_populist_row', str(r.party_name_short))
    qualifying = pg_nat[pg_nat.party_id.eq(party_id)]
    if ((qualifying.vote_share.ge(2)) | qualifying.seats.ge(1)).any():
        return 0, 0, 'eligible_not_listed', 'National seat or >=2% since 1989; absent from PopuList list'
    return None, None, 'coverage_unverified', 'No national seat/2% eligibility verified; absence is not a negative label'


def main():
    parties = pd.read_csv(source.audit_file('parlgov_party')).set_index('party_id')
    assert parties.index.is_unique
    elections = pd.read_csv(source.audit_file('parlgov_election'))
    cabinets = pd.read_csv(source.audit_file('parlgov_cabinet'))
    ep = elections[elections.election_type.eq('ep') & elections.election_date.str.startswith('2009')]
    assert ep.country_name.nunique() == 27 and len(ep) == 252
    national = elections[elections.election_type.eq('parliament') & elections.election_date.ge('1989-01-01')]
    versions = {'3': pd.read_excel(source.audit_file('populist3_release'), header=1),
                '4': pd.read_csv(source.audit_file('populist4_current'), sep=';')}
    scope = pd.read_csv(OUT / 'ep2009_classification_country_coverage.csv').set_index('iso2')
    gov_ids, gov_records = {}, []
    for iso, row in scope.iterrows():
        # ParlGov uses UK/GBR and ISO3 elsewhere; country-name linkage was reviewed.
        country = row.country
        g = cabinets[cabinets.country_name.eq(country) & cabinets.start_date.lt('2009-06-04')]
        g = g[g.start_date.eq(g.start_date.max())]
        assert not g.empty and g.cabinet_id.nunique() == 1
        gov_ids[iso] = set(g.loc[g.cabinet_party.eq(1), 'party_id'])
        gov_records.append({'country':iso,'parlgov_cabinet':g.cabinet_name.iloc[0],
                            'start_date':g.start_date.iloc[0], 'government_party_ids':'|'.join(map(str,sorted(gov_ids[iso]))),
                            'party_government_comparison_usable':iso not in ['CZ','HU'],
                            'source':'ParlGov development 2023-11-04; PPEG candidate registry checked separately'})
    dictionary = pd.read_csv(OUT / 'eurobarometer713_party_response_dictionary.csv')
    rows = []
    for r in dictionary[dictionary.named_response_option].itertuples(index=False):
        iso, code = r.country, r.code
        ids = NI_MATCHES if r.variable == 'v554' else MATCHES[iso]
        pid = ids.get(code,0)
        issue = COALITIONS.get((iso,code),'')
        if iso == 'GB':
            # Separate NI ballot geography. Conservatives in NI could refer to
            # UCUNF; SDLP is not a GB choice. Do not infer a move or intended party.
            if (r.variable == 'v553' and code in [50,100,201]) or (r.variable == 'v554' and code in [200,301,500,600,700,951]):
                issue = 'Party response inconsistent with region-specific ballot; review without recoding'
            if r.variable == 'v554' and code == 50:
                issue = 'UCUNF joint Conservative/UUP list; component classification pending'
        country = scope.loc[iso,'country']
        if pid:
            assert pid in parties.index and parties.loc[pid,'country_name'] == country
        in_ep = bool(pid and ((ep.country_name.eq(country)) & ep.party_id.eq(pid)).any())
        if (iso,code) == ('DE',400):
            in_ep = set([808,1180]).issubset(set(ep.loc[ep.country_name.eq(country),'party_id']))
        # Named independent candidates and subnational alliances are not ordinary
        # parties by default, even when ParlGov gives their list an identifier.
        if pid and str(parties.loc[pid,'party_name_short']).startswith('I-'):
            issue = 'Named independent candidate is outside party-ideology classification'
        if not pid:
            issue = issue or 'No reviewed ballot-identity crosswalk'
        elif not in_ep:
            issue = issue or 'Party identity proposed, but not independently verified in EP election rows'
        gov = None
        if in_ep and not issue and iso not in ['CZ','HU']:
            gov = int(pid in gov_ids[iso] or (iso,code) in GOVERNMENT_LISTS)
        row = {'country':iso,'sample':r.sample,'variable':r.variable,'code':code,'survey_label':r.label,
               'parlgov_party_id':pid or None,
               'parlgov_party_name':parties.loc[pid,'party_name_english'] if pid else '',
               'ep_participant_verified':in_ep,'government':gov,
               'identity_or_coalition_issue':issue,
               'government_source':'ParlGov cabinet before 2009-06-04',
               'ballot_source':'ParlGov EP 2009 election table; aggregate components explicit for CDU/CSU'}
        for version, pl in versions.items():
            eligible_national = national[national.election_date.le('2022-12-31')] if version == '3' else national
            incl,strict,status,note = classify_party(pl,parties,eligible_national,iso,pid) if pid else (None,None,'unmapped','')
            if issue or not in_ep:
                incl = strict = None
            row.update({f'populist_v{version}_inclusive':incl,f'populist_v{version}_strict':strict,
                        f'populist_v{version}_basis':status,f'populist_v{version}_note':note})
            for rule,val in [('inclusive',incl),('strict',strict)]:
                category = 'unresolved'
                if gov == 1:
                    category = 'government'
                elif gov == 0 and val is not None:
                    category = 'populist_opposition' if val else 'other_opposition'
                row[f'outcome_v{version}_{rule}'] = category
        rows.append(row)
    cross = pd.DataFrame(rows)
    assert not cross.duplicated(['sample','variable','code']).any()
    # Never backcast named successor parties via an externally supplied ID.
    for iso,pid in IDENTITY_FLAGS:
        sub=cross[cross.country.eq(iso)&cross.parlgov_party_id.eq(pid)]
        assert sub.populist_v4_inclusive.isna().all()
    for iso,code in [('FI',50),('NL',411)]:
        assert cross.loc[cross.country.eq(iso)&cross.code.eq(code),'outcome_v4_inclusive'].eq('unresolved').all()
    path=eb.verified_download('ZA4973_v3-0-0.sav')
    cols=['v6','v37','v54','v105','v216','v217','v541','v666','v796']
    cols += [f'v{i}' for i in range(133,151)] + [f'v{v[1]}' for v in eb.SAMPLES.values()]
    d,_=pyreadstat.read_sav(path,usecols=sorted(set(cols)),user_missing=True)
    priority,_,_=eb.priority_mask(d,133)
    adult=d.v37.eq(1)&d.v666.between(18,98)
    joint=adult&d.v105.isin([1,2,3,4])&priority&d.v216.isin([1,2])&d.v217.isin([1,2])
    aggregate, coverage=[],[]
    for iso in sorted(scope.index):
        base=adult & d.v6.isin([s for s,(c,_) in eb.SAMPLES.items() if c==iso])
        options=pd.Series(False,index=d.index)
        for version in ['3','4']:
            for rule in ['inclusive','strict']:
                outcome=pd.Series('unresolved',index=d.index)
                for r in cross[cross.country.eq(iso)].itertuples(index=False):
                    select=d.v6.eq(r.sample)&d.v541.eq(1)&d[r.variable].eq(r.code)
                    outcome.loc[select]=getattr(r,f'outcome_v{version}_{rule}')
                    options |= select
                outcome.loc[d.v541.eq(2)]='nonvote'
                for sample_type,mask in [('all_adults',base),('joint_attitudes',base&joint)]:
                    for category in ['government','other_opposition','populist_opposition','nonvote','unresolved']:
                        select=mask&outcome.eq(category)
                        aggregate.append({'country':iso,'version':version,'rule':rule,'sample_type':sample_type,
                                          'category':category,'n':int(select.sum()),'weight_sum':float(d.loc[select,'v54'].sum())})
                known=outcome.isin(['government','other_opposition','populist_opposition'])
                coverage.append({'country':iso,'version':version,'rule':rule,
                                 'joint_named_option_n':int((base&joint&options).sum()),
                                 'joint_classified_vote_n':int((base&joint&known).sum()),
                                 'joint_unresolved_named_option_n':int((base&joint&options&~known).sum())})
    for name,frame in [('ep2009_vote_crosswalk',cross),('ep2009_parlgov_cabinets',pd.DataFrame(gov_records)),
                        ('ep2009_outcome_marginals',pd.DataFrame(aggregate)),('ep2009_outcome_coverage',pd.DataFrame(coverage))]:
        frame.to_csv(OUT/(name+'.csv'),index=False)
    agg=pd.DataFrame(aggregate)
    selected=agg[agg.version.eq('4')&agg.rule.eq('inclusive')&agg.sample_type.eq('joint_attitudes')]
    counts=selected.pivot(index='country',columns='category',values='n')
    assert counts.sum().sum() == int(joint.sum())
    cov = pd.DataFrame(coverage)
    for (_, _), group in cov.groupby(['version', 'rule']):
        assert group.joint_named_option_n.sum() == 11798
        assert (group.joint_classified_vote_n + group.joint_unresolved_named_option_n).equals(group.joint_named_option_n)
    summary={'method':'Conservative partial crosswalk; unreviewed coalitions/identity changes are unresolved',
             'survey_options':len(cross),'options_with_ep_identity':int(cross.ep_participant_verified.sum()),
             'joint_counts_v4_inclusive':counts.sum().to_dict(),
             'countries_with_each_three_vote_category_observed':int(counts[['government','other_opposition','populist_opposition']].gt(0).all(axis=1).sum()),
             'countries_with_at_least_30_in_each_vote_category':int(counts[['government','other_opposition','populist_opposition']].ge(30).all(axis=1).sum()),
             'identity_flags':[{'country':c,'party_id':p,'reason':v} for (c,p),v in IDENTITY_FLAGS.items()],
             'limitations':['Counts are unweighted feasibility counts, not attitudes/outcome associations or power estimates.',
                            'Other opposition means within verified PopuList scope and not classified populist under the selected version/rule.',
                            'Post-election attitudes do not identify prior change or causes of voting.',
                            'Czech and Hungarian caretaker periods have no automatic government/opposition assignment.',
                            'ParlGov may aggregate alliances and party successors; unresolved entries cannot inherit the leading party label.',
                            'Official EP summaries have been acquired, but they aggregate small lists and are not a complete ballot catalogue.',
                            'Partial mapping is not final analysis eligibility. Cross-country exclusions are not chosen from effects.',
                            'Unresolved votes and nonvoters stay distinct. Zero observed populist votes is not absence of populist supply.']}
    (OUT/'ep2009_crosswalk_audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    print(counts.to_string())

if __name__=='__main__':
    main()
