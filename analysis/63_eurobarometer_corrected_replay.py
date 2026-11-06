"""Replay all EB fits/checks after the factual regional party correction.

The locked v1 code and outputs remain byte-identical. This driver changes only
the local input frame, corresponding coverage counts, and output destination.
No respondent frame is written. The original model algorithms are reused.
"""
from pathlib import Path
from datetime import datetime, timezone
import importlib.util
import json
import shutil
import subprocess
import pandas as pd
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / 'data/processed/three_explanations'
OUT = V1 / 'eb_v2'


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'analysis' / filename)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    correction = module('correction', '60_eb_regional_party_identity_check.py')
    model = module('model', '51_eurobarometer_models.py')
    digest = model.inputs.digest
    originals = {str(p.relative_to(ROOT)): digest(p) for p in V1.glob('eb_*') if p.is_file()}
    d, metadata, report, counts = correction.corrected_data()
    OUT.mkdir(exist_ok=True)
    audit = OUT / 'audit'
    audit.mkdir(exist_ok=True)
    shutil.copyfile(model.inputs.AUDIT / 'ep2009_vote_crosswalk.csv', audit / 'ep2009_vote_crosswalk.csv')
    coverage = []
    for version in [3, 4]:
        for rule in ['inclusive', 'strict']:
            col = f'outcome_v{version}_{rule}'
            for country, g in d[d.core_complete & d.named_response].groupby('country'):
                n = int(g[col].isin(['government', 'other_opposition', 'populist_opposition']).sum())
                coverage.append({'country': country, 'version': version, 'rule': rule,
                                 'joint_named_option_n': len(g), 'joint_classified_vote_n': n,
                                 'joint_unresolved_named_option_n': len(g) - n})
    pd.DataFrame(coverage).to_csv(audit / 'ep2009_outcome_coverage.csv', index=False)
    old = pd.read_csv(model.inputs.AUDIT / 'ep2009_outcome_coverage.csv').set_index(['country', 'version', 'rule']).sort_index()
    new = pd.DataFrame(coverage).set_index(['country', 'version', 'rule']).sort_index()
    assert old.index.equals(new.index)
    assert old.drop(index='GB', level=0).equals(new.drop(index='GB', level=0))
    assert (new.loc['GB', 'joint_classified_vote_n'] == old.loc['GB', 'joint_classified_vote_n'] - 1).all()
    model.inputs.AUDIT = audit
    model.inputs.OUT = OUT
    model.inputs.load_data = lambda: (d.copy(), metadata)
    model.OUT = OUT
    config = json.loads((V1 / 'eb_input_contract.json').read_text())
    config['parent_contract_sha256'] = digest(V1 / 'eb_input_contract.json')
    config['sample_totals'] = {r['target']: r['corrected_n'] for r in counts}
    config['revision'] = 'v2: one Scottish Greens response becomes unresolved; same original models and sensitivities'
    added = [Path(__file__), ROOT / 'analysis/60_eb_regional_party_identity_check.py',
             ROOT / 'analysis/51_eurobarometer_models.py', ROOT / 'analysis/54_eurobarometer_robustness.py',
             audit / 'ep2009_vote_crosswalk.csv', audit / 'ep2009_outcome_coverage.csv']
    config['fixed_input_hashes'].update({str(p.relative_to(ROOT)): digest(p) for p in added})
    (OUT / 'eb_input_contract.json').write_text(json.dumps(config, indent=2) + '\n')
    implementation = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    model.main()
    path = OUT / 'eb_models_run.json'
    run = json.loads(path.read_text())
    run.update({'input_lock_commit': implementation,
                'original_input_lock_commit': 'a59f22b',
                'revision_driver_sha256': digest(Path(__file__)),
                'revision_driver': str(Path(__file__).relative_to(ROOT)), 'revision': config['revision']})
    path.write_text(json.dumps(run, indent=2) + '\n')
    checks = module('checks', '52_eurobarometer_result_checks.py')
    checks.OUT = OUT
    checks.main()
    robustness = module('robustness', '54_eurobarometer_robustness.py')
    robustness.model = model
    robustness.inputs = model.inputs
    robustness.OUT = OUT
    robustness.main()
    checks2 = module('checks2', '55_eurobarometer_robustness_checks.py')
    checks2.OUT = OUT
    checks2.main()
    a = pd.read_csv(V1 / 'eb_model_margins.csv')
    b = pd.read_csv(OUT / 'eb_model_margins.csv')
    comparison = a.merge(b, on=['target', 'variable', 'outcome'], suffixes=('_v1', '_v2'), validate='one_to_one')
    comparison['point_change_pp'] = 100 * (comparison.probability_difference_v2 - comparison.probability_difference_v1)
    comparison.to_csv(OUT / 'eb_v1_v2_comparison.csv', index=False)
    for p, sha in originals.items():
        assert digest(ROOT / p) == sha, ('Original output changed', p)
    report.update({'completed_utc': datetime.now(timezone.utc).isoformat(),
                   'revision_driver_sha256': digest(Path(__file__)),
                   'complete_model_replay': True, 'complete_robustness_replay': True,
                   'original_aggregate_hashes_unchanged': originals,
                   'max_absolute_main_point_change_pp': float(comparison.point_change_pp.abs().max()),
                   'sample_changes': counts})
    (OUT / 'eb_corrected_replay_checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Corrected EB replay completed; v1 preserved byte-for-byte.', flush=True)


if __name__ == '__main__':
    with threadpool_limits(limits=1):
        main()
