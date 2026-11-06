"""Audit official CIS 7715 panel: availability, timing and sample composition.

Parse the published fixed-width layout as data. Never execute downloaded SPSS
syntax. Write only aggregate counts and variable metadata, not respondent rows.
"""
from pathlib import Path
import io
import json
import re
import zipfile
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/audit_20261106'
OUT = ROOT / 'data/processed/audit_20261106'

def read_cis(study):
    with zipfile.ZipFile(RAW / f'cis_{study}_data.zip') as z:
        syntax = z.read(f'ES{study}').decode('cp1252')
        layout = syntax.split('VARIABLE LABELS')[0]
        specs = re.findall(r'\b([A-Z][A-Z0-9_]*)\s+(\d+)(?:-(\d+))?(?:\((\d+)\))?', layout)
        names = [s[0] for s in specs]
        assert len(set(names)) == len(names)
        positions = [(int(s[1])-1,int(s[2] or s[1])) for s in specs]
        raw = z.read(f'DA{study}').decode('cp1252')
        lengths = {len(line) for line in raw.splitlines()}
        assert lengths == {max(end for _,end in positions)}, lengths
        d = pd.read_fwf(io.StringIO(raw), colspecs=positions, names=names)
        for name,_,_,decimals in specs:
            if decimals:
                # CIS writes a literal Spanish decimal comma, not an integer.
                d[name] = pd.to_numeric(d[name].astype('string').str.replace(',', '.', regex=False))
        labeltext = syntax.split('VARIABLE LABELS')[1].split('VALUE LABELS')[0]
        labels = {v:t.replace("''", "'") for v,t in re.findall(r"/?\b([A-Z][A-Z0-9_]*)\s+'((?:[^']|'')*)'", labeltext)}
        meta = pd.DataFrame([{'study':study,'variable':name,'start_1_based':start,
                             'end_1_based':end or start,'declared_decimals':decimals or 0,
                             'source_label':labels.get(name,'')} for name,start,end,decimals in specs])
        return d,meta

SPECS = {
    'P4':('national_economy_current','pre',1,5),
    'P5':('incumbent_government_performance_4_years','pre',1,5),
    'P11R':('named_vote_intention','pre',1,24),
    'PP201':('politicians_do_not_care','post',1,4),
    'PP203':('any_ruler_seeks_personal_interests','post',1,4),
    'PP301':('personal_issue_priority_first','post',1,97),
    'PP302':('personal_issue_priority_second','post',1,97),
    'PP303':('personal_issue_priority_third','post',1,97),
    'PP601':('trust_parliament','post',0,10),
    'PP602':('trust_political_parties','post',0,10),
    'PP8':('national_economy_current','post',1,5),
    'PP9':('national_economy_retrospective_4_years','post',1,5),
    'PP31R':('named_party_vote_2015','post',1,24),
    'PP59':('personal_economy_current','post',1,5),
    'PP60':('personal_economy_retrospective_4_years','post',1,5),
}

def main():
    pre,pre_meta = read_cis(3117)
    post,post_meta = read_cis(3126)
    panel,meta = read_cis(7715)
    assert len(pre)==17452 and len(post)==6242 and len(panel)==6242
    # The producer supplies the matched panel; no inferred linkage is used.
    assert panel.CUES.is_unique and pre.CUES.is_unique
    joined = panel[['CUES','P4','P5','P27','P28']].merge(
        pre[['CUES','P4','P5','P27','P28']],on='CUES',how='left',
        suffixes=('_panel','_pre'),validate='one_to_one',indicator=True)
    matched = joined['_merge'].eq('both').all()
    exact = matched and all(joined[v+'_panel'].equals(joined[v+'_pre']) for v in ['P4','P5','P27','P28'])
    # Only mark retention in the full first wave if IDs and repeated answers agree.
    composition=[]
    if exact:
        pre['retained'] = pre.CUES.isin(panel.CUES)
        for variable,concept,valid in [('P27','sex',[1,2]),('P4','pre_economy',[1,2,3,4,5]),('P5','pre_government_performance',[1,2,3,4,5])]:
            for value,g in pre[pre[variable].isin(valid)].groupby(variable):
                composition.append({'variable':variable,'concept':concept,'value':value,'n_pre':len(g),
                                    'n_in_official_panel':int(g.retained.sum()),
                                    'panel_fraction':g.retained.mean(),
                                    'note':'Selection into follow-up plus nonresponse; not an attrition rate among invitees.'})
    rows=[]; masks={}
    for var,(concept,timing,lo,hi) in SPECS.items():
        assert var in panel,var
        masks[var]=panel[var].between(lo,hi)
        rows.append({'variable':var,'concept':concept,'timing':timing,'n_panel':len(panel),
                     'valid_n':int(masks[var].sum()),'valid_pct':100*masks[var].mean(),
                     'valid_min':lo,'valid_max':hi,
                     'source_label':meta.set_index('variable').loc[var,'source_label']})
    groups={
        'pre_economy_government_and_post_named_vote':['P4','P5','PP31R'],
        'post_economy_priority_party_trust_and_named_vote':['PP8','PP301','PP602','PP31R'],
        'pre_economy_government_post_priority_trust_named_vote':['P4','P5','PP301','PP602','PP31R'],
        'pre_intention_and_post_named_vote':['P11R','PP31R'],
    }
    joint=[]
    for name,variables in groups.items():
        mask=pd.concat([masks[v] for v in variables],axis=1).all(axis=1)
        w=panel.loc[mask,'PESO']
        joint.append({'comparison':name,'variables':'|'.join(variables),'n':int(mask.sum()),
                      'kish_n_weight_only':float(w.sum()**2/(w**2).sum()),
                      'note':'Kish count describes weight dispersion, not full survey design or identification.'})
    joint.append({'comparison':'all_three_explanations_measured_before_election','variables':'absent','n':0,
                  'kish_n_weight_only':0,'note':'No direct priority or political elite trust question in pre-election wave.'})
    pd.concat([pre_meta,post_meta,meta]).to_csv(OUT/'cis_variable_inventory.csv',index=False)
    pd.DataFrame(rows).to_csv(OUT/'cis_panel_coverage.csv',index=False)
    pd.DataFrame(joint).to_csv(OUT/'cis_panel_joint_coverage.csv',index=False)
    pd.DataFrame(composition,columns=['variable','concept','value','n_pre',
        'n_in_official_panel','panel_fraction','note']).to_csv(OUT/'cis_panel_selection.csv',index=False)
    result={'n_pre':len(pre),'n_followup_planned':7798,'n_post':len(post),'n_official_panel':len(panel),
            'panel_id_and_repeated_answers_verified_against_pre':bool(exact),
            'n_panel_ids_present_in_separate_pre_release':int(joined['_merge'].eq('both').sum()),
            'repeated_value_agreement_fraction':{v:float(joined[v+'_panel'].eq(joined[v+'_pre']).mean()) for v in ['P4','P5','P27','P28']},
            'linkage_basis':'Official producer-supplied joint panel 7715. Independent exact join to separate 3117 release not used.',
            'pre_fieldwork':['2015-10-27','2015-11-16'],'post_fieldwork':['2016-01-07','2016-03-19'],
            'election':'2015-12-20','joint':joint,
            'limitations':['No pre-election trust or issue priority measure.',
                           'Follow-up selects sections and consenting respondents; 6242/17452 is not response rate.',
                           'No crisis-free counterfactual; all observations are years after 2008.',
                           'Unspecified other party and nonvoters excluded only from named-party audit counts, not from future turnout analysis.']}
    (OUT/'cis_panel_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
