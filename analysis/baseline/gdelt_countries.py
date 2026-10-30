"""Retrieve GDELT DOC timelinevolraw. English terms match machine translations.
One source per country cannot represent the national media system.
"""
from pathlib import Path
import requests,time
P=Path(__file__).resolve().parent/'data/gdelt';P.mkdir(exist_ok=True)
domains={'serbia':'b92.net','brazil':'folha.uol.com.br','israel':'haaretz.com','spain':'elpais.com','thailand':'bangkokpost.com','bulgaria':'dnevnik.bg','russia':'kommersant.ru','usa':'nytimes.com'}
terms={'all':'','climate':'"climate change"','inflation':'inflation'}
s=requests.Session()
for name,domain in domains.items():
 for issue,term in terms.items():
  dest=P/f'{name}_{issue}.json'
  if dest.exists():continue
  params={'query':f'domain:{domain} {term}'.strip(),'mode':'timelinevolraw','format':'json','startdatetime':'20170101000000','enddatetime':'20251015000000'}
  try:
   r=s.get('https://api.gdeltproject.org/api/v2/doc/doc',params=params,timeout=40)
   print(name,issue,r.status_code,len(r.content),flush=True)
   if r.status_code==200 and r.text.lstrip().startswith('{') and 'timeline' in r.json():dest.write_text(r.text)
  except Exception as e:print(name,issue,type(e).__name__,flush=True)
  time.sleep(6)
