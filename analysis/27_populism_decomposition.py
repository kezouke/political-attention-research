"""Independent continuous populism measure; descriptive accounting only."""
import importlib.util
from pathlib import Path
import pandas as pd
import pyreadr
from scipy.stats import spearmanr

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/processed'
spec=importlib.util.spec_from_file_location('programmes',ROOT/'analysis/24_programme_decomposition.py')
programmes=importlib.util.module_from_spec(spec);spec.loader.exec_module(programmes)


def main():
    v=next(iter(pyreadr.read_r(str(ROOT/'data/raw/vparty.RData')).values()))
    v=v.rename(columns={'country_text_id':'iso','v2paid':'party','v2pavote':'pervote'})
    v['date']=pd.to_datetime(v.historical_date)
    v['populism']=100*v.v2xpa_popul
    v=v[v.pervote.gt(0)&v.populism.notna()]
    assert not v.duplicated(['iso','date','party']).any()
    rows=[];coverage=[]
    for e in programmes.candidate_pairs().itertuples():
        a=v[v.iso.eq(e.iso)&v.date.eq(e.pre_date)]
        b=v[v.iso.eq(e.iso)&v.date.eq(e.post_date)]
        ca,cb=a.pervote.sum(),b.pervote.sum()
        meta=dict(pair_id=e.pair_id,iso=e.iso,kind=e.kind,country=e.country,onset_year=e.year,
                  pre_date=e.pre_date,post_date=e.post_date,pre_coverage=ca,post_coverage=cb,
                  wpd_change_pp=e.change_pp,status='included' if 75<=ca<=101 and 75<=cb<=101 else 'coverage')
        coverage.append(meta)
        if meta['status']!='included':continue
        row=dict(meta,**programmes.decomposition(a,b,'populism'))
        ids=set(a.party)&set(b.party);aa=a[a.party.isin(ids)];bb=b[b.party.isin(ids)]
        row.update(common_pre_coverage=aa.pervote.sum(),common_post_coverage=bb.pervote.sum())
        if len(ids):row.update({f'common_{k}':val for k,val in programmes.decomposition(aa,bb,'populism').items()})
        rows.append(row)
    out=pd.DataFrame(rows)
    out.to_csv(OUT/'populism_decomposition.csv',index=False,float_format='%.8g')
    pd.DataFrame(coverage).to_csv(OUT/'populism_coverage.csv',index=False,float_format='%.8g')
    summaries=[]
    for kind,q in out.groupby('kind'):
        summaries.append(dict(kind=kind,n=len(q),countries=q.iso.nunique(),mean_change=q.change_pp.mean(),median_change=q.change_pp.median(),
                              mean_within=q.within_pp.mean(),mean_reweight=q.reweight_pp.mean(),mean_roster=q.roster_pp.mean(),
                              wpd_spearman=spearmanr(q.change_pp,q.wpd_change_pp).statistic))
    pd.DataFrame(summaries).to_csv(OUT/'populism_decomposition_summary.csv',index=False,float_format='%.8g')
    balanced=out[out.kind.eq('banking')].merge(out[out.kind.eq('second')],on=['iso','onset_year'],suffixes=('_first','_second'))
    balanced['cumulative_second_change']=balanced.change_pp_first+balanced.change_pp_second
    balanced[['iso','onset_year','change_pp_first','cumulative_second_change']].to_csv(OUT/'populism_balanced_horizon.csv',index=False,float_format='%.8g')
    print(pd.DataFrame(summaries).round(3).to_string(index=False))


if __name__=='__main__':main()
