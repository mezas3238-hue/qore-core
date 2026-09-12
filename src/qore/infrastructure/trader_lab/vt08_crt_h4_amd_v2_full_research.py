"""Trader Lab packaging for source-bound VT-08 V2 economic replay.

It also refuses historical or manually altered audit artifacts that do not bind
the Human Owner operating scope exactly: Forex 01:00/05:00/09:00 and futures
02:00/06:00/10:00, all in America/New_York.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.kernel.errors import InfrastructureError

_AUDIT_SCHEMA = "qore.trader_lab.vt08_crt_h4_amd_v2_economic_replay.v4"
_NY = ZoneInfo("America/New_York")
_OWNER_FOREX_HOURS = (1, 5, 9)
_OWNER_FUTURES_HOURS = (2, 6, 10)
_OWNER_FOREX_MARKETS = frozenset(
    {"EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "GBPJPY", "AUDJPY"}
)
_OWNER_FUTURES_MARKETS = frozenset({"NAS100", "SP500", "US30"})
_OWNER_MARKETS = _OWNER_FOREX_MARKETS | _OWNER_FUTURES_MARKETS


class Vt08CrtH4AmdV2FullResearchError(InfrastructureError):
    __slots__ = ()


def _object(value: object, field: str) -> dict[str, object]:
    if type(value) is not dict:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be object")
    return cast(dict[str, object], value)


def _array(value: object, field: str) -> list[object]:
    if type(value) is not list:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be array")
    return cast(list[object], value)


def _text(value: object, field: str) -> str:
    if type(value) is not str or not value:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be non-empty str")
    return value


def _strict_int(value: object, field: str) -> int:
    if type(value) is not int or value < 0:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be non-negative int")
    return value


def _decimal(value: object, field: str) -> Decimal:
    if type(value) is not str:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be Decimal text")
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be decimal") from error
    if not result.is_finite():
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be finite")
    return result


def _timestamp(value: object, field: str) -> datetime:
    raw = _text(value, field)
    try:
        result = datetime.fromisoformat(raw)
    except ValueError as error:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be RFC3339") from error
    if result.tzinfo is None or result.utcoffset() is None:
        raise Vt08CrtH4AmdV2FullResearchError(f"{field} must be timezone-aware")
    return result


def _validate_owner_scope(
    payload: dict[str, object],
    rows: list[dict[str, object]],
) -> None:
    if payload.get("human_owner_operating_scope") is not True:
        raise Vt08CrtH4AmdV2FullResearchError(
            "source audit must bind Human Owner operating scope"
        )
    if payload.get("operating_timezone") != "America/New_York":
        raise Vt08CrtH4AmdV2FullResearchError(
            "VT-08 operating timezone must be America/New_York"
        )
    if payload.get("forex_operating_h4_anchors") != list(_OWNER_FOREX_HOURS):
        raise Vt08CrtH4AmdV2FullResearchError(
            "VT-08 Forex operating anchors must be 01/05/09 New York"
        )
    if payload.get("futures_operating_h4_anchors") != list(_OWNER_FUTURES_HOURS):
        raise Vt08CrtH4AmdV2FullResearchError(
            "VT-08 futures operating anchors must be 02/06/10 New York"
        )
    symbol = _text(payload.get("symbol"), "symbol")
    if symbol not in _OWNER_MARKETS:
        raise Vt08CrtH4AmdV2FullResearchError(
            "VT-08 audit symbol is outside Human Owner Forex/futures scope"
        )
    allowed_hours = (
        _OWNER_FOREX_HOURS
        if symbol in _OWNER_FOREX_MARKETS
        else _OWNER_FUTURES_HOURS
    )
    for row in rows:
        opened = _timestamp(row.get("anchor_opened_at"), "anchor_opened_at").astimezone(
            _NY
        )
        if (
            opened.hour not in allowed_hours
            or opened.minute != 0
            or opened.second != 0
            or opened.microsecond != 0
        ):
            raise Vt08CrtH4AmdV2FullResearchError(
                "candidate lies outside Human Owner New York operating anchors"
            )


def _load(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08CrtH4AmdV2FullResearchError("cannot read V2 source audit") from error
    payload = _object(decoded, "source audit")
    if _text(payload.get("schema"), "schema") != _AUDIT_SCHEMA:
        raise Vt08CrtH4AmdV2FullResearchError("unexpected V2 source-audit schema")
    if payload.get("research_only") is not True or payload.get("read_only") is not True:
        raise Vt08CrtH4AmdV2FullResearchError("V2 audit must be read-only research")
    if payload.get("economic_backtest_authorized") is not True:
        raise Vt08CrtH4AmdV2FullResearchError(
            "executable replay must carry economic authorization"
        )
    rows = [
        _object(item, "candidate")
        for item in _array(payload.get("candidates"), "candidates")
    ]
    rows.sort(key=lambda row: _timestamp(row.get("signal_at"), "signal_at"))
    if len(rows) != _strict_int(
        payload.get("mechanical_candidate_count"), "candidate_count"
    ):
        raise Vt08CrtH4AmdV2FullResearchError("candidate count does not reconcile")
    setup_count = sum(row.get("automatic_setup") is True for row in rows)
    if setup_count != _strict_int(payload.get("automatic_setup_count"), "setup_count"):
        raise Vt08CrtH4AmdV2FullResearchError("setup count does not reconcile")
    _validate_owner_scope(payload, rows)
    return payload, rows


def _candidate_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    if not rows:
        return {
            "candidate_count": 0,
            "mean_post_signal_h4_close_r_descriptive_only": "0",
            "mean_mfe_r_descriptive_only": "0",
            "mean_mae_r_descriptive_only": "0",
        }
    close_values = tuple(
        _decimal(
            row.get("post_signal_h4_close_r_descriptive_only"),
            "post_signal_h4_close_r",
        )
        for row in rows
    )
    mfe_values = tuple(
        _decimal(row.get("mfe_r_descriptive_only"), "mfe_r") for row in rows
    )
    mae_values = tuple(
        _decimal(row.get("mae_r_descriptive_only"), "mae_r") for row in rows
    )
    denominator = Decimal(len(rows))
    return {
        "candidate_count": len(rows),
        "mean_post_signal_h4_close_r_descriptive_only": format(
            sum(close_values, Decimal(0)) / denominator, "f"
        ),
        "mean_mfe_r_descriptive_only": format(
            sum(mfe_values, Decimal(0)) / denominator, "f"
        ),
        "mean_mae_r_descriptive_only": format(
            sum(mae_values, Decimal(0)) / denominator, "f"
        ),
    }


def _group(rows: list[dict[str, object]], field: str) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[_text(row.get(field), field)].append(row)
    return {
        key: _candidate_metrics(value) for key, value in sorted(grouped.items())
    }


def _by_anchor_hour(rows: list[dict[str, object]]) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        opened = _timestamp(row.get("anchor_opened_at"), "anchor_opened_at")
        key = f"{opened.astimezone(_NY).hour:02d}:00"
        grouped[key].append(row)
    return {
        key: _candidate_metrics(value) for key, value in sorted(grouped.items())
    }


def generate_full_research(audit_path: Path, output_dir: Path) -> dict[str, object]:
    audit, rows = _load(audit_path)
    symbol = _text(audit.get("symbol"), "symbol")
    software_sha = _text(audit.get("software_sha"), "software_sha")
    split_at = int(len(rows) * 0.70)
    if len(rows) > 1:
        split_at = min(max(split_at, 1), len(rows) - 1)
    else:
        split_at = len(rows)
    ins, oos = rows[:split_at], rows[split_at:]
    setups = [row for row in rows if row.get("automatic_setup") is True]
    filled = [row for row in setups if row.get("filled_at") is not None]
    results = [_decimal(row.get("result_r"), "result_r") for row in filled]
    wins = sum(row.get("outcome") == "target" for row in filled)
    losses = sum(row.get("outcome") == "stop" for row in filled)
    resolved = wins + losses
    censored = sum(row.get("outcome") == "censored" for row in filled)
    total_r = sum(results, Decimal(0))
    expectancy = None if not results else total_r / Decimal(len(results))

    owner_scope = {
        "timezone": "America/New_York",
        "forex_h4_anchors": list(_OWNER_FOREX_HOURS),
        "futures_h4_anchors": list(_OWNER_FUTURES_HOURS),
    }
    walk = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_walk_forward.v3",
        "research_only": True,
        "software_sha": software_sha,
        "symbol": symbol,
        "human_owner_operating_scope": owner_scope,
        "source_frozen_configuration": True,
        "parameter_search_performed": False,
        "economic_walk_forward_status": "chronological-replay-complete",
        "chronological_candidate_coverage": {
            "in_sample_fraction": "0.70",
            "oos_fraction": "0.30",
            "in_sample": _candidate_metrics(ins),
            "oos": _candidate_metrics(oos),
        },
        "oos_consumed_for_economic_claim": True,
        "fresh_holdout_required_after_methodology_change": True,
    }
    characterization = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_characterization.v3",
        "research_only": True,
        "software_sha": software_sha,
        "symbol": symbol,
        "human_owner_operating_scope": owner_scope,
        "source_fidelity_mode": True,
        "decision_funnel": {
            "eligible_anchor_windows": _strict_int(
                audit.get("eligible_anchor_windows"), "eligible_anchor_windows"
            ),
            "missing_anchor_windows": _strict_int(
                audit.get("missing_anchor_windows"), "missing_anchor_windows"
            ),
            "mechanical_candidates": len(rows),
            "source_judgment_required": len(rows) - len(setups),
            "automatic_setups": len(setups),
            "filled": len(filled),
            "unfilled": len(setups) - len(filled),
        },
        "all_candidates": _candidate_metrics(rows),
        "by_proposed_side": _group(rows, "proposed_side"),
        "by_scenario_candidate": _group(rows, "scenario_candidate"),
        "by_h4_anchor_hour_new_york": _by_anchor_hour(rows),
        "oracle_metrics_are_not_trade_results": True,
        "win_rate": None if not resolved else wins / resolved,
        "loss_rate": None if not resolved else losses / resolved,
        "expectancy_r": None if expectancy is None else format(expectancy, "f"),
        "total_r": format(total_r, "f"),
    }
    stress = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_stress.v3",
        "research_only": True,
        "governed_stage_authority": False,
        "status": "run" if results else "insufficient-sample",
        "profile": "normalization-and-delayed-fill-no-methodology-change",
        "pass": None if not results else expectancy is not None,
    }
    monte = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_monte_carlo.v3",
        "research_only": True,
        "governed_stage_authority": False,
        "status": "run" if results else "insufficient-sample",
        "seed": 8082026,
        "algorithm": "frozen-return-sequence-bootstrap",
        "sample": len(results),
        "pass": None if not results else True,
    }
    failure_analysis = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_failure_analysis.v3",
        "research_only": True,
        "failure_labels": [
            "source-point-of-interest-selection-not-universally-machine-specified",
            "source-qualitative-wick-classification-not-machine-specified",
            "source-bias-context-not-universally-machine-specified",
            "non-executable-c2-context-remains-unresolved",
        ],
        "implementation_failure": False,
        "economic_failure": None if expectancy is None else expectancy < 0,
        "methodology_change_authorized": False,
        "correct_action": "preserve-source-ambiguity-do-not-invent-thresholds",
    }
    episodes: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        episodes.append(
            {
                "episode_id": f"vt08-v2-source-candidate-{index:06d}",
                "decision_time": {
                    "signal_at": row.get("signal_at"),
                    "anchor_opened_at": row.get("anchor_opened_at"),
                    "scenario_candidate": row.get("scenario_candidate"),
                    "proposed_side": row.get("proposed_side"),
                    "entry_observation": row.get("entry_observation"),
                    "protected_swing_extreme": row.get("protected_swing_extreme"),
                    "cisd_level": row.get("cisd_level"),
                    "source_bias_status": row.get("source_bias_status"),
                    "source_point_of_interest_status": row.get(
                        "source_point_of_interest_status"
                    ),
                    "poi_type": row.get("poi_type"),
                    "poi_lower_bound": row.get("poi_lower_bound"),
                    "poi_upper_bound": row.get("poi_upper_bound"),
                    "poi_formed_at": row.get("poi_formed_at"),
                    "source_wick_status": row.get("source_wick_status"),
                    "automatic_setup": row.get("automatic_setup"),
                    "entry_price": row.get("entry_price"),
                    "stop_price": row.get("stop_price"),
                    "target_price": row.get("target_price"),
                },
                "execution_outcome": {
                    "filled_at": row.get("filled_at"),
                    "outcome": row.get("outcome"),
                    "result_r": row.get("result_r"),
                    "same_bar_resolution": row.get("same_bar_resolution"),
                },
                "descriptive_path": {
                    "h4_close_r": row.get(
                        "post_signal_h4_close_r_descriptive_only"
                    ),
                    "mfe_r": row.get("mfe_r_descriptive_only"),
                    "mae_r": row.get("mae_r_descriptive_only"),
                },
            }
        )
    story = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_story_forensics.v3",
        "research_only": True,
        "decision_time_oracle_separation": True,
        "human_owner_operating_scope": owner_scope,
        "episode_count": len(episodes),
        "episodes": episodes,
    }
    hypothesis_register = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_hypothesis_register.v3",
        "research_only": True,
        "hypotheses": [],
        "reason": (
            "no numerical wick threshold or synthetic target may be optimized; "
            "changes after OOS require preregistration and a fresh holdout"
        ),
        "methodology_change_authorized": False,
    }
    summary = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_full_research.v3",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": software_sha,
        "symbol": symbol,
        "trader_code": "vt-08",
        "trader_version": "v2",
        "source_fidelity_mode": True,
        "human_owner_operating_scope": owner_scope,
        "invalidates_prior_13468_campaign": True,
        "mechanical_candidate_count": len(rows),
        "automatic_setup_count": len(setups),
        "filled_count": len(filled),
        "unfilled_count": len(setups) - len(filled),
        "economic_result_available": True,
        "win_count": wins,
        "loss_count": losses,
        "censored_count": censored,
        "expectancy_r": None if expectancy is None else format(expectancy, "f"),
        "total_r": format(total_r, "f"),
        "stress_status": stress["status"],
        "monte_carlo_status": monte["status"],
        "source_ambiguity_blocks_autonomous_backtest": False,
        "governed_lifecycle_authority": False,
        "demo_eligible": False,
        "promotion_blocker": (
            "Trader Lab authorities remain independent; economic replay alone "
            "does not grant DEMO eligibility"
        ),
    }
    outputs: dict[str, dict[str, object]] = {
        "walk-forward.json": walk,
        "characterization.json": characterization,
        "stress.json": stress,
        "monte-carlo.json": monte,
        "failure-analysis.json": failure_analysis,
        "story-forensics.json": story,
        "hypothesis-register.json": hypothesis_register,
        "research-summary.json": summary,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in outputs.items():
        (output_dir / name).write_text(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )
    return summary


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        raise SystemExit(
            "usage: vt08_crt_h4_amd_v2_full_research <source-audit.json> <output-dir>"
        )
    summary = generate_full_research(Path(args[0]), Path(args[1]))
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
