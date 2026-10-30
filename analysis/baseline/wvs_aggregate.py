from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
BASE=Path(__file__).resolve().parent
p=pd.read_csv(BASE/'data/qog_ei.csv',usecols=['cname','ccodealp','year','wvs_epmip'])
cs=['BRA','BGR','ISR','SRB','THA','RUS','ESP','USA','GBR','DEU'];p=p[p.ccodealp.isin(cs)&p.year.between(2010,2020)&p.wvs_epmip.notna()].sort_values(['ccodealp','year']);p.to_csv(BASE/'outputs/wvs_2010_2020.csv',index=False,float_format='%.6f')
fig,ax=plt.subplots(figsize=(9,5));names={'BRA':'Бразилия','DEU':'Германия','RUS':'Россия','THA':'Таиланд','USA':'США'}
for code,name in names.items():
 d=p[p.ccodealp==code];ax.plot(d.year,d.wvs_epmip,marker='o',label=name)
ax.set(title='WVS: приоритет экологии при конфликте с ростом',ylabel='Опубликованная доля, %',xlabel='Год полевых работ',ylim=(25,75),xticks=range(2010,2021));ax.grid(axis='y',alpha=.2);ax.legend(frameon=False,ncol=2)
fig.text(.1,.01,'QoG Environmental Indicators 2021, WVS. Точки соединены для наглядности; года между волнами не измерены.',fontsize=8);fig.tight_layout(rect=[0,.06,1,1]);fig.savefig(BASE/'outputs/wvs_comparison.png',dpi=180)
print(p.round(2).to_string(index=False))
