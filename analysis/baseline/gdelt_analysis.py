"""Annual within-domain keyword rates and coverage diagnostics for GDELT DOC."""
from pathlib import Path
import json
import pandas as pd
base=Path(__file__).resolve().parent
series={}
for f in (base/'data/gdelt').glob('bbc_*.json'):
 d=json.loads(f.read_text());a=pd.DataFrame(d['timeline'][0]['data']);a['year']=a.date.str[:4].astype(int)
 series[f.stem]=a.groupby('year').value.agg(['sum','count'])
all_counts=series['bbc_all'];out=pd.DataFrame({'year':all_counts.index,'indexed_articles':all_counts['sum'].values,'days_in_response':all_counts['count'].values}).set_index('year')
for name,values in series.items():
 if name=='bbc_all':continue
 out[name+'_matches']=values['sum'];out[name+'_per_1000']=1000*values['sum']/out.index.map(all_counts['sum']).to_numpy()
out.to_csv(base/'outputs/gdelt_bbc_annual.csv');print(out.to_string())
