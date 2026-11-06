"""Count actual CSES measurement coverage without estimating political outcomes.

The output contains study-level counts only. Structural absence of a question is
distinct from item nonresponse. Dates and question meanings come from codebooks.
No country-specific important-problem code is harmonised in this audit.
"""
from pathlib import Path
import json
import re
import zipfile
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw/audit_20261106'
OUT=ROOT/'data/processed/audit_20261106'
EUROPE=set('AL AT BE BG HR CY CZ DK EE FI FR DE GR HU IS IE IT LV LT LU MT ME NL NO PL PT RO RS SK SI ES SE CH GB XK'.split())
# These ranges exclude source special values, not politically inconvenient cases.
SPECS={
 2:{'B3009':('mip_national',1,901),'B3010':('government_mip_performance',1,4),
    'B3011':('government_performance',1,4),'B3012':('democracy_satisfaction',1,4),
    'B3013':('power_makes_difference',1,5),'B3014':('vote_makes_difference',1,5),
    'B3044':('perceived_corruption',1,4)},
 3:{'C3001_1':('mip_personal_first',1,901),'C3001_2':('mip_personal_second',1,901),
    'C3002_1':('mip_national',1,901),'C3002_2':('mip_national_second',1,901),
    'C3006':('government_performance',1,4),'C3019':('democracy_satisfaction',1,4),
    'C3004':('power_makes_difference',1,5),'C3005':('vote_makes_difference',1,5)},
 4:{'D3003_1':('national_economy_retrospective',1,3),
    'D3002':('standard_of_living_future_10_years',1,5),
    'D3017':('democracy_satisfaction',1,4),
    'D3009':('power_makes_difference',1,5),'D3010':('vote_makes_difference',1,5)},
 5:{'E3011':('national_economy_retrospective',1,5),'E3009':('government_performance',1,4),
    'E3004_2':('elites_do_not_care',1,5),'E3004_3':('elites_trustworthy',1,5),
    'E3004_4':('politicians_main_problem',1,5),'E3004_7':('elites_rich_powerful',1,5),
    'E3023':('democracy_satisfaction',1,4),
    'E3016_1':('power_makes_difference',1,5),'E3016_2':('vote_makes_difference',1,5)}
}

def csv_read(name,columns):
    with zipfile.ZipFile(RAW/(name+'_csv.zip')) as z:
        filename=next(n for n in z.namelist() if n.endswith('.csv'))
        return pd.read_csv(z.open(filename),usecols=lambda c:c in columns,
                           dtype={c:'string' for c in columns if c.endswith('1005')},low_memory=False)

def main():
    columns=['IMD1003','IMD1004','IMD1005','IMD1006_UNALPHA2','IMD1006_UNALPHA3','IMD1006_NAM',
        'IMD1008_YEAR','IMD1009','IMD1011_1','IMD1011_2','IMD1013_Y','IMD1013_M',
        'IMD1014_1','IMD1010_1','IMD1010_2','IMD1010_3','IMD3002_LH_PL','IMD3002_LH_DC',
        'IMD3002_OUTGOV','IMD3013_1','IMD2006']+[f'IMD1008_MOD_{i}' for i in range(1,6)]
    imd=csv_read('cses_imd',columns)
    assert not imd.IMD1005.duplicated().any()
    imd=imd[imd.IMD1006_UNALPHA2.isin(EUROPE)&imd.IMD1008_YEAR.between(2004,2019)].copy()
    meta_cols=['IMD1003','IMD1004','IMD1006_UNALPHA2','IMD1006_UNALPHA3','IMD1006_NAM','IMD1008_YEAR','IMD1009','IMD1011_1','IMD1011_2']
    coverage=[]
    for key,g in imd.groupby('IMD1003',sort=True):
        row={k:g[k].iloc[0] for k in meta_cols}
        row.update(n=len(g),n_named_lower_house_vote=int((g.IMD3002_LH_PL.between(1,9000000)|g.IMD3002_LH_DC.between(1,9000000)).sum()),
                   n_incumbent_vote_flag=int(g.IMD3002_OUTGOV.isin([0,1]).sum()),
                   n_income_quintile=int(g.IMD2006.between(1,5).sum()))
        timing=g.IMD1014_1.where(g.IMD1014_1.between(-1000,3000))
        row.update(n_known_interview_lag=int(timing.notna().sum()),n_pre_election=int(timing.lt(0).sum()),
                   interview_lag_median_days=timing.median(),interview_lag_min_days=timing.min(),interview_lag_max_days=timing.max())
        for j in range(1,6):row[f'module{j}_n']=int(g[f'IMD1008_MOD_{j}'].eq(1).sum())
        coverage.append(row)
    pd.DataFrame(coverage).to_csv(OUT/'cses_study_coverage.csv',index=False)
    rows=[];joint=[];variables=[]
    for mod,spec in SPECS.items():
        prefix='ABCDE'[mod-1]
        cols=[prefix+'1005',prefix+'1004',*spec]
        d=csv_read(f'cses{mod}',cols).rename(columns={prefix+'1005':'IMD1005'})
        assert not d.IMD1005.duplicated().any()
        d=d.merge(imd,on='IMD1005',how='inner',validate='one_to_one')
        book=(RAW/f'cses{mod}_codebook_part2_variables.txt').read_text(errors='replace')
        for var,(concept,lo,hi) in spec.items():
            assert var in d,var
            match=re.search(r'^\s*'+re.escape(var)+r'\s+>>>\s+([^\n]+)',book,re.M)
            allowed=[1,2,4,5] if var=='D3002' else list(range(lo,hi+1))
            variables.append({'module':mod,'variable':var,'concept':concept,'valid_min':lo,'valid_max':hi,
                              'valid_values':json.dumps(allowed) if var=='D3002' else f'{lo} through {hi}',
                              'source_label_first_line':match[1].strip() if match else '',
                              'codebook_file':f'cses{mod}_codebook_part2_variables.txt'})
            d['valid_'+concept]=d[var].isin(allowed)
            for study,g in d.groupby('IMD1004'):
                rows.append({'module':mod,'study':study,'country':g.IMD1006_UNALPHA2.iloc[0],
                             'election_year':g.IMD1008_YEAR.iloc[0],'variable':var,'concept':concept,
                             'n':len(g),'valid_n':int(g['valid_'+concept].sum()),
                             'valid_pct':100*g['valid_'+concept].mean()})
        for study,g in d.groupby('IMD1004'):
            v=g.IMD3002_LH_PL.between(1,9000000)|g.IMD3002_LH_DC.between(1,9000000)
            conditions={name: g['valid_'+name] if 'valid_'+name in g else pd.Series(False,index=g.index)
                        for name in ['mip_national','national_economy_retrospective','elites_trustworthy','government_performance','perceived_corruption']}
            row={'module':mod,'study':study,'country':g.IMD1006_UNALPHA2.iloc[0],'n':len(g),
                 'n_vote_and_mip':int((v&conditions['mip_national']).sum()),
                 'n_vote_and_economy':int((v&conditions['national_economy_retrospective']).sum()),
                 'n_vote_economy_and_elite_trust':int((v&conditions['national_economy_retrospective']&conditions['elites_trustworthy']).sum()),
                 'n_vote_mip_and_corruption':int((v&conditions['mip_national']&conditions['perceived_corruption']).sum()),
                 'n_vote_economy_mip_elite_trust':int((v&conditions['national_economy_retrospective']&conditions['mip_national']&conditions['elites_trustworthy']).sum())}
            joint.append(row)
        print('module',mod,'matched rows',len(d),'studies',d.IMD1004.nunique())
    pd.DataFrame(rows).to_csv(OUT/'cses_variable_coverage.csv',index=False)
    pd.DataFrame(variables).to_csv(OUT/'cses_audited_variables.csv',index=False)
    pd.DataFrame(joint).to_csv(OUT/'cses_joint_coverage.csv',index=False)
    # Exact dates prevent accidental matches to another election in the same year.
    # No fuzzy match or substitution of an adjacent election is made here.
    events=pd.read_csv(ROOT/'data/processed/crisis_dynamics_episodes.csv')
    events=events[events.onset_year.between(2007,2009)&events['rank'].isin([0,1,2])&events.iso.ne('USA')]
    matched=events.merge(pd.DataFrame(coverage),left_on=['iso','date'],
                         right_on=['IMD1006_UNALPHA3','IMD1011_1'],how='left',
                         validate='one_to_many',indicator=True)
    keep=['iso','country','onset_year','rank','date','status','IMD1004','n',
          'module2_n','module3_n','module4_n','module5_n','_merge']
    matched[keep].to_csv(OUT/'core_election_cses_match.csv',index=False)
    print('European studies 2004-2019',len(coverage),'countries',imd.IMD1006_UNALPHA2.nunique(),'respondents',len(imd))

if __name__=='__main__':main()
