"""Audit separate issue positions and issue importance, without voting models.

The 2009 instrument split 7- and 11-point position scales. Keep scale assignment
explicit; endpoint rescaling is a sensitivity assumption, not measurement
invariance. Only metadata and aggregate availability/consistency checks export.
"""
from pathlib import Path
import importlib.util
import json
import re

import pandas as pd
import pyreadstat

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/processed/audit_20261106'
spec=importlib.util.spec_from_file_location('gles',ROOT/'analysis/46_gles_panel_audit.py')
gles=importlib.util.module_from_spec(spec);spec.loader.exec_module(gles)
spec=importlib.util.spec_from_file_location('eb',ROOT/'analysis/45_eurobarometer_audit.py')
eb=importlib.util.module_from_spec(spec);spec.loader.exec_module(eb)
TOPICS={
 'tax_welfare':{'position_09':'kp1_1090','importance_09':'kp1_1100','position_13':'kp9_1090','importance_13':'kp9_1100'},
 'immigration':{'position_09':'kp1_1130','importance_09':'kp1_1140','position_13':'kp9_1130','importance_13':'kp9_1140'},
 'climate_growth':{'position_09':'kp2_1290','importance_09':'kp2_1300','position_13':'kp9_1290','importance_13':'kp9_1300'},
}


def load_extra(filename):
    path=eb.verified_download(filename)
    _,m=pyreadstat.read_dta(path,metadataonly=True)
    cols=[v for v in m.column_names if re.match(r'kp\d+_(1090|1100|1130|1140|1290|1300)(_[17][1]?)?$',v)
          or v in ['lfdn','mut09','mut0913']]
    d,_=pyreadstat.read_dta(path,usecols=cols)
    return d,m


def base(d,m,year):
    econ,att=(1,2) if year==2009 else (8,10)
    return (gles.valid_scale(d,f'kp{econ}_800')&gles.issue_available(d,m,att)
            &gles.valid_scale(d,f'kp{att}_040a')&gles.valid_scale(d,f'kp{att}_040c')
            &d[f'kp{att}_170'].isin(range(1,6)))


def main():
    d,m=gles.read_selected('ZA5757_v1-1-0.dta')
    x,_=load_extra('ZA5757_v1-1-0.dta')
    d=d.merge(x.drop(columns=['mut09','mut0913']),on='lfdn',validate='one_to_one')
    assert len(d)==1025
    p09,m09=load_extra('ZA5305_en_v5-0-0.dta')
    p13,m13=load_extra('ZA5704_en_v3-2-0.dta')
    agreement=[]
    for topic,v in TOPICS.items():
        linked=d[['lfdn09','lfdn13',v['position_09'],v['importance_09'],v['position_13'],v['importance_13']]]
        a=linked.merge(p09,left_on='lfdn09',right_on='lfdn',validate='one_to_one',suffixes=('_l','_p'))
        pos=v['position_09'];imp=v['importance_09']
        seven=a[pos+'_7'].isin(range(1,8));eleven=a[pos+'_11'].isin(range(1,12))
        assert not (seven&eleven).any()
        expected=a[pos+'_7'].where(seven,a[pos+'_11'].where(eleven)+10)
        valid=a[pos].isin(list(range(1,8))+list(range(11,22)))
        assert valid.equals(seven|eleven)
        assert a.loc[valid,pos].eq(expected[valid]).all()
        li=a[imp+'_l'];pi=a[imp+'_p'];ok=li.isin(range(1,6))&pi.isin(range(1,6))
        assert li.isin(range(1,6)).equals(pi.isin(range(1,6))) and li[ok].eq(pi[ok]).all()
        parent_pos=v['position_13'].replace('kp9_','kp2_')
        parent_imp=v['importance_13'].replace('kp9_','kp2_')
        parent_values=p13[['lfdn',parent_pos,parent_imp]].rename(columns={parent_pos:'parent_position',parent_imp:'parent_importance'})
        b=linked.merge(parent_values,left_on='lfdn13',right_on='lfdn',validate='one_to_one')
        for lv,pv,top in [(v['position_13'],'parent_position',7),(v['importance_13'],'parent_importance',5)]:
            mask=b[lv].isin(range(1,top+1));assert mask.equals(b[pv].isin(range(1,top+1)))
            assert b.loc[mask,lv].eq(b.loc[mask,pv]).all()
        agreement.append({'topic':topic,'linked_valid_2009_7point':int(seven.sum()),
                          'linked_valid_2009_11point':int(eleven.sum()),
                          'parent_linked_substantive_disagreements':0})
    clean=d.mut09.eq(0)&d.mut0913.eq(0)
    outcomes={yr:gles.outcome(d,m,yr)[0]['named_vote_or_explicit_nonvote'] for yr in [2009,2013]}
    full={yr:clean&base(d,m,yr)&outcomes[yr] for yr in [2009,2013]}
    assert (full[2009]&full[2013]).sum()==391
    masks={};rows=[];meta=[]
    for topic,v in TOPICS.items():
        for variable in v.values():
            meta.append({'topic':topic,'variable':variable,'label':m.column_names_to_labels[variable],
                         'value_labels':m.variable_value_labels.get(variable,{})})
        pos09=d[v['position_09']];pos13=d[v['position_13']]
        imp09=d[v['importance_09']];imp13=d[v['importance_13']]
        for scale,valid09 in [('seven_only',pos09.isin(range(1,8))),
                              ('seven_or_eleven',pos09.isin(list(range(1,8))+list(range(11,22))))]:
            pair09=valid09&imp09.isin(range(1,6));pair13=pos13.isin(range(1,8))&imp13.isin(range(1,6))
            both=pair09&pair13
            masks[topic,scale]=both
            rows.append({'topic':topic,'position_scale_2009':scale,
                         'both_years_position_and_importance_clean_identity':int((both&clean).sum()),
                         'both_years_plus_core_attitudes_and_outcomes':int((both&full[2009]&full[2013]).sum()),
                         'extra_2013_position_code_11_observed':int(pos13.eq(11).sum())})
    for scale in ['seven_only','seven_or_eleven']:
        all_topics=pd.concat([masks[t,scale] for t in TOPICS],axis=1).all(axis=1)
        rows.append({'topic':'all_three','position_scale_2009':scale,
                     'both_years_position_and_importance_clean_identity':int((all_topics&clean).sum()),
                     'both_years_plus_core_attitudes_and_outcomes':int((all_topics&full[2009]&full[2013]).sum())})
    # 2013 within-campaign changes can use identical seven-point positions and
    # five-point importance in waves 2 and 4 (linked global 9 and 11).
    repeated=[]
    for t,v in TOPICS.items():
        pv=v['position_13'];iv=v['importance_13'];late_p=pv.replace('kp9_','kp11_');late_i=iv.replace('kp9_','kp11_')
        mask=(d[pv].isin(range(1,8))&d[late_p].isin(range(1,8))
              &d[iv].isin(range(1,6))&d[late_i].isin(range(1,6)))
        # Repeated attitudes must be before a reported postal vote, and intent
        # must be answered; later unknown routing cannot count as pre-vote.
        early=d.kp11_170.isin(range(1,6))
        repeated.append({'topic':t,'waves':'9_to_11','clean_identity_n':int((mask&clean).sum()),
                         'plus_core_attitudes_later_vote_and_not_already_postal':int((mask&full[2013]&early).sum())})
    # The full 2013 parent offers substantially more records than the long link.
    core13,cm=gles.read_selected('ZA5704_en_v3-2-0.dta')
    core13=core13.merge(p13,on='lfdn',validate='one_to_one')
    rename={v:re.sub(r'^kp(\d+)_',lambda q:f'kp{int(q[1])+7}_',v) for v in core13 if v.startswith('kp')}
    par=core13.rename(columns=rename)
    from types import SimpleNamespace
    pm=SimpleNamespace(variable_value_labels={rename.get(v,v):q for v,q in cm.variable_value_labels.items()})
    main13=base(par,pm,2013)&gles.outcome(par,pm,2013)[0]['named_vote_or_explicit_nonvote']
    parent_rows=[]
    for t,v in TOPICS.items():
        pv=v['position_13'];iv=v['importance_13'];late_p=pv.replace('kp9_','kp11_');late_i=iv.replace('kp9_','kp11_')
        early_pair=par[pv].isin(range(1,8))&par[iv].isin(range(1,6))
        both=early_pair&par[late_p].isin(range(1,8))&par[late_i].isin(range(1,6))
        parent_rows.append({'year':2013,'topic':t,'pre_position_importance_plus_core_and_outcome':int((early_pair&main13).sum()),
                            'repeated_position_importance_plus_core_and_outcome_before_postal':int((both&main13&par.kp11_170.isin(range(1,6))).sum())})
    summary={'linked_availability':rows,'linked_parent_agreement':agreement,'linked_2013_repeated':repeated,
             'full_2013_campaign':parent_rows,
             'limitations':['2009 and 2013 are both after crisis onset. No pre-crisis individual baseline.',
                            '2009 position assignment has seven- and eleven-point forms; use seven-point subgroup first for position changes.',
                            'Importance is absolute importance of each prompted topic, not a ranked choice or a fixed attention budget.',
                            'Climate position wording changes from willingness to accept economic harm to priority for climate versus growth.',
                            'Climate position change across years is not an invariant measure; within-2013 wording is consistent.',
                            'Questionnaire importance endpoints and codes have reversed visual direction; actual code 1 is high importance.',
                            'The 2009 wave-4 position variables are explicitly labelled incorrect in the parent release and are absent in the linked file; do not use them.',
                            'Availability counts do not measure issue change, effects, representativeness or model power.',
                            'Parent-link agreement is checked for every selected topic/scale; no row-level values are exported.']}
    for name,data in [('gles_position_importance_audit',summary),('gles_position_importance_metadata',meta)]:
        (OUT/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
