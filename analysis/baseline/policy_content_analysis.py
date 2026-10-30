"""Counts by pre-existing CAP topic labels, not a measurement of policy outcomes."""
from pathlib import Path
import pandas as pd
P=Path(__file__).resolve().parent
cats={1:'economy',2:'civil_rights',7:'environment',8:'energy',9:'immigration',12:'crime',16:'defense',20:'government'}
# UK delegated national-level legislation. Local orders omitted at source.
x=pd.read_csv(P/'data/uk_instruments.csv',low_memory=False);x=x[x.year.between(2010,2022)&x.majortopic.notna()].copy();x['year']=x.year.astype(int)
def annual(d,yearcol='year'):
 a=d.groupby([yearcol,'majortopic']).size().unstack(fill_value=0);n=d.groupby(yearcol).size();out=pd.DataFrame({'n':n});
 for code,label in cats.items():out[label+'_n']=a.get(code,0);out[label+'_pct']=100*out[label+'_n']/out.n
 return out
annual(x).to_csv(P/'outputs/uk_instruments_annual.csv')
# US executive orders, matching the same fraction of the two years.
y=pd.read_csv(P/'data/us_orders.csv',encoding='latin1');y=y[y.year.isin([2021,2025])&y.signed_date.mod(10000).between(120,1015)].copy();annual(y).to_csv(P/'outputs/us_orders_2021_2025_jan20_oct15.csv')
# Human-coded UK party manifesto arguments, 2010 and 2015.
m=pd.read_csv(P/'data/uk_manifestos.csv',encoding='latin1');m=m[m.year.isin([2010,2015]) & (m.majortopic>0)].copy();rows=[]
for party,col in [('Conservative','filter_con'),('Labour','filter_lab'),('Liberal Democrats','filter_ld')]:
 g=m[m[col]==1]
 for yr,z in g.groupby('year'):
  n=len(z)
  for code,label in cats.items():rows.append({'party':party,'year':yr,'topic':label,'n':int((z.majortopic==code).sum()),'denominator':n,'pct':100*(z.majortopic==code).sum()/n})
pd.DataFrame(rows).to_csv(P/'outputs/uk_manifestos_2010_2015.csv',index=False)
# Audit: publication year in US public laws does not consistently equal signed
# year, and dates mix Excel serial and strings. Exclude from annual analysis.
u=pd.read_csv(P/'data/us_laws.csv',encoding='latin1');z=u[u.year==2017].copy();parsed=pd.to_datetime(z.date_signed,format='%m/%d/%y',errors='coerce');print('2017 source-year with 2018 signed-date among simple dates:',int((parsed.dt.year==2018).sum()))
print('US EO (Jan 20 to Oct 15):\n',annual(y).loc[:,['n','environment_n','energy_n','immigration_n','civil_rights_n']].to_string());print('UK SI 2019,2022:\n',annual(x).loc[[2019,2022],['n','environment_n','environment_pct','energy_pct','immigration_pct']].to_string())
