"""Compare the same 2021–2022 inflation episode across available SPES countries.

This is a descriptive paired comparison, not an effect of inflation. Eurobarometer
fieldwork dates and exposure to the shock differ, and country observations share
common causes. The Fisher interval assumes independent country pairs and is used
only to show how imprecise the cross-country association is.
"""

from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[1]
raw = pd.read_csv(ROOT / 'data/processed/macro_issue_panel.csv')
paired = raw.loc[raw.year.isin([2021, 2022])].pivot(
    index=['country_name', 'iso'], columns='year', values=['price', 'inflation']
)
paired.columns = [f'{variable}_{year}' for variable, year in paired.columns]
paired = paired.dropna().reset_index()
paired['price_change_pp'] = paired.price_2022 - paired.price_2021
paired['inflation_change_pp'] = paired.inflation_2022 - paired.inflation_2021
paired = paired.sort_values('country_name')

n = len(paired)
r, p = pearsonr(paired.inflation_change_pp, paired.price_change_pp)
rho, _ = spearmanr(paired.inflation_change_pp, paired.price_change_pp)
z = np.arctanh(r)
interval = np.tanh([z - 1.96 / np.sqrt(n - 3), z + 1.96 / np.sqrt(n - 3)])
summary = pd.DataFrame([{
    'start_year': 2021, 'end_year': 2022, 'countries': n,
    'countries_price_rise': int((paired.price_change_pp > 0).sum()),
    'min_price_change_pp': paired.price_change_pp.min(),
    'median_price_change_pp': paired.price_change_pp.median(),
    'max_price_change_pp': paired.price_change_pp.max(),
    'pearson_r_delta_inflation_delta_price': r,
    'pearson_fisher_low_iid': interval[0],
    'pearson_fisher_high_iid': interval[1],
    'pearson_p_iid': p, 'spearman_rho': rho,
}])
paired.to_csv(ROOT / 'data/processed/common_shock_2021_2022_countries.csv', index=False)
summary.to_csv(ROOT / 'data/processed/common_shock_2021_2022_summary.csv', index=False)
print(summary.round(3).to_string(index=False))
