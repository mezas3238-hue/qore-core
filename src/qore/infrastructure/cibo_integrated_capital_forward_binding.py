"""Forward-population binding for CIBO Integrated Capital Truth.

This gate proves that the exact terminal settlements in Architect B's immutable
forward manifest are the same settlement population represented by the compound
cycle before cross-ledger realized-profit equivalence is accepted.

It does not create source IDs, infer realized profit, sum non-fungible capital
dimensions, or grant sizing/Risk/execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ArchBForwardEconomicManifest,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_compound_cycle_state import CiboCompoundCycleState
from qore.infrastructure.cibo_integrated_capital_truth import (
    CiboIntegratedCapitalTruthError,
    ProtectedOpenFloorEquivalenceBinding,
    RealizedProfitEquivalenceBinding,
    build_integrated_capital_truth,
)

INTEGRATED_CAPITAL_FORWARD_BINDING_ID = (
    "CIBO_INTEGRATED_CAPITAL_FORWARD_POPULATION_BINDING_V1"
)


@dataclass(frozen=True, slots=True)
class CiboIntegratedCapitalForwardBindingReport:
    binding_id: str
    manifest_sha256: str
    manifest_rows: int
    compound_settlements: int
    manifest_positive_profit_usd: Decimal
    compound_positive_profit_usd: Decimal
    manifest_scientifically_ready: bool
    account_scope_match: bool
    settlement_population_exact: bool
    positive_profit_reconciliation_match: bool
    integrated_capital_truth_pass: bool
    ready_for_scientific_consumption: bool
    blockers: tuple[str, ...]
    source_ledger_sha256: str | None = None
    compound_cycle_state_sha256: str | None = None
    runtime_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.binding_id != INTEGRATED_CAPITAL_FORWARD_BINDING_ID:
            raise CiboIntegratedCapitalTruthError(
                "forward capital binding identity drift"
            )
        if (
            not self.manifest_sha256.startswith("sha256:")
            or len(self.manifest_sha256) != 71
        ):
            raise CiboIntegratedCapitalTruthError(
                "forward capital binding manifest SHA invalid"
            )
        for name in ("manifest_rows", "compound_settlements"):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboIntegratedCapitalTruthError(
                    f"forward capital binding {name} invalid"
                )
        for name in (
            "manifest_positive_profit_usd",
            "compound_positive_profit_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboIntegratedCapitalTruthError(
                    f"forward capital binding {name} invalid"
                )
        for name in (
            "manifest_scientifically_ready",
            "account_scope_match",
            "settlement_population_exact",
            "positive_profit_reconciliation_match",
            "integrated_capital_truth_pass",
            "ready_for_scientific_consumption",
            "runtime_authority",
            "sizing_authority",
            "risk_authority",
            "execution_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboIntegratedCapitalTruthError(
                    f"forward capital binding {name} must be bool"
                )
        expected_ready = all(
            (
                self.manifest_scientifically_ready,
                self.account_scope_match,
                self.settlement_population_exact,
                self.positive_profit_reconciliation_match,
                self.integrated_capital_truth_pass,
                not self.blockers,
            )
        )
        if self.ready_for_scientific_consumption != expected_ready:
            raise CiboIntegratedCapitalTruthError(
                "forward capital binding readiness/blocker drift"
            )
        if self.integrated_capital_truth_pass:
            if (
                self.source_ledger_sha256 is None
                or self.compound_cycle_state_sha256 is None
            ):
                raise CiboIntegratedCapitalTruthError(
                    "forward capital binding truth refs required"
                )
        elif (
            self.source_ledger_sha256 is not None
            or self.compound_cycle_state_sha256 is not None
        ):
            raise CiboIntegratedCapitalTruthError(
                "forward capital binding cannot expose failed truth refs"
            )
        if any(
            (
                self.runtime_authority,
                self.sizing_authority,
                self.risk_authority,
                self.execution_authority,
            )
        ):
            raise CiboIntegratedCapitalTruthError(
                "forward capital binding has no productive authority"
            )


def bind_forward_population_to_integrated_capital_truth(
    *,
    manifest: ArchBForwardEconomicManifest,
    account_identity: CiboAccountCapitalIdentity,
    source_ledger: CapitalSourceLedger,
    compound_state: CiboCompoundCycleState,
    realized_profit_bindings: tuple[
        RealizedProfitEquivalenceBinding, ...
    ],
    protected_floor_bindings: tuple[
        ProtectedOpenFloorEquivalenceBinding, ...
    ] = (),
) -> CiboIntegratedCapitalForwardBindingReport:
    """Reconcile exact forward settlements before accepting capital truth."""

    if not isinstance(manifest, ArchBForwardEconomicManifest):
        raise CiboIntegratedCapitalTruthError(
            "forward capital binding requires Architect-B manifest"
        )
    if not isinstance(account_identity, CiboAccountCapitalIdentity):
        raise CiboIntegratedCapitalTruthError(
            "forward capital binding account identity invalid"
        )
    if not isinstance(source_ledger, CapitalSourceLedger):
        raise CiboIntegratedCapitalTruthError(
            "forward capital binding source ledger invalid"
        )
    if not isinstance(compound_state, CiboCompoundCycleState):
        raise CiboIntegratedCapitalTruthError(
            "forward capital binding compound state invalid"
        )

    manifest_trader_lineages(manifest)

    account_scope = (
        compound_state.account_identity == account_identity
        and all(
            row.provider_key == account_identity.provider_key
            and row.account_ref == account_identity.account_ref
            and row.environment.lower()
            == account_identity.environment.value.lower()
            for row in manifest.rows
        )
    )

    manifest_keys = tuple(
        sorted(
            (
                row.settlement_sha256,
                row.signal_fingerprint,
                row.trader_id,
                format(row.realized_net_pnl_usd, "f"),
            )
            for row in manifest.rows
        )
    )
    compound_keys = tuple(
        sorted(
            (
                row.settlement_sha256,
                row.signal_fingerprint,
                row.trader_id.value,
                format(row.realized_net_pnl_usd, "f"),
            )
            for row in compound_state.settlements
        )
    )
    settlement_exact = manifest_keys == compound_keys

    manifest_positive = sum(
        (
            row.realized_net_pnl_usd
            for row in manifest.rows
            if row.realized_net_pnl_usd > 0
        ),
        Decimal(0),
    )
    compound_positive = sum(
        (
            row.realized_net_pnl_usd
            for row in compound_state.settlements
            if row.realized_net_pnl_usd > 0
        ),
        Decimal(0),
    )
    positive_match = manifest_positive == compound_positive

    blockers: list[str] = []
    if not manifest.ready_for_scientific_consumption:
        blockers.append("FORWARD_MANIFEST_NOT_SCIENTIFICALLY_READY")
    if not account_scope:
        blockers.append("FORWARD_CAPITAL_ACCOUNT_SCOPE_MISMATCH")
    if not settlement_exact:
        blockers.append("FORWARD_COMPOUND_SETTLEMENT_POPULATION_MISMATCH")
    if not positive_match:
        blockers.append("FORWARD_COMPOUND_POSITIVE_PROFIT_MISMATCH")

    truth = None
    if account_scope and settlement_exact and positive_match:
        try:
            truth = build_integrated_capital_truth(
                account_identity=account_identity,
                source_ledger=source_ledger,
                compound_state=compound_state,
                realized_profit_bindings=realized_profit_bindings,
                protected_floor_bindings=protected_floor_bindings,
            )
        except CiboIntegratedCapitalTruthError:
            blockers.append("INTEGRATED_CAPITAL_TRUTH_NOT_RECONCILED")
    else:
        blockers.append("INTEGRATED_CAPITAL_TRUTH_POPULATION_GATE_BLOCKED")

    blockers = list(dict.fromkeys(blockers))
    truth_pass = truth is not None
    ready = (
        manifest.ready_for_scientific_consumption
        and account_scope
        and settlement_exact
        and positive_match
        and truth_pass
        and not blockers
    )

    return CiboIntegratedCapitalForwardBindingReport(
        binding_id=INTEGRATED_CAPITAL_FORWARD_BINDING_ID,
        manifest_sha256=manifest.fingerprint(),
        manifest_rows=len(manifest.rows),
        compound_settlements=len(compound_state.settlements),
        manifest_positive_profit_usd=manifest_positive,
        compound_positive_profit_usd=compound_positive,
        manifest_scientifically_ready=manifest.ready_for_scientific_consumption,
        account_scope_match=account_scope,
        settlement_population_exact=settlement_exact,
        positive_profit_reconciliation_match=positive_match,
        integrated_capital_truth_pass=truth_pass,
        ready_for_scientific_consumption=ready,
        blockers=tuple(blockers),
        source_ledger_sha256=(
            None if truth is None else truth.source_ledger_sha256
        ),
        compound_cycle_state_sha256=(
            None if truth is None else truth.compound_cycle_state_sha256
        ),
        runtime_authority=False,
        sizing_authority=False,
        risk_authority=False,
        execution_authority=False,
    )


def manifest_trader_lineages(
    manifest: ArchBForwardEconomicManifest,
) -> tuple[TraderLineage, ...]:
    """Return canonical lineages or fail if a manifest row is not canonical."""

    result: list[TraderLineage] = []
    for row in manifest.rows:
        try:
            lineage = TraderLineage(row.trader_id)
        except ValueError as error:
            raise CiboIntegratedCapitalTruthError(
                "forward capital binding manifest trader lineage invalid"
            ) from error
        result.append(lineage)
    return tuple(result)
