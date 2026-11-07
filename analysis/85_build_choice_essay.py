"""Build the single bilingual research essay from prose and checked aggregates."""
from pathlib import Path
import html
import re
import pandas as pd
from markdown_it import MarkdownIt

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'
DATA=ROOT/'data/processed'
P=DATA/'three_explanations'
REPO='https://github.com/kezouke/political-attention-research'
MD=MarkdownIt('commonmark',{'html':True}).enable('table')
TITLES={'ru':'После кризиса: кому достаётся недовольство?',
        'en':'After a crisis, who receives discontent?'}
DECK={'ru':'Потеря голосов правительством, поддержка популистов и неучастие имеют разные связи с экономикой и доверием. Мы проверили их на международных данных и повторных опросах одних и тех же людей.',
      'en':'Government losses, populist support and abstention have different relationships with the economy and trust. We test them using international data and repeated surveys of the same people.'}
FIGURES={
 'horizon':{
  'file':'horizon',
  'ru':('Поздний сдвиг заметнее, но не одинаков во всех кризисах',
        'Каждая тонкая линия соединяет первые и вторые выборы одного из 29 эпизодов. Изменение относительно последних докризисных выборов. Чёрная линия: медиана. Это порядок выборов, а не ежегодная траектория. Начало кризисов: 1991–2008; вторые выборы: 1997–2018. Классификация кампаний: WPD.'),
  'en':('Later gains are larger, but crises differ',
        'Each thin line joins the first and second elections for one of 29 episodes. Changes use the last pre-crisis election as baseline. Black line: median. These are successive elections, not annual trajectories. Crisis onsets: 1991–2008; second elections: 1997–2018. Campaign classification: WPD.')},
 'europe':{
  'file':'choice-europe',
  'ru':('У общего недоверия партиям выделяется неучастие',
        'Eurobarometer 2009: 15 962 человека, 19 стран. Недоверие вместо доверия при сохранении остальных признаков. Линии: 95%-ные интервалы из 1 000 повторных выборок стран. Страны имеют одинаковый вес. Все установки измерены после выборов. PopuList 4.0 включает пограничные случаи; популистские партии кабинета входят в исход «партии кабинета».'),
  'en':('Abstention stands out for general distrust of parties',
        'Eurobarometer 2009: 15,962 people in 19 countries. Distrust rather than trust, retaining other characteristics. Lines: 95% intervals from 1,000 country resamples. Countries have equal weight. Attitudes follow the election. PopuList 4.0 includes borderline cases; populist cabinet parties belong to the cabinet outcome.')},
 'before':{
  'file':'choice-before',
  'ru':('Повторные ответы сохраняют связь с неучастием',
        'BES: позднее доверие депутатам 3 вместо 5 на шкале 1–7 при одинаковых ранних установках и намерении. Остальные поздние установки также учтены. Показаны два из четырёх совместных исходов. Линии: 95%-ные интервалы, 1 000 повторных выборок людей. UKIP и Brexit Party классифицированы по PopuList. Это условные разницы, не наблюдённые переходы избирателей.'),
  'en':('Repeated answers retain an association with abstention',
        'BES: later trust in MPs at 3 rather than 5 on a 1–7 scale, conditional on early attitudes and intention. Other later attitudes are also included. Two of four jointly modelled outcomes are shown. Lines: 95% intervals, 1,000 participant resamples. PopuList classifies UKIP and the Brexit Party. These are conditional differences, not observed voter transitions.')},
 'countries':{
  'file':'choice-countries',
  'ru':('Получатели недоверия различаются между опросами',
        'Совместные модели исходов, PopuList 4.0 с пограничными случаями. Недоверие 0,75 вместо 0,25 на приведённой шкале 0–1; вопросы между странами различаются. Линии: 95%-ные интервалы из 1 000 повторных выборок людей, без полного восстановления дизайна обследований. Отсутствующая популистская точка в Португалии означает отсутствие категории в модели, а не нулевую оценку. Испанские смешанные списки в основном варианте не классифицированы. Бельгия, Исландия и Португалия 2009: без весов; остальные используют проверенные веса.'),
  'en':('Recipients of distrust differ across surveys',
        'Joint outcome models, PopuList 4.0 including borderline cases. Distrust at 0.75 rather than 0.25 on a rescaled 0–1 scale; questions differ across countries. Lines: 95% intervals from 1,000 participant resamples, not a reconstruction of the full survey design. Missing Portuguese populist points mean an absent model category, not a zero estimate. Spanish mixed lists are unclassified in the primary analysis. Belgium, Iceland and Portugal 2009 are unweighted; other surveys use verified weights.')},
 'programmes':{
  'file':'decomposition-economy',
  'ru':('Общая доля экономических тем меняется несколькими способами',
        '16 кризисных эпизодов, программы представляют не менее 75% голосов на обоих концах. Показан переход от последних докризисных к первым послекризисным выборам, в отличие от двух горизонтов первого графика. Точка: общий сдвиг доли закодированных экономических высказываний. Состав записей включает как появление партий, так и пропуски документов и изменения идентификаторов. Это доли текста, не приоритеты граждан.'),
  'en':('Several processes change the aggregate economic-topic share',
        'Sixteen crisis episodes, with programmes covering at least 75% of votes at both endpoints. This compares the last pre-crisis with the first post-crisis election, unlike the first chart’s two horizons. Diamond: net change in the coded economic-statement share. Record composition includes party entry, missing documents and identifier changes. These are text shares, not citizens’ priorities.')}
}

def bilingual(ru,en,cls='prose'):
    return ''.join(f'<div class="{cls}" lang="{lang}" data-copy="{lang}">{value}</div>'
                   for lang,value in [('ru',ru),('en',en)])

def numeric_table(kind,lang):
    ru=lang=='ru'
    outcomes={0:'Партии кабинета' if ru else 'Cabinet parties',
              1:'Другие вне кабинета' if ru else 'Other outside cabinet',
              2:'Популисты вне кабинета' if ru else 'Populists outside cabinet',
              3:'Неучастие' if ru else 'Abstention'}
    if kind=='horizon':
        d=pd.read_csv(DATA/'crisis_dynamics_balanced.csv')
        d=d[['iso','onset_year','date_first','change_pp_first','date_second','change_pp_second']]
        d.columns=['ISO','Кризис','Первые выборы','Сдвиг, п. п.','Вторые выборы','Сдвиг, п. п.'] if ru else ['ISO','Crisis','First election','Change, pp','Second election','Change, pp']
    elif kind=='programmes':
        d=pd.read_csv(DATA/'programme_decomposition.csv')
        d=d[d['sample'].eq('main')&d.kind.eq('banking')&d.topic.eq('economy')]
        d=d[['iso','onset_year','change_pp','within_pp','reweight_pp','roster_pp','pre_coverage','post_coverage']]
        d.columns=['ISO','Кризис','Всего, п. п.','Программы','Голоса','Состав','Охват до, %','Охват после, %'] if ru else ['ISO','Crisis','Total, pp','Programmes','Votes','Roster','Coverage before, %','Coverage after, %']
    else:
        if kind=='europe':
            d=pd.read_csv(P/'eb_v2/eb_model_margins.csv')
            d=d[d.target.eq('four_outcomes')&d.variable.isin(['government_distrust','party_distrust'])].copy()
            d['comparison']=d.variable.map({'government_distrust':'Правительство' if ru else 'Government','party_distrust':'Партии' if ru else 'Parties'})
        elif kind=='before':
            d=pd.read_csv(P/'bes_change_model_margins.csv')
            d=d[d.target.eq('four_outcomes')&d.variable.eq('politician_distrust')&d.outcome.isin([2,3])].copy()
            d['comparison']=d.year.astype(str)
        else:
            d=pd.read_csv(P/'national_model_margins.csv')
            d=d[d.target.eq('all_outcomes')&d.variable.eq('elite_distrust')&d.outcome.isin([2,3])].copy()
            d['comparison']=d.dataset
        d['outcome']=d.outcome.map(outcomes)
        for c in ['probability_difference','ci_low','ci_high']:d[c]*=100
        d=d[['comparison','outcome','n','probability_difference','ci_low','ci_high']]
        d.columns=['Сравнение','Исход','Человек','Разница, п. п.','Нижняя 95%','Верхняя 95%'] if ru else ['Comparison','Outcome','People','Difference, pp','Lower 95%','Upper 95%']
    return '<div class="table-scroll">'+d.to_html(index=False,border=0,float_format=lambda x:f'{x:.2f}',escape=True)+'</div>'

def figure(kind):
    cfg=FIGURES[kind];f=cfg['file'];parts=[]
    for lang in ['ru','en']:
        title,caption=cfg[lang]
        parts.append(f'<div data-copy="{lang}" lang="{lang}"><h3>{title}</h3>'
            f'<picture><source media="(max-width:600px)" srcset="figures/{f}-mobile-{lang}.svg">'
            f'<img src="figures/{f}-{lang}.svg" alt="{html.escape(title)}" loading="lazy" width="920"></picture>'
            f'<figcaption>{caption}</figcaption>'
            '<details><summary>'+('Числа и охват' if lang=='ru' else 'Values and coverage')+'</summary>'
            +numeric_table(kind,lang)+'</details></div>')
    return f'<figure class="figure" id="figure-{kind}">'+''.join(parts)+'</figure>'

def sections(lang):
    raw=(ROOT/f'article/essay.{lang}.md').read_text()
    pairs=re.split(r'<!-- section: ([a-z]+) -->',raw)
    assert not pairs[0].strip()
    return {pairs[i]:pairs[i+1].strip() for i in range(1,len(pairs),2)}

def render_pair(ru,en):
    a=re.split(r'<!-- figure: ([a-z]+) -->',ru)
    b=re.split(r'<!-- figure: ([a-z]+) -->',en)
    assert len(a)==len(b) and a[1::2]==b[1::2]
    result=bilingual(MD.render(a[0]),MD.render(b[0]))
    for i in range(1,len(a),2):
        result+=figure(a[i])+bilingual(MD.render(a[i+1]),MD.render(b[i+1]))
    return result

def methods():
    ru=f'''### Как проверены выводы

Основные сравнения заданы до соответствующих расчётов. Это продолжение разведочного проекта, а не полностью пререгистрированное исследование. Ранее просмотренные результаты и последующие уточнения отмечены в [протоколе]({REPO}/blob/main/planning/analysis-protocol-v1.md). Проверены альтернативные партийные классификации, коалиции, формулировки приоритетов, веса, исходные предпочтения, наблюдаемый отбор в панели и перенос прогнозов. Коррупционные скандалы, бюджетные сокращения и индивидуальная доступность кандидатов не устранены единым сопоставимым контролем. Большое число людей не заменяет число независимых стран.

Логистические модели используют слабую регуляризацию; нелинейный ориентир проверен отдельно для европейского среза и британской панели. Улучшение прогноза оценивается на людях или выборах, не использованных для обучения соответствующей модели. Log loss штрафует уверенные ошибочные вероятности. Критерий полезной добавки: снижение этой ошибки не менее чем на 1% при положительной нижней границе интервала. Для послевыборных опросов это проверка обобщения внутри данных, не прогноз заранее. Интервалы проверки качества используют повторные выборки фиксированных ошибок без нового обучения моделей; опросные интервалы не включают всю неопределённость дизайна и измерений.

Дополнительное связанное сравнение Германии 2009/2013 содержит 360 человек после всех ограничений. В этой отобранной группе экономические оценки улучшились и экономический приоритет снизился, но недоверие не снизилось аналогично. Малые группы и отбор не позволяют считать это общеевропейской причинной проверкой. Полные результаты: [общий срез]({REPO}/blob/main/EUROPEAN_RESULTS_V2.md), [Великобритания]({REPO}/blob/main/FIRST_BES_RESULTS.md), [Германия]({REPO}/blob/main/FIRST_GLES_RESULTS.md), [другие национальные опросы]({REPO}/blob/main/NATIONAL_RESULTS.md).

### Что дали программы и машинное обучение

Смена инструкций кодирования затрагивает восемь из 16 программных эпизодов; требование одинаковых инструкций и достаточного покрытия оставляет только четыре. Это ограничивает точность сравнения тем. Сохранён и отрицательный прогнозный результат 2023a: добавление тем программ не улучшило среднюю абсолютную ошибку на 89 парах выборов в 27 странах, 4,17 против 4,15 п. п. у базовой модели.

Отдельный пересчёт по Manifesto Project 2026a сохраняет те же 16 кризисных эпизодов, восемь ростов и восемь снижений экономической доли, а также 10 случаев преобладания изменения текстов. Ни один знак кризисного сдвига не меняется; наибольшая разница оценки меньше 0,003 п. п. Состав спокойных интервалов изменился: два выбыли и два добавились. На 73 общих интервалах компонент изменения текстов крупнейший в 49 случаях по старому выпуску и в 50 по новому; на всём новом наборе это 52 из 75. [Сравнение выпусков]({REPO}/blob/main/MANIFESTO_REFRESH.md) сохраняет исходные значения и объясняет изменения покрытия. Оно проверяет версию источника, не причинный механизм; прогнозный эксперимент на 89 парах здесь не пересчитывался.

В отдельном испанском тесте многоязычный E5-small с линейным классификатором дал macro-F1 0,588 против 0,482 у TF–IDF на 3 636 фрагментах отложенной программы. Один документ не проверяет перенос между странами и не валидирует распознавание обвинений элит. Поиск в Hugging Face и публичных архивах не дал подходящего независимого многоязычного эталона таких обвинений. Поэтому новая автоматическая мера не подставлена в основные выводы. [Аудит данных]({REPO}/blob/main/DATA_AUDIT_2026.md) сохраняет найденные источники и причины исключений.

### Источники и воспроизводимость

Eurobarometer 71.3: [ZA4973 v3.0.0](https://doi.org/10.4232/1.11135). GLES: [2009](https://doi.org/10.4232/1.12198), [2013](https://doi.org/10.4232/1.12561), [связанный выпуск](https://doi.org/10.4232/1.12536). BES: [teaching v1](https://doi.org/10.48420/25460980.v1). Национальные источники, версии и коды вопросов перечислены в методах. Кампании WPD и партии PopuList имеют разные единицы и пороги охвата; отсутствие партии в списке не автоматически означает отрицательную метку.

Графики и страницу можно восстановить из открытых агрегатов. Микроданные и свободные ответы не публикуются; для повтора анализа нужно самостоятельно получить исходные файлы по условиям поставщиков. ИИ использовался при подготовке кода и текста; независимой экспертной рецензии не было. [Методы и порядок воспроизведения]({REPO}/blob/main/CHOICE_METHODS.md) · [Проверка утверждений и переходов]({REPO}/blob/main/CHOICE_AUDIT.md) · [Таблицы результатов]({REPO}/tree/main/data/processed/three_explanations).
'''
    en=f'''### How the conclusions were checked

Main comparisons were specified before their respective model runs. This continues an exploratory project; it is not fully preregistered. Previously viewed results and subsequent decisions are recorded in the [protocol]({REPO}/blob/main/planning/analysis-protocol-v1.md). Checks cover party definitions, coalitions, priority wording, weights, initial preferences, observed panel selection and prediction transfer. Corruption scandals, fiscal cuts and individual candidate availability have not been eliminated by a common comparable control. Many people do not substitute for independent countries.

Logistic models use weak regularisation; a nonlinear benchmark is evaluated separately for the European cross-section and British panel. Predictive improvement is assessed on people or elections not used to train the corresponding model. Log loss penalises confidently wrong probabilities. Useful improvement requires at least a 1% reduction and a positive interval lower bound. Post-election surveys test generalisation within the data, not advance forecasting. Validation intervals resample fixed held-out losses without refitting; survey intervals do not include all design and measurement uncertainty.

An additional linked German 2009/2013 comparison retains 360 people. In this selected group, economic assessments improved and economic priority declined, without a corresponding decline in distrust. Small groups and selection prevent interpreting this as a European causal test. Full results: [common survey]({REPO}/blob/main/EUROPEAN_RESULTS_V2.md), [Britain]({REPO}/blob/main/FIRST_BES_RESULTS.md), [Germany]({REPO}/blob/main/FIRST_GLES_RESULTS.md), [additional national surveys]({REPO}/blob/main/NATIONAL_RESULTS.md).

### What programmes and machine learning contributed

Coding-instruction changes affect eight of the 16 programme episodes; requiring identical instructions and sufficient coverage leaves only four. This limits topic comparisons. We also retain a negative 2023a prediction result: programme topics did not improve mean absolute error across 89 election pairs in 27 countries, at 4.17 versus the baseline’s 4.15 vote-share points.

A separate replay using Manifesto Project 2026a retains the same 16 crisis episodes, eight increases and eight decreases in economic content, and 10 cases where programme revisions are the largest component. No crisis change reverses sign; the largest estimate revision is below 0.003 percentage points. The calm sample changes: two intervals leave and two enter. Among 73 shared intervals, programme revision is the largest component in 49 cases under the old release and 50 under the new one; across the full new sample it is 52 of 75. The [release comparison]({REPO}/blob/main/MANIFESTO_REFRESH.md) preserves the baseline and explains the coverage changes. This checks source-version sensitivity, not a causal mechanism; the 89-pair prediction experiment was not rerun here.

In a separate Spanish benchmark, multilingual E5-small with a linear classifier achieved macro-F1 of 0.588 versus TF–IDF’s 0.482 on 3,636 statements from a held-out programme. One document does not validate cross-country transfer or elite-blame classification. Searches of Hugging Face and public archives did not produce a suitable independent multilingual elite-blame benchmark. No new automated measure was therefore inserted into the main findings. The [data audit]({REPO}/blob/main/DATA_AUDIT_2026.md) preserves candidate sources and exclusions.

### Sources and reproducibility

Eurobarometer 71.3: [ZA4973 v3.0.0](https://doi.org/10.4232/1.11135). GLES: [2009](https://doi.org/10.4232/1.12198), [2013](https://doi.org/10.4232/1.12561), [linked release](https://doi.org/10.4232/1.12536). BES: [teaching v1](https://doi.org/10.48420/25460980.v1). Methods list national sources, versions and question codes. WPD campaigns and PopuList parties have different units and coverage thresholds; an unlisted party does not automatically receive a negative label.

Figures and the page rebuild from public aggregates. Microdata and free-text answers are not redistributed; reproducing the analysis requires obtaining source files under their providers’ terms. AI assisted with code and text; there has been no independent peer review. [Methods and reproduction]({REPO}/blob/main/CHOICE_METHODS.md) · [Claim and transition audit]({REPO}/blob/main/CHOICE_AUDIT.md) · [Result tables]({REPO}/tree/main/data/processed/three_explanations).
'''
    return '<section class="section" id="methods"><details class="methods-details"><summary><span data-copy="ru">Методы, дополнительные проверки и данные</span><span data-copy="en">Methods, additional checks and data</span></summary>'+bilingual(MD.render(ru),MD.render(en))+'</details></section>'

def main():
    ru,en=sections('ru'),sections('en');assert list(ru)==list(en)
    content='\n'.join(f'<section class="section" id="{anchor}">'+render_pair(ru[anchor],en[anchor])+'</section>' for anchor in ru)
    hero={lang:f'<p class="eyebrow">'+('Политическая экономия · опросы · модели' if lang=='ru' else 'Political economy · surveys · models')+f'</p><h1>{TITLES[lang]}</h1><p class="deck">{DECK[lang]}</p><p class="meta">'+('Елисей Смирнов · 7 ноября 2026 · Исследовательское эссе' if lang=='ru' else 'Elisei Smirnov · 7 November 2026 · Research essay')+'</p>' for lang in ['ru','en']}
    nav=[('horizon','После кризиса','After the crisis'),('europe','Получатели недовольства','Recipients of discontent'),('before','До голосования','Before voting'),('priorities','Приоритеты','Priorities'),('countries','Различия стран','Country differences'),('offers','Предложения партий','Party offers')]
    navigation='<nav class="contents" aria-label="Sections / Разделы">'+''.join(f'<a href="#{a}"><span data-copy="ru">{r}</span><span data-copy="en">{e}</span></a>' for a,r,e in nav)+'</nav>'
    page='''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>After a crisis, who receives discontent?</title>
<meta name="description" content="An original study of economic assessments, priorities, trust and political choice: 29 crises, a common European survey and national panels.">
<script>if(new URLSearchParams(location.search).get('lang')==='ru')document.documentElement.lang='ru';</script>
<link rel="stylesheet" href="choice.css?v=20261107"><script defer src="choice.js?v=20261107"></script></head>
<body><a class="skip" href="#story"><span data-copy="ru">К тексту</span><span data-copy="en">Skip to the essay</span></a>
<header class="masthead"><a class="brand" href="#top">Political Attention Research</a><nav class="locale" aria-label="Language / Язык"><a href="?lang=en" hreflang="en" data-locale>EN</a><a href="?lang=ru" hreflang="ru" data-locale>RU</a></nav></header>
<div class="hero" id="top">'''+bilingual(hero['ru'],hero['en'],'hero-copy')+navigation+'</div><main id="story">'+content+methods()+f'''</main>
<footer class="footer"><div class="footer-inner"><p><a href="{REPO}"><span data-copy="ru">Репозиторий исследования</span><span data-copy="en">Research repository</span></a> · <a href="https://www.linkedin.com/in/elisei-smirnov-ds/">Elisei Smirnov</a></p></div></footer></body></html>'''
    (DOCS/'index.html').write_text(page)
    print('Built one bilingual essay with five figures and aggregate tables')

if __name__=='__main__':main()
