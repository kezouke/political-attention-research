"""ESS8 edition 2.3 vs ESS10 edition 3.3 and ESS10SC edition 3.1.
Weighted estimates, equal weight across countries, exploratory uncertainty.
Survey changes are observational; mode and sample composition may change.
"""
from pathlib import Path
import numpy as np,pandas as pd
import scipy.stats as st
import statsmodels.formula.api as smf
P=Path(__file__).resolve().parent
cols=['cntry','wrclmch','pspwght','dweight','lrscale','agea','gndr','eisced','freehms','imwbcnt']
frames=[]
for fn,wave,mode in [('ess8e02_3.dta',8,'interview'),('ess10e03_3.dta',10,'interview'),('ess10sce03_1.dta',10,'self-completion')]:
 csv=P/'data'/(fn.replace('.dta','_selected.csv.gz')); d=pd.read_csv(csv) if csv.exists() else pd.read_stata(P/'data'/fn,columns=cols,convert_categoricals=False);d['wave']=wave;d['collection']=mode;frames.append(d)
a=pd.concat(frames,ignore_index=True);r=[]
for (wave,c,mode),g in a.groupby(['wave','cntry','collection']):
 g=g[g.wrclmch.between(1,5)&g.pspwght.gt(0)].copy();g['worried']=g.wrclmch.ge(4).astype(int)
 if len(g)==0:continue
 r.append(dict(wave=wave,country=c,mode=mode,n=len(g),pct=100*np.average(g.worried,weights=g.pspwght),kish_n=g.pspwght.sum()**2/(g.pspwght**2).sum()))
r=pd.DataFrame(r);r.to_csv(P/'outputs/ess_full_country_wave.csv',index=False)
x=r[r.wave==8].drop(columns=['mode']).merge(r[r.wave==10].drop(columns=['wave']),on='country',suffixes=('_2016','_2020'),validate='one_to_one');x['change_pp']=x.pct_2020-x.pct_2016;x.to_csv(P/'outputs/ess_full_country_changes.csv',index=False)
for k,g in [('all',x),('interview',x[x['mode']=='interview']),('self-completion',x[x['mode']=='self-completion'])]:
 t=st.ttest_1samp(g.change_pp,0); delta=g.change_pp.mean(); se=st.sem(g.change_pp);lo,hi=st.t.interval(.95,df=len(g)-1,loc=delta,scale=se)
 print(k,'countries',len(g),'mean2016',g.pct_2016.mean(),'mean2020',g.pct_2020.mean(),'change',delta,'ci',lo,hi,'p',t.pvalue,'n',g.n_2016.sum(),g.n_2020.sum())
print(x[['country','mode','n_2016','n_2020','pct_2016','pct_2020','change_pp']].round(2).to_string(index=False))
z=a[a.cntry.isin(x.country)&a.wrclmch.between(1,5)&a.lrscale.between(0,10)&a.agea.between(15,100)&a.gndr.isin([1,2])&a.eisced.between(1,7)&a.pspwght.gt(0)].copy();z['worried']=(z.wrclmch>=4).astype(int);z['age10']=z.agea/10;z['round10']=(z.wave==10).astype(int);z['eqweight']=z.pspwght/z.groupby(['cntry','wave']).pspwght.transform('sum');
m=smf.wls('worried ~ lrscale * round10 + age10 + C(gndr) + C(eisced) + C(cntry)',data=z,weights=z.eqweight).fit(cov_type='cluster',cov_kwds={'groups':z.cntry},use_t=True)
model=[]
for v in ['lrscale','round10','lrscale:round10']:
 lo,hi=m.conf_int().loc[v];model.append(dict(term=v,coef_pp=100*m.params[v],ci_low_pp=100*lo,ci_high_pp=100*hi,p=m.pvalues[v],n=len(z),countries=z.cntry.nunique()))
pd.DataFrame(model).to_csv(P/'outputs/ess_full_model.csv',index=False);print(pd.DataFrame(model).to_string(index=False))
# Sensitivity to design-only weights, with the same matched countries and outcome.
checks=[]
for (wave,c),g in a[a.cntry.isin(x.country)].groupby(['wave','cntry']):
 g=g[g.wrclmch.between(1,5)&g.dweight.gt(0)]
 checks.append({'wave':wave,'country':c,'pct_dweight':100*np.average(g.wrclmch.ge(4),weights=g.dweight)})
b=pd.DataFrame(checks);wide=b.pivot(index='country',columns='wave',values='pct_dweight').dropna();print('design-only, equal-country change:',(wide[10]-wide[8]).mean());wide.to_csv(P/'outputs/ess_full_design_weight_sensitivity.csv')
