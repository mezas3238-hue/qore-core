"""Causal adjudication program for VT-08 R3.8 Failure Forensics H01-H04.

This module opens a source-bound causal investigation from the frozen failure-
forensics artifact. It deliberately does not mutate the Trader, choose profitable
segments, tune on consumed evidence, or grant DEMO/LIVE authority.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import cast

from qore.kernel.errors import InfrastructureError

_SCHEMA = "qore.trader_lab.vt08_b01_causal_h01_h04.r3.8.v1"
_SOURCE_SCHEMA = "qore.trader_lab.vt08_b01_failure_forensics.r3.8.v1"
_FROZEN_BASELINE_RUN = 34693803930
_FROZEN_FORENSICS_RUN = 34696371933
_FROZEN_BASELINE_HEAD = "a5b9b5a80a55314f74cc1e3ef632803a91972c3b"
_FORBIDDEN_REUSE = "run-34693803930"
_EXPECTED_IDS = (
    "VT08-R3.8-FF-H01",
    "VT08-R3.8-FF-H02",
    "VT08-R3.8-FF-H03",
    "VT08-R3.8-FF-H04",
)


class Vt08B01CausalProgramError(InfrastructureError):
    __slots__ = ()


def _object(value: object, *, name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08B01CausalProgramError(f"{name} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, *, name: str) -> list[object]:
    if type(value) is not list:
        raise Vt08B01CausalProgramError(f"{name} must be an array")
    return cast(list[object], value)


def _text(value: object, *, name: str) -> str:
    if type(value) is not str or not value:
        raise Vt08B01CausalProgramError(f"{name} must be non-empty text")
    return value


def _boolean(value: object, *, name: str) -> bool:
    if type(value) is not bool:
        raise Vt08B01CausalProgramError(f"{name} must be bool")
    return value


def _integer(value: object, *, name: str) -> int:
    if type(value) is not int:
        raise Vt08B01CausalProgramError(f"{name} must be int")
    return value


def _load(path: Path) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08B01CausalProgramError(f"cannot read {path}") from error
    payload = _object(decoded, name="failure forensics artifact")
    if _text(payload.get("schema"), name="schema") != _SOURCE_SCHEMA:
        raise Vt08B01CausalProgramError("unexpected failure-forensics schema")
    if _text(payload.get("trader_code"), name="trader_code") != "vt-08":
        raise Vt08B01CausalProgramError("artifact must belong to VT-08")
    if (
        _integer(payload.get("baseline_run_id"), name="baseline_run_id")
        != _FROZEN_BASELINE_RUN
    ):
        raise Vt08B01CausalProgramError("unexpected frozen baseline run")
    if (
        _text(payload.get("baseline_head"), name="baseline_head")
        != _FROZEN_BASELINE_HEAD
    ):
        raise Vt08B01CausalProgramError("unexpected frozen baseline head")
    if not _boolean(payload.get("baseline_frozen"), name="baseline_frozen"):
        raise Vt08B01CausalProgramError("baseline must remain frozen")
    if not _boolean(
        payload.get("current_evidence_consumed"), name="current_evidence_consumed"
    ):
        raise Vt08B01CausalProgramError(
            "causal phase requires consumed research evidence"
        )
    if not _boolean(
        payload.get("independent_validation_reuse_prohibited"),
        name="independent_validation_reuse_prohibited",
    ):
        raise Vt08B01CausalProgramError(
            "independent-validation reuse must be prohibited"
        )
    if _boolean(payload.get("demo_eligible"), name="demo_eligible"):
        raise Vt08B01CausalProgramError(
            "causal program cannot start from DEMO authority"
        )
    return payload


def _hypotheses(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    items = _array(payload.get("hypothesis_register"), name="hypothesis_register")
    result: dict[str, dict[str, object]] = {}
    for raw in items:
        item = _object(raw, name="hypothesis")
        hypothesis_id = _text(item.get("id"), name="hypothesis.id")
        if hypothesis_id in result:
            raise Vt08B01CausalProgramError("duplicate hypothesis id")
        if (
            _text(item.get("forbidden_reuse"), name="forbidden_reuse")
            != _FORBIDDEN_REUSE
        ):
            raise Vt08B01CausalProgramError(
                "hypothesis lost forbidden-reuse governance"
            )
        if _text(item.get("status"), name="status") != "research_hypothesis_only":
            raise Vt08B01CausalProgramError(
                "hypothesis was promoted before causal adjudication"
            )
        result[hypothesis_id] = item
    if tuple(sorted(result)) != _EXPECTED_IDS:
        raise Vt08B01CausalProgramError("exact H01-H04 register is required")
    return result


def _track(
    *,
    hypothesis: dict[str, object],
    causal_question: str,
    source_boundary: tuple[str, ...],
    competing_mechanisms: tuple[str, ...],
    fresh_diagnostics: tuple[str, ...],
    falsification_gate: tuple[str, ...],
    prohibited_inference: tuple[str, ...],
) -> dict[str, object]:
    return {
        "hypothesis_id": _text(hypothesis.get("id"), name="hypothesis.id"),
        "family": _text(hypothesis.get("family"), name="hypothesis.family"),
        "status": "OPEN_CAUSAL_ADJUDICATION",
        "observed_evidence": hypothesis.get("evidence"),
        "causal_question": causal_question,
        "source_boundary": list(source_boundary),
        "competing_mechanisms": list(competing_mechanisms),
        "fresh_diagnostics": list(fresh_diagnostics),
        "falsification_gate": list(falsification_gate),
        "prohibited_inference": list(prohibited_inference),
        "forbidden_reuse": _FORBIDDEN_REUSE,
        "fresh_holdout_required": True,
        "methodology_mutation_authorized": False,
    }


def compile_vt08_b01_causal_program(path: Path) -> dict[str, object]:
    payload = _load(path)
    hypotheses = _hypotheses(payload)
    methodology_fingerprint = _text(
        payload.get("methodology_fingerprint"), name="methodology_fingerprint"
    )

    tracks = [
        _track(
            hypothesis=hypotheses["VT08-R3.8-FF-H01"],
            causal_question=(
                "Are stopped B01 trades primarily caused by incorrect/underspecified "
                "protected-swing geometry, by the source-authorized positional entry "
                "relationship to that swing, or by genuine structural invalidation "
                "after a valid setup?"
            ),
            source_boundary=(
                "protected swing must follow important-level interaction plus causal CISD",
                "R3.8 requires exactly one valid protected swing or abstention",
                "positional historical entry reference is the new H4 open",
                "protected-swing broker stop offset remains unresolved",
                "nearest/best retrospective protected swing is prohibited",
            ),
            competing_mechanisms=(
                "PS_PROVENANCE_OR_SELECTION_MISMATCH",
                "ENTRY_TO_PS_GEOMETRY_MISMATCH",
                "GENUINE_POST_ENTRY_STRUCTURAL_INVALIDATION",
                "UNRESOLVED_STOP_EXECUTION_OFFSET",
            ),
            fresh_diagnostics=(
                "pre-outcome PS provenance and candidate count",
                "CISD series start/open, confirmation close and confirmation latency",
                "entry-to-PS risk distance normalized by prior-H4 range",
                "sweep depth and post-CISD displacement known at decision time",
                "C2/C3 identity and important-level provenance",
                "MFE/MAE and stop-before-target path without hindsight feature selection",
            ),
            falsification_gate=(
                "pre-register one source-supported discriminator before fresh evidence",
                "run unchanged seven-market fresh holdout with identical data policy",
                "require reduced stop concentration plus non-degraded OOS and Stress",
                "reject causal claim if effect disappears or only survives retrospective slicing",
            ),
            prohibited_inference=(
                "do not widen stops because stopped trades lost",
                "do not choose an alternate PS using later price path",
                "do not invent numeric shallow/large thresholds from the consumed run",
            ),
        ),
        _track(
            hypothesis=hypotheses["VT08-R3.8-FF-H02"],
            causal_question=(
                "Is the cross-market dispersion a reproducible methodology-by-instrument "
                "interaction, or sampling/regime variation in one consumed campaign?"
            ),
            source_boundary=(
                "all seven Forex markets are authorized by the frozen Forex source family",
                "the source rulebook does not authorize selecting EURUSD/GBPUSD from P&L",
                "market promotion requires fresh evidence, not the frozen ranking",
            ),
            competing_mechanisms=(
                "TRUE_INSTRUMENT_DEPENDENCY",
                "VOLATILITY_OR_MICROSTRUCTURE_REGIME_DEPENDENCY",
                "SAMPLE_VARIATION",
                "DATA_QUALITY_OR_SESSION_CONSTRUCTION_INTERACTION",
            ),
            fresh_diagnostics=(
                "same methodology fingerprint across all seven markets",
                "equal data completeness and source-day/H4 construction checks",
                "per-market OOS, Stress, stop share, geometry and regime distributions",
                "interaction effect estimated without dropping frozen-run losers",
            ),
            falsification_gate=(
                "repeat all seven markets on previously unseen dates",
                "require directionally consistent separation with OOS/Stress survival",
                "reject market specialization if the ranking is unstable on fresh evidence",
            ),
            prohibited_inference=(
                "do not whitelist EURUSD/GBPUSD from run 34693803930",
                "do not blacklist the five negative markets from consumed P&L",
                "do not claim source-level instrument exclusions without primary evidence",
            ),
        ),
        _track(
            hypothesis=hypotheses["VT08-R3.8-FF-H03"],
            causal_question=(
                "Does B01 have a source-coherent interaction with the 01/05/09 New-York "
                "H4 anchors, or is the observed 05:00 advantage sampling noise?"
            ),
            source_boundary=(
                "source-complete Forex timing is 01/05/09/13 New York",
                "Human Owner operational subset is 01/05/09 New York",
                "05:00 is not source-authorized as a privileged winner",
                "source-complete and Owner-subset profiles must remain separate",
            ),
            competing_mechanisms=(
                "TRUE_ANCHOR_REGIME_INTERACTION",
                "SESSION_VOLATILITY_INTERACTION",
                "ANCHOR_SAMPLE_VARIATION",
                "BIAS_OR_C2_COMPOSITION_DIFFERENCE_BY_ANCHOR",
            ),
            fresh_diagnostics=(
                "pre-registered 01/05/09 Owner-subset stratification",
                "separate source-complete 13:00 diagnostic with no statistic pooling",
                "bias case, C2/C3 class, PS geometry and volatility by anchor",
                "OOS/Stress survival by anchor without choosing the best after results",
            ),
            falsification_gate=(
                "retain all three Owner anchors in fresh evidence collection",
                "require the 05:00 interaction to reproduce with mechanism-consistent diagnostics",
                "reject anchor specialization if advantage is unstable or stress-fragile",
            ),
            prohibited_inference=(
                "do not change the Trader to 05:00-only from the frozen campaign",
                "do not merge 13:00 source-complete results into Owner-subset economics",
                "do not invent a session filter from weekday/hour P&L",
            ),
        ),
        _track(
            hypothesis=hypotheses["VT08-R3.8-FF-H04"],
            causal_question=(
                "How much of measured expectancy is caused by the QORE H4-boundary "
                "containment rather than source-resolved trade lifecycle semantics?"
            ),
            source_boundary=(
                "R3.8 labels close-at-next-H4-boundary as an operational containment",
                "source-explicit filled-position behavior across an H4 boundary remains unresolved",
                "2R replay target and no-stop-offset are also containments, not universal source rules",
            ),
            competing_mechanisms=(
                "CONTAINMENT_TRUNCATES_VALID_POST_H4_CONTINUATION",
                "CONTAINMENT_PREVENTS_LARGER_ADVERSE_EXCURSION",
                "CONTAINMENT_IS_ECONOMICALLY_SECONDARY_TO_ENTRY_GEOMETRY",
            ),
            fresh_diagnostics=(
                "counterfactual path logging beyond H4 boundary without changing executed replay",
                "time-to-MFE, time-to-MAE and unresolved-at-boundary state",
                "source-adjudicated lifecycle alternative encoded before fresh outcome access",
                "paired diagnostic comparison with identical entries and PS geometry",
            ),
            falsification_gate=(
                "source-adjudicate lifecycle before selecting any alternative",
                "pre-register comparison on unseen evidence",
                "reject lifecycle causality if paired fresh results show no material robust effect",
            ),
            prohibited_inference=(
                "do not extend holds because containment exits were profitable in the frozen run",
                "do not pick the best lifecycle from run 34693803930",
                "do not relabel QORE containment as TTrades source authority",
            ),
        ),
    ]

    return {
        "schema": _SCHEMA,
        "trader_code": "vt-08",
        "bundle_id": "B01_SOURCE_FAITHFUL_HISTORICAL_REPLAY_V1",
        "parent_failure_forensics_run_id": _FROZEN_FORENSICS_RUN,
        "baseline_run_id": _FROZEN_BASELINE_RUN,
        "baseline_head": _FROZEN_BASELINE_HEAD,
        "methodology_fingerprint": methodology_fingerprint,
        "research_only": True,
        "causal_phase_open": True,
        "source_adjudication_required": True,
        "current_evidence_consumed": True,
        "independent_validation_reuse_prohibited": True,
        "forbidden_reuse": _FORBIDDEN_REUSE,
        "tracks": tracks,
        "global_preregistration": {
            "fresh_holdout": "previously unseen dates collected only after source adjudication",
            "markets": [
                "AUDJPY",
                "AUDUSD",
                "EURUSD",
                "GBPJPY",
                "GBPUSD",
                "USDCAD",
                "USDJPY",
            ],
            "owner_anchors_ny": [1, 5, 9],
            "selection_rule": "no market/hour/weekday selection from consumed evidence",
            "quality_gate": "ruff + mypy + focused causal tests + full pytest before economics",
            "success_requires": "mechanism-consistent fresh OOS improvement with Stress survival",
        },
        "methodology_mutation_authorized": False,
        "demo_eligible": False,
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1:
        print(
            "usage: vt08_b01_causal_h01_h04_r3_8 <failure-forensics.json>",
            file=sys.stderr,
        )
        return 2
    try:
        payload = compile_vt08_b01_causal_program(Path(arguments[0]))
    except Vt08B01CausalProgramError as error:
        print(f"VT-08 causal program failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
