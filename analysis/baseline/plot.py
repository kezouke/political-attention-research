import csv
from collections import defaultdict
import matplotlib.pyplot as plt
from pathlib import Path
p = Path(__file__).resolve().parent
series = defaultdict(list)
with (p / 'pew_points.csv').open(newline='') as f:
    for row in csv.DictReader(f):
        series[row['topic']].append((int(row['year']), int(row['percent'])))
fig, ax = plt.subplots(figsize=(9, 5.5))
colors = ['#218c78', '#9c5888', '#cb7340', '#5677a4']
for (topic, data), color in zip(series.items(), colors):
    data.sort()
    years, values = zip(*data)
    ax.plot(years, values, marker='o', linewidth=2, label=topic, color=color)
    for x, y in data:
        ax.annotate(str(y) + '%', (x, y), xytext=(5, 7), textcoords='offset points', fontsize=9)
ax.set(title='United States: very big national problems', ylabel='Share of adults (%)', xlabel='Year')
ax.set_xticks([2021, 2022, 2023, 2024])
ax.set_ylim(0, 80)
ax.grid(axis='y', alpha=.25)
ax.legend(frameon=False, ncol=2, loc='upper right')
fig.text(.1, .01, 'Pew Research Center, published May 23, 2024. Lines connect observed endpoints only.', fontsize=8)
fig.tight_layout(rect=[0, .05, 1, 1])
fig.savefig(p / 'pew_selected.png', dpi=180)
