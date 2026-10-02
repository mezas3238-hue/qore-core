"""Empirical cTrader DEMO entry-execution calibration for CIBO Phase20D.

This module measures observed entry slippage and execution latency from the
already-sealed forward economic manifest plus reconciled weighted provider
fills. It never infers fills from PnL, never projects current terms onto 2017,
never refits a policy, and grants no sizing/Risk/execution authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from math import ceil
from typing import Any

from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ArchBForwardEconomicManifest,
    ArchBForwardEconomicManifestRow,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    VersionedPhase20ExecutedRiskBook,
)
from qore.infrastructure.cibo_ce2i_phase20_outcome_reconciliation import (
    Phase20ExecutedRiskEvidence,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_provider_economics_evidence import (
    CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS,
)

PROVIDER_EXECUTION_CALIBRATION_ID = (
    "CIBO_CTRADER_DEMO_FORWARD_EXECUTION_CALIBRATION_V1"
)


@dataclass(frozen=True, slots=True)
class CiboProviderExecutionObservation:
    decision_evidence_sha256: str
    signal_fingerprint: str
    qore_symbol: str
    side: str
    provider_quote_price: Decimal
    weighted_fill_price: Decimal
    signed_slippage_price: Decimal
    signed_slippage_bps: Decimal
    adverse_slippage_bps: Decimal
    signed_slippage_cost_per_volume_usd: Decimal
    adverse_slippage_cost_per_volume_usd: Decimal
    provider_quote_age_ms: Decimal
    decision_to_fill_ms: Decimal
    fill_to_risk_reconciliation_ms: Decimal
    fill_evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            not self.decision_evidence_sha256.startswith("sha256:")
            or len(self.decision_evidence_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "provider execution calibration decision SHA invalid"
            )
        if not self.signal_fingerprint or not self.qore_symbol:
            raise CiboCapitalManagementError(
                "provider execution calibration signal/symbol required"
            )
        if self.side not in {"long", "short"}:
            raise CiboCapitalManagementError(
                "provider execution calibration side invalid"
            )
        for name in (
            "provider_quote_price",
            "weighted_fill_price",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"provider execution calibration {name} invalid"
                )
        for name in (
            "signed_slippage_price",
            "signed_slippage_bps",
            "adverse_slippage_bps",
            "signed_slippage_cost_per_volume_usd",
            "adverse_slippage_cost_per_volume_usd",
            "provider_quote_age_ms",
            "decision_to_fill_ms",
            "fill_to_risk_reconciliation_ms",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"provider execution calibration {name} invalid"
                )
        if (
            self.adverse_slippage_bps < 0
            or self.adverse_slippage_cost_per_volume_usd < 0
            or self.provider_quote_age_ms < 0
            or self.decision_to_fill_ms < 0
            or self.fill_to_risk_reconciliation_ms < 0
        ):
            raise CiboCapitalManagementError(
                "provider execution calibration latency/adverse values cannot be negative"
            )
        if self.adverse_slippage_bps != max(
            Decimal(0), self.signed_slippage_bps
        ):
            raise CiboCapitalManagementError(
                "provider execution calibration adverse-slippage drift"
            )
        if self.adverse_slippage_cost_per_volume_usd != max(
            Decimal(0), self.signed_slippage_cost_per_volume_usd
        ):
            raise CiboCapitalManagementError(
                "provider execution calibration adverse USD slippage drift"
            )
        if (
            not self.fill_evidence_refs
            or len(self.fill_evidence_refs)
            != len(set(self.fill_evidence_refs))
        ):
            raise CiboCapitalManagementError(
                "provider execution calibration fill refs required and unique"
            )


@dataclass(frozen=True, slots=True)
class CiboProviderExecutionSymbolSummary:
    qore_symbol: str
    observation_count: int
    mean_signed_slippage_bps: Decimal
    p95_adverse_slippage_bps: Decimal
    worst_adverse_slippage_bps: Decimal
    p95_adverse_slippage_cost_per_volume_usd: Decimal
    worst_adverse_slippage_cost_per_volume_usd: Decimal
    p95_provider_quote_age_ms: Decimal
    p95_decision_to_fill_ms: Decimal
    p95_fill_to_risk_reconciliation_ms: Decimal

    def __post_init__(self) -> None:
        if not self.qore_symbol or self.observation_count <= 0:
            raise CiboCapitalManagementError(
                "provider execution summary identity/count invalid"
            )
        for name in (
            "mean_signed_slippage_bps",
            "p95_adverse_slippage_bps",
            "worst_adverse_slippage_bps",
            "p95_adverse_slippage_cost_per_volume_usd",
            "worst_adverse_slippage_cost_per_volume_usd",
            "p95_provider_quote_age_ms",
            "p95_decision_to_fill_ms",
            "p95_fill_to_risk_reconciliation_ms",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"provider execution summary {name} invalid"
                )
        if any(
            value < 0
            for value in (
                self.p95_adverse_slippage_bps,
                self.worst_adverse_slippage_bps,
                self.p95_adverse_slippage_cost_per_volume_usd,
                self.worst_adverse_slippage_cost_per_volume_usd,
                self.p95_provider_quote_age_ms,
                self.p95_decision_to_fill_ms,
                self.p95_fill_to_risk_reconciliation_ms,
            )
        ):
            raise CiboCapitalManagementError(
                "provider execution summary one-sided metrics cannot be negative"
            )


@dataclass(frozen=True, slots=True)
class CiboProviderExecutionCalibration:
    calibration_id: str
    provider_key: str
    environment: str
    manifest_sha256: str
    manifest_candidate_rows: int
    manifest_complete_lineage_rows: int
    frozen_at: datetime
    total_observations: int
    observations: tuple[CiboProviderExecutionObservation, ...]
    symbol_summaries: tuple[CiboProviderExecutionSymbolSummary, ...]
    manifest_scientifically_ready: bool
    all_complete_rows_reconciled: bool
    required_symbol_coverage_met: bool
    minimum_symbol_observations_met: bool
    empirical_slippage_calibrated: bool
    execution_model_ready: bool
    historical_2017_exact_claimed: bool
    holdout_outcomes_used: bool
    target_aware: bool
    productive_authority: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.calibration_id != PROVIDER_EXECUTION_CALIBRATION_ID:
            raise CiboCapitalManagementError(
                "provider execution calibration identity drift"
            )
        if self.provider_key != "ctrader-demo" or self.environment != "demo":
            raise CiboCapitalManagementError(
                "provider execution calibration provider/environment drift"
            )
        _sha(self.manifest_sha256, "manifest_sha256")
        for name in (
            "manifest_candidate_rows",
            "manifest_complete_lineage_rows",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"provider execution calibration {name} invalid"
                )
        _aware(self.frozen_at, "frozen_at")
        if self.total_observations != len(self.observations):
            raise CiboCapitalManagementError(
                "provider execution calibration observation count drift"
            )
        summary_symbols = tuple(
            item.qore_symbol for item in self.symbol_summaries
        )
        if tuple(sorted(summary_symbols)) != summary_symbols:
            raise CiboCapitalManagementError(
                "provider execution summaries must be symbol ordered"
            )
        if len(summary_symbols) != len(set(summary_symbols)):
            raise CiboCapitalManagementError(
                "provider execution summaries must be symbol unique"
            )
        required = set(CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS.symbols)
        summary_by_symbol = {
            item.qore_symbol: item for item in self.symbol_summaries
        }
        observation_counts: dict[str, int] = {}
        for observation in self.observations:
            observation_counts[observation.qore_symbol] = (
                observation_counts.get(observation.qore_symbol, 0) + 1
            )
        if set(summary_by_symbol) != set(observation_counts):
            raise CiboCapitalManagementError(
                "provider execution calibration summary/observation symbol drift"
            )
        if any(
            summary_by_symbol[symbol].observation_count != count
            for symbol, count in observation_counts.items()
        ):
            raise CiboCapitalManagementError(
                "provider execution calibration summary count drift"
            )
        expected_symbol_coverage = required.issubset(summary_by_symbol)
        if self.required_symbol_coverage_met != expected_symbol_coverage:
            raise CiboCapitalManagementError(
                "provider execution calibration symbol coverage drift"
            )
        minimum_per_symbol = (
            FROZEN_PHASE20D_QUALIFICATION_PLAN.minimum_outcomes_per_lineage
        )
        expected_minimum = expected_symbol_coverage and all(
            summary_by_symbol[symbol].observation_count >= minimum_per_symbol
            for symbol in required
        )
        if self.minimum_symbol_observations_met != expected_minimum:
            raise CiboCapitalManagementError(
                "provider execution calibration symbol minimum drift"
            )
        expected_reconciled = (
            self.total_observations == self.manifest_complete_lineage_rows
            and self.total_observations > 0
        )
        if self.all_complete_rows_reconciled != expected_reconciled:
            raise CiboCapitalManagementError(
                "provider execution calibration manifest reconciliation drift"
            )
        if self.manifest_scientifically_ready:
            plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
            if self.manifest_candidate_rows < plan.minimum_candidate_outcomes:
                raise CiboCapitalManagementError(
                    "provider execution calibration manifest population below minimum"
                )
            if self.manifest_candidate_rows <= 0:
                raise CiboCapitalManagementError(
                    "provider execution calibration manifest candidate rows invalid"
                )
            coverage = Decimal(
                self.manifest_complete_lineage_rows
            ) / Decimal(self.manifest_candidate_rows)
            if coverage < plan.minimum_candidate_outcome_coverage:
                raise CiboCapitalManagementError(
                    "provider execution calibration manifest coverage below minimum"
                )
        for name in (
            "manifest_scientifically_ready",
            "all_complete_rows_reconciled",
            "required_symbol_coverage_met",
            "minimum_symbol_observations_met",
            "empirical_slippage_calibrated",
            "execution_model_ready",
            "historical_2017_exact_claimed",
            "holdout_outcomes_used",
            "target_aware",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"provider execution calibration {name} must be bool"
                )
        expected_ready = all(
            (
                self.manifest_scientifically_ready,
                self.all_complete_rows_reconciled,
                self.required_symbol_coverage_met,
                self.minimum_symbol_observations_met,
                self.total_observations > 0,
                not self.historical_2017_exact_claimed,
                not self.holdout_outcomes_used,
                not self.target_aware,
                not self.blockers,
            )
        )
        if self.empirical_slippage_calibrated != expected_ready:
            raise CiboCapitalManagementError(
                "provider execution calibration slippage readiness drift"
            )
        if self.execution_model_ready != expected_ready:
            raise CiboCapitalManagementError(
                "provider execution calibration execution-model readiness drift"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "provider execution calibration has no productive authority"
            )

    def fingerprint(self) -> str:
        payload = _canonical(asdict(self))
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def calibrate_ctrader_demo_forward_execution(
    *,
    manifest: ArchBForwardEconomicManifest,
    executed_risk_book: VersionedPhase20ExecutedRiskBook,
    frozen_at: datetime,
) -> CiboProviderExecutionCalibration:
    """Measure forward entry slippage/latency from exact provider fills."""

    if not isinstance(manifest, ArchBForwardEconomicManifest):
        raise CiboCapitalManagementError(
            "provider execution calibration requires Architect-B manifest"
        )
    if not isinstance(executed_risk_book, VersionedPhase20ExecutedRiskBook):
        raise CiboCapitalManagementError(
            "provider execution calibration requires executed-risk book"
        )
    _aware(frozen_at, "frozen_at")

    risk_by_id = {
        item.evidence_id: item for item in executed_risk_book.evidences
    }
    observations: list[CiboProviderExecutionObservation] = []
    blockers: list[str] = []

    for row in manifest.rows:
        risk = risk_by_id.get(row.execution_risk_evidence_id)
        if risk is None:
            blockers.append("EXECUTED_RISK_EVIDENCE_MISSING")
            continue
        observations.append(_observation(row=row, risk=risk))

    if any(risk.observed_at > frozen_at for risk in executed_risk_book.evidences):
        raise CiboCapitalManagementError(
            "provider execution calibration freeze predates observed risk evidence"
        )

    required = set(CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS.symbols)
    observed_symbols = {item.qore_symbol for item in observations}
    symbol_coverage = required.issubset(observed_symbols)
    if not symbol_coverage:
        blockers.append("REQUIRED_PROVIDER_SYMBOL_COVERAGE_INCOMPLETE")

    summaries = tuple(
        _summary(
            symbol=symbol,
            rows=tuple(
                item for item in observations if item.qore_symbol == symbol
            ),
        )
        for symbol in sorted(observed_symbols)
    )
    minimum_per_symbol = FROZEN_PHASE20D_QUALIFICATION_PLAN.minimum_outcomes_per_lineage
    minimum_symbol = symbol_coverage and all(
        item.observation_count >= minimum_per_symbol
        for item in summaries
        if item.qore_symbol in required
    )
    if not minimum_symbol:
        blockers.append("MINIMUM_PROVIDER_SYMBOL_OBSERVATIONS_NOT_MET")

    complete_reconciled = (
        len(observations) == manifest.complete_lineage_rows
        and len(observations) > 0
    )
    if not complete_reconciled:
        blockers.append("COMPLETE_MANIFEST_ROWS_NOT_EXECUTION_RECONCILED")
    if not manifest.ready_for_scientific_consumption:
        blockers.append("FORWARD_MANIFEST_NOT_SCIENTIFICALLY_READY")

    blockers = list(dict.fromkeys(blockers))
    ready = (
        manifest.ready_for_scientific_consumption
        and complete_reconciled
        and symbol_coverage
        and minimum_symbol
        and not blockers
    )
    return CiboProviderExecutionCalibration(
        calibration_id=PROVIDER_EXECUTION_CALIBRATION_ID,
        provider_key="ctrader-demo",
        environment="demo",
        manifest_sha256=manifest.fingerprint(),
        manifest_candidate_rows=manifest.candidate_rows,
        manifest_complete_lineage_rows=manifest.complete_lineage_rows,
        frozen_at=frozen_at,
        total_observations=len(observations),
        observations=tuple(observations),
        symbol_summaries=summaries,
        manifest_scientifically_ready=manifest.ready_for_scientific_consumption,
        all_complete_rows_reconciled=complete_reconciled,
        required_symbol_coverage_met=symbol_coverage,
        minimum_symbol_observations_met=minimum_symbol,
        empirical_slippage_calibrated=ready,
        execution_model_ready=ready,
        historical_2017_exact_claimed=False,
        holdout_outcomes_used=False,
        target_aware=False,
        productive_authority=False,
        blockers=tuple(blockers),
    )



def provider_execution_risk_sha256(
    risk: Phase20ExecutedRiskEvidence,
) -> str:
    """Canonical digest matching the Architect-B manifest risk digest."""

    if not isinstance(risk, Phase20ExecutedRiskEvidence):
        raise CiboCapitalManagementError(
            "provider execution risk digest requires canonical evidence"
        )
    raw = json.dumps(
        _canonical(asdict(risk)),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()

def _observation(
    *,
    row: ArchBForwardEconomicManifestRow,
    risk: Phase20ExecutedRiskEvidence,
) -> CiboProviderExecutionObservation:
    if risk.evidence_id != row.execution_risk_evidence_id:
        raise CiboCapitalManagementError(
            "provider execution risk evidence id drift"
        )
    if provider_execution_risk_sha256(risk) != row.executed_risk_sha256:
        raise CiboCapitalManagementError(
            "provider execution risk evidence SHA drift"
        )
    if row.provider_key != "ctrader-demo" or row.environment.lower() != "demo":
        raise CiboCapitalManagementError(
            "provider execution calibration provider/environment drift"
        )
    if (
        risk.decision_evidence_sha256 != row.decision_evidence_sha256
        or risk.signal_fingerprint != row.signal_fingerprint
        or risk.qore_symbol != row.qore_symbol
        or risk.filled_source_volume != row.executed_source_volume
        or risk.executed_initial_stop_risk_usd
        != row.executed_initial_stop_risk_usd
    ):
        raise CiboCapitalManagementError(
            "provider execution calibration manifest/risk lineage drift"
        )
    if not risk.fill_reconciled or not risk.mutation_outcome_known:
        raise CiboCapitalManagementError(
            "provider execution calibration requires reconciled known fill outcome"
        )
    if risk.capital_deployed_at is None:
        raise CiboCapitalManagementError(
            "provider execution calibration requires capital deployment timestamp"
        )
    provider_observed_at = datetime.fromisoformat(row.provider_observed_at)
    _aware(provider_observed_at, "provider_observed_at")
    if provider_observed_at > row.decision_at:
        raise CiboCapitalManagementError(
            "provider execution quote cannot postdate decision"
        )
    if risk.capital_deployed_at < row.decision_at:
        raise CiboCapitalManagementError(
            "provider execution fill cannot predate decision"
        )
    if risk.observed_at < risk.capital_deployed_at:
        raise CiboCapitalManagementError(
            "provider execution risk reconciliation cannot predate fill"
        )

    quote = row.provider_ask if risk.side == "long" else row.provider_bid
    signed_price = (
        risk.weighted_fill_price - quote
        if risk.side == "long"
        else quote - risk.weighted_fill_price
    )
    signed_bps = signed_price / quote * Decimal("10000")
    signed_cost_per_volume = (
        signed_price / row.provider_tick_size * row.provider_tick_value
    )
    return CiboProviderExecutionObservation(
        decision_evidence_sha256=row.decision_evidence_sha256,
        signal_fingerprint=row.signal_fingerprint,
        qore_symbol=row.qore_symbol,
        side=risk.side,
        provider_quote_price=quote,
        weighted_fill_price=risk.weighted_fill_price,
        signed_slippage_price=signed_price,
        signed_slippage_bps=signed_bps,
        adverse_slippage_bps=max(Decimal(0), signed_bps),
        signed_slippage_cost_per_volume_usd=signed_cost_per_volume,
        adverse_slippage_cost_per_volume_usd=max(
            Decimal(0),
            signed_cost_per_volume,
        ),
        provider_quote_age_ms=_milliseconds(
            row.decision_at - provider_observed_at
        ),
        decision_to_fill_ms=_milliseconds(
            risk.capital_deployed_at - row.decision_at
        ),
        fill_to_risk_reconciliation_ms=_milliseconds(
            risk.observed_at - risk.capital_deployed_at
        ),
        fill_evidence_refs=risk.fill_evidence_refs,
    )


def _summary(
    *,
    symbol: str,
    rows: tuple[CiboProviderExecutionObservation, ...],
) -> CiboProviderExecutionSymbolSummary:
    if not rows:
        raise CiboCapitalManagementError(
            "provider execution summary requires observations"
        )
    return CiboProviderExecutionSymbolSummary(
        qore_symbol=symbol,
        observation_count=len(rows),
        mean_signed_slippage_bps=sum(
            (item.signed_slippage_bps for item in rows),
            Decimal(0),
        )
        / Decimal(len(rows)),
        p95_adverse_slippage_bps=_p95(
            tuple(item.adverse_slippage_bps for item in rows)
        ),
        worst_adverse_slippage_bps=max(
            item.adverse_slippage_bps for item in rows
        ),
        p95_adverse_slippage_cost_per_volume_usd=_p95(
            tuple(
                item.adverse_slippage_cost_per_volume_usd
                for item in rows
            )
        ),
        worst_adverse_slippage_cost_per_volume_usd=max(
            item.adverse_slippage_cost_per_volume_usd for item in rows
        ),
        p95_provider_quote_age_ms=_p95(
            tuple(item.provider_quote_age_ms for item in rows)
        ),
        p95_decision_to_fill_ms=_p95(
            tuple(item.decision_to_fill_ms for item in rows)
        ),
        p95_fill_to_risk_reconciliation_ms=_p95(
            tuple(item.fill_to_risk_reconciliation_ms for item in rows)
        ),
    )


def _p95(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        raise CiboCapitalManagementError(
            "provider execution percentile requires values"
        )
    ordered = tuple(sorted(values))
    index = max(0, ceil(Decimal("0.95") * Decimal(len(ordered))) - 1)
    return ordered[index]


def _milliseconds(value: timedelta) -> Decimal:
    microseconds = (
        value.days * 86_400_000_000
        + value.seconds * 1_000_000
        + value.microseconds
    )
    if microseconds < 0:
        raise CiboCapitalManagementError(
            "provider execution calibration timing cannot be negative"
        )
    return Decimal(microseconds) / Decimal(1000)


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"provider execution calibration {name} must be timezone-aware"
        )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"provider execution calibration {name} must be canonical SHA-256"
        )


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value
