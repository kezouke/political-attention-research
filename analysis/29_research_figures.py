"""Publication figures from committed aggregates; no raw inputs required."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data/processed';FIG=ROOT/'docs/figures'
FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none','svg.hashsalt':'political-research-20261106',
                     'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#cbd5cf',
                     'axes.labelcolor':'#344c48','text.color':'#172525','xtick.color':'#526463','ytick.color':'#526463'})
TEAL,ORANGE,GRAY='#176759','#b65b35','#8d98ab'
NAMES={'BEL':'Бельгия','DEU':'Германия','DNK':'Дания','ESP':'Испания','FIN':'Финляндия',
       'GBR':'Великобритания','GRC':'Греция','IRL':'Ирландия','ISL':'Исландия','ITA':'Италия',
       'JPN':'Япония','LVA':'Латвия','NLD':'Нидерланды','PRT':'Португалия','ROU':'Румыния'}


def save(fig,name,lang):
    fig.savefig(FIG/f'{name}-{lang}.svg',bbox_inches='tight',facecolor='white',metadata={'Date':None})
    plt.close(fig)


def horizon(lang,mobile=False):
    d=pd.read_csv(DATA/'crisis_dynamics_balanced.csv')
    fig,ax=plt.subplots(figsize=(5.0,5.8) if mobile else (8.7,5.7))
    for r in d.itertuples():
        ax.plot([0,1],[r.change_pp_first,r.change_pp_second],color=TEAL,alpha=.16,lw=1)
        ax.scatter([0,1],[r.change_pp_first,r.change_pp_second],c=TEAL,s=21,alpha=.45,edgecolors='white',linewidths=.4,zorder=3)
    med=d[['change_pp_first','change_pp_second']].median().to_numpy()
    ax.plot([0,1],med,c='#172525',lw=3,zorder=4,marker='D',ms=7)
    for x,y in enumerate(med):ax.annotate(f'{y:+.2f}'.replace('.',',' if lang=='ru' else '.'),(x,y),xytext=(10,-17),textcoords='offset points',weight='bold',fontsize=11 if mobile else 13)
    es=d[d.iso.eq('ESP')].iloc[0]
    ax.plot([0,1],[es.change_pp_first,es.change_pp_second],c=ORANGE,lw=2,zorder=3)
    ax.annotate('Испания' if lang=='ru' else 'Spain',(1,es.change_pp_second),xytext=(10,0),textcoords='offset points',color=ORANGE,fontsize=10 if mobile else 11)
    ax.axhline(0,c='#526463',lw=.8,ls=':');ax.set_xlim(-.12,1.35)
    ax.set_xticks([0,1],['Первые выборы','Вторые выборы'] if lang=='ru' else ['First election','Second election'])
    ylabel=('Изменение доли популистов, п. п.' if lang=='ru' else 'Populist vote change, pp') if mobile else ('Изменение доли популистов от докризисных выборов, п. п.' if lang=='ru' else 'Populist vote change from the pre-crisis election, pp')
    ax.set_ylabel(ylabel)
    ax.text(.02,1.04,'29 эпизодов · чёрная линия: медиана' if lang=='ru' else '29 episodes · black line: median',transform=ax.transAxes,fontsize=11)
    ax.grid(axis='y',alpha=.16);save(fig,'horizon'+('-mobile' if mobile else ''),lang)


def decomposition(lang,topic,mobile=False):
    d=pd.read_csv(DATA/'programme_decomposition.csv')
    d=d[d['sample'].eq('main')&d.kind.eq('banking')&d.topic.eq(topic)].sort_values('change_pp')
    fig,ax=plt.subplots(figsize=(5.1,9.5) if mobile else (9.2,7.7));y=np.arange(len(d));positive=np.zeros(len(d));negative=positive.copy()
    labels=['Изменения программ','Перераспределение голосов','Изменение состава записей'] if lang=='ru' else ['Programme changes','Vote reweighting','Record-roster change']
    for field,color,label in zip(['within_pp','reweight_pp','roster_pp'],[TEAL,ORANGE,GRAY],labels):
        vals=d[field].to_numpy();left=np.where(vals>=0,positive,negative)
        ax.barh(y,vals,left=left,height=.35 if mobile else .58,color=color,label=label)
        positive+=np.maximum(vals,0);negative+=np.minimum(vals,0)
    ax.scatter(d.change_pp,y,marker='D',s=25,c='#172525',zorder=4,label='Общий сдвиг' if lang=='ru' else 'Net change')
    ax.axvline(0,c='#526463',lw=.8)
    names=[f'{NAMES.get(r.iso,r.country) if lang=="ru" else r.country} {int(r.onset_year)}' for r in d.itertuples()]
    if mobile:
        ax.set_yticks([]);ax.spines['left'].set_visible(False)
        for pos,name in zip(y,names):ax.text(.01,pos+.32,name,transform=ax.get_yaxis_transform(),fontsize=10.5,va='center')
        ax.set_ylim(-.6,len(d)-.1)
    else:ax.set_yticks(y,names,fontsize=10)
    ax.set_xlabel(('Вклад, п. п. текста' if lang=='ru' else 'Contribution, pp of text') if mobile else ('Вклад в изменение доли темы, п. п. текста' if lang=='ru' else 'Contribution to the topic-share change, pp of text'))
    ax.legend(loc='lower left' if mobile else 'lower center',bbox_to_anchor=(0,1.02) if mobile else (.43,1.01),ncol=1 if mobile else 2,frameon=False,fontsize=9.5)
    ax.grid(axis='x',alpha=.15);save(fig,'decomposition-'+topic+('-mobile' if mobile else ''),lang)


def spain(lang,mobile=False):
    d=pd.read_csv(DATA/'programme_decomposition.csv');d=d[d['sample'].eq('main')&d.iso.eq('ESP')]
    topics=['economy','welfare_expansion','orthodoxy','anticorruption']
    titles=['Экономика: все основные категории','Расширение социальных расходов','Финансовая дисциплина','Борьба с коррупцией'] if lang=='ru' else ['Core economic categories','Welfare expansion','Economic orthodoxy','Anticorruption']
    if mobile:titles=['Экономические\nкатегории','Расширение\nсоциальных расходов','Финансовая\nдисциплина','Борьба\nс коррупцией'] if lang=='ru' else ['Core economic\ncategories','Welfare\nexpansion','Economic\northodoxy','Anticorruption']
    fig,axes=plt.subplots(2,2,figsize=(5.2,6.0) if mobile else (8.8,5.8))
    for ax,topic,title in zip(axes.flat,topics,titles):
        a=d[d.kind.eq('banking')&d.topic.eq(topic)].iloc[0];b=d[d.kind.eq('second')&d.topic.eq(topic)].iloc[0]
        vals=[a.pre_share,a.post_share,b.post_share]
        ax.plot([0,1,2],vals,c=TEAL,lw=2,marker='o',ms=6)
        for x,y in enumerate(vals):ax.annotate(f'{y:.1f}%'.replace('.',',' if lang=='ru' else '.'),(x,y),xytext=(0,9),ha='center',textcoords='offset points',fontsize=10)
        ax.set_xticks([0,1,2],['2008','2011','2015']);ax.set_ylim(0,max(vals)*1.35)
        ax.set_title(title,fontsize=11,pad=14,loc='left');ax.grid(axis='y',alpha=.14)
        if mobile:ax.tick_params(axis='both',labelsize=9)
    fig.tight_layout(h_pad=3,w_pad=2 if mobile else 3);save(fig,'spain-policies'+('-mobile' if mobile else ''),lang)


def prediction(lang,mobile=False):
    d=pd.read_csv(DATA/'programme_prediction.csv')
    fig,ax=plt.subplots(figsize=(5.0,4.8) if mobile else (8.4,4.4));years=sorted(d.test_start.unique());x=np.arange(len(years))
    for off,model,col,label in [(-.25,'no_change',GRAY,'Без изменения голосов' if lang=='ru' else 'No vote change'),
                                (0,'baseline',ORANGE,'Базовая модель' if lang=='ru' else 'Baseline'),
                                (.25,'programme_changes',TEAL,'С данными программ' if lang=='ru' else 'With programme features')]:
        vals=d[d.model.eq(model)].set_index('test_start').loc[years,'election_mae']
        ax.bar(x+off,vals,width=.23,color=col,label=label)
    ax.set_xticks(x,[f'{y}–{str(y+4)[-2:]}' if mobile else f'{y}–{y+4}' for y in years]);ax.set_ylim(0,6)
    ax.set_ylabel(('Ошибка, п. п. голосов' if lang=='ru' else 'Absolute error, pp of votes') if mobile else ('Средняя абсолютная ошибка, п. п. голосов' if lang=='ru' else 'Mean absolute error, pp of votes'))
    ax.legend(frameon=False,fontsize=9,loc='lower left',bbox_to_anchor=(0,1.01)) if mobile else ax.legend(frameon=False,fontsize=9,loc='upper left')
    ax.grid(axis='y',alpha=.15);save(fig,'prediction'+('-mobile' if mobile else ''),lang)


if __name__=='__main__':
    for lang in ['ru','en']:
        for mobile in [False,True]:
            horizon(lang,mobile)
            for topic in ['economy','anticorruption','environment']:decomposition(lang,topic,mobile)
            spain(lang,mobile);prediction(lang,mobile)
