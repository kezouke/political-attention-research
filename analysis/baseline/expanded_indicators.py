"""Descriptive indicators from public World Bank WBL 1.0, Ember and CAP data.
Legal scores describe rules in selected areas, not implementation; electricity
mix is an observed outcome, not itself a measure of legal policy.
"""
from pathlib import Path
import pandas as pd
P=Path(__file__).resolve().parent
codes=['BRA','BGR','SRB','ISR','ESP','THA','RUS','USA','GBR','DEU']
w=pd.read_stata(P/'data/wbl_1971_2024.dta',columns=['economy','ISOcode','year','reportyr','WBL_index'],convert_categoricals=False);w=w[w.ISOcode.isin(codes)&w.year.between(2010,2023)].copy();w['year']=w.year.astype(int);w.to_csv(P/'outputs/wbl_legal_2010_2023.csv',index=False)
e=pd.read_csv(P/'data/ember_yearly.csv',usecols=['Area','ISO 3 code','Year','Category','Variable','Unit','Value']);e=e[e['ISO 3 code'].isin(codes)&e.Year.between(2010,2025)&(e.Category=='Electricity generation')&(e.Variable=='Renewables')&(e.Unit=='%')].copy();e=e[['Area','ISO 3 code','Year','Value']];e.to_csv(P/'outputs/ember_renewables_2010_2025.csv',index=False)
r=[]
for file,source in [('brazil_laws','laws'),('brazil_decrees','decrees'),('spain_elpais','El País'),('spain_elmundo','El Mundo')]:
 d=pd.read_csv(P/f'data/cap_expanded/{file}.csv',low_memory=False);d=d[d.year.between(2010,2014)&d.majortopic.notna()]
 for year,g in d.groupby('year'):
  row=dict(source=source,year=int(year),n=len(g));row.update({name:100*(g.majortopic==code).mean() for name,code in [('economy',1),('rights',2),('environment',7),('energy',8),('immigration',9),('crime',12),('government',20)]});r.append(row)
pd.DataFrame(r).to_csv(P/'outputs/cap_brazil_spain.csv',index=False)
print('WBL 2010 and 2023');print(w[w.year.isin([2010,2023])].sort_values(['economy','year']).to_string(index=False));print('Ember 2010 and 2025');print(e[e.Year.isin([2010,2025])].sort_values(['Area','Year']).to_string(index=False));print('CAP 2010 onward');print(pd.DataFrame(r).round(2).to_string(index=False))
