"""Test two explicit proxies for the '80% of manifestos' claim.

Manifesto Project 2023a percentages are shares of coded quasi-sentences.
These categories do not classify all possible references to the claimed ideas.
Strict: domain 4 economy (401-416) plus anti-corruption (304).
Broad additionally includes welfare (503-504), labour (701-702), democracy
and constitution (202-204), and administration/institutions (301-303, 305).
Distinct 3-digit codes are summed once. Country-election means are weighted by
vote share among documents with content and vote information. Brazil uses the
presidential first-round vote. Missing/unrepresented votes are reported.
"""
from pathlib import Path
import numpy as np,pandas as pd
P=Path(__file__).resolve().parents[1]
x=pd.read_csv(P/'data/raw/manifesto_2023a.csv',low_memory=False)
countries=['Brazil','Bulgaria','Israel','Serbia','Spain','Russia','United Kingdom','United States','France','Germany']
x=x[x.countryname.isin(countries)&x.date.between(201000,202299)].copy()
strict=[f'per{i}' for i in range(401,417)]+['per304']
extra=['per503','per504','per701','per702','per202','per203','per204','per301','per302','per303','per305']
x['vote']=np.where(x.countryname.eq('Brazil'),x.presvote,x.pervote)
x=x[(x.vote>0)&(x.total>0)&x[strict+extra].notna().all(axis=1)].copy()
x['strict']=x[strict].sum(axis=1);x['broad']=x[strict+extra].sum(axis=1)
assert (x.strict<=x.broad+1e-6).all() and (x.broad<=100.1).all()
x['environment']=x.per501;x['corruption']=x.per304
out=[]
for (country,date),g in x.groupby(['countryname','date']):
 row=dict(country=country,date=int(date),year=int(date)//100,n_documents=len(g),vote_coverage=g.vote.sum(),single_party_coverage=g.loc[g.progtype.eq(1),'vote'].sum())
 for v in ['strict','broad','environment','corruption']:row[v]=np.average(g[v],weights=g.vote)
 out.append(row)
y=pd.DataFrame(out);y.to_csv(P/'data/processed/manifesto_issue_shares.csv',index=False)
x[['countryname','date','partyname','candidatename','vote','total','progtype','strict','broad','environment','corruption']].to_csv(P/'data/processed/manifesto_issue_documents.csv',index=False)
print('ALL ELECTIONS\n',y.round(2).to_string(index=False));print('\nlatest country election'); print(y.sort_values('date').groupby('country').tail(1).round(2).to_string(index=False))
