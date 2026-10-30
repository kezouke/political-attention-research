"""Brazil MIP across ten Latinobarometro waves; SPES national series for BG/ES/RS.

The Brazilian item asks one spontaneous national problem. Categories are harmonised
conservatively; don't-know/non-response stay in primary denominator. Intervals use
Kish-effective-n Wilson approximation and ignore sample clustering/stratification.
"""
from pathlib import Path
from io import BytesIO
import zipfile, hashlib
import numpy as np
import pandas as pd
from scipy.stats import norm
P=Path(__file__).resolve().parents[1]
YEARS=[2010,2011,2013,2015,2016,2017,2018,2020,2023,2024]
VARS={2010:'P2ST',2011:'P2ST',2013:'P9STGBS',2015:'P9STGBS',2016:'P3STGBS',2017:'P3STGBS',2018:'P3STGBSC',2020:'p3stgbs',2023:'P4STGBS',2024:'P5STGBS'}
# Read each wave's published value labels. Code 4 in 2010/11 conflates unstable
# employment and immigration; it is omitted in the strict estimate and added
# as an explicitly non-comparable upper sensitivity range.
def crosswalk(year):
 if year<=2011:
  return {'economy_strict':{1,6,7,25},'economy_broad':{1,6,7,16,23 if year==2010 else 24,25},'economy_ambiguous':{4},'environment_strict':{12,27},'environment_expanded':{12,27},'race_discrimination':{18},'corruption':{13},'unemployment':{7},'health':{11}}
 if year<=2017:
  return {'economy_strict':{1,4,6,7,25},'economy_broad':{1,4,6,7,16,24,25},'economy_ambiguous':set(),'environment_strict':{12,27},'environment_expanded':{12,27},'race_discrimination':{18},'corruption':{13},'unemployment':{7},'health':{11}}
 if year<=2020:
  return {'economy_strict':{1,2,5,6,9,42},'economy_broad':{1,2,3,4,5,6,9,42},'economy_ambiguous':set(),'environment_strict':{14,15},'environment_expanded':{14,15,16},'race_discrimination':{31},'corruption':{34},'unemployment':{5},'health':{13}}
 return {'economy_strict':{1,2,5,8,9,10},'economy_broad':{1,2,3,4,5,8,9,10},'economy_ambiguous':set(),'environment_strict':{17,18},'environment_expanded':{17,18,19},'race_discrimination':{32},'corruption':{35},'unemployment':{9},'health':{16}}
def wilson(p,n):
 z=norm.ppf(.975);den=1+z*z/n;center=(p+z*z/(2*n))/den;half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
 return 100*max(0,center-half),100*min(1,center+half)
rows=[];codebook=[];provenance=[]
for year in YEARS:
 path=P/'data/raw'/f'lat_{year}.zip'
 with zipfile.ZipFile(path) as z:
  files=[x for x in z.namelist() if x.lower().endswith('.dta')]
  f=next((x for x in files if 'eng' in x.lower()),files[0]);reader=pd.io.stata.StataReader(BytesIO(z.read(f)),convert_categoricals=False)
  val=reader.value_labels(); labels=val.get(VARS[year],val.get(VARS[year].upper(),{})); d=reader.read()
  country=next(c for c in d if c.lower()=='idenpa');weight=next(c for c in d if c.lower()=='wt');months=next(c for c in d if c.lower()=='mesreal')
  g=d[d[country]==76].copy(); assert len(g)>900
  g=g[g[weight].gt(0)].copy(); g['valid']=g[VARS[year]].between(1,97); neff=g[weight].sum()**2/(g[weight]**2).sum()
  for issue,codes in crosswalk(year).items():
   pred=g[VARS[year]].isin(codes);pct=np.average(pred,weights=g[weight]);valid=g[g.valid]
   lo,hi=wilson(pct,neff)
   rows.append({'country':'Brazil','wave':year,'fieldwork_months':','.join(str(int(v)) for v in sorted(g[months].dropna().unique())),'question':VARS[year],'issue':issue,'n':len(g),'valid_n':len(valid),'positive_n':int(pred.sum()),'n_eff':neff,'pct_all':100*pct,'pct_valid':100*np.average(valid[VARS[year]].isin(codes),weights=valid[weight]),'ci_low_iid_approx':lo,'ci_high_iid_approx':hi})
   for code in sorted(codes):
    if code not in labels: raise ValueError(f'Missing source label {year} {code}')
    codebook.append({'wave':year,'issue':issue,'code':code,'source_label':labels[code]})
  provenance.append({'wave':year,'zip_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'member':f})
out=pd.DataFrame(rows);out.to_csv(P/'data/processed/brazil_mip_longitudinal.csv',index=False)
pd.DataFrame(codebook).to_csv(P/'data/processed/brazil_mip_code_crosswalk.csv',index=False)
pd.DataFrame(provenance).to_csv(P/'data/processed/brazil_mip_provenance.csv',index=False)
# Add only two-topic response options in the SPES standardised export. They
# cannot be added and they cannot be pooled with Brazil's one-answer item.
x=pd.read_csv(P/'data/raw/spes_aggregate.csv');x=x[x.country.isin(['BG','ES','RS'])&x.year.between(2010,2024)]
x=x[['country','country_name','year','eco','price','unemploy','immi','env_merged']].sort_values(['country','year']);x.to_csv(P/'data/processed/six_country_euro_priorities.csv',index=False)
print(out[out.issue.isin(['economy_strict','economy_broad','environment_strict','environment_expanded','race_discrimination','corruption','unemployment','health'])][['wave','issue','n','positive_n','pct_all','pct_valid','ci_low_iid_approx','ci_high_iid_approx']].round(2).to_string(index=False))
print(x[x.year.isin([2010,2012,2019,2022,2024])].round(2).to_string(index=False))
# Independent-wave normal intervals are a sensitivity calculation only, not
# survey-design inference. All weights in the Brazil samples happen to equal 1.
diffs=[]
for issue in ['economy_strict','economy_broad','environment_strict','race_discrimination','corruption','unemployment','health']:
 a=out[(out.wave==2010)&(out.issue==issue)].iloc[0];b=out[(out.wave==2024)&(out.issue==issue)].iloc[0]
 se=100*np.sqrt(a.pct_all/100*(1-a.pct_all/100)/a.n_eff+b.pct_all/100*(1-b.pct_all/100)/b.n_eff)
 diffs.append({'issue':issue,'first_wave':2010,'last_wave':2024,'difference_pp':b.pct_all-a.pct_all,'ci_low_iid_approx_pp':b.pct_all-a.pct_all-1.96*se,'ci_high_iid_approx_pp':b.pct_all-a.pct_all+1.96*se,'difference_valid_pp':b.pct_valid-a.pct_valid})
pd.DataFrame(diffs).to_csv(P/'data/processed/brazil_mip_endpoint_differences.csv',index=False)
