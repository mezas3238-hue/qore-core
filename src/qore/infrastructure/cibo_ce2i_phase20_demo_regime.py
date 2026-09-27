"""Causal regime evidence for cTrader DEMO Phase20D forward qualification.

The estimator uses only information known at the decision timestamp:
- closed M5 bars already present in the resident boundary snapshots;
- contemporaneous broker spread/session specifications;
- current account/Risk constraints; and
- the previously observed closed-balance high-water mark.

The rules are frozen and separately fingerprinted so the data adapter cannot be
changed silently after forward evidence begins.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from statistics import median

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    RiskCapitalConstraintEnvelope,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.ctrader_demo_compat import (
    CTraderDemoAccountState,
    CTraderDemoSymbolSpecification,
)
from qore.infrastructure.m5_boundary_cache import M5BoundarySnapshot

PHASE20_DEMO_REGIME_POLICY_ID = "CIBO_PHASE20D_DEMO_REGIME_EVIDENCE_V1"
_REQUIRED_HISTORY = 72
_RECENT_VOL_BARS = 12
_BASE_VOL_BARS = 60
_CORRELATION_WINDOW = 24
_MAX_EVIDENCE_AGE_SECONDS = Decimal("2")
_THIN_SPREAD_TO_RANGE = Decimal("0.25")
_STRESSED_SPREAD_TO_RANGE = Decimal("0.50")
_COMPRESSED_VOL_RATIO = Decimal("0.70")
_ELEVATED_VOL_RATIO = Decimal("1.50")
_DISLOCATED_VOL_RATIO = Decimal("2.50")
_CONCENTRATED_ABS_CORRELATION = 0.85
_BREAK_CORRELATION_DELTA = 0.65


def phase20_demo_regime_policy_sha256() -> str:
    payload = {
        "policy_id": PHASE20_DEMO_REGIME_POLICY_ID,
        "required_history": _REQUIRED_HISTORY,
        "recent_vol_bars": _RECENT_VOL_BARS,
        "base_vol_bars": _BASE_VOL_BARS,
        "correlation_window": _CORRELATION_WINDOW,
        "max_evidence_age_seconds": format(
            _MAX_EVIDENCE_AGE_SECONDS,
            "f",
        ),
        "thin_spread_to_range": format(_THIN_SPREAD_TO_RANGE, "f"),
        "stressed_spread_to_range": format(
            _STRESSED_SPREAD_TO_RANGE,
            "f",
        ),
        "compressed_vol_ratio": format(_COMPRESSED_VOL_RATIO, "f"),
        "elevated_vol_ratio": format(_ELEVATED_VOL_RATIO, "f"),
        "dislocated_vol_ratio": format(_DISLOCATED_VOL_RATIO, "f"),
        "concentrated_abs_correlation": _CONCENTRATED_ABS_CORRELATION,
        "break_correlation_delta": _BREAK_CORRELATION_DELTA,
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{sha256(raw).hexdigest()}"


def build_phase20_demo_regime_state(
    *,
    decision_at: datetime,
    opportunity_count: int,
    snapshots: tuple[M5BoundarySnapshot, ...],
    provider_specs: tuple[CTraderDemoSymbolSpecification, ...],
    account_state: CTraderDemoAccountState,
    risk_snapshot: AccountRiskSnapshot,
    risk_constraints: RiskCapitalConstraintEnvelope,
    highest_closed_balance: Decimal,
    position_path_adverse: bool = False,
) -> CiboCapitalRegimeState:
    """Build one causal, frozen-rule regime state for a DEMO decision epoch."""

    _aware(decision_at, name="decision_at")
    if (
        not isinstance(opportunity_count, int)
        or isinstance(opportunity_count, bool)
        or opportunity_count < 0
    ):
        raise CiboCapitalManagementError(
            "Phase20D DEMO regime opportunity_count must be non-negative int"
        )
    if (not snapshots or not provider_specs) and opportunity_count > 0:
        raise CiboCapitalManagementError(
            "Phase20D DEMO candidate regime requires market/provider evidence"
        )
    if not isinstance(account_state, CTraderDemoAccountState):
        raise CiboCapitalManagementError(
            "Phase20D DEMO regime requires canonical account state"
        )
    if not isinstance(risk_snapshot, AccountRiskSnapshot):
        raise CiboCapitalManagementError(
            "Phase20D DEMO regime requires canonical Risk snapshot"
        )
    if not isinstance(risk_constraints, RiskCapitalConstraintEnvelope):
        raise CiboCapitalManagementError(
            "Phase20D DEMO regime requires canonical Risk constraints"
        )
    if (
        not isinstance(highest_closed_balance, Decimal)
        or not highest_closed_balance.is_finite()
        or highest_closed_balance <= 0
    ):
        raise CiboCapitalManagementError(
            "Phase20D DEMO regime highest balance must be finite positive"
        )
    if type(position_path_adverse) is not bool:
        raise CiboCapitalManagementError(
            "Phase20D DEMO regime position_path_adverse must be bool"
        )

    if not snapshots or not provider_specs:
        equity = account_state.equity
        risk_used = max(
            Decimal(0),
            risk_constraints.aggregate_pre_order_worst_case_usd,
        )
        margin_total = account_state.margin + account_state.free_margin
        drawdown = max(
            Decimal(0),
            highest_closed_balance - account_state.equity,
        )
        return CiboCapitalRegimeState(
            liquidity=LiquidityState.STRESSED,
            volatility=VolatilityState.DISLOCATED,
            correlation=CorrelationState.BREAK,
            provider_condition=ProviderCondition.UNAVAILABLE,
            risk_utilization=_bounded_ratio(
                risk_used,
                max(equity, Decimal("0.00000001")),
            ),
            margin_utilization=_bounded_ratio(
                account_state.margin,
                margin_total,
            ),
            drawdown_utilization=_bounded_ratio(
                drawdown,
                highest_closed_balance,
            ),
            opportunity_count=0,
            position_path_adverse=position_path_adverse,
            evidence_stale=True,
        )

    snapshot_by_symbol = {item.symbol: item for item in snapshots}
    spec_by_symbol = {
        _qore_symbol(item): item
        for item in provider_specs
    }
    if len(snapshot_by_symbol) != len(snapshots):
        raise CiboCapitalManagementError(
            "Phase20D DEMO regime duplicate market snapshot"
        )
    if len(spec_by_symbol) != len(provider_specs):
        raise CiboCapitalManagementError(
            "Phase20D DEMO regime duplicate provider specification"
        )
    if not set(snapshot_by_symbol).issubset(set(spec_by_symbol)):
        raise CiboCapitalManagementError(
            "Phase20D DEMO regime market snapshot lacks provider specification"
        )

    stale = set(snapshot_by_symbol) != set(spec_by_symbol)
    for market_snapshot in snapshots:
        _aware(
            market_snapshot.observed_at,
            name="market snapshot observed_at",
        )
        if market_snapshot.observed_at > decision_at:
            raise CiboCapitalManagementError(
                "Phase20D DEMO regime market snapshot postdates decision"
            )
        if (
            _age_seconds(decision_at, market_snapshot.observed_at)
            > _MAX_EVIDENCE_AGE_SECONDS
        ):
            stale = True
        if len(market_snapshot.complete_bars) < _REQUIRED_HISTORY:
            stale = True
    for provider_spec in provider_specs:
        _aware(provider_spec.observed_at, name="provider observed_at")
        if provider_spec.observed_at > decision_at:
            raise CiboCapitalManagementError(
                "Phase20D DEMO regime provider evidence postdates decision"
            )
        if (
            _age_seconds(decision_at, provider_spec.observed_at)
            > _MAX_EVIDENCE_AGE_SECONDS
        ):
            stale = True

    liquidity = _liquidity(snapshot_by_symbol, spec_by_symbol)
    volatility = _volatility(tuple(snapshot_by_symbol.values()))
    correlation = _correlation(tuple(snapshot_by_symbol.values()))
    provider = _provider_condition(
        provider_specs=provider_specs,
        decision_at=decision_at,
    )
    if stale and provider is ProviderCondition.HEALTHY:
        provider = ProviderCondition.DEGRADED

    equity = account_state.equity
    risk_used = max(
        Decimal(0),
        risk_constraints.aggregate_pre_order_worst_case_usd,
    )
    risk_utilization = _bounded_ratio(
        risk_used,
        max(equity, Decimal("0.00000001")),
    )
    margin_total = account_state.margin + account_state.free_margin
    margin_utilization = _bounded_ratio(
        account_state.margin,
        margin_total,
    )
    drawdown = max(
        Decimal(0),
        highest_closed_balance - account_state.equity,
    )
    drawdown_utilization = _bounded_ratio(
        drawdown,
        highest_closed_balance,
    )

    if risk_snapshot.reconciled_at > decision_at:
        raise CiboCapitalManagementError(
            "Phase20D DEMO regime Risk snapshot postdates decision"
        )
    if risk_constraints.reconciled_at != risk_snapshot.reconciled_at:
        raise CiboCapitalManagementError(
            "Phase20D DEMO regime Risk reconciliation mismatch"
        )
    if provider is ProviderCondition.UNAVAILABLE:
        stale = True

    return CiboCapitalRegimeState(
        liquidity=liquidity,
        volatility=volatility,
        correlation=correlation,
        provider_condition=provider,
        risk_utilization=risk_utilization,
        margin_utilization=margin_utilization,
        drawdown_utilization=drawdown_utilization,
        opportunity_count=opportunity_count,
        position_path_adverse=position_path_adverse,
        evidence_stale=stale,
    )


def _liquidity(
    snapshots: dict[str, M5BoundarySnapshot],
    specs: dict[str, CTraderDemoSymbolSpecification],
) -> LiquidityState:
    worst = Decimal(0)
    for symbol, snapshot in snapshots.items():
        bars = snapshot.complete_bars[-_RECENT_VOL_BARS:]
        ranges = tuple(
            item.high - item.low
            for item in bars
            if item.high > item.low
        )
        if not ranges:
            return LiquidityState.STRESSED
        reference_range = median(ranges)
        if reference_range <= 0:
            return LiquidityState.STRESSED
        spec = specs[symbol]
        spread = spec.ask - spec.bid
        worst = max(worst, spread / reference_range)
    if worst >= _STRESSED_SPREAD_TO_RANGE:
        return LiquidityState.STRESSED
    if worst >= _THIN_SPREAD_TO_RANGE:
        return LiquidityState.THIN
    return LiquidityState.NORMAL


def _volatility(
    snapshots: tuple[M5BoundarySnapshot, ...],
) -> VolatilityState:
    ratios: list[Decimal] = []
    for snapshot in snapshots:
        bars = snapshot.complete_bars[-(_RECENT_VOL_BARS + _BASE_VOL_BARS):]
        if len(bars) < _RECENT_VOL_BARS + _BASE_VOL_BARS:
            return VolatilityState.DISLOCATED
        recent = bars[-_RECENT_VOL_BARS:]
        baseline = bars[:-_RECENT_VOL_BARS]
        recent_range = median(
            tuple(item.high - item.low for item in recent)
        )
        baseline_range = median(
            tuple(item.high - item.low for item in baseline)
        )
        if baseline_range <= 0:
            return VolatilityState.DISLOCATED
        ratios.append(recent_range / baseline_range)
    worst = max(ratios)
    typical = median(ratios)
    if worst >= _DISLOCATED_VOL_RATIO:
        return VolatilityState.DISLOCATED
    if worst >= _ELEVATED_VOL_RATIO:
        return VolatilityState.ELEVATED
    if typical <= _COMPRESSED_VOL_RATIO:
        return VolatilityState.COMPRESSED
    return VolatilityState.NORMAL


def _correlation(
    snapshots: tuple[M5BoundarySnapshot, ...],
) -> CorrelationState:
    series = {
        item.symbol: _returns(item, count=_CORRELATION_WINDOW * 2)
        for item in snapshots
    }
    recent_values: list[float] = []
    prior_values: list[float] = []
    symbols = sorted(series)
    for left_index, left in enumerate(symbols):
        for right in symbols[left_index + 1 :]:
            left_values = series[left]
            right_values = series[right]
            if (
                len(left_values) < _CORRELATION_WINDOW * 2
                or len(right_values) < _CORRELATION_WINDOW * 2
            ):
                return CorrelationState.BREAK
            recent_values.append(
                abs(
                    _pearson(
                        left_values[-_CORRELATION_WINDOW:],
                        right_values[-_CORRELATION_WINDOW:],
                    )
                )
            )
            prior_values.append(
                abs(
                    _pearson(
                        left_values[-2 * _CORRELATION_WINDOW:-_CORRELATION_WINDOW],
                        right_values[-2 * _CORRELATION_WINDOW:-_CORRELATION_WINDOW],
                    )
                )
            )
    if not recent_values:
        return CorrelationState.NORMAL
    delta = max(
        abs(recent - prior)
        for recent, prior in zip(recent_values, prior_values, strict=True)
    )
    if delta >= _BREAK_CORRELATION_DELTA:
        return CorrelationState.BREAK
    if max(recent_values) >= _CONCENTRATED_ABS_CORRELATION:
        return CorrelationState.CONCENTRATED
    return CorrelationState.NORMAL


def _provider_condition(
    *,
    provider_specs: tuple[CTraderDemoSymbolSpecification, ...],
    decision_at: datetime,
) -> ProviderCondition:
    fresh = tuple(
        _age_seconds(decision_at, item.observed_at)
        <= _MAX_EVIDENCE_AGE_SECONDS
        for item in provider_specs
    )
    if not any(fresh):
        return ProviderCondition.UNAVAILABLE
    if not all(fresh) or any(not item.trade_enabled for item in provider_specs):
        return ProviderCondition.DEGRADED
    return ProviderCondition.HEALTHY


def _returns(
    snapshot: M5BoundarySnapshot,
    *,
    count: int,
) -> tuple[float, ...]:
    closes = tuple(item.close for item in snapshot.complete_bars[-(count + 1):])
    if len(closes) < count + 1:
        return ()
    values: list[float] = []
    for prior, current in zip(closes[:-1], closes[1:], strict=True):
        if prior <= 0:
            return ()
        values.append(float((current / prior) - Decimal(1)))
    return tuple(values)


def _pearson(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 0.0
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    left_dev = tuple(item - left_mean for item in left)
    right_dev = tuple(item - right_mean for item in right)
    numerator = sum(
        x * y for x, y in zip(left_dev, right_dev, strict=True)
    )
    left_norm = math.sqrt(sum(item * item for item in left_dev))
    right_norm = math.sqrt(sum(item * item for item in right_dev))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _qore_symbol(spec: CTraderDemoSymbolSpecification) -> str:
    return "NAS100" if spec.provider_symbol == "NDX100" else spec.provider_symbol


def _age_seconds(later: datetime, earlier: datetime) -> Decimal:
    delta = later - earlier
    if delta.total_seconds() < 0:
        raise CiboCapitalManagementError(
            "Phase20D DEMO regime evidence timestamp from future"
        )
    return Decimal(str(delta.total_seconds()))


def _bounded_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= 0:
        return Decimal(1)
    return min(
        Decimal(1),
        max(Decimal(0), numerator / denominator),
    )


def _aware(value: datetime, *, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"Phase20D DEMO regime {name} must be timezone-aware"
        )
