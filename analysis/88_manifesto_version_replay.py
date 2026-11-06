"""Replay 2023a and, when supplied, compare the authenticated 2026a release.

Default invocation checks the old results without claiming a version comparison.
No original output is overwritten and no party-document rows are redistributed.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
OUT = DATA / "three_explanations/manifesto_refresh"
module_spec = importlib.util.spec_from_file_location("programme", ROOT / "analysis/24_programme_decomposition.py")
programme = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(programme)
KEYS = {
    "programme_coverage": ["pair_id", "sample"],
    "programme_decomposition": ["pair_id", "sample", "topic"],
    "programme_summary": ["sample", "kind", "topic"],
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(path):
    frame = pd.read_csv(path, low_memory=False)
    columns = sorted({f"per{i}" for values in programme.TOPICS.values() for i in values})
    required = set(columns + ["countryname", "date", "party", "pervote", "total", "progtype", "voteest", "manual", "coderid"])
    assert required <= set(frame.columns), sorted(required - set(frame.columns))
    assert not frame.duplicated(["countryname", "date", "party"]).any()
    usable = frame[frame.pervote.gt(0) & frame.total.gt(0) & frame[columns].notna().all(axis=1)].copy()
    for topic, codes in programme.TOPICS.items():
        usable[topic] = usable[[f"per{i}" for i in codes]].sum(axis=1)
    return frame, usable


def replay(documents):
    coverage, rows = [], []
    for pair in programme.candidate_pairs().itertuples():
        for sample in programme.SPECS:
            metadata, estimates = programme.analyse_pair(pair, documents, sample)
            coverage.append(metadata)
            rows.extend(estimates)
    results = pd.DataFrame(rows)
    return {"programme_coverage": pd.DataFrame(coverage),
            "programme_decomposition": results,
            "programme_summary": programme.summarize(results)}


def compare_baseline(name, actual):
    stored = pd.read_csv(DATA / f"{name}.csv")
    keys = KEYS[name]
    assert set(stored.columns) == set(actual.columns), name
    assert not stored.duplicated(keys).any() and not actual.duplicated(keys).any()
    stored = stored.set_index(keys).sort_index()
    actual = actual.set_index(keys).sort_index()
    assert actual.index.equals(stored.index), name
    maxima = {}
    for column in stored:
        a, b = actual[column], stored[column]
        if column in ("pre_date", "post_date"):
            assert pd.to_datetime(a).equals(pd.to_datetime(b)), (name, column)
        elif pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
            # Stored CSVs use eight significant digits, so rounding is expected.
            assert np.allclose(a, b, rtol=6e-8, atol=1e-8, equal_nan=True), (name, column)
            delta = (a - b).abs().dropna()
            maxima[column] = float(delta.max()) if len(delta) else 0.0
        else:
            assert a.fillna("<NA>").astype(str).equals(b.fillna("<NA>").astype(str)), (name, column)
    return {"rows": len(stored), "columns": len(stored.columns) + len(keys),
            "all_values_match_at_csv_precision": True, "max_absolute_difference_by_numeric_column": maxima}


def compare_versions(old, new):
    for name, values in new.items():
        values.to_csv(OUT / f"{name}_2026a.csv", index=False, float_format="%.12g")
    coverage = old["programme_coverage"].merge(new["programme_coverage"],
        on=KEYS["programme_coverage"], how="outer", suffixes=("_2023a", "_2026a"), validate="one_to_one")
    coverage.to_csv(OUT / "coverage_version_comparison.csv", index=False, float_format="%.12g")
    columns = KEYS["programme_decomposition"] + ["kind", "iso", "change_pp", "within_pp", "reweight_pp", "roster_pp", "pre_coverage", "post_coverage", "manual_changes"]
    changes = old["programme_decomposition"][columns].merge(new["programme_decomposition"][columns],
        on=KEYS["programme_decomposition"], how="outer", suffixes=("_2023a", "_2026a"), indicator=True, validate="one_to_one")
    common = changes["_merge"].eq("both")
    for column in ["change_pp", "within_pp", "reweight_pp", "roster_pp"]:
        changes[column + "_difference"] = changes[column + "_2026a"] - changes[column + "_2023a"]
    changes["change_sign_differs"] = pd.Series(pd.NA, index=changes.index, dtype="boolean")
    changes.loc[common, "change_sign_differs"] = np.sign(changes.loc[common, "change_pp_2023a"]).ne(np.sign(changes.loc[common, "change_pp_2026a"]))
    changes.to_csv(OUT / "estimate_version_comparison.csv", index=False, float_format="%.12g")
    summaries = []
    for kind in ["banking", "comparison"]:
        old_primary = old["programme_decomposition"]
        old_primary = old_primary[old_primary["sample"].eq("main") & old_primary.kind.eq(kind) & old_primary.topic.eq("economy")]
        fixed = set(old_primary.pair_id)
        for version, result in [("2023a", old), ("2026a", new)]:
            primary = result["programme_decomposition"]
            primary = primary[primary["sample"].eq("main") & primary.kind.eq(kind) & primary.topic.eq("economy")]
            for scope in ["original_pairs", "all_eligible_pairs"]:
                q = primary[primary.pair_id.isin(fixed)] if scope == "original_pairs" else primary
                summaries.append({"version": version, "kind": kind, "scope": scope,
                    "n": len(q), "original_pair_count": len(fixed), "countries": q.iso.nunique(),
                    "increase": int(q.change_pp.gt(0).sum()), "decrease": int(q.change_pp.lt(0).sum()),
                    "within_largest": int(q.within_pp.abs().gt(q[["reweight_pp", "roster_pp"]].abs().max(axis=1)).sum()),
                    "mean_change_pp": q.change_pp.mean(), "median_change_pp": q.change_pp.median()})
    summary = pd.DataFrame(summaries)
    summary.to_csv(OUT / "primary_version_summary.csv", index=False, float_format="%.12g")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, help="Authenticated 2026a CSV; omit for baseline verification only")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    baseline_path = ROOT / "data/raw/manifesto_2023a.csv"
    provenance = json.loads((DATA / "programme_provenance.json").read_text())
    assert sha(baseline_path) == provenance["sha256"]
    original_files = [DATA / f"{name}.csv" for name in KEYS] + [DATA / "programme_provenance.json"]
    original_hashes = {str(p.relative_to(ROOT)): sha(p) for p in original_files}
    _, baseline_documents = prepare(baseline_path)
    baseline = replay(baseline_documents)
    checks = {name: compare_baseline(name, result) for name, result in baseline.items()}
    record = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "baseline_sha256": sha(baseline_path), "baseline_replay": checks,
              "numerical_version_comparison_completed": False,
              "source_rows_redistributed": False, "original_outputs_sha256": original_hashes,
              "comparison_specification_sha256": sha(ROOT / "planning/manifesto-refresh-specification.md"),
              "driver_sha256": sha(Path(__file__)),
              "programme_driver_sha256": sha(ROOT / "analysis/24_programme_decomposition.py")}
    if args.candidate is not None:
        candidate_raw, candidate_documents = prepare(args.candidate)
        assert sha(args.candidate) != sha(baseline_path), "A copy of 2023a is not a new-release check"
        metadata_path = ROOT / "data/raw/manifesto_refresh_20261107/documents_2026a.csv"
        metadata = pd.read_csv(metadata_path)
        keys = ["countryname", "date", "party"]
        assert set(map(tuple, candidate_raw[keys].itertuples(index=False, name=None))) == set(map(tuple, metadata[keys].itertuples(index=False, name=None))), "Candidate keys differ from official 2026a document metadata"
        candidate = replay(candidate_documents)
        summary = compare_versions(baseline, candidate)
        record.update(numerical_version_comparison_completed=True, candidate_sha256=sha(args.candidate),
                      candidate_rows=len(candidate_raw), metadata_sha256=sha(metadata_path),
                      primary_summary=summary.to_dict("records"))
    assert all(sha(ROOT / name) == value for name, value in original_hashes.items())
    record["original_outputs_unchanged"] = True
    target = "version_replay_checks.json" if args.candidate is not None else "baseline_replay_checks.json"
    (OUT / target).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"baseline_replay_passed": True,
                      "tables": {name: check["rows"] for name, check in checks.items()},
                      "numerical_version_comparison_completed": args.candidate is not None,
                      "original_outputs_unchanged": True}, indent=2))


if __name__ == "__main__":
    main()
