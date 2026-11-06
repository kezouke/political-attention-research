"""Publication figures from checked aggregate tables, including mobile layouts."""
from pathlib import Path
import importlib.util
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/processed/three_explanations'
FIG=ROOT/'docs/figures'
REVIEW=ROOT/'output/research_figures/choice'
TEAL,ORANGE='#176759','#b65b35'
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':12,'svg.fonttype':'none',
    'svg.hashsalt':'choice-study-20261107','axes.spines.top':False,'axes.spines.right':False,
    'axes.spines.left':False,'axes.edgecolor':'#cbd5cf','axes.labelcolor':'#344c48',
    'text.color':'#172525','xtick.color':'#526463','ytick.color':'#344c48'})

def forest(name,lang,mobile,labels,series,limits):
    rows=len(labels)
    fig,ax=plt.subplots(figsize=(5.1,rows*.94+1.3) if mobile else (10,rows*.71+1.3))
    fig.subplots_adjust(left=.05 if mobile else .31,right=.96,top=.84 if rows<5 else .91,
                        bottom=.18 if rows<5 else .10)
    for i,(label,color,d) in enumerate(series):
        for row,r in enumerate(d):
            if r is None:continue
            x,lo,hi=[100*float(r[k]) for k in ['probability_difference','ci_low','ci_high']]
            assert lo<=x<=hi
            ax.errorbar(x,row+(-.12 if i==0 else .15),xerr=[[x-lo],[hi-x]],
                        fmt='o',color=color,capsize=2.7,ms=5.5,lw=1.5,
                        label=label if row==0 else None,zorder=3)
    ax.set_xlim(*limits);ax.set_ylim(rows-.5,-.6)
    ax.axvline(0,color='#84918b',lw=.9);ax.grid(axis='x',alpha=.14);ax.set_axisbelow(True)
    if mobile:
        ax.set_yticks([])
        for i,label in enumerate(labels):
            ax.text(.01,i-.40,label.replace('\n',' '),transform=ax.get_yaxis_transform(),
                    fontsize=13.5,va='center',bbox={'facecolor':'white','alpha':.88,'edgecolor':'none','pad':1})
    else:
        ax.set_yticks(range(rows),labels,fontsize=11.3);ax.tick_params(axis='y',length=0,pad=10)
    if mobile:ax.tick_params(axis='x',labelsize=12.5)
    ax.set_xlabel('Разница вероятности, п. п.' if lang=='ru' else 'Probability difference, pp',labelpad=10,fontsize=13 if mobile else 12)
    ax.legend(loc='lower left',bbox_to_anchor=(0,1.02),ncol=1 if mobile else 2,
              frameon=False,fontsize=14 if mobile else 11)
    suffix=f'{name}'+('-mobile' if mobile else '')+f'-{lang}'
    fig.savefig(FIG/f'{suffix}.svg',facecolor='white',metadata={'Date':None})
    fig.savefig(REVIEW/f'{suffix}.png',facecolor='white',dpi=140)
    plt.close(fig)

def main():
    FIG.mkdir(exist_ok=True);REVIEW.mkdir(parents=True,exist_ok=True)
    for file in ['national_checks.json','bes_change_checks.json']:
        assert (DATA/file).exists(),file
    eb=pd.read_csv(DATA/'eb_v2/eb_model_margins.csv').query("target == 'four_outcomes'")
    bes=pd.read_csv(DATA/'bes_change_model_margins.csv').query("target == 'four_outcomes' and variable == 'politician_distrust'")
    nat=pd.read_csv(DATA/'national_model_margins.csv').query("target == 'all_outcomes' and variable == 'elite_distrust'")
    assert eb.n.eq(15962).all() and nat.groupby('dataset').ngroups==8
    order=['ES2015','NL2010','NL2012','PT2005','PT2009','IS2013','BE2014','DK2007']
    country_ru=['Испания 2015','Нидерланды 2010','Нидерланды 2012','Португалия 2005',
                'Португалия 2009','Исландия 2013','Бельгия 2014','Дания 2007']
    country_en=['Spain 2015','Netherlands 2010','Netherlands 2012','Portugal 2005',
                'Portugal 2009','Iceland 2013','Belgium 2014','Denmark 2007']
    for lang in ['ru','en']:
        ru=lang=='ru'
        for mobile in [False,True]:
            outcome_labels=(['Партии кабинета','Другие партии\nвне кабинета','Популисты\nвне кабинета','Неучастие'] if ru else
                ['Cabinet parties','Other parties\noutside cabinet','Populists\noutside cabinet','Abstention'])
            series=[]
            for var,color,label in [('government_distrust',ORANGE,'Недоверие правительству' if ru else 'Distrust in government'),
                ('party_distrust',TEAL,'Недоверие партиям' if ru else 'Distrust in parties')]:
                d=eb[eb.variable.eq(var)].set_index('outcome')
                series.append((label,color,[d.loc[i] for i in range(4)]))
            forest('choice-europe',lang,mobile,outcome_labels,series,(-23,15))
            series=[]
            for outcome,color,label in [(2,TEAL,'Популистский голос' if ru else 'Populist vote'),
                                        (3,ORANGE,'Неучастие' if ru else 'Abstention')]:
                d=bes[bes.outcome.eq(outcome)].set_index('year')
                series.append((label,color,[d.loc[y] for y in [2015,2017,2019]]))
            forest('choice-before',lang,mobile,['2015 · n = 15 613','2017 · n = 8 758','2019 · n = 3 111'],series,(-.6,4))
            series=[]
            for outcome,color,label in [(2,TEAL,'Популистский голос' if ru else 'Populist vote'),
                                        (3,ORANGE,'Неучастие' if ru else 'Abstention')]:
                d=nat[nat.outcome.eq(outcome)].set_index('dataset')
                series.append((label,color,[d.loc[k] if k in d.index else None for k in order]))
            forest('choice-countries',lang,mobile,country_ru if ru else country_en,series,(-12,16))
    # Preserve historical definitions and regenerate both desktop/mobile versions.
    spec=importlib.util.spec_from_file_location('historical_figures',ROOT/'analysis/29_research_figures.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans']})
    original_save=old.save
    def readable_save(fig,name,lang):
        if '-mobile' in name:
            from matplotlib.text import Text
            for text in fig.findobj(Text):text.set_fontsize(text.get_fontsize()*1.25)
        original_save(fig,name,lang)
    old.save=readable_save
    for lang in ['ru','en']:
        for mobile in [False,True]:
            old.horizon(lang,mobile)
            old.decomposition(lang,'economy',mobile)
    for pattern in ['choice-*.svg','horizon-*.svg','decomposition-economy-*.svg']:
        for path in FIG.glob(pattern):
            path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
    print('Exported five figures in both languages and screen layouts')

if __name__=='__main__':main()
