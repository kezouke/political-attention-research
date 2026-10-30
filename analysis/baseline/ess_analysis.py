"""Exploratory analysis of published subsets of ESS round 8 and round 10.
The 2016 file is a 16-country extraction; 2020 file is complete-case selected
and contains no sampling weights. These are not directly comparable waves.
"""
from pathlib import Path
import pandas as pd
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf
P=Path(__file__).resolve().parent
cols=['cntry','wrclmch','pspwght','lrscale','agea','gndr','eisced','freehms','imwbcnt']
d=pd.read_csv(P/'data/ess_wizard_2016.csv',usecols=cols)
d=d[d.wrclmch.between(1,5)&(d.pspwght>0)].copy();d['worried']=(d.wrclmch>=4).astype(int)
results=[]
for country,g in d.groupby('cntry'):
 results.append({'country':country,'n_valid':len(g),'weighted_pct':100*np.average(g.worried,weights=g.pspwght),'unweighted_pct':100*g.worried.mean(),'eff_n_kish':g.pspwght.sum()**2/(g.pspwght**2).sum()})
pd.DataFrame(results).sort_values('country').to_csv(P/'outputs/ess2016_country.csv',index=False)
d['group']=pd.cut(d.lrscale,[-.1,2,4,5,7,10],labels=['0–2','3–4','5','6–7','8–10'])
rows=[]
for (c,group),g in d.groupby(['cntry','group'],observed=True):
 rows.append({'country':c,'group':str(group),'n':len(g),'weighted_pct':100*np.average(g.worried,weights=g.pspwght)})
cs=pd.DataFrame(rows);cs.to_csv(P/'outputs/ess2016_ideology_country.csv',index=False)
cs.groupby('group').agg(countries=('country','size'),total_n=('n','sum'),mean_country_pct=('weighted_pct','mean'),min_country_pct=('weighted_pct','min'),max_country_pct=('weighted_pct','max')).to_csv(P/'outputs/ess2016_ideology.csv')
# Weighted country fixed-effect regression is exploratory; country clustered SE
# is not a full complex survey design variance estimator.
z=d[d.lrscale.between(0,10)&d.agea.between(15,100)&d.gndr.isin([1,2])&d.eisced.between(1,7)].copy();z['age10']=z.agea/10
z['equal_country_weight']=z.pspwght/z.groupby('cntry').pspwght.transform('sum')*len(z)/z.cntry.nunique()
m=smf.wls('worried ~ lrscale + age10 + C(gndr) + C(eisced) + C(cntry)',data=z,weights=z.equal_country_weight).fit(cov_type='cluster',cov_kwds={'groups':z.cntry,'use_correction':True},use_t=True)
out=[]
for var in ['lrscale','age10']:
 lo,hi=m.conf_int().loc[var];out.append({'term':var,'n':len(z),'countries':z.cntry.nunique(),'coef_pp':100*m.params[var],'ci_low_pp':100*lo,'ci_high_pp':100*hi,'p':m.pvalues[var]})
pd.DataFrame(out).to_csv(P/'outputs/ess2016_model.csv',index=False)
t=pd.read_csv(P/'data/ess10_complete_case.csv.gz');t=t[t.wrclmch.between(1,5)];t['worried']=t.wrclmch>=4
r=t.groupby('cntry').agg(n=('worried','size'),unweighted_pct=('worried','mean'));r['unweighted_pct']*=100;r.to_csv(P/'outputs/ess2020_completecase.csv')
print('ESS8 valid',len(d),'countries',d.cntry.nunique());print(pd.read_csv(P/'outputs/ess2016_ideology.csv').to_string(index=False));print(pd.DataFrame(out).to_string(index=False));print('ESS10 selected valid',len(t))
