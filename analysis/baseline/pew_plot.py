from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
p=Path(__file__).resolve().parent;d=pd.read_csv(p/'data/pew_problem_trends.csv');labels={'Climate change':'Климат','Racism':'Расизм','Inflation':'Инфляция','Illegal immigration':'Нелегальная иммиграция'}
fig,ax=plt.subplots(figsize=(10,5))
for k,g in d.groupby('topic',sort=False):
 g=g.sort_values('year');ax.plot(g.year,g.percent,marker='o',label=labels[k],linestyle='--' if k in ['Climate change','Racism'] else '-')
ax.set(title='США: очень большая проблема, по данным Pew',xlabel='Год',ylabel='Доля респондентов, %',ylim=(0,80),xticks=range(2018,2027));ax.grid(axis='y',alpha=.2);ax.legend(frameon=False,ncol=2,loc='upper left');fig.text(.1,.01,'Пунктир соединяет отдельные измеренные точки, а не оценки промежуточных лет.',fontsize=8);fig.tight_layout(rect=[0,.06,1,1]);fig.savefig(p/'outputs/pew_trends.png',dpi=180)
