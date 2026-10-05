"""Bridge Native MAX cognitive scenarios into GEN-C11 world paths.

The bridge is intentionally evidence-conservative.  Native MAX already creates
BASE, ADVERSE, EXTREME and REGIME_CHANGE scenarios.  This module preserves
those scenario identities for MPC without inventing probabilities, realized
outcomes or numerical capacity shocks that the cognitive episode did not prove.
"""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta

from qore.infrastructure.cibo_capital_digital_twin import (
    Genc10WorldKind,
    Genc10WorldScenario,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboRegimePosture
from qore.infrastructure.cibo_cognitive_scenarios import ScenarioFamily
from qore.infrastructure.cibo_full_economic_digital_twin import (
    CiboObservedEconomicTwin,
)
from qore.infrastructure.cibo_multi_period_capital_mpc import (
    Genc11KnownOptionSchedule,
    Genc11WorldPath,
    Genc11WorldStep,
)
from qore.infrastructure.cibo_native_max_cognitive_episode import (
    CiboNativeMaxCognitiveEpisode,
)


_FAMILY_WORLD = {
    ScenarioFamily.BASE: (
        Genc10WorldKind.BALANCED,
        CiboRegimePosture.STABLE,
    ),
    ScenarioFamily.ADVERSE: (
        Genc10WorldKind.DEFENSIVE,
        CiboRegimePosture.DEFENSIVE,
    ),
    ScenarioFamily.EXTREME: (
        Genc10WorldKind.CRISIS,
        CiboRegimePosture.HALT_NEW_CAPITAL,
    ),
    ScenarioFamily.REGIME_CHANGE: (
        Genc10WorldKind.OPPORTUNITY_SCARCITY,
        CiboRegimePosture.WATCH,
    ),
}


def _sha(*values: object) -> str:
    raw = json.dumps(
        values,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_native_max_mpc_inputs(
    *,
    episode: CiboNativeMaxCognitiveEpisode,
    twin: CiboObservedEconomicTwin,
) -> tuple[
    tuple[Genc11WorldPath, ...],
    tuple[Genc11KnownOptionSchedule, ...],
]:
    """Translate the native cognitive scenario set into replay-safe MPC inputs."""

    if not isinstance(episode, CiboNativeMaxCognitiveEpisode):
        raise CiboCapitalManagementError(
            "native MAX MPC bridge requires canonical cognitive episode"
        )
    if not isinstance(twin, CiboObservedEconomicTwin):
        raise CiboCapitalManagementError(
            "native MAX MPC bridge requires Full Economic Twin"
        )
    episode.__post_init__()
    if not twin.opportunities:
        raise CiboCapitalManagementError(
            "native MAX MPC bridge requires current known opportunities"
        )
    families = tuple(item.family for item in episode.scenarios)
    expected = tuple(ScenarioFamily)
    if len(families) != len(set(families)) or set(families) != set(expected):
        raise CiboCapitalManagementError(
            "native MAX MPC bridge requires exact four scenario families"
        )
    if (
        episode.external_ai_call_count != 0
        or episode.external_reasoning_provider_used
    ):
        raise CiboCapitalManagementError(
            "native MAX MPC bridge forbids external reasoning"
        )

    first_at = twin.captured_at
    latest_known_action = max(
        item.earliest_action_at for item in twin.opportunities
    )
    second_at = max(
        first_at + timedelta(seconds=1),
        latest_known_action,
    )
    if second_at <= first_at:
        raise CiboCapitalManagementError(
            "native MAX MPC bridge horizon must advance"
        )
    step_times = (first_at, second_at)
    option_ids = tuple(sorted(item.option_id for item in twin.opportunities))

    paths: list[Genc11WorldPath] = []
    for cognitive in sorted(
        episode.scenarios,
        key=lambda item: item.family.value,
    ):
        world_kind, posture = _FAMILY_WORLD[cognitive.family]
        steps = tuple(
            Genc11WorldStep(
                step_index=index,
                projected_at=at,
                posture=posture,
                scenario=Genc10WorldScenario(
                    scenario_id=(
                        "native-max:"
                        + cognitive.family.value
                        + f":step-{index}"
                    ),
                    kind=world_kind,
                    declared_at=first_at,
                    scenario_evidence_sha256=_sha(
                        "native-max-scenario",
                        cognitive.fingerprint.value,
                        index,
                    ),
                    transition_uncertainty_evidence_sha256=_sha(
                        "native-max-uncertainty",
                        cognitive.uncertainty.logical_values(),
                        index,
                    ),
                    flows=(),
                    stop_risk_capacity_delta_usd=0,
                    stop_risk_usage_delta_usd=0,
                    margin_capacity_delta_usd=0,
                    margin_usage_delta_usd=0,
                    surviving_known_option_ids=option_ids,
                    hypothetical_new_option_count=0,
                    provider_constraints_changed=False,
                    uncertainty_calibrated=False,
                    market_probability_claimed=False,
                    actual_future_outcome_used=False,
                    productive_authority=False,
                ),
            )
            for index, at in enumerate(step_times, start=1)
        )
        paths.append(
            Genc11WorldPath(
                path_id="native-max:" + cognitive.family.value,
                world_kind=world_kind,
                steps=steps,
                factor_interaction_evidence_sha256=_sha(
                    "native-max-factor-interaction",
                    cognitive.fingerprint.value,
                    episode.causal_claim.claim_id,
                ),
                optionality_evidence_sha256=_sha(
                    "native-max-optionality",
                    cognitive.fingerprint.value,
                    episode.metacognitive_audit.audit_id,
                ),
                reserve_need_evidence_sha256=_sha(
                    "native-max-reserve",
                    cognitive.fingerprint.value,
                    episode.uncertainty.logical_values(),
                ),
                market_probability_claimed=False,
                future_outcome_used=False,
            )
        )

    schedules: list[Genc11KnownOptionSchedule] = []
    for opportunity in sorted(
        twin.opportunities,
        key=lambda item: item.option_id,
    ):
        decision_step = next(
            (
                index
                for index, at in enumerate(step_times, start=1)
                if at >= opportunity.earliest_action_at
            ),
            None,
        )
        if decision_step is None:
            raise CiboCapitalManagementError(
                "native MAX MPC bridge option lies outside causal horizon"
            )
        schedules.append(
            Genc11KnownOptionSchedule(
                option_id=opportunity.option_id,
                decision_step=decision_step,
                schedule_evidence_sha256=_sha(
                    "native-max-option-schedule",
                    opportunity.option_id,
                    opportunity.known_at,
                    opportunity.earliest_action_at,
                    opportunity.expires_at,
                ),
            )
        )

    return tuple(paths), tuple(schedules)
