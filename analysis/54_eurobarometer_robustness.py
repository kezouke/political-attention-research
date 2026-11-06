"""Declared EB robustness checks after the locked first linear estimates.

Read only locally authorized data. Export aggregate comparisons, never rows.
Specific nonlinear settings are fixed here, without outcome-driven tuning.
"""
from pathlib import Path
import importlib.util
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pyreadstat
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import OneHotEncoder
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('model',ROOT/'analysis/51_eurobarometer_models.py')
model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)
inputs=model.inputs;OUT=inputs.OUT
PARAMETERS={'learning_rate':.05,'max_iter':200,'max_leaf_nodes':15,'min_samples_leaf':40,
            'l2_regularization':1.,'early_stopping':False,'random_state':20261106}


def fit_result(x,extra=(),drop=(),contrasts=None):
    numeric=[v for v in inputs.CONTROLS+inputs.BLOCKS['full'] if v not in drop]+list(extra)
    encoder=OneHotEncoder(handle_unknown='ignore',sparse_output=False,dtype=float)
    X=np.column_stack([x[numeric].to_numpy(float),encoder.fit_transform(x[inputs.CATEGORICAL])])
    names=numeric+encoder.get_feature_names_out(inputs.CATEGORICAL).tolist()
    w=inputs.normalized_weights(x).to_numpy()
    assert np.isfinite(X).all()
    m=model.fitted(X,x.y.to_numpy(),w)
    return model.margins(m,X,w,names,contrasts or model.CONTRASTS)


def nonlinear_cv(x,block,mode):
    p=np.full((len(x),x.y.nunique()),np.nan)
    if mode=='within_country':
        strata=x.country.astype(str)+'_'+x.y.astype(str)
        splits=StratifiedKFold(5,shuffle=True,random_state=20261106).split(np.zeros(len(x)),strata)
    else:
        splits=((np.flatnonzero(x.country.ne(c).to_numpy()),np.flatnonzero(x.country.eq(c).to_numpy()))
                for c in sorted(x.country.unique()))
    for a,b in splits:
        train,test=x.iloc[a],x.iloc[b]
        X,Z,_=model.design(train,test,block)
        m=HistGradientBoostingClassifier(**PARAMETERS)
        m.fit(X,train.y.to_numpy(),sample_weight=inputs.normalized_weights(train).to_numpy())
        assert np.array_equal(m.classes_,np.arange(p.shape[1]))
        p[b]=m.predict_proba(Z)
    assert np.isfinite(p).all() and np.allclose(p.sum(axis=1),1)
    w=inputs.normalized_weights(x).to_numpy();y=x.y.to_numpy()
    country=[]
    for c in sorted(x.country.unique()):
        mask=x.country.eq(c).to_numpy()
        country.append({'country':c,**model.metrics(y[mask],p[mask],w[mask])})
    return model.metrics(y,p,w),country


def main():
    started=datetime.now(timezone.utc).isoformat()
    config=json.loads((OUT/'eb_input_contract.json').read_text())
    for p,sha in config['fixed_input_hashes'].items():assert inputs.digest(ROOT/p)==sha
    run=json.loads((OUT/'eb_models_run.json').read_text())
    assert inputs.digest(ROOT/'analysis/51_eurobarometer_models.py')==run['model_script_sha256']
    d,_=inputs.load_data()
    # Turnout needs no party classification. Verify original row order by sample
    # and age before expanding this sensitivity to unidentified party responses.
    raw,_=pyreadstat.read_sav(inputs.eb.verified_download('ZA4973_v3-0-0.sav'),
                             usecols=['v6','v541','v666'],user_missing=True)
    assert raw.loc[d.index,'v6'].eq(d['sample']).all()
    assert np.allclose((raw.loc[d.index,'v666']-50)/20,d.age_scaled)
    d['reported_voted']=raw.loc[d.index,'v541'].eq(1)
    assert not (d.reported_voted&d.reported_nonvote).any()
    omitted=[];single=[];alternatives=[];bounds=[];turnout=[];nonlinear=[];nonlinear_country=[]
    for target in model.TARGETS:
        x=inputs.analytic_sample(d,target).reset_index(drop=True)
        for c in sorted(x.country.unique()):
            z=x[x.country.ne(c)]
            omitted.extend([{'target':target,'omitted_country':c,'n':len(z),**r} for r in fit_result(z)])
            z=x[x.country.eq(c)]
            if z.y.nunique()==x.y.nunique():
                single.extend([{'target':target,'country':c,'n':len(z),
                                'smallest_outcome_n':int(z.y.value_counts().min()),
                                'scope':'Exploratory regularized country estimate; no claim of significant heterogeneity',**r}
                               for r in fit_result(z)])
        print(target+': country influence checked',flush=True)
        variants=[
            ('priority_including_tax','economic_priority','economic_priority_tax',(),()),
            ('personal_priority','economic_priority','economic_priority_personal',(),()),
            ('priority_economy_only','economic_priority','priority_economy',(),()),
            ('priority_unemployment_only','economic_priority','priority_unemployment',(),()),
            ('priority_prices_only','economic_priority','priority_prices',(),()),
            ('parliament_instead_of_party_trust','party_distrust','parliament_distrust',(),()),
            ('add_household_finances',None,None,('household_finances_bad',),()),
            ('add_bill_difficulty',None,None,('bill_difficulty',),()),
            ('add_eu_attitude',None,None,('eu_distrust','eu_image_negative'),()),
            ('add_household_and_eu',None,None,('household_finances_bad','bill_difficulty','eu_distrust','eu_image_negative'),()),
            ('without_left_right',None,None,(),('left_right','left_right_squared','left_right_missing')),
            ('without_government_trust',None,None,(),('government_distrust',)),
        ]
        for label,dest,source,extra,drop in variants:
            required=list(extra)+([source] if source else [])
            eligible=x[required].notna().all(axis=1) if required else pd.Series(True,index=x.index)
            reference=x.loc[eligible].copy();z=reference.copy()
            if dest:z[dest]=z[source]
            for kind,xx,ex,dr in [('reference_same_subset',reference,(),()),('alternative',z,extra,drop)]:
                rows=fit_result(xx,extra=ex,drop=dr)
                alternatives.extend([{'target':target,'scenario':label,'fit':kind,'n':len(xx),
                                     'replacement_source':source or '',**r} for r in rows])
        print(target+': measurement alternatives checked',flush=True)
        for mode in ['within_country']+(['leave_country_out'] if target=='opposition_type' else []):
            for block in ['baseline','plus_priority','full']:
                result,per=nonlinear_cv(x,block,mode)
                base={'target':target,'validation':mode,'block':block,'n':len(x),'learner':'fixed_HistGradientBoosting'}
                nonlinear.append({**base,**result});nonlinear_country.extend([{**base,**r} for r in per])
                print(f'{target}: {mode}, nonlinear {block} complete',flush=True)
        # Save completed aggregates at each target; no prediction records.
        for name,rows in [('eb_leave_one_country_margins',omitted),('eb_country_margins',single),
                          ('eb_measurement_sensitivity',alternatives),('eb_nonlinear_validation',nonlinear),
                          ('eb_nonlinear_validation_by_country',nonlinear_country)]:
            pd.DataFrame(rows).to_csv(OUT/(name+'.csv'),index=False)
    # Bounds refer to reported voters with complete core attitudes, not all
    # eligible citizens. Unresolved votes can all enter or all leave a category.
    for c,g in d[d.core_complete&d.reported_voted].groupby('country'):
        w=g.weight_country;unknown=g.outcome_v4_inclusive.eq('unresolved')
        for cat in ['government','other_opposition','populist_opposition']:
            known=g.outcome_v4_inclusive.eq(cat)
            bounds.append({'country':c,'category':cat,'reported_voters_n':len(g),
                           'unresolved_voters_n':int(unknown.sum()),
                           'lower_share':float(w[known].sum()/w.sum()),
                           'upper_share':float(w[known|unknown].sum()/w.sum()),
                           'interpretation':'Worst-case arithmetic bounds, not classification estimates or causal-effect intervals'})
    # Unknown parties can affect a classification-conditioned turnout analysis.
    # Repeat with every explicit turnout response, including no named party.
    for scope,countries in [('original_25',config['primary_government_countries']),('all_27',sorted(d.country.unique()))]:
        z=d[d.core_complete&d.country.isin(countries)&(d.reported_voted|d.reported_nonvote)].copy()
        z['y']=z.reported_nonvote.astype(int)
        turnout.extend([{'scope':scope,'n':len(z),'countries':z.country.nunique(),**r} for r in fit_result(z)])
    pd.DataFrame(bounds).to_csv(OUT/'eb_unknown_party_bounds.csv',index=False)
    pd.DataFrame(turnout).to_csv(OUT/'eb_turnout_all_reported.csv',index=False)
    # Audit paired validation differences with country sampling, conditional on
    # fitted held-out predictions. Positive means a lower log loss with new model.
    linear=pd.read_csv(OUT/'eb_model_validation_by_country.csv')
    hgb=pd.DataFrame(nonlinear_country);comparisons=[];rng=np.random.default_rng(20261106)
    for (target,mode),g in hgb.groupby(['target','validation']):
        def series(frame,block):return frame[frame.block.eq(block)].set_index('country').log_loss.sort_index()
        lin=linear[linear.target.eq(target)&linear.validation.eq(mode)]
        pairs=[('hgb_full_vs_hgb_baseline',series(g,'baseline'),series(g,'full')),
               ('hgb_full_vs_hgb_plus_priority',series(g,'plus_priority'),series(g,'full')),
               ('hgb_full_vs_linear_full',series(lin,'full'),series(g,'full'))]
        for label,a,b in pairs:
            assert a.index.equals(b.index)
            nc=len(a);draw=rng.integers(0,nc,size=(10000,nc))
            av=a.to_numpy();bv=b.to_numpy();delta=av-bv
            boot=delta[draw].mean(axis=1);rel=100*boot/av[draw].mean(axis=1)
            comparisons.append({'target':target,'validation':mode,'comparison':label,
                                'relative_improvement_percent':float(100*delta.mean()/av.mean()),
                                'ci_low_percent':float(np.quantile(rel,.025)),
                                'ci_high_percent':float(np.quantile(rel,.975)),
                                'passes_1pct_and_positive_interval':bool(100*delta.mean()/av.mean()>=1 and np.quantile(rel,.025)>0)})
    pd.DataFrame(comparisons).to_csv(OUT/'eb_nonlinear_comparisons.csv',index=False)
    summary={'start_utc':started,'end_utc':datetime.now(timezone.utc).isoformat(),
             'script_sha256':inputs.digest(Path(__file__).resolve()),'nonlinear_parameters':PARAMETERS,
             'scope':'Specific secondary specifications fixed after first linear results, before their own fitting',
             'country_influence_fits':len(pd.DataFrame(omitted)[['target','omitted_country']].drop_duplicates()),
             'per_country_estimates':'Exploratory, regularized, often small samples; not a significance vote count',
             'nonlinear_hyperparameter_search':False,'model_selection_on_test_set':False,
             'unknown_party_bounds':'Conditional on reported voters with complete core attitudes; no MNAR or causal-effect claim',
             'microdata_exported':False}
    (OUT/'eb_robustness_run.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2));print(pd.DataFrame(comparisons).round(3).to_string(index=False))

if __name__=='__main__':
    with threadpool_limits(limits=1):main()
