"""Export standalone review figures from verified aggregates only."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/processed/three_explanations'
OUT = ROOT / 'output/research_figures/verified_panels'
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'svg.fonttype': 'none',
                     'svg.hashsalt': 'political-attention-verified-panels',
                     'axes.spines.top': False, 'axes.spines.right': False, 'axes.spines.left': False,
                     'text.color': '#17252c', 'axes.labelcolor': '#17252c'})


def forest(filename, title, subtitle, series, limits, notes):
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.subplots_adjust(left=.31, right=.96, top=.76, bottom=.29)
    for offset, (label, color, data) in zip(np.linspace(-.18, .18, len(series)), series):
        x = data.set_index('outcome').reindex(range(4))
        val, low, high = [100 * x[c].to_numpy() for c in ['probability_difference', 'ci_low', 'ci_high']]
        ax.errorbar(val, np.arange(4) + offset, xerr=np.vstack([val - low, high - val]),
                    fmt='o', color=color, capsize=3, markersize=6, linewidth=1.7, label=label)
    ax.set_yticks(range(4), ['Правящие партии', 'Обычная оппозиция', 'Популистская оппозиция', 'Неучастие'])
    ax.tick_params(axis='y', length=0, pad=12)
    ax.set_ylim(3.5, -.5); ax.set_xlim(*limits)
    ax.axvline(0, color='#7b8990', lw=1)
    ax.grid(axis='x', alpha=.15); ax.set_axisbelow(True)
    ax.set_xlabel('Условная разница вероятности, процентные пункты', labelpad=13)
    fig.text(.05, .94, title, fontsize=19, fontweight='bold')
    fig.text(.05, .884, subtitle, fontsize=11.5, color='#52616b')
    fig.legend(loc='upper left', bbox_to_anchor=(.30, .85), ncol=len(series), frameon=False)
    for i, line in enumerate(notes):
        fig.text(.05, .17 - i * .043, line, fontsize=9.3, color='#52616b')
    for suffix in ['png', 'svg']:
        path = OUT / (filename + '.' + suffix)
        fig.savefig(path, dpi=170, facecolor='white', metadata={'Date': None} if suffix == 'svg' else {})
        if suffix == 'svg': path.write_text('\n'.join(s.rstrip() for s in path.read_text().splitlines()) + '\n')
    plt.close(fig)


def main():
    eb = pd.read_csv(DATA / 'eb_v2/eb_model_margins.csv').query("target == 'four_outcomes'")
    assert eb.n.eq(15962).all()
    forest('eb2009_trust_v2_ru', 'Недоверие правительству и партиям связано с разными исходами',
           'Eurobarometer 71.3 · Европейские выборы 2009 года · 19 стран · 15 962 участника',
           [('Правительству', '#b85b38', eb[eb.variable.eq('government_distrust')]),
            ('Партиям', '#176759', eb[eb.variable.eq('party_distrust')])], (-22, 14),
           ['Недоверие вместо доверия; экономика, приоритет, второй вид доверия, страна и социальные признаки учтены.',
            'Линии: 95%-ные интервалы, 1 000 повторных выборок стран. Страны имеют одинаковый суммарный вес.',
            'Ответы получены после выборов. Это условные связи. PopuList 4.0 включает пограничные случаи.',
            'Исправленная версия 2: неоднозначный шотландский ответ Greens оставлен неопределённым.'])
    bes = pd.read_csv(DATA / 'bes_model_margins.csv').query("target == 'four_outcomes' and variable == 'politician_distrust'")
    forest('bes_distrust_outcomes_ru', 'Предвыборное недоверие не означает одинакового ухода от власти',
           'British Election Study · Доверие депутатам 3 вместо 5 на шкале 1–7 · Последующий сообщённый голос',
           [(str(year), color, bes[bes.year.eq(year)]) for year, color in [(2015, '#176759'), (2017, '#b85b38'), (2019, '#506aa3')]],
           (-4.5, 3.2),
           ['Учтены исходное намерение, партийная идентичность, экономика, неодобрение правительства, приоритет и контроли.',
            'Линии: 95%-ные интервалы, 1 000 повторных выборок людей. N: 23 447 (2015), 17 100 (2017), 19 324 (2019).',
            'Установки предшествуют голосованию. Связь не является причинным эффектом; отбор в панель остаётся ограничением.',
            'Популистская оппозиция: UKIP и Brexit Party по PopuList. Неизвестная партия не приравнивается к неучастию.'])
    print(OUT)


if __name__ == '__main__': main()
