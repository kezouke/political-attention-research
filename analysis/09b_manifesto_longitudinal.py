"""Party manifesto topic sensitivity in five focus countries, MPDS2023a.

Election-level aggregates only. Archived source and party-level outputs are not
redistributed. These are category shares of coded quasi-sentences, conditional
on available documents and valid votes. They are not a census of campaign speech.
"""
from pathlib import Path
import numpy as np
import pandas as pd
P=Path(__file__).resolve().parents[1]
d=pd.read_csv(P/'data/raw/manifesto_2023a.csv',low_memory=False)
countries=['Brazil','Bulgaria','Israel','Serbia','Spain']
d=d[d.countryname.isin(countries)&d.date.between(201000,202299)].copy()
# Exclude per416: anti-growth/sustainability has environmental content.
cols=[f'per{i}' for i in range(401,416)]+['per501','per705','per607','per608']
d['vote']=np.where(d.countryname.eq('Brazil'),d.presvote,d.pervote)
d=d[d.vote.gt(0)&d.total.gt(0)&d[cols].notna().all(axis=1)].copy()
d['economy_401_415']=d[[f'per{i}' for i in range(401,416)]].sum(axis=1)
d['environment_positive_501']=d.per501
d['minority_positive_705']=d.per705
d['multicultural_both_607_608']=d.per607+d.per608
measures=['economy_401_415','environment_positive_501','minority_positive_705','multicultural_both_607_608']
rows=[]
for (country,date),g in d.groupby(['countryname','date']):
    row={'country':country,'date':date,'n_documents':len(g),'vote_coverage':g.vote.sum(),
         'single_party_vote_coverage':g[g.progtype.eq(1)].vote.sum(),
         'manual4_vote_coverage':g[g.manual.eq(4)].vote.sum(),
         'manual5_vote_coverage':g[g.manual.eq(5)].vote.sum()}
    for m in measures:
        row[m]=np.average(g[m],weights=g.vote)
        row[m+'_single_party']=np.average(g[g.progtype.eq(1)][m],weights=g[g.progtype.eq(1)].vote) if g.progtype.eq(1).any() else np.nan
    rows.append(row)
outputs=P/'data/processed'; agg=pd.DataFrame(rows);agg.to_csv(outputs/'manifesto_focus_longitudinal.csv',index=False)
# Restrict the endpoint comparison to matching party IDs with single-party
# manifestos at both elections and average their first/last vote shares as one
# constant set of weights. Composition cannot be removed within coalition docs.
matched=[]
for country,g in d.groupby('countryname'):
    lo,hi=g.date.min(),g.date.max();a=g[(g.date==lo)&g.progtype.eq(1)];b=g[(g.date==hi)&g.progtype.eq(1)]
    # Brazil identifies presidential candidate as well as party in original data;
    # do not claim a stable actor by matching party when candidates change.
    if country=='Brazil': continue
    if a.party.duplicated().any() or b.party.duplicated().any(): continue
    q=a.merge(b,on='party',suffixes=('_first','_last'))
    if q.empty:continue
    w=(q.vote_first+q.vote_last)/2
    for m in measures:
        matched.append({'country':country,'first_date':lo,'last_date':hi,'n_matched_parties':len(q),
                        'first_vote_coverage':q.vote_first.sum(),'last_vote_coverage':q.vote_last.sum(),
                        'manual_changed_parties':int((q.manual_first!=q.manual_last).sum()),
                        'topic':m,'first_share':np.average(q[m+'_first'],weights=w),
                        'last_share':np.average(q[m+'_last'],weights=w),
                        'change_pp':np.average(q[m+'_last']-q[m+'_first'],weights=w)})
pd.DataFrame(matched).to_csv(outputs/'manifesto_focus_matched_sensitivity.csv',index=False)
print(agg.round(2).to_string(index=False));print('\nMatched\n',pd.DataFrame(matched).round(2).to_string(index=False))
