"""Balanced election-order trajectories. Descriptive, not an event-study effect."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed'
spec = importlib.util.spec_from_file_location('crisis', ROOT / 'analysis/21_crisis_elections.py')
crisis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crisis)


def primary_pairs():
    pairs = pd.read_csv(OUT / 'crisis_election_pairs.csv', parse_dates=['pre_date', 'post_date', 'onset_from', 'onset_through'])
    return pairs[pairs.type.eq('legislative') & pairs.kind.eq('banking')
                 & pairs.window_years.eq(5) & pairs.status.eq('paired')
                 & ~pairs.borderline & ~pairs.ambiguous_election
                 & pairs.pre_regime.ge(2) & pairs.post_regime.ge(2)].copy()


def build_trajectories(pairs, calendar, banks):
    rows = []
    for event in pairs.itertuples():
        elections = calendar[calendar.iso.eq(event.iso) & calendar.type.eq('legislative')].sort_values('date')
        before = elections[elections.date.lt(event.pre_date)]
        after = elections[elections.date.gt(event.onset_through)]
        subsequent = banks[banks.iso.eq(event.iso) & banks.year.gt(event.year)]
        for rank in [-1, 0, 1, 2, 3]:
            chosen = (before.tail(1) if rank == -1 else elections[elections.date.eq(event.pre_date)]
                      if rank == 0 else after.iloc[rank - 1:rank])
            row = dict(iso=event.iso, country=event.country, onset_year=event.year,
                       baseline_date=event.pre_date, rank=rank, status='no_election')
            if len(chosen):
                e = chosen.iloc[0]
                years = (e.date - event.onset_through).days / 365.25
                intervening = bool((subsequent.year <= e.date.year).any())
                status = ('classification_missing' if pd.isna(e.vote_pct) else
                          'not_democratic' if pd.isna(e.regime) or e.regime < 2 else
                          'outside_ten_years' if years > 10 else
                          'subsequent_banking_crisis' if intervening else 'included')
                if rank == -1 and (event.pre_date - e.date).days > 6 * 365.25:
                    status = 'baseline_gap_over_six_years'
                row.update(date=e.date, years_from_onset=years, vote_pct=e.vote_pct,
                           change_pp=e.vote_pct - event.pre_vote_pct, regime=e.regime,
                           subsequent_crisis=intervening, status=status)
            rows.append(row)
    return pd.DataFrame(rows)


def main():
    pairs = primary_pairs()
    calendar = pd.read_csv(OUT / 'crisis_election_calendar.csv', parse_dates=['date'])
    names, _ = crisis.load_gdp()
    banks = crisis.load_banks(names, set(calendar.iso))
    trajectories = build_trajectories(pairs, calendar, banks)
    trajectories.to_csv(OUT / 'crisis_dynamics_episodes.csv', index=False, float_format='%.8g')
    first = trajectories[trajectories['rank'].eq(1)].set_index(['iso', 'onset_year'])
    second = trajectories[trajectories['rank'].eq(2)].set_index(['iso', 'onset_year'])
    good = second.index[second.status.eq('included') & first.status.eq('included')]
    summaries = []
    for sample, keys in [('balanced_two', good),
                         ('balanced_two_no_2007_09', good[~good.get_level_values(1).isin([2007, 2008, 2009])])]:
        for rank in [1, 2]:
            q = trajectories[trajectories['rank'].eq(rank)].set_index(['iso', 'onset_year']).loc[keys]
            d = q.change_pp
            summaries.append(dict(sample=sample, rank=rank, n=len(q), countries=q.reset_index().iso.nunique(),
                                  mean_pp=d.mean(), median_pp=d.median(), increases=int((d > 1e-5).sum()),
                                  q25_pp=d.quantile(.25), q75_pp=d.quantile(.75),
                                  median_years=q.years_from_onset.median()))
    balanced = first.loc[good, ['country', 'date', 'change_pp']].join(
        second.loc[good, ['date', 'change_pp', 'years_from_onset']], lsuffix='_first', rsuffix='_second')
    balanced['additional_pp'] = balanced.change_pp_second - balanced.change_pp_first
    balanced.to_csv(OUT / 'crisis_dynamics_balanced.csv', float_format='%.8g')
    pd.DataFrame(summaries).to_csv(OUT / 'crisis_dynamics_summary.csv', index=False, float_format='%.8g')
    print(pd.DataFrame(summaries).round(3).to_string(index=False))
    print('Second-election exclusions:', second.status.value_counts().to_dict())
    print('Additional change:', balanced.additional_pp.describe().round(3).to_dict())


if __name__ == '__main__':
    main()
