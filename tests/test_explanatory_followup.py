from pathlib import Path
import unittest
import pandas as pd
P=Path(__file__).resolve().parents[1]
class ExplanatoryEvidence(unittest.TestCase):
 def test_cis_comparable_snapshot(self):
  x=pd.read_csv(P/'data/processed/identity_spain_cis_selected.csv')
  i=x[x.issue.eq('immigration')].set_index('year');self.assertAlmostEqual(i.loc[2023,'pct_top3'],5.7);self.assertAlmostEqual(i.loc[2024,'pct_top3'],30.4)
  c=x[x.issue.eq('climate_change')].set_index('year');self.assertNotIn(2010,c.index);self.assertAlmostEqual(c.loc[2024,'pct_top3'],3.7)
 def test_thailand_rounded_observation_and_vote_denominator(self):
  x=pd.read_csv(P/'data/processed/thailand_public_opinion_snapshots.csv');g=x[(x.year==2010)&(x.issue=='poor economy')].iloc[0];self.assertTrue(pd.isna(g['percent']))
  t=pd.read_csv(P/'data/processed/thailand_issue_change_2009_2010.csv').iloc[0];self.assertEqual(t.change_pp,18)
 def test_macro_and_real_compensation(self):
  x=pd.read_csv(P/'data/processed/spain_macro_conditions.csv').set_index('year');self.assertAlmostEqual(x.loc[2019,'real_compensation_index_2019'],100);self.assertGreater(x.loc[2021,'real_compensation_index_2019'],x.loc[2022,'real_compensation_index_2019'])
  m=pd.read_csv(P/'data/processed/macro_issue_models.csv');r=m[(m.outcome=='unemploy')&(m.specification=='country_year_fe')].iloc[0];self.assertEqual(r.n,196);self.assertAlmostEqual(r.beta_pp_per_point,2.3265,places=3)
 def test_trust_association_and_falsification_bounds(self):
  x=pd.read_csv(P/'data/processed/ess_insecurity_trust_models.csv');r=x[(x.outcome=='trstprl')&(x.covariates=='base')].iloc[0];self.assertEqual((r.n,r.countries),(82358,22));self.assertLess(r.ci_high,0)
  c=pd.read_csv(P/'data/processed/structural_exposure_wdi.csv');r=c[(c.iso=='BRA')&(c.year==2022)].iloc[0];self.assertLess(r.energy_import_pct_use,0)
 def test_common_shock_does_not_create_a_positive_dose_response(self):
  c=pd.read_csv(P/'data/processed/common_shock_2021_2022_countries.csv')
  self.assertEqual(len(c),16)
  self.assertTrue((c.price_change_pp>0).all())
  r=c.price_change_pp.corr(c.inflation_change_pp)
  self.assertLess(r,0)
  s=pd.read_csv(P/'data/processed/common_shock_2021_2022_summary.csv').iloc[0]
  self.assertAlmostEqual(r,s.pearson_r_delta_inflation_delta_price,places=6)
if __name__=='__main__':unittest.main()
