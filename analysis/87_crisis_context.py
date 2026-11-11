"""Attach sourced context and frozen GDP growth to the unchanged 29 episodes.

This is descriptive publication material, not a new crisis definition or model.
Three annual growth observations are reported without selecting the worst year.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/processed'


def main():
    background = ROOT / 'data/context/crisis_background.json'
    gdp_path = ROOT / 'data/context/wdi_crisis_growth.csv'
    context = json.loads(background.read_text())
    c = pd.DataFrame(context['episodes'])
    c['context_source'] = c.source.map(context['sources'])
    assert c.context_source.notna().all()
    d = pd.read_csv(DATA / 'crisis_dynamics_balanced.csv')
    e = pd.read_csv(DATA / 'crisis_dynamics_episodes.csv')
    baseline = e[e['rank'].eq(0)][['iso', 'onset_year', 'date', 'vote_pct']]
    baseline = baseline.rename(columns={'date': 'baseline_date', 'vote_pct': 'baseline_vote_pct'})
    d = d.merge(baseline, on=['iso', 'onset_year'], validate='one_to_one')
    d = d.merge(c, on=['iso', 'onset_year'], validate='one_to_one', how='outer', indicator=True)
    assert d['_merge'].eq('both').all() and len(d) == 29 and d.iso.nunique() == 28
    d = d.drop(columns=['_merge', 'source']).rename(columns={'ru':'context_ru', 'en':'context_en'})
    rows = pd.read_csv(gdp_path)
    assert len(rows) == 87 and not rows[['iso','year']].duplicated().any()
    gdp = {(r.iso, r.year): r.gdp_growth for r in rows.itertuples()}
    for offset in range(3):
        d[f'gdp_growth_t{offset}'] = [gdp[(r.iso, r.onset_year + offset)] for r in d.itertuples()]
    cols = [f'gdp_growth_t{i}' for i in range(3)]
    assert np.isfinite(d[cols].to_numpy()).all()
    d['gdp_change_three_years_pct'] = ((1 + d[cols] / 100).prod(axis=1) - 1) * 100
    d['gdp_source'] = 'https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG'
    d['first_vote_pct'] = d.baseline_vote_pct + d.change_pp_first
    d['second_vote_pct'] = d.baseline_vote_pct + d.change_pp_second
    # Cross-check the join against independently retained election-rank records.
    for rank, date_col, share_col in [(1,'date_first','first_vote_pct'), (2,'date_second','second_vote_pct')]:
        q = d.merge(e[e['rank'].eq(rank)][['iso','onset_year','date','vote_pct']], on=['iso','onset_year'], validate='one_to_one')
        assert q[date_col].eq(q.date).all() and np.allclose(q[share_col], q.vote_pct)
    d = d.sort_values(['onset_year', 'iso'])
    d.to_csv(DATA / 'crisis_context.csv', index=False)
    public = ROOT / 'docs/data/crisis-context.csv'
    public.parent.mkdir(exist_ok=True)
    d.to_csv(public, index=False)
    summary = {
        'episodes': len(d), 'countries': int(d.iso.nunique()),
        'onsets_2007_2009': int(d.onset_year.between(2007,2009).sum()),
        'growth_window': 'Annual real GDP growth in onset calendar year t, t+1, t+2. Cumulative change compounds these rates relative to t-1. Descriptive, not output loss versus a counterfactual.',
        'sources_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [background, gdp_path, ROOT/'data/context/wdi_crisis_growth_source.json', DATA/'crisis_dynamics_balanced.csv', DATA/'crisis_dynamics_episodes.csv']},
    }
    (DATA / 'crisis_context_checks.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    print(f'Checked context, calendar and three annual GDP observations for {len(d)} episodes in {d.iso.nunique()} countries.')


if __name__ == '__main__':
    main()
