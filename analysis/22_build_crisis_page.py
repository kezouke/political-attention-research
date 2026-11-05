"""Build the offline chart bundle from published aggregates, without raw inputs."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/processed'


def read(name):
    return pd.read_csv(DATA / f'{name}.csv')


def records(frame, fields):
    return json.loads(frame[fields].to_json(orient='records', double_precision=8))


pairs = read('crisis_election_pairs')
sample = pairs.query(
    "window_years == 5 and status == 'paired' and not borderline "
    "and not ambiguous_election and pre_regime >= 2 and post_regime >= 2"
)
brazil = read('brazil_mip_longitudinal').query("issue in ['corruption', 'health', 'economy_strict']")
prices = read('price_shock_election_check')
data = {
    'pairs': records(sample, ['iso', 'country', 'region', 'year', 'kind', 'type', 'pre_date',
                              'post_date', 'pre_vote_pct', 'post_vote_pct', 'change_pp',
                              'pm_party', 'pm_pre_pct', 'pm_post_pct', 'pm_change_pp']),
    'brazil': records(brazil, ['wave', 'issue', 'n', 'pct_all', 'fieldwork_months']),
    'prices': records(prices, ['iso', 'country_name', 'price_2021', 'price_2022', 'price_change_pp',
                              'pre_date', 'post_date', 'pre_vote_pct', 'post_vote_pct',
                              'vote_change_pp', 'status']),
}
output = 'window.CRISIS_DATA = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n'
(ROOT / 'docs/crisis-data.js').write_text(output, encoding='utf-8')
