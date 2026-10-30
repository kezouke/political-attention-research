"""ESS8/10: association of subjective income difficulty with political trust.
Independent cross sections; association is not an effect of hardship or a vote.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
P=Path(__file__).resolve().parents[1]
cols=['cntry','hincfel','pspwght','trstprl','trstplt','imueclt','imbgeco','lrscale','agea','gndr','eisced']
frames=[]
for file,wave,mode in [('ess8e02_3.dta',8,'interview'),('ess10e03_3.dta',10,'interview'),('ess10sce03_1.dta',10,'self')]:
 x=pd.read_stata(P/'data/raw'/file,columns=cols,convert_categoricals=False);x['wave']=wave;x['mode']=mode;frames.append(x)
d=pd.concat(frames,ignore_index=True);match=set(d[d.wave==8].cntry)&set(d[d.wave==10].cntry)
d=d[d.cntry.isin(match)&d.pspwght.gt(0)&d.hincfel.between(1,4)].copy();d['pspwght']=d.pspwght.astype('float64');d['difficulty']=(d.hincfel>=3).astype(int)
rows=[]; models=[]
for outcome in ['trstprl','trstplt','imueclt','imbgeco']:
 valid=d[d[outcome].between(0,10)].copy()
 for (country,wave,mode,k),g in valid.groupby(['cntry','wave','mode','difficulty']):
  rows.append({'country':country,'wave':wave,'mode':mode,'difficulty':k,'outcome':outcome,'n':len(g),'mean_0_10':np.average(g[outcome],weights=g.pspwght)})
 for covar in ['base','with_ideology','country_wave','interview_only']:
  filt=valid.agea.between(15,100)&valid.gndr.isin([1,2])&valid.eisced.between(1,7)
  if covar=='with_ideology':filt &= valid.lrscale.between(0,10)
  if covar=='interview_only':
   interview=set(d[(d.wave==10)&(d['mode']=='interview')].cntry);filt &= valid.cntry.isin(interview)
  q=valid[filt].copy();q['weight']=q.pspwght/q.groupby(['cntry','wave']).pspwght.transform('sum');q['age10']=q.agea/10
  fixed='C(cntry)*C(wave)' if covar=='country_wave' else 'C(cntry) + C(wave)'
  formula=f'{outcome} ~ difficulty + age10 + C(gndr) + C(eisced) + {fixed}'+(' + lrscale' if covar=='with_ideology' else '')
  m=smf.wls(formula,data=q,weights=q.weight).fit(cov_type='cluster',cov_kwds={'groups':q.cntry},use_t=True);ci=m.conf_int().loc['difficulty']
  models.append({'outcome':outcome,'covariates':covar,'n':len(q),'countries':q.cntry.nunique(),'beta_0_10':m.params['difficulty'],'ci_low':ci[0],'ci_high':ci[1],'p':m.pvalues['difficulty']})
pd.DataFrame(rows).to_csv(P/'data/processed/ess_insecurity_trust_country.csv',index=False);pd.DataFrame(models).to_csv(P/'data/processed/ess_insecurity_trust_models.csv',index=False)
print(pd.DataFrame(models).round(3).to_string(index=False))
