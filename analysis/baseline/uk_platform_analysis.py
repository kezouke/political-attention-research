"""Transparent dictionary counts of four UK platforms; not topic positions."""
from pathlib import Path
import re
import pandas as pd
import fitz
P=Path(__file__).resolve().parent
patterns={'climate':r'\b(?:climate change|global warming|net.zero)\b','immigration':r'\b(?:immigra\w*|migran\w*|asylum|refugee\w*|deport\w*)\b','cost':r'\b(?:inflation|cost.of.living|rising prices)\b','identity':r'\b(?:lgbt\w*|gay|lesbian\w*|transgender|racism|racial discrimination)\b'}
rows=[];ex=[]
for path in sorted((P/'data/uk_platforms').glob('*.pdf')):
 text='\n'.join(page.get_text() for page in fitz.open(path));(path.with_suffix('.txt')).write_text(text)
 party,year=path.stem.split('_');n=len(re.findall(r"\b[\w]+(?:['’][\w]+)?\b",text));row={'party':party,'year':int(year),'words':n}
 for topic,pattern in patterns.items():
  hits=list(re.finditer(pattern,text,re.I));row[topic+'_count']=len(hits);row[topic+'_per_10k']=10000*len(hits)/n
  for m in hits:ex.append({'party':party,'year':year,'topic':topic,'match':m.group(),'context':re.sub(r'\s+',' ',text[max(0,m.start()-80):m.end()+110])})
 rows.append(row)
pd.DataFrame(rows).to_csv(P/'outputs/uk_platform_dictionary.csv',index=False);pd.DataFrame(ex).to_csv(P/'outputs/uk_platform_matches.csv',index=False);print(pd.DataFrame(rows).round(2).to_string(index=False))
