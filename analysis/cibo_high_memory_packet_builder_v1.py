#!/usr/bin/env python3
"""Build research-only CIBO HIGH MEMORY packets over the burned 3x1Y lab.

GitHub owns this code. Trader Lab only executes it against local replay artifacts.
The builder never grants Risk/execution/broker authority and never feeds
post-outcome data into predecision memory.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

GROUPS = ("group1", "group2", "group3")
TRADERS = (
    "VT08_FOREX",
    "R34_XAUUSD",
    "R38_EURUSD",
    "R43_GBPUSD",
    "R38_GBPJPY",
    "R42_AUDJPY",
    "VT31_NAS100",
)
OPAQUE_NATIVE_KEYS = {
    "result_sha256",
    "result_type",
    "result_value",
    "temporal_boundary",
}


def load_vt31_native(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    base = root / "handoff_continuation" / "vt31_semantic_bridge"
    for tag in ("r6", "r5"):
        payload = json.loads(
            (base / f"{tag}-specialist.json").read_text(encoding="utf-8")
        )
        for row in payload["reasoning_trace"]:
            copy = dict(row)
            copy["source_partition"] = tag
            result[str(row["decision_at"])] = copy
    return result


def decision_context(row: dict[str, Any]) -> dict[str, str]:
    raw = row.get("trader_opportunity", {}).get("decision_context", [])
    return {str(key): str(value) for key, value in raw}


def faculty_memory(
    row: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    inputs: dict[str, Any] = {}
    outputs: dict[str, Any] = {}
    receipts = row.get("cognitive_orchestration", {}).get("faculty_receipts", [])
    for receipt in receipts:
        code = str(receipt.get("function_code"))
        inputs[code] = receipt.get("input_payload", {})
        payload = receipt.get("output_payload", {})
        native = payload.get("native_engine_output", {})
        semantic_output: dict[str, Any] = {}
        if isinstance(native, dict):
            semantic_output = {
                key: value
                for key, value in native.items()
                if key not in OPAQUE_NATIVE_KEYS
            }
        outputs[code] = {
            "contribution_code": payload.get("contribution_code"),
            "evidence_status": payload.get("evidence_status"),
            "native_engine_called": payload.get("native_engine_called"),
            "native_engine_status": payload.get("native_engine_status"),
            "native_engine_name": payload.get("native_engine_name"),
            "native_result_type": (
                native.get("result_type") if isinstance(native, dict) else None
            ),
            "native_result_sha256": (
                native.get("result_sha256") if isinstance(native, dict) else None
            ),
            "semantic_output": semantic_output,
            "semantic_output_available": bool(semantic_output),
            "advisory_only": receipt.get("advisory_only"),
            "outcome_used": receipt.get("outcome_used"),
        }
    return inputs, outputs


def vt31_predecision(
    row: dict[str, Any],
    native: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if row["trader_id"] != "VT31_NAS100":
        return None
    item = native.get(str(row["market_decision_at"]))
    if item is None:
        return None
    return {
        key: value
        for key, value in item.items()
        if key != "outcome_fields_used_for_decision"
    }


def memory_status(
    trader: str,
    context_key_count: int,
    vt31_match: bool,
) -> str:
    if trader == "VT08_FOREX":
        return "NATIVE_MEMORY_UNDEREXPOSED__HIGH_MEMORY_REPAIR_REQUIRED"
    if trader == "VT31_NAS100":
        return (
            "NATIVE_M1_HIGH_MEMORY_EXACT_MATCH"
            if vt31_match
            else "NATIVE_M1_HIGH_MEMORY_NO_EXACT_CAUSAL_MATCH"
        )
    if context_key_count >= 30:
        return "RICH_TRADER_CONTEXT_PRESENT__NOT_PROPAGATED_TO_CF_SEMANTICS"
    return "HIGH_MEMORY_REPAIR_REQUIRED"


def build(
    root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    vt31 = load_vt31_native(root)
    packets: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    context_keys: dict[str, set[str]] = defaultdict(set)
    statuses: dict[str, Counter[str]] = defaultdict(Counter)
    faculty_calls: Counter[str] = Counter()
    faculty_semantic: Counter[str] = Counter()
    vt31_exact = 0

    for group in GROUPS:
        trace = json.loads(
            (root / group / "lab" / "decision-trace.json").read_text(
                encoding="utf-8"
            )
        )
        for row in trace["opportunities"]:
            trader = str(row["trader_id"])
            if trader not in TRADERS:
                continue

            context = decision_context(row)
            inputs, outputs = faculty_memory(row)
            native = vt31_predecision(row, vt31)

            counts[trader] += 1
            context_keys[trader].update(context)
            if native is not None:
                vt31_exact += 1

            for code, payload in outputs.items():
                faculty_calls[code] += 1
                if payload["semantic_output_available"]:
                    faculty_semantic[code] += 1

            status = memory_status(trader, len(context), native is not None)
            statuses[trader][status] += 1

            packets.append(
                {
                    "schema": "qore.cibo.high-memory-packet.v1",
                    "research_group": group,
                    "identity": {
                        "trader_id": trader,
                        "qore_symbol": row.get("qore_symbol"),
                        "signal_fingerprint": row.get("signal_fingerprint"),
                        "market_decision_at": row.get("market_decision_at"),
                    },
                    "predecision_memory": {
                        "trader_context": context,
                        "market_predecision_state": row.get(
                            "market_predecision_state"
                        ),
                        "faculty_inputs": inputs,
                        "faculty_outputs": outputs,
                        "vt31_native_cognition": native,
                        "memory_status": status,
                        "causal_predecision_only": True,
                        "post_outcome_values_injected": False,
                    },
                    "cibo_downstream_outputs": {
                        "cognitive_orchestration_summary": {
                            key: value
                            for key, value in row.get(
                                "cognitive_orchestration", {}
                            ).items()
                            if key != "faculty_receipts"
                        },
                        "context_quality": row.get("context_quality"),
                        "expectation": row.get("expectation"),
                        "ce2i": row.get("ce2i"),
                        "capital_science": row.get("capital_science"),
                        "cma": row.get("cma"),
                        "allocation": row.get("allocation"),
                        "qore_risk": row.get("qore_risk"),
                    },
                    "post_outcome_research_only": {
                        "evaluation_outcome": row.get("evaluation_outcome"),
                        "settlement": row.get("settlement"),
                        "used_to_build_predecision_memory": False,
                    },
                    "governance": {
                        "research_only": True,
                        "burned_reusable_holdout": True,
                        "fresh_oos_claimed": False,
                        "certification_claimed": False,
                        "execution_authority": False,
                        "risk_authority": False,
                        "live": False,
                        "production": False,
                        "real_capital": False,
                    },
                }
            )

    summary = {
        "schema": "qore.cibo.high-memory-study-summary.v1",
        "packet_count": len(packets),
        "expected_traders": list(TRADERS),
        "per_trader_decisions": {trader: counts[trader] for trader in TRADERS},
        "per_trader_context_key_count": {
            trader: len(context_keys[trader]) for trader in TRADERS
        },
        "per_trader_memory_status": {
            trader: dict(sorted(statuses[trader].items()))
            for trader in TRADERS
        },
        "vt31_exact_native_cognitive_matches": vt31_exact,
        "faculty_calls": dict(sorted(faculty_calls.items())),
        "faculty_semantic_output_available": dict(
            sorted(faculty_semantic.items())
        ),
        "economic_restart_gate": (
            "BLOCKED_UNTIL_HIGH_MEMORY_SEMANTIC_TRANSPORT_REPAIRED_7_OF_7"
        ),
        "restart_order_after_gate": [
            "SIZING",
            "ADAPTIVE_LEVERAGE",
            "CIBO_COMPOUND",
            "COMPOUND_PORTFOLIO",
        ],
        "governance": {
            "research_only": True,
            "fresh_oos_claimed": False,
            "certification_claimed": False,
            "live": False,
            "production": False,
            "real_capital": False,
        },
    }
    return packets, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    packets, summary = build(args.replay_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with (args.output_dir / "cibo_high_memory_packets.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in packets:
            handle.write(
                json.dumps(
                    row,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )

    (args.output_dir / "cibo_high_memory_summary.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
