"""Freeze national party identities, dated PopuList rules and cabinet outcomes."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'analysis'/file)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
inputs=module('national_inputs','79_national_comparison_inputs.py')
source=module('national_parties','47_party_classification_audit.py')
OUT=inputs.OUT
# English names are exact PPEG names. Explicit PopuList IDs handle aliases.
PARTIES={
 'ES2015':{
  1:("People's Party",None),2:("Spanish Socialist Workers' Party",None),
  3:('We can',2376),4:('Citizens',None),5:('Popular Unity',None),
  6:('In Common We Can',None),7:('It is time',None),8:('Catalan Republican Left',None),
  9:('Democracy and Freedom',None),10:('In Tide',None),11:('Basque Nationalist Party',None),
  12:('Basque Country Unite',2603),13:('Canarian Coalition',None),
  14:(None,None),15:(None,None),16:(None,None),17:(None,None),18:(None,None),19:(None,None),
  20:('Union, Progress and Democracy',None),21:(None,None),22:('Yes to the Future',None),
  23:('Democratic Union of Catalonia',None),24:(None,None),25:(None,None)},
 'NL2010':{1:('Christian Democratic Appeal',None),2:('Labour Party',None),
  3:("People's Party for Freedom and Democracy",None),4:('Green Left',None),
  5:('Socialist Party',357),6:("Democrats '66",None),7:('Christian Union',None),
  8:('Political Reformed Party',None),9:('Party for Freedom',1501),
  10:('Party for the Animals',None),11:(None,None)},
 'PT2005':{1:('Left Bloc',557),2:('Social Democratic Center - Popular Party',None),
  3:('CDU: PCP + PEV',None),4:('Social Democratic Party',None),5:('Portuguese Socialist Party',None),6:(None,None)},
 'IS2013':{1:('The Alliance - Social Democratic Party of Iceland',None),
  2:('Progressive Party',1455),3:('Independence Party',None),4:('Left Green Movement',None),
  5:('Bright Future',None),6:('Pirate Party',None),
  **{k:(None,None) for k in [7,8,10,12,13,14]}},
 'BE2014':{1:('Christian Democrats & Flemish',None),2:('Green',None),3:('New Flemish Alliance',501),
  4:('Socialist Party Different',None),5:('Flemish Interest',993),
  6:('Open Flemish Liberals and Democrats',None),7:(None,221),8:("Workers' Party of Belgium",256),
  20:('Francophone Socialist Party',None),21:('Reform Movement',None),
  22:('Democratic and Humanist Center',None),23:('Francophone Greens',None),
  24:('Francophone Democratic Federalists',None),25:(None,171),
  26:("Workers' Party of Belgium",256),27:('Popular Party',438)},
 'DK2007':{1:('Social Democrats',None),2:('Danish Social Liberal Party',None),
  3:("Conservative People's Party",None),5:("Socialist People's Party",1644),
  6:('Christian Democrats',None),7:("Danish People's Party",1418),8:('New Alliance',None),
  9:("Left, Denmark's Liberal Party",None),10:('Red-Green Unity List',306)},
}
PARTIES['NL2012']={**PARTIES['NL2010'],12:('50plus',None)}
PARTIES['PT2009']={**{k:v for k,v in PARTIES['PT2005'].items() if k!=6},
                  **{k:(None,None) for k in range(8,21)}}
GOV={'ES2015':{1},'NL2010':{1,7},'NL2012':{1,3},'PT2005':{2,4},
     'PT2009':{5},'IS2013':{1,4},'BE2014':{1,4,6,20,21,22},'DK2007':{3,9}}
MIXED_ES={5,6,7,9,10}


def make_crosswalk():
    parl,gov=source.ppeg('parl'),source.ppeg('comb')
    lists={'3':pd.read_excel(source.audit_file('populist3_release'),header=1),
           '4':pd.read_csv(source.audit_file('populist4_current'),sep=';')}
    rows=[];cabinets=[]
    for key,cfg in inputs.CONFIG.items():
        _,_,labels=inputs.load_source(key)
        history=parl[parl.iso3c.eq(cfg['iso'])&parl.edate.between('1989-01-01','2022-12-31')]
        election=history[history.edate.eq(cfg['date'])]
        cabinet=source.cabinet_record(gov,cfg['iso'],pd.Timestamp(cfg['date']),key)
        expected={PARTIES[key][c][0] for c in GOV[key]}
        if key=='IS2013':expected.discard('The Alliance - Social Democratic Party of Iceland');expected.add('The Alliance')
        observed=set(cabinet['government_parties'].split(' | '))-{'Independents/Non-Partisans (Cabinet)'}
        assert expected==observed,(key,expected,observed)
        cabinet['status']='Named cabinet parties checked; nonpartisans have no survey ballot; external supporters excluded'
        cabinets.append(cabinet)
        for code,(name,pid) in PARTIES[key].items():
            assert code in labels[cfg['vote']],(key,code)
            present=name is not None and name in set(election.pname_en)
            h=history[history.pname_en.eq(name)]
            eligible=bool((h.v_share_wgt.ge(.02)|h.seats.ge(1)).any())
            mixed=key=='ES2015' and code in MIXED_ES
            components=None
            if key.startswith('PT') and code==3:
                components=['Portuguese Communist Party','Ecologist Party "The Greens"']
                present=all(n in set(election.pname_en) for n in components)
                eligible=all((history.loc[history.pname_en.eq(n),'v_share_wgt'].ge(.02)|
                              history.loc[history.pname_en.eq(n),'seats'].ge(1)).any() for n in components)
            row={'dataset':key,'year':cfg['year'],'country':cfg['country'],'survey_code':code,
                 'survey_label':labels[cfg['vote']][code],'ppeg_name':name or '',
                 'populist_id':pid,'national_participation_verified':bool(present),
                 'national_scope_eligible':eligible,'mixed_list_unresolved':mixed,
                 'incumbent':code in GOV[key]}
            for ver,pl in lists.items():
                m=pl[pl.country_name.eq(cfg['country'])&pl.parlgov_id.eq(pid)] if pid else pl.iloc[:0]
                assert len(m)<=1
                values={r:np.nan for r in ['inclusive','strict']};basis='unresolved_identity_or_scope'
                if present and not mixed and len(m):
                    a=m.iloc[0];y=cfg['year']
                    values={'inclusive':int(a['populist']==1 and a.populist_start<=y<=a.populist_end),
                            'strict':int(a['populist']==1 and a.populist_startnobl<=y<=a.populist_endnobl)}
                    basis='explicit_dated_PopuList_row'
                elif present and eligible and not mixed:
                    if components:
                        # PCP has an explicit nonpopulist row; PEV is eligible
                        # and absent. Coalition membership is not a largest-party rule.
                        a=pl[pl.country_name.eq('Portugal')&pl.parlgov_id.eq(514)]
                        assert len(a)==1 and a['populist'].iloc[0]==0
                        assert not pl[pl.country_name.eq('Portugal')].party_name_english.str.contains('Green',case=False).any()
                        basis='PCP_explicit_zero_PEV_eligible_unlisted'
                    else:
                        assert not (pl.country_name.eq(cfg['country'])&pl.party_name_english.eq(name)).any(),(key,code)
                        basis='eligible_national_party_not_listed'
                    values={'inclusive':0,'strict':0}
                elif mixed:basis='coalition_identity_requires_component_classification'
                row[f'v{ver}_basis']=basis
                for rule,value in values.items():
                    row[f'populist_v{ver}_{rule}']=value
                    row[f'outcome_v{ver}_{rule}']=0 if code in GOV[key] else -1 if pd.isna(value) else 2 if value else 1
            rows.append(row)
    return pd.DataFrame(rows),pd.DataFrame(cabinets)


def add_outcomes(x,key,cw):
    x=x.copy();c=cw[cw.dataset.eq(key)]
    for ver in ['3','4']:
        for rule in ['inclusive','strict']:
            name=f'outcome_v{ver}_{rule}'
            x[name]=x.party_code.map(c.set_index('survey_code')[name]).fillna(-1).astype(int)
            x.loc[~x.turnout.eq(1),name]=-1
            x.loc[x.turnout.eq(0),name]=3
    # Cabinet membership does not require resolving an opposition's populism.
    named=x.party_code.isin(c.loc[c.national_participation_verified,'survey_code']) & x.turnout.eq(1)
    # Other/unidentified parties still count as known turnout, but do not
    # become a named opposition choice for this comparison.
    x['government_vote']=np.nan
    x.loc[named,'government_vote']=x.loc[named,'party_code'].isin(GOV[key]).astype(int)
    x['nonvote']=1-x.turnout
    x['outcome_es_coalitions']=x.outcome_v4_inclusive
    if key=='ES2015':
        # Deliberately labelled scenario, not a factual primary assignment.
        x.loc[x.turnout.eq(1)&x.party_code.isin([6,7,10]),'outcome_es_coalitions']=2
        x.loc[x.turnout.eq(1)&x.party_code.isin([5,9]),'outcome_es_coalitions']=1
    x['outcome_nl_previous_cabinet']=x.outcome_v4_inclusive
    if key=='NL2010':x.loc[x.turnout.eq(1)&x.party_code.eq(2),'outcome_nl_previous_cabinet']=0
    return x


def analytic_sample(x,target,outcome='outcome_v4_inclusive'):
    q=x[x.eligible & x[inputs.CORE].notna().all(axis=1)&x.weight.gt(0)].copy()
    if target=='government_vs_opposition':q['y']=q.government_vote
    elif target=='nonvote_vs_vote':q['y']=q.nonvote
    elif target=='opposition_type':q['y']=q[outcome].map({1:0,2:1})
    else:q['y']=q[outcome].where(q[outcome].ge(0))
    q=q[q.y.notna()].copy();q['y']=q.y.astype(int)
    return q


def main():
    cw,cab=make_crosswalk();cw.to_csv(OUT/'national_party_crosswalk.csv',index=False)
    cab.to_csv(OUT/'national_incumbent_cabinets.csv',index=False)
    rows=[];counts=[]
    for key in inputs.CONFIG:
        x,_,_=inputs.construct(key);x=add_outcomes(x,key,cw)
        core=x.eligible & x[inputs.CORE].notna().all(axis=1)&x.weight.gt(0)
        for version in ['3','4']:
            for rule in ['inclusive','strict']:
                o=f'outcome_v{version}_{rule}'
                for c in [-1,0,1,2,3]:
                    sel=core&x[o].eq(c)
                    rows.append(dict(dataset=key,version=version,rule=rule,outcome=c,core_n=int(core.sum()),
                                     n=int(sel.sum()),weight_share=float(x.loc[sel,'weight'].sum()/x.loc[core,'weight'].sum())))
        for target in inputs.TARGETS:
            q=analytic_sample(x,target);classes=q.y.value_counts().to_dict()
            expected={0,1} if target!='all_outcomes' else {0,1,2,3}
            valid=set(classes)==expected and min(classes.values())>=20
            # PT has no classified populist alternative: three-outcome
            # comparison remains useful, with no invented positive class.
            if key.startswith('PT') and target=='all_outcomes':valid=set(classes)=={0,1,3} and min(classes.values())>=20
            counts.append(dict(dataset=key,target=target,n=len(q),class_counts=json.dumps(classes,sort_keys=True),
                               estimable=valid,minimum_class_rule=20))
    pd.DataFrame(rows).to_csv(OUT/'national_outcome_coverage.csv',index=False)
    pd.DataFrame(counts).to_csv(OUT/'national_locked_counts.csv',index=False)
    print(pd.DataFrame(counts).to_string(index=False))


if __name__=='__main__':main()
