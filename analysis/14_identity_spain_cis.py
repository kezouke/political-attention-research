"""Extract selected national top-three issue percentages from original CIS PDFs.

A sparse September-only series, deliberately not annual interpolation. CIS
spontaneously records up to 3 answers. Gender violence and racism are narrow
issues; they do not represent every minority or LGBT concern. Percentages use
CIS-published weights; sampling mode, coding and questionnaire order change.
"""
from pathlib import Path
import hashlib,re,sys,urllib.request
import fitz
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
SOURCES={
2010:('https://www.cis.es/documents/d/cis/es2844mar_a',2473,'2010-09-03','2010-09-13','in-person','contra la mujer'),
2016:('https://www.cis.es/documents/d/cis/es3149mar_a',2483,'2016-09-03','2016-09-12','in-person','contra la mujer'),
2018:('https://www.cis.es/documents/d/cis/es3223mar_a',2972,'2018-09-01','2018-09-11','in-person','contra la mujer'),
2019:('https://www.cis.es/documents/d/cis/es3261marmt_a',5906,'2019-09-01','2019-09-18','in-person','de género'),
2023:('https://www.cis.es/documents/d/guest/es3420marMT_a',10104,'2023-09-01','2023-09-12','telephone','de género'),
2024:('https://www.cis.es/documents/d/cis/es3474mar_a',4027,'2024-09-02','2024-09-06','telephone','de género'),
2025:('https://www.cis.es/documents/20117/13443627/es3524mar-pdf.pdf/677f20fd-cc16-7d78-358b-91bc2a037998?version=1.1&t=1759843440220',4122,'2025-09-01','2025-09-06','telephone','de género'),
2026:('https://www.cis.es/documents/20117/14250083/es3577mar.pdf/ec0cb565-d864-472d-0461-add459e7b19e?version=1.0&t=1790164379049',4042,'2026-09-01','2026-09-04','telephone','de género')}
LABELS={'immigration':'La inmigración','unemployment':'El paro','housing':'La vivienda','racism':'El racismo','gender_violence':None,'climate_change':'El cambio climático','environment':'Los problemas medioambientales'}
rows=[]
for year,(url,n,start,end,mode,gender) in SOURCES.items():
 file=ROOT/'data/raw'/f'cis_september_{year}.pdf'
 if '--download' in sys.argv:
  data=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read()
  if not data.startswith(b'%PDF'):raise ValueError(f'not PDF: {url}')
  file.write_bytes(data)
 data=file.read_bytes();sha=hashlib.sha256(data).hexdigest()
 with fitz.open(stream=data,filetype='pdf') as d:
  pages=[(i+1,p.get_text()) for i,p in enumerate(d) if 'principal problema que existe actualmente en España' in p.get_text() and ('La violencia de género' in p.get_text() or 'La violencia contra la mujer' in p.get_text())]
  assert pages,(year,len(pages))
  page,body=pages[0]  # First is the national question; later repeats are personal.
  body=body.split('¿Y cuál es el problema que a Ud.',1)[0]
  for issue,default in LABELS.items():
   label=('La violencia '+gender) if issue=='gender_violence' else default
   if issue=='environment' and year>=2023:label='El medio ambiente'
   # Climate is not separately coded in early pages, not an implicit zero.
   if label not in body: continue
   segment=body.split(label,1)[1].strip().splitlines()
   expected=1 if year==2010 else 4
   vals=[]
   for line in segment:
    v=line.strip()
    if not re.fullmatch(r'-|\d*[,.]\d+|\d+',v):break
    vals.append(v)
    if len(vals)==expected:break
   assert len(vals)==expected,(year,issue,vals)
   result=vals[-1]
   if result=='-':continue
   pct=float(result.replace(',','.'))
   rows.append({'country':'Spain','year':year,'fieldwork_start':start,'fieldwork_end':end,'n_unweighted':n,'mode':mode,'issue':issue,'source_category':label,'pct_top3':pct,'page':page,'source_url':url,'sha256':sha,'denominator':'all respondents; source weighted where applicable','response_format':'spontaneous; up to three','coding_note':'recoded table' if year in (2025,2026) else 'published source category'})
out=pd.DataFrame(rows)
assert out.query("year==2023 and issue=='immigration'").pct_top3.iloc[0]==5.7
assert out.query("year==2024 and issue=='immigration'").pct_top3.iloc[0]==30.4
assert out.query("year==2019 and issue=='gender_violence'").pct_top3.iloc[0]==6.6
assert out.query("year==2026 and issue=='gender_violence'").pct_top3.iloc[0]==0.9
assert out.query("year==2026 and issue=='housing'").pct_top3.iloc[0]==37.5
out.to_csv(ROOT/'data/processed/identity_spain_cis_selected.csv',index=False)
print(out.pivot(index='year',columns='issue',values='pct_top3').to_string())
