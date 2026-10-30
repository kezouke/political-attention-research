"""Exploratory dictionary coding of Spain's 2023 PP/PSOE election documents.

The unit is a machine-split text span, not a manifesto quasi-sentence. Multi-label
matches overlap. This is a reproducible pilot, not a measurement of all parties.
"""
from pathlib import Path
import re, hashlib
import fitz
import numpy as np
import pandas as pd
P=Path(__file__).resolve().parents[1]
PATTERNS={
'economy':r'\b(?:econom[ií]\w*|emple\w*|desemple\w*|paro|salari\w*|sueld\w*|impuest\w*|inflaci[oó]n|coste de (?:la )?vida|precios?|pensiones?|tribut\w*|renta\w*|fiscal\w*)\b',
'institutions':r'\b(?:corrupci[oó]n|anticorrupci[oó]n|transparencia|institucion\w*|democraci\w*|administraci[oó]n p[uú]blica|gobernanza)\b',
'climate_environment':r'\b(?:cambio clim[aá]tico|crisis clim[aá]tica|calentamiento global|medio ambiente|medioambient\w*|energ[ií]as? renovables?|emisiones|ecol[oó]gic\w*)\b',
'identity':r'\b(?:lgtbi\w*|lgbt\w*|homosex\w*|lesbian\w*|transg[eé]nero\w*|transex\w*|identidad de g[eé]nero|discriminaci[oó]n racial|racismo)\b',
'migration':r'\b(?:inmigra\w*|migra\w*|refugiad\w*|asilo|deportaci[oó]n)\b'}
rows=[]
for party,start in [('psoe',10),('pp',8)]:
    with fitz.open(P/'data/raw'/f'spain_{party}_2023.pdf') as doc:
        pages=[page.get_text() for page in list(doc)[start:]]
    text='\n'.join(pages)
    text=re.sub(r'(?<=\w)-\s*\n\s*(?=\w)','',text)
    text=re.sub(r'\s+',' ',text)
    spans=[x.strip() for x in re.split(r'(?<=[.!?])\s+',text) if len(re.findall(r'\w+',x))>=8]
    for i,span in enumerate(spans):
        row={'party':party,'span_id':i,'text':span,'hash':hashlib.sha256(span.encode()).hexdigest()[:16]}
        row.update({k:int(bool(re.search(p,span,re.I))) for k,p in PATTERNS.items()})
        row['economic_institutional']=int(row['economy'] or row['institutions'])
        rows.append(row)
d=pd.DataFrame(rows)
cols=['economy','institutions','climate_environment','identity','migration','economic_institutional']
out=d.groupby('party')[cols].agg(['sum','mean']);out.columns=['_'.join(c) for c in out.columns];out['n']=d.groupby('party').size();out.reset_index().to_csv(P/'data/processed/spain_text_pilot.csv',index=False)
# A fixed stratified sample supports transparent, qualitative checks; raw spans are excluded from Git.
sample=pd.concat([g.sample(min(12,len(g)),random_state=42) for _,g in d.groupby(['party','economic_institutional'])]).sort_values(['party','economic_institutional','span_id'])
sample.to_csv(P/'data/raw/spain_text_audit_private.csv',index=False)
print(out.to_string()); print('Audit rows',len(sample))
