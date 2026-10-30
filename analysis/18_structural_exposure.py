"""Country structural exposure indicators from World Bank WDI, not causal estimates."""
from pathlib import Path
import requests,json,hashlib
import pandas as pd
P=Path(__file__).resolve().parents[1]; raw=P/'data/raw';out=P/'data/processed';countries='BRA;BGR;ISR;SRB;ESP;THA;FRA'
series={'energy_import_pct_use':'EG.IMP.CONS.ZS','natural_resource_rents_pct_gdp':'NY.GDP.TOTL.RT.ZS','trade_pct_gdp':'NE.TRD.GNFS.ZS','industry_manufacturing_pct_gdp':'NV.IND.MANF.ZS','services_employment_pct':'SL.SRV.EMPL.ZS','tourism_receipts_usd':'ST.INT.RCPT.CD','gdp_usd':'NY.GDP.MKTP.CD','central_government_revenue_pct_gdp':'GC.REV.XGRT.GD.ZS'}
frames=[];prov=[]
for name,code in series.items():
 f=raw/f'wdi_structure_{code}_20261030.json'
 if not f.exists():
  r=requests.get(f'https://api.worldbank.org/v2/country/{countries}/indicator/{code}',params={'format':'json','date':'2010:2024','per_page':1000},timeout=40);r.raise_for_status();f.write_bytes(r.content)
 j=json.loads(f.read_text());assert isinstance(j,list) and j[1],(code,j)
 frames.append(pd.DataFrame([{'country':x['country']['value'],'iso':x['countryiso3code'],'year':int(x['date']),name:x['value']} for x in j[1]]))
 prov.append({'indicator':code,'source':'https://data.worldbank.org/indicator/'+code,'snapshot_sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
d=frames[0]
for f in frames[1:]:d=d.merge(f,on=['country','iso','year'],validate='one_to_one')
# Gross inbound travel receipts / GDP is a scale indicator, not value-added or tourism GDP share.
d['travel_receipts_pct_gdp']=100*d.tourism_receipts_usd/d.gdp_usd
d.sort_values(['iso','year']).to_csv(out/'structural_exposure_wdi.csv',index=False);pd.DataFrame(prov).to_csv(out/'structural_wdi_provenance.csv',index=False)
print(d[d.year.isin([2019,2022,2024])].sort_values(['year','iso']).round(2).to_string(index=False))
