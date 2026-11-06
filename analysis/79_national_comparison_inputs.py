"""Construct within-survey national comparisons. No pooled respondent export.

This preparation step audits coding and sample availability before models.
Question wording, timing and scales remain specific to each survey.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import zipfile
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/audit_20261106'
AUDIT = ROOT / 'data/processed/audit_20261106'
OUT = ROOT / 'data/processed/three_explanations'


def module(name, file):
    s = importlib.util.spec_from_file_location(name, ROOT / 'analysis' / file)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


cis = module('cis_national', '34_cis_panel_audit.py')
nl = module('nl_national', '38_dpes_audit.py')
ext = module('extensions_national', '41_national_extensions_audit.py')
dk = module('dk_national', '43_dnes_audit.py')
be = module('be_national', '44_partirep_audit.py')
CORE = ['economy_bad', 'government_disapproval', 'economic_priority', 'elite_distrust']
NUMERIC = ['age_scaled', 'age_squared', 'left_right', 'left_right_squared', 'left_right_missing']
CATEGORICAL = ['gender', 'education', 'region', 'early_intention']
TARGETS = ['government_vs_opposition', 'opposition_type', 'nonvote_vs_vote', 'all_outcomes']

# Exact code lists, not an automatic keyword classifier. Main priority includes
# economy, employment and income/prices. Broad variants add welfare/fiscal topics.
DK_ECON = [200, 201, 210, 211, 212, 230, 231, 240, 250, 260, 270, 290, 291,
           300, 310, 320, 330, 340, 350, 360, 370, 380, 390, 392, 393]
CONFIG = {
    'ES2015': dict(iso='ESP', country='Spain', year=2015, date='2015-12-20', stem='cis_7715',
        economy=('PP9', [1,2,3,4,5], 1,5), government=('P5',[1,2,3,4,5],1,5),
        trust=('PP602',list(range(11)),10,0), priority='PP301',
        priority_main=[1,7,13,14,15,17,43,50], priority_broad=[1,6,7,13,14,15,17,18,19,20,21,24,42,43,50],
        priority_valid=None, vote='PP31R', turnout=('PP29',[5],[1,2,3,4]),
        age='P28', gender='P27', education=('PESTUDIOS',list(range(1,9))),
        lr=('P21',1,10), region=('CCAA',list(range(1,20))), intention='P11R', weight='PESO',
        timing='government/intention/age/LR pre; economy/priority/trust/vote/education post',
        priority_question='first personal election issue; expanded response list, not comparable to 2008/2011 list'),
    'NL2010': dict(iso='NLD', country='Netherlands', year=2010, date='2010-06-09', stem='dpes_2010',
        economy=('V820',[1,2,3],None,None), government=('V073',[1,2,3,4,5],1,5),
        trust=('V811',[1,2,3,4],1,4), priority='V041', priority_main=[1,8,9],
        priority_broad=[1,2,6,7,8,9,11], priority_valid=list(range(1,17)),
        vote='V512', turnout=('V510',[1],[0]), age='V443', gender='V010',
        education=('V410',list(range(1,6))), lr=('V711',0,10), region=None,
        intention='V081', weight='WGT5', timing='priority/government/intention pre; economy/trust/LR/vote post',
        priority_question='first national problem; income and prices share one category'),
    'NL2012': dict(iso='NLD', country='Netherlands', year=2012, date='2012-09-12', stem='dpes_2012',
        economy=('V311',[1,2,3],1,3), government=('V093',[1,2,3,4,5],1,5),
        trust=('V451',[1,2,3,4],1,4), priority='V071', priority_main=[1,8,9],
        priority_broad=[1,2,6,7,8,9,11], priority_valid=list(range(1,17)),
        vote='V212', turnout=('V210',[1],[2]), age='V340', gender='V341',
        education=('V344',list(range(1,6))), lr=('V130',0,10), region=None,
        intention=None, weight='WGT2', timing='post; party trust in dropoff questionnaire',
        priority_question='first national problem; income, prices and taxes share category 8'),
    'PT2005': dict(iso='PRT', country='Portugal', year=2005, date='2005-02-20', stem='pes_2005',
        economy=('p61',[1,2,3,4,5],1,5), government=('p5',[1,2,3,4],1,4),
        trust=('p12.3',[1,2,3,4,5],5,1), priority='p1',
        priority_main=[9,30,32,33,34,35,37,40,41,42,49],
        priority_broad=[9,*range(30,44),49,69], priority_valid=None,
        vote='p25', turnout=('p24',[1],[2]), age='d2', gender='Sexo',
        education=('d4',list(range(1,12))), lr=('p69',0,10), region=None,
        intention=None, weight='ponsd', timing='post',
        priority_question='most important national problem over last three years'),
    'PT2009': dict(iso='PRT', country='Portugal', year=2009, date='2009-09-27', stem='pes_2009',
        economy=('P69',[1,2,3,4,5],5,1), government=('P7',[1,2,3,4],4,1),
        trust=('P11_5',[1,2,3,4,5],1,5), priority='P1',
        priority_main=[1,2,15,16,20,27,28,38,40,41,49,52],
        priority_broad=[1,2,8,11,15,16,18,20,23,26,27,28,31,37,38,40,41,43,45,49,50,51,52],
        priority_valid=None, vote='P28', turnout=('P27',[1],[2]), age='D2', gender='SEXO',
        education=('D4',list(range(1,8))), lr=('P76',0,10), region=None,
        intention=None, weight=None, timing='post',
        priority_question='most important personal election issue; national-problem question separate'),
    'IS2013': dict(iso='ISL', country='Iceland', year=2013, date='2013-04-27', stem='icenes_2013',
        economy=('ecobettwors',[1,3,5],1,5), government=('govprfmJS',[1,2,3,4],1,4),
        trust=('pltrust',[1,2,3,4,5],1,5), priority='issue12013',
        priority_main=[1,6], priority_broad=[1,2,3,6,9], priority_valid=[1,2,3,4,5,6,7,8,9,90],
        vote='prtvote13', turnout=('vote13',[1],[2]), age='age', gender='gender',
        education=('education',list(range(1,9))), lr=('lrscale',0,10), region=None,
        intention=None, weight=None, timing='post', priority_question='first personal election issue'),
    'BE2014': dict(iso='BEL', country='Belgium', year=2014, date='2014-05-25', stem='partirep_2014',
        economy=('V400',[1,2,3],1,3), government=('V54',[1,2,3,4,5],5,1),
        trust=('V59_10',list(range(1,12)),10,0), priority='V25',
        priority_main=[1,5], priority_broad=[1,5,8], priority_valid=list(range(1,9)),
        vote='V60B', turnout=('V40B',[1],[2]), age='V70018_1', gender='V70015_1',
        education=('V3',list(range(1,11))), lr=('V40',0,10), region=('REGION',[1,2]),
        intention='V21', weight=None, timing='priority/government/trust/intention/LR pre; economy/vote post',
        priority_question='most important for vote among eight fixed topics; Flanders/Wallonia only'),
    'DK2007': dict(iso='DNK', country='Denmark', year=2007, date='2007-11-13', stem='dnes_2007',
        economy=('V175',[1,2,3,4,5],1,5), government=('V191',[1,2,3,4,5],1,5),
        trust=('V275',[1,2,3,4],1,4), priority='V81', priority_main=DK_ECON,
        priority_broad=None, priority_valid=None, vote='V28', turnout=None,
        age='V514', gender='V379', education=('V488',[1,2,3,4]), lr=('V291',1,11), region=None,
        intention=None, weight='V523', timing='post; mixed survey sources including web panel',
        priority_question='first most important problem politicians should address; producer detailed code key'),
}


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def verified(key, suffix=None):
    a = json.loads((AUDIT / 'acquisition_manifest.json').read_text())[key]
    p = ROOT / a['local_path'] if suffix is None else RAW / (key + suffix)
    assert digest(p) == a['sha256'], key
    return p


def cis_labels():
    with zipfile.ZipFile(verified('cis_7715_data')) as z:
        s = z.read('ES7715').decode('cp1252').split('VALUE LABELS',1)[1]
    labels = {}
    for m in re.finditer(r'(?:^|\n)/?(\w+)\s*\n(.*?)(?=\n/\w+\s*\n|\Z)', s, re.S):
        labels[m[1]] = {int(k):v.replace("''", "'") for k,v in re.findall(r"(-?\d+)\s+'((?:[^']|'')*)'",m[2])}
    return labels


def load_source(key):
    cfg = CONFIG[key]; stem = cfg['stem']
    manifest = json.loads((AUDIT / 'acquisition_manifest.json').read_text())
    if key.startswith('ES'):
        verified(stem + '_data'); d, info = cis.read_cis(7715)
        names = info.set_index('variable').source_label.to_dict(); labels = cis_labels()
    elif key.startswith('NL'):
        fileid = nl.FILES[cfg['year']][0]
        d = pd.read_csv(verified(f'{stem}_file_{fileid}'),sep='\t',low_memory=False,na_values=['.'])
        d.columns = d.columns.str.upper()
        meta = nl.ddi(verified(stem + '_ddi'))
        names = {v:a['label'] for v,a in meta.items()}
        labels = {v:{code:c['label'] for code,c in a['categories'].items()} for v,a in meta.items()}
    elif key.startswith(('PT','IS')):
        fileid = ext.FILES[stem][0]
        d = pd.read_csv(verified(f'{stem}_file_{fileid}'),sep='\t',low_memory=False,na_values=['.'])
        meta = ext.read_ddi(verified(stem + '_ddi'))
        names = {v:a['label'] for v,a in meta.items()}
        labels = {v:{code:c['label'] for code,c in a['categories'].items()} for v,a in meta.items()}
    elif key.startswith('BE'):
        d, labels = be.read_2014(manifest)
        names = {r['variable']:r['question'] for r in be.english_inventory(verified(stem + '_codebook'),2014)}
    else:
        d,m,_ = dk.read_source(2007,manifest)
        names = m.column_names_to_labels; labels = m.variable_value_labels
    assert d.index.is_unique
    return d, names, labels


def category(x, valid=None):
    if valid is not None: x = x.where(x.isin(valid))
    return x.astype('Float64').astype('string').fillna('missing')


def scale(d, spec, special=None):
    v, valid, good, bad = spec
    s = pd.to_numeric(d[v],errors='raise').where(d[v].isin(valid))
    if special: s = s.replace(special)
    return (s - good) / (bad - good)


def dk_key():
    text = (RAW / 'dnes_2011_doc_34.txt').read_text()
    # The appendix includes valid non-economic topics on both sides. The
    # producer states explicitly that the same code key was used in 2007.
    section = text[text.index('Tabel 9. Emnesorteret kodenøgle'):]
    pairs = re.findall(r'^\s*(\d{1,4})\s+([^\d\s][^\n]+)', section, re.M)
    return {int(code): label.strip() for code, label in pairs}


def dk_codes():
    codes = set(dk_key())
    codes = {x for x in codes if 20 <= x <= 1200 and x != 90}
    return sorted(codes | {2})


def construct(key):
    cfg = CONFIG[key]; d,names,labels = load_source(key)
    x = pd.DataFrame(index=d.index)
    # Local row key only, never joined across independent surveys/elections.
    x['person_id'] = np.arange(len(d))
    for field, spec in [('economy_bad','economy'),('government_disapproval','government'),('elite_distrust','trust')]:
        if key == 'NL2010' and field == 'economy_bad': x[field] = d.V820.map({1:0.,2:1.,3:.5})
        else: x[field] = scale(d,cfg[spec],{11:0} if key=='BE2014' and spec=='trust' else None)
    v=cfg['priority']; valid=cfg['priority_valid']
    if key=='ES2015': valid=[c for c in labels[v] if c<96]
    if key.startswith('PT'): valid=[c for c in labels[v] if c<99] if key=='PT2005' else [c for c in labels[v] if c<97]
    if key=='DK2007': valid=dk_codes()
    broad=cfg['priority_broad']
    if key=='DK2007': broad=[c for c in valid if 200<=c<500 or c in [600,610,616,620,621]]
    assert set(cfg['priority_main']) <= set(valid), (key, 'priority main')
    assert set(broad) <= set(valid), (key, 'priority broad')
    x['priority_code'] = d[v]
    for col,codes in [('economic_priority',cfg['priority_main']),('economic_priority_broad',broad)]:
        x[col] = d[v].isin(codes).astype(float).where(d[v].isin(valid))
    age = 2014-d[cfg['age']] if key=='BE2014' else d[cfg['age']]
    x['eligible'] = age.between(18,85 if key=='BE2014' else 100)
    if key=='ES2015': x['eligible'] &= age.ne(99)  # 99 is missing, not age 99 in CIS.
    x['age_scaled']=(age-50)/20; x['age_squared']=x.age_scaled**2
    lr,lo,hi=cfg['lr']; l=d[lr].replace({11:0}) if key=='BE2014' else d[lr]
    l=((l-lo)/(hi-lo)).where(l.between(lo,hi))
    x['left_right_missing']=l.isna().astype(float)
    x['left_right']=l.fillna(.5); x['left_right_squared']=x.left_right**2
    x['gender']=category(d[cfg['gender']],[1,2])
    x['education']=category(d[cfg['education'][0]],cfg['education'][1])
    x['region']=category(d[cfg['region'][0]],cfg['region'][1]) if cfg['region'] else 'not_available'
    x['early_intention']=category(d[cfg['intention']]) if cfg['intention'] else 'not_available'
    x['weight']=pd.to_numeric(d[cfg['weight']],errors='raise') if cfg['weight'] else 1.
    x['party_code']=d[cfg['vote']]
    x['turnout']=np.nan
    if cfg['turnout']:
        tv,yes,no=cfg['turnout']; x.loc[d[tv].isin(yes),'turnout']=1; x.loc[d[tv].isin(no),'turnout']=0
    else:
        x.loc[d.V28.isin([1,2,3,5,6,7,8,9,10,11,14]),'turnout']=1
        x.loc[d.V28.eq(15),'turnout']=0
    if key=='BE2014':
        x.loc[d.V40B.eq(1)&d.V60B.eq(12),'turnout']=np.nan
        for w in ['WEIGHT1','WEIGHT2','WEIGHT3','WEIGHT4']:x[w]=d[w]
        x['alternative_trust']=scale(d,('V59_4',list(range(1,12)),10,0),{11:0})
    if key=='DK2007': x['source_group']=d.V4
    if key=='NL2012': x['economic_priority_narrow']=d[v].isin([1,9]).astype(float).where(d[v].isin(valid))
    if key=='ES2015': x['alternative_economy']=scale(d,('P4',[1,2,3,4,5],1,5))
    selected={cfg[a][0] for a in ['economy','government','trust','education','lr']}
    selected|={cfg[a] for a in ['priority','vote','age','gender']}
    if cfg['turnout']:selected.add(cfg['turnout'][0])
    if cfg['intention']:selected.add(cfg['intention'])
    if cfg['weight']:selected.add(cfg['weight'])
    if cfg['region']:selected.add(cfg['region'][0])
    metadata={v:dict(label=names.get(v),values=labels.get(v,{})) for v in sorted(selected)}
    if key=='DK2007': metadata[cfg['priority']]['values']=dk_key()
    return x,metadata,dict(valid=valid,main=cfg['priority_main'],broad=broad)


def main():
    rows=[];metadata={};priority=[]
    for key in CONFIG:
        x,meta,codes=construct(key);metadata[key]=meta
        core=x.eligible & x[CORE].notna().all(axis=1) & x.weight.gt(0)
        assert x.loc[core,CORE].ge(0).all().all() and x.loc[core,CORE].le(1).all().all()
        rows.append(dict(dataset=key,source_n=len(x),age_eligible_n=int(x.eligible.sum()),
                         core_n=int(core.sum()),core_known_turnout_n=int((core & x.turnout.notna()).sum()),
                         core_explicit_nonvote_n=int((core & x.turnout.eq(0)).sum()),
                         core_priority_yes_n=int((core & x.economic_priority.eq(1)).sum()),
                         weight=CONFIG[key]['weight'] or 'unweighted',timing=CONFIG[key]['timing']))
        labels=meta[CONFIG[key]['priority']]['values']
        for c in codes['valid']:
            priority.append(dict(dataset=key,code=c,source_label=labels.get(c,''),
                                 primary_economic=c in codes['main'],broad_economic=c in codes['broad']))
    pd.DataFrame(rows).to_csv(OUT/'national_measurement_coverage.csv',index=False)
    pd.DataFrame(priority).to_csv(OUT/'national_priority_crosswalk.csv',index=False)
    (OUT/'national_selected_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    (OUT/'national_measurement_config.json').write_text(json.dumps(CONFIG,ensure_ascii=False,indent=2)+'\n')
    print(pd.DataFrame(rows).to_string(index=False))


if __name__=='__main__':main()
