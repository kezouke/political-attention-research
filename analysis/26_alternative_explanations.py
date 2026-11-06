"""Comparator timing, pre-crisis changes, coverage and country sensitivity."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'data/processed'
RNG = np.random.default_rng(20261106)


def country_bootstrap(frame, column, reps=4000):
    """Equal-country mean and resampling interval, not a causal-effect CI."""
    values = frame.groupby('iso')[column].mean().dropna().to_numpy()
    if len(values) < 2:
        return [np.nan]*3
    means = RNG.choice(values,(reps,len(values)),replace=True).mean(axis=1)
    return [values.mean(), *np.quantile(means,[.025,.975])]


def dynamics_benchmarks():
    main = pd.read_csv(OUT/'crisis_dynamics_balanced.csv')
    controls = pd.read_csv(OUT/'crisis_election_controls.csv',parse_dates=['pre_date','post_date'])
    c = controls[controls.type.eq('legislative') & controls.status.eq('paired')
                 & controls.pre_regime.ge(2) & controls.post_regime.ge(2)
                 & controls.iso.isin(main.iso)].copy()
    # Both consecutive intervals must meet the original calm-period rule.
    joined = c.merge(c,on='iso',suffixes=('_a','_b'))
    joined = joined[joined.post_date_a.eq(joined.pre_date_b)
                    & (joined.post_date_b-joined.pre_date_a).dt.days.le(10*365.25)].copy()
    joined['first_change_pp'] = joined.post_vote_pct_a-joined.pre_vote_pct_a
    joined['second_change_pp'] = joined.post_vote_pct_b-joined.pre_vote_pct_a
    joined['additional_pp'] = joined.post_vote_pct_b-joined.post_vote_pct_a
    outcols = ['iso','country_a','pre_date_a','post_date_a','post_date_b','first_change_pp','second_change_pp','additional_pp']
    joined[outcols].rename(columns={'country_a':'country','pre_date_a':'baseline_date','post_date_a':'first_date','post_date_b':'second_date'}).to_csv(OUT/'crisis_dynamics_calm.csv',index=False,float_format='%.8g')
    rows=[]
    bank=main.rename(columns={'change_pp_first':'first_change_pp','change_pp_second':'second_change_pp'})
    for name,q in [('banking',bank),('calm',joined),('banking_common_countries',bank[bank.iso.isin(joined.iso)])]:
        for col in ['first_change_pp','second_change_pp','additional_pp']:
            mean,lo,hi=country_bootstrap(q,col)
            rows.append(dict(sample=name,outcome=col,n=len(q),countries=q.iso.nunique(),
                             mean_pp=q[col].mean(),median_pp=q[col].median(),equal_country_mean=mean,
                             bootstrap_low=lo,bootstrap_high=hi,increased=int(q[col].gt(1e-5).sum())))
    # Country-specific difference between banking and calm trajectories.
    for col in ['first_change_pp','second_change_pp','additional_pp']:
        compared=bank.groupby('iso')[col].mean().to_frame('bank').join(joined.groupby('iso')[col].mean().rename('calm')).dropna()
        compared['difference']=compared.bank-compared.calm
        mean,lo,hi=country_bootstrap(compared.reset_index(),'difference')
        rows.append(dict(sample='within_country_bank_minus_calm',outcome=col,n=len(compared),countries=len(compared),
                         mean_pp=mean,median_pp=compared.difference.median(),equal_country_mean=mean,
                         bootstrap_low=lo,bootstrap_high=hi))
    result=pd.DataFrame(rows)
    result.to_csv(OUT/'crisis_dynamics_benchmarks.csv',index=False,float_format='%.8g')
    print(result.round(3).to_string(index=False))


def programme_checks():
    data=pd.read_csv(OUT/'programme_decomposition.csv')
    main=data[data['sample'].eq('main')].copy()
    results=[]
    for topic in ['economy','material_broad','anticorruption','environment']:
        selected=main[main.topic.eq(topic)]
        bank=selected[selected.kind.eq('banking')]
        prior=selected[selected.kind.eq('prior')].copy()
        prior['original_id']=prior.pair_id.str.replace('_prior','',regex=False)
        common=bank.merge(prior,left_on='pair_id',right_on='original_id',suffixes=('_bank','_prior'))
        common['iso']=common.iso_bank
        for col in ['change_pp','within_pp','reweight_pp','roster_pp']:
            common['difference']=common[col+'_bank']-common[col+'_prior']
            mean,lo,hi=country_bootstrap(common,'difference')
            results.append(dict(topic=topic,check='bank_minus_prior',outcome=col,n=len(common),countries=common.iso.nunique(),
                                mean=common.difference.mean(),median=common.difference.median(),
                                equal_country_mean=mean,bootstrap_low=lo,bootstrap_high=hi))
        for name,q in [('all',bank),('no_2007_09',bank[~bank.onset_year.between(2007,2009)]),
                       ('common_75',bank[bank.common_pre_coverage.ge(75)&bank.common_post_coverage.ge(75)]),
                       ('no_manual_change',bank[bank.manual_changes.eq(0)]),
                       ('no_coder_change',bank[bank.coder_changes.eq(0)])]:
            for col in ['change_pp','within_pp','reweight_pp','roster_pp']:
                mean,lo,hi=country_bootstrap(q,col)
                results.append(dict(topic=topic,check=name,outcome=col,n=len(q),countries=q.iso.nunique(),
                                    mean=q[col].mean(),median=q[col].median(),equal_country_mean=mean,bootstrap_low=lo,bootstrap_high=hi))
        for iso in bank.iso.unique():
            q=bank[bank.iso.ne(iso)]
            results.append(dict(topic=topic,check='leave_out_'+iso,outcome='change_pp',n=len(q),countries=q.iso.nunique(),
                                mean=q.change_pp.mean(),median=q.change_pp.median()))
    checks=pd.DataFrame(results)
    checks.to_csv(OUT/'programme_robustness.csv',index=False,float_format='%.8g')
    print(checks[checks.topic.eq('economy') & ~checks.check.str.startswith('leave_out')].round(3).to_string(index=False))


if __name__=='__main__':
    dynamics_benchmarks()
    programme_checks()
