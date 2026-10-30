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
