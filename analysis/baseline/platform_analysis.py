from pathlib import Path
import re
import pandas as pd
import matplotlib.pyplot as plt
BASE=Path(__file__).resolve().parent
patterns={
'climate':r'\b(?:climate|global warming|greenhouse gas(?:es)?)\b',
'immigration':r'\b(?:immigra\w*|migran\w*|deport\w*|asylum|refugee\w*)\b',
'prices':r'\b(?:inflation|cost of living|consumer prices|price increases?|rising prices)\b',
'identity':r'\b(?:lgbt\w*|gay|lesbian\w*|transgender|same.sex marriage|gender identity|racial discrimination|racism)\b',
'economy':r'\b(?:economy|economic|jobs?|unemployment|wages?)\b'}
rows=[];contexts=[]
for f in sorted((BASE/'data/platforms').glob('*.txt')):
 text=f.read_text();party,year=f.stem.split('_');n=len(re.findall(r"\b[\w]+(?:['’][\w]+)?\b",text));row={'party':party,'year':int(year),'words':n}
 for key,pat in patterns.items():
  matches=list(re.finditer(pat,text,re.I));row[key+'_count']=len(matches);row[key+'_per_10k']=10000*len(matches)/n
  for m in matches:
   contexts.append({'party':party,'year':int(year),'topic':key,'match':m.group(), 'context':re.sub(r'\s+',' ',text[max(0,m.start()-90):min(len(text),m.end()+120)])})
 # Exclude a law title to check whether names are driving the price measure.
 cleaned=re.sub(r'\binflation\s+reduction\s+act\b',' ',text,flags=re.I)
 row['prices_excluding_law_count']=len(re.findall(patterns['prices'],cleaned,re.I))
 row['prices_excluding_law_per_10k']=10000*row['prices_excluding_law_count']/n
 rows.append(row)
pd.DataFrame(rows).to_csv(BASE/'outputs/platform_term_counts.csv',index=False,float_format='%.4f');pd.DataFrame(contexts).to_csv(BASE/'outputs/platform_matches.csv',index=False)
d=pd.DataFrame(rows);plt.rcParams['font.family']='DejaVu Sans';fig,axs=plt.subplots(1,2,figsize=(10,4.7),sharey=True)
for ax,party,title in zip(axs,['democratic','republican'],['Демократы','Республиканцы']):
 sub=d[d.party==party].sort_values('year')
 for topic,label in [('climate','Климат'),('immigration','Миграция'),('prices','Цены'),('identity','Права / идентичность')]:ax.plot(sub.year,sub[topic+'_per_10k'],marker='o',label=label)
 ax.set(title=title,xlabel='Год программы',xticks=[2012,2016,2020,2024]);ax.grid(axis='y',alpha=.2)
axs[0].set_ylabel('Упоминаний на 10 000 слов');axs[1].legend(frameon=False,fontsize=8)
fig.suptitle('Программы партий США: поисковые термины');fig.text(.1,.01,'UCSB American Presidency Project. В 2020 году республиканцы сохранили программу 2016 года.',fontsize=8);fig.tight_layout(rect=[0,.06,1,.95]);fig.savefig(BASE/'outputs/platform_dictionary.png',dpi=180)
print(d.to_string(index=False))
