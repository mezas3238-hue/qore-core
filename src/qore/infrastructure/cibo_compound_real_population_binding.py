"""Strict binding of real forward economic evidence into Compound science.

This module is intentionally a fail-closed adapter. It does not collect provider
facts, reconstruct missing economics, open the sealed holdout, or grant runtime
authority. Architect B owns the provider/Risk/CMA/forward evidence surface.
Architect A consumes only immutable evidence that already satisfies this
contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.account_wide_risk import (
    TraderIdentity,
    canonical_trader_identity,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
)
from qore.infrastructure.cibo_compound_path_monte_carlo import (
    CompoundMonteCarloEpisode,
)


class CompoundPopulationEvidenceKind(StrEnum):
    FORWARD_OBSERVED = "FORWARD_OBSERVED"
    SYNTHETIC_CONTRACT = "SYNTHETIC_CONTRACT"
    BURNED_RESEARCH = "BURNED_RESEARCH"
    SEALED_HOLDOUT = "SEALED_HOLDOUT"


_FOLD_ORDER = {
    "WF1": 1,
    "WF2": 2,
    "WF3": 3,
    "WF4": 4,
}


@dataclass(frozen=True, slots=True)
class ForwardCompoundEconomicRecord:
    episode_id: str
    deployment_id: str
    market_event_id: str
    decision_id: str
    candidate_id: str
    trader_id: TraderIdentity
    signal_fingerprint: str
    account_identity_fingerprint: str
    qualification_fold_id: str
    decision_at: datetime
    deployed_at: datetime
    settled_at: datetime
    source_generation: int
    deployed_capital_usd: Decimal
    stop_risk_usd: Decimal
    margin_usd: Decimal
    realized_pnl_usd: Decimal
    protected_floor_graduation_usd: Decimal
    decision_evidence_sha256: str
    provider_economics_sha256: str
    risk_lineage_sha256: str
    cma_lineage_sha256: str
    terminal_settlement_sha256: str
    release_evidence_sha256: str
    source_manifest_sha256: str
    frozen_candidate_id: str
    frozen_candidate_code_sha: str
    evidence_kind: CompoundPopulationEvidenceKind
    floor_evidence_sha256: str | None = None
    market_record_present: bool = True
    terminal_release_present: bool = True
    future_leakage_used: bool = False

    def __post_init__(self) -> None:
        for name in (
            "episode_id",
            "deployment_id",
            "market_event_id",
            "decision_id",
            "candidate_id",
            "signal_fingerprint",
            "account_identity_fingerprint",
        ):
            if not getattr(self, name):
                raise CiboCompoundCapitalError(
                    f"real compound population {name} is required"
                )
        canonical_trader_identity(self.trader_id)
        if self.qualification_fold_id not in _FOLD_ORDER:
            raise CiboCompoundCapitalError(
                "real compound population requires canonical WF1..WF4"
            )
        for name in ("decision_at", "deployed_at", "settled_at"):
            _aware(getattr(self, name), name)
        if self.decision_at > self.deployed_at:
            raise CiboCompoundCapitalError(
                "real compound population decision follows deployment"
            )
        if self.settled_at <= self.deployed_at:
            raise CiboCompoundCapitalError(
                "real compound population settlement must follow deployment"
            )
        if self.decision_at < FROZEN_PHASE20_POLICY_CANDIDATE.frozen_at:
            raise CiboCompoundCapitalError(
                "real compound population contains pre-freeze decision"
            )
        if (
            self.frozen_candidate_id
            != FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id
            or self.frozen_candidate_code_sha
            != FROZEN_PHASE20_POLICY_CANDIDATE.code_sha
        ):
            raise CiboCompoundCapitalError(
                "real compound population frozen candidate lineage drift"
            )
        if self.evidence_kind is not CompoundPopulationEvidenceKind.FORWARD_OBSERVED:
            raise CiboCompoundCapitalError(
                "real compound population requires FORWARD_OBSERVED evidence"
            )
        if (
            not isinstance(self.source_generation, int)
            or isinstance(self.source_generation, bool)
            or self.source_generation < 1
        ):
            raise CiboCompoundCapitalError(
                "real compound population source generation must be positive int"
            )
        for name in (
            "deployed_capital_usd",
            "stop_risk_usd",
            "margin_usd",
        ):
            _money(getattr(self, name), name, positive=True)
        if (
            not isinstance(self.realized_pnl_usd, Decimal)
            or not self.realized_pnl_usd.is_finite()
        ):
            raise CiboCompoundCapitalError(
                "real compound population realized PnL must be finite Decimal"
            )
        _money(
            self.protected_floor_graduation_usd,
            "protected_floor_graduation_usd",
        )
        if self.protected_floor_graduation_usd > max(
            Decimal(0),
            self.realized_pnl_usd,
        ):
            raise CiboCompoundCapitalError(
                "real compound population floor graduation exceeds realized profit"
            )
        for name in (
            "decision_evidence_sha256",
            "provider_economics_sha256",
            "risk_lineage_sha256",
            "cma_lineage_sha256",
            "terminal_settlement_sha256",
            "release_evidence_sha256",
            "source_manifest_sha256",
        ):
            _sha(getattr(self, name), name)
        if self.protected_floor_graduation_usd > 0:
            if self.floor_evidence_sha256 is None:
                raise CiboCompoundCapitalError(
                    "real compound population floor graduation requires evidence"
                )
            _sha(self.floor_evidence_sha256, "floor_evidence_sha256")
        elif self.floor_evidence_sha256 is not None:
            raise CiboCompoundCapitalError(
                "real compound population zero floor graduation cannot carry evidence"
            )
        for name in (
            "market_record_present",
            "terminal_release_present",
            "future_leakage_used",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"real compound population {name} must be bool"
                )
        if (
            not self.market_record_present
            or not self.terminal_release_present
            or self.future_leakage_used
        ):
            raise CiboCompoundCapitalError(
                "real compound population provenance/governance drift"
            )


def bind_forward_compound_population(
    records: tuple[ForwardCompoundEconomicRecord, ...],
) -> tuple[CompoundMonteCarloEpisode, ...]:
    """Bind provider-valid forward records into the canonical MC episode type."""

    if not records:
        raise CiboCompoundCapitalError(
            "real compound population cannot be empty"
        )
    _require_unique(records, "episode_id")
    _require_unique(records, "deployment_id")
    _require_unique(records, "market_event_id")
    _require_unique(records, "decision_id")
    _require_four_non_overlapping_folds(records)
    accounts = {
        item.account_identity_fingerprint
        for item in records
    }
    if len(accounts) != 1:
        raise CiboCompoundCapitalError(
            "real compound population cannot mix account identities"
        )
    manifests = {
        item.source_manifest_sha256
        for item in records
    }
    if len(manifests) != 1:
        raise CiboCompoundCapitalError(
            "real compound population cannot mix source manifests"
        )

    ordered = tuple(
        sorted(
            records,
            key=lambda item: (
                item.deployed_at,
                item.settled_at,
                item.episode_id,
            ),
        )
    )
    return tuple(
        CompoundMonteCarloEpisode(
            episode_id=item.episode_id,
            deployment_id=item.deployment_id,
            market_event_id=item.market_event_id,
            decision_id=item.decision_id,
            candidate_id=item.candidate_id,
            trader_id=item.trader_id,
            signal_fingerprint=item.signal_fingerprint,
            deployed_at=item.deployed_at,
            settled_at=item.settled_at,
            source_generation=item.source_generation,
            deployed_capital_usd=item.deployed_capital_usd,
            stop_risk_usd=item.stop_risk_usd,
            margin_usd=item.margin_usd,
            realized_pnl_usd=item.realized_pnl_usd,
            protected_floor_graduation_usd=(
                item.protected_floor_graduation_usd
            ),
            floor_evidence_sha256=item.floor_evidence_sha256,
            market_record_present=item.market_record_present,
            terminal_release_present=item.terminal_release_present,
            future_leakage_used=item.future_leakage_used,
        )
        for item in ordered
    )


def _require_unique(
    records: tuple[ForwardCompoundEconomicRecord, ...],
    field: str,
) -> None:
    values = tuple(getattr(item, field) for item in records)
    if len(values) != len(set(values)):
        raise CiboCompoundCapitalError(
            f"real compound population duplicate {field}"
        )


def _require_four_non_overlapping_folds(
    records: tuple[ForwardCompoundEconomicRecord, ...],
) -> None:
    represented = {item.qualification_fold_id for item in records}
    if represented != set(_FOLD_ORDER):
        raise CiboCompoundCapitalError(
            "real compound population requires all four frozen temporal folds"
        )
    bounds: list[tuple[int, datetime, datetime]] = []
    for fold_id, order in _FOLD_ORDER.items():
        rows = tuple(
            item for item in records
            if item.qualification_fold_id == fold_id
        )
        start = min(item.decision_at for item in rows)
        end = max(item.settled_at for item in rows)
        bounds.append((order, start, end))
    bounds.sort(key=lambda item: item[0])
    for (_, _, prior_end), (_, next_start, _) in zip(
        bounds,
        bounds[1:],
        strict=False,
    ):
        if prior_end >= next_start:
            raise CiboCompoundCapitalError(
                "real compound population temporal folds overlap or interleave"
            )


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"real compound population {name} must be timezone-aware"
        )


def _money(
    value: Decimal,
    name: str,
    *,
    positive: bool = False,
) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or (value <= 0 if positive else value < 0)
    ):
        qualifier = "positive" if positive else "non-negative"
        raise CiboCompoundCapitalError(
            f"real compound population {name} must be finite {qualifier} Decimal"
        )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"real compound population {name} must be canonical SHA-256"
        )


@dataclass(frozen=True, slots=True)
class TraderLabBurnedResearchCompoundRecord:
    """Historical/reused-holdout episode input for capability testing only.

    This contract is intentionally separate from ForwardCompoundEconomicRecord.
    It cannot satisfy forward-observed, qualification, economic-replication, or
    certification evidence requirements.
    """

    episode_id: str
    trader_id: TraderIdentity
    signal_fingerprint: str
    account_identity_fingerprint: str
    decision_at: datetime
    deployed_at: datetime
    settled_at: datetime
    source_generation: int
    deployed_capital_usd: Decimal
    stop_risk_usd: Decimal
    margin_usd: Decimal
    realized_pnl_usd: Decimal
    source_trace_sha256: str
    evidence_kind: CompoundPopulationEvidenceKind = (
        CompoundPopulationEvidenceKind.BURNED_RESEARCH
    )
    future_leakage_used: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        for name in (
            "episode_id",
            "signal_fingerprint",
            "account_identity_fingerprint",
        ):
            if not getattr(self, name):
                raise CiboCompoundCapitalError(
                    f"Trader Lab burned-research {name} is required"
                )
        canonical_trader_identity(self.trader_id)
        for name in ("decision_at", "deployed_at", "settled_at"):
            _aware(getattr(self, name), name)
        if self.decision_at > self.deployed_at:
            raise CiboCompoundCapitalError(
                "Trader Lab burned-research decision follows deployment"
            )
        if self.settled_at <= self.deployed_at:
            raise CiboCompoundCapitalError(
                "Trader Lab burned-research settlement must follow deployment"
            )
        if (
            not isinstance(self.source_generation, int)
            or isinstance(self.source_generation, bool)
            or self.source_generation < 1
        ):
            raise CiboCompoundCapitalError(
                "Trader Lab burned-research source generation must be positive int"
            )
        for name in (
            "deployed_capital_usd",
            "stop_risk_usd",
            "margin_usd",
        ):
            _money(getattr(self, name), name, positive=True)
        if (
            not isinstance(self.realized_pnl_usd, Decimal)
            or not self.realized_pnl_usd.is_finite()
        ):
            raise CiboCompoundCapitalError(
                "Trader Lab burned-research realized PnL must be finite Decimal"
            )
        _sha(self.source_trace_sha256, "source_trace_sha256")
        if self.evidence_kind is not CompoundPopulationEvidenceKind.BURNED_RESEARCH:
            raise CiboCompoundCapitalError(
                "Trader Lab reused-holdout binding requires BURNED_RESEARCH evidence"
            )
        for name in (
            "future_leakage_used",
            "productive_authority",
            "certification_ready",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"Trader Lab burned-research {name} must be bool"
                )
        if (
            self.future_leakage_used
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "Trader Lab burned-research evidence cannot claim future leakage, "
                "productive authority, or certification readiness"
            )


@dataclass(frozen=True, slots=True)
class TraderLabBurnedResearchPopulationBinding:
    """Canonical MC bridge for a reused holdout; never certification evidence."""

    episodes: tuple[CompoundMonteCarloEpisode, ...]
    source_trace_sha256: str
    evidence_kind: CompoundPopulationEvidenceKind = (
        CompoundPopulationEvidenceKind.BURNED_RESEARCH
    )
    descriptive_only: bool = True
    forward_observed: bool = False
    economic_replication_claimed: bool = False
    certification_ready: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.episodes, tuple) or not self.episodes:
            raise CiboCompoundCapitalError(
                "Trader Lab burned-research binding requires episodes"
            )
        if any(
            not isinstance(item, CompoundMonteCarloEpisode)
            for item in self.episodes
        ):
            raise CiboCompoundCapitalError(
                "Trader Lab burned-research binding requires canonical MC episodes"
            )
        _sha(self.source_trace_sha256, "source_trace_sha256")
        if self.evidence_kind is not CompoundPopulationEvidenceKind.BURNED_RESEARCH:
            raise CiboCompoundCapitalError(
                "Trader Lab burned-research binding kind drift"
            )
        if not self.descriptive_only:
            raise CiboCompoundCapitalError(
                "Trader Lab burned-research binding must remain descriptive"
            )
        for name in (
            "forward_observed",
            "economic_replication_claimed",
            "certification_ready",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool or getattr(self, name):
                raise CiboCompoundCapitalError(
                    "Trader Lab burned-research binding cannot claim forward, "
                    "economic, certification, or productive authority"
                )


def bind_trader_lab_burned_research_population(
    records: tuple[TraderLabBurnedResearchCompoundRecord, ...],
) -> TraderLabBurnedResearchPopulationBinding:
    """Bind a used holdout into MC episodes without laundering it as forward evidence."""

    if not isinstance(records, tuple) or not records:
        raise CiboCompoundCapitalError(
            "Trader Lab burned-research population cannot be empty"
        )
    if any(
        type(item) is not TraderLabBurnedResearchCompoundRecord
        for item in records
    ):
        raise CiboCompoundCapitalError(
            "Trader Lab burned-research population requires exact research records"
        )
    for item in records:
        item.__post_init__()
    episode_ids = tuple(item.episode_id for item in records)
    if len(episode_ids) != len(set(episode_ids)):
        raise CiboCompoundCapitalError(
            "Trader Lab burned-research population duplicate episode_id"
        )
    accounts = {item.account_identity_fingerprint for item in records}
    if len(accounts) != 1:
        raise CiboCompoundCapitalError(
            "Trader Lab burned-research population cannot mix account identities"
        )
    traces = {item.source_trace_sha256 for item in records}
    if len(traces) != 1:
        raise CiboCompoundCapitalError(
            "Trader Lab burned-research population cannot mix source traces"
        )
    ordered = tuple(
        sorted(
            records,
            key=lambda item: (
                item.deployed_at,
                item.settled_at,
                item.episode_id,
            ),
        )
    )
    episodes = tuple(
        CompoundMonteCarloEpisode(
            episode_id=item.episode_id,
            deployment_id=f"{item.episode_id}:research-deployment",
            market_event_id=f"{item.episode_id}:research-market",
            decision_id=f"{item.episode_id}:research-decision",
            candidate_id=f"{item.episode_id}:research-candidate",
            trader_id=item.trader_id,
            signal_fingerprint=item.signal_fingerprint,
            deployed_at=item.deployed_at,
            settled_at=item.settled_at,
            source_generation=item.source_generation,
            deployed_capital_usd=item.deployed_capital_usd,
            stop_risk_usd=item.stop_risk_usd,
            margin_usd=item.margin_usd,
            realized_pnl_usd=item.realized_pnl_usd,
            protected_floor_graduation_usd=Decimal(0),
            floor_evidence_sha256=None,
            market_record_present=True,
            terminal_release_present=True,
            future_leakage_used=False,
        )
        for item in ordered
    )
    return TraderLabBurnedResearchPopulationBinding(
        episodes=episodes,
        source_trace_sha256=next(iter(traces)),
    )
