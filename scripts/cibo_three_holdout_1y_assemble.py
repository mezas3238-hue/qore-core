#!/usr/bin/env python3
"""Assemble exact seven-Trader fixed 1Y research groups for CIBO replay.

The output deliberately uses the existing Phase22 V4 serialized geometry
contract as an internal compatibility surface only. Each payload is explicitly
marked NON_CERTIFYING_BURNED_ADAPTIVE_RESEARCH; no Fresh OOS claim is made.

Trader legacy sizing is discarded. Only volume-free geometry, structural
outcome and causal predecision context enter CIBO.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_chronological_replay import (
    reconstructed_signal_fingerprint,
)
from qore.infrastructure.cibo_phase22_fresh_opportunity_batch import (
    Phase22FreshOpportunity,
    Phase22FreshTraderEvidence,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)
from qore.infrastructure.cibo_phase22_v4_fresh_batch import (
    build_phase22_v4_fresh_batch,
)

GROUPS = ("GROUP_1", "GROUP_2", "GROUP_3")
FORBIDDEN_CONTEXT = ("exit", "realized", "outcome", "pnl", "raw_net", "scaled_net")


def _json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"expected object: {path}")
    return raw


def _sha(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _artifact_digest(value: str) -> str:
    if (
        not value.startswith("sha256:")
        or len(value) != 71
        or any(c not in "0123456789abcdef" for c in value[7:])
    ):
        raise ValueError("artifact digest invalid")
    return value


def _context(rows: dict[str, object]) -> tuple[tuple[str, str], ...]:
    values: dict[str, str] = {}
    for key, value in rows.items():
        if value is None:
            continue
        normalized = str(key)
        if any(token in normalized.lower() for token in FORBIDDEN_CONTEXT):
            raise ValueError(f"outcome-like context forbidden: {normalized}")
        text = str(value)
        if text:
            values[normalized] = text
    return tuple(sorted(values.items()))


def _fingerprint(
    *,
    trader: str,
    symbol: str,
    side: str,
    signal_at: datetime,
    entry_at: datetime,
    entry: Decimal,
    stop: Decimal,
    target: Decimal,
    evidence_ids: tuple[str, ...],
) -> str:
    return "sha256:" + reconstructed_signal_fingerprint(
        trader_id=TraderLineage(trader),
        qore_symbol=symbol,
        side=side,
        signal_at=signal_at,
        entry_at=entry_at,
        entry_price=entry,
        structural_stop=stop,
        technical_target=target,
        source_evidence_ids=evidence_ids,
    )


def _vt08_rows(
    payload: dict[str, Any],
    *,
    artifact_id: int,
) -> list[Phase22FreshOpportunity]:
    methodology = str(payload["methodology_fingerprint"])
    if len(methodology) != 64:
        raise ValueError("VT08 methodology fingerprint invalid")
    out = []
    for row in payload["trades"]:
        signal_at = datetime.fromisoformat(str(row["signal_at"]))
        # Frozen VT08 B01 backtest models the entry at candidate.decision_at;
        # signal_at is that exact decision/entry clock.
        entry_at = signal_at
        exit_at = datetime.fromisoformat(str(row["exited_at"]))
        side = str(row["side"])
        entry = Decimal(str(row["entry"]))
        stop = Decimal(str(row["stop"]))
        target = Decimal(str(row["target"]))
        exit_price = Decimal(str(row["exit_price"]))
        risk = entry - stop if side == "long" else stop - entry
        gain = exit_price - entry if side == "long" else entry - exit_price
        if risk <= 0:
            raise ValueError("VT08 invalid stop geometry")
        outcome_r = gain / risk
        symbol = str(row["symbol"])
        evidence = (
            f"github-actions:3x1y-vt08:{artifact_id}",
            f"trader-lab:{payload['group_id']}",
        )
        out.append(
            Phase22FreshOpportunity(
                trader_id=TraderLineage.VT08_FOREX,
                qore_symbol=symbol,
                signal_fingerprint=_fingerprint(
                    trader="VT08_FOREX",
                    symbol=symbol,
                    side=side,
                    signal_at=signal_at,
                    entry_at=entry_at,
                    entry=entry,
                    stop=stop,
                    target=target,
                    evidence_ids=evidence,
                ),
                signal_at=signal_at,
                entry_at=entry_at,
                exit_at=exit_at,
                side=side,
                entry_price=entry,
                structural_stop=stop,
                technical_target=target,
                exit_reason=str(row["exit_reason"]),
                gross_structural_outcome_r=outcome_r,
                methodology_sha256="sha256:" + methodology,
                source_evidence_ids=evidence,
                decision_context=_context(
                    {
                        "family": "VT08_B01_R3_15",
                        "ctx_timeframe": "M15",
                        "ctx_portfolio": "B_COMBINED",
                        "ctx_symbol": symbol,
                    }
                ),
            )
        )
    return out


def _vt31_rows(
    payload: dict[str, Any],
    *,
    artifact_id: int,
) -> list[Phase22FreshOpportunity]:
    methodology = str(payload["source"]["certified_strategy_fingerprint"])
    if len(methodology) != 64:
        raise ValueError("VT31 methodology fingerprint invalid")
    out = []
    for row in payload["trades"]:
        signal_at = datetime.fromisoformat(str(row["signal_at"]))
        entry_at = datetime.fromisoformat(str(row["entry_at"]))
        exit_at = datetime.fromisoformat(str(row["exit_at"]))
        side = str(row["side"])
        entry = Decimal(str(row["entry_price"]))
        stop = Decimal(str(row["structural_stop"]))
        target = Decimal(str(row["technical_target"]))
        evidence = (
            f"github-actions:3x1y-vt31:{artifact_id}",
            f"trader-lab:{payload['group_id']}",
        )
        out.append(
            Phase22FreshOpportunity(
                trader_id=TraderLineage.VT31_NAS100,
                qore_symbol="NAS100",
                signal_fingerprint=_fingerprint(
                    trader="VT31_NAS100",
                    symbol="NAS100",
                    side=side,
                    signal_at=signal_at,
                    entry_at=entry_at,
                    entry=entry,
                    stop=stop,
                    target=target,
                    evidence_ids=evidence,
                ),
                signal_at=signal_at,
                entry_at=entry_at,
                exit_at=exit_at,
                side=side,
                entry_price=entry,
                structural_stop=stop,
                technical_target=target,
                exit_reason=str(row["exit_reason"]),
                gross_structural_outcome_r=Decimal(str(row["r_multiple"])),
                methodology_sha256="sha256:" + methodology,
                source_evidence_ids=evidence,
                decision_context=_context(
                    {
                        "family": "SILVER_BULLET_M1",
                        "ctx_timeframe": "M1",
                        "ctx_session": "NEW_YORK_AM",
                    }
                ),
            )
        )
    return out


def _turtle_rows(
    payload: dict[str, Any],
    *,
    artifact_id: int,
    trader_id: str,
) -> list[Phase22FreshOpportunity]:
    symbol = str(payload["symbol"])
    method_material = {
        "trader_id": trader_id,
        "geometry_module": payload["geometry_module"],
        "candidate": payload["module_report"].get("candidate"),
        "candidate_identity": payload["module_report"].get("candidate_identity"),
        "frozen_contract": payload["module_report"].get("frozen_contract"),
        "frozen_contract_verification": payload["module_report"].get(
            "frozen_contract_verification"
        ),
    }
    methodology = _sha(method_material)
    out = []
    for row in payload["trades"]:
        signal_at = datetime.fromisoformat(str(row["signal_at"]))
        entry_at = datetime.fromisoformat(str(row["entry_at"]))
        exit_at = datetime.fromisoformat(str(row["exit_at"]))
        side = str(row["side"])
        entry = Decimal(str(row["entry_price"]))
        stop = Decimal(str(row["structural_stop"]))
        target = Decimal(str(row["technical_target"]))
        evidence = (
            f"github-actions:3x1y-{trader_id.lower()}:{artifact_id}",
            f"trader-lab:{payload['group_id']}",
        )
        context: dict[str, object] = {}
        for key, value in row.get("setup_context", {}).items():
            context["ctx_" + str(key)] = value
        for key, value in row.get("regime", {}).items():
            # D1 may remain inside a frozen Trader's own methodology but is
            # explicitly not part of the CIBO research feature surface.
            if str(key).startswith("d1_"):
                continue
            context["reg_" + str(key)] = value
        for key in ("family", "posture", "target_route"):
            if row.get(key) is not None:
                context[key] = row[key]
        out.append(
            Phase22FreshOpportunity(
                trader_id=TraderLineage(trader_id),
                qore_symbol=symbol,
                signal_fingerprint=_fingerprint(
                    trader=trader_id,
                    symbol=symbol,
                    side=side,
                    signal_at=signal_at,
                    entry_at=entry_at,
                    entry=entry,
                    stop=stop,
                    target=target,
                    evidence_ids=evidence,
                ),
                signal_at=signal_at,
                entry_at=entry_at,
                exit_at=exit_at,
                side=side,
                entry_price=entry,
                structural_stop=stop,
                technical_target=target,
                exit_reason=str(row["exit_reason"]),
                gross_structural_outcome_r=Decimal(str(row["raw_net_010_r"])),
                methodology_sha256=methodology,
                source_evidence_ids=evidence,
                decision_context=_context(context),
            )
        )
    return out


def _candidate_bindings(audit: dict[str, Any]) -> dict[str, str]:
    if audit.get("all_phases_green") is not True or audit.get("candidate_count") != 7:
        raise ValueError("Trader Lab audit is not 7/7 GREEN")
    phase = next(
        row for row in audit["phases"] if row["phase"] == "P01_TRADER_LAB_RESEARCH"
    )
    result = {}
    for trader, row in phase["traders"].items():
        if (
            row.get("trader_lab_candidate") is not True
            or row.get("trader_lab_state") != "research_ready"
            or row.get("status") != "GREEN"
        ):
            raise ValueError(f"Trader Lab binding not ready: {trader}")
        token = str(row["output_token"])
        if len(token) != 64:
            raise ValueError("candidate fingerprint length drift")
        result[trader] = token
    if set(result) != set(CANONICAL_PHASE22_TRADER_IDS):
        raise ValueError("Trader Lab candidate surface drift")
    return result


def assemble_group(
    *,
    group_id: str,
    roots: dict[str, Path],
    artifacts: dict[str, tuple[int, str]],
    audit: dict[str, Any],
) -> dict[str, Any]:
    bindings = _candidate_bindings(audit)
    opportunity_by_trader: dict[str, list[Phase22FreshOpportunity]] = {}
    vt08 = _json(roots["VT08_FOREX"] / group_id / "vt08-group-lane.json")
    vt31 = _json(roots["VT31_NAS100"] / group_id / "vt31-group-lane.json")
    opportunity_by_trader["VT08_FOREX"] = _vt08_rows(
        vt08,
        artifact_id=artifacts["VT08_FOREX"][0],
    )
    opportunity_by_trader["VT31_NAS100"] = _vt31_rows(
        vt31,
        artifact_id=artifacts["VT31_NAS100"][0],
    )
    for trader in (
        "R34_XAUUSD",
        "R38_EURUSD",
        "R43_GBPUSD",
        "R38_GBPJPY",
        "R42_AUDJPY",
    ):
        payload = _json(
            roots[trader] / group_id / "trader-lab-1y-group-lane.json"
        )
        opportunity_by_trader[trader] = _turtle_rows(
            payload,
            artifact_id=artifacts[trader][0],
            trader_id=trader,
        )

    traders = []
    for trader_id in CANONICAL_PHASE22_TRADER_IDS:
        rows = tuple(opportunity_by_trader[trader_id])
        if not rows:
            raise ValueError(f"{group_id}:{trader_id}: zero opportunities")
        digest = _artifact_digest(artifacts[trader_id][1])
        traders.append(
            Phase22FreshTraderEvidence(
                trader_id=trader_id,
                source_artifact_sha256=digest,
                opportunities=rows,
                fresh_outcomes_executed=True,
                methodology_changed=False,
                legacy_trader_sizing_used_for_cibo=False,
            )
        )

    batch = build_phase22_v4_fresh_batch(tuple(traders))
    opportunities = [row.payload() for row in batch.opportunities]
    return {
        "schema": "qore.cibo.phase22.v4-fresh-batch-assembly.v1",
        "candidate_id": batch.candidate_id,
        "batch_sha256": batch.fingerprint(),
        "validation_mode": "NON_CERTIFYING_BURNED_ADAPTIVE_RESEARCH",
        "research_group_id": group_id,
        "adaptive_search_holdout_burned": True,
        "trader_lab_candidate_bindings": bindings,
        "traders": [
            {
                "trader_id": evidence.trader_id,
                "lane_artifact_id": artifacts[evidence.trader_id][0],
                "lane_artifact_sha256": evidence.source_artifact_sha256,
                "opportunity_count": len(evidence.opportunities),
                "evidence_sha256": evidence.fingerprint(),
                "trader_lab_candidate_fingerprint": bindings[evidence.trader_id],
                "trader_lab_state": "research_ready",
            }
            for evidence in traders
        ],
        "opportunities": opportunities,
        "legacy_trader_sizing_used_for_cibo": False,
        "productive_authority": False,
        "fresh_oos_claimed": False,
        "certification_claimed": False,
    }


def _lane_arg(value: str) -> tuple[str, Path, int, str]:
    trader, sep, rest = value.partition("=")
    if not sep:
        raise ValueError("lane must be TRADER=ROOT,ARTIFACT_ID,DIGEST")
    parts = rest.split(",", 2)
    if len(parts) != 3:
        raise ValueError("lane must be TRADER=ROOT,ARTIFACT_ID,DIGEST")
    return trader, Path(parts[0]), int(parts[1]), parts[2]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", action="append", required=True)
    parser.add_argument("--trader-lab-audit", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    roots: dict[str, Path] = {}
    artifacts: dict[str, tuple[int, str]] = {}
    for raw in args.lane:
        trader, root, artifact_id, digest = _lane_arg(raw)
        roots[trader] = root
        artifacts[trader] = (artifact_id, digest)
    if set(roots) != set(CANONICAL_PHASE22_TRADER_IDS):
        raise ValueError("exact seven lanes required")

    audit = _json(args.trader_lab_audit)
    summary = {}
    for group_id in GROUPS:
        payload = assemble_group(
            group_id=group_id,
            roots=roots,
            artifacts=artifacts,
            audit=audit,
        )
        out = args.output_root / group_id
        out.mkdir(parents=True, exist_ok=True)
        (out / "seven-trader-cibo-batch.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        counts = {
            row["trader_id"]: int(row["opportunity_count"])
            for row in payload["traders"]
        }
        summary[group_id] = {
            "opportunity_count": len(payload["opportunities"]),
            "by_trader": counts,
            "batch_sha256": payload["batch_sha256"],
        }

    report = {
        "schema": "qore.cibo.trader-lab.3x1y-seven-trader-assembly.v1",
        "status": "READY_FOR_CIBO_REPLAY",
        "groups": summary,
        "all_groups_exact_7_traders": True,
        "all_traders_research_ready": True,
        "legacy_trader_sizing_used_for_cibo": False,
        "adaptive_search_holdouts_burned": True,
        "fresh_oos_claimed": False,
        "certification_claimed": False,
        "broker_mutation": False,
        "live": False,
        "production": False,
        "real_capital": False,
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "assembly-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
