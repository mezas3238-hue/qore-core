"""Frozen VT-31 R4 New York reversal candidate.

The candidate is a deterministic, pre-entry implementation of the TTrades
New York reversal profile. NAS100 is the source market. SP500 and US30 use
the identical Human Owner-authorized transfer configuration.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

CANDIDATE_ID = "VT31_R4_TTRADES_NY_REVERSAL_001"
SCHEMA = "qore.trader_lab.vt31_r4_candidate.v1"
EVIDENCE_SCHEMA = "qore.ctrader_demo.vt31_silver_bullet_v2_m1_evidence.v1"
MARKETS = ("NAS100", "SP500", "US30")
NY = ZoneInfo("America/New_York")


class Vt31R4CandidateError(ValueError):
    """Raised when evidence or candidate invariants fail."""


@dataclass(frozen=True, slots=True)
class Bar:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def __post_init__(self) -> None:
        if self.opened_at.tzinfo is None or self.closed_at.tzinfo is None:
            raise Vt31R4CandidateError("bar timestamps must be timezone-aware")
        if self.closed_at <= self.opened_at:
            raise Vt31R4CandidateError("bar chronology is invalid")
        if self.low > min(self.open, self.close) or self.high < max(
            self.open, self.close
        ):
            raise Vt31R4CandidateError("bar OHLC is invalid")


@dataclass(frozen=True, slots=True)
class Setup:
    market: str
    local_date: date
    side: str
    signal_at: datetime
    entry: Decimal
    initial_stop: Decimal
    target: Decimal
    directional_body_fraction: Decimal

    @property
    def risk(self) -> Decimal:
        return abs(self.entry - self.initial_stop)


@dataclass(frozen=True, slots=True)
class LoadedEvidence:
    market: str
    provider_symbol: str
    account_fingerprint: str
    software_sha: str
    checked_at: datetime
    bars: tuple[Bar, ...]


def _ts(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise Vt31R4CandidateError(f"{field} must be a timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise Vt31R4CandidateError(f"{field} is invalid") from error
    if parsed.tzinfo is None:
        raise Vt31R4CandidateError(f"{field} must be timezone-aware")
    return parsed.astimezone(UTC)


def _decimal(value: object, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise Vt31R4CandidateError(f"{field} must be numeric")
    try:
        return Decimal(str(value))
    except Exception as error:
        raise Vt31R4CandidateError(f"{field} must be numeric") from error


def contract_payload() -> dict[str, object]:
    """Return the immutable pre-fresh candidate contract."""
    return {
        "candidate_id": CANDIDATE_ID,
        "source_market": "NAS100",
        "owner_authorized_transfer_markets": ["SP500", "US30"],
        "identical_configuration_across_markets": True,
        "methodology_sources": [
            "https://ttrades.com/understanding-the-new-york-reversal-in-daily-profiles/",
            "https://ttrades.com/how-to-use-smt-divergence-ttrades-fractal-model/",
            "https://ttrades.com/relative-strength-weakness-smt-divergence-full-guide/",
            "https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/",
            "https://ttrades.com/protected-swings-and-cisd-how-to-trail-your-stop-loss/",
        ],
        "source_day": "18:00-to-17:00-America/New_York",
        "poi": "previous-complete-source-day-extreme",
        "london_failure": "02:00-to-05:00-does-not-reach-selected-POI",
        "ny_sweep_window": "08:30-to-10:30-America/New_York",
        "sweep": "first-eligible-previous-source-day-extreme",
        "both_extremes": "abstain",
        "confirmation": "M5-opposing-series-CISD",
        "confirmation_quality": (
            "direction-aligned-body-at-least-opposing-wick"
        ),
        "simultaneous_cross_index_selection": (
            "maximum-directional-body-fraction;exact-ties-abstain"
        ),
        "entry": "M5-CISD-confirmation-close",
        "initial_stop": "M5-protected-opposing-series-extreme",
        "management": (
            "trail-only-after-new-M1-protected-swing-confirmed-by-"
            "sweep-and-close-through-opposing-series"
        ),
        "initial_risk_denominator": "frozen-at-entry",
        "target": "opposite-London-session-extreme",
        "lifecycle": "16:00-America/New_York",
        "daily_selection": "first-eligible-event-per-market",
        "gap_policy": "censor-trade",
        "same_bar_policy": "censor-unknown-path",
        "friction_gate_r_per_trade": "0.05",
        "stress_research_r_per_trade": ["0.025", "0.05", "0.075", "0.10"],
        "minimum_aggregate_sample": 150,
        "minimum_sample_each_market": 30,
        "profit_factor_gate": ">=1.10",
        "max_drawdown_gate_r": "<=20",
        "quartile_gate": ">=3-of-4-positive",
        "market_gate": "every-market-stressed-mean-positive",
        "side_gate": "long-and-short-stressed-mean-positive",
        "temporal_gate": ">=2-of-3-eligible-blocks-positive",
        "monte_carlo": {
            "algorithm": "sha256-domain-separated-moving-block-bootstrap-v1",
            "paths": 10000,
            "block_length": 5,
            "positive_terminal_probability": ">=0.70",
            "p95_max_drawdown_r": "<=20",
        },
        "fresh_partition": (
            "earliest-unobserved-contiguous-cTrader-DEMO-history-strictly-"
            "before-2024-08-15;target-at-least-730-days;otherwise-forward-DEMO"
        ),
        "fresh_acquisition": "one-shot-after-freeze",
        "causal_equivalence_required": True,
        "retuning_after_fresh": False,
        "demo_only": True,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def contract_fingerprint() -> str:
    encoded = json.dumps(
        contract_payload(), sort_keys=True, separators=(",", ":")
    ).encode()
    return sha256(encoded).hexdigest()


def load_evidence(path: Path, expected_market: str) -> LoadedEvidence:
    """Load and strictly validate one immutable cTrader DEMO M1 file."""
    try:
        decoded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt31R4CandidateError("cannot read evidence") from error
    if not isinstance(decoded, dict):
        raise Vt31R4CandidateError("evidence root must be an object")
    payload = cast(dict[str, object], decoded)
    if payload.get("schema") != EVIDENCE_SCHEMA:
        raise Vt31R4CandidateError("unexpected evidence schema")
    if payload.get("environment") != "demo" or payload.get("read_only") is not True:
        raise Vt31R4CandidateError("evidence must be read-only DEMO")
    if payload.get("account_is_live") is not False:
        raise Vt31R4CandidateError("LIVE evidence is prohibited")
    if payload.get("trading_permission_verified") is not True:
        raise Vt31R4CandidateError("DEMO permission must be verified")
    symbol = payload.get("symbol")
    if not isinstance(symbol, dict) or symbol.get("symbol_name") != expected_market:
        raise Vt31R4CandidateError("market identity mismatch")
    provider = payload.get("provider_symbol_name")
    account = payload.get("account_fingerprint")
    software_sha = payload.get("software_sha")
    if not isinstance(provider, str) or not provider:
        raise Vt31R4CandidateError("provider symbol is missing")
    if not isinstance(account, str) or len(account) != 64:
        raise Vt31R4CandidateError("account fingerprint is invalid")
    if not isinstance(software_sha, str) or len(software_sha) != 40:
        raise Vt31R4CandidateError("software SHA is invalid")
    checked_at = _ts(payload.get("checked_at"), "checked_at")
    periods = payload.get("periods")
    if not isinstance(periods, dict) or set(periods) != {"M1"}:
        raise Vt31R4CandidateError("evidence must contain only M1")
    raw_bars = periods["M1"]
    if not isinstance(raw_bars, list) or not raw_bars:
        raise Vt31R4CandidateError("M1 evidence is empty")
    bars: list[Bar] = []
    for raw in raw_bars:
        if not isinstance(raw, dict):
            raise Vt31R4CandidateError("M1 bar must be an object")
        bars.append(
            Bar(
                opened_at=_ts(raw.get("opened_at"), "opened_at"),
                closed_at=_ts(raw.get("closed_at"), "closed_at"),
                open=_decimal(raw.get("open"), "open"),
                high=_decimal(raw.get("high"), "high"),
                low=_decimal(raw.get("low"), "low"),
                close=_decimal(raw.get("close"), "close"),
            )
        )
    ordered = tuple(
        sorted(
            trades,
            key=lambda item: (
                cast(str, item["signal_at"]),
                cast(str, item["market"]),
            ),
        )
    )
    friction = Decimal("0.05")
    market_stress = {
        market: _metrics(
            tuple(item for item in ordered if item["market"] == market),
            friction,
        )
        for market in MARKETS
    }
    side_stress = {
        side: _metrics(
            tuple(item for item in ordered if item["side"] == side),
            friction,
        )
        for side in ("long", "short")
    }
    quartiles = _quartiles(ordered, friction)
    aggregate = _metrics(ordered)
    stress = _metrics(ordered, friction)
    temporal: dict[str, dict[str, object]] = {}
    for market in MARKETS:
        own = tuple(item for item in ordered if item["market"] == market)
        for year in sorted({cast(str, item["local_date"])[:4] for item in own}):
            temporal[f"{market}:{year}"] = _metrics(
                tuple(
                    item
                    for item in own
                    if cast(str, item["local_date"]).startswith(year)
                ),
                friction,
            )
    eligible = [value for value in temporal.values() if value["sample"] >= 10]
    gates = {
        "aggregate_sample_at_least_150": aggregate["sample"] >= 150,
        "each_market_sample_at_least_30": all(
            value["sample"] >= 30 for value in market_stress.values()
        ),
        "aggregate_stressed_mean_positive": Decimal(cast(str, stress["mean_r"])) > 0,
        "aggregate_stressed_pf_at_least_1_10": (
            stress["profit_factor"] is not None
            and Decimal(cast(str, stress["profit_factor"])) >= Decimal("1.10")
        ),
        "aggregate_stressed_dd_at_most_20r": (
            Decimal(cast(str, stress["max_drawdown_r"])) <= Decimal(20)
        ),
        "every_market_stressed_mean_positive": all(
            Decimal(cast(str, value["mean_r"])) > 0
            for value in market_stress.values()
        ),
        "both_sides_stressed_mean_positive": all(
            value["sample"] and Decimal(cast(str, value["mean_r"])) > 0
            for value in side_stress.values()
        ),
        "three_of_four_quartiles_positive": sum(
            Decimal(cast(str, value["mean_r"])) > 0 for value in quartiles
        )
        >= 3,
        "two_thirds_eligible_temporal_blocks_positive": bool(eligible)
        and sum(
            Decimal(cast(str, value["mean_r"])) > 0 for value in eligible
        )
        * 3
        >= len(eligible) * 2,
    }
    return {
        "schema": SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "contract": contract_payload(),
        "contract_fingerprint": contract_fingerprint(),
        "aggregate": aggregate,
        "stress_0_05r": stress,
        "market_stress": market_stress,
        "side_stress": side_stress,
        "quartiles": quartiles,
        "temporal_blocks": temporal,
        "gates": gates,
        "passes_economic_gates": all(gates.values()),
        "trades": ordered,
        "environment": "demo",
        "read_only": True,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
        "abstention_policy": dict(Counter({"deterministic": 1})),
    }
