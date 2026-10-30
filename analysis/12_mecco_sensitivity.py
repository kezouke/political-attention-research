"""Endpoints and fixed-basket leave-one-out checks for MeCCO article counts.
These counts do not provide an all-articles denominator and are not audience shares.
"""
from pathlib import Path
import pandas as pd
P=Path(__file__).resolve().parents[1]
d=pd.read_csv(P/'data/processed/mecco_source_annual.csv')
rows=[]
for region,g in d.groupby('region'):
 sources=sorted(g.source.unique())
 for exclude in [None]+(sources if len(sources)>1 else []):
  basket=g if exclude is None else g[g.source!=exclude]
  for start,end in [(2010,2025),(2019,2025),(2021,2025)]:
   early=basket[basket.year==start];late=basket[basket.year==end]
   assert set(early.source)==set(late.source)==set(basket.source.unique())
   a=int(early.articles.sum()); b=int(late.articles.sum());assert a>0
   rows.append({'region':region,'excluded_source':exclude or 'none','n_sources':early.source.nunique(),'start':start,'end':end,'start_count':a,'end_count':b,'change_pct':100*(b/a-1)})
pd.DataFrame(rows).to_csv(P/'data/processed/mecco_endpoint_sensitivity.csv',index=False)
print(pd.DataFrame(rows).query("excluded_source=='none'").round(1).to_string(index=False))
