"""Check publication claims and assets using public aggregates only."""
from pathlib import Path
import hashlib
import json
import re
import pandas as pd
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/processed'
P=DATA/'three_explanations'
claims=[]
sources=set()

def read(name):
    path=DATA/name;sources.add(path)
    return pd.read_csv(path)

def claim(name,value,expected,source,decimals=2):
    assert abs(float(value)-expected)<(.501*10**(-decimals)),(name,value,expected)
    claims.append({'claim':name,'value':float(value),'published_rounded_value':expected,
                   'decimals':decimals,'source':source})

def one(d,**filters):
    for k,v in filters.items():d=d[d[k].eq(v)]
    assert len(d)==1,(filters,len(d))
    return d.iloc[0]

def main():
    file='crisis_context.csv';context=read(file)
    assert len(context)==29 and context.iso.nunique()==28
    assert context.onset_year.between(2007,2009).sum()==13
    assert not context[['iso','onset_year']].duplicated().any()
    assert (ROOT/'docs/data/crisis-context.csv').read_bytes()==(DATA/file).read_bytes()
    assert context[['context_ru','context_en','context_source']].notna().all().all()
    for iso,year,x in [('FIN',1991,-9.7),('IND',1993,20.2)]:
        claim(f'context_gdp_{iso}_{year}',one(context,iso=iso,onset_year=year).gdp_change_three_years_pct,x,file,1)
    r=one(context,iso='ESP',onset_year=2008)
    for column,x in [('baseline_vote_pct',0),('first_vote_pct',0),('second_vote_pct',20.66)]:
        claim('spain_wpd_'+column,r[column],x,file)
    file='spain_macro_conditions.csv';d=read(file)
    for year,x in [(2007,8.2),(2011,21.4)]:
        claim(f'spain_unemployment_{year}',one(d,year=year).unemployment,x,file,1)
    d=read('crisis_dynamics_summary.csv')
    for rank,expected in [(1,.18),(2,5.48)]:
        r=one(d,sample='balanced_two',rank=rank)
        assert r.n==29 and r.countries==28
        claim(f'historical_median_{rank}',r.median_pp,expected,'crisis_dynamics_summary.csv')
    claim('historical_excluding_2007_09',one(d,sample='balanced_two_no_2007_09',rank=2).median_pp,1.22,'crisis_dynamics_summary.csv')
    d=read('crisis_dynamics_benchmarks.csv')
    r=one(d,sample='within_country_bank_minus_calm',outcome='second_change_pp')
    assert r.countries==21 and one(d,sample='calm',outcome='second_change_pp')['n']==50
    for c,x in [('mean_pp',5.41),('bootstrap_low',-1.19),('bootstrap_high',12.04)]:
        claim('crisis_calm_'+c,r[c],x,'crisis_dynamics_benchmarks.csv')
    d=read('programme_decomposition.csv');d=d[d['sample'].eq('main')&d.topic.eq('economy')]
    for kind,n,largest in [('banking',16,10),('comparison',75,51)]:
        q=d[d.kind.eq(kind)];assert len(q)==n
        v=q[['within_pp','reweight_pp','roster_pp']].abs().idxmax(axis=1).eq('within_pp').sum()
        claim(kind+'_within_largest',v,largest,'programme_decomposition.csv',0)
        if kind=='banking':
            assert q.iso.nunique()==15 and q.change_pp.gt(0).sum()==q.change_pp.lt(0).sum()==8
            assert q.manual_changes.gt(0).sum()==8
    r=one(d,kind='banking',iso='ESP')
    for column,x in [('change_pp',7.29),('within_pp',7.77),('reweight_pp',-1.85),('roster_pp',1.36)]:
        claim('spain_programme_'+column,r[column],x,'programme_decomposition.csv')
    assert abs(r.change_pp-r.within_pp-r.reweight_pp-r.roster_pp)<1e-8
    d=read('programme_prediction_elections.csv');v=d.groupby('model').absolute_error.mean()
    assert d.pair_id.nunique()==89 and d.iso.nunique()==27
    claim('programme_prediction_baseline',v.baseline,4.15,'programme_prediction_elections.csv')
    claim('programme_prediction_topics',v.programme_changes,4.17,'programme_prediction_elections.csv')
    d=read('nlp_metrics.csv')
    for model,x in [('tfidf',.482),('e5_bert',.588)]:
        r=one(d,model=model,split='test');assert r.n==3636
        claim('nlp_'+model,r.macro_f1,x,'nlp_metrics.csv',3)
    file='three_explanations/eb_v2/eb_model_margins.csv';d=read(file)
    for var,outcome,x,lo,hi in [('government_distrust',0,-16.03,None,None),
                              ('party_distrust',3,8.24,4.51,11.46),
                              ('party_distrust',2,-.61,-3.30,1.48)]:
        r=one(d,target='four_outcomes',variable=var,outcome=outcome);assert r.n==15962
        claim(f'eb_{var}_{outcome}',r.probability_difference*100,x,file)
        if lo is not None:
            claim(f'eb_{var}_{outcome}_low',r.ci_low*100,lo,file)
            claim(f'eb_{var}_{outcome}_high',r.ci_high*100,hi,file)
    file='three_explanations/bes_model_margins.csv';d=read(file)
    for year,x in [(2015,.74),(2017,.31),(2019,.24)]:
        r=one(d,year=year,target='four_outcomes',variable='politician_distrust',outcome=2)
        claim(f'bes_levels_pop_{year}',r.probability_difference*100,x,file)
    file='three_explanations/bes_model_sensitivity.csv';d=read(file)
    for year,x in [(2015,5.22),(2017,1.25),(2019,1.08)]:
        r=one(d,year=year,target='four_outcomes',scenario='without_both_prior_preferences',fit='alternative',variable='politician_distrust',outcome=2)
        claim(f'bes_without_preferences_{year}',r.probability_difference*100,x,file)
    file='three_explanations/bes_change_model_margins.csv';d=read(file)
    for year,n,pop,non in [(2015,15613,2.05,1.20),(2017,8758,.64,1.98),(2019,3111,.65,2.30)]:
        for outcome,x in [(2,pop),(3,non)]:
            r=one(d,year=year,target='four_outcomes',variable='politician_distrust',outcome=outcome)
            assert r.n==n and r.ci_low>0
            claim(f'bes_repeated_{year}_{outcome}',r.probability_difference*100,x,file)
    d=read('three_explanations/bes_change_incremental_validation.csv')
    q=d[d.target.eq('four_outcomes')&d.baseline_block.eq('without_trust')&d.expanded_block.eq('full')]
    assert len(q)==3 and q.relative_improvement_percent.lt(1).all()
    file='three_explanations/gles_importance_incremental_validation.csv';d=read(file)
    r=one(d,model_topics='all_three',baseline_block='late_position',expanded_block='late_importance')
    assert r.n==2962 and r.relative_ci_high<0
    claim('gles_importance_improvement',r.relative_improvement_percent,-.55,file)
    d=read('three_explanations/gles_importance_model_margins.csv')
    q=d[d.model_topics.eq('all_three')&d.position_scenario.eq('observed')&d.outcome.eq(2)]
    assert len(q)==3 and q.ci_low.lt(0).all() and q.ci_high.gt(0).all()
    for topic,x in [('tax_welfare',.94),('immigration',1.00),('climate_growth',.62)]:
        r=one(q,topic=topic);assert r.n==2962
        claim('gles_importance_'+topic,r.probability_difference*100,x,'three_explanations/gles_importance_model_margins.csv')
    d=read('three_explanations/gles_importance_simultaneous.csv')
    claim('gles_multiple_topics_increase',100*d.loc[d.topics_increasing.ge(2),'weight_share'].sum(),14.35,'three_explanations/gles_importance_simultaneous.csv')
    file='three_explanations/national_model_margins.csv';d=read(file)
    for outcome,x in [(2,6.50),(3,10.21)]:
        r=one(d,dataset='NL2012',target='all_outcomes',variable='elite_distrust',outcome=outcome)
        claim(f'national_nl2012_{outcome}',r.probability_difference*100,x,file)
    for outcome,x in [(2,-1.47),(3,7.07)]:
        r=one(d,dataset='ES2015',target='all_outcomes',variable='elite_distrust',outcome=outcome)
        claim(f'national_es2015_{outcome}',r.probability_difference*100,x,file)
        if outcome==2:
            claim('national_es2015_pop_low',r.ci_low*100,-3.27,file)
            claim('national_es2015_pop_high',r.ci_high*100,.22,file)
    r=one(d,dataset='BE2014',target='all_outcomes',variable='elite_distrust',outcome=2)
    claim('national_be_inclusive',r.probability_difference*100,3.09,file)
    file='three_explanations/national_sensitivity.csv';d=read(file)
    r=one(d,dataset='BE2014',target='all_outcomes',scenario='v4_strict',fit='alternative',variable='elite_distrust',outcome=2)
    claim('national_be_strict',r.probability_difference*100,.70,file)
    d=read('three_explanations/national_sensitivity_status.csv')
    assert not one(d,dataset='IS2013',target='opposition_type',scenario='v4_strict').estimable

    file='three_explanations/manifesto_refresh/primary_version_summary.csv';d=read(file)
    r=one(d,version='2026a',kind='banking',scope='all_eligible_pairs')
    assert r.n==16 and r.countries==15
    for c,x in [('increase',8),('decrease',8),('within_largest',10)]:
        claim('manifesto_2026a_banking_'+c,r[c],x,file,0)
    r=one(d,version='2026a',kind='comparison',scope='all_eligible_pairs')
    assert r.n==75
    claim('manifesto_2026a_calm_within_largest',r.within_largest,52,file,0)
    file='three_explanations/manifesto_refresh/matched_version_summary.csv';d=read(file)
    for version,x in [('2023a',49),('2026a',50)]:
        r=one(d,version=version,kind='comparison');assert r.n==73
        claim('manifesto_matched_calm_'+version,r.within_largest,x,file,0)
    file='three_explanations/manifesto_refresh/estimate_version_comparison.csv';d=read(file)
    q=d[d['sample'].eq('main')&d.topic.eq('economy')&d.kind_2023a.eq('banking')]
    assert len(q)==16 and q['_merge'].eq('both').all() and not q.change_sign_differs.any()
    maximum=q.change_pp_difference.abs().max();assert maximum<.003
    claim('manifesto_banking_max_revision_pp',maximum,.00267,file,5)

    page=ROOT/'docs/index.html';soup=BeautifulSoup(page.read_text(),'html.parser')
    ids=[x['id'] for x in soup.select('[id]')];assert len(ids)==len(set(ids))
    assert len(soup.select('figure'))==5
    expected_episodes={f'{r.iso}-{r.onset_year}' for r in context.itertuples()}
    for lang in ['ru','en']:
        cards=soup.select(f'#crisis-context-{lang} .crisis-card')
        assert len(cards)==29
        assert {c['data-episode'] for c in cards}==expected_episodes
    for a in soup.select('a[href^="#"]'):assert a['href'][1:] in ids,a
    for node,attribute in [('img','src'),('source','srcset'),('link','href'),('script','src')]:
        for el in soup.select(f'{node}[{attribute}]'):
            path=el[attribute].split('?')[0]
            if not path.startswith(('http:','https:','data:')):assert (ROOT/'docs'/path).is_file(),path
    for sec in soup.select('main > section'):
        for lang in ['ru','en']:assert sec.select_one(f'[data-copy="{lang}"]') is not None
    assert '\u2014' not in soup.get_text()
    assert 'brazil' not in ids and 'prices' not in ids
    for lang in ['ru','en']:
        source=(ROOT/f'article/essay.{lang}.md').read_text()
        assert '<!-- figure:' not in soup.get_text()
        assert len(re.findall(r'<!-- section:',source))==9
        for url in re.findall(r'\]\((https?://[^)]+)\)',source):assert '10990' not in url
    for a in soup.select('a[href]'):
        prefix='https://github.com/kezouke/political-attention-research/blob/main/'
        if a['href'].startswith(prefix):assert (ROOT/a['href'][len(prefix):]).exists(),a['href']
    for file in sources:
        cols=set(pd.read_csv(file,nrows=0).columns)
        assert not cols.intersection({'person_id','respondent_id','lfdn','free_text','id'})
    pd.DataFrame(claims).to_csv(P/'choice_claim_values.csv',index=False)
    files=sorted(sources|{page,ROOT/'article/essay.ru.md',ROOT/'article/essay.en.md',
                         ROOT/'analysis/84_choice_publication_figures.py',ROOT/'analysis/85_build_choice_essay.py',
                         ROOT/'analysis/87_crisis_context.py',ROOT/'data/context/crisis_background.json',
                         ROOT/'docs/choice.css',ROOT/'data/context/wdi_crisis_growth.csv',
                         ROOT/'data/context/wdi_crisis_growth_source.json',Path(__file__)})
    result={'numeric_claims_passed':len(claims),'figures':5,'parallel_article_sections':9,
            'context_episodes_per_language':29,'context_public_csv_matches':True,
            'local_assets_present':True,'internal_links_resolve':True,'raw_microdata_read':False,
            'meaning_and_transition_review':'CHOICE_AUDIT.md; separate editorial review, not established by these assertions',
            'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    (P/'choice_publication_checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='sha256'},indent=2))

if __name__=='__main__':main()
