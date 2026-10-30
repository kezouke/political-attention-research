from pathlib import Path
import unittest
import pandas as pd
P=Path(__file__).resolve().parents[1]
class FrontpageChecks(unittest.TestCase):
 def test_outlet_year_denominator_and_intervals(self):
  d=pd.read_csv(P/'data/processed/spain_frontpage_2000_2011.csv')
  self.assertEqual(len(d),2*12*8)
  self.assertTrue((d.hits<=d.n).all())
  self.assertTrue((d.lo_month_bootstrap_pct<=d.hi_month_bootstrap_pct).all())
  r=d[(d.outlet=='El País')&(d.year==2010)&(d.topic=='economy_labour_commerce')].iloc[0]
  self.assertEqual((r.hits,r.n),(374,2907));self.assertAlmostEqual(r.share_pct,100*374/2907)
 def test_endpoint_choice_changes_spain_count_direction(self):
  d=pd.read_csv(P/'data/processed/mecco_endpoint_sensitivity.csv')
  a=d[(d.region=='spain')&(d.excluded_source=='none')].set_index('start')
  self.assertEqual((a.loc[2010,'start_count'],a.loc[2010,'end_count']),(1698,2071))
  self.assertGreater(a.loc[2010,'change_pct'],0);self.assertLess(a.loc[2021,'change_pct'],0)
if __name__=='__main__':unittest.main()
