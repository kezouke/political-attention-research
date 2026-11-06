"""Availability and temporal ordering in the official CC BY BES teaching panel.

No vote model or estimate of political associations. The restricted variable
selection avoids exporting individual rows and importing wave-25 profile fields
as if they were known in 2014. Count availability, including panel overlap.
"""
from pathlib import Path
import hashlib
import io
import json
import zipfile
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw/audit_20261106'
OUT=ROOT/'data/processed/audit_20261106'
SPECS={
 'econGenRetro':('national_economy_past_12_months',[1,2,3,4,5]),
 'econPersonalRetro':('household_economy_past_12_months',[1,2,3,4,5]),
 'small_mii_cat':('most_important_national_issue',[1,2,3,4,5,7,8,9,10,11,12,13]),
 'trustMPs':('trust_members_of_parliament',list(range(1,8))),
 'generalElectionVote':('named_party_vote_or_intention',[1,2,3,4,5,6,7,8,11,12]),
 'approveUKGovt':('government_approval',list(range(1,6))),
 'partyId':('party_identification',[1,2,3,4,5,6,7,8,11,12]),
 'bestOnMII':('party_competence_on_important_issue',[0,1,2,3,4,5,6,7,8,11,12]),
}

def main():
    path=RAW/'bes_teaching_long_v1.zip'
    metadata=json.loads((RAW/'bes_teaching_figshare.json').read_text())
    f=next(x for x in metadata['files'] if x['name']=='BESIP_teaching_long.dta.zip')
    assert hashlib.md5(path.read_bytes()).hexdigest()==f['computed_md5']
    with zipfile.ZipFile(path) as z:
        b=io.BytesIO(z.read('BESIP_teaching_long.dta'))
        with pd.io.stata.StataReader(b,convert_categoricals=False) as reader:
            labels=reader.variable_labels()
            values=reader.value_labels()
            d=reader.read(columns=['id','wave','weight',*SPECS])
    assert not d.duplicated(['id','wave']).any()
    n_all=len(d); ids_all=d.id.nunique()
    d=d[d.wave.between(1,19)].copy()
    rows=[];coverage=[]
    for var,(concept,allowed) in SPECS.items():
        d['valid_'+var]=d[var].isin(allowed)
        for wave,g in d.groupby('wave'):
            rows.append({'wave':int(wave),'variable':var,'concept':concept,'n_rows':len(g),
                         'valid_n':int(g['valid_'+var].sum()),
                         'source_label':labels[var]})
    for wave,g in d.groupby('wave'):
        valid=g[['valid_'+v for v in ['econGenRetro','small_mii_cat','trustMPs']]].all(axis=1)
        coverage.append({'wave':int(wave),'n_rows':len(g),'n_joint_economy_priority_trust':int(valid.sum()),
                         'n_positive_weight':int(g.weight.gt(0).sum())})
    pairs=[]
    # Dates verified in producer's waves 1-19 documentation. Wave 10 precedes
    # the 2017 election but follows Brexit. These are not pre-2008 observations.
    for pre,post,year in [(4,6,2015),(10,13,2017),(17,19,2019)]:
        before=d[d.wave.eq(pre)].set_index('id')
        after=d[d.wave.eq(post)].set_index('id')
        matched=before.merge(after,how='inner',left_index=True,right_index=True,
                             suffixes=('_pre','_post'),validate='one_to_one')
        prevars=['econGenRetro','small_mii_cat','trustMPs']
        complete=matched[['valid_'+v+'_pre' for v in prevars]].all(axis=1)
        named=matched.valid_generalElectionVote_post
        base=matched.valid_generalElectionVote_pre
        gov=matched.valid_approveUKGovt_pre
        pairs.append({'election_year':year,'pre_wave':pre,'post_wave':post,
                      'n_pre':len(before),'n_post':len(after),'n_same_person':len(matched),
                      'n_pre_all_three_and_post_named_vote':int((complete&named).sum()),
                      'n_also_pre_named_intention':int((complete&named&base).sum()),
                      'n_also_pre_government_approval':int((complete&named&gov).sum()),
                      'n_also_pre_intention_and_government_approval':int((complete&named&base&gov).sum()),
                      'n_positive_pre_weight_among_joint':int((complete&named&matched.weight_pre.gt(0)).sum()),
                      'longitudinal_weight_verified':False,
                      'pre_crisis_baseline':False})
    pd.DataFrame(rows).to_csv(OUT/'bes_variable_coverage.csv',index=False)
    pd.DataFrame(coverage).to_csv(OUT/'bes_wave_coverage.csv',index=False)
    pd.DataFrame(pairs).to_csv(OUT/'bes_panel_joint_coverage.csv',index=False)
    (OUT/'bes_teaching_variable_inventory.json').write_text(json.dumps(labels,indent=2)+'\n')
    (OUT/'bes_teaching_value_labels.json').write_text(json.dumps({k:{str(kk):vv for kk,vv in v.items()} for k,v in values.items()},indent=2)+'\n')
    summary={'release_doi':metadata['doi'],'release_file_md5':f['computed_md5'],
             'all_release_rows':n_all,'all_release_distinct_people':ids_all,
             'waves_1_19_rows':len(d),'waves_1_19_distinct_people':d.id.nunique(),
             'pairs':pairs,'cautions':['No observation before 2014, no identification of a 2008 crisis effect.',
              'Online YouGov panel; attrition, selection and longitudinal weights need audit before population claims.',
              'Trust in MPs is not itself a full populist-attitude scale or a measure of exposure to party rhetoric.',
              'The collapsed MII categories do not isolate corruption, elite blame, or every economic concern.',
              'Named party counts exclude unspecified other party, nonvoting and missing; future models must retain separate abstention outcomes.',
              'Pre-election temporal order does not remove party-driven perceptions or time-varying confounding.',
              'Do not use profile attributes collected at wave 25 as baseline historical controls.']}
    (OUT/'bes_panel_audit.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
