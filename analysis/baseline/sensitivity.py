from pathlib import Path
import json
import pandas as pd
from scipy.stats import binomtest
import statsmodels.formula.api as smf
BASE=Path(__file__).resolve().parent
x=pd.read_csv(BASE/'data/spes_aggregate.csv');EU=['Austria','Belgium','Bulgaria','Croatia','Cyprus','Czechia','Denmark','Estonia','Finland','France','Germany','Greece','Hungary','Ireland','Italy','Latvia','Lithuania','Luxembourg','Malta','Netherlands','Poland','Portugal','Romania','Slovakia','Slovenia','Spain','Sweden'];WEST={'Austria':'AUT','Belgium':'BEL','Denmark':'DNK','Finland':'FIN','France':'FRA','Germany':'DEU','Ireland':'IRL','Italy':'ITA','Luxembourg':'LUX','Netherlands':'NLD','Portugal':'PRT','Spain':'ESP','Sweden':'SWE','United Kingdom':'GBR'}
rows=[]
for k in ['price','unemploy','immi','env_merged','crime','eco','health']:
 z=x[x.country_name.isin(EU)].pivot(index='country_name',columns='year',values=k);d=(z[2024]-z[2019]).dropna();pos=int((d>0).sum());neg=int((d<0).sum()); rows.append({'indicator':k,'n':len(d),'mean_change':d.mean(),'median_change':d.median(),'positive':pos,'negative':neg,'sign_p':binomtest(pos,pos+neg).pvalue})
pd.DataFrame(rows).to_csv(BASE/'outputs/eu27_paired_change.csv',index=False)
w=pd.DataFrame([{'iso':r['countryiso3code'],'year':int(r['date']),'inflation':r['value']} for r in json.loads((BASE/'data/worldbank_inflation.json').read_text())[1]]);x=x[x.country_name.isin(WEST)&x.year.between(2010,2024)].copy();x['iso']=x.country_name.map(WEST);p=x.merge(w,on=['iso','year']).dropna(subset=['inflation','price']);out=[]
for name,q in [('all',p),('without_2022_2023',p[~p.year.isin([2022,2023])]),('2012_to_2019',p[p.year.between(2012,2019)]),('2020_to_2024',p[p.year.between(2020,2024)])]:
 m=smf.ols('price ~ inflation + C(country_name) + C(year)',q).fit(cov_type='cluster',cov_kwds={'groups':q.country_name},use_t=True);out.append({'sample':name,'N':int(m.nobs),'beta':m.params['inflation'],'lower':m.conf_int().loc['inflation',0],'upper':m.conf_int().loc['inflation',1],'p':m.pvalues['inflation']})
pd.DataFrame(out).to_csv(BASE/'outputs/inflation_robustness.csv',index=False)
print('EU27:',pd.DataFrame(rows).round(4).to_string(index=False));print('\n',pd.DataFrame(out).round(4).to_string(index=False))
