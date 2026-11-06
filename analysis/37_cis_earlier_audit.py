"""Audit older CIS files and document a response-list measurement break.

Use producer-supplied SPSS files, never run downloaded syntax. Output variable
metadata and availability counts only. The 2008 and 2011 respondents are not a
panel across elections; a within-election panel is a different design.
"""
from pathlib import Path
import json
import zipfile
import pandas as pd
import pyreadstat

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw/audit_20261106'
OUT=ROOT/'data/processed/audit_20261106'
SPECS={
 7708:{'s17':('national_economy_current',1,5),'s301':('personal_priority_first',1,10),
       's601':('trust_parliament',0,10),'s602':('trust_parties',0,10),
       's201':('rulers_seek_personal_interests',1,4),'s203':('politicians_do_not_care',1,4),
       's34':('named_party_vote',1,12)},
 2920:{'p8':('national_economy_current',1,5),'p9':('national_economy_retrospective_4_years',1,5),
       'p301':('personal_priority_first',1,10),'p601':('trust_parliament',0,10),
       'p602':('trust_parties',0,10),'p203':('rulers_seek_personal_interests',1,4),
       'p201':('politicians_do_not_care',1,4),'p36':('named_party_vote',1,14),
       'p1101':('crisis_responsibility_government',1,5),
       'p1105':('crisis_responsibility_banks',1,5)},
}

def main():
    rows=[];joint=[];categories=[]
    for study,spec in SPECS.items():
        with zipfile.ZipFile(RAW/f'cis_{study}_data.zip') as z:
            name=next(n for n in z.namelist() if n.endswith('.sav'))
            target=RAW/f'cis_{study}_embedded.sav'
            target.write_bytes(z.read(name))
        d,meta=pyreadstat.read_sav(target,apply_value_formats=False)
        assert len(d)=={7708:6083,2920:6082}[study]
        masks={}
        for var,(concept,lo,hi) in spec.items():
            assert var in d,var
            mask=d[var].between(lo,hi)
            masks[concept]=mask
            rows.append({'study':study,'election_year':2008 if study==7708 else 2011,
                         'variable':var,'concept':concept,'timing':'post_election',
                         'n':len(d),'valid_n':int(mask.sum()),'valid_min':lo,'valid_max':hi,
                         'source_label':meta.column_names_to_labels.get(var)})
        required=['national_economy_current','personal_priority_first','trust_parties','named_party_vote']
        joint.append({'study':study,'election_year':2008 if study==7708 else 2011,
                      'n':len(d),'joint_post_economy_priority_trust_named_vote':int(pd.concat([masks[v] for v in required],axis=1).all(axis=1).sum()),
                      'repeated_people_across_2008_2011_2015':False})
        var='s301' if study==7708 else 'p301'
        for code,label in meta.variable_value_labels[var].items():
            categories.append({'study':study,'variable':var,'code':int(code),'label':label,
                               'corruption_offered_separately':False})
        (OUT/f'cis_{study}_variable_inventory.json').write_text(json.dumps(meta.column_names_to_labels,ensure_ascii=False,indent=2)+'\n')
        (OUT/f'cis_{study}_value_labels.json').write_text(json.dumps(meta.variable_value_labels,ensure_ascii=False,indent=2)+'\n')
    pd.DataFrame(rows).to_csv(OUT/'cis_earlier_variable_coverage.csv',index=False)
    pd.DataFrame(joint).to_csv(OUT/'cis_earlier_joint_coverage.csv',index=False)
    pd.DataFrame(categories).to_csv(OUT/'cis_earlier_priority_codes.csv',index=False)
    print(pd.DataFrame(joint).to_string(index=False))
    print('Questionnaire check: 2008/2011 offered nine named issues plus other; 2015 explicitly adds corruption and territorial organisation. Missing option is not zero salience.')

if __name__=='__main__':main()
