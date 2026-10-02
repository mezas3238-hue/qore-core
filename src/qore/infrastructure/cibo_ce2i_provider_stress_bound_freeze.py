"""Core-certification provider stress-bound freeze for CIBO.

Empirical provider execution remains the stronger deployment lane.  When the
authorized DEMO account does not contain enough executions to calibrate
slippage, CIBO Core may freeze the already-predeclared Phase20C adverse matrix
as a conservative pre-holdout uncertainty bound.

This lane never claims empirical slippage, historical provider economics, or
deployment readiness for cTrader DEMO or FundedNext.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_provider_stress import (
    Phase20ProviderStressScenario,
    phase20c_synthetic_predeclared_stress_scenarios,
)
from qore.infrastructure.cibo_ce2i_provider_economics_evidence import (
    CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS,
)
from qore.infrastructure.cibo_ce2i_provider_economics_provenance import (
    provider_economics_provenance_sha256,
)

PROVIDER_STRESS_BOUND_FREEZE_ID = "CIBO_PROVIDER_ECONOMICS_STRESS_BOUND_FREEZE_V1"
PROVIDER_STRESS_BOUND_POLICY_ID = (
    "CIBO_PROVIDER_ECONOMICS_STRESS_BOUND_ALTERNATIVE_V1"
)
EMPIRICAL_INVENTORY_RUN_ID = 36871397260
EMPIRICAL_INVENTORY_ARTIFACT_ID = 11166344413
EMPIRICAL_INVENTORY_ARTIFACT_DIGEST = (
    "sha256:56e8752ea87595ecebd5d8f255b50f5e7b7aea1e82927dd36f320b4ec5b8e47f"
)
EMPIRICAL_INVENTORY_HEAD_SHA = "40281158a01e20eac99dd52a748aceff510eef43"


@dataclass(frozen=True, slots=True)
class CiboProviderStressBoundFreeze:
    freeze_id: str
    policy_id: str
    provider_key: str
    frozen_at: datetime
    current_provider_terms_provenance_sha256: str
    empirical_inventory_run_id: int
    empirical_inventory_artifact_id: int
    empirical_inventory_artifact_digest: str
    empirical_inventory_head_sha: str
    account_entry_deals_found: int
    market_entry_deals_found: int
    qore_deals_found: int
    empirical_population_sufficient: bool
    empirical_slippage_claimed: bool
    scenario_ids: tuple[str, ...]
    scenario_matrix_sha256: str
    scenarios_predeclared: bool
    scenarios_non_improving: bool
    outcome_tuned: bool
    policy_pass_tuned: bool
    synthetic_counterfactual: bool
    historical_provider_economics_claimed: bool
    holdout_outcomes_used: bool
    core_pre_holdout_ready: bool
    provider_deployment_ready: bool
    core_blockers: tuple[str, ...]
    deployment_blockers: tuple[str, ...]
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.freeze_id != PROVIDER_STRESS_BOUND_FREEZE_ID:
            raise CiboCapitalManagementError(
                "provider stress-bound freeze identity drift"
            )
        if self.policy_id != PROVIDER_STRESS_BOUND_POLICY_ID:
            raise CiboCapitalManagementError(
                "provider stress-bound policy identity drift"
            )
        if self.provider_key != "ctrader-demo":
            raise CiboCapitalManagementError(
                "provider stress-bound provider drift"
            )
        if self.frozen_at.tzinfo is None or self.frozen_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "provider stress-bound frozen_at must be timezone-aware"
            )
        if self.current_provider_terms_provenance_sha256 != (
            provider_economics_provenance_sha256()
        ):
            raise CiboCapitalManagementError(
                "provider stress-bound current-terms provenance drift"
            )
        if (
            self.empirical_inventory_run_id != EMPIRICAL_INVENTORY_RUN_ID
            or self.empirical_inventory_artifact_id
            != EMPIRICAL_INVENTORY_ARTIFACT_ID
            or self.empirical_inventory_artifact_digest
            != EMPIRICAL_INVENTORY_ARTIFACT_DIGEST
            or self.empirical_inventory_head_sha
            != EMPIRICAL_INVENTORY_HEAD_SHA
        ):
            raise CiboCapitalManagementError(
                "provider stress-bound empirical inventory lineage drift"
            )
        for name in (
            "account_entry_deals_found",
            "market_entry_deals_found",
            "qore_deals_found",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"provider stress-bound {name} must be non-negative int"
                )
        expected_scenarios = phase20c_synthetic_predeclared_stress_scenarios()
        expected_ids = tuple(item.scenario_id for item in expected_scenarios)
        if self.scenario_ids != expected_ids:
            raise CiboCapitalManagementError(
                "provider stress-bound scenario identity drift"
            )
        if self.scenario_matrix_sha256 != provider_stress_matrix_sha256():
            raise CiboCapitalManagementError(
                "provider stress-bound scenario digest drift"
            )
        if (
            self.empirical_population_sufficient
            or self.empirical_slippage_claimed
            or not self.scenarios_predeclared
            or not self.scenarios_non_improving
            or self.outcome_tuned
            or self.policy_pass_tuned
            or not self.synthetic_counterfactual
            or self.historical_provider_economics_claimed
            or self.holdout_outcomes_used
            or not self.core_pre_holdout_ready
            or self.provider_deployment_ready
            or self.core_blockers
            or not self.deployment_blockers
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "provider stress-bound governance/readiness drift"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(
            _canonical(asdict(self)),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_provider_stress_bound_freeze(
    *,
    empirical_inventory: dict[str, Any],
    frozen_at: datetime | None = None,
) -> CiboProviderStressBoundFreeze:
    """Seal the predeclared stress lane after proving empirical insufficiency."""

    evidence = CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS
    if not evidence.provider_terms_ready:
        raise CiboCapitalManagementError(
            "provider stress-bound requires frozen current provider terms"
        )
    if (
        evidence.historical_exact_claimed
        or evidence.holdout_outcomes_used
        or evidence.target_aware
        or evidence.broker_mutation_performed
    ):
        raise CiboCapitalManagementError(
            "provider stress-bound current evidence is contaminated"
        )

    if empirical_inventory.get("schema") != (
        "qore.cibo.ctrader_demo.empirical_slippage.v1"
    ):
        raise CiboCapitalManagementError(
            "provider stress-bound empirical inventory schema mismatch"
        )
    if empirical_inventory.get("status") != "EMPIRICAL_SLIPPAGE_NOT_READY":
        raise CiboCapitalManagementError(
            "provider stress-bound alternative requires an insufficient empirical lane"
        )
    for key, expected in (
        ("provider_key", "ctrader-demo"),
        ("environment", "demo"),
        ("empirical_slippage_calibrated", False),
        ("execution_model_ready", False),
        ("broker_mutation_performed", False),
        ("holdout_outcomes_used", False),
        ("historical_2017_exact_claimed", False),
        ("target_aware", False),
        ("productive_authority", False),
    ):
        if empirical_inventory.get(key) != expected:
            raise CiboCapitalManagementError(
                f"provider stress-bound empirical inventory drift: {key}"
            )

    account_entries = _int_field(
        empirical_inventory, "account_entry_deals_found"
    )
    market_entries = _int_field(
        empirical_inventory, "market_entry_deals_found"
    )
    qore_deals = _int_field(empirical_inventory, "qore_deals_found")
    if not (account_entries == 3 and market_entries == 1 and qore_deals == 1):
        raise CiboCapitalManagementError(
            "provider stress-bound immutable empirical inventory count drift"
        )

    scenarios = phase20c_synthetic_predeclared_stress_scenarios()
    _validate_predeclared_scenarios(scenarios)
    observed_at = datetime.fromisoformat(evidence.observed_at)
    frozen = frozen_at or datetime.now(UTC)
    if frozen.tzinfo is None or frozen.utcoffset() is None:
        raise CiboCapitalManagementError(
            "provider stress-bound frozen_at must be timezone-aware"
        )
    if frozen < observed_at:
        raise CiboCapitalManagementError(
            "provider stress-bound cannot predate provider observation"
        )

    return CiboProviderStressBoundFreeze(
        freeze_id=PROVIDER_STRESS_BOUND_FREEZE_ID,
        policy_id=PROVIDER_STRESS_BOUND_POLICY_ID,
        provider_key=evidence.provider_key,
        frozen_at=frozen,
        current_provider_terms_provenance_sha256=(
            provider_economics_provenance_sha256()
        ),
        empirical_inventory_run_id=EMPIRICAL_INVENTORY_RUN_ID,
        empirical_inventory_artifact_id=EMPIRICAL_INVENTORY_ARTIFACT_ID,
        empirical_inventory_artifact_digest=(
            EMPIRICAL_INVENTORY_ARTIFACT_DIGEST
        ),
        empirical_inventory_head_sha=EMPIRICAL_INVENTORY_HEAD_SHA,
        account_entry_deals_found=account_entries,
        market_entry_deals_found=market_entries,
        qore_deals_found=qore_deals,
        empirical_population_sufficient=False,
        empirical_slippage_claimed=False,
        scenario_ids=tuple(item.scenario_id for item in scenarios),
        scenario_matrix_sha256=provider_stress_matrix_sha256(),
        scenarios_predeclared=True,
        scenarios_non_improving=True,
        outcome_tuned=False,
        policy_pass_tuned=False,
        synthetic_counterfactual=True,
        historical_provider_economics_claimed=False,
        holdout_outcomes_used=False,
        core_pre_holdout_ready=True,
        provider_deployment_ready=False,
        core_blockers=(),
        deployment_blockers=(
            "PROVIDER_DEPLOYMENT_EMPIRICAL_SLIPPAGE_REQUIRED",
            "PROVIDER_DEPLOYMENT_EXECUTION_MODEL_REQUIRED",
        ),
        productive_authority=False,
    )


def provider_stress_matrix_sha256() -> str:
    scenarios = phase20c_synthetic_predeclared_stress_scenarios()
    payload = tuple(_scenario_payload(item) for item in scenarios)
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _validate_predeclared_scenarios(
    scenarios: tuple[Phase20ProviderStressScenario, ...],
) -> None:
    ids = tuple(item.scenario_id for item in scenarios)
    required = {
        "CF_BASELINE_CURRENT_SNAPSHOT",
        "CF_SPREAD_X2",
        "CF_COMMISSION_X2",
        "CF_SLIPPAGE_FLOOR_4",
        "CF_MARGIN_X2",
        "CF_EXECUTION_DELAY_2000MS",
        "CF_LIQUIDITY_UNAVAILABLE",
        "CF_MINIMUM_VOLUME_CLIFF",
        "CF_COMBINED_ADVERSE",
    }
    if len(scenarios) != 9 or set(ids) != required:
        raise CiboCapitalManagementError(
            "provider stress-bound frozen matrix membership drift"
        )
    if any(
        item.historical_provider_economics_claimed
        or item.outcome_tuned
        or item.policy_pass_tuned
        for item in scenarios
    ):
        raise CiboCapitalManagementError(
            "provider stress-bound matrix is outcome/provider contaminated"
        )

    baseline = scenarios[0]
    if baseline.scenario_id != "CF_BASELINE_CURRENT_SNAPSHOT":
        raise CiboCapitalManagementError(
            "provider stress-bound baseline must be first"
        )
    for item in scenarios[1:]:
        if (
            item.spread_multiplier < baseline.spread_multiplier
            or item.commission_multiplier < baseline.commission_multiplier
            or item.minimum_slippage_reserve_per_volume_usd
            < baseline.minimum_slippage_reserve_per_volume_usd
            or item.margin_multiplier < baseline.margin_multiplier
            or item.broker_risk_buffer < baseline.broker_risk_buffer
        ):
            raise CiboCapitalManagementError(
                "provider stress-bound adverse matrix improved economics"
            )


def _scenario_payload(
    scenario: Phase20ProviderStressScenario,
) -> dict[str, object]:
    payload = asdict(scenario)
    return _canonical(payload)  # type: ignore[return-value]


def _int_field(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise CiboCapitalManagementError(
            f"provider stress-bound empirical field invalid: {key}"
        )
    return value


def _canonical(value: object) -> object:
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
