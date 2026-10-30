"""SPES priorities against independent macro indicators, descriptive not causal.
World Bank ILO unemployment and CPI; Eurostat annual compensation / HICP for Spain.
Raw API snapshots preserve retrieval; existing annual survey data are not panel persons.
"""
from pathlib import Path
import json,requests
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
P=Path(__file__).resolve().parents[1];R=P/'data/raw';O=P/'data/processed'
west={'Austria':'AUT','Belgium':'BEL','Denmark':'DNK','Finland':'FIN','France':'FRA','Germany':'DEU','Ireland':'IRL','Italy':'ITA','Luxembourg':'LUX','Netherlands':'NLD','Portugal':'PRT','Spain':'ESP','Sweden':'SWE','United Kingdom':'GBR','Bulgaria':'BGR','Serbia':'SRB'}
session=requests.Session()
def cached(name,url,params):
 f=R/name
 if not f.exists():
  r=session.get(url,params=params,timeout=50);r.raise_for_status();f.write_bytes(r.content)
 return json.loads(f.read_text())
frames=[]
for indicator,name in [('FP.CPI.TOTL.ZG','inflation'),('SL.UEM.TOTL.ZS','unemployment')]:
 j=cached('wb_'+name+'_20261030.json',f'https://api.worldbank.org/v2/country/{";".join(west.values())}/indicator/{indicator}',{'format':'json','date':'2007:2024','per_page':'1000'})
 assert isinstance(j,list) and j[1],(name,str(j)[:300])
 frames.append(pd.DataFrame([{'iso':x['countryiso3code'],'year':int(x['date']),name:x['value']} for x in j[1]]))
macro=frames[0].merge(frames[1],on=['iso','year'],validate='one_to_one');macro['country_name']=macro.iso.map({v:k for k,v in west.items()})
survey=pd.read_csv(R/'spes_aggregate.csv');panel=survey[survey.country_name.isin(west)&survey.year.between(2010,2024)].merge(macro,on=['country_name','year'],how='left',validate='one_to_one')
panel[['country_name','iso','year','price','unemploy','inflation','unemployment']].to_csv(O/'macro_issue_panel.csv',index=False)
# Models were chosen as a transparent within-country descriptive comparison.
z=panel[panel.country_name.isin(list(west)[:14])].dropna(subset=['price','unemploy','inflation','unemployment']).copy();out=[]
for outcome,predictor in [('price','inflation'),('unemploy','unemployment')]:
 for tag,formula in [('country_fe',f'{outcome} ~ {predictor} + C(country_name)'),('country_year_fe',f'{outcome} ~ {predictor} + C(country_name) + C(year)')]:
  m=smf.ols(formula,data=z).fit(cov_type='cluster',cov_kwds={'groups':z.country_name},use_t=True);ci=m.conf_int().loc[predictor]
  out.append({'outcome':outcome,'predictor':predictor,'specification':tag,'n':int(m.nobs),'countries':z.country_name.nunique(),'beta_pp_per_point':m.params[predictor],'lo':ci[0],'hi':ci[1],'p':m.pvalues[predictor]})
pd.DataFrame(out).to_csv(O/'macro_issue_models.csv',index=False)
# Exploratory stability across country omissions and time windows.
checks=[]
for outcome,predictor in [('price','inflation'),('unemploy','unemployment')]:
 for label,q in [('all',z),('pre_pandemic',z[z.year.between(2012,2019)]),('without_2020_2021',z[~z.year.isin([2020,2021])]),('without_2022_2023',z[~z.year.isin([2022,2023])])]+[(f'excluding_{c}',z[z.country_name.ne(c)]) for c in sorted(z.country_name.unique())]:
  m=smf.ols(f'{outcome} ~ {predictor} + C(country_name) + C(year)',data=q).fit(cov_type='cluster',cov_kwds={'groups':q.country_name},use_t=True)
  ci=m.conf_int().loc[predictor];checks.append({'outcome':outcome,'predictor':predictor,'sample':label,'n':int(m.nobs),'n_countries':q.country_name.nunique(),'beta':m.params[predictor],'lo':ci[0],'hi':ci[1],'p':m.pvalues[predictor]})
pd.DataFrame(checks).to_csv(O/'macro_issue_robustness.csv',index=False)

# Eurostat JSON-stat order is fixed by dimensions; selected dimensions are singletons.
def eurostat(name,dataset,params):
 j=cached(name,'https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/'+dataset,{'freq':'A','geo':'ES','sinceTimePeriod':'2007','untilTimePeriod':'2024','lang':'en',**params})
 dims=j['id']; sizes=j['size']; vals=j['value']; maps=[]
 for dim in dims:
  cat=j['dimension'][dim]['category']['index']; maps.append({v:k for k,v in cat.items()} if isinstance(cat,dict) else dict(enumerate(cat)))
 records=[]
 for flat,value in vals.items():
  i=int(flat);idx=[]
  for size in reversed(sizes):idx.append(i%size);i//=size
  idx=list(reversed(idx)); row={dim:maps[n][v] for n,(dim,v) in enumerate(zip(dims,idx))};row['value']=value;records.append(row)
 return pd.DataFrame(records)
c=eurostat('eurostat_comp_es_20261030.json','nama_10_lp_ulc',{'unit':'EUR','na_item':'D1_SAL_PER'}).rename(columns={'value':'compensation_eur'})
h=eurostat('eurostat_hicp_es_inx_20261030.json','prc_hicp_aind',{'unit':'INX_A_AVG','coicop':'CP00'}).rename(columns={'value':'hicp_index'})
c['year']=c.time.astype(int);h['year']=h.time.astype(int)
r=c[['year','compensation_eur']].merge(h[['year','hicp_index']],on='year',validate='one_to_one');r['real_compensation_index_2019']=100*(r.compensation_eur/r.hicp_index)/(r.loc[r.year==2019,'compensation_eur'].iloc[0]/r.loc[r.year==2019,'hicp_index'].iloc[0]);r=r.merge(macro[macro.iso.eq('ESP')][['year','inflation','unemployment']],on='year',how='left',validate='one_to_one').sort_values('year');r.to_csv(O/'spain_macro_conditions.csv',index=False)
print('Models\n',pd.DataFrame(out).round(3).to_string(index=False));print('\nSpain\n',r[r.year.isin([2007,2010,2013,2019,2021,2022,2023,2024])].round(2).to_string(index=False))
