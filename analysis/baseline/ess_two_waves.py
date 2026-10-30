import pandas as pd,numpy as np
from scipy.stats import ttest_rel
from pathlib import Path
P=Path(__file__).resolve().parent
a=pd.read_csv(P/'data/ess_wizard_2016.csv',usecols=['cntry','dweight','wrclmch']);b=pd.read_csv(P/'data/ess10_early_release.csv.gz',usecols=['cntry','dweight','wrclmch']); common=sorted(set(a.cntry)&set(b.cntry));rows=[]
for wave,d in [(8,a),(10,b)]:
 for c in common:
  g=d[(d.cntry==c)&d.wrclmch.between(1,5)&(d.dweight>0)].copy(); x=(g.wrclmch>=4).astype(int); rows.append({'country':c,'wave':wave,'n':len(g),'pct':100*np.average(x,weights=g.dweight),'kish_n':g.dweight.sum()**2/(g.dweight**2).sum()})
r=pd.DataFrame(rows); r.to_csv(P/'outputs/ess_early_two_waves.csv',index=False); p=r.pivot(index='country',columns='wave',values='pct');p['change_pp']=p[10]-p[8];print(r.to_string(index=False)); print(p.to_string());print('means',p.mean().to_dict(),'paired t',ttest_rel(p[10],p[8]))
