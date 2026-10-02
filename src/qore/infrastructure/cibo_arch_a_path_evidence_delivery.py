"""Architect-A descriptive capital-path evidence delivery.

This layer composes the already-reconciled capital-state delivery with one
canonical CompoundPathHistory. It exposes exact chronological path facts only
when the history's terminal state SHA equals the integrated Compound state SHA.

The output is descriptive evidence. It cannot claim causal treatment effect,
economic utility, certification, holdout access or productive authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal

from qore.infrastructure.cibo_arch_a_capital_state_delivery import (
    ArchACapitalStateDelivery,
)
from qore.infrastructure.cibo_compound_path_history import CompoundPathHistory

ARCH_A_PATH_EVIDENCE_DELIVERY_ID = (
    "CIBO_INTEGRATOR_ARCH_A_PATH_EVIDENCE_DELIVERY_V1"
)


@dataclass(frozen=True, slots=True)
class ArchAPathEvidenceDelivery:
    delivery_id: str
    source_manifest_sha256: str
    source_ledger_sha256: str
    compound_cycle_state_sha256: str
    compound_path_history_sha256: str
    path_snapshot_count: int
    minimum_original_base_usd: Decimal
    minimum_compound_economic_value_usd: Decimal
    minimum_strategic_reserve_usd: Decimal
    minimum_opportunity_reserve_usd: Decimal
    minimum_active_compound_capacity_usd: Decimal
    minimum_stop_risk_headroom_usd: Decimal
    minimum_margin_headroom_usd: Decimal
    maximum_protected_floor_usd: Decimal
    peak_closing_realized_capital_usd: Decimal
    terminal_closing_realized_capital_usd: Decimal
    maximum_realized_capital_giveback_usd: Decimal
    highest_generation: int
    descriptive_path_ready: bool
    causal_effect_identified: bool = False
    economic_utility_ready: bool = False
    certification_ready: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.delivery_id != ARCH_A_PATH_EVIDENCE_DELIVERY_ID:
            raise ValueError("A path-evidence delivery identity drift")
        for name in (
            "source_manifest_sha256",
            "source_ledger_sha256",
            "compound_cycle_state_sha256",
            "compound_path_history_sha256",
        ):
            _sha(getattr(self, name), name)
        if (
            not isinstance(self.path_snapshot_count, int)
            or isinstance(self.path_snapshot_count, bool)
            or self.path_snapshot_count < 2
        ):
            raise ValueError("A path-evidence snapshot count invalid")
        for name in (
            "minimum_original_base_usd",
            "minimum_compound_economic_value_usd",
            "minimum_strategic_reserve_usd",
            "minimum_opportunity_reserve_usd",
            "minimum_active_compound_capacity_usd",
            "minimum_stop_risk_headroom_usd",
            "minimum_margin_headroom_usd",
            "maximum_protected_floor_usd",
            "peak_closing_realized_capital_usd",
            "terminal_closing_realized_capital_usd",
            "maximum_realized_capital_giveback_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise ValueError(f"A path-evidence {name} invalid")
        if (
            not isinstance(self.highest_generation, int)
            or isinstance(self.highest_generation, bool)
            or self.highest_generation < 0
        ):
            raise ValueError("A path-evidence generation invalid")
        for name in (
            "descriptive_path_ready",
            "causal_effect_identified",
            "economic_utility_ready",
            "certification_ready",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"A path-evidence {name} must be bool")
        if not self.descriptive_path_ready:
            raise ValueError("A path-evidence delivery must be descriptively ready")
        if (
            self.causal_effect_identified
            or self.economic_utility_ready
            or self.certification_ready
            or self.productive_authority
        ):
            raise ValueError(
                "A path-evidence delivery cannot claim causal/certification authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        for name, value in tuple(payload.items()):
            if isinstance(value, Decimal):
                payload[name] = format(value, "f")
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_arch_a_path_evidence_delivery(
    *,
    capital_delivery: ArchACapitalStateDelivery,
    path_history: CompoundPathHistory,
) -> ArchAPathEvidenceDelivery:
    if not isinstance(capital_delivery, ArchACapitalStateDelivery):
        raise ValueError("A path-evidence requires canonical capital delivery")
    if not isinstance(path_history, CompoundPathHistory):
        raise ValueError("A path-evidence requires canonical path history")
    if not capital_delivery.settlement_delivery_ready:
        raise ValueError(
            "A path-evidence requires settlement-ready capital delivery"
        )
    if (
        capital_delivery.source_ledger_sha256 is None
        or capital_delivery.compound_cycle_state_sha256 is None
    ):
        raise ValueError("A path-evidence requires integrated truth hashes")

    terminal = path_history.snapshots[-1]
    if terminal.state_sha256 != capital_delivery.compound_cycle_state_sha256:
        raise ValueError(
            "A path-evidence history terminal state does not match capital truth"
        )
    if (
        terminal.original_base_usd != capital_delivery.terminal_original_base_usd
        or terminal.compound_economic_value_usd
        != capital_delivery.terminal_compound_economic_value_usd
        or terminal.protected_floor_usd
        != capital_delivery.terminal_protected_floor_usd
    ):
        raise ValueError(
            "A path-evidence terminal economics drift from capital delivery"
        )

    summary = path_history.summary
    return ArchAPathEvidenceDelivery(
        delivery_id=ARCH_A_PATH_EVIDENCE_DELIVERY_ID,
        source_manifest_sha256=capital_delivery.source_manifest_sha256,
        source_ledger_sha256=capital_delivery.source_ledger_sha256,
        compound_cycle_state_sha256=capital_delivery.compound_cycle_state_sha256,
        compound_path_history_sha256=path_history.fingerprint(),
        path_snapshot_count=len(path_history.snapshots),
        minimum_original_base_usd=summary.minimum_original_base_usd,
        minimum_compound_economic_value_usd=(
            summary.minimum_compound_economic_value_usd
        ),
        minimum_strategic_reserve_usd=summary.minimum_strategic_reserve_usd,
        minimum_opportunity_reserve_usd=summary.minimum_opportunity_reserve_usd,
        minimum_active_compound_capacity_usd=(
            summary.minimum_active_compound_capacity_usd
        ),
        minimum_stop_risk_headroom_usd=(
            summary.minimum_remaining_stop_risk_capacity_usd
        ),
        minimum_margin_headroom_usd=summary.minimum_remaining_margin_capacity_usd,
        maximum_protected_floor_usd=summary.maximum_protected_floor_usd,
        peak_closing_realized_capital_usd=(
            summary.peak_closing_realized_capital_usd
        ),
        terminal_closing_realized_capital_usd=(
            summary.terminal_closing_realized_capital_usd
        ),
        maximum_realized_capital_giveback_usd=(
            summary.maximum_realized_capital_giveback_usd
        ),
        highest_generation=summary.highest_generation,
        descriptive_path_ready=True,
        causal_effect_identified=False,
        economic_utility_ready=False,
        certification_ready=False,
        productive_authority=False,
    )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise ValueError(f"A path-evidence {name} invalid")
