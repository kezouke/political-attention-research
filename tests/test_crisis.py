"""Check that the displayed election and survey comparisons match the published tables."""

import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_csv(name):
    with (ROOT / 'data/processed' / f'{name}.csv').open(newline='') as file:
        return list(csv.DictReader(file))


class CrisisEssayTests(unittest.TestCase):
    def test_bank_pairs_and_incumbent_tallies(self):
        pairs = [row for row in read_csv('crisis_election_pairs')
                 if row['type'] == 'legislative' and row['kind'] == 'banking'
                 and row['window_years'] == '5' and row['status'] == 'paired'
                 and row['borderline'] == 'False' and row['ambiguous_election'] == 'False'
                 and float(row['pre_regime']) >= 2 and float(row['post_regime']) >= 2]
        shifts = [float(row['change_pp']) for row in pairs]
        self.assertEqual((len(shifts), sum(x > 0 for x in shifts), sum(x < 0 for x in shifts)), (29, 15, 7))
        self.assertEqual(len({row['iso'] for row in pairs}), 28)
        self.assertEqual((min(row['year'] for row in pairs), max(row['year'] for row in pairs)), ('1991', '2008'))
        self.assertEqual((min(row['pre_date'][:4] for row in pairs), max(row['post_date'][:4] for row in pairs)),
                         ('1989', '2013'))
        with_pm = [row for row in pairs if row['pm_change_pp']]
        pm_losses = [row for row in with_pm if float(row['pm_change_pp']) < 0]
        self.assertEqual((len(with_pm), len(pm_losses), sum(float(r['change_pp']) > 0 for r in pm_losses)),
                         (21, 17, 8))
        spain = next(row for row in pairs if row['iso'] == 'ESP' and row['year'] == '2008')
        self.assertEqual((spain['pre_date'], spain['post_date']), ('2008-03-09', '2011-11-20'))
        self.assertEqual(float(spain['change_pp']), 0)
        iceland = next(row for row in pairs if row['iso'] == 'ISL')
        self.assertEqual((iceland['year'], iceland['pre_date'], iceland['post_date']),
                         ('2008', '2007-05-12', '2009-04-25'))
        self.assertEqual((float(iceland['pre_vote_pct']), float(iceland['post_vote_pct'])), (0, 22))

    def test_slovak_banking_episode_is_not_an_ordinary_recession(self):
        slovak = [row for row in read_csv('crisis_election_pairs') if row['iso'] == 'SVK']
        self.assertTrue(any(row['year'] == '1998' and row['kind'] == 'banking' for row in slovak))
        self.assertFalse(any(row['year'] == '1999' and row['kind'] == 'recession' for row in slovak))

    def test_price_figure_keeps_missing_elections_distinct_from_zero(self):
        rows = read_csv('price_shock_election_check')
        paired = [row for row in rows if row['status'] == 'paired']
        self.assertEqual((len(rows), len(paired), sum(float(r['vote_change_pp']) > 0 for r in paired)),
                         (16, 8, 7))
        self.assertTrue(all(float(row['price_change_pp']) > 0 for row in rows))
        self.assertTrue(all(not row['vote_change_pp'] for row in rows if row['status'] != 'paired'))
        self.assertEqual(next(r['status'] for r in rows if r['iso'] == 'SRB'), 'not_classified')

    def test_offline_bundle_and_bilingual_article(self):
        bundle = (ROOT / 'docs/crisis-data.js').read_text()
        data = json.loads(bundle.removeprefix('window.CRISIS_DATA = ').strip().removesuffix(';'))
        self.assertEqual(len(data['pairs']), 77)
        self.assertEqual(len({r['iso'] for r in data['pairs']}), 37)
        self.assertEqual(len(data['brazil']), 30)
        self.assertEqual(len(data['prices']), 16)
        self.assertTrue(any(r['iso'] == 'BRA' and r['type'] == 'presidential'
                            and r['year'] == 2015 and r['post_vote_pct'] == 46.03 for r in data['pairs']))
        for row in data['pairs']:
            self.assertAlmostEqual(row['post_vote_pct'] - row['pre_vote_pct'], row['change_pp'], places=6)
        article = (ROOT / 'docs/index.html').read_text()
        for text in ('Elections after banking crises', 'Выборы после банковских кризисов',
                     '29 pairs of parliamentary elections in 28 countries',
                     '29 пар парламентских выборов в 28 странах', '1991–2008', '1989–2013'):
            self.assertIn(text, article)
        self.assertIn('src="crisis-data.js"', article)
        companion = (ROOT / 'docs/attention.html').read_text()
        for text in ('46.03%', '46,03%', '16.8% to 46.8%', '16,8% до 46,8%'):
            self.assertIn(text, companion)
        for figure in ('brazil', 'prices'):
            self.assertIn(f'attention.html?lang=ru#{figure}', article)
            self.assertNotIn(f'id="{figure}-figure"', article)
            self.assertIn(f'id="{figure}-figure"', companion)
        self.assertIn('src="crisis-data.js"', companion)
