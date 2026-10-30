from pathlib import Path
import unittest
import pandas as pd

P=Path(__file__).resolve().parents[1]

class ManifestoFollowUp(unittest.TestCase):
    def test_reference_counts_and_sensitivity(self):
        x=pd.read_csv(P/'data/processed/spain_cap_dictionary_benchmark.csv')
        q=x[(x.party=='PP')&(x.year==2000)&(x.topic=='economy_institutions')].iloc[0]
        self.assertEqual(tuple(map(int,[q.tp,q.fp,q.fn,q.tn])),(236,113,606,1297))
        self.assertAlmostEqual(q.recall_pct,28.0285035629,places=5)
        self.assertTrue(q.recall_block_lo<q.recall_pct<q.recall_block_hi)
    def test_matched_single_party_has_coverage_and_codebook_caveat(self):
        x=pd.read_csv(P/'data/processed/manifesto_focus_matched_sensitivity.csv')
        q=x[(x.country=='Spain')&(x.topic=='environment_positive_501')].iloc[0]
        self.assertEqual(int(q.n_matched_parties),6)
        self.assertEqual(int(q.manual_changed_parties),6)
        self.assertAlmostEqual(q.change_pp,q.last_share-q.first_share,places=8)
        self.assertLess(q.last_vote_coverage,60)
    def test_missing_thailand_is_not_zero(self):
        x=pd.read_csv(P/'data/processed/manifesto_focus_longitudinal.csv')
        self.assertFalse(x.country.eq('Thailand').any())
        self.assertEqual(set(x.country),{'Brazil','Bulgaria','Israel','Serbia','Spain'})

if __name__=='__main__':unittest.main()
