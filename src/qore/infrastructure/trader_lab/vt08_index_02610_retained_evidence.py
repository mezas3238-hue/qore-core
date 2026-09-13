"""Aggregate retained VT-08 Futures/index 02/06/10 research evidence.

This module consumes the already-retained source-executable V2 artifacts from
run 34661791159. It reports descriptive candidate-path evidence only. It never
turns unresolved candidates into trades and grants no promotion authority.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

from qore.kernel.errors import InfrastructureError

SCHEMA = "qore.research.vt08_index_02610_retained_evidence.v1"
SOURCE_RUN_ID = 34661791159
SOURCE_SOFTWARE_SHA = "a5b9c6e0d65539c1f755dda8bb3d7ce7b1a839b0"
EXPECTED_MARKETS = ("NAS100", "SP500", "US30")
EXPECTED_PROVIDER_SYMBOLS = {
    "NAS100": "USTEC",
    "SP500": "US500",
    "US30": "US30",
}
EXPECTED_ANCHORS = (2, 6, 10)
EXPECTED_ANCHOR_LABELS = ("02:00", "06:00", "10:00")
EXPECTED_TIMEZONE = "America/New_York"


class Vt08Index02610EvidenceError(InfrastructureError):
    __slots__ = ()


def _object(value: object, *, name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08Index02610EvidenceError(f"{name} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, *, name: str) -> list[object]:
    if type(value) is not list:
        raise Vt08Index02610EvidenceError(f"{name} must be an array")
    return cast(list[object], value)


def _text(value: object, *, name: str) -> str:
    if type(value) is not str or not value:
        raise Vt08Index02610EvidenceError(f"{name} must be non-empty text")
    return value


def _integer(value: object, *, name: str) -> int:
    if type(value) is not int or value < 0:
        raise Vt08Index02610EvidenceError(f"{name} must be a non-negative int")
    return value


def _decimal(value: object, *, name: str) -> Decimal:
    raw = _text(value, name=name)
    try:
        parsed = Decimal(raw)
    except InvalidOperation as error:
        raise Vt08Index02610EvidenceError(f"{name} must be Decimal text") from error
    if not parsed.is_finite():
        raise Vt08Index02610EvidenceError(f"{name} must be finite")
    return parsed


def _read_json(path: Path) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08Index02610EvidenceError(f"cannot read {path}") from error
    return _object(decoded, name=str(path))


@dataclass(frozen=True, slots=True)
class AnchorEvidence:
    candidate_count: int
    mean_mae_r: Decimal
    mean_mfe_r: Decimal
    mean_h4_close_r: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "candidate_count": self.candidate_count,
            "mean_mae_r_descriptive_only": format(self.mean_mae_r, "f"),
            "mean_mfe_r_descriptive_only": format(self.mean_mfe_r, "f"),
            "mean_post_signal_h4_close_r_descriptive_only": format(
                self.mean_h4_close_r, "f"
            ),
        }


@dataclass(frozen=True, slots=True)
class MarketEvidence:
    canonical_market: str
    provider_symbol: str
    bar_count: int
    first_opened_at: str
    last_closed_at: str
    mechanical_candidates: int
    automatic_setups: int
    filled_count: int
    source_judgment_required: int
    anchors: tuple[tuple[str, AnchorEvidence], ...]

    def payload(self) -> dict[str, object]:
        return {
            "canonical_market": self.canonical_market,
            "provider_symbol": self.provider_symbol,
            "bar_count": self.bar_count,
            "first_opened_at": self.first_opened_at,
            "last_closed_at": self.last_closed_at,
            "mechanical_candidates": self.mechanical_candidates,
            "automatic_setups": self.automatic_setups,
            "filled_count": self.filled_count,
            "source_judgment_required": self.source_judgment_required,
            "by_anchor_new_york": {
                label: evidence.payload() for label, evidence in self.anchors
            },
        }


def _require_scope(payload: dict[str, object], *, name: str) -> None:
    scope = _object(payload.get("human_owner_operating_scope"), name=name)
    anchors = tuple(_array(scope.get("futures_h4_anchors"), name=f"{name}.anchors"))
    if anchors != EXPECTED_ANCHORS:
        raise Vt08Index02610EvidenceError(f"{name} futures anchors drifted")
    if _text(scope.get("timezone"), name=f"{name}.timezone") != EXPECTED_TIMEZONE:
        raise Vt08Index02610EvidenceError(f"{name} timezone drifted")


def _load_market(directory: Path, *, expected_market: str) -> MarketEvidence:
    summary = _read_json(directory / "research-summary.json")
    characterization = _read_json(directory / "characterization.json")
    market = _read_json(directory / "market-evidence.json")

    if _text(summary.get("software_sha"), name="software_sha") != SOURCE_SOFTWARE_SHA:
        raise Vt08Index02610EvidenceError("retained evidence software SHA drifted")
    if _text(summary.get("symbol"), name="summary.symbol") != expected_market:
        raise Vt08Index02610EvidenceError("summary canonical market mismatch")
    if summary.get("environment") != "demo" or summary.get("read_only") is not True:
        raise Vt08Index02610EvidenceError("retained evidence must be DEMO/read-only")
    if summary.get("research_only") is not True:
        raise Vt08Index02610EvidenceError("retained evidence must remain research-only")
    _require_scope(summary, name="summary.operating_scope")

    if _text(market.get("software_sha"), name="market.software_sha") != SOURCE_SOFTWARE_SHA:
        raise Vt08Index02610EvidenceError("market evidence software SHA drifted")
    if _text(market.get("canonical_symbol"), name="canonical_symbol") != expected_market:
        raise Vt08Index02610EvidenceError("market evidence canonical symbol mismatch")
    provider = _text(market.get("provider_symbol_name"), name="provider_symbol_name")
    if provider != EXPECTED_PROVIDER_SYMBOLS[expected_market]:
        raise Vt08Index02610EvidenceError("provider symbol mapping drifted")
    owner_scope = _object(market.get("owner_operating_scope"), name="owner scope")
    owner_anchors = tuple(
        _array(owner_scope.get("futures_h4_opens"), name="owner futures anchors")
    )
    if owner_anchors != EXPECTED_ANCHORS:
        raise Vt08Index02610EvidenceError("market owner anchors drifted")
    if _text(owner_scope.get("timezone"), name="owner timezone") != EXPECTED_TIMEZONE:
        raise Vt08Index02610EvidenceError("market owner timezone drifted")

    coverage = _object(market.get("coverage"), name="coverage")
    bar_count = _integer(coverage.get("bar_count"), name="coverage.bar_count")
    if bar_count <= 0:
        raise Vt08Index02610EvidenceError("market evidence cannot be empty")

    funnel = _object(characterization.get("decision_funnel"), name="decision_funnel")
    mechanical = _integer(
        funnel.get("mechanical_candidates"), name="mechanical_candidates"
    )
    automatic = _integer(funnel.get("automatic_setups"), name="automatic_setups")
    filled = _integer(funnel.get("filled"), name="filled")
    source_judgment = _integer(
        funnel.get("source_judgment_required"), name="source_judgment_required"
    )
    if source_judgment > mechanical:
        raise Vt08Index02610EvidenceError("source judgment count exceeds candidates")
    if automatic > mechanical or filled > automatic:
        raise Vt08Index02610EvidenceError("candidate/setup/fill funnel does not reconcile")

    by_anchor = _object(
        characterization.get("by_h4_anchor_hour_new_york"),
        name="by_h4_anchor_hour_new_york",
    )
    if tuple(sorted(by_anchor)) != tuple(sorted(EXPECTED_ANCHOR_LABELS)):
        raise Vt08Index02610EvidenceError("anchor characterization drifted")

    anchors: list[tuple[str, AnchorEvidence]] = []
    anchor_candidate_total = 0
    for label in EXPECTED_ANCHOR_LABELS:
        row = _object(by_anchor.get(label), name=f"anchor {label}")
        count = _integer(row.get("candidate_count"), name=f"{label}.candidate_count")
        anchor_candidate_total += count
        anchors.append(
            (
                label,
                AnchorEvidence(
                    candidate_count=count,
                    mean_mae_r=_decimal(
                        row.get("mean_mae_r_descriptive_only"),
                        name=f"{label}.mean_mae",
                    ),
                    mean_mfe_r=_decimal(
                        row.get("mean_mfe_r_descriptive_only"),
                        name=f"{label}.mean_mfe",
                    ),
                    mean_h4_close_r=_decimal(
                        row.get("mean_post_signal_h4_close_r_descriptive_only"),
                        name=f"{label}.mean_h4_close",
                    ),
                ),
            )
        )
    if anchor_candidate_total != mechanical:
        raise Vt08Index02610EvidenceError("anchor candidate counts do not reconcile")

    return MarketEvidence(
        canonical_market=expected_market,
        provider_symbol=provider,
        bar_count=bar_count,
        first_opened_at=_text(coverage.get("first_opened_at"), name="first_opened_at"),
        last_closed_at=_text(coverage.get("last_closed_at"), name="last_closed_at"),
        mechanical_candidates=mechanical,
        automatic_setups=automatic,
        filled_count=filled,
        source_judgment_required=source_judgment,
        anchors=tuple(anchors),
    )


def _weighted_anchor(
    markets: tuple[MarketEvidence, ...], *, label: str
) -> AnchorEvidence:
    count = 0
    mae = Decimal(0)
    mfe = Decimal(0)
    close = Decimal(0)
    for market in markets:
        rows = dict(market.anchors)
        row = rows[label]
        count += row.candidate_count
        mae += row.mean_mae_r * row.candidate_count
        mfe += row.mean_mfe_r * row.candidate_count
        close += row.mean_h4_close_r * row.candidate_count
    if count == 0:
        return AnchorEvidence(0, Decimal(0), Decimal(0), Decimal(0))
    denominator = Decimal(count)
    return AnchorEvidence(
        candidate_count=count,
        mean_mae_r=mae / denominator,
        mean_mfe_r=mfe / denominator,
        mean_h4_close_r=close / denominator,
    )


def build_report(
    *, nas100: Path, sp500: Path, us30: Path
) -> dict[str, object]:
    markets = (
        _load_market(nas100, expected_market="NAS100"),
        _load_market(sp500, expected_market="SP500"),
        _load_market(us30, expected_market="US30"),
    )
    aggregate_anchors = {
        label: _weighted_anchor(markets, label=label).payload()
        for label in EXPECTED_ANCHOR_LABELS
    }
    mechanical = sum(item.mechanical_candidates for item in markets)
    automatic = sum(item.automatic_setups for item in markets)
    filled = sum(item.filled_count for item in markets)
    source_judgment = sum(item.source_judgment_required for item in markets)

    return {
        "schema": SCHEMA,
        "source_run_id": SOURCE_RUN_ID,
        "source_software_sha": SOURCE_SOFTWARE_SHA,
        "research_only": True,
        "consumed_evidence": True,
        "fresh_holdout": False,
        "demo_eligible": False,
        "live_authorized": False,
        "production_authorized": False,
        "markets": [item.payload() for item in markets],
        "aggregate": {
            "mechanical_candidate_count": mechanical,
            "automatic_setup_count": automatic,
            "filled_count": filled,
            "source_judgment_required": source_judgment,
            "by_anchor_new_york": aggregate_anchors,
        },
        "adjudication": {
            "executable_economic_sample_available": filled > 0,
            "win_loss_pf_claim_authorized": filled > 0,
            "retained_source_contract_blocks_trade_economics": filled == 0,
            "reason": (
                "retained source-faithful index evidence contains mechanical "
                "candidates but no automatic executable setups; descriptive MFE/MAE/"
                "H4-close paths are not trades"
            ),
            "schedule_selection_from_descriptive_paths_authorized": False,
            "v2_vs_v3_schedule_only_comparison_authorized": False,
        },
        "governance": {
            "timezone": EXPECTED_TIMEZONE,
            "owner_futures_anchors": list(EXPECTED_ANCHORS),
            "canonical_markets": list(EXPECTED_MARKETS),
            "methodology_mutation": False,
            "certified_forex_b01_mutated": False,
            "requires_distinct_preregistered_candidate_for_new_execution_logic": True,
            "requires_fresh_unseen_validation_after_methodology_change": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100", type=Path, required=True)
    parser.add_argument("--sp500", type=Path, required=True)
    parser.add_argument("--us30", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    report = build_report(nas100=args.nas100, sp500=args.sp500, us30=args.us30)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            report,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
