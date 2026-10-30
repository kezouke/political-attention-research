"""Checks for sample definitions, denominators and published conclusions."""
from pathlib import Path
import unittest
import pandas as pd
P=Path(__file__).resolve().parents[1]

class ResearchResults(unittest.TestCase):
    def test_ess_country_wave_group_coverage(self):
        x=pd.read_csv(P/'data/processed/ess_hardship_country.csv')
        self.assertEqual(len(x),22*2*2)
        self.assertEqual(x.groupby(['country','wave']).size().min(),2)
        self.assertTrue(x.weighted_pct.between(0,100).all())
        self.assertEqual(int(x[(x.wave==10)&(x.difficulty==1)].n.sum()),6978)
        self.assertEqual(int(x[(x.wave==10)&(x.difficulty==0)].n.sum()),35926)
    def test_four_cells_are_consistent(self):
        x=pd.read_csv(P/'data/processed/ess_four_groups.csv')
        self.assertEqual(len(x),22*2*4)
        for _,g in x.groupby(['country','wave']):
            self.assertEqual(len(g),4)
            self.assertEqual(int(g.n.sum()),int(g.total_n.iloc[0]))
            self.assertAlmostEqual(g.weighted_pct.sum(),100,places=6)
        x=x.set_index(['country','wave','difficulty','worried'])
        y=pd.read_csv(P/'data/processed/ess_hardship_overlap.csv')
        for _,r in y.iterrows():
            self.assertAlmostEqual(x.loc[(r.cntry,r.wave,1,1),'weighted_pct'],r.both_pct,places=7)
    def test_text_audit_is_stratified_and_not_claimed_as_accuracy(self):
        a=pd.read_csv(P/'data/processed/spain_text_audit.csv')
        self.assertEqual(len(a),48)
        self.assertEqual(len(a.groupby(['party','economic_institutional'])),4)
        self.assertTrue((a.groupby(['party','economic_institutional']).size()==12).all())
        self.assertEqual(int(((a.economic_institutional==0)&(a.reference==1)).sum()),9)
        self.assertEqual(int(((a.economic_institutional==1)&(a.reference==1)).sum()),20)
    def test_media_comparison_units(self):
        d=pd.read_csv(P/'data/processed/us_media_public_agenda.csv')
        self.assertEqual(len(d),56)
        r=d[(d.year==2016)&(d.topic=='macroeconomy')].iloc[0]
        self.assertEqual(int(r.news_total_n),1070)
        self.assertEqual(int(r.news_n),3)
        self.assertAlmostEqual(r.poll_normalized_pct,26.2686,places=3)
    def test_model_uncertainty_is_preserved(self):
        x=pd.read_csv(P/'data/processed/ess_hardship_model.csv'); r=x[(x['sample']=='all_matched')&(x['term']=='difficulty_round10')].iloc[0]
        self.assertAlmostEqual(r.coef_pp,1.3524,places=3)
        self.assertLess(r.ci_low_pp,0);self.assertGreater(r.ci_high_pp,0)
        self.assertEqual(int(r.n),73871)
    def test_manifesto_proxies_and_election_coverage(self):
        x=pd.read_csv(P/'data/processed/manifesto_issue_shares.csv');self.assertTrue((x.strict<=x.broad).all());self.assertTrue(x.broad.between(0,100.1).all());self.assertTrue(x.vote_coverage.between(0,100.1).all())
        r=x[(x.country=='Serbia')&(x.date==202204)].iloc[0];self.assertAlmostEqual(r.broad,63.4,places=1)
        self.assertFalse((x.country=='Thailand').any())
    def test_no_interpolated_2011_europe(self):
        x=pd.read_csv(P/'data/processed/europe_priorities_mean.csv');self.assertFalse((x.year==2011).any());r=x.set_index('year');self.assertEqual(int(r.loc[2010,'n_countries']),14);self.assertAlmostEqual(r.loc[2024,'price'],33.67,places=2)
    def test_media_denominators_and_basket(self):
        n=pd.read_csv(P/'data/processed/nyt_topics_2010_2016.csv').set_index('year');self.assertEqual(int(n.loc[2010,'n']),658);self.assertEqual(int(n.loc[2016,'civil_rights_n']),22)
        x=pd.read_csv(P/'data/processed/mecco_baskets_annual.csv');r=x[(x.region=='latin_america')&(x.year==2025)].iloc[0];self.assertEqual(int(r.articles),1550);self.assertEqual(int(r.n_sources),2)
    def test_site_bundle_exists(self):
        html=(P/'docs/index.html').read_text();data=(P/'docs/data.js').read_text();self.assertIn('data-language="en"',html);self.assertIn('lang="ru"',html);self.assertIn('"ess_model"',data);self.assertNotIn('userId=',html+data)

if __name__=='__main__':unittest.main()
