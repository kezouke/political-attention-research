"""Vote-weighted salience in coded documents in Manifesto Project 2023a.
Weights are vote shares among coded documents; Brazil uses first-round presidential vote.
Not an estimate for unrepresented parties or a measure of enacted policy.
"""
from pathlib import Path
import numpy as np,pandas as pd
P=Path(__file__).resolve().parent
x=pd.read_csv(P/'data/manifesto_2023a.csv',low_memory=False)
cs=['United States','United Kingdom','Spain','Serbia','Russia','Brazil','Israel','Bulgaria','France','Germany']
x=x[x.countryname.isin(cs)&x.date.between(201000,202399)].copy()
x['vote']=np.where(x.countryname.eq('Brazil'),x.presvote,x.pervote)
codes={'environment':'per501','anticorruption':'per304','law_order':'per605','diversity_positive':'per607','minorities':'per705'}
x=x[(x.vote>0)&(x.total>0)&x[list(codes.values())].notna().all(axis=1)].copy()
out=[]
for (country,date),g in x.groupby(['countryname','date']):
 row={'country':country,'date':int(date),'year':int(date)//100,'n_documents':len(g),'vote_coverage':g.vote.sum()}
 for label,col in codes.items():row[label]=np.average(g[col],weights=g.vote)
 full=g[g.progtype==1];row['single_party_vote_coverage']=full.vote.sum()
 for label,col in codes.items():row['single_party_'+label]=np.average(full[col],weights=full.vote) if len(full) else np.nan
 out.append(row)
d=pd.DataFrame(out);d.to_csv(P/'outputs/manifesto_vote_weighted.csv',index=False)
x[['countryname','date','partyname','partyabbrev','candidatename','vote','total','progtype']+list(codes.values())].to_csv(P/'outputs/manifesto_documents.csv',index=False)
print(d[['country','date','n_documents','vote_coverage','single_party_vote_coverage','environment','anticorruption','law_order','minorities']].to_string(index=False,float_format=lambda x:f'{x:.2f}'))
