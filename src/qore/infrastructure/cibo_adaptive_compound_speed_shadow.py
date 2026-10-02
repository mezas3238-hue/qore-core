"""Preregistered GEN-C8 adaptive compound-speed shadow engine.

GEN-C8 changes only a research posture for the pace of future marginal-capital
proposals. It does not convert posture into lots, leverage or a capital amount
and cannot bypass GEN-C4/C5/C6, T19/T20, QORE Risk or Execution.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum

from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboRegimePosture,
    ProviderCondition,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_sequential_compounding_shadow_policy import (
    SequentialCompoundPosture,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_store import (
    Genc5ShadowDecisionSeal,
)

GENC8_POLICY_ID = "CIBO_GENC8_ADAPTIVE_COMPOUND_SPEED_SHADOW_V1"
GENC8_POLICY_FROZEN_AT = datetime(2026, 9, 30, 0, 20, tzinfo=UTC)


class Genc8SpeedPosture(StrEnum):
    PAUSE = "PAUSE"
    DEFENSIVE = "DEFENSIVE"
    CAUTIOUS = "CAUTIOUS"
    NORMAL = "NORMAL"
    ACCELERATED = "ACCELERATED"


class Genc8FactKind(StrEnum):
    LOSS_CLUSTER = "LOSS_CLUSTER"
    EDGE_CALIBRATION = "EDGE_CALIBRATION"
    SHARED_UNCERTAINTY = "SHARED_UNCERTAINTY"
    RELATIONSHIP_STABILITY = "RELATIONSHIP_STABILITY"
    PORTFOLIO_CONCENTRATION = "PORTFOLIO_CONCENTRATION"
    MARGIN_HEADROOM = "MARGIN_HEADROOM"
    RISK_HEADROOM = "RISK_HEADROOM"


class Genc8Severity(StrEnum):
    BENIGN = "BENIGN"
    WATCH = "WATCH"
    ADVERSE = "ADVERSE"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


_MANDATORY_FACTS = tuple(Genc8FactKind)

_POSTURE_RANK = {
    Genc8SpeedPosture.PAUSE: 0,
    Genc8SpeedPosture.DEFENSIVE: 1,
    Genc8SpeedPosture.CAUTIOUS: 2,
    Genc8SpeedPosture.NORMAL: 3,
    Genc8SpeedPosture.ACCELERATED: 4,
}


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C8 {name} must be timezone-aware"
        )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C8 {name} must be canonical SHA-256"
        )


@dataclass(frozen=True, slots=True)
class Genc8RegimeEvidence:
    evidence_id: str
    decision_at: datetime
    account_provider_key: str
    account_ref: str
    regime_posture: CiboRegimePosture
    provider_condition: ProviderCondition
    evidence_sha256: str
    source: str
    policy_version: str
    calibrated: bool
    capital_eligible: bool
    outcome_present: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if (
            not self.evidence_id
            or not self.account_provider_key
            or not self.account_ref
            or not self.source
            or not self.policy_version
        ):
            raise CiboCompoundCapitalError(
                "GEN-C8 regime evidence identity/source is required"
            )
        _aware(self.decision_at, "regime decision_at")
        if type(self.regime_posture) is not CiboRegimePosture:
            raise CiboCompoundCapitalError(
                "GEN-C8 regime posture is invalid"
            )
        if type(self.provider_condition) is not ProviderCondition:
            raise CiboCompoundCapitalError(
                "GEN-C8 provider condition is invalid"
            )
        _sha(self.evidence_sha256, "regime evidence_sha256")
        for name in (
            "calibrated",
            "capital_eligible",
            "outcome_present",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C8 regime {name} must be bool"
                )
        if self.outcome_present or self.productive_authority:
            raise CiboCompoundCapitalError(
                "GEN-C8 regime evidence cannot carry outcome/authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["decision_at"] = self.decision_at.isoformat()
        payload["regime_posture"] = self.regime_posture.value
        payload["provider_condition"] = self.provider_condition.value
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Genc8AdaptiveSpeedFact:
    fact_id: str
    decision_at: datetime
    account_provider_key: str
    account_ref: str
    kind: Genc8FactKind
    severity: Genc8Severity
    evidence_sha256: str
    source: str
    model_id: str
    calibrated: bool
    capital_eligible: bool
    outcome_present: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if (
            not self.fact_id
            or not self.account_provider_key
            or not self.account_ref
            or not self.source
            or not self.model_id
        ):
            raise CiboCompoundCapitalError(
                "GEN-C8 adaptive fact identity/source/model is required"
            )
        _aware(self.decision_at, "fact decision_at")
        if type(self.kind) is not Genc8FactKind:
            raise CiboCompoundCapitalError(
                "GEN-C8 adaptive fact kind is invalid"
            )
        if type(self.severity) is not Genc8Severity:
            raise CiboCompoundCapitalError(
                "GEN-C8 adaptive fact severity is invalid"
            )
        _sha(self.evidence_sha256, "fact evidence_sha256")
        for name in (
            "calibrated",
            "capital_eligible",
            "outcome_present",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C8 adaptive fact {name} must be bool"
                )
        if self.outcome_present or self.productive_authority:
            raise CiboCompoundCapitalError(
                "GEN-C8 adaptive fact cannot carry outcome/authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["decision_at"] = self.decision_at.isoformat()
        payload["kind"] = self.kind.value
        payload["severity"] = self.severity.value
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Genc8AdaptiveCompoundSpeedDecision:
    policy_id: str
    policy_sha256: str
    policy_frozen_at: datetime
    decision_id: str
    decision_at: datetime
    account_provider_key: str
    account_ref: str
    genc5_decision_sha256: str
    regime_evidence_sha256: str
    fact_evidence_sha256s: tuple[str, ...]
    control_posture: Genc8SpeedPosture
    treatment_posture: Genc8SpeedPosture
    binding_ceiling_posture: Genc8SpeedPosture
    binding_reason: str
    blocker_codes: tuple[str, ...]
    treatment_differs_from_control: bool
    amount_decided_usd: None = None
    outcome_present_at_seal: bool = False
    runtime_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    live_authority: bool = False
    real_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.policy_id != GENC8_POLICY_ID:
            raise CiboCompoundCapitalError("GEN-C8 policy identity drift")
        if self.policy_sha256 != genc8_policy_sha256():
            raise CiboCompoundCapitalError("GEN-C8 policy digest drift")
        if self.policy_frozen_at != GENC8_POLICY_FROZEN_AT:
            raise CiboCompoundCapitalError("GEN-C8 policy freeze drift")
        if (
            not self.decision_id
            or not self.account_provider_key
            or not self.account_ref
            or not self.binding_reason
        ):
            raise CiboCompoundCapitalError(
                "GEN-C8 decision identity/reason is required"
            )
        _aware(self.decision_at, "decision_at")
        if self.decision_at < self.policy_frozen_at:
            raise CiboCompoundCapitalError(
                "GEN-C8 cannot evaluate pre-freeze state"
            )
        _sha(self.genc5_decision_sha256, "genc5_decision_sha256")
        _sha(self.regime_evidence_sha256, "regime_evidence_sha256")
        if (
            not isinstance(self.fact_evidence_sha256s, tuple)
            or len(self.fact_evidence_sha256s) != len(_MANDATORY_FACTS)
            or len(self.fact_evidence_sha256s) != len(
                set(self.fact_evidence_sha256s)
            )
        ):
            raise CiboCompoundCapitalError(
                "GEN-C8 fact evidence SHA list must cover exact mandatory fact set"
            )
        for item in self.fact_evidence_sha256s:
            _sha(item, "fact_evidence_sha256")
        for name in (
            "control_posture",
            "treatment_posture",
            "binding_ceiling_posture",
        ):
            if type(getattr(self, name)) is not Genc8SpeedPosture:
                raise CiboCompoundCapitalError(
                    f"GEN-C8 {name} is invalid"
                )
        if self.treatment_posture is not self.binding_ceiling_posture:
            raise CiboCompoundCapitalError(
                "GEN-C8 V1 treatment must equal non-compensatory ceiling"
            )
        expected_differs = self.treatment_posture is not self.control_posture
        if type(self.treatment_differs_from_control) is not bool:
            raise CiboCompoundCapitalError(
                "GEN-C8 treatment/control divergence flag must be bool"
            )
        if self.treatment_differs_from_control != expected_differs:
            raise CiboCompoundCapitalError(
                "GEN-C8 treatment/control divergence flag drift"
            )
        if self.amount_decided_usd is not None:
            raise CiboCompoundCapitalError(
                "GEN-C8 speed posture cannot decide a capital amount"
            )
        for name in (
            "outcome_present_at_seal",
            "runtime_authority",
            "sizing_authority",
            "risk_authority",
            "execution_authority",
            "live_authority",
            "real_capital_authority",
        ):
            if type(getattr(self, name)) is not bool or getattr(self, name):
                raise CiboCompoundCapitalError(
                    "GEN-C8 shadow decision cannot contain outcome/authority"
                )


def genc8_policy_sha256() -> str:
    payload = {
        "policy_id": GENC8_POLICY_ID,
        "frozen_at": GENC8_POLICY_FROZEN_AT.isoformat(),
        "control": "exact durable GEN-C5 treatment posture",
        "treatment": "non-compensatory minimum posture ceiling",
        "mandatory_facts": tuple(item.value for item in _MANDATORY_FACTS),
        "regime_ceiling": {
            CiboRegimePosture.HALT_NEW_CAPITAL.value: "PAUSE",
            CiboRegimePosture.RECOVERY.value: "DEFENSIVE",
            CiboRegimePosture.DEFENSIVE.value: "DEFENSIVE",
            CiboRegimePosture.WATCH.value: "CAUTIOUS",
            CiboRegimePosture.STABLE.value: "ACCELERATED",
        },
        "provider_ceiling": {
            ProviderCondition.UNAVAILABLE.value: "PAUSE",
            ProviderCondition.DEGRADED.value: "DEFENSIVE",
            ProviderCondition.HEALTHY.value: "ACCELERATED",
        },
        "fact_ceiling": {
            Genc8Severity.UNKNOWN.value: "PAUSE",
            Genc8Severity.CRITICAL.value: "PAUSE",
            Genc8Severity.ADVERSE.value: "DEFENSIVE",
            Genc8Severity.WATCH.value: "CAUTIOUS",
            Genc8Severity.BENIGN.value: "ACCELERATED",
        },
        "weighted_score": False,
        "capital_amount_decided": False,
        "outcome_aware": False,
        "runtime_authority": False,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


def evaluate_genc8_adaptive_compound_speed(
    *,
    decision_id: str,
    genc5: Genc5ShadowDecisionSeal,
    regime: Genc8RegimeEvidence,
    facts: tuple[Genc8AdaptiveSpeedFact, ...],
) -> Genc8AdaptiveCompoundSpeedDecision:
    """Compare C5 control with a categorical non-score C8 speed ceiling."""

    if not decision_id:
        raise CiboCompoundCapitalError("GEN-C8 decision_id is required")
    if not isinstance(genc5, Genc5ShadowDecisionSeal):
        raise CiboCompoundCapitalError(
            "GEN-C8 requires canonical GEN-C5 decision seal"
        )
    if not isinstance(regime, Genc8RegimeEvidence):
        raise CiboCompoundCapitalError(
            "GEN-C8 requires canonical regime evidence"
        )
    if not isinstance(facts, tuple) or any(
        not isinstance(item, Genc8AdaptiveSpeedFact) for item in facts
    ):
        raise CiboCompoundCapitalError(
            "GEN-C8 facts must be canonical tuple"
        )
    if genc5.decision_at < GENC8_POLICY_FROZEN_AT:
        raise CiboCompoundCapitalError(
            "GEN-C8 cannot consume pre-freeze GEN-C5 decision"
        )
    if (
        regime.decision_at != genc5.decision_at
        or regime.account_provider_key != genc5.account_provider_key
        or regime.account_ref != genc5.account_ref
    ):
        raise CiboCompoundCapitalError(
            "GEN-C8 regime/GEN-C5 causal binding drift"
        )

    kinds = tuple(item.kind for item in facts)
    if len(kinds) != len(set(kinds)):
        raise CiboCompoundCapitalError(
            "GEN-C8 duplicate adaptive fact kind"
        )
    if set(kinds) != set(_MANDATORY_FACTS):
        raise CiboCompoundCapitalError(
            "GEN-C8 mandatory adaptive fact set incomplete"
        )
    for item in facts:
        if (
            item.decision_at != genc5.decision_at
            or item.account_provider_key != genc5.account_provider_key
            or item.account_ref != genc5.account_ref
        ):
            raise CiboCompoundCapitalError(
                "GEN-C8 fact/GEN-C5 causal binding drift"
            )

    blockers: list[str] = []
    ceilings: list[tuple[Genc8SpeedPosture, str]] = []

    if not regime.calibrated or not regime.capital_eligible:
        blockers.append("REGIME_EVIDENCE_NOT_CAPITAL_ELIGIBLE")
        ceilings.append(
            (Genc8SpeedPosture.PAUSE, "regime evidence not eligible")
        )
    else:
        ceilings.append(
            (
                _regime_ceiling(regime.regime_posture),
                f"regime:{regime.regime_posture.value}",
            )
        )
        ceilings.append(
            (
                _provider_ceiling(regime.provider_condition),
                f"provider:{regime.provider_condition.value}",
            )
        )

    for item in sorted(facts, key=lambda fact: fact.kind.value):
        if not item.calibrated or not item.capital_eligible:
            blockers.append(
                f"FACT_NOT_CAPITAL_ELIGIBLE:{item.kind.value}"
            )
            ceilings.append(
                (
                    Genc8SpeedPosture.PAUSE,
                    f"{item.kind.value}:NOT_CAPITAL_ELIGIBLE",
                )
            )
        else:
            ceilings.append(
                (
                    _severity_ceiling(item.severity),
                    f"{item.kind.value}:{item.severity.value}",
                )
            )

    treatment, reason = min(
        ceilings,
        key=lambda item: (
            _POSTURE_RANK[item[0]],
            item[1],
        ),
    )
    control = _control_posture(genc5.treatment_posture)

    return Genc8AdaptiveCompoundSpeedDecision(
        policy_id=GENC8_POLICY_ID,
        policy_sha256=genc8_policy_sha256(),
        policy_frozen_at=GENC8_POLICY_FROZEN_AT,
        decision_id=decision_id,
        decision_at=genc5.decision_at,
        account_provider_key=genc5.account_provider_key,
        account_ref=genc5.account_ref,
        genc5_decision_sha256=genc5.decision_sha256,
        regime_evidence_sha256=regime.fingerprint(),
        fact_evidence_sha256s=tuple(
            item.fingerprint()
            for item in sorted(facts, key=lambda fact: fact.kind.value)
        ),
        control_posture=control,
        treatment_posture=treatment,
        binding_ceiling_posture=treatment,
        binding_reason=reason,
        blocker_codes=tuple(blockers),
        treatment_differs_from_control=treatment is not control,
        amount_decided_usd=None,
        outcome_present_at_seal=False,
        runtime_authority=False,
        sizing_authority=False,
        risk_authority=False,
        execution_authority=False,
        live_authority=False,
        real_capital_authority=False,
    )


def _control_posture(
    posture: SequentialCompoundPosture,
) -> Genc8SpeedPosture:
    mapping = {
        SequentialCompoundPosture.COMPOUND_PAUSED: Genc8SpeedPosture.PAUSE,
        SequentialCompoundPosture.DEFENSIVE: Genc8SpeedPosture.DEFENSIVE,
        SequentialCompoundPosture.CAUTIOUS_COMPOUND: Genc8SpeedPosture.CAUTIOUS,
    }
    try:
        return mapping[posture]
    except KeyError as error:
        raise CiboCompoundCapitalError(
            "GEN-C8 control received posture outside frozen GEN-C5 V1 ceiling"
        ) from error


def _regime_ceiling(posture: CiboRegimePosture) -> Genc8SpeedPosture:
    return {
        CiboRegimePosture.HALT_NEW_CAPITAL: Genc8SpeedPosture.PAUSE,
        CiboRegimePosture.RECOVERY: Genc8SpeedPosture.DEFENSIVE,
        CiboRegimePosture.DEFENSIVE: Genc8SpeedPosture.DEFENSIVE,
        CiboRegimePosture.WATCH: Genc8SpeedPosture.CAUTIOUS,
        CiboRegimePosture.STABLE: Genc8SpeedPosture.ACCELERATED,
    }[posture]


def _provider_ceiling(
    condition: ProviderCondition,
) -> Genc8SpeedPosture:
    return {
        ProviderCondition.UNAVAILABLE: Genc8SpeedPosture.PAUSE,
        ProviderCondition.DEGRADED: Genc8SpeedPosture.DEFENSIVE,
        ProviderCondition.HEALTHY: Genc8SpeedPosture.ACCELERATED,
    }[condition]


def _severity_ceiling(severity: Genc8Severity) -> Genc8SpeedPosture:
    return {
        Genc8Severity.UNKNOWN: Genc8SpeedPosture.PAUSE,
        Genc8Severity.CRITICAL: Genc8SpeedPosture.PAUSE,
        Genc8Severity.ADVERSE: Genc8SpeedPosture.DEFENSIVE,
        Genc8Severity.WATCH: Genc8SpeedPosture.CAUTIOUS,
        Genc8Severity.BENIGN: Genc8SpeedPosture.ACCELERATED,
    }[severity]
