"""Deterministic, pre-registration-only hypothesis register for the first cohort.

The register converts observed cross-market diagnostic signals into falsifiable
research proposals.  It does not modify methodologies or execution semantics,
and it marks every input OOS lineage as consumed for research.  Any later
variant must carry a new identity and prove itself on a fresh unseen holdout.
"""

from __future__ import annotations

import json
import re
import sys
from hashlib import sha256
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.first_cohort_failure_analysis import (
    FirstCohortFailureAnalysisError,
)

_SCHEMA = "qore.trader_lab.first_cohort_hypothesis_register.v1"
_FAILURE_SCHEMA = "qore.trader_lab.first_cohort_failure_analysis_aggregate.v1"
_CHARACTERIZATION_SCHEMA = (
    "qore.trader_lab.first_cohort_characterization_aggregate.v1"
)
_MULTI_SCHEMA = "qore.trader_lab.first_cohort_multi_pair_walk_forward.v1"
_CODES = ("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")

_MECHANISMS: dict[str, tuple[str, str, str, bool, bool]] = {
    "sparse_activity": (
        "Signal preconditions may suppress too many legitimate opportunities.",
        "signal_precondition_review",
        "Increase powered setup count without making fresh-holdout expectancy negative.",
        True,
        False,
    ),
    "poor_fill_conversion": (
        "LIMIT geometry and the frozen three-bar validity window may reject valid setups.",
        "versioned_execution_model_experiment",
        "Improve fill conversion while preserving or improving fresh-holdout expectancy.",
        False,
        True,
    ),
    "negative_expectancy": (
        "The current signal and payoff geometry do not produce positive average payoff.",
        "signal_or_geometry_methodology_change",
        "Produce positive expectancy with policy-compliant sample size on fresh evidence.",
        True,
        False,
    ),
    "low_hit_rate": (
        "The setup definition may not discriminate sufficiently between valid reversals.",
        "context_or_confirmation_methodology_change",
        "Raise hit rate without creating a brittle optimum or underpowered sample.",
        True,
        False,
    ),
    "parameter_instability": (
        "Observed performance may be concentrated at an isolated parameter value.",
        "parameter_plateau_methodology_review",
        "Create a positive neighboring plateau that generalizes under stress.",
        True,
        False,
    ),
    "oos_collapse": (
        "In-sample qualification may not generalize across time.",
        "generalization_methodology_review",
        "Retain positive expectancy across pre-registered folds and a fresh final holdout.",
        True,
        False,
    ),
    "stress_fragility": (
        "The apparent edge may be smaller than plausible execution costs.",
        "cost_robustness_methodology_review",
        "Remain policy-positive under the same or stricter pre-registered stress.",
        True,
        False,
    ),
    "exit_stop_dominance": (
        "Invalidation geometry or entry quality may cause excessive stop exits.",
        "stop_entry_geometry_methodology_change",
        "Reduce stop dominance without merely widening risk or lowering thresholds.",
        True,
        False,
    ),
    "direction_asymmetry": (
        "One direction may require distinct past-only context rather than deletion post hoc.",
        "directional_context_methodology_review",
        "Reproduce the asymmetry and improve both pooled and weak-side fresh-holdout results.",
        True,
        False,
    ),
    "regime_dependency": (
        "Edge may depend on a past-only trend or volatility state.",
        "past_only_regime_methodology_review",
        "Reproduce the regime split and improve weak-regime behavior on fresh evidence.",
        True,
        False,
    ),
    "instrument_dependency": (
        "Methodology assumptions may transfer unevenly across instrument microstructure.",
        "instrument_transferability_review",
        "Reproduce cross-instrument differences without selecting instruments from the "
        "consumed OOS.",
        True,
        False,
    ),
    "geometry_problem": (
        "Stop, target, or entry distances may be mismatched to observed price paths.",
        "risk_reward_geometry_methodology_change",
        "Improve risk-normalized excursions and expectancy without increasing tail risk.",
        True,
        False,
    ),
}


def _object(value: object, *, name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise FirstCohortFailureAnalysisError(f"{name} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, *, name: str) -> list[object]:
    if type(value) is not list:
        raise FirstCohortFailureAnalysisError(f"{name} must be an array")
    return cast(list[object], value)


def _text(value: object, *, name: str) -> str:
    if type(value) is not str or not value:
        raise FirstCohortFailureAnalysisError(f"{name} must be non-empty text")
    return value


def _integer(value: object, *, name: str) -> int:
    if type(value) is not int or value < 0:
        raise FirstCohortFailureAnalysisError(f"{name} must be a non-negative int")
    return value


def _read(path: Path, *, schema: str, name: str) -> dict[str, object]:
    try:
        raw = path.read_bytes()
        decoded: object = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FirstCohortFailureAnalysisError(f"cannot read {name}") from error
    payload = _object(decoded, name=name)
    if _text(payload.get("schema"), name=f"{name} schema") != schema:
        raise FirstCohortFailureAnalysisError(f"unsupported {name} schema")
    return payload


def _rows(payload: dict[str, object], *, name: str) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for value in _array(payload.get("results"), name=f"{name} results"):
        row = _object(value, name=f"{name} result")
        code = _text(row.get("trader_code"), name=f"{name} trader_code")
        if code in result:
            raise FirstCohortFailureAnalysisError(f"duplicate {name} Trader")
        result[code] = row
    if tuple(result) != _CODES:
        raise FirstCohortFailureAnalysisError(f"{name} cohort identity/order changed")
    return result


def _default_profile(row: dict[str, object]) -> dict[str, object]:
    defaults = [
        profile
        for value in _array(row.get("profiles"), name="characterization profiles")
        if (
            profile := _object(value, name="characterization profile")
        ).get("profile")
        == "production-default"
    ]
    if len(defaults) != 1:
        raise FirstCohortFailureAnalysisError(
            "Trader requires one aggregate production-default profile"
        )
    return defaults[0]


def _input_digest(paths: tuple[Path, ...]) -> str:
    component_digests = [sha256(path.read_bytes()).hexdigest() for path in paths]
    canonical = json.dumps(
        component_digests,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(canonical).hexdigest()


def run_hypothesis_register(
    failure_path: Path,
    characterization_path: Path,
    multi_pair_path: Path,
    *,
    software_sha: str,
) -> dict[str, object]:
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise FirstCohortFailureAnalysisError("software_sha must be a lowercase Git SHA")
    failure = _read(failure_path, schema=_FAILURE_SCHEMA, name="failure aggregate")
    characterization = _read(
        characterization_path,
        schema=_CHARACTERIZATION_SCHEMA,
        name="characterization aggregate",
    )
    multi = _read(multi_pair_path, schema=_MULTI_SCHEMA, name="multi-pair evidence")
    accounts = {
        _text(payload.get("account_fingerprint"), name="account fingerprint")
        for payload in (failure, characterization, multi)
    }
    if len(accounts) != 1:
        raise FirstCohortFailureAnalysisError("aggregate evidence account mismatch")
    software_shas = {
        _text(payload.get("software_sha"), name="aggregate software_sha")
        for payload in (failure, characterization, multi)
    }
    if software_shas != {software_sha}:
        raise FirstCohortFailureAnalysisError(
            "aggregate evidence must bind the requested exact software SHA"
        )
    failure_rows = _rows(failure, name="failure aggregate")
    characterization_rows = _rows(characterization, name="characterization aggregate")
    _rows(multi, name="multi-pair evidence")

    hypotheses: list[dict[str, object]] = []
    for code in _CODES:
        failure_row = failure_rows[code]
        counts = _object(
            failure_row.get("diagnostic_signal_counts"), name="diagnostic signal counts"
        )
        signal_counts = {
            signal: _integer(value, name=f"diagnostic count {signal}")
            for signal, value in counts.items()
            if signal in _MECHANISMS
        }
        default = _default_profile(characterization_rows[code])
        for value in _array(
            default.get("classification_labels"), name="classification labels"
        ):
            signal = _text(value, name="classification label")
            if signal in _MECHANISMS:
                signal_counts.setdefault(signal, 6)
        ordered = sorted(signal_counts.items(), key=lambda item: (-item[1], item[0]))
        parent_parameters = _object(
            default.get("parameters"), name="parent parameters"
        )
        methodology_identity = _object(
            default.get("methodology_identity"), name="methodology identity"
        )
        for rank, (signal, count) in enumerate(ordered, start=1):
            mechanism, change_family, prediction, methodology_change, execution_experiment = (
                _MECHANISMS[signal]
            )
            hypotheses.append(
                {
                    "hypothesis_id": f"HYP-{code.upper()}-{rank:03d}",
                    "trader": code,
                    "software_sha": software_sha,
                    "priority_rank_within_trader": rank,
                    "origin_methodology": methodology_identity,
                    "origin_configuration": {
                        "config_fingerprint": default.get("config_fingerprint"),
                        "parameters": parent_parameters,
                    },
                    "evidence_observed": {
                        "causal_signal": signal,
                        "instrument_occurrence_count": count,
                        "source_classification_labels": default.get(
                            "classification_labels"
                        ),
                    },
                    "causal_signal": signal,
                    "proposed_mechanism": mechanism,
                    "proposed_change_family": change_family,
                    "predicted_improvement": prediction,
                    "falsification_criterion": (
                        "A pre-registered variant fails to improve the predicted metric on a "
                        "fresh unseen holdout, loses policy robustness under stress, or reduces "
                        "sample below the pre-registered minimum."
                    ),
                    "required_fresh_holdout": True,
                    "new_evidence_required": (
                        "source-controlled variant on a pre-registered, previously unseen "
                        "dataset bound to its exact software and methodology fingerprints"
                    ),
                    "overfitting_risk": (
                        "high if the observed OOS influences tuning; controlled only by "
                        "pre-registration and a fresh unseen holdout"
                    ),
                    "forbidden_evidence_reuse": [
                        "current per-instrument OOS",
                        "current pooled OOS",
                        "current stressed OOS",
                    ],
                    "confidence": "high" if count >= 4 else "medium" if count >= 2 else "low",
                    "methodology_change_required": methodology_change,
                    "execution_model_experiment_required": execution_experiment,
                    "status": "pre_registration_required",
                    "parent_trader_version": _text(
                        methodology_identity.get("trader_version"),
                        name="parent trader version",
                    ),
                    "parent_methodology_fingerprint": _text(
                        methodology_identity.get("methodology_fingerprint"),
                        name="parent methodology fingerprint",
                    ),
                    "parent_config_fingerprint": _text(
                        default.get("config_fingerprint"),
                        name="parent config fingerprint",
                    ),
                    "parent_parameters": parent_parameters,
                }
            )

    source_paths = (failure_path, characterization_path, multi_pair_path)
    symbols = sorted(
        _text(value, name="symbol")
        for value in _array(failure.get("symbols"), name="symbols")
    )
    return {
        "schema": _SCHEMA,
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": software_sha,
        "account_fingerprint": next(iter(accounts)),
        "dataset_lineage": {
            "symbols": symbols,
            "aggregate_input_sha256": _input_digest(source_paths),
            "current_holdout_state": "consumed_for_research",
        },
        "research_cycle": [
            "observe",
            "diagnose",
            "hypothesize",
            "pre_register",
            "modify",
            "fresh_holdout",
            "stress",
            "monte_carlo",
            "authority",
        ],
        "variant_identity_policy": {
            "new_methodology_identity_required": True,
            "new_config_fingerprint_required": True,
            "hypothesis_id_binding_required": True,
            "parent_trader_version_required": True,
            "source_controlled_change_required": True,
            "evidence_lineage_required": True,
            "holdout_lineage_required": True,
        },
        "holdout_governance": {
            "current_oos_state": "consumed_for_research",
            "consumed_holdout_cannot_certify_modified_strategy": True,
            "fresh_previously_unseen_holdout_required": True,
            "software_sha_required": True,
            "exact_methodology_fingerprint_required": True,
        },
        "hypotheses": hypotheses,
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 4:
        print(
            "usage: python -m "
            "qore.infrastructure.trader_lab.first_cohort_hypothesis_register "
            "FAILURE_AGGREGATE CHARACTERIZATION_AGGREGATE MULTI_PAIR SOFTWARE_SHA",
            file=sys.stderr,
        )
        return 2
    try:
        payload = run_hypothesis_register(
            Path(arguments[0]),
            Path(arguments[1]),
            Path(arguments[2]),
            software_sha=arguments[3],
        )
    except FirstCohortFailureAnalysisError as error:
        print(f"hypothesis register failed: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
