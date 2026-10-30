from pathlib import Path
import re,logging
import pandas as pd
from pypdf import PdfReader
logging.getLogger('pypdf').setLevel(logging.ERROR)
BASE=Path(__file__).resolve().parent;r=PdfReader(BASE/'data/eurobarometer_105_annex.pdf')
def table(page):
 t=r.pages[page].extract_text(extraction_mode='layout');rows={}
 for line in t.splitlines():
  m=re.match(r'^\s*(EU27|[A-Z]{2})\s+((?:-?\d+\s+){15}-?\d+)\s*$',line)
  if m: rows[m.group(1)]=list(map(int,m.group(2).split()))
 return rows
country1=table(42);candidate1=table(43);country2=table(44);candidate2=table(45)
rows=[]
for code in ['EU27','BE','BG','DK','DE','ES','FR','IT','NL','SE','RS','UK']:
 a=(country1 if code in country1 else candidate1)[code];b=(country2 if code in country2 else candidate2)[code]
 # a is crime, economy, prices, Middle East conflict, unemployment, housing, public debt, migration;
 # candidate table inserts Cyprus at index 5 and omits migration. Migration is at candidate b first pair.
 candidate=code in ['RS','UK']
 if candidate:
  fields={'crime':a[0:2],'economy':a[2:4],'prices':a[4:6],'middle_east':a[6:8],'unemployment':a[8:10],'housing':a[12:14],'immigration':b[0:2],'environment_climate':b[10:12],'security_defence':b[12:14]}
 else:
  fields={'crime':a[0:2],'economy':a[2:4],'prices':a[4:6],'middle_east':a[6:8],'unemployment':a[8:10],'housing':a[10:12],'immigration':a[14:16],'environment_climate':b[8:10],'security_defence':b[10:12]}
 for topic,(value,change) in fields.items():
  rows.append({'geography':code,'issue':topic,'autumn_2025':value-change,'spring_2026':value,'change_pp':change})
out=pd.DataFrame(rows);out.to_csv(BASE/'outputs/eurobarometer_2025_2026.csv',index=False);print(out.pivot(index='geography',columns='issue',values='spring_2026').to_string())
