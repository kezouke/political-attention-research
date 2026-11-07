"""Compare public 2026a document metadata with the frozen programme sample.

This is a coverage audit, not a recalculation of topic shares. The numerical
2026a dataset requires a separate authenticated download. Original outputs are
never overwritten. Only aggregate counts, not Manifesto rows, are published.
"""
from pathlib import Path
import hashlib
import importlib.util
import json

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/three_explanations"
RAW = ROOT / "data/raw/manifesto_refresh_20261107"
spec = importlib.util.spec_from_file_location("programme", ROOT / "analysis/24_programme_decomposition.py")
programme = importlib.util.module_from_spec(spec)
spec.loader.exec_module(programme)


def main():
    metadata_path = RAW / "documents_2026a.csv"
    current = pd.read_csv(metadata_path)
    old_path = ROOT / "data/raw/manifesto_2023a.csv"
    old = pd.read_csv(old_path, low_memory=False)
    keys = ["countryname", "date", "party"]
    assert not current.duplicated(keys).any()
    assert not old.duplicated(keys).any()
    provenance = json.loads((ROOT / "data/processed/programme_provenance.json").read_text())
    old_hash = hashlib.sha256(old_path.read_bytes()).hexdigest()
    assert old_hash == provenance["sha256"]
    current_keys = set(map(tuple, current[keys].itertuples(index=False, name=None)))
    old_keys = set(map(tuple, old[keys].itertuples(index=False, name=None)))
    published = pd.read_csv(ROOT / "data/processed/programme_coverage.csv")
    published = published[published["sample"].eq("main")].set_index("pair_id")
    rows = []
    used_main_banking_keys = set()
    eligible = programme.load_documents()
    for pair in programme.candidate_pairs().itertuples():
        country = programme.ALIASES.get(pair.country, pair.country)
        for endpoint in ("pre", "post"):
            month = int(getattr(pair, endpoint + "_date").strftime("%Y%m"))
            old_endpoint = old[old.countryname.eq(country) & old.date.eq(month)]
            current_endpoint = current[current.countryname.eq(country) & current.date.eq(month)]
            left = set(old_endpoint.party)
            right = set(current_endpoint.party)
            used = eligible[eligible.countryname.eq(country) & eligible.date.eq(month) & eligible.progtype.isin([1, 2, 8])]
            used_keys = set(map(tuple, used[keys].itertuples(index=False, name=None)))
            status = published.loc[pair.pair_id, "status"]
            if pair.kind == "banking" and status == "included":
                used_main_banking_keys.update(used_keys)
            rows.append({
                "pair_id": pair.pair_id, "kind": pair.kind, "iso": pair.iso,
                "endpoint": endpoint, "month": month,
                "published_2023a_status": status,
                "documents_2023a_all_types": len(left),
                "document_keys_2026a": len(right),
                "same_keys": len(left & right), "added_keys": len(right - left),
                "removed_or_recoded_keys": len(left - right),
                "eligible_documents_2023a": len(used_keys),
                "eligible_old_keys_missing_in_2026a": len(used_keys - current_keys),
            })
    coverage = pd.DataFrame(rows)
    coverage.to_csv(OUT / "manifesto_refresh_coverage.csv", index=False)
    main = coverage[coverage.kind.eq("banking") & coverage.published_2023a_status.eq("included")]
    result = {
        "baseline_version": "2023a", "metadata_version": "2026a",
        "baseline_sha256": old_hash,
        "metadata_sha256": hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
        "baseline_rows": len(old), "current_metadata_rows": len(current),
        "full_catalog_common_keys": len(old_keys & current_keys),
        "full_catalog_added_keys": len(current_keys - old_keys),
        "full_catalog_removed_or_recoded_keys": len(old_keys - current_keys),
        "main_banking_pairs": int(main.pair_id.nunique()),
        "main_banking_endpoints": len(main),
        "main_banking_unique_used_document_keys": len(used_main_banking_keys),
        "main_banking_used_keys_missing": len(used_main_banking_keys - current_keys),
        "main_banking_endpoints_with_added_keys": int(main.added_keys.gt(0).sum()),
        "topic_values_compared": False,
        "numerical_replay_performed_by_this_script": False,
        "access_status": "This script reads public document metadata only. Authenticated numerical acquisition is recorded separately in manifesto_refresh_sources.json.",
        "interpretation": "Key coverage alone does not validate topic values, vote weights, coding manuals or document types. See script 88 and manifesto_refresh/version_replay_checks.json for the separate numerical comparison.",
        "raw_rows_redistributed": False,
    }
    (OUT / "manifesto_refresh_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
