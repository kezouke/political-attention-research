"""Audit a regional party ambiguity discovered while mapping BES parties.

The common EB Greens response must not automatically identify the Green Party
of England and Wales for a Scottish respondent. Export only aggregate counts.
This records a factual correction before the revised EB model run.
"""
from pathlib import Path
import importlib.util
import json
import numpy as np
import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('eb_inputs', ROOT / 'analysis/50_eurobarometer_model_inputs.py')
inputs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inputs)


def corrected_data():
    d, metadata = inputs.load_data()
    raw, labels = pyreadstat.read_sav(inputs.eb.verified_download('ZA4973_v3-0-0.sav'),
                                     usecols=['v6', 'v553', 'v743', 'v772'], user_missing=True)
    assert raw.loc[d.index, 'v6'].eq(d['sample']).all()
    assert labels.variable_value_labels['v743'][16] == 'Scotland'
    assert labels.variable_value_labels['v772'][1] == 'Scotland'
    green = d.country.eq('GB') & raw.loc[d.index, 'v553'].eq(800)
    scotland = raw.loc[d.index, 'v743'].eq(16)
    assert np.array_equal(scotland.to_numpy(), raw.loc[d.index, 'v772'].eq(1).to_numpy())
    # A missing region cannot resolve the generic Greens label either.
    england_wales = raw.loc[d.index, 'v743'].between(6, 15)
    unresolved = green & ~england_wales
    original = d.copy()
    for version in ['3', '4']:
        for rule in ['inclusive', 'strict']:
            d.loc[unresolved, f'outcome_v{version}_{rule}'] = 'unresolved'
    report = {'all_adult_Greens_responses': int(green.sum()),
              'core_complete_Greens_responses': int((green & d.core_complete).sum()),
              'core_complete_Scottish_Greens_responses': int((green & scotland & d.core_complete).sum()),
              'core_complete_unresolved_region_Greens_responses': int((unresolved & ~scotland & d.core_complete).sum()),
              'correction': 'Generic Greens response only mapped to the eligible England/Wales party when region establishes England or Wales',
              'reason': 'Scottish Greens is a distinct party; absence from PopuList does not establish a negative label without verified scope',
              'region_variables': {'v743': 'P7 region I, Scotland code 16; England/Wales 6..15',
                                   'v772': 'P7 region II, Scotland code 1, cross-checked'},
              'respondent_rows_exported': False, 'revised_model_fitted_by_this_script': False}
    counts = []
    for target in ['government_vs_opposition', 'opposition_type', 'nonvote_vs_vote', 'four_outcomes']:
        a, b = inputs.analytic_sample(original, target), inputs.analytic_sample(d, target)
        counts.append({'target': target, 'original_n': len(a), 'corrected_n': len(b), 'difference': len(b) - len(a)})
    return d, metadata, report, counts


def main():
    _, _, report, counts = corrected_data()
    out = ROOT / 'data/processed/three_explanations'
    (out / 'eb_regional_identity_correction.json').write_text(json.dumps(report, indent=2) + '\n')
    pd.DataFrame(counts).to_csv(out / 'eb_regional_identity_sample_changes.csv', index=False)
    print(json.dumps(report, indent=2)); print(pd.DataFrame(counts).to_string(index=False))


if __name__ == '__main__':
    main()
