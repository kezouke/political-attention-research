"""Probe archived GDELT DOC timeline coverage; refuse to invent denominators."""
from pathlib import Path
import requests,time,json
base=Path(__file__).parent/'data'/'gdelt';base.mkdir(exist_ok=True)
queries={'bbc_all':'domain:bbc.com','bbc_climate':'domain:bbc.com "climate change"','bbc_inflation':'domain:bbc.com inflation','bbc_immigration':'domain:bbc.com immigration'}
for key,q in queries.items():
 p={'query':q,'mode':'timelinevolraw','format':'json','startdatetime':'20170101000000','enddatetime':'20261029235959'}
 for attempt in range(3):
  try:
   r=requests.get('https://api.gdeltproject.org/api/v2/doc/doc',params=p,timeout=90)
   print(key,attempt,r.status_code,len(r.content),r.text[:90],flush=True)
   if r.status_code==200 and r.text.lstrip().startswith('{'):
    (base/(key+'.json')).write_text(r.text);break
  except Exception as e:print(key,type(e).__name__,str(e)[:100],flush=True)
  time.sleep(8)
 time.sleep(8)
