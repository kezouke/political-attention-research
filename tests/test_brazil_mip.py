"""Independent checks on committed aggregates and their denominator contracts."""
from pathlib import Path
import unittest
import pandas as pd
P=Path(__file__).resolve().parents[1]
class BrazilianMIP(unittest.TestCase):
 def test_waves_denominators_and_manual_numerators(self):
  x=pd.read_csv(P/'data/processed/brazil_mip_longitudinal.csv').set_index(['wave','issue'])
  self.assertEqual(x.index.get_level_values(0).nunique(),10)
  self.assertEqual(int(x.loc[(2010,'health'),'positive_n']),339)
  self.assertEqual(int(x.loc[(2024,'health'),'positive_n']),258)
  self.assertEqual(int(x.loc[(2017,'corruption'),'positive_n']),374)
  self.assertAlmostEqual(x.loc[(2010,'economy_strict'),'pct_all'],207/1204*100,places=8)
  self.assertAlmostEqual(x.loc[(2024,'economy_strict'),'pct_all'],206/1204*100,places=8)
  self.assertTrue((x.pct_valid>=x.pct_all-1e-10).all())
 def test_euro_coverage_and_missing_wave(self):
  x=pd.read_csv(P/'data/processed/six_country_euro_priorities.csv')
  self.assertEqual(set(x.country),{'BG','ES','RS'})
  self.assertFalse(x.year.eq(2011).any())
  self.assertEqual(int(x[x.country.eq('RS')].year.min()),2012)
  self.assertAlmostEqual(x[(x.country.eq('ES'))&(x.year.eq(2010))].unemploy.iloc[0],72.146682,places=5)
