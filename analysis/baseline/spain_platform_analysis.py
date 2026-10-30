from pathlib import Path
import re
import pandas as pd
BASE=Path(__file__).resolve().parent
patterns={'clima':r'\b(?:cambio clim[aá]tico|crisis clim[aá]tica|calentamiento global|emisiones de (?:gases|carbono|co2))\b','medio_ambiente':r'\b(?:medio ambiente|medioambiental\w*|ambiental\w*|ecol[oó]gic\w*)\b','migracion':r'\b(?:inmigra\w*|migra\w*|refugiad\w*|asilo|deportaci[oó]n)\b','precios':r'\b(?:inflaci[oó]n|coste de vida|costo de vida|precio\w*)\b','corrupcion':r'\b(?:corrupci[oó]n|anticorrupci[oó]n|soborno\w*)\b','identidad':r'\b(?:lgtbi\w*|lgbt\w*|homosex\w*|lesbiana\w*|transg[eé]nero\w*|transex\w*|discriminaci[oó]n racial|racismo)\b'}
rows=[];matches=[]
for f in sorted((BASE/'data/spain_platforms').glob('*.txt')):
 text=f.read_text();text=re.sub(r'(?<=\w)-\s*\n\s*(?=\w)','',text);party,year=f.stem.split('_');n=len(re.findall(r'\b\w+\b',text)); row={'party':party,'year':int(year),'words':n}
 for k,pat in patterns.items():
  hits=list(re.finditer(pat,text,re.I));row[k+'_count']=len(hits);row[k+'_per_10k']=10000*len(hits)/n
  for m in hits:matches.append({'party':party,'year':year,'topic':k,'match':m.group(),'context':re.sub(r'\s+',' ',text[max(0,m.start()-70):m.end()+100])})
 rows.append(row)
pd.DataFrame(rows).to_csv(BASE/'outputs/spain_platform_counts.csv',index=False,float_format='%.4f');pd.DataFrame(matches).to_csv(BASE/'outputs/spain_platform_matches.csv',index=False)
print(pd.DataFrame(rows).to_string(index=False))
