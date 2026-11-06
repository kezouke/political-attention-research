"""Aggregate validation of the first locked EB model run.

No respondent records are read. Country bootstrap of held-out losses is
conditional on fitted CV predictions; it does not refit model training folds.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/processed/three_explanations'


def main():
    run=json.loads((OUT/'eb_models_run.json').read_text())
    for path,key in [(ROOT/'analysis/51_eurobarometer_models.py','model_script_sha256'),
                     (OUT/'eb_input_contract.json','contract_sha256')]:
        assert hashlib.sha256(path.read_bytes()).hexdigest()==run[key]
    config=json.loads((OUT/'eb_input_contract.json').read_text())
    for p,sha in config['fixed_input_hashes'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha
    point=pd.read_csv(OUT/'eb_model_margins.csv')
    assert point.successful_draws.eq(1000).all()
    assert point[['probability_at_low','probability_at_high']].ge(0).all().all()
    assert point[['probability_at_low','probability_at_high']].le(1).all().all()
    assert point.groupby(['target','variable']).probability_difference.sum().abs().lt(1e-9).all()
    assert point.groupby(['target','variable']).probability_at_low.sum().sub(1).abs().lt(1e-9).all()
    assert point.groupby(['target','variable']).probability_at_high.sum().sub(1).abs().lt(1e-9).all()
    overall=pd.read_csv(OUT/'eb_model_validation.csv')
    country=pd.read_csv(OUT/'eb_model_validation_by_country.csv')
    keys=['target','block','validation']
    means=country.groupby(keys)[['log_loss','brier_sum_over_classes']].mean().reset_index()
    joined=overall.merge(means,on=keys,suffixes=('_all','_countries'),validate='one_to_one')
    for metric in ['log_loss','brier_sum_over_classes']:
        assert np.allclose(joined[metric+'_all'],joined[metric+'_countries'])
    expected=4*8*2
    assert len(overall)==expected and not overall.duplicated(keys).any()
    comparisons=[('baseline','economy_government'),('economy_government','plus_priority'),
                 ('plus_priority','full'),('baseline','full'),('without_economy','full'),
                 ('without_government','full'),('without_priority','full'),('without_party_trust','full')]
    rows=[];rng=np.random.default_rng(20261106)
    for (target,mode),g in country.groupby(['target','validation']):
        for old,new in comparisons:
            a=g[g.block.eq(old)].set_index('country').log_loss.sort_index()
            b=g[g.block.eq(new)].set_index('country').log_loss.reindex(a.index)
            assert a.notna().all() and b.notna().all()
            delta=a.to_numpy()-b.to_numpy() # positive = improvement
            nc=len(delta);draw=rng.integers(0,nc,size=(10000,nc))
            boot=delta[draw].mean(axis=1);relative=100*boot/a.to_numpy()[draw].mean(axis=1)
            rows.append({'target':target,'validation':mode,'baseline_block':old,'expanded_block':new,
                         'countries':nc,'log_loss_reduction':float(delta.mean()),
                         'ci_low':float(np.quantile(boot,.025)),'ci_high':float(np.quantile(boot,.975)),
                         'relative_improvement_percent':float(100*delta.mean()/a.mean()),
                         'relative_ci_low':float(np.quantile(relative,.025)),
                         'relative_ci_high':float(np.quantile(relative,.975)),
                         'passes_1pct_and_positive_interval':bool(100*delta.mean()/a.mean()>=1 and np.quantile(boot,.025)>0),
                         'uncertainty_scope':'Country resampling of fixed held-out losses; training folds not refitted'})
    improvements=pd.DataFrame(rows);improvements.to_csv(OUT/'eb_model_incremental_validation.csv',index=False)
    report={'locked_inputs_match':True,'target_validation_block_combinations':expected,
            'bootstrap_marginal_draws_per_estimate':1000,'probability_and_country_weight_invariants_passed':True,
            'validation_loss_bootstrap_draws':10000,'validation_interval_refits_training':False,
            'remaining_checks':['Leave-one-country-out marginal stability, rather than held-out loss alone.',
                                'Detailed missing/unknown-party bounds and additional measurement alternatives.',
                                'Within-country heterogeneous slopes and nonlinear model benchmark.',
                                'Pre-election panels and national-election comparisons; EB cannot establish change before a vote.']}
    (OUT/'eb_result_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    print(improvements[(improvements.validation=='within_country')&
                        improvements.baseline_block.isin(['baseline','plus_priority'])]
          [['target','baseline_block','expanded_block','relative_improvement_percent','relative_ci_low','relative_ci_high',
            'passes_1pct_and_positive_interval']].round(3).to_string(index=False))

if __name__=='__main__':main()
