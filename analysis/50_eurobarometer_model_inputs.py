"""Freeze EB-2009 measurement rules and samples before association models.

Respondent records exist only in local memory. Exports contain definitions,
source hashes, and aggregate availability checks. This module does not estimate
attitude/vote associations and is imported by the subsequent model runner.
"""
from pathlib import Path
import hashlib
import importlib.util
import json

import numpy as np
import pandas as pd
import pyreadstat

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'data/processed/audit_20261106'
OUT=ROOT/'data/processed/three_explanations'
OUT.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('eb_audit',ROOT/'analysis/45_eurobarometer_audit.py')
eb=importlib.util.module_from_spec(spec);spec.loader.exec_module(eb)

VARIABLES={
 'national_economy_bad':{'source':'v105','rule':'(x-1)/3 for x=1..4; higher is worse; current national conditions'},
 'household_finances_bad':{'source':'v109','rule':'(x-1)/3 for x=1..4; current household finances'},
 'economic_priority':{'source':'v134 v135 v137','rule':'any mentioned among economy, rising prices, unemployment; strict national priority routing'},
 'economic_priority_tax':{'source':'v134 v135 v136 v137','rule':'same plus taxation'},
 'economic_priority_personal':{'source':'v152 v153 v155','rule':'same three topics for personal priorities; strict personal routing'},
 'party_distrust':{'source':'v216','rule':'0=tend to trust (1), 1=tend not to trust (2); DK missing'},
 'government_distrust':{'source':'v217','rule':'0=tend to trust (1), 1=tend not to trust (2); not government-performance rating'},
 'parliament_distrust':{'source':'v218','rule':'0=tend to trust (1), 1=tend not to trust (2)'},
 'eu_distrust':{'source':'v219','rule':'0=tend to trust (1), 1=tend not to trust (2)'},
 'eu_image_negative':{'source':'v221','rule':'(x-1)/4 for 1..5; higher is more negative'},
 'age_scaled':{'source':'v666','rule':'(age-50)/20, uniform adult restriction 18..98; not verified voting eligibility'},
 'female':{'source':'v665','rule':'1=female (2), 0=male (1); source has only two gender categories'},
 'education':{'source':'v664','rule':'1..2=finished by 15; 3..6=16..19; 7..9=20+; 10=student; 11=no full-time education; other=missing'},
 'occupation':{'source':'v795','rule':'retain producer categories 1..8, otherwise missing'},
 'community':{'source':'v671','rule':'1=rural, 2=small/middle town, 3=large town, otherwise missing'},
 'left_right':{'source':'v659','rule':'(x-5.5)/4.5 for 1..10; missing set to fixed midpoint 0 plus explicit missing indicator; also squared term'},
 'bill_difficulty':{'source':'v696','rule':'(3-x)/2 for x=1..3; higher is greater difficulty paying bills last year'},
 'weight_country':{'source':'v54','rule':'W31 demographic voting-age poststratification; normalize within analytic country before country-equal weighting'},
 'weight_population':{'source':'v65','rule':'W52 additionally accounts for EU country population; sensitivity only'},
}
CONTROLS=['age_scaled','age_squared','female','female_missing','left_right','left_right_squared','left_right_missing']
CATEGORICAL=['education','occupation','community','country']
BLOCKS={
 'baseline':[],
 'economy_government':['national_economy_bad','government_distrust'],
 'plus_priority':['national_economy_bad','government_distrust','economic_priority'],
 'full':['national_economy_bad','government_distrust','economic_priority','party_distrust'],
 'without_economy':['government_distrust','economic_priority','party_distrust'],
 'without_government':['national_economy_bad','economic_priority','party_distrust'],
 'without_priority':['national_economy_bad','government_distrust','party_distrust'],
 'without_party_trust':['national_economy_bad','government_distrust','economic_priority'],
}


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def load_data():
    cross=pd.read_csv(AUDIT/'ep2009_vote_crosswalk.csv')
    cols=['v6','v37','v54','v65','v105','v109','v216','v217','v218','v219','v221',
          'v541','v659','v664','v665','v666','v671','v696','v795','v796']
    cols += [f'v{i}' for i in range(133,169)] + [f'v{x[1]}' for x in eb.SAMPLES.values()]
    raw,meta=pyreadstat.read_sav(eb.verified_download('ZA4973_v3-0-0.sav'),usecols=sorted(set(cols)),user_missing=True)
    national,_,_=eb.priority_mask(raw,133);personal,_,_=eb.priority_mask(raw,151)
    adult=raw.v37.eq(1)&raw.v666.between(18,98)
    d=pd.DataFrame(index=raw.index)
    d['country']=raw.v6.map({s:c for s,(c,_) in eb.SAMPLES.items()})
    d['sample']=raw.v6
    d['adult']=adult
    d['priority_valid']=national
    d['priority_personal_valid']=personal
    d['weight_country']=raw.v54
    d['weight_population']=raw.v65
    d['national_economy_bad']=(raw.v105.where(raw.v105.isin([1,2,3,4]))-1)/3
    d['household_finances_bad']=(raw.v109.where(raw.v109.isin([1,2,3,4]))-1)/3
    for name,var in [('party_distrust','v216'),('government_distrust','v217'),
                     ('parliament_distrust','v218'),('eu_distrust','v219')]:
        d[name]=raw[var].where(raw[var].isin([1,2]))-1
    d['eu_image_negative']=(raw.v221.where(raw.v221.between(1,5))-1)/4
    d['economic_priority']=raw[['v134','v135','v137']].eq(1).any(axis=1).astype(float).where(national)
    d['economic_priority_tax']=raw[['v134','v135','v136','v137']].eq(1).any(axis=1).astype(float).where(national)
    d['economic_priority_personal']=raw[['v152','v153','v155']].eq(1).any(axis=1).astype(float).where(personal)
    for name,v in [('economy','v134'),('prices','v135'),('unemployment','v137'),('immigration','v141')]:
        d['priority_'+name]=raw[v].where(national)
    d['priority_environment']=raw.v145.where(raw.v796.eq(1),raw.v146).where(national)
    d['questionnaire_split']=raw.v796
    d['age_scaled']=(raw.v666-50)/20
    d['age_squared']=d.age_scaled**2
    gender=raw.v665.where(raw.v665.isin([1,2]))
    d['female']=(gender-1).fillna(0)
    d['female_missing']=gender.isna().astype(float)
    d['education']=raw.v664.map({1:'by15',2:'by15',3:'16to19',4:'16to19',5:'16to19',6:'16to19',
                                7:'20plus',8:'20plus',9:'20plus',10:'student',11:'no_full_time'}).fillna('missing')
    d['occupation']=raw.v795.where(raw.v795.isin(range(1,9)),0).astype(int).astype(str)
    d['community']=raw.v671.where(raw.v671.isin([1,2,3]),0).astype(int).astype(str)
    lr=raw.v659.where(raw.v659.between(1,10))
    d['left_right']=((lr-5.5)/4.5).fillna(0)
    d['left_right_squared']=d.left_right**2
    d['left_right_missing']=lr.isna().astype(float)
    d['bill_difficulty']=(3-raw.v696.where(raw.v696.isin([1,2,3])))/2
    d['named_response']=False
    d['government_known']=np.nan
    for version in [3,4]:
        for rule in ['inclusive','strict']:
            col=f'outcome_v{version}_{rule}'
            d[col]='unresolved'
            for r in cross.itertuples(index=False):
                select=raw.v6.eq(r.sample)&raw.v541.eq(1)&raw[r.variable].eq(r.code)
                d.loc[select,col]=getattr(r,col)
                d.loc[select,'government_known']=r.government
                d.loc[select,'named_response']=True
            d.loc[raw.v541.eq(2),col]='nonvote'
    d['reported_nonvote']=raw.v541.eq(2)
    d['core_complete']=d[['national_economy_bad','economic_priority','government_distrust','party_distrust']].notna().all(axis=1)
    d=d.loc[adult].copy()
    assert len(d)==26087 and d.weight_country.gt(0).all()
    assert int((d.core_complete&d.named_response).sum())==11798
    # Release with no original respondent IDs, text, or individual responses.
    # The returned object stays in local process memory, never a repository file.
    return d,meta


def country_sets(cross,version=4,rule='inclusive'):
    col=f'outcome_v{version}_{rule}'
    available=cross.groupby('country')[col].agg(set)
    government=[c for c,s in available.items() if 'government' in s and ('other_opposition' in s or 'populist_opposition' in s)]
    three=[c for c,s in available.items() if {'government','other_opposition','populist_opposition'}.issubset(s)]
    assert 'CZ' not in government and 'HU' not in government
    return government,three


def analytic_sample(d,target,version=4,rule='inclusive',country_scope=None):
    cross=pd.read_csv(AUDIT/'ep2009_vote_crosswalk.csv')
    gov,three=country_sets(cross,version,rule)
    col=f'outcome_v{version}_{rule}'
    countries=country_scope if country_scope is not None else (three if target in ['opposition_type','four_outcomes'] else gov)
    keep=d.core_complete&d.country.isin(countries)
    if target=='government_vs_opposition':
        # Broader known-government mask is an additional sensitivity, not a
        # silently different comparison sample for the main four-category map.
        keep &= d[col].isin(['government','other_opposition','populist_opposition'])
        y=d[col].eq('government').astype(int)
    elif target=='opposition_type':
        keep &= d[col].isin(['other_opposition','populist_opposition'])
        y=d[col].eq('populist_opposition').astype(int)
    elif target=='nonvote_vs_vote':
        keep &= d[col].ne('unresolved')
        y=d[col].eq('nonvote').astype(int)
    elif target=='four_outcomes':
        keep &= d[col].ne('unresolved')
        y=d[col].map({'government':0,'other_opposition':1,'populist_opposition':2,'nonvote':3})
    else:raise ValueError(target)
    x=d.loc[keep].copy();x['y']=y.loc[keep].astype(int)
    assert x[CONTROLS].notna().all().all()
    return x


def normalized_weights(d,mode='equal_country'):
    if mode=='equal_country':
        w=d.weight_country/d.groupby('country').weight_country.transform('sum')
    elif mode=='population':w=d.weight_population.copy()
    elif mode=='demographic':w=d.weight_country.copy()
    elif mode=='unweighted':w=pd.Series(1.,index=d.index)
    else:raise ValueError(mode)
    return w*len(w)/w.sum()


def main():
    d,meta=load_data()
    cross=pd.read_csv(AUDIT/'ep2009_vote_crosswalk.csv')
    summary=[];checks=[];marginals=[]
    for target in ['government_vs_opposition','opposition_type','nonvote_vs_vote','four_outcomes']:
        x=analytic_sample(d,target)
        for country,g in x.groupby('country'):
            w=normalized_weights(g)
            summary.append({'target':target,'country':country,'n':len(g),
                            'weight_dispersion_kish_n':float(w.sum()**2/w.pow(2).sum()),
                            'left_right_missing_n':int(g.left_right_missing.sum()),
                            'education_missing_n':int(g.education.eq('missing').sum()),
                            'bill_difficulty_valid_n':int(g.bill_difficulty.notna().sum()),
                            'household_finances_valid_n':int(g.household_finances_bad.notna().sum()),
                            'eu_trust_valid_n':int(g.eu_distrust.notna().sum())})
            for outcome,gg in g.groupby('y'):
                marginals.append({'target':target,'country':country,'outcome':int(outcome),'n':len(gg)})
            for v in ['national_economy_bad','economic_priority','government_distrust','party_distrust']:
                checks.append({'target':target,'country':country,'variable':v,'distinct_values':g[v].nunique(),
                               'weighted_mean':float(np.average(g[v],weights=w)),
                               'weighted_variance':float(np.average((g[v]-np.average(g[v],weights=w))**2,weights=w))})
    # Predictor overlap only; never cross trust profiles with outcome here.
    overlap=(d[d.core_complete].groupby(['country','government_distrust','party_distrust']).size()
             .rename('n').reset_index())
    sources={str(p.relative_to(ROOT)):digest(p) for p in [
        AUDIT/'ep2009_vote_crosswalk.csv',AUDIT/'ep2009_parlgov_cabinets.csv',
        ROOT/'planning/analysis-protocol-v1.md',Path(__file__).resolve()]}
    config={'protocol_commit':'bdbd371','raw_source':'ZA4973_v3-0-0.sav; authenticated_downloads.json',
            'fixed_input_hashes':sources,'primary_version':4,'primary_rule':'inclusive',
            'controls_numeric':CONTROLS,'controls_categorical':CATEGORICAL,'blocks':BLOCKS,
            'variables':VARIABLES,'primary_government_countries':country_sets(cross)[0],
            'primary_three_choice_countries':country_sets(cross)[1],
            'sample_totals':pd.DataFrame(summary).groupby('target').n.sum().to_dict(),
            'core_question_names':'Current national economy, national priority, government trust, party trust',
            'country_exclusions':'CZ/HU caretaker status unresolved; choice-type contrasts require verified alternatives',
            'unresolved_policy':'Retain as unresolved in coverage tables; exclude from classified outcome models; no imputed party',
            'main_regularization_C':1.0,'regularization_sensitivity_C':[0.1,10.0],
            'seed':20261106,'folds':5,'bootstrap_country_draws':1000,
            'bootstrap_weight_rule':'Resample countries, retain within-country weights; standardize contrasts over resampled country distribution',
            'contrast_values':{'national_economy_bad':[1/3,2/3],'government_distrust':[0,1],
                               'economic_priority':[0,1],'party_distrust':[0,1]},
            'limitations':['No pre-election party attachment or earlier vote in selected EB data; ideology is measured post-election.',
                           'Known party participants verify availability of categories, not an exhaustive ballot census.',
                           'Complete-case selection and unresolved parties can depend on politics; country-equal weighting does not correct them.',
                           'Left-right and demographics with missing values retain explicit missing indicators/categories.',
                           'These counts and predictor distributions are not outcome associations.']}
    for name,frame in [('eb_samples',pd.DataFrame(summary)),('eb_outcome_counts',pd.DataFrame(marginals)),
                       ('eb_predictor_support',pd.DataFrame(checks)),('eb_trust_overlap',overlap)]:
        frame.to_csv(OUT/(name+'.csv'),index=False)
    (OUT/'eb_input_contract.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
    metadata=[{'source':v,'label':meta.column_names_to_labels[v],'value_labels':meta.variable_value_labels.get(v,{})}
              for v in sorted({v for info in VARIABLES.values() for v in info['source'].split()})]
    (OUT/'eb_model_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:config[k] for k in ['sample_totals','primary_government_countries','primary_three_choice_countries']},indent=2))

if __name__=='__main__':main()
