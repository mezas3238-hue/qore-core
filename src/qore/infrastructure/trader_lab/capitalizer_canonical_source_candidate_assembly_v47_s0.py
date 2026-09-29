"""Canonical source-candidate assembly primitives for Capitalizer V47-S0.

S0 is pre-economic. It builds deterministic, causal binders needed to transform
provider-native history into the V46 canonical historical bundle.

The first closed primitive is exact provider-tick fill resolution. Unlike the
legacy M1 touch convention, S0 never back-dates a fill to the opening timestamp
of an M1 bar whose later high/low proved the touch.

Frozen in PR #623 comment 5889541472.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import cast

from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateDecision,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerSide,
)
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_historical_replay_adapter_v46 as v46_adapter,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_CAPITALIZER_CANONICAL_SOURCE_CANDIDATE_ASSEMBLY_V47_S0"
PREDECLARATION_COMMENT_ID = 5889541472
PRICE_SCALE = Decimal(100_000)


class S0BinderStatus(StrEnum):
    READY = "READY"
    COMPOSER_READY_REQUIRES_BINDING = "COMPOSER_READY_REQUIRES_BINDING"
    MISSING = "MISSING"


@dataclass(frozen=True, slots=True)
class S0Binder:
    key: str
    status: S0BinderStatus
    hard_blocker: bool
    evidence: str


@dataclass(frozen=True, slots=True)
class DecodedProviderTick:
    observed_at: datetime
    price: Decimal


@dataclass(frozen=True, slots=True)
class ProviderFillResolution:
    side: CapitalizerSide
    quote_side: str
    armed_level: Decimal
    interval_start: datetime
    interval_end: datetime
    filled: bool
    fill_at: datetime | None
    fill_price: Decimal | None
    provider_tick_count: int
    provider_native: bool = True
    interpolation_used: bool = False
    synthetic_tick_used: bool = False
    m1_open_backdating_used: bool = False
    outcome_used: bool = False

    def __post_init__(self) -> None:
        _aware(self.interval_start)
        _aware(self.interval_end)
        if self.interval_end < self.interval_start:
            raise ValueError("S0 fill interval cannot move backward")
        if self.quote_side not in {"ASK", "BID"}:
            raise ValueError("S0 quote side must be ASK/BID")
        expected = "ASK" if self.side is CapitalizerSide.LONG else "BID"
        if self.quote_side != expected:
            raise ValueError("S0 executable quote side mismatch")
        if self.armed_level <= 0:
            raise ValueError("S0 armed level must be positive")
        if self.provider_tick_count < 0:
            raise ValueError("S0 tick count cannot be negative")
        if self.filled != (self.fill_at is not None and self.fill_price is not None):
            raise ValueError("S0 fill payload mismatch")
        if self.fill_at is not None:
            fill_at = _aware(self.fill_at)
            if not self.interval_start <= fill_at <= self.interval_end:
                raise ValueError("S0 fill timestamp outside requested interval")
        if (
            not self.provider_native
            or self.interpolation_used
            or self.synthetic_tick_used
            or self.m1_open_backdating_used
            or self.outcome_used
        ):
            raise ValueError("S0 provider-fill governance violated")


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("S0 requires timezone-aware timestamps")
    return value.astimezone(UTC)


def decode_provider_tick_interval(
    ticks: tuple[object, ...],
    *,
    interval_start: datetime,
    interval_end: datetime,
    digits: int,
    has_more: bool,
) -> tuple[DecodedProviderTick, ...]:
    """Decode complete cTrader compressed historical ticks for one interval.

    cTrader historical tick payloads are newest-first. The first row is
    absolute; subsequent rows carry timestamp/price deltas.
    """

    start = _aware(interval_start)
    end = _aware(interval_end)
    if end < start:
        raise ValueError("S0 tick interval cannot move backward")
    if has_more:
        raise ValueError("S0 exact fill requires complete tick response")
    if digits < 0:
        raise ValueError("S0 digits must be non-negative")
    if not ticks:
        return ()

    current_timestamp: int | None = None
    current_relative: int | None = None
    newest_first: list[DecodedProviderTick] = []
    quant = Decimal(1).scaleb(-digits)

    for index, raw in enumerate(ticks):
        timestamp = getattr(raw, "timestamp", None)
        relative = getattr(raw, "tick", None)
        if type(timestamp) is not int or type(relative) is not int:
            raise ValueError("S0 historical tick lacks integer fields")
        if index == 0:
            if timestamp <= 0 or relative <= 0:
                raise ValueError("S0 first historical tick must be absolute")
            current_timestamp = timestamp
            current_relative = relative
        else:
            if current_timestamp is None or current_relative is None:
                raise AssertionError("S0 internal tick decoder state missing")
            current_timestamp += timestamp
            current_relative += relative

        if current_timestamp <= 0 or current_relative <= 0:
            raise ValueError("S0 decoded tick became non-positive")
        observed_at = datetime.fromtimestamp(current_timestamp / 1000, tz=UTC)
        if not start <= observed_at <= end:
            raise ValueError("S0 decoded tick escaped requested interval")
        price = (Decimal(current_relative) / PRICE_SCALE).quantize(quant)
        newest_first.append(
            DecodedProviderTick(observed_at=observed_at, price=price)
        )

    for newer, older in zip(
        newest_first[:-1],
        newest_first[1:],
        strict=True,
    ):
        if older.observed_at > newer.observed_at:
            raise ValueError("S0 provider ticks are not newest-first")

    return tuple(reversed(newest_first))


def resolve_exact_provider_fill(
    *,
    side: CapitalizerSide,
    armed_level: Decimal,
    interval_start: datetime,
    interval_end: datetime,
    ticks: tuple[object, ...],
    digits: int,
    has_more: bool,
) -> ProviderFillResolution:
    """Resolve first executable provider quote that reaches an armed level.

    LONG uses ASK <= level.
    SHORT uses BID >= level.
    """

    if not armed_level.is_finite() or armed_level <= 0:
        raise ValueError("S0 armed level must be finite and positive")
    decoded = decode_provider_tick_interval(
        ticks,
        interval_start=interval_start,
        interval_end=interval_end,
        digits=digits,
        has_more=has_more,
    )
    match: DecodedProviderTick | None = None
    for tick in decoded:
        reached = (
            tick.price <= armed_level
            if side is CapitalizerSide.LONG
            else tick.price >= armed_level
        )
        if reached:
            match = tick
            break

    return ProviderFillResolution(
        side=side,
        quote_side="ASK" if side is CapitalizerSide.LONG else "BID",
        armed_level=armed_level,
        interval_start=_aware(interval_start),
        interval_end=_aware(interval_end),
        filled=match is not None,
        fill_at=None if match is None else match.observed_at,
        fill_price=None if match is None else match.price,
        provider_tick_count=len(decoded),
    )


def request_provider_tick_interval(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol_id: int,
    side: CapitalizerSide,
    interval_start: datetime,
    interval_end: datetime,
    request_id: str,
) -> tuple[tuple[object, ...], bool]:
    """Read the executable quote side only; no mutation/execution API is used."""

    quote_type = 2 if side is CapitalizerSide.LONG else 1
    result = client.request(
        "ProtoOAGetTickDataReq",
        {
            "ctidTraderAccountId": client.account_id,
            "symbolId": symbol_id,
            "type": quote_type,
            "fromTimestamp": int(_aware(interval_start).timestamp() * 1000),
            "toTimestamp": int(_aware(interval_end).timestamp() * 1000),
        },
        client_msg_id=request_id,
        timeout_seconds=60.0,
    )
    if isinstance(result, Failure):
        raise RuntimeError(
            "S0 historical tick request failed: "
            f"{type(result.error).__name__}"
        )
    if getattr(result.value, "ctidTraderAccountId", None) != client.account_id:
        raise RuntimeError("S0 historical tick response account mismatch")
    tick_data = tuple(
        cast(Iterable[object], getattr(result.value, "tickData", ()))
    )
    has_more = getattr(result.value, "hasMore", None)
    if type(has_more) is not bool:
        raise RuntimeError("S0 historical tick response missing hasMore")
    return tick_data, has_more




@dataclass(frozen=True, slots=True)
class SourceStrategyIsolationAssessment:
    canonical_result: v46_adapter.CapitalizerCanonicalHistoricalAdapterResult
    cognitive_gate_source: str = "EXOGENOUS_PASS_FOR_SOURCE_STRATEGY_ISOLATION"
    full_trader_fidelity_claimed: bool = False
    candidate_promotion_allowed: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.cognitive_gate_source != (
            "EXOGENOUS_PASS_FOR_SOURCE_STRATEGY_ISOLATION"
        ):
            raise ValueError("S0 isolation cognitive source identity drift")
        if (
            self.full_trader_fidelity_claimed
            or self.candidate_promotion_allowed
            or self.trader_certified
        ):
            raise ValueError("S0 isolation cannot claim full Trader authority")


def assess_source_strategy_isolation_bundle(
    bundle: v46_adapter.CapitalizerCanonicalHistoricalBundle,
) -> SourceStrategyIsolationAssessment:
    """Run the official V46 adapter under an explicit exogenous PASS token.

    This helper never synthesizes a PASS. The caller must construct the bundle
    with PASS_TO_STRATEGY and accepts that the result is source-strategy
    isolation only, not a historical replay of the full cognitive Trader.
    """

    if (
        bundle.cognitive_gate_decision
        is not CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY
    ):
        raise ValueError(
            "S0 source-strategy isolation requires explicit exogenous PASS"
        )
    result = v46_adapter.assess_canonical_historical_bundle(bundle)
    return SourceStrategyIsolationAssessment(canonical_result=result)


def build_readiness_report() -> dict[str, object]:
    """Track S0 construction blockers without opening economics."""

    binders = (
        S0Binder(
            key="ICT_SOURCE_EVENT_ARMING",
            status=S0BinderStatus.COMPOSER_READY_REQUIRES_BINDING,
            hard_blocker=True,
            evidence=(
                "V3 causal liquidity/sweep/M3-MSS/M1-zone primitives exist; "
                "S0 market-level arming adapter is not yet composed."
            ),
        ),
        S0Binder(
            key="HTF_POI_AND_CLOSURE_BINDING",
            status=S0BinderStatus.COMPOSER_READY_REQUIRES_BINDING,
            hard_blocker=True,
            evidence="Source POI and Candle2/Candle3 detectors exist.",
        ),
        S0Binder(
            key="DAILY_BIAS_BINDING",
            status=S0BinderStatus.COMPOSER_READY_REQUIRES_BINDING,
            hard_blocker=True,
            evidence="Daily bias composer exists once HTF closure is bound.",
        ),
        S0Binder(
            key="M15_CISD_BINDING",
            status=S0BinderStatus.COMPOSER_READY_REQUIRES_BINDING,
            hard_blocker=True,
            evidence="CISD detector exists; historical M15 series binding remains.",
        ),
        S0Binder(
            key="PROTECTED_SWING_BINDING",
            status=S0BinderStatus.COMPOSER_READY_REQUIRES_BINDING,
            hard_blocker=True,
            evidence="Protected-swing composer exists; causal series binding remains.",
        ),
        S0Binder(
            key="M1_MSS_FVG_OB_BINDING",
            status=S0BinderStatus.COMPOSER_READY_REQUIRES_BINDING,
            hard_blocker=True,
            evidence="V46-R1 primitives exist; one assembly path remains to bind.",
        ),
        S0Binder(
            key="STRUCTURAL_TARGET_CANDIDATE_BINDING",
            status=S0BinderStatus.COMPOSER_READY_REQUIRES_BINDING,
            hard_blocker=True,
            evidence=(
                "CIBO Target Destination V2 supplies causal target-family "
                "semantics; S0 direct candidate binding remains."
            ),
        ),
        S0Binder(
            key="DETERMINISTIC_ROUTE_AND_WICK_BINDING",
            status=S0BinderStatus.COMPOSER_READY_REQUIRES_BINDING,
            hard_blocker=True,
            evidence="V46-R1 route/wick composers exist.",
        ),
        S0Binder(
            key="EXACT_PROVIDER_TICK_FILL",
            status=S0BinderStatus.READY,
            hard_blocker=False,
            evidence=(
                "S0 decodes complete provider tick intervals and resolves "
                "first executable ASK/BID touch without M1-open backdating."
            ),
        ),
        S0Binder(
            key="V46_CANONICAL_BUNDLE_ASSEMBLY",
            status=S0BinderStatus.READY,
            hard_blocker=False,
            evidence=(
                "S0 isolation wrapper calls the official V46-R2 adapter and "
                "requires an explicit exogenous PASS token; it cannot claim "
                "full-Trader fidelity or promotion authority."
            ),
        ),
    )
    blockers = tuple(row.key for row in binders if row.hard_blocker)
    return {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "evaluation": "PRE_ECONOMIC_CANDIDATE_ASSEMBLY_READINESS",
        "binders": [asdict(row) for row in binders],
        "blocking_binder_count": len(blockers),
        "blocking_binders": blockers,
        "exact_provider_tick_fill_ready": True,
        "legacy_m1_open_backdating_allowed": False,
        "v41_30s_threshold_reused": False,
        "v41_features_used": False,
        "exogenous_cognitive_pass_isolation_only": True,
        "strategy_economics_calculated": False,
        "exit_simulation_run": False,
        "realized_r_read": False,
        "fresh_holdout_opened": False,
        "candidate_count": 0,
        "trader_certified": False,
        "next_phase": (
            "CANONICAL_SOURCE_CANDIDATE_ASSEMBLY_READY_FOR_ISOLATION_REPLAY"
            if not blockers
            else "CANONICAL_SOURCE_CANDIDATE_ASSEMBLY_GAPS_REMAIN"
        ),
    }


def write_report(report: dict[str, object], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-canonical-source-candidate-assembly-v47-s0.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    report = build_readiness_report()
    write_report(report, Path("audit-output"))
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
