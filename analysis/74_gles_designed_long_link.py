"""Paired descriptions from the archive's designed person linkage, no vote fits."""
from pathlib import Path
from datetime import datetime, timezone
import importlib.util
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
def module(name, file):
    s = importlib.util.spec_from_file_location(name, ROOT / 'analysis' / file)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m
inputs = module('inputs', '66_gles_model_inputs.py')
extra = module('extra', '49_gles_priority_position_audit.py')
OUT = inputs.OUT


def paired(x, early, late, variable, sample, seed):
    a, b, w = x[early].to_numpy(float), x[late].to_numpy(float), x.weight_09.to_numpy(float)
    assert np.isfinite(np.column_stack([a, b, w])).all() and (w > 0).all()
    delta = b - a; rng = np.random.default_rng(seed)
    values = []
    for _ in range(2000):
        ids = rng.integers(0, len(x), len(x))
        values.append(np.average(delta[ids], weights=w[ids]))
    return {'sample': sample, 'variable': variable, 'n': len(x),
            'effective_n': float(w.sum() ** 2 / np.square(w).sum()),
            'mean_2009': float(np.average(a, weights=w)), 'mean_2013': float(np.average(b, weights=w)),
            'mean_change': float(np.average(delta, weights=w)),
            'ci_low': float(np.quantile(values, .025)), 'ci_high': float(np.quantile(values, .975)),
            'decreased_share': float(np.average(delta < 0, weights=w)),
            'same_share': float(np.average(np.isclose(delta, 0), weights=w)),
            'increased_share': float(np.average(delta > 0, weights=w)), 'bootstrap_draws': 2000}


def main():
    start = datetime.now(timezone.utc).isoformat()
    contract = json.loads((OUT / 'gles_input_contract.json').read_text())
    for p, sha in contract['fixed_input_hashes'].items(): assert inputs.digest(ROOT / p) == sha
    d, _ = inputs.load_data()
    linked, _ = inputs.panel.read_selected('ZA5757_v1-1-0.dta')
    positions, _ = extra.load_extra('ZA5757_v1-1-0.dta')
    linked = linked[['lfdn', 'lfdn09', 'lfdn13', 'mut09', 'mut0913']].merge(
        positions.drop(columns=['mut09', 'mut0913']), on='lfdn', validate='one_to_one')
    linked = linked[linked.mut09.eq(0) & linked.mut0913.eq(0)].copy()
    assert linked.lfdn09.is_unique and linked.lfdn13.is_unique
    a, b = d[d.year.eq(2009)].add_suffix('_09'), d[d.year.eq(2013)].add_suffix('_13')
    z = linked.merge(a, left_on='lfdn09', right_on='person_id_09', validate='one_to_one').merge(
        b, left_on='lfdn13', right_on='person_id_13', validate='one_to_one')
    assert len(z) == len(linked) == 972
    core = z.eligible_09 & z.core_complete_09 & z.eligible_13 & z.core_complete_13
    x = z[core & z.outcome_v4_inclusive_09.ge(0) & z.outcome_v4_inclusive_13.ge(0)].copy()
    assert core.sum() == 467 and len(x) == 360
    rows = [paired(x, v + '_09', v + '_13', v, 'complete_core_and_outcomes', 20261106 + i)
            for i, v in enumerate(inputs.CORE)]
    for i, topic in enumerate(['tax_welfare', 'immigration']):
        variables = extra.TOPICS[topic]
        p09, p13 = x[variables['position_09']], x[variables['position_13']]
        s09, s13 = x[variables['importance_09']], x[variables['importance_13']]
        seven, eleven = p09.between(1, 7), p09.between(11, 21)
        for scale in ['seven_only', 'seven_or_eleven']:
            valid = seven if scale == 'seven_only' else seven | eleven
            valid &= p13.between(1, 7) & s09.between(1, 5) & s13.between(1, 5)
            q = x[valid].copy()
            q['position_early'] = ((p09 - 1) / 6).where(seven, (p09 - 11) / 10)
            q['position_late'] = (p13 - 1) / 6
            q['importance_early'] = (5 - s09) / 4; q['importance_late'] = (5 - s13) / 4
            for measure in ['position', 'importance']:
                rows.append(paired(q, measure + '_early', measure + '_late', topic + '_' + measure, scale, 20261116 + i))
    retained = set(x.person_id_09)
    base = d[d.year.eq(2009) & d.eligible & d.core_complete].copy()
    comparison = []
    for label, q in [('initial_complete_2009', base), ('retained_complete_both_years', base[base.person_id.isin(retained)])]:
        for v in inputs.CORE + ['age_scaled', 'left_right']:
            comparison.append({'sample': label, 'variable': v, 'n': len(q),
                               'weighted_mean': float(np.average(q[v], weights=q.weight))})
    result = pd.DataFrame(rows)
    assert np.allclose(result.mean_2013 - result.mean_2009, result.mean_change)
    assert result.ci_low.le(result.ci_high).all()
    assert np.allclose(result.decreased_share + result.same_share + result.increased_share, 1)
    result.to_csv(OUT / 'gles_linked_paired_changes.csv', index=False)
    pd.DataFrame(comparison).to_csv(OUT / 'gles_linked_selection_description.csv', index=False)
    manifest = json.loads((inputs.AUDIT / 'authenticated_downloads.json').read_text())
    record = next(e for e in manifest['files'] if e['filename'] == 'ZA5757_v1-1-0.dta')
    assert inputs.digest(ROOT / record['local_path']) == record['sha256']
    report = {'start_utc': start, 'end_utc': datetime.now(timezone.utc).isoformat(),
              'hashes': {str(p.relative_to(ROOT)): inputs.digest(p) for p in [Path(__file__), ROOT / 'planning/gles-long-link-specification.md',
                         OUT / 'gles_input_contract.json', ROOT / record['local_path'], ROOT / 'analysis/49_gles_priority_position_audit.py']},
              'clean_linked_n': 972, 'both_core_n': 467, 'both_core_and_outcomes_n': 360,
              'initial_complete_2009_n': len(base), 'paired_estimates': len(rows),
              'weight': '2009 initial wave gew_q1_w1, not a corrected longitudinal weight',
              'vote_model_fitted': False, 'climate_position_change_computed': False, 'microdata_exported': False,
              'limitations': ['Selected survivors', 'Both years follow crisis onset', 'Government coalition changes',
                              'Seven/eleven endpoint rescaling is a sensitivity assumption']}
    (OUT / 'gles_linked_changes_run.json').write_text(json.dumps(report, indent=2) + '\n')
    print(result[['sample', 'variable', 'n', 'mean_change', 'ci_low', 'ci_high']].round(4).to_string(index=False))


if __name__ == '__main__': main()
