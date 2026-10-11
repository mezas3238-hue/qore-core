"""Issue772 Gate C0 nine-market pre-economic aggregation and cohort exposure."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_issue772_source_census_aggregate_v1 import (  # noqa: E501
    max3,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    source_id,
)

IDENTITY="QORE_SCALPER_ISSUE772_C0_FULL_NATIVE_AGGREGATION_INTEGRITY_AUDIT_V1"


def classify(rows:tuple[dict[str,Any],...])->dict[str,Any]:
    counter:Counter[str]=Counter()
    by_symbol:dict[str,Counter[str]]=defaultdict(Counter)
    by_family:dict[str,Counter[str]]=defaultdict(Counter)
    by_inherited:dict[str,Counter[str]]=defaultdict(Counter)
    def flags(row:dict[str,Any])->list[str]:
        val=["N"]
        for col,name in (
            ("h1_local_closure_has_non_strict_bucket","H1_DIRECT_PARTIAL"),
            ("h1_local_closure_premature_bucket","H1_EARLY_CLOSE"),
            ("m15_direct_components_non_strict","M15_DIRECT_PARTIAL"),
            ("m15_direct_components_early_close","M15_EARLY_CLOSE"),
            ("m15_structural_span_timestamp_gap","M15_SPAN_GAP"),
        ):
            if row[col]:
                val.append(name)
        if any(row[x] for x in (
            "h1_local_closure_has_non_strict_bucket",
            "m15_direct_components_non_strict",
        )):
            val.append("EITHER_DIRECT_PARTIAL")
        if not row["h1_event_origin_recovered_original_V48"]:
            val.append("H1_ORIGIN_UNKNOWN")
        if not row["m15_original_setup_reconstructed"]:
            val.append("M15_ORIGIN_UNKNOWN")
        if not row["h1_strict_full_H1_same_original_event"]:
            val.append("H1_STRICT_SIGNATURE_DIFFERENT_OR_MISSING")
        if not row["m15_conditional_strict_exact_setup_match"]:
            val.append("M15_CONDITIONAL_STRICT_DIFFERENT_OR_MISSING")
        if row["h1_last5_available_full"]:
            val.append("H1_FIVE_AVAILABLE")
        if row["h1_last5_full_nominal_hours_consecutive"]:
            val.append("H1_FIVE_CONSECUTIVE")
        return val
    for row in rows:
        ff=flags(row)
        for name in ff:
            counter[name]+=1
            by_symbol[row["symbol"]][name]+=1
            by_family[row["trigger_family"]][name]+=1
            by_inherited[
                "INHERITED" if row["h1_inherited"] else "FRESH"
            ][name]+=1
    return {
        "counts":dict(sorted(counter.items())),
        "by_symbol":{
            k:dict(sorted(v.items())) for k,v in sorted(by_symbol.items())
        },
        "by_trigger_family":{
            k:dict(sorted(v.items())) for k,v in sorted(by_family.items())
        },
        "by_inherited":{
            k:dict(sorted(v.items())) for k,v in sorted(by_inherited.items())
        },
    }


def aggregate(root:Path,manifest_path:Path,output:Path)->dict[str,Any]:
    paths=tuple(sorted(root.rglob(
        "scalper-issue772-c0-source-aggregate-exposure.jsonl"
    )))
    reports=tuple(sorted(root.rglob(
        "scalper-issue772-c0-market-report.json"
    )))
    frozen_paths=tuple(sorted(root.rglob(
        "capitalizer-*-v49-hf-capacity-opportunities.jsonl"
    )))
    if len(paths)!=9 or len(reports)!=9 or len(frozen_paths)!=9:
        raise ValueError("exactly nine original source ledgers and C0 audits")
    sources=tuple(
        V49Opportunity(**json.loads(line))
        for p in frozen_paths for line in p.read_text(
            encoding="utf-8"
        ).splitlines() if line.strip()
    )
    all_rows=tuple(
        json.loads(line)
        for p in paths for line in p.read_text(
            encoding="utf-8"
        ).splitlines() if line.strip()
    )
    report_rows=tuple(
        json.loads(p.read_text(encoding="utf-8")) for p in reports
    )
    source_ids={source_id(s) for s in sources}
    rows_by_id={x["source_opportunity_id"]:x for x in all_rows}
    if (len(sources)!=2876 or len(source_ids)!=2876 or
        len(all_rows)!=2876 or len(rows_by_id)!=2876 or
        set(rows_by_id)!=source_ids or
        len({x["symbol"] for x in report_rows})!=9 or
        sum(x["source_ids"] for x in report_rows)!=2876):
        raise ValueError("C0 changed immutable 2876 identities")
    original_a=max3(sources)
    if len(original_a)!=2020:
        raise ValueError("C0 original source-only A MAX3 not 2020")
    a=tuple(x for x in all_rows if x["source_opportunity_id"] in original_a)
    if len(a)!=2020:
        raise ValueError("A source identity mismatch")
    sample=json.loads(manifest_path.read_text(encoding="utf-8"))
    ids=[x["source_id"] for x in sample["sample20"]]
    if len(ids)!=len(set(ids)) or len(ids)!=20 or not set(ids)<=original_a:
        raise ValueError("20 original P0 772 hash sample identity changed")
    sample_c0=tuple(rows_by_id[x] for x in ids)
    market_bucket={
        x["symbol"]:x["bucket_census"] for x in report_rows
    }
    global_bucket:dict[str,Counter[str]]={
        "H1":Counter(),"M15":Counter()
    }
    for row in report_rows:
        for tf in ("H1","M15"):
            global_bucket[tf].update(row["bucket_census"][tf])
    output.mkdir(parents=True,exist_ok=True)
    (output/"scalper-issue772-c0-A2020-source-integrity.jsonl").write_text(
        "".join(json.dumps(x,sort_keys=True)+"\n" for x in a),
        encoding="utf-8",
    )
    (output/"scalper-issue772-c0-all2876-source-integrity.jsonl").write_text(
        "".join(json.dumps(x,sort_keys=True)+"\n" for x in all_rows),
        encoding="utf-8",
    )
    (output/"scalper-issue772-c0-20-traces-integrity.jsonl").write_text(
        "".join(json.dumps(x,sort_keys=True)+"\n" for x in sample_c0),
        encoding="utf-8",
    )
    result={
        "identity":IDENTITY,"sources":len(all_rows),
        "original_A":len(a),
        "sample20_source_IDs_identical":True,
        "counts_source_2876":classify(all_rows),
        "counts_original_A_2020":classify(a),
        "counts_original_sample20":classify(sample_c0),
        "bucket_census_total":{
            k:dict(sorted(v.items())) for k,v in global_bucket.items()
        },
        "bucket_census_by_symbol":market_bucket,
        "legacy_H1_original_bias_detector_USED_ONLY_AS_COMPARATOR":True,
        "legacy_M15_original_structural_detector_USED_ONLY_AS_COMPARATOR":True,
        "strict_H1_no_independent_author_adjudication":True,
        "strict_M15_no_full_H1_M1_route_rebuild":True,
        "original_H1_POI_upstream_provenance_unresolved":True,
        "M1_first_online_CISD_unresolved":True,
        "benchmark_five_H1_old_label_is_available_not_consecutive":True,
        "old_swing_distance_R_is_tautological_not_late_entry_measure":True,
        "no_outcomes_loaded":True,"certified":False,
        "V49_DCVC_VPS_modified":False,"promotable":False,
    }
    (output/"scalper-issue772-gate-c0-nine-market-results.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print("ISSUE772_C0_FINAL",json.dumps({
        "A":len(a),"sources":len(all_rows),
        "source_counts":result["counts_source_2876"]["counts"],
        "A_counts":result["counts_original_A_2020"]["counts"],
        "bucket_totals":result["bucket_census_total"],
    },sort_keys=True))
    return result


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("nine_market_root",type=Path)
    p.add_argument("sample20_manifest",type=Path)
    p.add_argument("output",type=Path)
    z=p.parse_args()
    aggregate(z.nine_market_root,z.sample20_manifest,z.output)


if __name__=="__main__":
    main()
