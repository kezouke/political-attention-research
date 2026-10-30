"""Match the exact days and domain for two GDELT DOC timelinevolraw queries."""
from pathlib import Path
import pandas as pd,json
P=Path(__file__).resolve().parent;folder=P/'data/gdelt';rows=[]
for domain in ['bbc','guardian','nyt']:
 full=folder/(domain+'_all.json')
 if not full.exists():continue
 a=pd.DataFrame(json.loads(full.read_text())['timeline'][0]['data'])[['date','value']].rename(columns={'value':'total'})
 for issue in ['climate','inflation','immigration']:
  path=folder/(domain+'_'+issue+'.json')
  if not path.exists():continue
  b=pd.DataFrame(json.loads(path.read_text())['timeline'][0]['data'])[['date','value']].rename(columns={'value':'matches'})
  z=a.merge(b,on='date',how='inner',validate='one_to_one');z['date']=pd.to_datetime(z.date,format='%Y%m%dT%H%M%SZ');z=z[(z.date.dt.month*100+z.date.dt.day).between(101,1015)]
  for year,g in z.groupby(z.date.dt.year):
   if year>2025:continue
   total=g.total.sum();hits=g.matches.sum();rows.append({'outlet':domain,'topic':issue,'year':year,'days':len(g),'total':int(total),'matches':int(hits),'per_1000':1000*hits/total if total else None})
pd.DataFrame(rows).to_csv(P/'outputs/gdelt_matched_jan_oct.csv',index=False);print(pd.DataFrame(rows).query("year >= 2021").round(2).to_string(index=False))
