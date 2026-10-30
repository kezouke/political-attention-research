"""Sensitivity of ESS climate-worry estimates to non-observation after routing.

This is a separate computational pass, not independent human peer review. Assuming
that people routed past climate worry are not strongly worried is a counterfactual
bounding scenario, not observed worry. A respondent who denies climate change is happening may not have been asked
the worry question; their true response remains unknown.
"""
from pathlib import Path
import numpy as np
import pandas as pd
P=Path(__file__).resolve().parents[1]
parts=[]
for file,wave,mode in [('ess8e02_3.dta',8,'interview'),('ess10e03_3.dta',10,'interview'),('ess10sce03_1.dta',10,'self')]:
    d=pd.read_stata(P/'data/raw'/file,columns=['cntry','ccnthum','wrclmch','pspwght'],convert_categoricals=False)
    d['wave']=wave;d['mode']=mode;parts.append(d)
d=pd.concat(parts,ignore_index=True);d=d[d.pspwght.gt(0)].copy()
countries=set(d[d.wave==8].cntry)&set(d[d.wave==10].cntry)
d=d[d.cntry.isin(countries)]
rows=[]
for (c,w),g in d.groupby(['cntry','wave']):
    observed=g[g.wrclmch.between(1,5)]
    added=g[(g.ccnthum==55)&g.wrclmch.isna()]
    expanded=pd.concat([observed,added])
    rows.append({'country':c,'wave':w,'mode':g['mode'].iloc[0],'observed_n':len(observed),
      'routed_skeptic_n':len(added),'positive_weight_n':len(g),'observed_pct':100*np.average(observed.wrclmch>=4,weights=observed.pspwght),
      'scenario_skeptics_not_worried_pct':100*np.average(expanded.wrclmch>=4,weights=expanded.pspwght),
      'scenario_skeptics_strongly_worried_pct':100*np.average((expanded.wrclmch>=4)|((expanded.ccnthum==55)&expanded.wrclmch.isna()),weights=expanded.pspwght)})
r=pd.DataFrame(rows);r.to_csv(P/'data/processed/audit_ess_skip_sensitivity.csv',index=False)
wide=r.pivot(index='country',columns='wave',values=['observed_pct','scenario_skeptics_not_worried_pct','scenario_skeptics_strongly_worried_pct']);
for metric in ['observed_pct','scenario_skeptics_not_worried_pct','scenario_skeptics_strongly_worried_pct']:
    wide[(metric,'change')]=wide[(metric,10)]-wide[(metric,8)]
wide[('change_min_pp','')]=wide[('scenario_skeptics_not_worried_pct',10)]-wide[('scenario_skeptics_strongly_worried_pct',8)]
wide[('change_max_pp','')]=wide[('scenario_skeptics_strongly_worried_pct',10)]-wide[('scenario_skeptics_not_worried_pct',8)]
wide.columns=[f'{a}_{b}' if b else a for a,b in wide.columns];wide=wide.reset_index()
wide.to_csv(P/'data/processed/audit_ess_changes_sensitivity.csv',index=False)
# A leave-one-out range quantifies dependence on the 22 matched countries.
c=wide.observed_pct_change.to_numpy()
loo=np.array([np.delete(c,i).mean() for i in range(len(c))]);
pd.DataFrame([{'n_countries':len(c),'mean_change_pp':c.mean(),'median_change_pp':np.median(c),'loo_min_pp':loo.min(),'loo_max_pp':loo.max()}]).to_csv(P/'data/processed/audit_ess_country_sensitivity.csv',index=False)
print('ESS sensitivity',wide[wide.country.isin(['ES','IL'])].round(3).to_string(index=False))
