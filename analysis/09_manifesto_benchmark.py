"""Out-of-corpus benchmark for the Spanish dictionaries already used in 2023.

Reference is the independently coded Spanish Comparative Agendas Project corpus,
not a new human annotation by this research team. Each document uses CAP-coded
quasi-sentences (not the 2023 pilot's punctuation-delimited spans). Code alignment
is imperfect; mismatches include taxonomy differences and cannot be attributed
solely to classifier error. The benchmark predates and does not validate 2023.
"""
from pathlib import Path
import ast
import hashlib
import re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CAP_PATH = ROOT/'data/raw/cap_spain_manifestos.csv'
# Read the exact, frozen dictionary without executing the original pipeline.
tree = ast.parse((ROOT/'analysis/06_spain_text_pilot.py').read_text())
for statement in tree.body:
    if isinstance(statement, ast.Assign) and any(isinstance(n, ast.Name) and n.id == 'PATTERNS' for n in statement.targets):
        patterns = ast.literal_eval(statement.value)
        break
else:
    raise ValueError('PATTERNS not found')

# CAP broad primary-topic codes. These are comparison targets, not perfect labels
# for the narrower lexical definitions. Identity lexicon does not represent all
# civil rights; renewable energy lexicon does not represent all energy.
references = {
    'economy_institutions': {1,5,13,15,20},
    'climate_environment': {7},
    'identity': {2},
    'migration': {9},
}
raw = pd.read_csv(CAP_PATH)
raw = raw[raw.majortopic.notna() & raw.year.notna() & raw['sentence text'].notna()].copy()
raw['year']=raw.year.astype(int)
raw['majortopic']=raw.majortopic.astype(int)
raw = raw[((raw.politicalparty=='PP') & (raw.year==2000)) | ((raw.politicalparty=='PSOE') & (raw.year==2008))].copy()

def metrics(g, y, pred):
    tp=int(((y==1)&(pred==1)).sum()); fn=int(((y==1)&(pred==0)).sum())
    fp=int(((y==0)&(pred==1)).sum()); tn=int(((y==0)&(pred==0)).sum())
    return {'n':len(g),'tp':tp,'fp':fp,'fn':fn,'tn':tn,
            'reference_pct':100*(tp+fn)/len(g), 'predicted_pct':100*(tp+fp)/len(g),
            'precision_pct':100*tp/(tp+fp) if tp+fp else np.nan,
            'recall_pct':100*tp/(tp+fn) if tp+fn else np.nan}

rows=[]; examples=[]; topic_counts=[]
for (party,year),doc in raw.groupby(['politicalparty','year']):
    doc=doc.sort_values('id').reset_index(drop=True)
    for name,codes in references.items():
        target=doc.majortopic.isin(codes).astype(int)
        if name=='economy_institutions':
            pred=(doc['sentence text'].str.contains(patterns['economy'],flags=re.I,regex=True,na=False) | doc['sentence text'].str.contains(patterns['institutions'],flags=re.I,regex=True,na=False)).astype(int)
        else:
            pred=doc['sentence text'].str.contains(patterns[name],flags=re.I,regex=True,na=False).astype(int)
        row={'party':party,'year':year,'topic':name,**metrics(doc,target,pred)}
        # Resample contiguous 30-quasi-sentence blocks. The interval indicates
        # sensitivity to within-document text composition, not sampling from
        # voters, other manifestos or a future 2023 corpus.
        rng=np.random.default_rng(42000+year+len(name))
        blocks=np.array_split(np.arange(len(doc)), max(1,int(np.ceil(len(doc)/30))))
        draws=[]
        for _ in range(1500):
            ix=np.concatenate([blocks[j] for j in rng.integers(0,len(blocks),len(blocks))])
            y=target.to_numpy()[ix];p=pred.to_numpy()[ix]
            if p.sum() and y.sum():
                tp=((y==1)&(p==1)).sum()
                draws.append((100*tp/p.sum(),100*tp/y.sum()))
        q=np.percentile(np.asarray(draws),[2.5,97.5],axis=0)
        row.update({'precision_block_lo':q[0,0],'precision_block_hi':q[1,0],
                    'recall_block_lo':q[0,1],'recall_block_hi':q[1,1]})
        rows.append(row)
        for kind,mask in [('false_positive',(target==0)&(pred==1)),('false_negative',(target==1)&(pred==0))]:
            errors=doc.loc[mask].copy()
            if len(errors):
                # Stable, reproducible sample of disagreements, no copyrighted text.
                for _,r in errors.sample(min(8,len(errors)),random_state=42).iterrows():
                    examples.append({'party':party,'year':year,'topic':name,'error_type':kind,
                        'cap_id':int(r.id),'cap_topic':int(r.majortopic),
                        'cap_subtopic':int(r.subtopic),'text_sha256':hashlib.sha256(str(r['sentence text']).encode()).hexdigest()})
        for code,count in doc.loc[(target==1)&(pred==0),'majortopic'].value_counts().sort_index().items():
            topic_counts.append({'party':party,'year':year,'topic':name,'missed_reference_code':int(code),'n':int(count)})
output=ROOT/'data/processed'
pd.DataFrame(rows).to_csv(output/'spain_cap_dictionary_benchmark.csv',index=False)
pd.DataFrame(examples).to_csv(output/'spain_cap_disagreement_ids.csv',index=False)
pd.DataFrame(topic_counts).to_csv(output/'spain_cap_missed_topics.csv',index=False)
print(pd.DataFrame(rows).round(1).to_string(index=False))
