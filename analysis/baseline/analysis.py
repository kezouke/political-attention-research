from pathlib import Path
import json, re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import binomtest
import statsmodels.formula.api as smf

BASE=Path(__file__).resolve().parent
DATA=BASE/'data'
OUT=BASE/'outputs';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
WEST={'Austria':'AUT','Belgium':'BEL','Denmark':'DNK','Finland':'FIN','France':'FRA','Germany':'DEU','Ireland':'IRL','Italy':'ITA','Luxembourg':'LUX','Netherlands':'NLD','Portugal':'PRT','Spain':'ESP','Sweden':'SWE','United Kingdom':'GBR'}
LABEL={'price':'Цены и стоимость жизни','eco':'Экономика','unemploy':'Безработица','immi':'Иммиграция','env_merged':'Среда, климат и энергия','crime':'Преступность','health':'Здравоохранение'}
COLORS={'price':'#C34B38','eco':'#B57B30','unemploy':'#885F2B','immi':'#5C65A8','env_merged':'#21856A','crime':'#9A557A','health':'#217A9B'}
x=pd.read_csv(DATA/'spes_aggregate.csv'); x=x[x.country_name.isin(WEST) & x.year.between(2010,2024)].copy()
assert not x.duplicated(['country_name','year']).any()
counts=x.groupby('year').country_name.nunique();assert (counts==14).all(),counts
series=x.groupby('year')[list(LABEL)].mean().reindex(range(2010,2025));series.to_csv(OUT/'western_country_means.csv',float_format='%.5f')
fig,ax=plt.subplots(figsize=(10,6));
for k in ['price','unemploy','immi','env_merged','crime']:
 ax.plot(series.index,series[k],marker='o',markersize=3,label=LABEL[k],color=COLORS[k])
ax.set(title='Проблемы своей страны: 14 стран Западной Европы',ylabel='Среднее страновых долей, %',xlabel='Год',ylim=(0,60),xticks=range(2010,2025,2));ax.grid(axis='y',alpha=.22);ax.legend(frameon=False,ncol=2,loc='upper right',fontsize=9)
fig.text(.1,.01,'SPES / Eurobarometer; страны имеют равный вес. За 2011 год данных нет. Среда включает энергоснабжение.',fontsize=8)
fig.tight_layout(rect=[0,.06,1,1]);fig.savefig(OUT/'western_trends.png',dpi=180);plt.close(fig)
# Within-country pair comparisons. Binomial sign test tests symmetry across countries, not sampling error of respondents.
summary=[]
for t0,t1 in [(2010,2019),(2019,2024),(2021,2023),(2022,2024)]:
 for k in LABEL:
  piv=x.pivot(index='country_name',columns='year',values=k);delta=(piv[t1]-piv[t0]).dropna();pos=int((delta>0).sum());neg=int((delta<0).sum());n=pos+neg
  summary.append(dict(from_year=t0,to_year=t1,issue=k,n_countries=len(delta),mean_change=delta.mean(),median_change=delta.median(),positive=pos,negative=neg,sign_p=binomtest(pos,n,p=.5).pvalue if n else None))
pd.DataFrame(summary).to_csv(OUT/'paired_changes.csv',index=False,float_format='%.6f')
pivot=x[x.year.isin([2019,2024])].pivot(index='country_name',columns='year',values=['price','immi','env_merged','unemploy','crime'])
delta=pd.DataFrame({k:pivot[k][2024]-pivot[k][2019] for k in ['price','immi','env_merged','unemploy','crime']});delta.to_csv(OUT/'country_changes_2019_2024.csv',float_format='%.5f')
# Inflation panel: country/year fixed effects, cluster standard errors by country.
raw=json.loads((DATA/'worldbank_inflation.json').read_text())[1]
w=pd.DataFrame([{'iso':r['countryiso3code'],'year':int(r['date']),'inflation':r['value']} for r in raw])
x['iso']=x.country_name.map(WEST);p=x.merge(w,on=['iso','year']).dropna(subset=['inflation','price']);
models=[]
for spec in ['price ~ inflation + C(country_name)','price ~ inflation + C(country_name) + C(year)']:
 m=smf.ols(spec,data=p).fit(cov_type='cluster',cov_kwds={'groups':p['country_name'],'use_correction':True},use_t=True)
 models.append({'specification':spec,'n':int(m.nobs),'countries':p.country_name.nunique(),'beta':float(m.params['inflation']),'se_cluster':float(m.bse['inflation']),'p_t_df_clusters_minus_1':float(m.pvalues['inflation']),'ci_low':float(m.conf_int().loc['inflation',0]),'ci_high':float(m.conf_int().loc['inflation',1]),'r2':float(m.rsquared)})
loo=[]
for c in WEST:
 z=p[p.country_name!=c];m=smf.ols('price ~ inflation + C(country_name) + C(year)',data=z).fit(cov_type='cluster',cov_kwds={'groups':z.country_name},use_t=True);loo.append({'excluded':c,'beta':m.params['inflation'],'p':m.pvalues['inflation']})
pd.DataFrame(models).to_csv(OUT/'inflation_models.csv',index=False);pd.DataFrame(loo).to_csv(OUT/'inflation_leave_one_out.csv',index=False)
# Existing human-coded NYT Index sample plus transparent independent dictionary coding of the indexed abstracts.
nyt=pd.read_csv(DATA/'nyt.csv',encoding='latin1',low_memory=False);nyt=nyt[nyt.year.between(2010,2016)].copy();nyt=nyt[nyt.majortopic.notna() & nyt.Description.notna()].copy()
patterns={'climate':r'\b(climate change|global warming|greenhouse gas(?:es)?|carbon emission(?:s)?)\b','immigration':r'\b(immigra\w*|migran\w*|deport\w*|asylum|refugee\w*)\b','inflation_cost':r'\b(inflation|cost of living|consumer prices|rising prices|price increases?)\b','civil_rights':r'\b(civil rights|racial discrimination|racism|gay rights|same.sex marriage|transgender)\b'}
for key,pat in patterns.items():nyt[key]=nyt.Description.str.contains(pat,case=False,regex=True,na=False)
nyt['valid']=1;agg=nyt.groupby('year').agg(n=('valid','sum'),**{k:(k,'sum') for k in patterns});
for k in patterns:agg[k+'_pct']=100*agg[k]/agg.n
agg.to_csv(OUT/'nyt_keyword_counts.csv');
# Match samples for transparent manual inspection, without asserting classifier precision.
sample=[]
for k in patterns:
 subset=nyt[nyt[k]].sample(n=min(20,int(nyt[k].sum())),random_state=471)
 for _,r in subset.iterrows():sample.append({'query':k,'year':r.year,'text':r.Description,'human_code':r.majortopic})
pd.DataFrame(sample).to_csv(OUT/'nyt_keyword_audit_sample.csv',index=False)
fig,ax=plt.subplots(figsize=(10,5));
for k,l in [('climate','Климат'),('immigration','Иммиграция'),('inflation_cost','Инфляция / стоимость жизни'),('civil_rights','Права и дискриминация')]:ax.plot(agg.index,agg[k+'_pct'],marker='o',label=l)
ax.set(title='New York Times: словарный поиск в описаниях индексных записей',ylabel='Доля записей, %',xlabel='Год',xticks=range(2010,2017));ax.grid(axis='y',alpha=.22);ax.legend(frameon=False,ncol=2)
fig.text(.1,.01,'Одна газета; выборка индекса, 2010–2016. Узкий словарь и пропуски тем; проценты не равны аудитории.',fontsize=8)
fig.tight_layout(rect=[0,.06,1,1]);fig.savefig(OUT/'nyt_dictionary.png',dpi=180);plt.close(fig)
# Media climate concern combines volume and tone; not a count or share.
m=pd.read_csv(DATA/'mccc_monthly.csv.gz',parse_dates=['Date']);m['year']=m.Date.dt.year;annual=m.groupby('year').Aggregate.agg(['mean','count']);annual=annual.loc[2010:2026];annual.to_csv(OUT/'mccc_annual.csv')
fig,ax=plt.subplots(figsize=(10,4.8));a=annual.loc[2010:2025];ax.bar(a.index,a['mean'],color='#28836F');ax.set(title='Климатическая тревожность в СМИ США: индекс MCCC',ylabel='Среднее месячного индекса',xlabel='Год');ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
fig.text(.1,.01,'Ardia et al., версия 2026: объём климатических материалов и их тональность. Это не доля публикаций.',fontsize=8)
fig.tight_layout(rect=[0,.06,1,1]);fig.savefig(OUT/'mccc_annual.png',dpi=180);plt.close(fig)
print('DESCRIPTIVE 2019 TO 2024');print(pd.DataFrame(summary).query('from_year==2019 and to_year==2024').round(3).to_string(index=False));print('\nREGRESSION');print(pd.DataFrame(models).round(4).to_string(index=False));print('\nLEAVE ONE OUT range',min(v['beta'] for v in loo),max(v['beta'] for v in loo));print('\nNYT');print(agg.to_string());print('\nMCCC');print(annual.to_string())
