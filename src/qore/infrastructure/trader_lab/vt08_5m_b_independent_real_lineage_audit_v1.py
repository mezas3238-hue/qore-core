"""Architect B independent closed-bar audit of A's 488 B01 candidate envelopes.

This consumes *both* A's original historical artifacts and frozen market M15
source bars, re-hashing constituent OHLC itself. The data belongs to research.
Neither a valid source event nor a passing lineage test authorizes any fill.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_5m_a_to_b_candidate_readiness_v1 import (
    inspect_architect_a_candidate,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

MARKETS: Final = ("EURJPY", "USDCHF", "NZDUSD", "CADJPY", "USDCAD")
EXPECTED: Final = {"EURJPY": 88, "USDCHF": 88, "NZDUSD": 126, "CADJPY": 88, "USDCAD": 98}
ORIGINAL_SOURCE_SHA: Final = "b2d33e1b4829d8b4afc76983decca8a99131403c"
LINEAGE_SCHEMA: Final = "qore.trader_lab.vt08_5m_a_b_narrow_source_lineage.research.v1"
_NY = ZoneInfo("America/New_York")


def _canonical_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        .encode("utf-8")
    ).hexdigest()


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("missing causal ISO source timestamp")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("source timestamp lacks timezone")
    return parsed.astimezone(UTC)


def _sha_m15(rows: tuple[Vt08B01Bar, ...]) -> str:
    """Reproduce documented canonical M15 tuple using independently loaded raw bars."""
    value = [
        (
            row.opened_at.astimezone(UTC).isoformat(),
            row.closed_at.astimezone(UTC).isoformat(),
            str(row.open),
            str(row.high),
            str(row.low),
            str(row.close),
        )
        for row in rows
    ]
    return hashlib.sha256(
        json.dumps(value, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _window(
    bars_by_open: dict[datetime, Vt08B01Bar],
    start: datetime,
    end: datetime,
) -> tuple[Vt08B01Bar, ...]:
    """Reconstruct an exact continuously covered M15 interval, no bar interpolation."""
    if not start < end:
        raise ValueError("M15 source window invalid")
    if (end - start).total_seconds() % 900 != 0:
        raise ValueError("M15 source window not aligned with 15m close")
    cursor = start
    rows: list[Vt08B01Bar] = []
    while cursor < end:
        row = bars_by_open.get(cursor)
        if row is None or row.closed_at.astimezone(UTC) != cursor + timedelta(
            minutes=15
        ):
            raise ValueError("M15 evidence missing or candle close inconsistent")
        rows.append(row)
        cursor += timedelta(minutes=15)
    if cursor != end:
        raise ValueError("M15 source window not aligned with 15m close")
    return tuple(rows)


def _verify_ohlc(
    rows: tuple[Vt08B01Bar, ...],
    declared: object,
) -> None:
    if not isinstance(declared, dict):
        raise ValueError("source day proof missing")
    if type(declared.get("m15_count")) is not int or len(rows) != declared["m15_count"]:
        raise ValueError("source day raw M15 count mismatch")
    if declared.get("m15_sha256") != _sha_m15(rows):
        raise ValueError("source day M15 hash mismatch")
    actual = {
        "open": rows[0].open,
        "high": max(x.high for x in rows),
        "low": min(x.low for x in rows),
        "close": rows[-1].close,
    }
    for name, val in actual.items():
        if Decimal(str(declared.get(name))) != val:
            raise ValueError(f"source day {name} OHLC mismatch")


def _bias_from_closed_days(previous: dict[str, object], current: dict[str, object]) -> str:
    """Direct arithmetic cross-check, separate from A's resolve_bias implementation."""
    high = Decimal(str(previous["high"]))
    low = Decimal(str(previous["low"]))
    price = Decimal(str(current["close"]))
    current_low = Decimal(str(current["low"]))
    current_high = Decimal(str(current["high"]))
    if price > high:
        return "long"
    if price < low:
        return "short"
    bullish = current_low < low < price
    bearish = current_high > high > price
    if bullish == bearish:
        return "UNRESOLVED"
    return "long" if bullish else "short"


SOURCE_SNAPSHOT_TIMESTAMPS: Final = (
    "h4_anchor_at",
    "decision_at",
    "evidence_as_of",
    "candle2_closed_at",
    "opposing_series_opened_at",
    "cisd_confirmed_at",
    "ps_confirmed_at",
    "pending_expiry_at",
)
SOURCE_SNAPSHOT_PRICES: Final = ("entry_price", "stop_price", "target_price")
SOURCE_SNAPSHOT_OTHER: Final = (
    "schema",
    "market",
    "ny_date",
    "anchor_ny_hour",
    "source_family",
    "ltf_profile",
    "side",
    "scenario",
    "source_rule_ref",
    "entry_basis",
    "stop_basis",
    "target_basis",
    "filled_lifecycle",
    "source_methodology_sha256",
    "evidence_sha256",
    "research_only",
    "execution_authorized",
    "live_authorized",
)


def _verify_source_and_snapshot_identity(event: dict[str, object]) -> None:
    """Recompute A source and mutable snapshot IDs from declared root fields.

    The immutable ID must not depend on later evidence_sha256. This calculation
    is reproduced independently rather than calling A's hash method.
    """
    keys = SOURCE_SNAPSHOT_OTHER + SOURCE_SNAPSHOT_TIMESTAMPS + SOURCE_SNAPSHOT_PRICES
    if any(key not in event for key in keys):
        raise ValueError("candidate source snapshot missing canonical payload field")
    source_payload = {key: event[key] for key in keys}
    for key in SOURCE_SNAPSHOT_TIMESTAMPS:
        source_payload[key] = _timestamp(event[key]).isoformat(timespec="microseconds")
    for key in SOURCE_SNAPSHOT_PRICES:
        number = Decimal(str(event[key]))
        if not number.is_finite() or number <= 0:
            raise ValueError("candidate price invalid in snapshot root")
        source_payload[key] = format(number.normalize(), "f")
    source_payload["ny_date"] = _timestamp(event["h4_anchor_at"]).astimezone(
        _NY
    ).date().isoformat()
    source_payload["anchor_ny_hour"] = _timestamp(
        event["h4_anchor_at"]
    ).astimezone(_NY).hour
    if _canonical_digest(source_payload) != event.get("event_fingerprint"):
        raise ValueError("A snapshot fingerprint inconsistent with canonical source payload")
    if event.get("event_id") != f"vt08-5m:{event['event_fingerprint']}":
        raise ValueError("A snapshot ID does not bind canonical fingerprint")
    source_identity = {
        "schema": "VT08_5M_CANDIDATE_EVENT_V1",
        "source_rule_ref": event["source_rule_ref"],
        "source_methodology_sha256": event["source_methodology_sha256"],
        "market": event["market"],
        "ltf_profile": event["ltf_profile"],
        "source_family": event["source_family"],
        "scenario": event["scenario"],
        "side": event["side"],
        "h4_anchor_at": _timestamp(event["h4_anchor_at"]).isoformat(
            timespec="microseconds"
        ),
        "opposing_series_opened_at": _timestamp(
            event["opposing_series_opened_at"]
        ).isoformat(timespec="microseconds"),
    }
    if event.get("source_event_id") != (
        f"vt08-5m-source:{_canonical_digest(source_identity)}"
    ):
        raise ValueError("A stable source identity inconsistent with source origin")


def audit_candidate(
    event: object,
    bars_by_open: dict[datetime, Vt08B01Bar],
) -> dict[str, object]:
    if not isinstance(event, dict):
        raise ValueError("invalid candidate envelope")
    _verify_source_and_snapshot_identity(event)
    decision = _timestamp(event.get("decision_at"))
    if event.get("anchor_ny_hour") != decision.astimezone(_NY).hour:
        raise ValueError("candidate anchor NY/UTC clock mismatch")
    bias = event.get("bias_asof_evidence")
    material = event.get("h4_source_m15_provenance")
    if not isinstance(bias, dict) or not isinstance(material, dict):
        raise ValueError("missing full physical source proof")

    current = bias.get("source_day_current")
    previous = bias.get("source_day_previous")
    if not isinstance(current, dict) or not isinstance(previous, dict):
        raise ValueError("source day pair missing")
    current_close = _timestamp(current.get("closed_at"))
    previous_close = _timestamp(previous.get("closed_at"))
    current_open = _timestamp(current.get("opened_at"))
    previous_open = _timestamp(previous.get("opened_at"))
    if not (previous_open < previous_close <= current_open < current_close <= decision):
        raise ValueError("future/overlap in daily bias M15 proof")
    if current_close != _timestamp(event.get("bias_feature_cutoff")):
        raise ValueError("daily bias source cutoff mismatch")
    if current_close != _timestamp(bias.get("bias_feature_cutoff")):
        raise ValueError("daily bias report cutoff mismatch")
    if bias.get("decision_at") != decision.isoformat():
        raise ValueError("daily bias report wrong decision time")
    _verify_ohlc(_window(bars_by_open, current_open, current_close), current)
    _verify_ohlc(_window(bars_by_open, previous_open, previous_close), previous)
    if current.get("m15_sha256") != material.get("current_source_day_m15_sha256"):
        raise ValueError("current day source hash binding failure")
    if previous.get("m15_sha256") != material.get("previous_source_day_m15_sha256"):
        raise ValueError("previous day source hash binding failure")
    if bias.get("bias_side") != _bias_from_closed_days(previous, current):
        raise ValueError("source bias side does not match OHLC")

    c2_closed = _timestamp(event.get("candle2_closed_at"))
    if c2_closed != decision:
        raise ValueError("C2 closed after source decision")
    c2_open = c2_closed - timedelta(hours=4)
    c1_open = c2_open - timedelta(hours=4)
    c1_rows = _window(bars_by_open, c1_open, c2_open)
    c2_rows = _window(bars_by_open, c2_open, c2_closed)
    if _sha_m15(c1_rows) != material.get("c1_m15_sha256"):
        raise ValueError("source C1 raw M15 hash mismatch")
    if _sha_m15(c2_rows) != material.get("c2_m15_sha256"):
        raise ValueError("source C2 raw M15 hash mismatch")
    cisd = _timestamp(event.get("cisd_confirmed_at"))
    ps = _timestamp(event.get("ps_confirmed_at"))
    if cisd != ps or cisd not in {bar.closed_at for bar in c2_rows}:
        raise ValueError("source CISD/PS not an observed closed C2 M15")
    if material.get("cisd_confirmed_at") != cisd.isoformat():
        raise ValueError("source CISD timestamp not tied to physical M15")
    if material.get("decision_at") != decision.isoformat():
        raise ValueError("source C2 physical decision mismatch")
    if material.get("c2_m15_sha256") == material.get("c1_m15_sha256"):
        raise ValueError("indistinguishable reference/source H4 proof")

    # A's lineage hash is checked independently, but is NOT a signed manifest.
    payload = {
        "envelope_snapshot_event_id": event.get("event_id"),
        "bias_asof": bias,
        "source_h4": material,
    }
    if _canonical_digest(payload) != event.get("source_lineage_sha256"):
        raise ValueError("A source-lineage payload/hash inconsistent")
    if _canonical_digest(material) != event.get("evidence_sha256"):
        raise ValueError("A evidence snapshot/hash inconsistent")
    if event.get("cognitive_feature_provenance_complete") is not False:
        raise ValueError("source event misrepresents full cognitive provenance")
    if event.get("joint_a_b_contract_signed") is not False:
        raise ValueError("source event misrepresents joint signature")
    if event.get("trades_executed") != 0 or event.get("pnl_evaluated") is not False:
        raise ValueError("source event claims unmeasured economic results")

    inspected = inspect_architect_a_candidate(event)
    if inspected.cognitive_ready:
        raise ValueError("unsigned/incomplete A V1 incorrectly authorized cognition")
    if inspected.blockers != (
        "A_B:COGNITIVE_FEATURE_PROVENANCE_INCOMPLETE",
        "A_B:CONTRACT_NOT_JOINTLY_FROZEN",
    ):
        raise ValueError("unexpected A-to-B readiness blockers")
    if bias.get("bias_side") != event.get("side"):
        raise ValueError("source candidate/bias side disagreement")
    return {
        "source_event_id": inspected.source_event_id,
        "snapshot_event_id": inspected.snapshot_event_id,
        "ny_date": decision.astimezone(_NY).date().isoformat(),
        "anchor": decision.astimezone(_NY).hour,
        "cognitive_ready": False,
        "blockers": inspected.blockers,
        "verified_closed_m15": True,
    }


def audit_market(
    candidate_json: Path,
    raw_m15_json: Path,
) -> dict[str, object]:
    decoded = json.loads(candidate_json.read_text(encoding="utf-8"))
    if not isinstance(decoded, dict) or decoded.get("schema") != LINEAGE_SCHEMA:
        raise ValueError("unrecognized A original candidate evidence")
    fingerprint, market, _checked, sha, bars = load_market_evidence(raw_m15_json)
    if sha != ORIGINAL_SOURCE_SHA or market not in MARKETS:
        raise ValueError("wrong raw M15 corpus or source version")
    if decoded.get("market") != market or decoded.get("account_fingerprint") != fingerprint:
        raise ValueError("candidate/raw market identity mismatch")
    events = decoded.get("events")
    if not isinstance(events, list) or len(events) != EXPECTED[market]:
        raise ValueError("candidate count diverged from immutable A ledger")
    by_open = {bar.opened_at: bar for bar in bars}
    seen: set[str] = set()
    days: Counter[str] = Counter()
    for event in events:
        report = audit_candidate(event, by_open)
        identity = str(report["source_event_id"])
        if identity in seen:
            raise ValueError("duplicate source event identity")
        seen.add(identity)
        days[str(report["ny_date"])] += 1
    # Owner daily-cardinality: unique days only, ambiguous excluded in A ledger.
    ambiguity = sum(n for n in days.values() if n > 1)
    single = sum(n == 1 for n in days.values())
    if single != decoded.get("unique_daily_candidates"):
        raise ValueError("A day-level eligible count mismatch")
    if ambiguity != decoded.get("ambiguous_day_candidates_excluded"):
        raise ValueError("A day-level ambiguity count mismatch")
    if decoded.get("all_cognitive_features_verified") is not False:
        raise ValueError("incorrect total-cognition claim in A artifact")
    if decoded.get("trades_executed") != 0 or decoded.get("pnl_evaluated") is not False:
        raise ValueError("incorrect simulated fill/PnL claim")
    return {
        "market": market,
        "candidate_events_raw_source_verified": len(events),
        "owner_daily_unique_candidates_not_fills": single,
        "owner_daily_ambiguous_excluded": ambiguity,
        "cognitive_ready": 0,
        "actual_executions": 0,
        "position_cognition_from_real_fills": 0,
        "unattested_bias_cutoff": 0,
        "missing_situation_feature_lineage": len(events),
        "unsigned_joint_contract": len(events),
        "source_sha": sha,
        "research_only": True,
    }


def run_all(root: Path) -> dict[str, object]:
    reports = [
        audit_market(
            root / "candidates" / market / f"{market}-candidate-lineage-full.json",
            root / "source" / market / "market-evidence-1095d.json",
        )
        for market in MARKETS
    ]
    counts = [row["candidate_events_raw_source_verified"] for row in reports]
    if not all(type(value) is int for value in counts):
        raise ValueError("independent source counts are not integers")
    total = sum(value for value in counts if isinstance(value, int))
    if total != 488:
        raise ValueError("488-candidate research ledger not fully reproduced")
    return {
        "schema": "qore.vt08.b_independent_a_source_lineage_audit.research.v1",
        "candidate_events": total,
        "source_lineage_m15_reverified": total,
        "cognitive_ready": 0,
        "actual_fills": 0,
        "preregistered_economic_metrics_computed": False,
        "research_only": True,
        "markets": reports,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_all(args.artifacts_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in result.items() if k != "markets"}, sort_keys=True))


if __name__ == "__main__":
    main()
