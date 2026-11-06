"""Locked observational EB models; no respondent-level exports.

Post-election measurement means these are conditional associations and held-out
classification checks, not electoral forecasts or causal effects. Input hashes
must match the committed measurement contract before any real-data fitting.
"""
from pathlib import Path
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import platform
import warnings

import numpy as np
import pandas as pd
import scipy
from scipy.special import expit, softmax
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import OneHotEncoder
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('inputs',ROOT/'analysis/50_eurobarometer_model_inputs.py')
inputs=importlib.util.module_from_spec(spec);spec.loader.exec_module(inputs)
OUT=inputs.OUT
CONTRASTS={'national_economy_bad':(1/3,2/3),'government_distrust':(0.,1.),
           'economic_priority':(0.,1.),'party_distrust':(0.,1.)}
TARGETS=['government_vs_opposition','opposition_type','nonvote_vs_vote','four_outcomes']


def fitted(X,y,w,C=1.):
    model=LogisticRegression(C=C,l1_ratio=0.,solver='lbfgs',tol=1e-7,max_iter=1500)
    with warnings.catch_warnings():
        warnings.simplefilter('error',ConvergenceWarning)
        model.fit(X,y,sample_weight=w)
    assert np.isfinite(model.coef_).all()
    return model


def design(train,test,block='full',drop_controls=False):
    numeric=([] if drop_controls else inputs.CONTROLS)+inputs.BLOCKS[block]
    categories=['country'] if drop_controls else inputs.CATEGORICAL
    encoder=OneHotEncoder(handle_unknown='ignore',sparse_output=False,dtype=float)
    cat_train=encoder.fit_transform(train[categories]);cat_test=encoder.transform(test[categories])
    X=np.column_stack([train[numeric].to_numpy(float),cat_train])
    Z=np.column_stack([test[numeric].to_numpy(float),cat_test])
    assert np.isfinite(X).all() and np.isfinite(Z).all()
    names=numeric+encoder.get_feature_names_out(categories).tolist()
    return X,Z,names


def metrics(y,p,w):
    labels=np.arange(p.shape[1]);onehot=np.eye(len(labels))[y]
    return {'log_loss':float(log_loss(y,p,sample_weight=w,labels=labels)),
            'brier_sum_over_classes':float(np.average(((p-onehot)**2).sum(axis=1),weights=w))}


def margins(model,X,w,names,contrasts=CONTRASTS):
    eta=model.decision_function(X)
    out=[]
    binary=eta.ndim==1
    for variable,(low,high) in contrasts.items():
        if variable not in names:continue
        j=names.index(variable)
        def probability(value):
            if binary:
                q=expit(eta+(value-X[:,j])*model.coef_[0,j])
                return np.column_stack([1-q,q])
            shifted=eta+(value-X[:,j,None])*model.coef_[:,j]
            return softmax(shifted,axis=1)
        lo,hi=probability(low),probability(high)
        delta=np.average(hi-lo,weights=w,axis=0)
        assert abs(delta.sum())<1e-10
        for k,c in enumerate(model.classes_):
            out.append({'variable':variable,'outcome':int(c),'low':low,'high':high,
                        'probability_difference':float(delta[k]),
                        'probability_at_low':float(np.average(lo[:,k],weights=w)),
                        'probability_at_high':float(np.average(hi[:,k],weights=w))})
    return out


def cross_validate(x,block,mode,seed,C=1.):
    n=len(x);p=np.full((n,x.y.nunique()),np.nan)
    if mode=='within_country':
        # Stratification is set before prediction; labels are used only to split,
        # not to estimate a held-out country's intercept or any feature encoding.
        strata=x.country.astype(str)+'_'+x.y.astype(str)
        smallest=strata.value_counts().min()
        assert smallest>=5,('Too few observations for declared five folds',smallest)
        splits=StratifiedKFold(5,shuffle=True,random_state=seed).split(np.zeros(n),strata)
    elif mode=='leave_country_out':
        splits=((np.flatnonzero(x.country.ne(c).to_numpy()),np.flatnonzero(x.country.eq(c).to_numpy()))
                for c in sorted(x.country.unique()))
    else:raise ValueError(mode)
    for train,test in splits:
        a,b=x.iloc[train],x.iloc[test]
        X,Z,_=design(a,b,block)
        model=fitted(X,a.y.to_numpy(),inputs.normalized_weights(a).to_numpy(),C)
        assert np.array_equal(model.classes_,np.arange(p.shape[1]))
        p[test]=model.predict_proba(Z)
    assert np.isfinite(p).all() and np.allclose(p.sum(axis=1),1.)
    w=inputs.normalized_weights(x).to_numpy();y=x.y.to_numpy()
    overall=metrics(y,p,w)
    per_country=[];calibration=[]
    for c in sorted(x.country.unique()):
        mask=x.country.eq(c).to_numpy()
        per_country.append({'country':c,**metrics(y[mask],p[mask],w[mask])})
    # Fixed probability bins; export only aggregates, no IDs or predictions.
    for k in range(p.shape[1]):
        bins=np.minimum((10*p[:,k]).astype(int),9)
        for b in range(10):
            mask=bins==b
            if not mask.any():continue
            calibration.append({'outcome':k,'bin':b,'n':int(mask.sum()),
                                'mean_probability':float(np.average(p[mask,k],weights=w[mask])),
                                'observed_fraction':float(np.average(y[mask]==k,weights=w[mask]))})
    return overall,per_country,calibration


def bootstrap_margins(x,X,names,C,draws,seed):
    countries=sorted(x.country.unique());nc=len(countries)
    code=pd.Categorical(x.country,categories=countries).codes
    y=x.y.to_numpy();w=inputs.normalized_weights(x).to_numpy()
    rng=np.random.default_rng(seed)
    multiplicities=np.stack([np.bincount(rng.integers(0,nc,nc),minlength=nc) for _ in range(draws)])
    def one(item):
        index,mult=item
        ww=w*mult[code];keep=ww>0
        # Fix total penalized likelihood weight to original analytic n. Average
        # contrasts over the sampled countries, including repeated countries.
        ww=ww[keep]*w.sum()/ww.sum()
        model=fitted(X[keep],y[keep],ww,C)
        return [{**r,'draw':index} for r in margins(model,X[keep],ww,names)]
    rows=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i,result in enumerate(pool.map(one,enumerate(multiplicities)),1):
            rows.extend(result)
            if i%100==0:print(f'bootstrap {i}/{draws}',flush=True)
    b=pd.DataFrame(rows)
    ci=b.groupby(['variable','outcome']).probability_difference.agg(
        ci_low=lambda z:z.quantile(.025),ci_high=lambda z:z.quantile(.975),
        bootstrap_sd='std',successful_draws='count').reset_index()
    assert ci.successful_draws.eq(draws).all()
    return ci


def self_test():
    rng=np.random.default_rng(671)
    X=rng.normal(size=(800,3));y=rng.binomial(1,expit(X[:,0]-X[:,1]));w=rng.uniform(.5,2,len(y))
    m=fitted(X,y,w);names=['national_economy_bad','government_distrust','economic_priority']
    for row in margins(m,X,w,names):
        low=X.copy();high=X.copy();j=names.index(row['variable'])
        low[:,j]=row['low'];high[:,j]=row['high'];k=row['outcome']
        brute=np.average(m.predict_proba(high)[:,k]-m.predict_proba(low)[:,k],weights=w)
        assert np.isclose(row['probability_difference'],brute)
    logits=np.column_stack([X[:,0],X[:,1],-X[:,0],np.zeros(len(X))])
    probs=softmax(logits,axis=1);y=np.array([rng.choice(4,p=r) for r in probs])
    m=fitted(X,y,w)
    for row in margins(m,X,w,names):
        low=X.copy();high=X.copy();j=names.index(row['variable'])
        low[:,j]=row['low'];high[:,j]=row['high'];k=row['outcome']
        brute=np.average(m.predict_proba(high)[:,k]-m.predict_proba(low)[:,k],weights=w)
        assert np.isclose(row['probability_difference'],brute)
    assert metrics(y,m.predict_proba(X),w)['log_loss']<np.log(4)
    print('Synthetic checks passed: binary/multinomial standardized differences equal direct probability calculations.',flush=True)


def main():
    start=datetime.now(timezone.utc).isoformat()
    config=json.loads((OUT/'eb_input_contract.json').read_text())
    for path,sha in config['fixed_input_hashes'].items():
        assert inputs.digest(ROOT/path)==sha,('Locked input changed',path)
    assert config['contrast_values']=={k:list(v) for k,v in CONTRASTS.items()}
    d,_=inputs.load_data()
    coefficients=[];point_rows=[];cv_rows=[];cv_country=[];calibration=[];sensitivity=[]
    for ti,target in enumerate(TARGETS):
        x=inputs.analytic_sample(d,target).reset_index(drop=True)
        assert len(x)==config['sample_totals'][target]
        print(f'{target}: n={len(x)}, countries={x.country.nunique()}',flush=True)
        w=inputs.normalized_weights(x).to_numpy();y=x.y.to_numpy()
        X,_,names=design(x,x)
        model=fitted(X,y,w,config['main_regularization_C'])
        point=pd.DataFrame(margins(model,X,w,names))
        ci=bootstrap_margins(x,X,names,config['main_regularization_C'],config['bootstrap_country_draws'],config['seed']+ti)
        point=point.merge(ci,on=['variable','outcome'],validate='one_to_one');point['target']=target
        point['n']=len(x);point['countries']=x.country.nunique();point_rows.extend(point.to_dict('records'))
        for k,beta in enumerate(model.coef_):
            for feature,value in zip(names,beta):
                coefficients.append({'target':target,'coefficient_class':int(model.classes_[k] if len(model.classes_)>2 else 1),
                                     'feature':feature,'coefficient':float(value),'intercept':float(model.intercept_[k])})
        # Write completed aggregate estimates before the next potentially long job.
        pd.DataFrame(point_rows).to_csv(OUT/'eb_model_margins.csv',index=False)
        pd.DataFrame(coefficients).to_csv(OUT/'eb_model_coefficients.csv',index=False)
        for mode in ['within_country','leave_country_out']:
            for block in inputs.BLOCKS:
                result,country,cal=cross_validate(x,block,mode,config['seed'])
                header={'target':target,'block':block,'validation':mode,'n':len(x),'countries':x.country.nunique()}
                cv_rows.append({**header,**result})
                cv_country.extend([{**header,**r} for r in country]);calibration.extend([{**header,**r} for r in cal])
            print(f'{target}: {mode} complete',flush=True)
        # Regularization, weighting, coverage, and classification are declared
        # sensitivities; the primary model is never selected from these outputs.
        scenarios=[('C_0.1',x,.1,'equal_country'),('C_10',x,10.,'equal_country'),
                   ('population_weight',x,1.,'population'),('demographic_weight',x,1.,'demographic'),
                   ('unweighted',x,1.,'unweighted')]
        coverage=pd.read_csv(inputs.AUDIT/'ep2009_outcome_coverage.csv')
        good=coverage[coverage.version.eq(4)&coverage.rule.eq('inclusive')]
        good=good.loc[good.joint_classified_vote_n/good.joint_named_option_n>=.9,'country']
        scenarios.append(('coverage_at_least_90pct',x[x.country.isin(good)].copy(),1.,'equal_country'))
        for version,rule in [(3,'inclusive'),(4,'strict'),(3,'strict')]:
            # Same initial countries isolate relabelling rather than dropping
            # countries that cease to have a positive class under a new rule.
            z=inputs.analytic_sample(d,target,version,rule,country_scope=sorted(x.country.unique())).reset_index(drop=True)
            scenarios.append((f'v{version}_{rule}_same_countries',z,1.,'equal_country'))
        for label,z,C,weight_mode in scenarios:
            XX,_,nn=design(z,z);ww=inputs.normalized_weights(z,weight_mode).to_numpy()
            mm=fitted(XX,z.y.to_numpy(),ww,C)
            sensitivity.extend([{'target':target,'scenario':label,'n':len(z),'countries':z.country.nunique(),**r}
                                for r in margins(mm,XX,ww,nn)])
        for name,rows in [('eb_model_validation',cv_rows),('eb_model_validation_by_country',cv_country),
                          ('eb_model_calibration',calibration),('eb_model_sensitivity',sensitivity)]:
            pd.DataFrame(rows).to_csv(OUT/(name+'.csv'),index=False)
    audit={'start_utc':start,'end_utc':datetime.now(timezone.utc).isoformat(),
           'input_lock_commit':'a59f22b','protocol_commit':'bdbd371','contract_sha256':inputs.digest(OUT/'eb_input_contract.json'),
           'model_script_sha256':inputs.digest(Path(__file__).resolve()),'python':platform.python_version(),
           'numpy':np.__version__,'scipy':scipy.__version__,'sklearn':sklearn.__version__,'pandas':pd.__version__,
           'seed':config['seed'],'country_bootstrap_draws':config['bootstrap_country_draws'],
           'convergence_warning_policy':'ConvergenceWarning raises, no failed fits silently removed',
           'microdata_exported':False,'interpretation':'Post-election conditional associations, not causes or pre-election forecasts'}
    (OUT/'eb_models_run.json').write_text(json.dumps(audit,indent=2)+'\n')
    print('All locked EB fits, bootstrap intervals, validation and declared sensitivities completed.',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--self-test',action='store_true');args=parser.parse_args()
    with threadpool_limits(limits=1):
        if args.self_test:self_test()
        else:main()
