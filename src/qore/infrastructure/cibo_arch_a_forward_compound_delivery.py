"""Bridge from integrated B/Compound truth into Architect-A forward records.

This adapter emits the existing ForwardCompoundEconomicRecord contract used by
Architect A. Protected-floor attribution is derived from canonical floor
tranches and compound-lot settlement provenance; callers cannot inject a floor
credit. A separate CMA-lineage digest is recomputed from terminal settlement
identity instead of aliasing the terminal-settlement SHA.

Research-only. No holdout access or productive authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_arch_a_capital_state_delivery import (
    build_arch_a_capital_state_delivery,
)
from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ArchBForwardEconomicManifest,
    ArchBForwardEconomicManifestRow,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_compound_cycle_state import CiboCompoundCycleState
from qore.infrastructure.cibo_compound_path_monte_carlo import (
    CompoundMonteCarloFloorAttribution,
    extract_compound_monte_carlo_episodes,
)
from qore.infrastructure.cibo_compound_real_population_binding import (
    CompoundPopulationEvidenceKind,
    ForwardCompoundEconomicRecord,
)
from qore.infrastructure.cibo_integrated_capital_truth import (
    ProtectedOpenFloorEquivalenceBinding,
    RealizedProfitEquivalenceBinding,
)

ARCH_A_FORWARD_COMPOUND_DELIVERY_ID = (
    "CIBO_INTEGRATOR_ARCH_A_FORWARD_COMPOUND_RECORD_DELIVERY_V1"
)


@dataclass(frozen=True, slots=True)
class ArchAForwardCompoundDelivery:
    delivery_id: str
    source_manifest_sha256: str
    records: tuple[ForwardCompoundEconomicRecord, ...]
    compound_episode_count: int
    represented_folds: tuple[str, ...]
    forward_manifest_scientifically_ready: bool
    exact_capital_truth_bound: bool
    ready_for_arch_a_compound_binding: bool
    blockers: tuple[str, ...]
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.delivery_id != ARCH_A_FORWARD_COMPOUND_DELIVERY_ID:
            raise ValueError("A forward-compound delivery identity drift")
        _sha(self.source_manifest_sha256, "source_manifest_sha256")
        if self.compound_episode_count != len(self.records):
            raise ValueError("A forward-compound record count drift")
        if self.represented_folds != tuple(sorted(set(self.represented_folds))):
            raise ValueError("A forward-compound folds must be sorted unique")
        for name in (
            "forward_manifest_scientifically_ready",
            "exact_capital_truth_bound",
            "ready_for_arch_a_compound_binding",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"A forward-compound {name} must be bool")
        expected = (
            self.forward_manifest_scientifically_ready
            and self.exact_capital_truth_bound
            and bool(self.records)
            and set(self.represented_folds) == {"WF1", "WF2", "WF3", "WF4"}
            and not self.blockers
        )
        if self.ready_for_arch_a_compound_binding != expected:
            raise ValueError("A forward-compound readiness drift")
        if self.productive_authority:
            raise ValueError("A forward-compound delivery grants no authority")


def build_arch_a_forward_compound_delivery(
    *,
    manifest: ArchBForwardEconomicManifest,
    account_identity: CiboAccountCapitalIdentity,
    source_ledger: CapitalSourceLedger,
    compound_state: CiboCompoundCycleState,
    realized_profit_bindings: tuple[RealizedProfitEquivalenceBinding, ...],
    protected_floor_bindings: tuple[ProtectedOpenFloorEquivalenceBinding, ...] = (),
) -> ArchAForwardCompoundDelivery:
    capital_delivery = build_arch_a_capital_state_delivery(
        manifest=manifest,
        account_identity=account_identity,
        source_ledger=source_ledger,
        compound_state=compound_state,
        realized_profit_bindings=realized_profit_bindings,
        protected_floor_bindings=protected_floor_bindings,
    )
    manifest_sha = manifest.fingerprint()
    if capital_delivery.source_manifest_sha256 != manifest_sha:
        raise ValueError("A forward-compound source manifest drift")

    floor_attributions = _derive_floor_attributions(compound_state)
    episodes = extract_compound_monte_carlo_episodes(
        state=compound_state,
        floor_attributions=floor_attributions,
    )
    episode_by_settlement: dict[str, object] = {}
    for episode in episodes:
        deployment = next(
            item
            for item in compound_state.deployments
            if item.deployment_id == episode.deployment_id
        )
        assert deployment.settlement_sha256 is not None
        if deployment.settlement_sha256 in episode_by_settlement:
            raise ValueError("A forward-compound settlement reused by episodes")
        episode_by_settlement[deployment.settlement_sha256] = episode

    records: list[ForwardCompoundEconomicRecord] = []
    for row in manifest.rows:
        episode = episode_by_settlement.get(row.settlement_sha256)
        if episode is None:
            continue
        if row.policy_selected is not True:
            raise ValueError(
                "A forward-compound executed episode is not policy-selected"
            )
        records.append(
            _record(
                row=row,
                episode=episode,
                account_identity=account_identity,
                source_manifest_sha256=manifest_sha,
            )
        )

    represented_folds = tuple(sorted({item.qualification_fold_id for item in records}))
    blockers: list[str] = []
    if not manifest.ready_for_scientific_consumption:
        blockers.append("FORWARD_MANIFEST_NOT_SCIENTIFICALLY_READY")
    if not capital_delivery.settlement_delivery_ready:
        blockers.append("INTEGRATED_CAPITAL_TRUTH_NOT_READY")
    if not records:
        blockers.append("NO_COMPOUND_FORWARD_EPISODES")
    if records and set(represented_folds) != {"WF1", "WF2", "WF3", "WF4"}:
        blockers.append("COMPOUND_FORWARD_FOUR_FOLD_COVERAGE_NOT_MET")

    ready = (
        manifest.ready_for_scientific_consumption
        and capital_delivery.settlement_delivery_ready
        and bool(records)
        and set(represented_folds) == {"WF1", "WF2", "WF3", "WF4"}
        and not blockers
    )
    return ArchAForwardCompoundDelivery(
        delivery_id=ARCH_A_FORWARD_COMPOUND_DELIVERY_ID,
        source_manifest_sha256=manifest_sha,
        records=tuple(
            sorted(
                records,
                key=lambda item: (
                    item.deployed_at,
                    item.settled_at,
                    item.deployment_id,
                ),
            )
        ),
        compound_episode_count=len(records),
        represented_folds=represented_folds,
        forward_manifest_scientifically_ready=(
            manifest.ready_for_scientific_consumption
        ),
        exact_capital_truth_bound=capital_delivery.settlement_delivery_ready,
        ready_for_arch_a_compound_binding=ready,
        blockers=tuple(dict.fromkeys(blockers)),
        productive_authority=False,
    )


def _record(
    *,
    row: ArchBForwardEconomicManifestRow,
    episode: object,
    account_identity: CiboAccountCapitalIdentity,
    source_manifest_sha256: str,
) -> ForwardCompoundEconomicRecord:
    from qore.infrastructure.cibo_compound_path_monte_carlo import (
        CompoundMonteCarloEpisode,
    )

    if not isinstance(episode, CompoundMonteCarloEpisode):
        raise ValueError("A forward-compound episode type invalid")
    if (
        episode.signal_fingerprint != row.signal_fingerprint
        or episode.trader_id.value != row.trader_id
        or episode.realized_pnl_usd != row.realized_net_pnl_usd
    ):
        raise ValueError("A forward-compound episode/manifest identity drift")
    return ForwardCompoundEconomicRecord(
        episode_id=episode.episode_id,
        deployment_id=episode.deployment_id,
        market_event_id=episode.market_event_id,
        decision_id=episode.decision_id,
        candidate_id=episode.candidate_id,
        trader_id=episode.trader_id,
        signal_fingerprint=episode.signal_fingerprint,
        account_identity_fingerprint=_account_fingerprint(account_identity),
        qualification_fold_id=row.fold_id,
        decision_at=row.decision_at,
        deployed_at=episode.deployed_at,
        settled_at=episode.settled_at,
        source_generation=episode.source_generation,
        deployed_capital_usd=episode.deployed_capital_usd,
        stop_risk_usd=episode.stop_risk_usd,
        margin_usd=episode.margin_usd,
        realized_pnl_usd=episode.realized_pnl_usd,
        protected_floor_graduation_usd=(
            episode.protected_floor_graduation_usd
        ),
        decision_evidence_sha256=row.decision_evidence_sha256,
        provider_economics_sha256=row.provider_economics_sha256,
        risk_lineage_sha256=row.executed_risk_sha256,
        cma_lineage_sha256=_cma_lineage_sha256(row),
        terminal_settlement_sha256=row.settlement_sha256,
        release_evidence_sha256=row.release_evidence_sha256,
        source_manifest_sha256=source_manifest_sha256,
        frozen_candidate_id=row.candidate_id,
        frozen_candidate_code_sha=row.code_sha,
        evidence_kind=CompoundPopulationEvidenceKind.FORWARD_OBSERVED,
        floor_evidence_sha256=episode.floor_evidence_sha256,
        market_record_present=True,
        terminal_release_present=True,
        future_leakage_used=False,
    )


def _derive_floor_attributions(
    state: CiboCompoundCycleState,
) -> tuple[CompoundMonteCarloFloorAttribution, ...]:
    all_lots = {
        item.lot_id: item
        for item in (
            state.compound_ledger.active_lots
            + state.compound_ledger.archived_lots
        )
    }
    attributions: list[CompoundMonteCarloFloorAttribution] = []
    for deployment in state.deployments:
        if not deployment.settled or deployment.settlement_sha256 is None:
            continue
        settlements = tuple(
            item
            for item in state.settlements
            if item.deployment_id == deployment.deployment_id
        )
        if len(settlements) != 1:
            raise ValueError("A floor attribution settlement not unique")
        settlement = settlements[0]
        if settlement.realized_net_pnl_usd <= 0:
            continue

        tranches = []
        for tranche in state.floor_ledger.tranches:
            lot = all_lots.get(tranche.source_compound_lot_id)
            if lot is None:
                raise ValueError("A floor attribution source lot missing")
            if (
                lot.origin_signal_fingerprint == settlement.signal_fingerprint
                and lot.origin_position_id == settlement.position_id
                and lot.realized_at == settlement.occurred_at
            ):
                tranches.append(tranche)
        if not tranches:
            continue
        amount = sum((item.amount_usd for item in tranches), Decimal(0))
        payload = {
            "schema": "CIBO_ARCH_A_DERIVED_FLOOR_ATTRIBUTION_V1",
            "deployment_id": deployment.deployment_id,
            "settlement_sha256": settlement.settlement_sha256,
            "tranches": [
                {
                    "tranche_id": item.tranche_id,
                    "source_compound_lot_id": item.source_compound_lot_id,
                    "amount_usd": format(item.amount_usd, "f"),
                    "protection_class": item.protection_class.value,
                    "admitted_at": item.admitted_at.isoformat(),
                    "policy_id": item.policy_id,
                    "policy_sha256": item.policy_sha256,
                    "broker_guarantee_evidence_id": (
                        item.broker_guarantee_evidence_id
                    ),
                    "broker_guarantee_sha256": item.broker_guarantee_sha256,
                }
                for item in sorted(tranches, key=lambda row: row.tranche_id)
            ],
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        evidence_sha = "sha256:" + hashlib.sha256(raw).hexdigest()
        occurred_at = max(item.admitted_at for item in tranches)
        attributions.append(
            CompoundMonteCarloFloorAttribution(
                deployment_id=deployment.deployment_id,
                occurred_at=occurred_at,
                amount_usd=amount,
                evidence_sha256=evidence_sha,
            )
        )
    return tuple(
        sorted(attributions, key=lambda item: item.deployment_id)
    )


def _cma_lineage_sha256(row: ArchBForwardEconomicManifestRow) -> str:
    payload = {
        "schema": "CIBO_ARCH_A_CMA_LINEAGE_V1",
        "signal_fingerprint": row.signal_fingerprint,
        "settlement_sha256": row.settlement_sha256,
        "settlement_deal_ids": list(row.settlement_deal_ids),
        "realized_net_pnl_usd": format(row.realized_net_pnl_usd, "f"),
        "outcome_observed_at": row.outcome_observed_at.isoformat(),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _account_fingerprint(identity: CiboAccountCapitalIdentity) -> str:
    payload = {
        "provider_key": identity.provider_key,
        "account_ref": identity.account_ref,
        "environment": identity.environment.value,
        "provider_program": identity.provider_program,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise ValueError(f"A forward-compound {name} invalid")
