"""Source-bound historical regime adapter for Phase22 V4.

The adapter reuses the frozen Phase20 DEMO market-regime classifier for the
historical market dimensions. It never relabels the current cTrader DEMO
provider model as historical provider state.

Market dimensions:
- liquidity: historical closed M5 ranges + frozen current provider spread,
  explicitly counterfactual;
- volatility: historical closed M5 only;
- correlation: historical closed M5 only.

Exactly the five-market M5 surface used by the canonical Phase20 DEMO runtime
is retained. Missing causal history fails closed rather than being backfilled.
"""
# ruff: noqa: I001, E402

from __future__ import annotations

import hashlib
import json
from bisect import bisect_right
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_demo_regime import (
    PHASE20_DEMO_REGIME_POLICY_ID,
    _correlation,
    _liquidity,
    _volatility,
    phase20_demo_regime_policy_sha256,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_phase22_v4_chronological_execution import (
    Phase22HistoricalRegimeEvidence,
)
from qore.infrastructure.cibo_phase22_v4_chronological_replay_plan import (
    Phase22ChronologicalReplayPlan,
)
from qore.infrastructure.cibo_phase22_v4_execution_inputs import (
    Phase22SealedProviderNumericInput,
)
from qore.infrastructure.cibo_phase22_v4_source_receipt import (
    load_phase22_v4_source_receipt,
)

V4_SOURCE_RECEIPT = load_phase22_v4_source_receipt(
    Path("docs/research/CIBO-PHASE22-V4-SOURCE-RECEIPT.json")
)
V4_SOURCE_BINDINGS = V4_SOURCE_RECEIPT.bindings
from qore.infrastructure.ctrader_demo_compat import (
    CTraderDemoSymbolSpecification,
)
from qore.infrastructure.m5_boundary_cache import M5BoundarySnapshot
from qore.infrastructure.trader_lab.cibo_market_atlas_journey_extractor_v1 import (
    load_raw_m5,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
)

PHASE22_HISTORICAL_REGIME_ADAPTER_ID = (
    "CIBO_PHASE22_V4_HISTORICAL_REGIME_PHASE20_POLICY_ADAPTER_V1"
)
PHASE22_REGIME_SYMBOLS = (
    "AUDJPY",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "XAUUSD",
)
_REQUIRED_HISTORY = 72


def load_phase22_historical_regime_corpora(
    source_roots: Mapping[str, Path],
) -> tuple[Evidence, ...]:
    """Load the exact five immutable M5 corpora used for regime replay."""

    if set(source_roots) != set(PHASE22_REGIME_SYMBOLS):
        raise CiboCapitalManagementError(
            "Phase22 historical regime source-root surface drift"
        )
    corpora = []
    for symbol in PHASE22_REGIME_SYMBOLS:
        root = source_roots[symbol]
        if not isinstance(root, Path):
            raise CiboCapitalManagementError(
                "Phase22 historical regime source root must be pathlib.Path"
            )
        evidence, _provenance = load_raw_m5(root)
        if evidence.symbol != symbol:
            raise CiboCapitalManagementError(
                f"Phase22 historical regime corpus symbol drift: {symbol}"
            )
        corpora.append(evidence)
    return tuple(corpora)


def build_phase22_historical_regime_evidence(
    *,
    plan: Phase22ChronologicalReplayPlan,
    provider: Phase22SealedProviderNumericInput,
    provider_numeric_freeze_sha256: str,
    corpora: tuple[Evidence, ...],
) -> tuple[Phase22HistoricalRegimeEvidence, ...]:
    """Build one causal regime receipt per historical decision epoch."""

    if not isinstance(plan, Phase22ChronologicalReplayPlan):
        raise CiboCapitalManagementError(
            "Phase22 historical regime requires chronological replay plan"
        )
    if not isinstance(provider, Phase22SealedProviderNumericInput):
        raise CiboCapitalManagementError(
            "Phase22 historical regime requires sealed provider model"
        )
    _require_sha256(
        provider_numeric_freeze_sha256,
        "provider_numeric_freeze_sha256",
    )
    by_symbol = {item.symbol: item for item in corpora}
    if (
        len(by_symbol) != len(corpora)
        or set(by_symbol) != set(PHASE22_REGIME_SYMBOLS)
    ):
        raise CiboCapitalManagementError(
            "Phase22 historical regime corpus surface drift"
        )

    policy_sha = phase20_demo_regime_policy_sha256()
    source_receipt_sha = V4_SOURCE_RECEIPT.fingerprint()
    source_ids = _source_evidence_ids(
        policy_sha=policy_sha,
        source_receipt_sha=source_receipt_sha,
        provider_numeric_freeze_sha256=provider_numeric_freeze_sha256,
    )
    bars_by_symbol = {
        symbol: by_symbol[symbol].bars
        for symbol in PHASE22_REGIME_SYMBOLS
    }
    closed_at_by_symbol = {
        symbol: tuple(bar.closed_at for bar in bars_by_symbol[symbol])
        for symbol in PHASE22_REGIME_SYMBOLS
    }

    result = []
    for epoch in plan.epochs:
        history_counts = {
            symbol: bisect_right(
                closed_at_by_symbol[symbol],
                epoch.market_decision_at,
            )
            for symbol in PHASE22_REGIME_SYMBOLS
        }
        history_tails = {
            symbol: bars_by_symbol[symbol][
                max(0, history_counts[symbol] - _REQUIRED_HISTORY):
                history_counts[symbol]
            ]
            for symbol in PHASE22_REGIME_SYMBOLS
        }
        sufficient = all(
            history_counts[symbol] >= _REQUIRED_HISTORY
            for symbol in PHASE22_REGIME_SYMBOLS
        )
        if sufficient:
            snapshots = tuple(
                _snapshot(
                    corpus=by_symbol[symbol],
                    bars=history_tails[symbol],
                    decision_at=epoch.market_decision_at,
                )
                for symbol in PHASE22_REGIME_SYMBOLS
            )
            specs = tuple(
                _counterfactual_spec(provider.spec_for(symbol))
                for symbol in PHASE22_REGIME_SYMBOLS
            )
            snapshot_map = {item.symbol: item for item in snapshots}
            spec_map = {
                item.provider_symbol: item
                for item in specs
            }
            liquidity = _liquidity(snapshot_map, spec_map)
            volatility = _volatility(snapshots)
            correlation = _correlation(snapshots)
            provider_condition = ProviderCondition.HEALTHY
            stale = False
        else:
            liquidity = LiquidityState.STRESSED
            volatility = VolatilityState.DISLOCATED
            correlation = CorrelationState.BREAK
            provider_condition = ProviderCondition.DEGRADED
            stale = True

        evidence_sha = _epoch_evidence_sha(
            decision_epoch_id=epoch.decision_epoch_id,
            market_decision_at=epoch.market_decision_at,
            history_counts=history_counts,
            history_tails=history_tails,
            policy_sha=policy_sha,
            source_receipt_sha=source_receipt_sha,
            provider_numeric_freeze_sha256=provider_numeric_freeze_sha256,
            liquidity=liquidity,
            volatility=volatility,
            correlation=correlation,
            provider_condition=provider_condition,
            market_history_sufficient=sufficient,
        )
        result.append(
            Phase22HistoricalRegimeEvidence(
                decision_epoch_id=epoch.decision_epoch_id,
                observed_at=epoch.market_decision_at,
                liquidity=liquidity,
                volatility=volatility,
                correlation=correlation,
                provider_condition=provider_condition,
                concentration_limit_by_group=(),
                evidence_sha256=evidence_sha,
                source_evidence_ids=source_ids,
                regime_policy_sha256=policy_sha,
                provider_numeric_freeze_sha256=(
                    provider_numeric_freeze_sha256
                ),
                market_history_sufficient=sufficient,
                counterfactual_provider_model=True,
                historical_provider_state_claimed=False,
                position_path_adverse=False,
                evidence_stale=stale,
                outcome_fields_used=False,
                target_aware=False,
                productive_authority=False,
            )
        )
    return tuple(result)


def _snapshot(
    *,
    corpus: Evidence,
    bars: tuple[Bar, ...],
    decision_at: datetime,
) -> M5BoundarySnapshot:
    if not bars:
        raise CiboCapitalManagementError(
            "Phase22 historical regime cannot construct empty market snapshot"
        )
    causal = tuple(bars[-_REQUIRED_HISTORY:])
    evidence = Evidence(
        symbol=corpus.symbol,
        digits=corpus.digits,
        bars=causal,
    )
    return M5BoundarySnapshot(
        symbol=corpus.symbol,
        anchor=decision_at,
        evidence=evidence,
        current_open=causal[-1].close,
        broker_tick_at=decision_at,
        observed_at=decision_at,
        new_bar_first_seen_at=decision_at,
        market_state_updated_at=decision_at,
        aggregate_finished_at=decision_at,
        complete_bars=causal,
        h1=(),
        h4=(),
        d1=(),
    )


def _counterfactual_spec(spec: object) -> CTraderDemoSymbolSpecification:
    from qore.infrastructure.cibo_phase22_provider_numeric_execution import (
        Phase22ProviderNumericExecutionSpec,
    )

    if not isinstance(spec, Phase22ProviderNumericExecutionSpec):
        raise CiboCapitalManagementError(
            "Phase22 historical regime provider spec invalid"
        )
    spread = spec.ask - spec.bid
    return CTraderDemoSymbolSpecification(
        provider_symbol=spec.qore_symbol,
        bid=spec.bid,
        ask=spec.ask,
        spread_points=spread / spec.derived_price_quantum,
        digits=spec.display_digits,
        point=spec.derived_price_quantum,
        contract_size=spec.contract_size_per_volume,
        tick_size=spec.derived_price_quantum,
        tick_value=spec.derived_value_per_quantum_usd,
        minimum_volume=spec.minimum_volume,
        maximum_volume=spec.maximum_volume,
        volume_step=spec.volume_step,
        minimum_stop_distance_points=Decimal(0),
        freeze_level_points=Decimal(0),
        margin_per_volume=spec.margin_per_volume_usd,
        trade_enabled=True,
        session_open=True,
        observed_at=spec.observed_at,
        open_commission_per_lot_usd=spec.commission_per_volume_usd,
    )


def _source_evidence_ids(
    *,
    policy_sha: str,
    source_receipt_sha: str,
    provider_numeric_freeze_sha256: str,
) -> tuple[str, ...]:
    bindings = tuple(
        item
        for item in V4_SOURCE_BINDINGS
        if item.timeframe == "M5" and item.symbol in PHASE22_REGIME_SYMBOLS
    )
    if tuple(item.symbol for item in bindings) != PHASE22_REGIME_SYMBOLS:
        by_symbol = {item.symbol: item for item in bindings}
        if set(by_symbol) != set(PHASE22_REGIME_SYMBOLS):
            raise CiboCapitalManagementError(
                "Phase22 historical regime source binding drift"
            )
        bindings = tuple(by_symbol[symbol] for symbol in PHASE22_REGIME_SYMBOLS)
    values = (
        policy_sha,
        source_receipt_sha,
        provider_numeric_freeze_sha256,
        *(item.artifact_digest for item in bindings),
    )
    if len(values) != len(set(values)):
        raise CiboCapitalManagementError(
            "Phase22 historical regime source evidence duplicated"
        )
    return values


def _epoch_evidence_sha(
    *,
    decision_epoch_id: str,
    market_decision_at: datetime,
    history_counts: dict[str, int],
    history_tails: dict[str, tuple[Bar, ...]],
    policy_sha: str,
    source_receipt_sha: str,
    provider_numeric_freeze_sha256: str,
    liquidity: LiquidityState,
    volatility: VolatilityState,
    correlation: CorrelationState,
    provider_condition: ProviderCondition,
    market_history_sufficient: bool,
) -> str:
    payload: dict[str, Any] = {
        "adapter_id": PHASE22_HISTORICAL_REGIME_ADAPTER_ID,
        "phase20_regime_policy_id": PHASE20_DEMO_REGIME_POLICY_ID,
        "phase20_regime_policy_sha256": policy_sha,
        "phase22_source_receipt_sha256": source_receipt_sha,
        "provider_numeric_freeze_sha256": provider_numeric_freeze_sha256,
        "decision_epoch_id": decision_epoch_id,
        "market_decision_at": market_decision_at.isoformat(),
        "market_history_sufficient": market_history_sufficient,
        "liquidity": liquidity.value,
        "volatility": volatility.value,
        "correlation": correlation.value,
        "provider_condition": provider_condition.value,
        "provider_condition_semantics": (
            "CURRENT_EMPIRICAL_COUNTERFACTUAL_MODEL_READY_"
            "NOT_HISTORICAL_PROVIDER_STATE"
        ),
        "counterfactual_provider_model": True,
        "historical_provider_state_claimed": False,
        "outcome_fields_used": False,
        "concentration_limit_by_group": [],
        "history": {
            symbol: {
                "bar_count_before_decision": history_counts[symbol],
                "causal_tail_sha256": _bars_sha(
                    history_tails[symbol]
                ),
            }
            for symbol in PHASE22_REGIME_SYMBOLS
        },
    }
    return _payload_sha(payload)


def _bars_sha(bars: tuple[Bar, ...]) -> str:
    payload = [
        {
            "opened_at": item.opened_at.isoformat(),
            "closed_at": item.closed_at.isoformat(),
            "open": format(item.open, "f"),
            "high": format(item.high, "f"),
            "low": format(item.low, "f"),
            "close": format(item.close, "f"),
        }
        for item in bars
    ]
    return _payload_sha({"bars": payload})


def _payload_sha(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _require_sha256(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"Phase22 historical regime {name} invalid"
        )
