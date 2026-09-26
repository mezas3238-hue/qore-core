"""Census of the frozen M5 directional-state mapping over V3 2Y populations.

Inputs are existing GREEN artifacts:
- V3 M3 microstructure context 2Y rows (all 8,099 closebacks),
- CISD counterfactual census 2Y rows (all 3,007 CISD-first-blockers).

The mapping is descriptive only and cannot admit trades in this step.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_v3_m5_directional_state_v1 import (
    IDENTITY as STATE_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_v3_m5_directional_state_v1 import (
    CapitalizerM5DirectionalState,
    classify_m5_directional_state,
)

IDENTITY = "QORE_CAPITALIZER_V3_M5_DIRECTIONAL_STATE_CENSUS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_M5_DIRECTIONAL_STATE_CENSUS_2Y_V1"
)
EXPECTED_CLOSEBACKS = 8099
EXPECTED_VALID_MSS = 1254
EXPECTED_CISD_FIRST_BLOCKERS = 3007
EXPECTED_SAME_BAR_CISD_ONLY = 1298


def _counter_template() -> Counter[str]:
    return Counter(
        {
            CapitalizerM5DirectionalState.ALIGNED.value: 0,
            CapitalizerM5DirectionalState.OPPOSED.value: 0,
            CapitalizerM5DirectionalState.NEUTRAL.value: 0,
        }
    )


def _state(*, side: str, signature: str) -> str:
    return classify_m5_directional_state(
        side=CapitalizerSide(side),
        microstructure_signature=signature,
    ).value


def _load_micro_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-m3-microstructure-context-2y-v1-rows.jsonl")
    )
    if len(paths) != 1:
        raise ValueError("M5 state census requires one microstructure ledger")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("microstructure row must be object")
            rows.append(raw)
    return tuple(rows)


def _load_cisd_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-cisd-counterfactual-census-2y-v1-rows.jsonl")
    )
    if len(paths) != 1:
        raise ValueError("M5 state census requires one CISD census ledger")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("CISD census row must be object")
            rows.append(raw)
    return tuple(rows)


def _count_micro(
    rows: tuple[dict[str, Any], ...],
) -> tuple[Counter[str], Counter[str], Counter[str]]:
    all_states = _counter_template()
    valid_states = _counter_template()
    cisd_states = _counter_template()
    for row in rows:
        value = _state(
            side=str(row["side"]),
            signature=str(row["microstructure_signature"]),
        )
        all_states[value] += 1
        if bool(row["valid_m3_within_h1"]):
            valid_states[value] += 1
        if str(row["first_blocker"]) == "CISD":
            cisd_states[value] += 1
    return all_states, valid_states, cisd_states


def _count_same_bar(
    rows: tuple[dict[str, Any], ...],
) -> Counter[str]:
    result = _counter_template()
    for row in rows:
        if not bool(row["same_bar_cisd_only"]):
            continue
        value = _state(
            side=str(row["side"]),
            signature=str(row["raw_m5_microstructure_signature"]),
        )
        result[value] += 1
    return result


def build_market_report(
    micro_root: Path,
    cisd_root: Path,
) -> dict[str, Any]:
    micro_rows = _load_micro_rows(micro_root)
    cisd_rows = _load_cisd_rows(cisd_root)
    if not micro_rows or not cisd_rows:
        raise ValueError("M5 state census requires non-empty inputs")

    symbols = {str(item["symbol"]) for item in micro_rows}
    sessions = {str(item["session"]) for item in micro_rows}
    if len(symbols) != 1 or len(sessions) != 1:
        raise ValueError("M5 state market input must be one symbol/session")
    symbol = next(iter(symbols))
    session = next(iter(sessions))
    if {str(item["symbol"]) for item in cisd_rows} != {symbol}:
        raise ValueError("CISD census symbol mismatch")
    if {str(item["session"]) for item in cisd_rows} != {session}:
        raise ValueError("CISD census session mismatch")

    all_states, valid_states, cisd_states = _count_micro(micro_rows)
    same_bar_states = _count_same_bar(cisd_rows)
    cisd_first = sum(str(row["first_blocker"]) == "CISD" for row in micro_rows)
    same_bar = sum(bool(row["same_bar_cisd_only"]) for row in cisd_rows)

    return {
        "identity": IDENTITY,
        "state_identity": STATE_IDENTITY,
        "symbol": symbol,
        "session": session,
        "closebacks": len(micro_rows),
        "valid_mss": sum(bool(row["valid_m3_within_h1"]) for row in micro_rows),
        "cisd_first_blockers": cisd_first,
        "same_bar_cisd_only": same_bar,
        "all_closebacks_by_state": dict(all_states),
        "valid_mss_by_state": dict(valid_states),
        "cisd_first_blockers_by_state": dict(cisd_states),
        "same_bar_cisd_only_by_state": dict(same_bar_states),
        "same_bar_cisd_only_aligned": same_bar_states[
            CapitalizerM5DirectionalState.ALIGNED.value
        ],
        "same_bar_cisd_only_opposed": same_bar_states[
            CapitalizerM5DirectionalState.OPPOSED.value
        ],
        "same_bar_cisd_only_neutral": same_bar_states[
            CapitalizerM5DirectionalState.NEUTRAL.value
        ],
        "m5_state_mapping_frozen": True,
        "neutral_is_fail_closed": True,
        "uses_closeback_time_information_only": True,
        "v3_liquidity_level_reaction_claimed": False,
        "strategy_mutated": False,
        "outcome_used_for_admission": False,
        "diagnostic_only": True,
        "economic_candidate": False,
    }


def write_market(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    path = output / f"capitalizer-{symbol}-v3-m5-directional-state-census-2y-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-m5-directional-state-census-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"M5 state matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _sum_states(
    reports: list[dict[str, Any]],
    key: str,
) -> dict[str, int]:
    result = _counter_template()
    for report in reports:
        raw = report[key]
        if not isinstance(raw, dict):
            raise ValueError(f"{key} must be mapping")
        for state, count in raw.items():
            result[str(state)] += int(count)
    return dict(result)


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    per_session: dict[str, Counter[str]] = {}
    for report in reports:
        session = str(report["session"])
        counter = per_session.setdefault(session, Counter())
        counter["closebacks"] += int(report["closebacks"])
        counter["valid_mss"] += int(report["valid_mss"])
        counter["cisd_first_blockers"] += int(report["cisd_first_blockers"])
        counter["same_bar_cisd_only"] += int(report["same_bar_cisd_only"])
        counter["same_bar_cisd_only_aligned"] += int(
            report["same_bar_cisd_only_aligned"]
        )
        counter["same_bar_cisd_only_opposed"] += int(
            report["same_bar_cisd_only_opposed"]
        )
        counter["same_bar_cisd_only_neutral"] += int(
            report["same_bar_cisd_only_neutral"]
        )

    closebacks = sum(int(item["closebacks"]) for item in reports)
    valid = sum(int(item["valid_mss"]) for item in reports)
    cisd = sum(int(item["cisd_first_blockers"]) for item in reports)
    same_bar = sum(int(item["same_bar_cisd_only"]) for item in reports)
    same_bar_states = _sum_states(reports, "same_bar_cisd_only_by_state")
    aligned = same_bar_states[CapitalizerM5DirectionalState.ALIGNED.value]

    return {
        "identity": MATRIX_IDENTITY,
        "state_identity": STATE_IDENTITY,
        "market_count": 9,
        "closebacks": closebacks,
        "valid_mss": valid,
        "cisd_first_blockers": cisd,
        "same_bar_cisd_only": same_bar,
        "closeback_control_reproduced": closebacks == EXPECTED_CLOSEBACKS,
        "valid_mss_control_reproduced": valid == EXPECTED_VALID_MSS,
        "cisd_control_reproduced": cisd == EXPECTED_CISD_FIRST_BLOCKERS,
        "same_bar_control_reproduced": same_bar == EXPECTED_SAME_BAR_CISD_ONLY,
        "all_closebacks_by_state": _sum_states(reports, "all_closebacks_by_state"),
        "valid_mss_by_state": _sum_states(reports, "valid_mss_by_state"),
        "cisd_first_blockers_by_state": _sum_states(
            reports, "cisd_first_blockers_by_state"
        ),
        "same_bar_cisd_only_by_state": same_bar_states,
        "same_bar_cisd_only_aligned": aligned,
        "same_bar_cisd_only_aligned_rate": (
            None if same_bar == 0 else aligned / same_bar
        ),
        "per_session": {
            key: dict(value) for key, value in sorted(per_session.items())
        },
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "m5_state_mapping_frozen": True,
        "neutral_is_fail_closed": True,
        "uses_closeback_time_information_only": True,
        "v3_liquidity_level_reaction_claimed": False,
        "strategy_mutated": False,
        "outcome_used_for_admission": False,
        "diagnostic_only": True,
        "economic_candidate": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-v3-m5-directional-state-census-2y-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("micro_root", type=Path)
    market.add_argument("cisd_root", type=Path)
    market.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        report = build_market_report(args.micro_root, args.cisd_root)
        write_market(report, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
