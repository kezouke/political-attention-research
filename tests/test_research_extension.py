"""Independent numerical contracts and edge cases for the new research."""
import importlib.util
import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data/processed'


def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'analysis'/file)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


class ResearchExtensionTests(unittest.TestCase):
    def test_exact_accounting_with_changes_and_entry(self):
        decompose=module('programme_test','24_programme_decomposition.py').decomposition
        a=pd.DataFrame({'party':[1,2],'pervote':[60.,40.],'topic':[20.,40.]})
        b=pd.DataFrame({'party':[1,2],'pervote':[50.,50.],'topic':[30.,60.]})
        q=decompose(a,b,'topic')
        self.assertAlmostEqual(q['pre_share'],28)
        self.assertAlmostEqual(q['post_share'],45)
        self.assertAlmostEqual(q['within_pp'],14.5)
        self.assertAlmostEqual(q['reweight_pp'],2.5)
        self.assertEqual(q['roster_pp'],0)
        b=pd.DataFrame({'party':[1,3],'pervote':[50.,50.],'topic':[30.,80.]})
        q=decompose(a,b,'topic')
        self.assertAlmostEqual(q['roster_pp'],24)
        self.assertAlmostEqual(sum(q[k] for k in ['within_pp','reweight_pp','roster_pp']),27)

    def test_missing_first_election_is_never_skipped(self):
        dynamics=module('dynamics_test','23_crisis_dynamics.py')
        p=pd.DataFrame([dict(iso='XXX',country='Example',year=2008,pre_date=pd.Timestamp('2007-01-01'),
                            onset_through=pd.Timestamp('2008-12-31'),pre_vote_pct=10)])
        c=pd.DataFrame(dict(iso=['XXX']*3,type=['legislative']*3,
                            date=pd.to_datetime(['2007-01-01','2009-01-01','2013-01-01']),
                            vote_pct=[10,np.nan,20],regime=[3]*3))
        b=pd.DataFrame({'iso':['XXX'],'year':[2008]})
        q=dynamics.build_trajectories(p,c,b).set_index('rank')
        self.assertEqual(q.loc[1,'status'],'classification_missing')
        self.assertEqual(q.loc[2,'date'],pd.Timestamp('2013-01-01'))
        b=pd.DataFrame({'iso':['XXX','XXX'],'year':[2008,2012]})
        q=dynamics.build_trajectories(p,c,b).set_index('rank')
        self.assertEqual(q.loc[2,'status'],'subsequent_banking_crisis')

    def test_balanced_horizon_preserves_original_baseline(self):
        d=pd.read_csv(OUT/'crisis_dynamics_balanced.csv')
        p=pd.read_csv(OUT/'crisis_election_pairs.csv')
        p=p[p.type.eq('legislative')&p.kind.eq('banking')&p.window_years.eq(5)&p.status.eq('paired')&~p.borderline&~p.ambiguous_election&p.pre_regime.ge(2)&p.post_regime.ge(2)]
        q=d.merge(p,left_on=['iso','onset_year'],right_on=['iso','year'],validate='one_to_one')
        self.assertEqual(len(q),29)
        np.testing.assert_allclose(q.change_pp_first,q.change_pp)
        np.testing.assert_allclose(q.additional_pp,q.change_pp_second-q.change_pp_first)
        self.assertAlmostEqual(d.change_pp_second.median(),5.48)
        self.assertTrue((d.date_second>d.date_first).all())
        self.assertTrue((d.years_from_onset<=10).all())

    def test_every_published_decomposition_reconciles(self):
        d=pd.read_csv(OUT/'programme_decomposition.csv')
        for prefix in ['', 'raw_', 'common_']:
            good=d.dropna(subset=[prefix+'change_pp'])
            np.testing.assert_allclose(good[prefix+'post_share']-good[prefix+'pre_share'],good[prefix+'change_pp'],atol=2e-6)
            np.testing.assert_allclose(good[[prefix+k for k in ['within_pp','reweight_pp','roster_pp']]].sum(axis=1),good[prefix+'change_pp'],atol=2e-6)
        m=d[d['sample'].eq('main')&d.kind.eq('banking')&d.topic.eq('economy')]
        self.assertEqual((len(m),m.iso.nunique()),(16,15))
        self.assertTrue(m.pre_coverage.ge(75).all()&m.post_coverage.ge(75).all())
        self.assertEqual((m.change_pp>0).sum(),8)
        q=m[m.common_pre_coverage.ge(75)&m.common_post_coverage.ge(75)]
        self.assertEqual((len(q),int((q.common_within_pp.abs()>q.common_reweight_pp.abs()).sum())),(11,9))
        summary=pd.read_csv(OUT/'programme_summary.csv')
        for (sample,kind,topic),q in d.groupby(['sample','kind','topic']):
            s=summary
            s=s[s['sample'].eq(sample)&s.kind.eq(kind)&s.topic.eq(topic)].iloc[0]
            self.assertEqual(len(q),s.n)
            self.assertAlmostEqual(q.change_pp.mean(),s.mean_change,places=5)

    def test_prediction_errors_and_nlp_claims(self):
        d=pd.read_csv(OUT/'programme_prediction_elections.csv')
        self.assertEqual(d.pair_id.nunique(),89)
        self.assertEqual(d.iso.nunique(),27)
        q=d.groupby('model').absolute_error.mean()
        self.assertEqual(round(q.baseline,2),4.15)
        self.assertEqual(round(q.programme_changes,2),4.17)
        nlp=pd.read_csv(OUT/'nlp_metrics.csv').query('split == "test"').set_index('model')
        self.assertEqual(int(nlp.loc['e5_bert','n']),3636)
        self.assertGreater(nlp.loc['e5_bert','macro_f1'],nlp.loc['tfidf','macro_f1'])
        self.assertEqual(round(100*nlp.loc['e5_bert','accuracy'],1),60.2)

    def test_page_assets_anchors_and_bilingual_scope(self):
        html=(ROOT/'docs/index.html').read_text();s=BeautifulSoup(html,'html.parser')
        ids=[x['id'] for x in s.select('[id]')];self.assertEqual(len(ids),len(set(ids)))
        for a in s.select('a[href^="#"]'):self.assertIn(a['href'][1:],ids)
        for img in s.select('img[src]'):self.assertTrue((ROOT/'docs'/img['src']).exists())
        for sec in s.select('main > section'):
            self.assertIsNotNone(sec.select_one('[data-copy="ru"]'))
            self.assertIsNotNone(sec.select_one('[data-copy="en"]'))
        self.assertNotIn('—',s.get_text())
        self.assertNotIn('id="brazil"',html);self.assertNotIn('id="prices"',html)
        d=json.loads((ROOT/'docs/research-data.js').read_text().removeprefix('window.RESEARCH_DATA = ').strip().removesuffix(';'))
        self.assertEqual(len(d['horizon']),29);self.assertEqual(len(d['programmes']),48)


if __name__=='__main__':unittest.main()
