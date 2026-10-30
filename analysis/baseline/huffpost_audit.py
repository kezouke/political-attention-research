"""Audit dataset coverage; descriptive keyword counts are not validated labels."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import pandas as pd

root = Path(__file__).parent
patterns = {
    'climate': r'\b(?:climate change|global warming|greenhouse gases)\b',
    'immigration': r'\b(?:immigra\w*|migrants?|deport\w*|asylum|refugees?)\b',
    'prices': r'\b(?:inflation|cost of living|consumer prices|food prices)\b',
    'identity': r'\b(?:lgbtq?\w*|gay|lesbian|transgender|same.sex marriage|racism)\b',
}
totals = Counter()
categories = Counter()
matches = Counter()
examples = defaultdict(list)
with (root / 'data/huffpost_v3.jsonl').open() as stream:
    for line in stream:
        article = json.loads(line)
        year = int(article['date'][:4])
        category = article['category']
        headline = article['headline']
        totals[year] += 1
        categories[(year, category)] += 1
        for topic, pattern in patterns.items():
            if re.search(pattern, headline, re.I):
                matches[(year, topic)] += 1
                if len(examples[(year, topic)]) < 12:
                    examples[(year, topic)].append(headline)

out = root / 'outputs'
pd.DataFrame([{'year': y, 'articles': n} for y, n in sorted(totals.items())]).to_csv(out / 'huffpost_coverage.csv', index=False)
pd.DataFrame([{'year': y, 'category': c, 'articles': n} for (y, c), n in sorted(categories.items())]).to_csv(out / 'huffpost_categories.csv', index=False)
pd.DataFrame([{'year': y, 'topic': t, 'matches': matches[y, t], 'all_headlines': totals[y], 'per_10000': 10000 * matches[y, t] / totals[y]} for y in sorted(totals) for t in patterns]).to_csv(out / 'huffpost_keywords.csv', index=False)
pd.DataFrame([{'year': y, 'topic': t, 'headline': s} for (y, t), vals in examples.items() for s in vals]).to_csv(out / 'huffpost_examples.csv', index=False)
