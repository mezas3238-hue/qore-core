"""Integrator delivery adapter from B forward evidence to Architect-A capital science.

The adapter joins the exact Architect-B terminal forward population to canonical
Compound/Integrated Capital Truth. It exports only fields that are present in
canonical state. Path minima, giveback and per-episode protected-floor
graduation remain explicit gaps until a chronological state-history source
exists; terminal state is never relabelled as path history.

Research-only. No sizing, Risk, execution, LIVE, holdout or real-capital
authority is granted.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ArchBForwardEconomicManifest,
    ArchBForwardEconomicManifestRow,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_compound_capital import CompoundCapitalState
from qore.infrastructure.cibo_compound_cycle_state import (
    CiboCompoundCycleState,
    CompoundCycleDeployment,
    CompoundCycleMarketRecord,
    CompoundCycleSettlementRecord,
)
from qore.infrastructure.cibo_integrated_capital_forward_binding import (
    bind_forward_population_to_integrated_capital_truth,
)
from qore.infrastructure.cibo_integrated_capital_truth import (
    ProtectedOpenFloorEquivalenceBinding,
    RealizedProfitEquivalenceBinding,
)

ARCH_A_CAPITAL_STATE_DELIVERY_ID = "CIBO_INTEGRATOR_ARCH_A_CAPITAL_STATE_DELIVERY_V1"

_PATH_GAPS = (
    "PATH_MINIMUM_REALIZED_BASE_CAPITAL_HISTORY_NOT_MATERIALIZED",
    "PATH_MINIMUM_COMPOUND_CAPITAL_HISTORY_NOT_MATERIALIZED",
    "PATH_MINIMUM_LIQUID_RESERVE_HISTORY_NOT_MATERIALIZED",
    "PATH_MINIMUM_OPTIONALITY_RESERVE_HISTORY_NOT_MATERIALIZED",
    "PROTECTED_FLOOR_GRADUATION_PER_EPISODE_NOT_MATERIALIZED",
    "PROFIT_GIVEBACK_PATH_NOT_MATERIALIZED",
    "CRISIS_FACTOR_HISTORY_NOT_BOUND_TO_DELIVERY",
)


@dataclass(frozen=True, slots=True)
class ArchACapitalStateDeliveryRow:
    source_manifest_sha256: str
    decision_evidence_sha256: str
    signal_fingerprint: str
    trader_id: str
    settlement_sha256: str
    settlement_occurred_at: datetime
    source_kind: str
    realized_net_pnl_usd: Decimal
    provider_economics_sha256: str
    deployment_id: str | None
    market_event_id: str | None
    decision_id: str | None
    deployed_at: datetime | None
    source_lot_id: str | None
    source_capital_generation: int | None
    deployed_capital_usd: Decimal | None
    stop_risk_usd: Decimal | None
    margin_usd: Decimal | None
    capital_lock_minutes: Decimal | None

    def __post_init__(self) -> None:
        for name in (
            "source_manifest_sha256",
            "decision_evidence_sha256",
            "settlement_sha256",
            "provider_economics_sha256",
        ):
            _sha(getattr(self, name), name)
        if not self.signal_fingerprint or not self.trader_id:
            raise ValueError("A capital-state delivery row identity required")
        _aware(self.settlement_occurred_at, "settlement_occurred_at")
        if self.source_kind not in {"BASE_CAPITAL", "COMPOUND_CAPITAL"}:
            raise ValueError("A capital-state delivery source kind invalid")
        if (
            not isinstance(self.realized_net_pnl_usd, Decimal)
            or not self.realized_net_pnl_usd.is_finite()
        ):
            raise ValueError("A capital-state delivery realized PnL invalid")

        compound_fields = (
            self.deployment_id,
            self.market_event_id,
            self.decision_id,
            self.deployed_at,
            self.source_lot_id,
            self.source_capital_generation,
            self.deployed_capital_usd,
            self.stop_risk_usd,
            self.margin_usd,
            self.capital_lock_minutes,
        )
        if self.source_kind == "BASE_CAPITAL":
            if any(value is not None for value in compound_fields):
                raise ValueError(
                    "base-capital delivery cannot fabricate deployment fields"
                )
            return
        if any(value is None for value in compound_fields):
            raise ValueError(
                "compound-capital delivery requires complete deployment lineage"
            )
        assert self.deployed_at is not None
        _aware(self.deployed_at, "deployed_at")
        if self.deployed_at > self.settlement_occurred_at:
            raise ValueError("compound deployment cannot postdate settlement")
        if (
            not isinstance(self.source_capital_generation, int)
            or isinstance(self.source_capital_generation, bool)
            or self.source_capital_generation < 1
        ):
            raise ValueError("compound source generation invalid")
        for name in (
            "deployed_capital_usd",
            "stop_risk_usd",
            "margin_usd",
            "capital_lock_minutes",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise ValueError(f"A capital-state delivery {name} invalid")


@dataclass(frozen=True, slots=True)
class ArchACapitalStateBalance:
    state: str
    amount_usd: Decimal

    def __post_init__(self) -> None:
        if not self.state:
            raise ValueError("A capital-state balance identity required")
        if (
            not isinstance(self.amount_usd, Decimal)
            or not self.amount_usd.is_finite()
            or self.amount_usd < 0
        ):
            raise ValueError("A capital-state balance amount invalid")


@dataclass(frozen=True, slots=True)
class ArchACapitalStateDelivery:
    delivery_id: str
    source_manifest_sha256: str
    source_ledger_sha256: str | None
    compound_cycle_state_sha256: str | None
    rows: tuple[ArchACapitalStateDeliveryRow, ...]
    terminal_original_base_usd: Decimal
    terminal_compound_economic_value_usd: Decimal
    terminal_protected_floor_usd: Decimal
    terminal_policy_protected_floor_usd: Decimal
    terminal_broker_guaranteed_floor_usd: Decimal
    terminal_compound_balances: tuple[ArchACapitalStateBalance, ...]
    highest_generation: int
    exact_settlement_population_bound: bool
    integrated_capital_truth_pass: bool
    forward_manifest_scientifically_ready: bool
    settlement_delivery_ready: bool
    full_a001_capital_path_ready: bool
    gaps: tuple[str, ...]
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.delivery_id != ARCH_A_CAPITAL_STATE_DELIVERY_ID:
            raise ValueError("A capital-state delivery identity drift")
        _sha(self.source_manifest_sha256, "source_manifest_sha256")
        for name in ("source_ledger_sha256", "compound_cycle_state_sha256"):
            value = getattr(self, name)
            if value is not None:
                _sha(value, name)
        if len(self.rows) != len(
            {(row.settlement_sha256, row.signal_fingerprint) for row in self.rows}
        ):
            raise ValueError("A capital-state delivery rows must be unique")
        for name in (
            "terminal_original_base_usd",
            "terminal_compound_economic_value_usd",
            "terminal_protected_floor_usd",
            "terminal_policy_protected_floor_usd",
            "terminal_broker_guaranteed_floor_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise ValueError(f"A capital-state delivery {name} invalid")
        if (
            not isinstance(self.highest_generation, int)
            or isinstance(self.highest_generation, bool)
            or self.highest_generation < 0
        ):
            raise ValueError("A capital-state delivery generation invalid")
        for name in (
            "exact_settlement_population_bound",
            "integrated_capital_truth_pass",
            "forward_manifest_scientifically_ready",
            "settlement_delivery_ready",
            "full_a001_capital_path_ready",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"A capital-state delivery {name} must be bool")
        expected_settlement_ready = (
            self.exact_settlement_population_bound
            and self.integrated_capital_truth_pass
            and len(self.rows) > 0
            and self.source_ledger_sha256 is not None
            and self.compound_cycle_state_sha256 is not None
        )
        if self.settlement_delivery_ready != expected_settlement_ready:
            raise ValueError("A capital-state settlement readiness drift")
        expected_full = (
            self.settlement_delivery_ready
            and self.forward_manifest_scientifically_ready
            and not self.gaps
        )
        if self.full_a001_capital_path_ready != expected_full:
            raise ValueError("A capital-state full readiness drift")
        if self.productive_authority:
            raise ValueError("A capital-state delivery grants no productive authority")

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["rows"] = [
            {
                **asdict(row),
                "settlement_occurred_at": row.settlement_occurred_at.isoformat(),
                "deployed_at": (
                    None if row.deployed_at is None else row.deployed_at.isoformat()
                ),
                "realized_net_pnl_usd": format(row.realized_net_pnl_usd, "f"),
                "deployed_capital_usd": _fmt(row.deployed_capital_usd),
                "stop_risk_usd": _fmt(row.stop_risk_usd),
                "margin_usd": _fmt(row.margin_usd),
                "capital_lock_minutes": _fmt(row.capital_lock_minutes),
            }
            for row in self.rows
        ]
        payload["terminal_compound_balances"] = [
            {"state": item.state, "amount_usd": format(item.amount_usd, "f")}
            for item in self.terminal_compound_balances
        ]
        for name in (
            "terminal_original_base_usd",
            "terminal_compound_economic_value_usd",
            "terminal_protected_floor_usd",
            "terminal_policy_protected_floor_usd",
            "terminal_broker_guaranteed_floor_usd",
        ):
            payload[name] = format(getattr(self, name), "f")
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_arch_a_capital_state_delivery(
    *,
    manifest: ArchBForwardEconomicManifest,
    account_identity: CiboAccountCapitalIdentity,
    source_ledger: CapitalSourceLedger,
    compound_state: CiboCompoundCycleState,
    realized_profit_bindings: tuple[RealizedProfitEquivalenceBinding, ...],
    protected_floor_bindings: tuple[ProtectedOpenFloorEquivalenceBinding, ...] = (),
) -> ArchACapitalStateDelivery:
    binding = bind_forward_population_to_integrated_capital_truth(
        manifest=manifest,
        account_identity=account_identity,
        source_ledger=source_ledger,
        compound_state=compound_state,
        realized_profit_bindings=realized_profit_bindings,
        protected_floor_bindings=protected_floor_bindings,
    )
    manifest_sha = manifest.fingerprint()

    settlements = {item.settlement_sha256: item for item in compound_state.settlements}
    if len(settlements) != len(compound_state.settlements):
        raise ValueError("A capital-state compound settlement digest reused")

    rows: list[ArchACapitalStateDeliveryRow] = []
    for forward_row in manifest.rows:
        settlement = settlements.get(forward_row.settlement_sha256)
        if settlement is None:
            raise ValueError("A capital-state forward settlement missing from Compound")
        _bind_forward_to_settlement(forward_row, settlement)
        rows.append(
            _delivery_row(
                forward_row=forward_row,
                settlement=settlement,
                source_manifest_sha256=manifest_sha,
                compound_state=compound_state,
            )
        )

    balances = tuple(
        ArchACapitalStateBalance(
            state=state.value,
            amount_usd=compound_state.compound_ledger.balance(state),
        )
        for state in CompoundCapitalState
    )
    settlement_ready = (
        binding.settlement_population_exact
        and binding.integrated_capital_truth_pass
        and bool(rows)
        and binding.source_ledger_sha256 is not None
        and binding.compound_cycle_state_sha256 is not None
    )
    gaps = list(_PATH_GAPS)
    if not manifest.ready_for_scientific_consumption:
        gaps.append("FORWARD_MANIFEST_NOT_SCIENTIFICALLY_READY")

    return ArchACapitalStateDelivery(
        delivery_id=ARCH_A_CAPITAL_STATE_DELIVERY_ID,
        source_manifest_sha256=manifest_sha,
        source_ledger_sha256=binding.source_ledger_sha256,
        compound_cycle_state_sha256=binding.compound_cycle_state_sha256,
        rows=tuple(rows),
        terminal_original_base_usd=compound_state.current_original_base_usd,
        terminal_compound_economic_value_usd=(
            compound_state.compound_ledger.current_economic_value_usd
        ),
        terminal_protected_floor_usd=compound_state.floor_ledger.total_floor_usd,
        terminal_policy_protected_floor_usd=(
            compound_state.floor_ledger.policy_protected_floor_usd
        ),
        terminal_broker_guaranteed_floor_usd=(
            compound_state.floor_ledger.broker_guaranteed_floor_usd
        ),
        terminal_compound_balances=balances,
        highest_generation=compound_state.highest_generation,
        exact_settlement_population_bound=binding.settlement_population_exact,
        integrated_capital_truth_pass=binding.integrated_capital_truth_pass,
        forward_manifest_scientifically_ready=(
            manifest.ready_for_scientific_consumption
        ),
        settlement_delivery_ready=settlement_ready,
        full_a001_capital_path_ready=False,
        gaps=tuple(dict.fromkeys(gaps)),
        productive_authority=False,
    )


def _delivery_row(
    *,
    forward_row: ArchBForwardEconomicManifestRow,
    settlement: CompoundCycleSettlementRecord,
    source_manifest_sha256: str,
    compound_state: CiboCompoundCycleState,
) -> ArchACapitalStateDeliveryRow:
    if settlement.source_kind == "BASE_CAPITAL":
        return ArchACapitalStateDeliveryRow(
            source_manifest_sha256=source_manifest_sha256,
            decision_evidence_sha256=forward_row.decision_evidence_sha256,
            signal_fingerprint=forward_row.signal_fingerprint,
            trader_id=forward_row.trader_id,
            settlement_sha256=settlement.settlement_sha256,
            settlement_occurred_at=settlement.occurred_at,
            source_kind=settlement.source_kind,
            realized_net_pnl_usd=settlement.realized_net_pnl_usd,
            provider_economics_sha256=forward_row.provider_economics_sha256,
            deployment_id=None,
            market_event_id=None,
            decision_id=None,
            deployed_at=None,
            source_lot_id=None,
            source_capital_generation=None,
            deployed_capital_usd=None,
            stop_risk_usd=None,
            margin_usd=None,
            capital_lock_minutes=None,
        )

    if settlement.deployment_id is None:
        raise ValueError("compound settlement missing deployment id")
    deployment = _one_deployment(compound_state, settlement.deployment_id)
    if not deployment.settled or deployment.settlement_sha256 != settlement.settlement_sha256:
        raise ValueError("compound deployment settlement binding drift")
    if (
        deployment.signal_fingerprint != settlement.signal_fingerprint
        or deployment.trader_id != settlement.trader_id
    ):
        raise ValueError("compound deployment identity drift")
    market = _one_market_record(compound_state, deployment.market_event_id)
    if market.decision_id != deployment.decision_id:
        raise ValueError("compound deployment market decision drift")

    all_lots = (
        compound_state.compound_ledger.active_lots
        + compound_state.compound_ledger.archived_lots
    )
    source_lots = tuple(
        lot for lot in all_lots if lot.lot_id == deployment.source_lot_id
    )
    if len(source_lots) != 1:
        raise ValueError("compound deployment source lot not found exactly once")
    if source_lots[0].generation != deployment.source_generation:
        raise ValueError("compound deployment source generation drift")

    seconds = Decimal(
        str((settlement.occurred_at - deployment.deployed_at).total_seconds())
    )
    lock_minutes = seconds / Decimal("60")
    return ArchACapitalStateDeliveryRow(
        source_manifest_sha256=source_manifest_sha256,
        decision_evidence_sha256=forward_row.decision_evidence_sha256,
        signal_fingerprint=forward_row.signal_fingerprint,
        trader_id=forward_row.trader_id,
        settlement_sha256=settlement.settlement_sha256,
        settlement_occurred_at=settlement.occurred_at,
        source_kind=settlement.source_kind,
        realized_net_pnl_usd=settlement.realized_net_pnl_usd,
        provider_economics_sha256=forward_row.provider_economics_sha256,
        deployment_id=deployment.deployment_id,
        market_event_id=deployment.market_event_id,
        decision_id=deployment.decision_id,
        deployed_at=deployment.deployed_at,
        source_lot_id=deployment.source_lot_id,
        source_capital_generation=deployment.source_generation,
        deployed_capital_usd=deployment.amount_usd,
        stop_risk_usd=deployment.stop_risk_usd,
        margin_usd=deployment.margin_usd,
        capital_lock_minutes=lock_minutes,
    )


def _bind_forward_to_settlement(
    forward_row: ArchBForwardEconomicManifestRow,
    settlement: CompoundCycleSettlementRecord,
) -> None:
    if (
        settlement.signal_fingerprint != forward_row.signal_fingerprint
        or settlement.trader_id.value != forward_row.trader_id
        or settlement.realized_net_pnl_usd != forward_row.realized_net_pnl_usd
    ):
        raise ValueError("A capital-state forward/settlement identity drift")


def _one_deployment(
    state: CiboCompoundCycleState,
    deployment_id: str,
) -> CompoundCycleDeployment:
    rows = tuple(item for item in state.deployments if item.deployment_id == deployment_id)
    if len(rows) != 1:
        raise ValueError("compound deployment not found exactly once")
    return rows[0]


def _one_market_record(
    state: CiboCompoundCycleState,
    market_event_id: str,
) -> CompoundCycleMarketRecord:
    rows = tuple(item for item in state.market_records if item.event_id == market_event_id)
    if len(rows) != 1:
        raise ValueError("compound market record not found exactly once")
    return rows[0]


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise ValueError(f"A capital-state delivery {name} invalid")


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"A capital-state delivery {name} must be timezone-aware")


def _fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")
