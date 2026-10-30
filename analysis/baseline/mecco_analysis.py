"""Extract public MeCCO Highcharts monthly arrays, aggregate full calendar years.
Counts are article hits, not audience shares. Source pages and arrays retained.
Russian basket intentionally excludes Izvestiya, which has zero throughout 2025.
"""
from pathlib import Path
import json,re,pandas as pd
P=Path(__file__).resolve().parent
selected={'russia':['Rossiskaya Gazeta','Nezavisimaya Gazeta','Komsomolskaya Pravda'],'spain':['El Pais','El Mundo','La Vanguardia','Expansion'],'latin_america':['O Globo (Brazil)','Folha de S.Paulo (Brazil)'],'middle_east':['Jerusalem Post'],'asia':['Bangkok Post']}
rows=[]
for region,names in selected.items():
 html=(P/f'data/mecco_{region}.html').read_text();part=html[html.index("$('#chart-A')"):html.index("$('#chart-B')")]
 series={}
 for name,year,values in re.findall(r"name:\s*'([^']+)'[\s\S]*?pointStart:\s*Date\.UTC\((\d+),[^)]*\)[\s\S]*?data:\s*\[([^\]]+)\]",part):
  if name in names:
   a=json.loads('['+values+']');series[name]=(int(year),a)
 for name,(year,a) in series.items():
  for i,v in enumerate(a):
   y=year+i//12;m=i%12+1
   if 2010<=y<=2025:rows.append({'region':region,'source':name,'year':y,'month':m,'articles':v})
 assert set(series)==set(names),(region,set(series),set(names))
d=pd.DataFrame(rows);d.to_csv(P/'outputs/mecco_monthly_selected.csv',index=False)
y=d.groupby(['region','source','year']).agg(months=('month','size'),articles=('articles','sum')).reset_index();assert (y.months==12).all();y.to_csv(P/'outputs/mecco_source_annual.csv',index=False)
g=y.groupby(['region','year']).agg(articles=('articles','sum'),n_sources=('source','nunique')).reset_index();g['index_2010']=g.groupby('region').articles.transform(lambda a:100*a/a.iloc[0]);g.to_csv(P/'outputs/mecco_baskets_annual.csv',index=False)
print(g[g.year.isin([2010,2019,2021,2025])].round(2).to_string(index=False));print(y[y.year.isin([2010,2021,2025])].to_string(index=False))
