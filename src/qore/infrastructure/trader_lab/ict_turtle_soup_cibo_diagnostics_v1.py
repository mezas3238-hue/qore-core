"""CIBO diagnostic attribution over consumed ICT Turtle Soup R5 holdout evidence.

Research-only adapter. It joins exact R5 trade timestamps to frozen Behavior Lab
events, emits deterministic CIBO observation states, and preserves the authority
boundary: observation/association/hypothesis != operating rule.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
    CiboFunctionalEvidence,
    CiboGovernedEvidenceKind,
)
from qore.infrastructure.cibo.opportunity_search import (
    CiboOpportunityHypothesis,
    CiboOpportunitySearch,
    CiboOpportunityState,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure

IDENTITY = "ICT_TS_CIBO_DIAGNOSTICS_V1"
PARENT_IDENTITY = "ICT_TS_BEHAVIOR_LAB_V1"
HOLDOUT_ID = "ICT_TS_R5_FRESH_2016_2018"
LAB_REF = CiboEvidenceRef("lab:ict-ts-behavior-v1:run-35125861002")
HOLDOUT_REF = CiboEvidenceRef("lab:ict-ts-r5-holdout:run-35118222306")


class EvidenceTier(StrEnum):
    E0_OBSERVATION = "E0_OBSERVATION"
    E1_ASSOCIATION = "E1_ASSOCIATION"
    E2_CAUSAL_HYPOTHESIS = "E2_CAUSAL_HYPOTHESIS"
    E3_REPLICATED_MECHANISM = "E3_REPLICATED_MECHANISM"
    E4_CANDIDATE_RULE = "E4_CANDIDATE_RULE"


@dataclass(frozen=True, slots=True)
class EventObservation:
    symbol: str
    timeframe: str
    side: str
    source_opened_at: datetime
    raid_at: datetime
    same_source_reclaim: bool
    cisd_confirmed: bool
    fvg_after_raid: bool
    exact_equal_count: int
    opposite_reference_hit_24h: bool
    opposite_reference_hit_minutes: int | None


@dataclass(frozen=True, slots=True)
class CiboTradeDiagnostic:
    trade_id: int
    symbol: str
    side: str
    entry_at: datetime
    exit_at: datetime
    exit_reason: str
    gross_r: float
    primary_net_r: float
    evidence_tier: str
    authority: str
    setup_validity_state: str
    market_phase: str
    delivery_state: str
    liquidity_state: str
    primary_dol_state: str
    protected_swing_state: str
    d1_full_c1_traverse_pre_entry: bool
    h4_full_c1_traverse_pre_entry: bool
    d1_cisd_observed: bool
    h4_cisd_observed: bool
    d1_reclaim_observed: bool
    h4_reclaim_observed: bool
    h4_fvg_observed: bool
    observation_codes: tuple[str, ...]
    diagnostic_cause_codes: tuple[str, ...]
    evidence_status: str
    evidence_refs: tuple[str, ...]


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no", "", "nan", "none"}:
        return False
    raise ValueError(f"invalid boolean value: {value}")


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return None
    return int(float(text))


def _load_trades(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, list) or not payload:
        raise ValueError("holdout trades must be a non-empty list")
    return payload


def _trade_keys(trades: list[dict[str, Any]]) -> set[tuple[str, str, str, datetime]]:
    result: set[tuple[str, str, str, datetime]] = set()
    for trade in trades:
        symbol = str(trade["symbol"])
        side = str(trade["side"])
        result.add((symbol, "D1", side, _dt(str(trade["daily_c2_opened_at"]))))
        result.add((symbol, "H4", side, _dt(str(trade["h4_c2_opened_at"]))))
    return result


def _load_matching_events(
    path: Path,
    keys: set[tuple[str, str, str, datetime]],
) -> tuple[
    dict[tuple[str, str, str, datetime], EventObservation],
    set[tuple[str, str, str, datetime]],
]:
    prior: dict[tuple[str, str, str, datetime], EventObservation] = {}
    swing3: set[tuple[str, str, str, datetime]] = set()
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            key = (
                str(row["symbol"]),
                str(row["timeframe"]),
                str(row["side"]),
                _dt(str(row["source_opened_at"])),
            )
            if key not in keys:
                continue
            reference_type = str(row["reference_type"])
            if reference_type == "swing-3":
                swing3.add(key)
                continue
            if reference_type != "prior-candle":
                continue
            if key in prior:
                raise ValueError(f"duplicate exact prior-candle event: {key}")
            prior[key] = EventObservation(
                symbol=key[0],
                timeframe=key[1],
                side=key[2],
                source_opened_at=key[3],
                raid_at=_dt(str(row["raid_at"])),
                same_source_reclaim=_bool(row["same_source_reclaim"]),
                cisd_confirmed=_bool(row["cisd_confirmed"]),
                fvg_after_raid=_bool(row["fvg_after_raid"]),
                exact_equal_count=int(row["exact_equal_count"]),
                opposite_reference_hit_24h=_bool(row["opposite_reference_hit_24h"]),
                opposite_reference_hit_minutes=_int_or_none(
                    row["opposite_reference_hit_minutes"]
                ),
            )
    missing = keys - prior.keys()
    if missing:
        raise ValueError(f"missing exact prior-candle events: {len(missing)}")
    return prior, swing3


def _opposite_hit_pre_entry(event: EventObservation, entry_at: datetime) -> bool:
    if not event.opposite_reference_hit_24h:
        return False
    if event.opposite_reference_hit_minutes is None:
        return False
    hit_at = event.raid_at + timedelta(minutes=event.opposite_reference_hit_minutes)
    return hit_at <= entry_at


def _liquidity_state(
    d1_key: tuple[str, str, str, datetime],
    h4_key: tuple[str, str, str, datetime],
    d1: EventObservation,
    h4: EventObservation,
    swing3: set[tuple[str, str, str, datetime]],
) -> str:
    stacked = (
        d1.exact_equal_count > 1
        or h4.exact_equal_count > 1
        or d1_key in swing3
        or h4_key in swing3
    )
    return (
        "stacked-or-confluent-liquidity"
        if stacked
        else "isolated-prior-candle-liquidity"
    )


def _delivery_state(d1: EventObservation, h4: EventObservation) -> str:
    if d1.cisd_confirmed and h4.cisd_confirmed:
        return "d1-h4-ltf-cisd-observed"
    if d1.cisd_confirmed:
        return "d1-only-ltf-cisd-observed"
    if h4.cisd_confirmed:
        return "h4-only-ltf-cisd-observed"
    return "reclaim-without-ltf-cisd-observed"


def _market_phase(d1_full: bool, h4_full: bool) -> str:
    if d1_full and h4_full:
        return "two-level-full-range-repricing"
    if d1_full:
        return "daily-full-range-repricing"
    if h4_full:
        return "h4-full-range-repricing"
    return "partial-range-repricing"


def _functional_evidence(as_of: datetime) -> CiboFunctionalEvidence:
    return CiboFunctionalEvidence(
        status=CiboEvidenceStatus.EVIDENCE_DEPENDENT,
        evidence_refs=(LAB_REF, HOLDOUT_REF),
        as_of=as_of,
        dependency_kind=CiboGovernedEvidenceKind.LAB,
        reasons=("consumed-diagnostic-only", "no-authority-root"),
    )


def _diagnose_one(
    trade_id: int,
    trade: dict[str, Any],
    prior: dict[tuple[str, str, str, datetime], EventObservation],
    swing3: set[tuple[str, str, str, datetime]],
) -> CiboTradeDiagnostic:
    symbol = str(trade["symbol"])
    side = str(trade["side"])
    entry_at = _dt(str(trade["entry_at"]))
    exit_at = _dt(str(trade["exit_at"]))
    d1_key = (symbol, "D1", side, _dt(str(trade["daily_c2_opened_at"])))
    h4_key = (symbol, "H4", side, _dt(str(trade["h4_c2_opened_at"])))
    d1 = prior[d1_key]
    h4 = prior[h4_key]
    d1_full = _opposite_hit_pre_entry(d1, entry_at)
    h4_full = _opposite_hit_pre_entry(h4, entry_at)

    observation_codes = {
        "d1-reclaim" if d1.same_source_reclaim else "d1-no-reclaim",
        "h4-reclaim" if h4.same_source_reclaim else "h4-no-reclaim",
        "d1-ltf-cisd" if d1.cisd_confirmed else "d1-no-ltf-cisd",
        "h4-ltf-cisd" if h4.cisd_confirmed else "h4-no-ltf-cisd",
        "h4-fvg" if h4.fvg_after_raid else "h4-no-fvg",
        "d1-full-c1-traverse" if d1_full else "d1-no-full-c1-traverse",
        "h4-full-c1-traverse" if h4_full else "h4-no-full-c1-traverse",
    }
    cause_codes: set[str] = set()
    if not d1_full:
        cause_codes.add("e1-clue.d1-incomplete-full-range-repricing")
    if str(trade["exit_reason"]) == "stop":
        cause_codes.add("e1-cluster.hard-stop")
    if d1.cisd_confirmed != h4.cisd_confirmed:
        cause_codes.add("e0-observation.htf-ltf-cisd-asymmetry")

    evidence = _functional_evidence(exit_at)
    return CiboTradeDiagnostic(
        trade_id=trade_id,
        symbol=symbol,
        side=side,
        entry_at=entry_at,
        exit_at=exit_at,
        exit_reason=str(trade["exit_reason"]),
        gross_r=float(trade["gross_r"]),
        primary_net_r=float(trade["primary_net_r"]),
        evidence_tier=EvidenceTier.E0_OBSERVATION.value,
        authority=CiboFunctionalAuthority.OBSERVATION.value,
        setup_validity_state="source-valid-consumed-r5",
        market_phase=_market_phase(d1_full, h4_full),
        delivery_state=_delivery_state(d1, h4),
        liquidity_state=_liquidity_state(d1_key, h4_key, d1, h4, swing3),
        primary_dol_state="intact-at-entry-by-r5-contract",
        protected_swing_state="authentic-ideal-confirmed-by-r5-contract",
        d1_full_c1_traverse_pre_entry=d1_full,
        h4_full_c1_traverse_pre_entry=h4_full,
        d1_cisd_observed=d1.cisd_confirmed,
        h4_cisd_observed=h4.cisd_confirmed,
        d1_reclaim_observed=d1.same_source_reclaim,
        h4_reclaim_observed=h4.same_source_reclaim,
        h4_fvg_observed=h4.fvg_after_raid,
        observation_codes=tuple(sorted(observation_codes)),
        diagnostic_cause_codes=tuple(sorted(cause_codes)),
        evidence_status=evidence.status.value,
        evidence_refs=tuple(ref.value for ref in evidence.evidence_refs),
    )


def diagnose_holdout(trades_path: Path, events_path: Path) -> list[CiboTradeDiagnostic]:
    trades = _load_trades(trades_path)
    keys = _trade_keys(trades)
    prior, swing3 = _load_matching_events(events_path, keys)
    return [
        _diagnose_one(index, trade, prior, swing3)
        for index, trade in enumerate(trades, start=1)
    ]


def _hypothesis_record(as_of: datetime) -> tuple[object, ...]:
    hypothesis = CiboOpportunityHypothesis(
        opportunity_code="ict-ts.d1-full-c1-traverse",
        market_refs=(LAB_REF, HOLDOUT_REF),
        evidence=_functional_evidence(as_of),
        state=CiboOpportunityState.HYPOTHESIS,
        authority=CiboFunctionalAuthority.OPINION,
        declared_at=as_of,
    )
    evaluated = CiboOpportunitySearch().evaluate(hypothesis)
    if isinstance(evaluated, Failure):
        raise evaluated.error
    return evaluated.value.logical_values()


def _serialize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


def write_outputs(
    diagnostics: list[CiboTradeDiagnostic],
    output: Path,
) -> dict[str, Any]:
    if len(diagnostics) != 12:
        raise ValueError(f"expected 12 R5 trades, got {len(diagnostics)}")
    output.mkdir(parents=True, exist_ok=True)
    rows = [_serialize(asdict(item)) for item in diagnostics]
    (output / "cibo-trade-ledger.json").write_text(
        json.dumps(rows, indent=2, sort_keys=True) + "\n"
    )
    with (output / "cibo-trade-ledger.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: json.dumps(value, sort_keys=True)
                    if isinstance(value, list)
                    else value
                    for key, value in row.items()
                }
            )

    winners = [item for item in diagnostics if item.gross_r > 0]
    losers = [item for item in diagnostics if item.gross_r < 0]
    stops = [item for item in diagnostics if item.exit_reason == "stop"]
    non_stops = [item for item in diagnostics if item.exit_reason != "stop"]
    as_of = max(item.exit_at for item in diagnostics)
    summary = {
        "schema": "qore.ict_ts_cibo_diagnostics.holdout.v1",
        "identity": IDENTITY,
        "parent_identity": PARENT_IDENTITY,
        "holdout_id": HOLDOUT_ID,
        "trade_count": len(diagnostics),
        "exact_d1_matches": len(diagnostics),
        "exact_h4_matches": len(diagnostics),
        "approximate_matching_used": False,
        "evidence_status": "CONSUMED_DIAGNOSTIC_ONLY",
        "cibo_authority_ceiling": CiboFunctionalAuthority.OPINION.value,
        "evidence_tier_ceiling": EvidenceTier.E2_CAUSAL_HYPOTHESIS.value,
        "observations": {
            "d1_reclaim": sum(item.d1_reclaim_observed for item in diagnostics),
            "h4_reclaim": sum(item.h4_reclaim_observed for item in diagnostics),
            "h4_fvg": sum(item.h4_fvg_observed for item in diagnostics),
            "d1_full_c1_traverse_pre_entry": sum(
                item.d1_full_c1_traverse_pre_entry for item in diagnostics
            ),
            "h4_full_c1_traverse_pre_entry": sum(
                item.h4_full_c1_traverse_pre_entry for item in diagnostics
            ),
        },
        "cohorts": {
            "gross_winners": {
                "n": len(winners),
                "d1_full_c1_traverse": sum(
                    item.d1_full_c1_traverse_pre_entry for item in winners
                ),
            },
            "gross_losers": {
                "n": len(losers),
                "d1_full_c1_traverse": sum(
                    item.d1_full_c1_traverse_pre_entry for item in losers
                ),
            },
            "hard_stops": {
                "n": len(stops),
                "d1_full_c1_traverse": sum(
                    item.d1_full_c1_traverse_pre_entry for item in stops
                ),
                "gross_total_r": sum(item.gross_r for item in stops),
            },
            "non_stops": {
                "n": len(non_stops),
                "gross_total_r": sum(item.gross_r for item in non_stops),
            },
        },
        "registered_hypothesis": _serialize(_hypothesis_record(as_of)),
        "governance": {
            "pnl_used_for_filter_selection": False,
            "candidate_rule_created": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="CIBO Turtle Soup holdout diagnostics V1")
    parser.add_argument("trades", type=Path)
    parser.add_argument("events", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    diagnostics = diagnose_holdout(args.trades, args.events)
    print(json.dumps(write_outputs(diagnostics, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
