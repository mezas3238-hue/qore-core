#!/usr/bin/env python3
"""Read-only, sealed Native CIBO P0 rejection audit + blind 200-row shadow cohort.

No CIBO thresholds changed. No shadow PnL, ATR, imagined fills, or order_send.
Primary code reproduces FIRST blocking branch in sovereign_capital_runtime.py.
Secondary module gates are evidence only; never count each as another refusal.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile

COGNITIVE = {
    "nonpositive-causal-expected-net-utility": "COG_CF07_NONPOSITIVE_CAUSAL_NET_UTILITY",
    "walk-forward-provisional-forecast-history-required": "COG_CF07_PROVISIONAL_FORECAST",
    "walk-forward-cold-start-history-required": "COG_CF07_COLD_START",
}
CAP_COMPOUND = "CAP_REALIZED_PROFIT_INCREMENTAL_COMPOUND_NOT_ADMITTED"
CAP_PAUSE = "CAP_GENC12_NEW_CAPITAL_PAUSED"
CAP_PORTFOLIO = "CAP_PORTFOLIO_MULTIPLIER_ZERO"
CAP_COMPETITION = "CAP_POSITION_COMPETITION_REJECT"
READY = "RISK_REVIEW_READY"
SEED = "qore-cibo-p0-2026-10-09-taxonomy-blind-v1"


class AuditMismatch(ValueError):
    """Opaque/missing gate evidence is NOT license to assume a cause."""


def _one_sensor(row: dict, collection: str, key: str, name: str) -> dict:
    hits = [s for s in row[collection] if s[key] == name]
    if len(hits) != 1:
        raise AuditMismatch(f"expected one {name} on {row.get('signal_fingerprint')}")
    return hits[0]


def _values(sensor: dict) -> dict:
    return dict(sensor["input_metrics"] + sensor["output_metrics"])


def classify(row: dict) -> tuple[str, tuple[str, ...]]:
    disp = row["capital_disposition"]
    secondary = tuple(sorted({
        s["function_code"] for s in row["function_sensors"]
        if s.get("decision_gate_triggered")
    }))
    if disp == "COGNITIVE_BLOCK":
        calibration = _one_sensor(row, "cognitive_sensors", "component_code", "CALIBRATION")
        v = _values(calibration)
        code = COGNITIVE.get(v.get("note"))
        if code is None or v.get("abstention_required") != "True":
            raise AuditMismatch("unknown cognitive blocking rule, fail-closed")
        if row["risk_decision"] != "NOT_REQUESTED":
            raise AuditMismatch("cognitive blocked row reached QORE Risk")
        return code, secondary
    if disp == "CAPITAL_BLOCK":
        if row["risk_decision"] != "NOT_REQUESTED":
            raise AuditMismatch("capital blocked row reached QORE Risk")
        pause = _values(_one_sensor(
            row, "function_sensors", "function_code", "CAPITAL_SCIENCE:GEN-C12"
        )).get("consumer_action") == "PAUSE_NEW_CAPITAL"
        if pause:
            return CAP_PAUSE, secondary
        compound = _values(_one_sensor(
            row, "function_sensors", "function_code", "CIBO_COMPOUND"
        ))
        if (compound.get("realized_profit_source_requested") == "True"
            and compound.get("allow_incremental_compound") == "False"):
            return CAP_COMPOUND, secondary
        portfolio = _values(_one_sensor(
            row, "function_sensors", "function_code", "COMPOUND_PORTFOLIO"
        ))
        competition = _values(_one_sensor(
            row, "function_sensors", "function_code", "POSITION_COMPETITION"
        ))
        if portfolio.get("multiplier") == "0":
            return CAP_PORTFOLIO, secondary
        if competition.get("admit_opportunity") == "False":
            return CAP_COMPETITION, secondary
        raise AuditMismatch("unclassified economic block: cannot assume it is a risk failure")
    if disp == READY:
        if row["risk_decision"] not in ("ALLOW", "REDUCE") or float(row["authorized_volume"]) <= 0:
            raise AuditMismatch("risk-ready without authorized positive volume")
        return READY, secondary
    raise AuditMismatch(f"unknown CIBO disposition {disp}")


def _load_zip(archive: Path, member: str) -> dict:
    with ZipFile(archive) as z:
        if member not in z.namelist():
            raise AuditMismatch(f"missing {member} in {archive}")
        with z.open(member) as f:
            return json.load(f)


def audit(native: dict, manifest: dict | None = None, sample_each: int = 100) -> tuple[dict, list[dict], list[dict]]:
    rows = native["decision_receipts"]
    keys = [r["signal_fingerprint"] for r in rows]
    if len(keys) != 3368 or len(set(keys)) != 3368:
        raise AuditMismatch("Native 3368 identity count violated")
    op_by_id: dict[str, dict] = {}
    if manifest is not None:
        opportunity_rows = manifest["opportunities"]
        op_by_id = {x["signal_fingerprint"]: x for x in opportunity_rows}
        if len(op_by_id) != 3368 or set(op_by_id) != set(keys):
            raise AuditMismatch("manifest/Native 3368 identity mismatch")
    output = []
    for row in rows:
        fingerprint = row["signal_fingerprint"]
        code, secondary = classify(row)
        o = op_by_id.get(fingerprint)
        if o and row["decided_at"] != o["market_decision_at"]:
            raise AuditMismatch(f"market vs Native decision clock drift: {fingerprint}")
        output.append({
            "signal_fingerprint": fingerprint,
            "trader_id": row["trader_id"],
            "symbol": (o["qore_symbol"] if o else ""),
            "market_decision_at": row["decided_at"],
            "disposition": row["capital_disposition"],
            "primary_block_code": code,
            "secondary_triggered_functions": "|".join(secondary),
            "risk_decision": row["risk_decision"],
            "authorized_volume_abstract": row["authorized_volume"],
            "selection_uses_outcomes": False,
        })
    counts = Counter(x["primary_block_code"] for x in output)
    if sum(counts[k] for k in COGNITIVE.values()) != 1804 or (
        counts[CAP_COMPOUND] + counts[CAP_PAUSE] + counts[CAP_PORTFOLIO] +
        counts[CAP_COMPETITION] != 1553 or counts[READY] != 11
    ):
        raise AuditMismatch(f"baseline drift, cannot certify taxonomy: {counts}")
    # Blind, deterministic, class-balanced sample. Rank BEFORE loading/using outcomes.
    sample = []
    for disposition in ("COGNITIVE_BLOCK", "CAPITAL_BLOCK"):
        subset = [x for x in output if x["disposition"] == disposition]
        ordered = sorted(subset, key=lambda x: hashlib.sha256(
            f"{SEED}|{disposition}|{x['signal_fingerprint']}".encode()
        ).hexdigest())
        if sample_each > len(ordered):
            raise AuditMismatch("shadow sample larger than rejection stratum")
        for x in ordered[:sample_each]:
            sample.append({
                "signal_fingerprint": x["signal_fingerprint"],
                "trader_id": x["trader_id"],
                "symbol": x["symbol"],
                "disposition": disposition,
                "primary_block_code": x["primary_block_code"],
                "market_decision_at": x["market_decision_at"],
            })
    digest = hashlib.sha256(json.dumps(
        sample, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()
    summary = {
        "schema": "qore.cibo.p0.block-taxonomy-blind-sample.v1",
        "research_only": True, "broker_fills_proven": False,
        "selection_uses_postdecision_outcomes": False,
        "sample_seed": SEED, "sample_sha256": "sha256:" + digest,
        "sample_cognitive": sample_each, "sample_capital": sample_each,
        "decision_count": len(rows), "primary_counts": dict(sorted(counts.items())),
        "interpretation": "first effective blocking branch, NOT marginal causal effect",
        "unsupported_claims": [
            "ATR-normalized PnL without causal bars", "real MT5 fills",
            "true shadow win-rate/PF/DD", "certified improved CIBO selection"
        ],
    }
    return summary, output, sample


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-zip", type=Path, required=True)
    parser.add_argument("--manifest-zip", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sample-each", type=int, default=100)
    args = parser.parse_args()
    native = _load_zip(args.native_zip, "cibo-native-baseline.json")
    manifest = (_load_zip(args.manifest_zip, "walk-forward-manifest.json")
                if args.manifest_zip else None)
    summary, census, sample = audit(native, manifest, args.sample_each)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in (("summary.json", summary), ("blind-sample-200.json", sample)):
        (args.output_dir / name).write_text(
            json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
    with (args.output_dir / "decision-block-census-3368.csv").open(
        "w", newline="", encoding="utf-8"
    ) as fp:
        w = csv.DictWriter(fp, fieldnames=list(census[0]))
        w.writeheader()
        w.writerows(census)
    print("CIBO_P0_BLOCK_AUDIT", json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
