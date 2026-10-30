"""Sensitivity bounds for missing manifesto documents, not a complete-population estimate."""
from pathlib import Path
import pandas as pd
P=Path(__file__).resolve().parents[1]
# Missing vote bounds are conditional on vote coverage reflecting distinct valid votes.
x=pd.read_csv(P/'data/processed/manifesto_issue_shares.csv');x=x[x.country.isin(['Brazil','Bulgaria','Israel','Serbia','Spain'])].sort_values('date').groupby('country').tail(1).copy();x=x[x.vote_coverage.between(0,100)].copy()
x['missing_vote_pct']=100-x.vote_coverage
x['broad_lower_bound_pct']=x.broad*x.vote_coverage/100
x['broad_upper_bound_pct']=x.broad_lower_bound_pct+x.missing_vote_pct
x[['country','date','n_documents','vote_coverage','broad','broad_lower_bound_pct','broad_upper_bound_pct']].to_csv(P/'data/processed/audit_manifesto_missing_bounds.csv',index=False)
print('Manifesto bounds',x[['country','date','broad','vote_coverage','broad_lower_bound_pct','broad_upper_bound_pct']].round(2).to_string(index=False))
