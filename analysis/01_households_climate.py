"""ESS8/10: financial difficulty and climate worry in the same respondent.

ESS rounds are independent cross sections. Weighted least squares is a linear
probability model with country-clustered SE, not a full survey design estimator.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
P=Path(__file__).resolve().parents[1]
COLS=['cntry','wrclmch','hincfel','pspwght','lrscale','agea','gndr','eisced']
frames=[]
for filename,wave,mode in [('ess8e02_3.dta',8,'interview'),('ess10e03_3.dta',10,'interview'),('ess10sce03_1.dta',10,'self')]:
    x=pd.read_stata(P/'data/raw'/filename,columns=COLS,convert_categoricals=False)
    x['wave']=wave; x['mode']=mode; frames.append(x)
d=pd.concat(frames,ignore_index=True)
old=set(d.loc[d.wave==8,'cntry']); new=set(d.loc[d.wave==10,'cntry']);matched=old&new
d=d[d.cntry.isin(matched)&d.wrclmch.between(1,5)&d.hincfel.between(1,4)&d.pspwght.gt(0)].copy()
d['worried']=(d.wrclmch>=4).astype(int);d['difficulty']=(d.hincfel>=3).astype(int);d['round10']=(d.wave==10).astype(int)
rows=[]
for (c,w,k),g in d.groupby(['cntry','wave','difficulty']):
    rows.append({'country':c,'wave':w,'difficulty':k,'n':len(g),'weighted_pct':100*np.average(g.worried,weights=g.pspwght),'weight_sum':g.pspwght.sum()})
r=pd.DataFrame(rows);r.to_csv(P/'data/processed/ess_hardship_country.csv',index=False)
z=d.groupby(['cntry','wave']).apply(lambda g:pd.Series({'n':len(g),'difficult_pct':100*np.average(g.difficulty,weights=g.pspwght),'both_pct':100*np.average(g.difficulty*g.worried,weights=g.pspwght)}),include_groups=False).reset_index()
z.to_csv(P/'data/processed/ess_hardship_overlap.csv',index=False)
t=r.groupby(['wave','difficulty']).agg(countries=('country','nunique'),n=('n','sum'),mean_pct=('weighted_pct','mean')).reset_index();t.to_csv(P/'data/processed/ess_hardship_summary.csv',index=False)
# Restrict both waves to countries using ESS10 interviews, including video.
interview_countries=set(d.loc[(d.wave==10)&(d['mode']=='interview'),'cntry'])
models=[]
for label,countries in [('all_matched',matched),('interview_countries',interview_countries)]:
 q=d[d.cntry.isin(countries)&d.lrscale.between(0,10)&d.agea.between(15,100)&d.gndr.isin([1,2])&d.eisced.between(1,7)].copy()
 q['age10']=q.agea/10;q['weight']=q.pspwght/q.groupby(['cntry','wave']).pspwght.transform('sum')
 fit=smf.wls('worried ~ difficulty * round10 + lrscale + age10 + C(gndr) + C(eisced) + C(cntry)',data=q,weights=q.weight).fit(cov_type='cluster',cov_kwds={'groups':q.cntry},use_t=True)
 for term in ['difficulty','round10','difficulty:round10']:
  ci=fit.conf_int().loc[term];models.append({'sample':label,'term':term,'n':len(q),'countries':q.cntry.nunique(),'coef_pp':100*fit.params[term],'ci_low_pp':100*ci[0],'ci_high_pp':100*ci[1],'p':fit.pvalues[term]})
 effect=fit.t_test('difficulty + difficulty:round10 = 0');ci=effect.conf_int().reshape(-1)
 models.append({'sample':label,'term':'difficulty_round10','n':len(q),'countries':q.cntry.nunique(),'coef_pp':100*float(effect.effect.item()),'ci_low_pp':100*ci[0],'ci_high_pp':100*ci[1],'p':float(effect.pvalue.item())})
pd.DataFrame(models).to_csv(P/'data/processed/ess_hardship_model.csv',index=False)
print('group means\n',t.to_string(index=False)); print('overlap mean by wave\n',z.groupby('wave')[['difficult_pct','both_pct']].mean().to_string());print('model\n',pd.DataFrame(models).round(4).to_string(index=False))
