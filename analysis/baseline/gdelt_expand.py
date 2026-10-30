from pathlib import Path
import requests,time,json
folder=Path(__file__).resolve().parent/'data'/'gdelt';folder.mkdir(exist_ok=True)
queries={
 'bbc_climate':'domain:bbc.com "climate change"',
 'bbc_immigration':'domain:bbc.com immigration',
 'guardian_all':'domain:theguardian.com',
 'guardian_climate':'domain:theguardian.com "climate change"',
 'guardian_inflation':'domain:theguardian.com inflation',
 'guardian_immigration':'domain:theguardian.com immigration',
 'nyt_all':'domain:nytimes.com',
 'nyt_climate':'domain:nytimes.com "climate change"',
 'nyt_inflation':'domain:nytimes.com inflation',
 'nyt_immigration':'domain:nytimes.com immigration',
}
for name,q in queries.items():
 params={'query':q,'mode':'timelinevolraw','format':'json','startdatetime':'20170101000000','enddatetime':'20251015000000'}
 for attempt in range(3):
  try:
   r=requests.get('https://api.gdeltproject.org/api/v2/doc/doc',params=params,timeout=60);print(name,attempt,r.status_code,len(r.content),flush=True)
   if r.status_code==200 and r.text.lstrip().startswith('{'):
    data=r.json(); assert 'timeline' in data;(folder/(name+'.json')).write_text(r.text);break
  except Exception as e:print(name,type(e).__name__,str(e)[:100],flush=True)
  time.sleep(12)
 time.sleep(7)
