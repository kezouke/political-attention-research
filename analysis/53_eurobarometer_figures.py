"""Review figures from aggregate locked results; no microdata access."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/processed/three_explanations'
FIG=ROOT/'output/research_figures'
FIG.mkdir(exist_ok=True,parents=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none',
                     'svg.hashsalt':'political-attention-eb2009',
                     'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,
                     'axes.edgecolor':'#aab4bc','text.color':'#17252c','axes.labelcolor':'#17252c'})


def main():
    d=pd.read_csv(DATA/'eb_model_margins.csv')
    d=d[d.target.eq('four_outcomes')]
    fig,ax=plt.subplots(figsize=(10.8,6.3))
    fig.subplots_adjust(left=.32,right=.97,top=.78,bottom=.30)
    ys=np.arange(4)
    for var,offset,color,label in [
        ('government_distrust',-.12,'#b85b38','Недоверие правительству'),
        ('party_distrust',.12,'#176759','Недоверие партиям')]:
        x=d[d.variable.eq(var)].set_index('outcome').reindex(range(4))
        vals=x.probability_difference.to_numpy()*100
        low=x.ci_low.to_numpy()*100;high=x.ci_high.to_numpy()*100
        ax.errorbar(vals,ys+offset,xerr=np.vstack([vals-low,high-vals]),fmt='o',
                    color=color,markersize=7,capsize=3,linewidth=2,label=label)
    ax.set_yticks(ys,['Голос за правящие партии','Голос за другую оппозицию',
                     'Голос за популистскую оппозицию','Неучастие в выборах'])
    ax.tick_params(axis='y',length=0,pad=13)
    ax.invert_yaxis();ax.set_ylim(3.5,-.5)
    ax.axvline(0,color='#7a8991',linewidth=1)
    ax.set_xlim(-22,14);ax.set_xticks([-20,-15,-10,-5,0,5,10])
    ax.grid(axis='x',alpha=.13);ax.set_axisbelow(True)
    ax.set_xlabel('Разница предсказанной вероятности, процентные пункты',labelpad=13)
    fig.text(.055,.94,'Кому не доверяют и какой выбор сообщают',fontsize=19,fontweight='bold')
    fig.text(.055,.885,'Европейские выборы 2009 года · 19 стран · 15 963 участника',fontsize=12,color='#52616b')
    fig.legend(loc='upper left',bbox_to_anchor=(.31,.865),ncol=2,frameon=False,fontsize=10.5)
    fig.text(.055,.14,'Сравнение недоверия с доверием при учёте экономики, приоритетов, второго вида доверия,',fontsize=10,color='#52616b')
    fig.text(.055,.105,'страны и социально-демографических характеристик. Линии: 95% интервалы, повторная выборка стран.',fontsize=10,color='#52616b')
    fig.text(.055,.06,'Установки измерены после выборов. Это условные связи, не причинные эффекты. Источник: Eurobarometer 71.3.',fontsize=9.4,color='#52616b')
    fig.text(.055,.025,'Партии: PopuList 4.0 с пограничными случаями. Неопределённые партийные ответы исключены.',fontsize=8.8,color='#52616b')
    for suffix in ['svg','png']:
        fig.savefig(FIG/f'eb2009_trust_outcomes_ru.{suffix}',dpi=170,facecolor='white',
                    metadata={'Date':None} if suffix=='svg' else {})
        if suffix=='svg':
            path=FIG/'eb2009_trust_outcomes_ru.svg'
            path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
    plt.close(fig)
    print('Saved',FIG/'eb2009_trust_outcomes_ru.png')

if __name__=='__main__':main()
