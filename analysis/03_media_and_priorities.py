"""US NYT Index CAP categories, 2010-2016, and European MIP trends.

The NYT Index is CAP's sample of the first entry on odd-numbered index pages,
not all articles, social media, audience reach or a measurement of gender alone.
SPES is a country-level annual summary of Eurobarometer issue mentions.
These series measure different populations and are not subtracted or pooled.
"""
from pathlib import Path
import pandas as pd
P=Path(__file__).resolve().parents[1]
d=pd.read_csv(P/'data/raw/nyt.csv',low_memory=False);d=d[d.year.between(2010,2016)&d.majortopic.notna()].copy()
topics={'economy':1,'civil_rights':2,'environment':7,'energy':8,'immigration':9,'crime':12}
rows=[]
for year,g in d.groupby('year'):
 row={'year':int(year),'n':len(g)}
 for k,v in topics.items():row[k+'_n']=int(g.majortopic.eq(v).sum());row[k+'_pct']=100*g.majortopic.eq(v).mean()
 rows.append(row)
r=pd.DataFrame(rows);r.to_csv(P/'data/processed/nyt_topics_2010_2016.csv',index=False)
x=pd.read_csv(P/'data/raw/spes_aggregate.csv');west=['Austria','Belgium','Denmark','Finland','France','Germany','Ireland','Italy','Luxembourg','Netherlands','Portugal','Spain','Sweden','United Kingdom'];
x=x[x.country_name.isin(west)&x.year.between(2010,2024)][['country_name','year','price','unemploy','eco','immi','env_merged','health']].copy();x.to_csv(P/'data/processed/europe_priorities_country.csv',index=False)
y=x.groupby('year').agg(n_countries=('country_name','nunique'),price=('price','mean'),unemploy=('unemploy','mean'),eco=('eco','mean'),immi=('immi','mean'),env_merged=('env_merged','mean'),health=('health','mean')).reset_index();y.to_csv(P/'data/processed/europe_priorities_mean.csv',index=False)
print('NYT Index',r.round(2).to_string(index=False)); print('Europe',y[y.year.isin([2010,2012,2019,2021,2022,2024])].round(2).to_string(index=False));print('2010 and 2024 country response counts\n',x[x.year.isin([2010,2024])].groupby('year').count().to_string())
