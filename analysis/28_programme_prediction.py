"""Does programme content add predictive value for continuing parties?

Historical forward tests, country-grouped tuning, election-balanced errors.
The baseline omits polls, leadership and incumbency: it is deliberately modest.
"""
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import GroupKFold

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data/processed'
spec=importlib.util.spec_from_file_location('programmes',ROOT/'analysis/24_programme_decomposition.py')
programmes=importlib.util.module_from_spec(spec);spec.loader.exec_module(programmes)
TOPICS=['economy','material_broad','anticorruption','environment']
BASE=['vote_pre','duration','postyear']


def dataset():
    docs=programmes.load_documents();docs=docs[docs.progtype.isin([1,2,8])]
    audit=pd.read_csv(OUT/'programme_coverage.csv',parse_dates=['pre_date','post_date'])
    audit=audit[audit['sample'].eq('main')&audit.status.eq('included')&audit.kind.isin(['banking','recession','comparison'])]
    audit=audit.sort_values('kind').drop_duplicates(['iso','pre_date','post_date'])
    rows=[]
    for e in audit.itertuples():
        d=docs[docs.countryname.eq(programmes.ALIASES.get(e.country,e.country))]
        a=d[d.date.eq(int(e.pre_date.strftime('%Y%m')))];b=d[d.date.eq(int(e.post_date.strftime('%Y%m')))]
        q=a.merge(b,on='party',suffixes=('_pre','_post'))
        for p in q.itertuples():
            r=dict(iso=e.iso,pair_id=e.pair_id,kind=e.kind,vote_pre=p.pervote_pre,
                   duration=e.duration_years,postyear=e.post_date.year,parfam=str(p.parfam_pre),
                   target=p.pervote_post-p.pervote_pre)
            for t in TOPICS:
                r[t+'_pre']=getattr(p,t+'_pre');r[t+'_change']=getattr(p,t+'_post')-getattr(p,t+'_pre')
            rows.append(r)
    return pd.DataFrame(rows)


def model(features,alpha):
    return make_pipeline(ColumnTransformer([('numeric',StandardScaler(),features),
                                            ('family',OneHotEncoder(handle_unknown='ignore'),['parfam'])]),
                         Ridge(alpha=alpha))


def election_mae(truth,pred,pairs):
    return pd.DataFrame({'error':np.abs(np.asarray(truth)-pred),'pair':np.asarray(pairs)}).groupby('pair').error.mean().mean()


def main():
    d=dataset();rows=[];predictions=[]
    feature_sets={'baseline':BASE,'prior_topics':BASE+[t+'_pre' for t in TOPICS],
                  'programme_changes':BASE+[t+s for t in TOPICS for s in ['_pre','_change']]}
    for start in [2000,2005,2010,2015]:
        train=d[d.postyear.lt(start)];test=d[d.postyear.ge(start)&d.postyear.lt(start+5)]
        if train.iso.nunique()<5 or test.empty:continue
        for name,features in feature_sets.items():
            scores=[]
            for alpha in [1,10,100,1000]:
                errors=[]
                for ix,jx in GroupKFold(n_splits=5).split(train,groups=train.iso):
                    a,b=train.iloc[ix],train.iloc[jx]
                    estimator=model(features,alpha)
                    weights=1/a.groupby('pair_id').target.transform('size').to_numpy()
                    estimator.fit(a,a.target,ridge__sample_weight=weights/weights.mean())
                    errors.append(election_mae(b.target,estimator.predict(b),b.pair_id))
                scores.append((np.mean(errors),alpha))
            _,alpha=min(scores)
            estimator=model(features,alpha)
            weights=1/train.groupby('pair_id').target.transform('size').to_numpy()
            estimator.fit(train,train.target,ridge__sample_weight=weights/weights.mean())
            pred=estimator.predict(test)
            rows.append(dict(test_start=start,model=name,alpha=alpha,n_train=len(train),n_test=len(test),
                             test_elections=test.pair_id.nunique(),test_countries=test.iso.nunique(),
                             election_mae=election_mae(test.target,pred,test.pair_id),
                             party_mae=np.abs(test.target-pred).mean()))
            q=test[['iso','pair_id','kind']].copy();q['absolute_error']=np.abs(test.target-pred)
            # Aggregates over parties only, never source rows.
            q=q.groupby(['iso','pair_id','kind']).absolute_error.mean().reset_index()
            q['model']=name;q['test_start']=start;predictions.append(q)
        rows.append(dict(test_start=start,model='no_change',n_train=len(train),n_test=len(test),
                         test_elections=test.pair_id.nunique(),test_countries=test.iso.nunique(),
                         election_mae=election_mae(test.target,np.zeros(len(test)),test.pair_id),party_mae=test.target.abs().mean()))
        q=test[['iso','pair_id','kind']].copy();q['absolute_error']=test.target.abs()
        q=q.groupby(['iso','pair_id','kind']).absolute_error.mean().reset_index()
        q['model']='no_change';q['test_start']=start;predictions.append(q)
    metrics=pd.DataFrame(rows);metrics.to_csv(OUT/'programme_prediction.csv',index=False,float_format='%.8g')
    errors=pd.concat(predictions,ignore_index=True);errors.to_csv(OUT/'programme_prediction_elections.csv',index=False,float_format='%.8g')
    wide=errors.pivot(index=['iso','pair_id','test_start'],columns='model',values='absolute_error').reset_index()
    rng=np.random.default_rng(20261106);comparisons=[]
    for name in ['prior_topics','programme_changes']:
        diff=wide[name]-wide.baseline
        by_country=wide.assign(difference=diff).groupby('iso').difference.mean().to_numpy()
        boot=rng.choice(by_country,(4000,len(by_country)),replace=True).mean(axis=1)
        comparisons.append(dict(model=name,elections=len(wide),countries=len(by_country),
                                election_mean_error_difference=diff.mean(),country_mean_error_difference=by_country.mean(),
                                bootstrap_low=np.quantile(boot,.025),bootstrap_high=np.quantile(boot,.975)))
    pd.DataFrame(comparisons).to_csv(OUT/'programme_prediction_comparison.csv',index=False,float_format='%.8g')
    print(metrics.round(3).to_string(index=False))
    print('Pooled election MAE',errors.groupby('model').absolute_error.mean().round(3).to_dict())


if __name__=='__main__':main()
