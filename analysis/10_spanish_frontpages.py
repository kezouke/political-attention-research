"""Spain CAP front-page records, 1996–2011: topic shares and date bootstrap.

Intervals describe variation under independent date resampling in the observed
outlet/year archive, not coding errors, audience exposure or cross-outlet validity.
"""
from pathlib import Path
import numpy as np
import pandas as pd
P=Path(__file__).resolve().parents[1]
SOURCES={'El País':'spain_elpais.csv','El Mundo':'spain_elmundo.csv'}
TOPICS={'macroeconomy':{1},'labour':{5},'economy_labour_commerce':{1,5,15},'civil_rights_broad':{2},'environment_broad':{7},'energy':{8},'migration':{9},'government':{20}}
R=2000
rows=[];difference=[]
rng=np.random.default_rng(20261030)
for outlet,filename in SOURCES.items():
 d=pd.read_csv(P/'data/raw'/filename)
 d=d[d.year.between(2000,2011)].copy()
 d['date']=pd.to_datetime(d[['year','month','day']],errors='coerce')
 if d.date.isna().any(): raise ValueError(f'{outlet}: invalid dates')
 for year,g in d.groupby('year'):
  daily=g.groupby('date').size().rename('total').to_frame()
  for name,codes in TOPICS.items():
   hit=g[g.majortopic.isin(codes)].groupby('date').size().rename('hit')
   t=daily.join(hit).fillna(0)
   counts=t[['hit','total']].to_numpy(); n=len(counts)
   draw=rng.integers(0,n,size=(R,n)); sums=counts[draw].sum(axis=1); pct=100*sums[:,0]/sums[:,1]
   lo,hi=np.quantile(pct,[.025,.975])
   monthly=t.groupby(t.index.month).sum()[['hit','total']].to_numpy()
   draw_month=rng.integers(0,len(monthly),size=(R,len(monthly))); monthly_totals=monthly[draw_month].sum(axis=1); monthly_pct=100*monthly_totals[:,0]/monthly_totals[:,1]
   mlo,mhi=np.quantile(monthly_pct,[.025,.975])
   rows.append({'outlet':outlet,'year':year,'topic':name,'hits':int(t.hit.sum()),'n':int(t.total.sum()),'days':n,'share_pct':100*t.hit.sum()/t.total.sum(),'lo_day_bootstrap_pct':lo,'hi_day_bootstrap_pct':hi,'lo_month_bootstrap_pct':mlo,'hi_month_bootstrap_pct':mhi})
  # Keep both terms in a single resample, preserving within-day correlation.
  a=g.assign(economy=g.majortopic.isin(TOPICS['economy_labour_commerce']).astype(int),rights=g.majortopic.isin(TOPICS['civil_rights_broad']).astype(int)).groupby('date').agg(economy=('economy','sum'),rights=('rights','sum'),total=('majortopic','size')).to_numpy()
  draw=rng.integers(0,len(a),size=(R,len(a))); z=a[draw].sum(axis=1); est=100*(a[:,0].sum()-a[:,1].sum())/a[:,2].sum(); dist=100*(z[:,0]-z[:,1])/z[:,2]
  difference.append({'outlet':outlet,'year':year,'comparison':'economy_labour_commerce_minus_civil_rights_broad','difference_pp':est,'lo_pp':np.quantile(dist,.025),'hi_pp':np.quantile(dist,.975),'n':int(a[:,2].sum()),'days':len(a)})
out=pd.DataFrame(rows);out.to_csv(P/'data/processed/spain_frontpage_2000_2011.csv',index=False)
pd.DataFrame(difference).to_csv(P/'data/processed/spain_frontpage_contrasts.csv',index=False)
print(out[(out.year.isin([2010,2011]))&out.topic.isin(['economy_labour_commerce','civil_rights_broad','environment_broad'])].round(2).to_string(index=False))
print(pd.DataFrame(difference).query('year>=2010').round(2).to_string(index=False))
