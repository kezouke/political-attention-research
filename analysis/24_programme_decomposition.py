"""Exact programme/vote decomposition with an explicit coverage audit.

No row-level Manifesto Project data are redistributed. The roster term is not
called new-party entry: it includes missing documents and changed party IDs.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed'
TOPICS = {
    'economy': list(range(401, 416)),
    'material_broad': list(range(401, 416)) + list(range(503, 508)) + list(range(701, 705)),
    'anticorruption': [304], 'environment': [501],
    'culture_broad': [601, 603, 604, 605, 606, 607, 608, 705],
    'market': [401, 414], 'planning': [403, 404, 412],
    'demand': [409], 'orthodoxy': [414], 'welfare_expansion': [504],
}
ALIASES = {'Türkiye': 'Turkey', 'Czechia': 'Czech Republic'}
SPECS = ['main', 'coverage60', 'coverage90', 'single_party', 'same_manual', 'observed_votes', 'include_estimates']


def load_documents():
    d = pd.read_csv(ROOT / 'data/raw/manifesto_2023a.csv', low_memory=False)
    cols = sorted({f'per{i}' for ids in TOPICS.values() for i in ids})
    d = d[d.pervote.gt(0) & d.total.gt(0) & d[cols].notna().all(axis=1)].copy()
    for name, codes in TOPICS.items():
        d[name] = d[[f'per{i}' for i in codes]].sum(axis=1)
    assert not d.duplicated(['countryname', 'date', 'party']).any()
    return d


def candidate_pairs():
    p = pd.read_csv(OUT / 'crisis_election_pairs.csv', parse_dates=['pre_date', 'post_date'])
    p = p[p.type.eq('legislative') & p.window_years.eq(5) & p.status.eq('paired')
          & ~p.borderline & ~p.ambiguous_election & p.pre_regime.ge(2) & p.post_regime.ge(2)].copy()
    p['pair_id'] = p.iso + '_' + p.year.astype(str) + '_' + p.kind
    controls = pd.read_csv(OUT / 'crisis_election_controls.csv', parse_dates=['pre_date', 'post_date'])
    controls = controls[controls.type.eq('legislative') & controls.status.eq('paired')
                        & controls.pre_regime.ge(2) & controls.post_regime.ge(2) & controls.iso.isin(p.iso)].copy()
    controls['pair_id'] = controls.iso + '_' + controls.pre_date.dt.strftime('%Y%m') + '_calm'
    controls['year'] = controls.post_date.dt.year
    calendar = pd.read_csv(OUT / 'crisis_election_calendar.csv', parse_dates=['date'])
    preceding = []
    for e in p[p.kind.eq('banking')].itertuples():
        prev = calendar[calendar.iso.eq(e.iso) & calendar.type.eq('legislative') & calendar.date.lt(e.pre_date)].tail(1)
        if prev.empty or pd.isna(prev.iloc[0].regime) or prev.iloc[0].regime < 2 or (e.pre_date - prev.iloc[0].date).days > 6 * 365.25:
            continue
        r = e._asdict()
        r.update(pair_id=e.pair_id + '_prior', kind='prior', post_date=e.pre_date,
                 pre_date=prev.iloc[0].date, change_pp=e.pre_vote_pct - prev.iloc[0].vote_pct)
        preceding.append(r)
    # Second-election interval is a continuation of the same original episode.
    second = pd.read_csv(OUT / 'crisis_dynamics_balanced.csv', parse_dates=['date_first', 'date_second'])
    for e in second.itertuples():
        preceding.append(dict(iso=e.iso, country=e.country, year=e.onset_year, kind='second',
                              pair_id=f'{e.iso}_{e.onset_year}_second', pre_date=e.date_first,
                              post_date=e.date_second, change_pp=e.additional_pp))
    return pd.concat([p, controls, pd.DataFrame(preceding)], ignore_index=True)


def decomposition(a, b, topic, normalise=True):
    """Shapley/midpoint identity. One-sided records have a separate roster term."""
    a, b = a.set_index('party'), b.set_index('party')
    va = a.pervote / (a.pervote.sum() if normalise else 100)
    vb = b.pervote / (b.pervote.sum() if normalise else 100)
    common = a.index.intersection(b.index)
    first = float((va * a[topic]).sum())
    last = float((vb * b[topic]).sum())
    within = float((((va.loc[common] + vb.loc[common]) / 2) * (b.loc[common, topic] - a.loc[common, topic])).sum())
    between = float((((a.loc[common, topic] + b.loc[common, topic]) / 2) * (vb.loc[common] - va.loc[common])).sum())
    entered = b.index.difference(a.index)
    left = a.index.difference(b.index)
    roster = float((vb.loc[entered] * b.loc[entered, topic]).sum() - (va.loc[left] * a.loc[left, topic]).sum())
    assert np.isclose(last - first, within + between + roster, atol=1e-8)
    return dict(pre_share=first, post_share=last, change_pp=last-first,
                within_pp=within, reweight_pp=between, roster_pp=roster)


def analyse_pair(e, documents, sample):
    name = ALIASES.get(e.country, e.country)
    source = documents[documents.countryname.eq(name)]
    types = [1] if sample == 'single_party' else ([1, 2, 3, 8] if sample == 'include_estimates' else [1, 2, 8])
    source = source[source.progtype.isin(types)]
    if sample == 'observed_votes':
        source = source[source.voteest.eq(0)]
    a = source[source.date.eq(int(e.pre_date.strftime('%Y%m')))].copy()
    b = source[source.date.eq(int(e.post_date.strftime('%Y%m')))].copy()
    if sample == 'same_manual':
        match = a[['party', 'manual']].merge(b[['party', 'manual']], on='party', suffixes=('_a', '_b'))
        ids = match.loc[match.manual_a.eq(match.manual_b) & match.manual_a.between(1, 5), 'party']
        a, b = a[a.party.isin(ids)], b[b.party.isin(ids)]
    coverage_a, coverage_b = a.pervote.sum(), b.pervote.sum()
    threshold = 60 if sample == 'coverage60' else 90 if sample == 'coverage90' else 75
    ids = set(a.party) & set(b.party)
    common_a, common_b = a[a.party.isin(ids)], b[b.party.isin(ids)]
    manual = common_a[['party', 'manual', 'coderid']].merge(common_b[['party', 'manual', 'coderid']], on='party', suffixes=('_a', '_b'))
    status = ('missing_endpoint' if a.empty or b.empty else
              'overlapping_votes' if max(coverage_a, coverage_b) > 101 else
              'low_coverage' if min(coverage_a, coverage_b) < threshold else 'included')
    meta = dict(pair_id=e.pair_id, sample=sample, iso=e.iso, country=e.country, onset_year=e.year,
                kind=e.kind, pre_date=e.pre_date, post_date=e.post_date,
                duration_years=(e.post_date-e.pre_date).days/365.25,
                pre_coverage=coverage_a, post_coverage=coverage_b,
                n_pre=len(a), n_post=len(b), n_common=len(ids),
                common_pre_coverage=common_a.pervote.sum(), common_post_coverage=common_b.pervote.sum(),
                manual_changes=int(manual.manual_a.ne(manual.manual_b).sum()),
                coder_changes=int(manual.coderid_a.ne(manual.coderid_b).sum()),
                status=status, populist_change_pp=e.change_pp)
    results = []
    if status == 'included':
        for topic in TOPICS:
            row = dict(meta, topic=topic, **decomposition(a, b, topic))
            row.update({f'raw_{k}': v for k, v in decomposition(a, b, topic, False).items()})
            if len(ids):
                row.update({f'common_{k}': v for k, v in decomposition(common_a, common_b, topic).items()})
            # Worst-case missing-document bounds; no sampling uncertainty implied.
            row['missing_lower_change'] = coverage_b / 100 * row['post_share'] - (coverage_a / 100 * row['pre_share'] + 100-coverage_a)
            row['missing_upper_change'] = coverage_b / 100 * row['post_share'] + 100-coverage_b - coverage_a / 100 * row['pre_share']
            results.append(row)
    return meta, results


def summarize(results):
    rows = []
    for (sample, kind, topic), q in results.groupby(['sample', 'kind', 'topic']):
        common = q[q.common_pre_coverage.ge(50) & q.common_post_coverage.ge(50)]
        row = dict(sample=sample, kind=kind, topic=topic, n=len(q), countries=q.iso.nunique(),
                   mean_change=q.change_pp.mean(), median_change=q.change_pp.median(),
                   mean_within=q.within_pp.mean(), mean_reweight=q.reweight_pp.mean(), mean_roster=q.roster_pp.mean(),
                   within_largest=int((q.within_pp.abs() > q[['reweight_pp','roster_pp']].abs().max(axis=1)).sum()),
                   mean_abs_within=q.within_pp.abs().mean(), mean_abs_reweight=q.reweight_pp.abs().mean(),
                   mean_abs_roster=q.roster_pp.abs().mean(), common_n=len(common),
                   common_within_larger=int((common.common_within_pp.abs() > common.common_reweight_pp.abs()).sum()),
                   mean_common_within=common.common_within_pp.mean(), mean_common_reweight=common.common_reweight_pp.mean(),
                   n_unchanged_manual=int(q.manual_changes.eq(0).sum()))
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    docs = load_documents()
    pairs = candidate_pairs()
    audit, rows = [], []
    for e in pairs.itertuples():
        for sample in SPECS:
            meta, results = analyse_pair(e, docs, sample)
            audit.append(meta); rows.extend(results)
    audit, results = pd.DataFrame(audit), pd.DataFrame(rows)
    summary = summarize(results)
    for frame, name in [(audit,'programme_coverage'),(results,'programme_decomposition'),(summary,'programme_summary')]:
        frame.to_csv(OUT/f'{name}.csv',index=False,float_format='%.8g')
    provenance = {'source': 'Manifesto Project 2023a', 'sha256': hashlib.sha256((ROOT/'data/raw/manifesto_2023a.csv').read_bytes()).hexdigest(),
                  'topics': TOPICS, 'specifications': SPECS, 'raw_rows_redistributed': False}
    (OUT/'programme_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(summary[summary['sample'].eq('main') & summary.topic.isin(['economy','anticorruption','environment'])].round(3).to_string(index=False))
    print('Banking main coverage:',audit[audit['sample'].eq('main') & audit.kind.eq('banking')].status.value_counts().to_dict())


if __name__ == '__main__':
    main()
