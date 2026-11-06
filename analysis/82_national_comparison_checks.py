"""Verify national output completeness, class identities and probability accounting."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/processed/three_explanations'


def main():
    lock=json.loads((OUT/'national_input_contract.json').read_text())
    run=json.loads((OUT/'national_models_run.json').read_text())
    for mapping in [lock['fixed_hashes'],run['hashes']]:
        for path,sha in mapping.items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha,path
    counts=pd.read_csv(OUT/'national_locked_counts.csv')
    m=pd.read_csv(OUT/'national_model_margins.csv')
    v=pd.read_csv(OUT/'national_model_validation.csv')
    inc=pd.read_csv(OUT/'national_incremental_validation.csv')
    s=pd.read_csv(OUT/'national_sensitivity.csv')
    status=pd.read_csv(OUT/'national_sensitivity_status.csv')
    assert run['full_models']==30 and counts.estimable.sum()==30
    assert [len(a) for a in [m,v,inc]]==[296,240,240]
    assert m.successful_draws.eq(1000).all() and inc.bootstrap_draws.eq(2000).all()
    assert m.ci_low.le(m.ci_high).all() and inc.ci_low.le(inc.ci_high).all()
    expected=set(map(tuple,counts.loc[counts.estimable,['dataset','target']].to_numpy()))
    assert set(m.groupby(['dataset','target']).groups)==expected
    for row in counts[counts.estimable].itertuples():
        a=m[m.dataset.eq(row.dataset)&m.target.eq(row.target)]
        assert a.n.eq(row.n).all()
        assert set(a.outcome)==set(map(int,json.loads(row.class_counts)))
    for d,keys in [(m,['dataset','target','variable']),
                   (s,['dataset','target','scenario','fit','variable'])]:
        assert not d.duplicated(keys+['outcome']).any()
        assert np.isfinite(d.probability_difference).all()
        assert np.allclose(d.groupby(keys).probability_difference.sum(),0)
        for col in ['probability_at_low','probability_at_high']:
            assert d[col].between(0,1).all() and np.allclose(d.groupby(keys)[col].sum(),1)
        assert np.allclose(d.probability_difference,d.probability_at_high-d.probability_at_low)
    for row in inc.itertuples():
        a=v[v.dataset.eq(row.dataset)&v.target.eq(row.target)].set_index('block')
        delta=a.loc[row.baseline_block,'log_loss']-a.loc[row.expanded_block,'log_loss']
        assert np.isclose(delta,row.log_loss_reduction)
        assert np.isclose(100*delta/a.loc[row.baseline_block,'log_loss'],row.relative_improvement_percent)
        assert row.passes_1pct_and_positive_interval==(row.relative_improvement_percent>=1 and row.ci_low>0)
    # Reference fits with unchanged full samples must reproduce primary points.
    pair=s[s.fit.eq('reference')].merge(m,on=['dataset','target','variable','outcome'],suffixes=('_ref','_main'),validate='many_to_one')
    same=pair.n_ref.eq(pair.n_main)
    max_delta=float((pair.loc[same,'probability_difference_ref']-pair.loc[same,'probability_difference_main']).abs().max())
    assert max_delta<1e-5,max_delta
    for row in status.itertuples():
        a=s[s.dataset.eq(row.dataset)&s.target.eq(row.target)&s.scenario.eq(row.scenario)]
        if not row.estimable:
            assert a.empty
            continue
        assert set(a.fit)=={'reference','alternative'}
        for fit,n,classes in [('reference',row.reference_n,row.reference_classes),
                              ('alternative',row.alternative_n,row.alternative_classes)]:
            q=a[a.fit.eq(fit)]
            assert q.n.eq(n).all() and set(q.outcome)==set(json.loads(classes))
        if row.same_people:assert row.reference_n==row.alternative_n
    assert not (m.dataset.str.startswith('PT')&m.target.eq('opposition_type')).any()
    assert not (m.dataset.str.startswith('PT')&m.target.eq('all_outcomes')&m.outcome.eq(2)).any()
    strict_is=status[status.dataset.eq('IS2013')&status.target.eq('opposition_type')&status.scenario.eq('v4_strict')]
    assert len(strict_is)==1 and not strict_is.estimable.iloc[0]
    # Country coverage and exclusions sum to the complete-measurement population.
    c=pd.read_csv(OUT/'national_outcome_coverage.csv')
    for _,a in c.groupby(['dataset','version','rule']):
        assert a.n.sum()==a.core_n.iloc[0] and np.isclose(a.weight_share.sum(),1)
    report=dict(input_hashes_match=True,national_surveys=8,additional_countries=6,
        full_models=30,margin_rows=len(m),margin_bootstrap_draws=1000,validation_comparisons=len(inc),
        sensitivity_specifications=len(status),sensitivity_estimable=int(status.estimable.sum()),
        sensitivity_margin_rows=len(s),reference_max_difference_probability=max_delta,
        probability_checks_passed=True,absent_populist_classes_not_fabricated=True,
        raw_records_read=False,individual_bootstrap_not_full_survey_design=True)
    (OUT/'national_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
