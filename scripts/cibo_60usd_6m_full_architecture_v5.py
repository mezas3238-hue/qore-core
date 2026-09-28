"""CIBO USD60 six-month integrated full-architecture capability replay V5.

This is an isolated research measurement, not PR #651 certification evidence.

Contract:
- every retained valid opportunity from all seven Traders is forwarded to CIBO;
- every opportunity receives canonical T01 minimal-seed sizing when account
  capacity can express the minimum;
- no expectation/rank/identity filter may block the Trader's base entry;
- advanced CE2I allocation may add exposure only after the USD60 survival base
  is protected by realized closed PnL;
- frozen Phase20 TRAIN expectations are never consumed before their 2022-03-09
  cutoff;
- extra capital uses the current CIBO contracts for regime selection,
  optionality/drawdown reserve, opportunity competition, execution-efficient
  sizing, profit-funded expansion, reservation, release and recycling;
- T07 protected-open-floor expansion and T14 dynamic de-risking are not allowed
  to alter historical PnL because the sealed seven-Trader rows do not retain
  broker-confirmed historical stop mutations/retained-risk ceilings. They remain
  covered by the V4 functional probe.

Historical provider economics are incomplete across the sealed Phase18 rows.
Therefore one normalized volume unit equals USD1 structural stop risk and exact
broker-executable USD PnL is NOT claimed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CapitalSource,
    CiboCapitalState,
    TraderOpportunityEnvelope,
    plan_minimal_seed,
    plan_self_financing_expansion,
)
from qore.infrastructure.cibo_capital_source_ledger import (
    CapitalReservationRequest,
    CapitalSourceLedger,
)
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalSourceLedgerStore,
)
from qore.infrastructure.cibo_ce2i_execution_efficiency import (
    ExecutionCostCurveInput,
    cap_expansion_plan_by_execution,
    execution_efficient_volume_cap,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
)
from qore.infrastructure.cibo_ce2i_phase20_robust_allocator import (
    Phase20AllocatorDisposition,
    propose_phase20h_robust_allocation,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    build_frozen_train_expectation,
    frozen_train_prior_for,
)
from qore.infrastructure.cibo_ce2i_recycling import (
    ReleasedCapacityEvidence,
    register_released_capacity,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
    select_ce2i_tools_for_regime,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

getcontext().prec = 50

EXPERIMENT_ID = "CIBO_60USD_6M_FULL_ARCHITECTURE_INTEGRATED_V5"
INITIAL_SEED_USD = Decimal("60")
SURVIVAL_CAPITAL_USD = Decimal("60")
NORMALIZED_STOP_RISK_PER_VOLUME_USD = Decimal("1")
NORMALIZED_MARGIN_PER_VOLUME_USD = Decimal("0.000001")
VOLUME_STEP = Decimal("0.01")
MINIMUM_VOLUME = Decimal("1")
MAXIMUM_VOLUME = Decimal("1000000000")
NORMALIZED_MARGIN_HEADROOM_USD = Decimal("1000000000")
DEFAULT_START = "2022-01-01T00:00:00+00:00"
DEFAULT_END = "2022-07-01T00:00:00+00:00"
ADVANCED_EVIDENCE_CUTOFF = "2022-03-09T17:00:00+00:00"
MILESTONES_USD = (
    Decimal("300"),
    Decimal("1000"),
    Decimal("5000"),
    Decimal("10000"),
)

ECONOMICALLY_INTEGRATED_TOOLS = {
    "T01",
    "T05",
    "T06",
    "T09",
    "T11",
    "T12",
    "T13",
    "T15",
    "T18",
    "T19",
    "T20",
}
FUNCTIONAL_ONLY_TOOLS = {"T07", "T14"}
ARCHITECTURE_ONLY_TOOLS = {"T02", "T03", "T04", "T08", "T10", "T16", "T17"}


@dataclass(frozen=True, slots=True)
class SourceSpec:
    key: str
    trader_id: TraderLineage
    qore_symbol: str | None
    outcome_field: str
    net_stop_r: Decimal


SOURCE_SPECS: tuple[SourceSpec, ...] = (
    SourceSpec(
        "gbpjpy",
        TraderLineage.R38_GBPJPY,
        "GBPJPY",
        "raw_net_010_r",
        Decimal("1.10"),
    ),
    SourceSpec(
        "gbpusd",
        TraderLineage.R43_GBPUSD,
        "GBPUSD",
        "raw_net_010_r",
        Decimal("1.10"),
    ),
    SourceSpec(
        "audjpy",
        TraderLineage.R42_AUDJPY,
        "AUDJPY",
        "raw_net_010_r",
        Decimal("1.10"),
    ),
    SourceSpec(
        "eurusd",
        TraderLineage.R38_EURUSD,
        "EURUSD",
        "raw_net_010_r",
        Decimal("1.10"),
    ),
    SourceSpec(
        "xauusd",
        TraderLineage.R34_XAUUSD,
        "XAUUSD",
        "raw_net_010_r",
        Decimal("1.10"),
    ),
    SourceSpec(
        "vt08",
        TraderLineage.VT08_FOREX,
        None,
        "raw_outcome_r",
        Decimal("1.00"),
    ),
    SourceSpec(
        "vt31",
        TraderLineage.VT31_NAS100,
        "NAS100",
        "legacy_vt31_net_r_per_requested_r",
        Decimal("1.05"),
    ),
)


@dataclass(frozen=True, slots=True)
class Trade:
    trader_id: TraderLineage
    symbol: str
    fingerprint: str
    side: str
    signal_at: datetime
    entry_at: datetime
    exit_at: datetime
    entry_price: Decimal
    structural_stop: Decimal
    technical_target: Decimal
    outcome_r: Decimal


@dataclass(slots=True)
class OpenAllocation:
    trade: Trade
    base_risk_usd: Decimal
    expansion_risk_usd: Decimal
    total_risk_usd: Decimal
    expansion_reservation_ids: tuple[str, ...]
    expansion_reservation_amounts: tuple[Decimal, ...]
    applied_tools: tuple[str, ...]


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _money(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.000001")), "f")


def _ratio(value: Decimal) -> Decimal:
    return min(Decimal(1), max(Decimal(0), value))


def _days(start: datetime, at: datetime) -> str:
    return format(
        Decimal(str((at - start).total_seconds())) / Decimal("86400"),
        "f",
    )


def _fingerprint(spec: SourceSpec, row: dict[str, Any], index: int) -> str:
    payload = {
        "trader": spec.trader_id.value,
        "symbol": spec.qore_symbol or str(row["symbol"]),
        "signal_at": str(row["signal_at"]),
        "entry_at": str(row["entry_at"]),
        "exit_at": str(row["exit_at"]),
        "source_index": index,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _load(
    path: Path,
    *,
    spec: SourceSpec,
    start: datetime,
    end: datetime,
) -> list[Trade]:
    result: list[Trade] = []
    for index, row in enumerate(_jsonl(path)):
        signal_at = datetime.fromisoformat(str(row["signal_at"]))
        entry_at = datetime.fromisoformat(str(row["entry_at"]))
        exit_at = datetime.fromisoformat(str(row["exit_at"]))
        for value in (signal_at, entry_at, exit_at):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("trade timestamp must be timezone-aware")
        if not signal_at <= entry_at < exit_at:
            raise ValueError(
                f"{spec.trader_id.value} chronology drift at source row {index}"
            )
        if entry_at < start or exit_at > end:
            continue

        side = str(row["side"]).lower()
        entry = Decimal(str(row["entry_price"]))
        stop = Decimal(str(row["structural_stop"]))
        target = Decimal(str(row["technical_target"]))
        valid = (
            side == "long" and stop < entry < target
        ) or (
            side == "short" and target < entry < stop
        )
        if not valid:
            raise ValueError(
                f"{spec.trader_id.value} invalid geometry at source row {index}"
            )
        raw_outcome = Decimal(str(row[spec.outcome_field]))
        outcome = raw_outcome / spec.net_stop_r
        if not outcome.is_finite():
            raise ValueError(
                f"{spec.trader_id.value} non-finite R at source row {index}"
            )
        result.append(
            Trade(
                trader_id=spec.trader_id,
                symbol=spec.qore_symbol or str(row["symbol"]),
                fingerprint=_fingerprint(spec, row, index),
                side=side,
                signal_at=signal_at,
                entry_at=entry_at,
                exit_at=exit_at,
                entry_price=entry,
                structural_stop=stop,
                technical_target=target,
                outcome_r=outcome,
            )
        )
    return result


def _opportunity(trade: Trade) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=trade.trader_id,
        signal_fingerprint=trade.fingerprint,
        qore_symbol=trade.symbol,
        provider_symbol=f"NORMALIZED:{trade.symbol}",
        side=trade.side,
        entry_type="historical_normalized_integrated_v5",
        intended_entry=trade.entry_price,
        stop_loss=trade.structural_stop,
        take_profit=trade.technical_target,
        stop_loss_per_volume=NORMALIZED_STOP_RISK_PER_VOLUME_USD,
        margin_per_volume=NORMALIZED_MARGIN_PER_VOLUME_USD,
        volume_step=VOLUME_STEP,
        minimum_volume=MINIMUM_VOLUME,
        maximum_volume=MAXIMUM_VOLUME,
        minimum_execution_steps=1,
    )


def _capital_state_for_seed(
    *,
    realized_capital: Decimal,
    realized_pnl: Decimal,
    hard_headroom: Decimal,
) -> CiboCapitalState:
    protected = max(Decimal(0), realized_pnl)
    return CiboCapitalState(
        assigned_capital_usd=max(realized_capital, Decimal("0.000001")),
        hard_risk_headroom_usd=hard_headroom,
        margin_headroom_usd=NORMALIZED_MARGIN_HEADROOM_USD,
        base_capital_at_risk_usd=max(
            Decimal(0),
            SURVIVAL_CAPITAL_USD - protected,
        ),
        realized_net_profit_usd=protected,
        protected_open_economic_floor_usd=Decimal(0),
        proven_self_financing_capacity_usd=protected,
        reserved_expansion_risk_usd=Decimal(0),
        cost_reserve_usd=Decimal(0),
    )


def _capital_state_for_expansion(
    *,
    realized_capital: Decimal,
    expansion_headroom: Decimal,
) -> CiboCapitalState:
    return CiboCapitalState(
        assigned_capital_usd=max(realized_capital, Decimal("0.000001")),
        hard_risk_headroom_usd=expansion_headroom,
        margin_headroom_usd=NORMALIZED_MARGIN_HEADROOM_USD,
        base_capital_at_risk_usd=Decimal(0),
        realized_net_profit_usd=expansion_headroom,
        protected_open_economic_floor_usd=Decimal(0),
        proven_self_financing_capacity_usd=expansion_headroom,
        reserved_expansion_risk_usd=Decimal(0),
        cost_reserve_usd=Decimal(0),
    )


def _regime_state(
    *,
    realized_capital: Decimal,
    peak_capital: Decimal,
    reserved_total_risk: Decimal,
    opportunity_count: int,
) -> CiboCapitalRegimeState:
    # Historical provider spread/commission/margin snapshots are absent from the
    # sealed population. V5 therefore uses market-neutral normalized provider
    # fields and lets the canonical regime selector react to observed account
    # risk, drawdown and opportunity density only.
    risk_utilization = _ratio(
        reserved_total_risk / max(realized_capital, Decimal("0.000001"))
    )
    drawdown = max(Decimal(0), peak_capital - realized_capital)
    drawdown_utilization = _ratio(
        drawdown / max(peak_capital, Decimal("0.000001"))
    )
    return CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=risk_utilization,
        margin_utilization=Decimal(0),
        drawdown_utilization=drawdown_utilization,
        opportunity_count=opportunity_count,
        position_path_adverse=False,
        evidence_stale=False,
    )


def _store_ledger(
    store: DurableCapitalSourceLedgerStore,
    ledger: CapitalSourceLedger,
) -> None:
    current = store.load()
    store.store(ledger, expected_generation=current.generation)


def _add_realized_profit_source(
    *,
    store: DurableCapitalSourceLedgerStore,
    source_id: str,
    amount: Decimal,
) -> None:
    if amount <= 0:
        return
    current = store.load()
    next_ledger = current.ledger.add_source(
        source_id=source_id,
        source=CapitalSource.REALIZED_PROFIT,
        proven_amount_usd=amount,
    )
    store.store(next_ledger, expected_generation=current.generation)


def _reserve_profit_capacity(
    *,
    store: DurableCapitalSourceLedgerStore,
    reservation_prefix: str,
    amount: Decimal,
) -> tuple[tuple[str, ...], tuple[Decimal, ...]]:
    if amount <= 0:
        return (), ()
    current = store.load()
    remaining = amount
    requests: list[CapitalReservationRequest] = []
    for account in sorted(
        (
            item
            for item in current.ledger.accounts
            if item.source is CapitalSource.REALIZED_PROFIT
            and item.available_usd > 0
        ),
        key=lambda item: item.source_id,
    ):
        take = min(remaining, account.available_usd)
        if take <= 0:
            continue
        reservation_id = f"{reservation_prefix}:{len(requests)}"
        requests.append(
            CapitalReservationRequest(
                reservation_id=reservation_id,
                source_id=account.source_id,
                amount_usd=take,
            )
        )
        remaining -= take
        if remaining <= Decimal("0.0000001"):
            break
    if remaining > Decimal("0.0000001"):
        raise RuntimeError(
            f"realized-profit ledger cannot fund expansion remainder {remaining}"
        )
    reserved = current.ledger.reserve_many(tuple(requests))
    for request in requests:
        reserved = reserved.deploy(request.reservation_id)
    store.store(reserved, expected_generation=current.generation)
    return (
        tuple(item.reservation_id for item in requests),
        tuple(item.amount_usd for item in requests),
    )


def _settle_profit_capacity(
    *,
    store: DurableCapitalSourceLedgerStore,
    reservation_ids: tuple[str, ...],
    reservation_amounts: tuple[Decimal, ...],
    outcome_r: Decimal,
) -> None:
    if not reservation_ids:
        return
    returned_fraction = (
        Decimal(1)
        if outcome_r >= 0
        else max(Decimal(0), min(Decimal(1), Decimal(1) + outcome_r))
    )
    current = store.load()
    ledger = current.ledger
    for reservation_id, amount in zip(
        reservation_ids,
        reservation_amounts,
        strict=True,
    ):
        ledger = ledger.settle_deployment(
            reservation_id,
            returned_capacity_usd=amount * returned_fraction,
        )
    store.store(ledger, expected_generation=current.generation)


def run(
    *,
    source_paths: dict[str, Path],
    output_dir: Path,
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    cutoff = datetime.fromisoformat(ADVANCED_EVIDENCE_CUTOFF)
    if not start < cutoff < end:
        raise ValueError("V5 window must straddle the frozen-prior cutoff")
    if set(source_paths) != {spec.key for spec in SOURCE_SPECS}:
        raise ValueError("seven-Trader source set incomplete")

    trades: list[Trade] = []
    source_counts: dict[str, int] = {}
    for spec in SOURCE_SPECS:
        rows = _load(
            source_paths[spec.key],
            spec=spec,
            start=start,
            end=end,
        )
        if not rows:
            raise ValueError(f"{spec.trader_id.value} has no V5 rows")
        source_counts[spec.trader_id.value] = len(rows)
        trades.extend(rows)

    required = {spec.trader_id for spec in SOURCE_SPECS}
    if {item.trader_id for item in trades} != required:
        raise ValueError("V5 requires all seven Trader lineages")

    by_id = {item.fingerprint: item for item in trades}
    if len(by_id) != len(trades):
        raise ValueError("V5 fingerprint collision")

    mission = derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key="qore-sandbox",
            account_ref="cibo-60usd-6m-v5",
            environment=MarketRuntimeEnvironment.SANDBOX,
        )
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    profit_store = DurableCapitalSourceLedgerStore(
        output_dir / "v5-profit-capital-ledger.json"
    )
    recycle_store = DurableCapitalSourceLedgerStore(
        output_dir / "v5-released-risk-ledger.json"
    )

    entry_by_at: dict[datetime, list[Trade]] = defaultdict(list)
    exit_by_at: dict[datetime, list[Trade]] = defaultdict(list)
    for trade in trades:
        entry_by_at[trade.entry_at].append(trade)
        exit_by_at[trade.exit_at].append(trade)
    event_times = sorted(set(entry_by_at) | set(exit_by_at))

    stats: dict[str, dict[str, Any]] = {}
    for spec in SOURCE_SPECS:
        stats[spec.trader_id.value] = {
            "opportunities": source_counts[spec.trader_id.value],
            "forwarded": 0,
            "entries": 0,
            "holds": 0,
            "wins": 0,
            "losses": 0,
            "breakeven": 0,
            "gross_profit": Decimal(0),
            "gross_loss": Decimal(0),
            "net": Decimal(0),
            "base_risk": Decimal(0),
            "expansion_risk": Decimal(0),
            "expanded_entries": 0,
        }

    tool_counts: dict[str, int] = {
        code: 0
        for code in (
            ECONOMICALLY_INTEGRATED_TOOLS
            | FUNCTIONAL_ONLY_TOOLS
            | ARCHITECTURE_ONLY_TOOLS
        )
    }
    tool_effective_pnl_entries: dict[str, int] = {
        code: 0 for code in ECONOMICALLY_INTEGRATED_TOOLS
    }

    realized_pnl = Decimal(0)
    realized_capital = INITIAL_SEED_USD
    peak_capital = realized_capital
    minimum_capital = realized_capital
    max_drawdown = Decimal(0)
    reserved_total_risk = Decimal(0)
    reserved_expansion_risk = Decimal(0)
    peak_reserved_risk = Decimal(0)
    open_allocations: dict[str, OpenAllocation] = {}
    ledger_rows: list[dict[str, Any]] = []

    first_base_protected_at: datetime | None = None
    first_advanced_allocation_at: datetime | None = None
    insolvency_at: datetime | None = None
    milestone_hits: dict[Decimal, dict[str, Any]] = {}
    executed_so_far = wins_so_far = losses_so_far = be_so_far = 0
    trading_dates = sorted({item.entry_at.date() for item in trades})

    for at in event_times:
        # Entry before exit at identical timestamps, preserving the existing
        # conservative replay convention.
        batch = sorted(
            entry_by_at.get(at, ()),
            key=lambda item: (item.trader_id.value, item.fingerprint),
        )

        accepted_in_batch: list[Trade] = []
        for trade in batch:
            row = stats[trade.trader_id.value]
            row["forwarded"] += 1
            opportunity = _opportunity(trade)
            hard_headroom = max(
                Decimal(0),
                realized_capital - reserved_total_risk,
            )
            plan = plan_minimal_seed(
                opportunity,
                _capital_state_for_seed(
                    realized_capital=realized_capital,
                    realized_pnl=realized_pnl,
                    hard_headroom=hard_headroom,
                ),
            )
            tool_counts["T01"] += 1
            if plan.action is not CapitalAction.OPEN_MINIMAL_SEED:
                row["holds"] += 1
                ledger_rows.append(
                    {
                        "event": "ENTRY",
                        "at": at.isoformat(),
                        "fingerprint": trade.fingerprint,
                        "trader": trade.trader_id.value,
                        "symbol": trade.symbol,
                        "decision": "CIBO_HOLD",
                        "reason": plan.reason,
                        "base_risk_usd": "0",
                        "expansion_risk_usd": "0",
                        "total_risk_usd": "0",
                        "realized_pnl_before_usd": _money(realized_pnl),
                    }
                )
                continue

            base_risk = plan.stop_risk_usd
            reserved_total_risk += base_risk
            peak_reserved_risk = max(peak_reserved_risk, reserved_total_risk)
            row["entries"] += 1
            row["base_risk"] += base_risk
            executed_so_far += 1
            accepted_in_batch.append(trade)
            open_allocations[trade.fingerprint] = OpenAllocation(
                trade=trade,
                base_risk_usd=base_risk,
                expansion_risk_usd=Decimal(0),
                total_risk_usd=base_risk,
                expansion_reservation_ids=(),
                expansion_reservation_amounts=(),
                applied_tools=("T01",),
            )

        protected_profit = max(Decimal(0), realized_pnl)
        base_protected = protected_profit >= SURVIVAL_CAPITAL_USD
        if base_protected and first_base_protected_at is None:
            first_base_protected_at = at

        # Advanced tooling becomes causal only after the frozen TRAIN evidence
        # cutoff. It can never remove the already accepted minimal seed.
        expansion_headroom = max(
            Decimal(0),
            protected_profit - reserved_total_risk,
        )
        if (
            accepted_in_batch
            and base_protected
            and at >= cutoff
            and expansion_headroom >= MINIMUM_VOLUME
        ):
            regime_state = _regime_state(
                realized_capital=realized_capital,
                peak_capital=peak_capital,
                reserved_total_risk=reserved_total_risk,
                opportunity_count=len(accepted_in_batch),
            )
            regime = select_ce2i_tools_for_regime(
                mission=mission,
                state=regime_state,
            )
            tool_counts["T12"] += 1

            candidates: list[CapitalOpportunityCandidate] = []
            for trade in accepted_in_batch:
                spec = next(
                    item
                    for item in SOURCE_SPECS
                    if item.trader_id is trade.trader_id
                )
                expectation = build_frozen_train_expectation(
                    trader_id=trade.trader_id,
                    stop_risk_usd=(
                        expansion_headroom / spec.net_stop_r
                    ),
                    as_of=at,
                )
                candidates.append(
                    CapitalOpportunityCandidate(
                        signal_fingerprint=trade.fingerprint,
                        trader_id=trade.trader_id,
                        qore_symbol=trade.symbol,
                        provider_symbol=f"NORMALIZED:{trade.symbol}",
                        decision_as_of=at,
                        expectation=expectation,
                        stop_risk_usd=expansion_headroom,
                        margin_usd=(
                            expansion_headroom
                            * NORMALIZED_MARGIN_PER_VOLUME_USD
                        ),
                        concentration_group=trade.symbol,
                        concentration_risk_usd=expansion_headroom,
                    )
                )

            concentration = tuple(
                (symbol, expansion_headroom)
                for symbol in sorted({item.symbol for item in accepted_in_batch})
            )
            allocation = propose_phase20h_robust_allocation(
                mission=mission,
                regime=regime,
                hard_risk_headroom_usd=expansion_headroom,
                margin_headroom_usd=NORMALIZED_MARGIN_HEADROOM_USD,
                concentration_limit_by_group=concentration,
                candidates=tuple(candidates),
                known_options=(),
            )
            for code in allocation.applied_tools:
                tool_counts[code] += 1

            if (
                allocation.disposition is Phase20AllocatorDisposition.ALLOCATE
                and allocation.allocation is not None
                and allocation.allocation.selected_signal_fingerprints
            ):
                selected_id = allocation.allocation.selected_signal_fingerprints[0]
                trade = by_id[selected_id]
                prior = frozen_train_prior_for(trade.trader_id)
                if prior.expected_structural_r > 0:
                    opportunity = _opportunity(trade)
                    expansion_plan = plan_self_financing_expansion(
                        opportunity,
                        _capital_state_for_expansion(
                            realized_capital=realized_capital,
                            expansion_headroom=expansion_headroom,
                        ),
                    )
                    if expansion_plan.action is CapitalAction.EXPAND:
                        spec = next(
                            item
                            for item in SOURCE_SPECS
                            if item.trader_id is trade.trader_id
                        )
                        curve = ExecutionCostCurveInput(
                            evidence_id=(
                                "V5_NORMALIZED_ZERO_COST:"
                                f"{trade.trader_id.value}:{trade.fingerprint}"
                            ),
                            volume_step=opportunity.volume_step,
                            maximum_volume=expansion_plan.volume,
                            gross_edge_per_volume_usd=(
                                prior.expected_structural_r
                                / spec.net_stop_r
                            ),
                            spread_cost_per_volume_usd=Decimal(0),
                            commission_cost_per_volume_usd=Decimal(0),
                            slippage_cost_per_volume_usd=Decimal(0),
                            impact_cost_per_volume_squared_usd=Decimal(0),
                        )
                        cap = execution_efficient_volume_cap(curve)
                        tool_counts["T11"] += 1
                        expansion_plan = cap_expansion_plan_by_execution(
                            plan=expansion_plan,
                            opportunity=opportunity,
                            cap=cap,
                        )
                        if expansion_plan.action is CapitalAction.EXPAND:
                            risk = expansion_plan.stop_risk_usd
                            reservation_ids, reservation_amounts = (
                                _reserve_profit_capacity(
                                    store=profit_store,
                                    reservation_prefix=(
                                        f"v5-exp:{trade.fingerprint}"
                                    ),
                                    amount=risk,
                                )
                            )
                            tool_counts["T19"] += 1
                            tool_counts["T06"] += 1
                            allocation_row = open_allocations[trade.fingerprint]
                            allocation_row.expansion_risk_usd = risk
                            allocation_row.total_risk_usd += risk
                            allocation_row.expansion_reservation_ids = (
                                reservation_ids
                            )
                            allocation_row.expansion_reservation_amounts = (
                                reservation_amounts
                            )
                            allocation_row.applied_tools = tuple(
                                dict.fromkeys(
                                    allocation_row.applied_tools
                                    + allocation.applied_tools
                                    + ("T11", "T06", "T19")
                                )
                            )
                            reserved_total_risk += risk
                            reserved_expansion_risk += risk
                            peak_reserved_risk = max(
                                peak_reserved_risk,
                                reserved_total_risk,
                            )
                            trader_stats = stats[trade.trader_id.value]
                            trader_stats["expansion_risk"] += risk
                            trader_stats["expanded_entries"] += 1
                            if first_advanced_allocation_at is None:
                                first_advanced_allocation_at = at

        for trade in batch:
            allocation = open_allocations.get(trade.fingerprint)
            if allocation is None:
                continue
            ledger_rows.append(
                {
                    "event": "ENTRY",
                    "at": at.isoformat(),
                    "fingerprint": trade.fingerprint,
                    "trader": trade.trader_id.value,
                    "symbol": trade.symbol,
                    "decision": "EXECUTE",
                    "applied_tools": list(allocation.applied_tools),
                    "base_protected": base_protected,
                    "advanced_evidence_available": at >= cutoff,
                    "base_risk_usd": _money(allocation.base_risk_usd),
                    "expansion_risk_usd": _money(
                        allocation.expansion_risk_usd
                    ),
                    "total_risk_usd": _money(allocation.total_risk_usd),
                    "realized_pnl_before_usd": _money(realized_pnl),
                    "capital_before_usd": _money(realized_capital),
                }
            )

        for trade in sorted(
            exit_by_at.get(at, ()),
            key=lambda item: (item.trader_id.value, item.fingerprint),
        ):
            allocation = open_allocations.pop(trade.fingerprint, None)
            if allocation is None:
                continue
            delta = allocation.total_risk_usd * trade.outcome_r

            reserved_total_risk -= allocation.total_risk_usd
            reserved_expansion_risk -= allocation.expansion_risk_usd
            if reserved_total_risk < 0 or reserved_expansion_risk < 0:
                raise RuntimeError("V5 reserved risk accounting became negative")

            if allocation.expansion_reservation_ids:
                _settle_profit_capacity(
                    store=profit_store,
                    reservation_ids=allocation.expansion_reservation_ids,
                    reservation_amounts=allocation.expansion_reservation_amounts,
                    outcome_r=trade.outcome_r,
                )
                tool_counts["T20"] += 1

            # T05 receives authoritative release evidence from every settled
            # position. It remains a risk-headroom dimension and never creates
            # economic profit capital.
            register_released_capacity(
                ReleasedCapacityEvidence(
                    evidence_id=f"v5-exit:{trade.fingerprint}",
                    source=CapitalSource.RELEASED_RISK_CAPACITY,
                    amount_usd=allocation.total_risk_usd,
                    reconciled_at=at,
                    upstream_reference=trade.fingerprint,
                ),
                ledger_store=recycle_store,
            )
            tool_counts["T05"] += 1

            realized_pnl += delta
            realized_capital = INITIAL_SEED_USD + realized_pnl
            peak_capital = max(peak_capital, realized_capital)
            minimum_capital = min(minimum_capital, realized_capital)
            max_drawdown = max(
                max_drawdown,
                peak_capital - realized_capital,
            )
            if realized_capital <= 0 and insolvency_at is None:
                insolvency_at = at

            if delta > 0:
                _add_realized_profit_source(
                    store=profit_store,
                    source_id=f"profit:{trade.fingerprint}",
                    amount=delta,
                )

            row = stats[trade.trader_id.value]
            row["net"] += delta
            if delta > 0:
                row["wins"] += 1
                row["gross_profit"] += delta
                wins_so_far += 1
            elif delta < 0:
                row["losses"] += 1
                row["gross_loss"] += delta
                losses_so_far += 1
            else:
                row["breakeven"] += 1
                be_so_far += 1

            for code in allocation.applied_tools:
                if code in tool_effective_pnl_entries:
                    tool_effective_pnl_entries[code] += 1

            for milestone in MILESTONES_USD:
                if milestone not in milestone_hits and realized_pnl >= milestone:
                    milestone_hits[milestone] = {
                        "at": at,
                        "executed_entries": executed_so_far,
                        "wins": wins_so_far,
                        "losses": losses_so_far,
                        "breakeven": be_so_far,
                    }

            ledger_rows.append(
                {
                    "event": "EXIT",
                    "at": at.isoformat(),
                    "fingerprint": trade.fingerprint,
                    "trader": trade.trader_id.value,
                    "symbol": trade.symbol,
                    "outcome_r": str(trade.outcome_r),
                    "total_risk_usd": _money(allocation.total_risk_usd),
                    "realized_trade_pnl_usd": _money(delta),
                    "cumulative_realized_pnl_usd": _money(realized_pnl),
                    "capital_after_usd": _money(realized_capital),
                }
            )

    if open_allocations or reserved_total_risk != 0 or reserved_expansion_risk != 0:
        raise RuntimeError("V5 ended with unsettled allocations")

    total_forwarded = sum(item["forwarded"] for item in stats.values())
    total_entries = sum(item["entries"] for item in stats.values())
    total_holds = sum(item["holds"] for item in stats.values())
    total_wins = sum(item["wins"] for item in stats.values())
    total_losses = sum(item["losses"] for item in stats.values())
    total_be = sum(item["breakeven"] for item in stats.values())
    reconciled_pnl = sum((item["net"] for item in stats.values()), Decimal(0))
    if total_forwarded != len(trades):
        raise RuntimeError("not every V5 opportunity reached CIBO")
    if total_entries + total_holds != len(trades):
        raise RuntimeError("V5 opportunity disposition drift")
    if total_entries != total_wins + total_losses + total_be:
        raise RuntimeError("V5 outcome count drift")
    if reconciled_pnl != realized_pnl:
        raise RuntimeError("V5 per-Trader PnL drift")

    per_trader: dict[str, dict[str, Any]] = {}
    for name, row in sorted(stats.items()):
        pf = (
            None
            if row["gross_loss"] == 0
            else row["gross_profit"] / abs(row["gross_loss"])
        )
        per_trader[name] = {
            "opportunities": row["opportunities"],
            "opportunities_forwarded_to_cibo": row["forwarded"],
            "executed_entries": row["entries"],
            "cibo_holds_no_capacity": row["holds"],
            "wins": row["wins"],
            "losses": row["losses"],
            "breakeven": row["breakeven"],
            "gross_profit_usd": _money(row["gross_profit"]),
            "gross_loss_usd": _money(row["gross_loss"]),
            "net_pnl_usd": _money(row["net"]),
            "profit_factor": None if pf is None else str(pf),
            "base_risk_assigned_usd": _money(row["base_risk"]),
            "expansion_risk_assigned_usd": _money(row["expansion_risk"]),
            "expanded_entries": row["expanded_entries"],
        }

    milestones: dict[str, Any] = {}
    for milestone in MILESTONES_USD:
        hit = milestone_hits.get(milestone)
        at = None if hit is None else hit["at"]
        milestones[str(milestone)] = {
            "reached": hit is not None,
            "reached_at": None if at is None else at.isoformat(),
            "calendar_days_elapsed": None if at is None else _days(start, at),
            "trading_days_elapsed": (
                None
                if at is None
                else sum(day <= at.date() for day in trading_dates)
            ),
            "entries_to_reach": (
                None if hit is None else hit["executed_entries"]
            ),
            "wins_to_reach": None if hit is None else hit["wins"],
            "losses_to_reach": None if hit is None else hit["losses"],
            "breakeven_to_reach": None if hit is None else hit["breakeven"],
        }

    economic_status: dict[str, str] = {}
    for code in sorted(
        ECONOMICALLY_INTEGRATED_TOOLS
        | FUNCTIONAL_ONLY_TOOLS
        | ARCHITECTURE_ONLY_TOOLS
    ):
        if code in ARCHITECTURE_ONLY_TOOLS:
            economic_status[code] = "ARCHITECTURE_ONLY_NOT_EXECUTABLE"
        elif code in FUNCTIONAL_ONLY_TOOLS:
            economic_status[code] = (
                "FUNCTIONAL_GREEN_NOT_PNL_ACTIVE_MISSING_HISTORICAL_EVIDENCE"
            )
        elif tool_counts[code] > 0:
            economic_status[code] = "INTEGRATED_AND_EXECUTED"
        else:
            economic_status[code] = "INTEGRATED_NOT_TRIGGERED_BY_PATH"

    report: dict[str, Any] = {
        "schema": "qore.cibo.research.60usd-6m-full-architecture-integrated.v5",
        "experiment_id": EXPERIMENT_ID,
        "status": "COMPLETED_MEASUREMENT",
        "measurement_window": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "advanced_evidence_cutoff": cutoff.isoformat(),
            "six_calendar_months": True,
            "selection_note": (
                "common seven-Trader overlap window chosen so full architecture "
                "can be exercised after the frozen-prior cutoff; not a certification holdout"
            ),
        },
        "capital_contract": {
            "initial_seed_usd": _money(INITIAL_SEED_USD),
            "survival_capital_usd": _money(SURVIVAL_CAPITAL_USD),
            "profit_cap_enabled": False,
            "all_valid_trader_entries_forwarded": True,
            "base_entry_expectation_filter": False,
            "base_entry_rank_filter": False,
            "outcome_aware_sizing": False,
            "floating_pnl_as_spendable_capital": False,
        },
        "evidence_boundary": {
            "phase18_rows_r_denominated": True,
            "exact_historical_provider_economics_complete": False,
            "exact_broker_executable_usd_claimed": False,
            "normalized_stop_risk_numeraire": (
                "USD risk is normalized to total net loss at structural stop"
            ),
            "net_stop_r_by_lineage": {
                spec.trader_id.value: str(spec.net_stop_r)
                for spec in SOURCE_SPECS
            },
            "regime_market_fields": (
                "NORMALIZED_NEUTRAL_FOR_LIQUIDITY_VOLATILITY_CORRELATION_PROVIDER"
            ),
            "historical_broker_stop_mutations_available": False,
            "t07_pnl_active": False,
            "t14_pnl_active": False,
        },
        "portfolio": {
            "opportunities": len(trades),
            "opportunities_forwarded_to_cibo": total_forwarded,
            "executed_entries": total_entries,
            "cibo_holds_no_capacity": total_holds,
            "wins": total_wins,
            "losses": total_losses,
            "breakeven": total_be,
            "net_realized_profit_usd": _money(realized_pnl),
            "ending_realized_capital_usd": _money(realized_capital),
            "minimum_realized_capital_usd": _money(minimum_capital),
            "peak_realized_capital_usd": _money(peak_capital),
            "max_realized_drawdown_usd": _money(max_drawdown),
            "peak_reserved_stop_risk_usd": _money(peak_reserved_risk),
            "first_base_protected_at": (
                None
                if first_base_protected_at is None
                else first_base_protected_at.isoformat()
            ),
            "first_advanced_allocation_at": (
                None
                if first_advanced_allocation_at is None
                else first_advanced_allocation_at.isoformat()
            ),
            "insolvency_at": (
                None if insolvency_at is None else insolvency_at.isoformat()
            ),
            "capital_amplification_profit_over_seed": str(
                realized_pnl / INITIAL_SEED_USD
            ),
        },
        "milestones": milestones,
        "per_trader": per_trader,
        "tool_execution_counts": dict(sorted(tool_counts.items())),
        "tool_pnl_active_entry_counts": dict(
            sorted(tool_effective_pnl_entries.items())
        ),
        "tool_status": economic_status,
        "flags": {
            "survival_positive_capital": (
                insolvency_at is None and minimum_capital > 0
            ),
            "base_protection_reached": first_base_protected_at is not None,
            "advanced_allocation_used": first_advanced_allocation_at is not None,
            "target_300_reached": Decimal("300") in milestone_hits,
        },
        "governance": {
            "isolated_experiment": True,
            "pr651_certification_evidence": False,
            "phase20d_evidence": False,
            "phase21_evidence": False,
            "phase22_evidence": False,
            "vps_used": False,
            "broker_mutation": False,
            "live_authority": False,
            "real_capital_authority": False,
        },
    }

    (output_dir / "report-v5.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "trade-ledger-v5.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in ledger_rows),
        encoding="utf-8",
    )
    with (output_dir / "per-trader-v5.csv").open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "trader",
                "opportunities",
                "forwarded",
                "entries",
                "holds",
                "wins",
                "losses",
                "breakeven",
                "gross_profit_usd",
                "gross_loss_usd",
                "net_pnl_usd",
                "profit_factor",
                "base_risk_assigned_usd",
                "expansion_risk_assigned_usd",
                "expanded_entries",
            ]
        )
        for trader, row in per_trader.items():
            writer.writerow(
                [
                    trader,
                    row["opportunities"],
                    row["opportunities_forwarded_to_cibo"],
                    row["executed_entries"],
                    row["cibo_holds_no_capacity"],
                    row["wins"],
                    row["losses"],
                    row["breakeven"],
                    row["gross_profit_usd"],
                    row["gross_loss_usd"],
                    row["net_pnl_usd"],
                    row["profit_factor"],
                    row["base_risk_assigned_usd"],
                    row["expansion_risk_assigned_usd"],
                    row["expanded_entries"],
                ]
            )

    m300 = milestones["300"]
    lines = [
        "# CIBO USD60 / 6M Full Architecture Integrated V5",
        "",
        f"- Window: {start.isoformat()} -> {end.isoformat()}",
        f"- Advanced causal cutoff: {cutoff.isoformat()}",
        f"- Opportunities forwarded: {total_forwarded}/{len(trades)}",
        f"- Executed entries: {total_entries}",
        f"- Wins / Losses / BE: {total_wins} / {total_losses} / {total_be}",
        f"- Net realized profit: USD {_money(realized_pnl)}",
        f"- Ending capital: USD {_money(realized_capital)}",
        f"- Minimum capital: USD {_money(minimum_capital)}",
        f"- Max drawdown: USD {_money(max_drawdown)}",
        (
            "- Base protection reached: "
            f"{report['flags']['base_protection_reached']}"
        ),
        (
            "- Advanced allocation used: "
            f"{report['flags']['advanced_allocation_used']}"
        ),
        f"- +USD300 reached: {m300['reached']}",
    ]
    if m300["reached"]:
        lines.extend(
            [
                f"- +USD300 at: {m300['reached_at']}",
                f"- Calendar days to +USD300: {m300['calendar_days_elapsed']}",
                f"- Trading days to +USD300: {m300['trading_days_elapsed']}",
                f"- Entries to +USD300: {m300['entries_to_reach']}",
                f"- W/L/BE to +USD300: {m300['wins_to_reach']} / "
                f"{m300['losses_to_reach']} / {m300['breakeven_to_reach']}",
            ]
        )
    lines.extend(
        [
            "",
            "## Tool integration",
            "",
            *[
                f"- {code}: {economic_status[code]} "
                f"(calls={tool_counts[code]})"
                for code in sorted(economic_status)
            ],
            "",
            "## Evidence boundary",
            "",
            (
                "V5 normalizes each lineage so one USD risk unit equals one USD total net loss at structural stop. It does not "
                "claim exact historical broker-executable USD because provider "
                "contract/spread/commission/slippage/margin evidence is absent "
                "from the sealed seven-Trader rows."
            ),
        ]
    )
    (output_dir / "V5-SUMMARY.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    for spec in SOURCE_SPECS:
        parser.add_argument(f"--{spec.key}", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    args = parser.parse_args()
    report = run(
        source_paths={
            spec.key: getattr(args, spec.key)
            for spec in SOURCE_SPECS
        },
        output_dir=args.output_dir,
        start=datetime.fromisoformat(args.start),
        end=datetime.fromisoformat(args.end),
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
