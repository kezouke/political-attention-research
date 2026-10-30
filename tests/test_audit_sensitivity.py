"""Checks of identities and scenario-specific denominator logic in the audit."""
from pathlib import Path
import unittest
import pandas as pd
P=Path(__file__).resolve().parents[1]
class AuditSensitivity(unittest.TestCase):
 def test_ess_bounds_and_counts(self):
  x=pd.read_csv(P/'data/processed/audit_ess_skip_sensitivity.csv')
  self.assertEqual(len(x),44)
  self.assertTrue((x.scenario_skeptics_not_worried_pct<=x.observed_pct+1e-8).all())
  self.assertTrue((x.observed_pct<=x.scenario_skeptics_strongly_worried_pct+1e-8).all())
  row=x[(x.country=='IL')&(x.wave==10)].iloc[0]
  self.assertEqual(int(row.routed_skeptic_n),80)
  self.assertAlmostEqual(row.scenario_skeptics_not_worried_pct,30.286,places=2)
 def test_ess_independent_recalculation_matches_previous_snapshot(self):
  x=pd.read_csv(P/'data/processed/audit_ess_skip_sensitivity.csv')
  original=pd.read_csv(P/'analysis/baseline/outputs/ess_full_country_wave.csv')
  matched=x.merge(original,on=['country','wave'],validate='one_to_one')
  self.assertEqual(len(matched),44)
  self.assertLess((matched.observed_pct-matched.pct).abs().max(),0.0001)
  self.assertTrue((matched.observed_n==matched.n).all())
 def test_manifesto_bounds(self):
  x=pd.read_csv(P/'data/processed/audit_manifesto_missing_bounds.csv')
  self.assertEqual(set(x.country),{'Israel','Serbia','Brazil','Bulgaria','Spain'})
  self.assertTrue((x.broad_lower_bound_pct<=x.broad+1e-7).all())
  self.assertTrue((x.broad<=x.broad_upper_bound_pct+1e-7).all())
  row=x[x.country=='Israel'].iloc[0]
  self.assertAlmostEqual(row.broad_lower_bound_pct,32.46,places=2)
  self.assertAlmostEqual(row.broad_upper_bound_pct,76.40,places=2)
if __name__=='__main__':unittest.main()
