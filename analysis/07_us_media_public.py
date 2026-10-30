"""Compare matched major topics in NYT index entries and annual Gallup MIP.

CAP's Gallup values normalise poll response mentions, not percentages of people.
NYT is a systematic index sample, not audience impressions or social media.
"""
from pathlib import Path
import pandas as pd
P=Path(__file__).resolve().parents[1]
n=pd.read_csv(P/'data/raw/nyt.csv',low_memory=False)
n=n[n.year.between(2010,2016)&n.majortopic.notna()].copy()
n.majortopic=n.majortopic.astype(int)
g=pd.read_csv(P/'data/raw/cap_gallup_mip.csv')
g=g[g.year.between(2010,2016)]
topics={1:'macroeconomy',2:'civil_rights',5:'labor',7:'environment',8:'energy',9:'immigration',12:'crime',20:'government'}
rows=[]
for year in range(2010,2017):
 news=n[n.year==year];poll=g[g.year==year]
 for code,name in topics.items():
  x=poll[poll.majortopic==code]
  if len(x)!=1 or pd.isna(x.percent.iloc[0]): continue
  rows.append({'year':year,'topic':name,'topic_code':code,'news_n':int(news.majortopic.eq(code).sum()),'news_total_n':len(news),'news_pct':100*news.majortopic.eq(code).mean(),'poll_normalized_pct':100*x.percent.iloc[0]})
pd.DataFrame(rows).to_csv(P/'data/processed/us_media_public_agenda.csv',index=False)
print(pd.DataFrame(rows).query('year==2016').round(2).to_string(index=False))
