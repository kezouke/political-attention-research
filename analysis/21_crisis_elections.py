"""Pair crisis onsets with actual elections, and retain an auditable denominator."""

import json
import re
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pyreadr

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw'
OUT = ROOT / 'data/processed'
FIRST_ONSET, LAST_ONSET = 1990, 2015
LAST_ELECTION = pd.Timestamp('2020-12-31')
MAX_BASELINE_YEARS = 6
PRIMARY_WINDOW = 5

WPD_ALIASES = {
    'Czechia': 'CZE', 'Russia': 'RUS', 'Slovakia': 'SVK', 'Türkiye': 'TUR',
    'United States': 'USA', 'Venezuela': 'VEN',
}
IMF_ALIASES = {
    **WPD_ALIASES, 'Czech Republic': 'CZE', 'Russian Federation': 'RUS',
    'Slovak Republic': 'SVK', 'Slovak Rep': 'SVK', 'Turkey': 'TUR', 'United States of America': 'USA',
    'Venezuela, Rep. Bol. de': 'VEN',
}
# National executive elections. Ceremonial presidential races are omitted.
DIRECT_EXECUTIVE = set('ARG BOL BRA CHL COL ECU SLV IDN MEX PER PHL USA VEN'.split())
SAMPLES = ('main', 'wide_timing', 'all_regimes', 'without_2007_09')


def ppeg_file(component):
    name = f'ppeg_{component}_2025v1'
    with ZipFile(RAW / f'{name}.zip') as archive:
        return pd.read_csv(archive.open(f'{name}.csv'), low_memory=False)


def load_gdp():
    countries = json.loads((RAW / 'wdi_country_metadata.json').read_text())[1]
    names = {r['name']: r['id'] for r in countries if r['region']['id'] != 'NA'}
    rows = json.loads((RAW / 'wdi_real_gdp_growth_1978_2024.json').read_text())[1]
    growth = {(r['countryiso3code'], int(r['date'])): r['value'] for r in rows
              if r['countryiso3code'] and r['value'] is not None}
    return names, growth


def load_banks(names, countries):
    """Date to the month when known. LV table A1 flags borderline cases with 8/."""
    workbook = RAW / 'laeven_valencia_2020.xlsx'
    monthly = pd.read_excel(workbook, sheet_name='Monthly Crisis Dates', usecols=[0, 1])
    resolution = pd.read_excel(workbook, sheet_name='Crisis Resolution and Outcomes', usecols=[0, 1, 2])
    dates = {}
    for country, values in monthly.dropna().itertuples(index=False, name=None):
        for value in str(values).split(','):
            value = value.strip()
            if re.fullmatch(r'[A-Za-z]{3}-\d{2}', value):
                month = pd.to_datetime(value, format='%b-%y')
                if month.year > 2020:
                    month -= pd.DateOffset(years=100)
                dates[(country, month.year)] = month
    rows = []
    for label, year, end in resolution.dropna(subset=['Start']).itertuples(index=False, name=None):
        if not isinstance(label, str) or not isinstance(year, (int, float)):
            continue
        country = re.sub(r'\s+\d+/.*$', '', label).strip()
        iso = IMF_ALIASES.get(country, names.get(country))
        if iso not in countries:
            continue
        year = int(year)
        end_match = re.match(r'\d{4}', str(end))
        rows.append({'iso': iso, 'year': year, 'end_year': int(end_match[0]) if end_match else year,
                     'month': dates.get((country, year)), 'borderline': '8/' in label})
    frame = pd.DataFrame(rows)
    assert frame.loc[frame.iso.eq('ESP') & frame.year.eq(2008), 'month'].item() == pd.Timestamp('2008-09-01')
    assert frame.loc[frame.iso.eq('THA') & frame.year.eq(1997), 'month'].item() == pd.Timestamp('1997-07-01')
    return frame


def normalize_elections(names, parl, pres):
    source = next(iter(pyreadr.read_r(str(RAW / 'world_populism_app.rds')).values()))
    source['iso'] = source.COUNTRY.map({**names, **WPD_ALIASES})
    if source.iso.isna().any():
        raise ValueError(f'Unmapped WPD country: {source.loc[source.iso.isna(), "COUNTRY"].unique()}')
    country_info = source.dropna(subset=['REGION'])[['iso', 'COUNTRY', 'REGION']].drop_duplicates()
    assert country_info.iso.is_unique and len(country_info) == 50
    source = source[source.ROUND.eq(1) & ~source.SYSTEM.eq('Constituency seats')].copy()
    source['type'] = source.TYPE_BROAD.str.lower()
    source = source[source.type.eq('legislative') | source.iso.isin(DIRECT_EXECUTIVE)]
    source['source_date'] = pd.to_datetime(source.Date)
    # The second Bloc Québécois row is dated 2019 in the original DATE field,
    # but was assigned to 2011 by the dashboard. PPEG verifies the 2011 value.
    source = source[~(source.iso.eq('CAN') & source.source_date.eq('2011-05-02')
                      & source.PARTY.eq('Bloc Quebecois') & source.DATE.eq('21/10/2019'))]
    assert not source[source.VOTE.notna()].duplicated(['iso', 'source_date', 'type', 'PARTY', 'CANDIDATE']).any()

    official = pd.concat([
        parl[['iso3c', 'edate']].assign(type='legislative'),
        pres.loc[pres.pres_not_by_elec.eq('no') & pres.iso3c.isin(DIRECT_EXECUTIVE), ['iso3c', 'edate']]
        .assign(type='presidential'),
    ]).drop_duplicates().dropna(subset=['edate']).rename(columns={'iso3c': 'iso', 'edate': 'date'})
    official['date'] = pd.to_datetime(official.date)
    rows = []
    for (iso, kind), block in source.groupby(['iso', 'type']):
        dates = official.loc[official.iso.eq(iso) & official.type.eq(kind), 'date'].sort_values()
        for raw_date, group in block.groupby('source_date'):
            nearby = dates[(dates - raw_date).abs().dt.days.le(14)]
            date = raw_date
            if len(nearby) == 1:
                date = nearby.iloc[0]
            elif len(nearby) > 1 and raw_date not in nearby.tolist():
                raise ValueError(f'Ambiguous PPEG date for {iso} {kind} {raw_date}')
            with_vote = group.dropna(subset=['VOTE'])
            rows.append({
                'iso': iso, 'type': kind, 'date': date, 'wpd_date': raw_date,
                'vote_pct': with_vote.VOTE.sum(),
                'classified_entries': len(with_vote),
                'classified_names': ' | '.join(with_vote.CANDIDATE.fillna(with_vote.PARTY)),
                'date_status': 'matched' if date in dates.tolist() else 'wpd_only',
            })

    wpd = pd.DataFrame(rows)
    assert not wpd.duplicated(['iso', 'type', 'date']).any()
    assert wpd.vote_pct.between(0, 100).all()
    calendars = []
    for (iso, kind), block in wpd.groupby(['iso', 'type']):
        # Use PPEG to detect missing elections during WPD coverage and through
        # the fixed study end. A PPEG-only election has unknown classification.
        lo = block.date.min()
        missing = official.loc[official.iso.eq(iso) & official.type.eq(kind)
                               & official.date.between(lo, LAST_ELECTION)
                               & ~official.date.isin(block.date)]
        calendars.append(pd.concat([block, missing.assign(date_status='classification_missing')]))
    calendar = pd.concat(calendars, ignore_index=True).merge(country_info, on='iso', validate='many_to_one')
    return calendar[calendar.date.le(LAST_ELECTION)].sort_values(['iso', 'type', 'date'])


def build_events(calendar, banks, growth):
    rows = []
    for iso in sorted(calendar.iso.unique()):
        national = banks[banks.iso.eq(iso)]
        for year in range(FIRST_ONSET, LAST_ONSET + 1):
            this_year = national[national.year.eq(year)]
            if not this_year.empty:
                episode = this_year.iloc[0]
                month = episode.month
                lo = month if pd.notna(month) else pd.Timestamp(year, 1, 1)
                hi = lo + (pd.offsets.MonthEnd(0) if pd.notna(month) else pd.offsets.YearEnd(0))
                rows.append({'iso': iso, 'year': year, 'kind': 'banking', 'onset_from': lo,
                             'onset_through': hi, 'borderline': bool(episode.borderline),
                             'timing': 'month' if pd.notna(month) else 'year'})
            g = growth.get((iso, year))
            lag = growth.get((iso, year - 1))
            if g is None or lag is None or g >= 0 or lag < 0:
                continue
            # Keep bank-linked contractions out of the separate recession group.
            if (national.year.le(year + 1) & national.end_year.ge(year - 1)).any():
                continue
            rows.append({'iso': iso, 'year': year, 'kind': 'recession',
                         'onset_from': pd.Timestamp(year, 1, 1), 'onset_through': pd.Timestamp(year, 12, 31),
                         'borderline': False, 'timing': 'year'})
    events = pd.DataFrame(rows)
    events['gdp_growth_pct'] = [growth.get((r.iso, r.year)) for r in events.itertuples()]
    return events.sort_values(['iso', 'year', 'kind'])


def incumbent_change(iso, pre, post, parliament, cabinet):
    """Follow the head of government’s party immediately before the election."""
    prior = cabinet[cabinet.iso3c.eq(iso) & cabinet.idate.lt(post)]
    if prior.empty:
        return {}
    party = prior.loc[prior.idate.eq(prior.idate.max()) & prior.pm_party.eq('yes'), ['party_id', 'pname_en']].drop_duplicates()
    if len(party) != 1:
        return {}
    party_id, name = party.iloc[0]
    votes = parliament[parliament.iso3c.eq(iso) & parliament.party_id.eq(party_id)]
    before = votes.loc[votes.edate.eq(pre), 'v_share_wgt'].dropna().unique()
    after = votes.loc[votes.edate.eq(post), 'v_share_wgt'].dropna().unique()
    if len(before) != 1 or len(after) != 1:
        return {}
    return {'pm_party': name, 'pm_pre_pct': 100 * before[0], 'pm_post_pct': 100 * after[0],
            'pm_change_pp': 100 * (after[0] - before[0])}


def compare(pair, before, after, parliament, cabinet):
    for label, election in [('pre', before), ('post', after)]:
        if election is not None:
            pair.update({f'{label}_date': election.date, f'{label}_vote_pct': election.vote_pct,
                         f'{label}_entries': election.classified_entries,
                         f'{label}_names': election.classified_names,
                         f'{label}_date_status': election.date_status,
                         f'{label}_regime': election.regime})
    if before is None or after is None:
        pair['status'] = 'no_pre_election' if before is None else 'no_post_election'
        return pair
    if pd.isna(before.vote_pct) or pd.isna(after.vote_pct):
        pair['status'] = 'classification_missing'
        return pair
    pair.update(status='paired', change_pp=after.vote_pct - before.vote_pct)
    if pair['type'] == 'legislative':
        pair.update(incumbent_change(pair['iso'], before.date, after.date, parliament, cabinet))
        post_rows = parliament[parliament.iso3c.eq(pair['iso']) & parliament.edate.eq(after.date)]
        pre_rows = parliament[parliament.iso3c.eq(pair['iso']) & parliament.edate.eq(before.date)]
        for label, rows in [('pre', pre_rows), ('post', post_rows)]:
            if not rows.empty:
                total, eligible = rows.iloc[0][['total_vote', 'electorate']]
                if pd.notna(total) and pd.notna(eligible) and eligible > 0:
                    pair[f'{label}_turnout_pct'] = 100 * total / eligible
    return pair


def pair_events(calendar, events, parliament, cabinet):
    rows = []
    metadata = calendar[['iso', 'COUNTRY', 'REGION']].drop_duplicates().set_index('iso')
    for event in events.itertuples(index=False):
        subsets = calendar[calendar.iso.eq(event.iso)].groupby('type')
        for kind, elections in subsets:
            # Include gaps after the beginning of each country's election series.
            if elections.date.min() > event.onset_through:
                continue
            preceding = elections[elections.date.lt(event.onset_from)
                                  & elections.date.ge(event.onset_from - pd.DateOffset(years=MAX_BASELINE_YEARS))]
            for window in [3, PRIMARY_WINDOW]:
                following = elections[elections.date.gt(event.onset_through)
                                      & elections.date.le(event.onset_through + pd.DateOffset(years=window))]
                before = preceding.iloc[-1] if len(preceding) else None
                after = following.iloc[0] if len(following) else None
                pair = dict(event._asdict(), country=metadata.at[event.iso, 'COUNTRY'],
                            region=metadata.at[event.iso, 'REGION'], type=kind, window_years=window,
                            ambiguous_election=bool(elections.date.between(event.onset_from, event.onset_through).any()))
                rows.append(compare(pair, before, after, parliament, cabinet))
    return pd.DataFrame(rows)


def control_pairs(calendar, banks, growth, parliament, cabinet):
    """Same-country consecutive pairs with nonnegative observed intervening GDP."""
    rows = []
    for (iso, kind), elections in calendar.groupby(['iso', 'type']):
        national = banks[banks.iso.eq(iso)]
        observed = list(elections.itertuples())
        for before, after in zip(observed, observed[1:]):
            if not FIRST_ONSET <= before.date.year <= LAST_ONSET:
                continue
            if after.date > before.date + pd.DateOffset(years=MAX_BASELINE_YEARS):
                continue
            if (national.year.le(after.date.year) & national.end_year.ge(before.date.year)).any():
                continue
            values = [growth.get((iso, year)) for year in range(before.date.year, after.date.year + 1)]
            if any(value is None or value < 0 for value in values):
                continue
            row = {'iso': iso, 'country': after.COUNTRY, 'region': after.REGION,
                   'type': kind, 'kind': 'comparison'}
            rows.append(compare(row, before, after, parliament, cabinet))
    return pd.DataFrame(rows)


def competitive(frame):
    """V-Dem Regimes of the World codes 2 and 3 denote electoral and liberal democracies."""
    return frame.pre_regime.ge(2) & frame.post_regime.ge(2)


def add_regimes(calendar):
    regimes = next(iter(pyreadr.read_r(str(RAW / 'vdem.RData')).values()))
    regimes = regimes[['country_text_id', 'year', 'v2x_regime']].rename(
        columns={'country_text_id': 'iso', 'v2x_regime': 'regime'})
    return (calendar.assign(year=calendar.date.dt.year)
            .merge(regimes, on=['iso', 'year'], how='left', validate='many_to_one')
            .drop(columns='year'))


def independent_scale(pairs, controls):
    """A continuous, vote-weighted V-Party check for the same legislative elections."""
    parties = next(iter(pyreadr.read_r(str(RAW / 'vparty.RData')).values()))
    columns = ['country_text_id', 'historical_date', 'v2pavote', 'v2xpa_popul']
    parties = parties[columns].dropna().rename(columns={'country_text_id': 'iso'})
    parties['date'] = pd.to_datetime(parties.historical_date)
    parties['weighted'] = parties.v2pavote * parties.v2xpa_popul
    indexed = parties.groupby(['iso', 'date']).agg(votes=('v2pavote', 'sum'), weighted=('weighted', 'sum'))
    indexed = indexed[indexed.votes.between(75, 101)]
    indexed['score'] = indexed.weighted / indexed.votes

    def merge_scores(data):
        for label in ['pre', 'post']:
            fields = indexed[['votes', 'score']].rename(
                columns={'votes': f'{label}_score_coverage_pct', 'score': f'{label}_score'})
            data = data.merge(fields, left_on=['iso', f'{label}_date'],
                              right_index=True, how='left', validate='many_to_one')
        score_columns = ['pre_score', 'post_score', 'pre_score_coverage_pct', 'post_score_coverage_pct']
        data.loc[data.type.ne('legislative'), score_columns] = float('nan')
        data['score_change'] = data.post_score - data.pre_score
        return data

    return merge_scores(pairs), merge_scores(controls)


def summarize(pairs, controls):
    base = pairs[pairs.status.eq('paired') & ~pairs.borderline]
    comparator = controls[controls.status.eq('paired')]
    summaries = []
    for sample in SAMPLES:
        selected_sample = base
        comparison_sample = comparator
        if sample != 'all_regimes':
            selected_sample = selected_sample[competitive(selected_sample)]
            comparison_sample = comparison_sample[competitive(comparison_sample)]
        if sample != 'wide_timing':
            selected_sample = selected_sample[~selected_sample.ambiguous_election]
        if sample == 'without_2007_09':
            selected_sample = selected_sample[~selected_sample.year.between(2007, 2009)]
            comparison_sample = comparison_sample[
                ~(comparison_sample.pre_date.dt.year.le(2009) & comparison_sample.post_date.dt.year.ge(2007))]
        for window in [3, PRIMARY_WINDOW]:
            selected = selected_sample[selected_sample.window_years.eq(window)]
            for kind, panel in selected.groupby('type'):
                bench = comparison_sample[comparison_sample.type.eq(kind) & comparison_sample.iso.isin(panel.iso)]
                for label, data in [*panel.groupby('kind'), ('comparison', bench)]:
                    if data.empty:
                        continue
                    change = data.change_pp
                    matched = data[data.pm_change_pp.notna()]
                    scores = data[data.score_change.notna()] if kind == 'legislative' else data.iloc[:0]
                    summaries.append({
                        'sample': sample, 'window_years': window, 'type': kind, 'kind': label,
                        'n': len(data), 'countries': data.iso.nunique(),
                        'increased': int(change.gt(.00001).sum()), 'decreased': int(change.lt(-.00001).sum()),
                        'unchanged': int(change.abs().le(.00001).sum()), 'up_over_1pp': int(change.gt(1).sum()),
                        'median_pp': change.median(), 'mean_pp': change.mean(),
                        'q25_pp': change.quantile(.25), 'q75_pp': change.quantile(.75),
                        'min_pp': change.min(), 'max_pp': change.max(),
                        'pm_n': len(matched), 'pm_down': int(matched.pm_change_pp.lt(0).sum()),
                        'pm_down_pop_up': int((matched.pm_change_pp.lt(0) & matched.change_pp.gt(.00001)).sum()),
                        'pm_median_pp': matched.pm_change_pp.median(),
                        'vparty_n': len(scores), 'vparty_median_change': scores.score_change.median(),
                    })
    return pd.DataFrame(summaries)


def price_episode(parliament):
    """Link SPES to identifiable election-year series from The PopuList."""
    prices = pd.read_csv(OUT / 'common_shock_2021_2022_countries.csv')
    vote = pd.read_csv(RAW / 'populist_4_country_elections.csv').set_index(['country_code', 'year'])
    rows = []
    for row in prices.itertuples(index=False):
        item = row._asdict()
        dates = parliament.loc[parliament.iso3c.eq(row.iso), 'edate'].dropna().drop_duplicates().sort_values()
        pre = dates[dates.dt.year.lt(2022)]
        post = dates[dates.dt.year.gt(2022) & dates.dt.year.le(2025)]
        before = pre.iloc[-1] if len(pre) else None
        after = post.iloc[0] if len(post) else None
        item.update(pre_date=before, post_date=after, status='paired')
        if row.iso not in vote.index.get_level_values(0):
            item['status'] = 'not_classified'
        elif before is None or after is None:
            item['status'] = 'no_election_in_window'
        elif dates.dt.year.eq(2022).any():
            item['status'] = 'election_during_shock_year'
        elif dates.dt.year.eq(before.year).sum() != 1 or dates.dt.year.eq(after.year).sum() != 1:
            item['status'] = 'multiple_elections_in_endpoint_year'
        else:
            a = vote['c2_populist_votes'].get((row.iso, before.year))
            b = vote['c2_populist_votes'].get((row.iso, after.year))
            if pd.isna(a) or pd.isna(b):
                item['status'] = 'missing_vote_share'
            else:
                item.update(pre_vote_pct=a, post_vote_pct=b, vote_change_pp=b - a)
        rows.append(item)
    return pd.DataFrame(rows)


def main():
    names, growth = load_gdp()
    parliament, president, cabinet = [ppeg_file(key) for key in ['parl', 'pres', 'comb']]
    for frame in [parliament, president, cabinet]:
        frame['edate'] = pd.to_datetime(frame.edate)
    cabinet['idate'] = pd.to_datetime(cabinet.idate)
    calendar = add_regimes(normalize_elections(names, parliament, president))
    banks = load_banks(names, set(calendar.iso))
    events = build_events(calendar, banks, growth)
    pairs = pair_events(calendar, events, parliament, cabinet)
    controls = control_pairs(calendar, banks, growth, parliament, cabinet)
    pairs, controls = independent_scale(pairs, controls)
    summary = summarize(pairs, controls)
    price = price_episode(parliament)
    for table, name in [(calendar, 'crisis_election_calendar'), (pairs, 'crisis_election_pairs'),
                        (controls, 'crisis_election_controls'), (summary, 'crisis_election_summary'),
                        (price, 'price_shock_election_check')]:
        table.to_csv(OUT / f'{name}.csv', index=False, float_format='%.8g')
    print(summary[summary["sample"].eq("main")].round(3).to_string(index=False))


if __name__ == '__main__':
    main()
