"""Within-survey national models under the frozen measurement specification."""
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import importlib.util
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import OneHotEncoder
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'analysis'/file)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
crosswalk=module('national_crosswalk','80_national_party_crosswalk.py')
inputs=crosswalk.inputs;OUT=inputs.OUT
shared=module('national_shared','59_bes_pre_election_models.py');helpers=shared.helpers
CORE=inputs.CORE
BLOCKS={'baseline':[], 'economy_government':CORE[:2], 'plus_priority':CORE[:3],
        'full':CORE, **{'without_'+name:[v for v in CORE if v!=col]
        for name,col in zip(['economy','government','priority','trust'],CORE)}}
PAIRS=[('baseline','economy_government'),('economy_government','plus_priority'),
       ('plus_priority','full'),('baseline','full'),('without_economy','full'),
       ('without_government','full'),('without_priority','full'),('without_trust','full')]
CONTRASTS={v:((0.,1.) if v=='economic_priority' else (.25,.75)) for v in CORE}


def weights(x):
    w=x.weight.to_numpy(float);return w*len(x)/w.sum()


def design(train,test,block='full',intention=True):
    numeric=inputs.NUMERIC+BLOCKS[block]
    cats=[v for v in inputs.CATEGORICAL if intention or v!='early_intention']
    e=OneHotEncoder(handle_unknown='ignore',sparse_output=False,dtype=float)
    X=np.column_stack([train[numeric].to_numpy(float),e.fit_transform(train[cats])])
    Z=np.column_stack([test[numeric].to_numpy(float),e.transform(test[cats])])
    assert np.isfinite(X).all() and np.isfinite(Z).all()
    return X,Z,numeric+e.get_feature_names_out(cats).tolist()


def bootstrap(x,X,names,seed):
    y=x.y.to_numpy();w=weights(x);classes=np.unique(y)
    def one(child):
        rng=np.random.default_rng(child)
        count=np.bincount(rng.integers(0,len(x),len(x)),minlength=len(x))
        ww=w*count;keep=ww>0;ww=ww[keep]*len(x)/ww.sum()
        m=helpers.fitted(X[keep],y[keep],ww)
        assert np.array_equal(m.classes_,classes)
        return helpers.margins(m,X[keep],ww,names,CONTRASTS)
    rows=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i,r in enumerate(pool.map(one,np.random.SeedSequence(seed).spawn(1000)),1):
            rows.extend(r)
            if i%250==0:print(f'National bootstrap {i}/1000',flush=True)
    return pd.DataFrame(rows).groupby(['variable','outcome']).probability_difference.agg(
        ci_low=lambda s:s.quantile(.025),ci_high=lambda s:s.quantile(.975),
        bootstrap_sd='std',successful_draws='count').reset_index()


def validate(x,block):
    classes=np.sort(x.y.unique());codes=pd.Categorical(x.y,categories=classes).codes
    p=np.full((len(x),len(classes)),np.nan)
    for a,b in StratifiedKFold(5,shuffle=True,random_state=20261106).split(np.zeros(len(x)),x.y):
        train,test=x.iloc[a],x.iloc[b];X,Z,_=design(train,test,block)
        m=helpers.fitted(X,train.y.to_numpy(),weights(train))
        assert np.array_equal(m.classes_,classes)
        p[b]=m.predict_proba(Z)
    assert np.isfinite(p).all() and np.allclose(p.sum(axis=1),1)
    loss=-np.log(np.clip(p[np.arange(len(x)),codes],np.finfo(float).eps,1))
    return helpers.metrics(codes,p,weights(x)),loss


def scenarios(key):
    common=['C_0.1','C_10','unweighted','broad_priority','without_early_intention','v3_inclusive','v4_strict']
    return common+{'ES2015':['es_coalitions','pre_economy'],
        'NL2010':['nl_previous_cabinet'],'NL2012':['narrow_priority'],
        'BE2014':['party_trust','WEIGHT1','WEIGHT2','WEIGHT3','WEIGHT4'],
        'DK2007':['exclude_web']}.get(key,[])


def sample_pair(d,target,scenario):
    """Alternative and reference share persons, but may change outcome categories."""
    o={'v3_inclusive':'outcome_v3_inclusive','v4_strict':'outcome_v4_strict',
       'es_coalitions':'outcome_es_coalitions','nl_previous_cabinet':'outcome_nl_previous_cabinet'}.get(scenario,'outcome_v4_inclusive')
    alternative=d.copy()
    if scenario=='broad_priority':alternative['economic_priority']=alternative.economic_priority_broad
    if scenario=='narrow_priority':alternative['economic_priority']=alternative.economic_priority_narrow
    if scenario=='pre_economy':alternative['economy_bad']=alternative.alternative_economy
    if scenario=='party_trust':alternative['elite_distrust']=alternative.alternative_trust
    if scenario.startswith('WEIGHT'):alternative['weight']=alternative[scenario]
    if scenario=='unweighted':alternative['weight']=1.
    if scenario=='exclude_web':alternative['eligible'] &= alternative.source_group.ne(6)
    if scenario=='nl_previous_cabinet':
        mask=alternative.turnout.eq(1)&alternative.party_code.eq(2)
        alternative.loc[mask,'government_vote']=1.
    a=crosswalk.analytic_sample(alternative,target,outcome=o)
    r=crosswalk.analytic_sample(d,target)
    # Changing classification can expand the sample. Compare on common people
    # for controls/weight changes, and report a separate full alternative when
    # classification makes previously unresolved votes usable.
    expansion=scenario=='es_coalitions' and target in ['opposition_type','all_outcomes']
    if expansion:
        # A primary-labelled reference cannot recover excluded coalitions.
        # Fit the alternative on its full sample; no misleading matched claim.
        return r,a,False
    ids=sorted(set(a.person_id)&set(r.person_id))
    return r.set_index('person_id',drop=False).loc[ids],a.set_index('person_id',drop=False).loc[ids],True


def main():
    start=datetime.now(timezone.utc).isoformat()
    lock=json.loads((OUT/'national_input_contract.json').read_text())
    for p,sha in lock['fixed_hashes'].items():assert inputs.digest(ROOT/p)==sha,p
    cw=pd.read_csv(OUT/'national_party_crosswalk.csv')
    counts=pd.read_csv(OUT/'national_locked_counts.csv').set_index(['dataset','target'])
    points=[];validation=[];incremental=[];sensitivity=[];status=[]
    for ki,key in enumerate(inputs.CONFIG):
        d,_,_=inputs.construct(key);d=crosswalk.add_outcomes(d,key,cw)
        for ti,target in enumerate(inputs.TARGETS):
            base=counts.loc[(key,target)]
            if not base.estimable:continue
            x=crosswalk.analytic_sample(d,target).reset_index(drop=True)
            assert len(x)==base.n and x.person_id.is_unique and x.y.value_counts().min()>=20
            print(f'National {key} {target}, n={len(x)}',flush=True)
            X,_,names=design(x,x);w=weights(x)
            m=helpers.fitted(X,x.y.to_numpy(),w)
            p=pd.DataFrame(helpers.margins(m,X,w,names,CONTRASTS))
            p=p.merge(bootstrap(x,X,names,20261106+10*ki+ti),on=['variable','outcome'],validate='one_to_one')
            p['dataset']=key;p['target']=target;p['n']=len(x);points.extend(p.to_dict('records'))
            pd.DataFrame(points).to_csv(OUT/'national_model_margins.csv',index=False)
            losses={};cache={}
            for block,cols in BLOCKS.items():
                signature=tuple(cols)
                if signature not in cache:cache[signature]=validate(x,block)
                metrics,loss=cache[signature];losses[block]=loss
                validation.append(dict(dataset=key,target=target,block=block,n=len(x),**metrics))
            for a,b in PAIRS:
                incremental.append(dict(dataset=key,target=target,baseline_block=a,expanded_block=b,
                    **shared.paired_loss_comparison(losses[a],losses[b],w,x.person_id.to_numpy(),20261106)))
            for scenario in scenarios(key):
                ref,alt,matched=sample_pair(d,target,scenario)
                valid=len(alt)>0 and alt.y.nunique()>=2 and alt.y.value_counts().min()>=20
                if target=='opposition_type':valid=valid and set(alt.y)=={0,1}
                # Strict Iceland no longer has a populist category. Its joint
                # three-outcome model is still estimable and is labelled so.
                status.append(dict(dataset=key,target=target,scenario=scenario,reference_n=len(ref),
                    alternative_n=len(alt),same_people=matched,reference_classes=json.dumps(sorted(ref.y.unique().tolist())),
                    alternative_classes=json.dumps(sorted(alt.y.unique().tolist())),estimable=bool(valid)))
                if not valid:continue
                for name,q in [('reference',ref),('alternative',alt)]:
                    X,_,names=design(q,q,intention=not(name=='alternative' and scenario=='without_early_intention'))
                    C=.1 if name=='alternative' and scenario=='C_0.1' else 10. if name=='alternative' and scenario=='C_10' else 1.
                    mm=helpers.fitted(X,q.y.to_numpy(),weights(q),C)
                    sensitivity.extend([dict(dataset=key,target=target,scenario=scenario,fit=name,n=len(q),
                        same_people=matched,**r) for r in helpers.margins(mm,X,weights(q),names,CONTRASTS)])
            for file,rows in [('national_model_validation',validation),('national_incremental_validation',incremental),
                               ('national_sensitivity',sensitivity),('national_sensitivity_status',status)]:
                pd.DataFrame(rows).to_csv(OUT/(file+'.csv'),index=False)
            print(f'National {key} {target}: complete',flush=True)
    report=dict(start_utc=start,end_utc=datetime.now(timezone.utc).isoformat(),
        hashes={str(p.relative_to(ROOT)):inputs.digest(p) for p in [Path(__file__),OUT/'national_input_contract.json',
                ROOT/'analysis/51_eurobarometer_models.py',ROOT/'analysis/59_bes_pre_election_models.py']},
        full_models=int(counts.estimable.sum()),margin_bootstrap_draws=1000,validation_loss_draws=2000,
        refitted_folds_for_validation_intervals=False,resampling_unit='individual within survey, not reconstructed survey PSU',
        pooled_cross_country_coefficients=False,microdata_exported=False)
    (OUT/'national_models_run.json').write_text(json.dumps(report,indent=2)+'\n')
    print('National comparisons completed.',flush=True)


if __name__=='__main__':
    with threadpool_limits(limits=1):main()
