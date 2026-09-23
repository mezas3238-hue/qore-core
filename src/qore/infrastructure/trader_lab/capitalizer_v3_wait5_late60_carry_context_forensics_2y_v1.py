"""Decision-time M5 carry-context forensics for rejected WAIT5_LATE60.

Structural states are computed without outcomes. Outcomes are attached only after
the structural census and only as consumed post-result diagnostics.

Predeclared dimensions:
- M5 directional state at the original H1 deadline;
- M5 directional state from the last completed M5 available at late entry;
- deadline -> entry state transition;
- any ALIGNED / OPPOSED completed M5 during carry;
- counts of ALIGNED / NEUTRAL / OPPOSED completed M5 during carry;
- whether new completed-M5 evidence exists after the deadline before entry.

No admission rule is promoted from this consumed 2Y result.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import (
    CapitalizerM5Bar,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_microstructure_discovery import (
    classify_microstructure_events,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    TFBar,
    _aggregate_tf,
)
from qore.infrastructure.trader_lab.capitalizer_v3_m5_directional_state_v1 import (
    CapitalizerM5DirectionalState,
    classify_m5_directional_state,
)

IDENTITY = "QORE_CAPITALIZER_V3_WAIT5_LATE60_CARRY_CONTEXT_FORENSICS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_WAIT5_LATE60_CARRY_CONTEXT_FORENSICS_2Y_V1"
)
EXPECTED_LATE_RAW = 365
EXPECTED_LATE_SELECTED = 354
EXTENSION_MINUTES = 60

NO_COMPLETED_M5 = "NO_COMPLETED_M5"


@dataclass(frozen=True, slots=True)
class CarryContextRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    entry_at: str
    original_deadline: str
    delay_minutes: int
    entry_mode: str
    deadline_signature: str
    deadline_state: str
    entry_signature: str
    entry_state: str
    state_transition: str
    carry_completed_m5: int
    carry_aligned_count: int
    carry_neutral_count: int
    carry_opposed_count: int
    any_aligned_since_deadline: bool
    any_opposed_since_deadline: bool
    new_completed_m5_evidence: bool
    realized_r_diagnostic: str
    outcome_used_for_state: bool = False


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _load_market_trades(root: Path) -> tuple[v3.V3Trade, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-late60-2y-v1-trades.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("carry context requires one LATE60 market trade ledger")
    rows: list[v3.V3Trade] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(v3.V3Trade(**json.loads(line)))
    return tuple(rows)


def _m5_bar(
    bar: TFBar,
    *,
    symbol: str,
    digits: int,
) -> CapitalizerM5Bar:
    return CapitalizerM5Bar(
        symbol=symbol,
        opened_at=bar.opened_at,
        closed_at=bar.closed_at,
        open=bar.source.open,
        high=bar.source.high,
        low=bar.source.low,
        close=bar.source.close,
        volume=None,
        digits=digits,
    )


def _signature(
    previous: TFBar,
    current: TFBar,
    *,
    symbol: str,
    digits: int,
) -> str:
    previous_bar = _m5_bar(previous, symbol=symbol, digits=digits)
    current_bar = _m5_bar(current, symbol=symbol, digits=digits)
    events = classify_microstructure_events(current_bar, previous_bar)
    if not events:
        return "NONE"
    return "+".join(item.value for item in events)


def _state_at(
    m5: tuple[TFBar, ...],
    closes: tuple[datetime, ...],
    *,
    at: datetime,
    side: CapitalizerSide,
    symbol: str,
    digits: int,
) -> tuple[CapitalizerM5DirectionalState, str, int | None]:
    index = bisect.bisect_right(closes, at) - 1
    if index <= 0:
        return CapitalizerM5DirectionalState.NEUTRAL, NO_COMPLETED_M5, None

    current = m5[index]
    previous = m5[index - 1]
    if current.opened_at - previous.opened_at != timedelta(minutes=5):
        return CapitalizerM5DirectionalState.NEUTRAL, NO_COMPLETED_M5, index

    signature = _signature(
        previous,
        current,
        symbol=symbol,
        digits=digits,
    )
    return (
        classify_m5_directional_state(
            side=side,
            microstructure_signature=signature,
        ),
        signature,
        index,
    )


def _carry_states(
    m5: tuple[TFBar, ...],
    closes: tuple[datetime, ...],
    *,
    after: datetime,
    through: datetime,
    side: CapitalizerSide,
    symbol: str,
    digits: int,
) -> tuple[CapitalizerM5DirectionalState, ...]:
    start = bisect.bisect_right(closes, after)
    end = bisect.bisect_right(closes, through)
    states: list[CapitalizerM5DirectionalState] = []
    for index in range(start, end):
        if index <= 0:
            continue
        current = m5[index]
        previous = m5[index - 1]
        if current.opened_at - previous.opened_at != timedelta(minutes=5):
            states.append(CapitalizerM5DirectionalState.NEUTRAL)
            continue
        signature = _signature(
            previous,
            current,
            symbol=symbol,
            digits=digits,
        )
        states.append(
            classify_m5_directional_state(
                side=side,
                microstructure_signature=signature,
            )
        )
    return tuple(states)


def build_market_report(
    late60_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[CarryContextRow, ...]]:
    all_trades = _load_market_trades(late60_root)
    late = tuple(
        item for item in all_trades if item.entry_mode.startswith("LATE60_")
    )
    if not late:
        raise ValueError("carry context requires LATE60 trades")

    bars = tuple(iter_cibo_m1(m1_root))
    if not bars:
        raise ValueError("carry context found no native M1")
    symbol = bars[0].symbol
    digits = bars[0].digits
    if any(item.symbol != symbol for item in late):
        raise ValueError("LATE60/M1 symbol mismatch")

    m5 = _aggregate_tf(bars, minutes=5)
    closes = tuple(item.closed_at for item in m5)
    rows: list[CarryContextRow] = []

    for trade in late:
        side = CapitalizerSide(trade.side)
        entry_at = _aware(trade.entry_at)
        original_deadline = _aware(trade.h1_deadline) - timedelta(
            minutes=EXTENSION_MINUTES
        )
        delay_minutes = int(
            (entry_at - original_deadline).total_seconds() // 60
        )
        if not 0 <= delay_minutes < EXTENSION_MINUTES:
            raise ValueError("late trade outside frozen LATE60 window")

        deadline_state, deadline_signature, _deadline_index = _state_at(
            m5,
            closes,
            at=original_deadline,
            side=side,
            symbol=symbol,
            digits=digits,
        )
        entry_state, entry_signature, _entry_index = _state_at(
            m5,
            closes,
            at=entry_at,
            side=side,
            symbol=symbol,
            digits=digits,
        )
        carry = _carry_states(
            m5,
            closes,
            after=original_deadline,
            through=entry_at,
            side=side,
            symbol=symbol,
            digits=digits,
        )
        counts = Counter(item.value for item in carry)
        rows.append(
            CarryContextRow(
                symbol=symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                side=trade.side,
                entry_at=trade.entry_at,
                original_deadline=original_deadline.isoformat(),
                delay_minutes=delay_minutes,
                entry_mode=trade.entry_mode,
                deadline_signature=deadline_signature,
                deadline_state=deadline_state.value,
                entry_signature=entry_signature,
                entry_state=entry_state.value,
                state_transition=(
                    f"{deadline_state.value}->{entry_state.value}"
                ),
                carry_completed_m5=len(carry),
                carry_aligned_count=counts[
                    CapitalizerM5DirectionalState.ALIGNED.value
                ],
                carry_neutral_count=counts[
                    CapitalizerM5DirectionalState.NEUTRAL.value
                ],
                carry_opposed_count=counts[
                    CapitalizerM5DirectionalState.OPPOSED.value
                ],
                any_aligned_since_deadline=(
                    counts[CapitalizerM5DirectionalState.ALIGNED.value] > 0
                ),
                any_opposed_since_deadline=(
                    counts[CapitalizerM5DirectionalState.OPPOSED.value] > 0
                ),
                new_completed_m5_evidence=bool(carry),
                realized_r_diagnostic=trade.realized_gross_r,
            )
        )

    ordered = tuple(sorted(rows, key=lambda item: (item.entry_at, item.symbol)))
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": ordered[0].session,
        "late_raw_trades": len(ordered),
        "deadline_states": dict(
            Counter(item.deadline_state for item in ordered)
        ),
        "entry_states": dict(
            Counter(item.entry_state for item in ordered)
        ),
        "state_transitions": dict(
            Counter(item.state_transition for item in ordered)
        ),
        "any_opposed_since_deadline": sum(
            item.any_opposed_since_deadline for item in ordered
        ),
        "any_aligned_since_deadline": sum(
            item.any_aligned_since_deadline for item in ordered
        ),
        "new_completed_m5_evidence": sum(
            item.new_completed_m5_evidence for item in ordered
        ),
        "no_new_completed_m5_evidence": sum(
            not item.new_completed_m5_evidence for item in ordered
        ),
        "state_semantics_identity": (
            "QORE_CAPITALIZER_V3_M5_DIRECTIONAL_STATE_V1"
        ),
        "outcome_used_for_state": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "rule_promotion_allowed": False,
    }, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[CarryContextRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-wait5-late60-carry-context-forensics-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-wait5-late60-carry-context-forensics-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"carry context matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _load_rows(root: Path) -> tuple[CarryContextRow, ...]:
    rows: list[CarryContextRow] = []
    for path in sorted(
        root.rglob(
            "capitalizer-*-v3-wait5-late60-carry-context-forensics-2y-v1-rows.jsonl"
        )
    ):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(CarryContextRow(**json.loads(line)))
    return tuple(rows)


def _load_all_late60(root: Path) -> tuple[v3.V3Trade, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-late60-2y-v1-trades.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError("carry context matrix requires 9 LATE60 ledgers")
    rows: list[v3.V3Trade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(v3.V3Trade(**json.loads(line)))
    return tuple(rows)


def _trade_key(trade: v3.V3Trade) -> tuple[str, str, str, str, str]:
    return (
        trade.symbol,
        trade.session,
        trade.operating_date,
        trade.side,
        trade.entry_at,
    )


def _row_key(row: CarryContextRow) -> tuple[str, str, str, str, str]:
    return (
        row.symbol,
        row.session,
        row.operating_date,
        row.side,
        row.entry_at,
    )


def _metrics(trades: tuple[v3.V3Trade, ...]) -> dict[str, Any] | None:
    value = v3._metrics(
        tuple(
            sorted(
                trades,
                key=lambda item: (_aware(item.entry_at), item.symbol),
            )
        )
    )
    return None if value is None else asdict(value)


def _economic_dimension(
    selected_by_key: dict[tuple[str, str, str, str, str], v3.V3Trade],
    rows: tuple[CarryContextRow, ...],
    *,
    field: str,
) -> dict[str, Any]:
    grouped: dict[str, list[v3.V3Trade]] = defaultdict(list)
    for row in rows:
        trade = selected_by_key.get(_row_key(row))
        if trade is None:
            continue
        grouped[str(getattr(row, field))].append(trade)
    return {
        key: {
            "trades": len(value),
            "metrics": _metrics(tuple(value)),
        }
        for key, value in sorted(grouped.items())
    }


def build_matrix(
    context_root: Path,
    late60_root: Path,
) -> dict[str, Any]:
    reports = _load_reports(context_root)
    rows = _load_rows(context_root)
    if len(rows) != EXPECTED_LATE_RAW:
        raise ValueError("carry context raw late control mismatch")

    combined = _load_all_late60(late60_root)
    selected = v3._portfolio_max3(combined)
    selected_late = tuple(
        item for item in selected if item.entry_mode.startswith("LATE60_")
    )
    if len(selected_late) != EXPECTED_LATE_SELECTED:
        raise ValueError("carry context selected late control mismatch")

    selected_by_key = {_trade_key(item): item for item in selected_late}
    if len(selected_by_key) != len(selected_late):
        raise ValueError("duplicate selected LATE60 trade key")

    deadline_states = Counter(item.deadline_state for item in rows)
    entry_states = Counter(item.entry_state for item in rows)
    transitions = Counter(item.state_transition for item in rows)

    selected_rows = tuple(
        item for item in rows if _row_key(item) in selected_by_key
    )
    if len(selected_rows) != EXPECTED_LATE_SELECTED:
        raise ValueError("selected carry-context row count mismatch")

    any_opposed_groups: dict[str, tuple[v3.V3Trade, ...]] = {}
    any_aligned_groups: dict[str, tuple[v3.V3Trade, ...]] = {}
    new_evidence_groups: dict[str, tuple[v3.V3Trade, ...]] = {}
    for label, predicate in (
        ("TRUE", lambda item: item.any_opposed_since_deadline),
        ("FALSE", lambda item: not item.any_opposed_since_deadline),
    ):
        any_opposed_groups[label] = tuple(
            selected_by_key[_row_key(item)]
            for item in selected_rows
            if predicate(item)
        )
    for label, predicate in (
        ("TRUE", lambda item: item.any_aligned_since_deadline),
        ("FALSE", lambda item: not item.any_aligned_since_deadline),
    ):
        any_aligned_groups[label] = tuple(
            selected_by_key[_row_key(item)]
            for item in selected_rows
            if predicate(item)
        )
    for label, predicate in (
        ("TRUE", lambda item: item.new_completed_m5_evidence),
        ("FALSE", lambda item: not item.new_completed_m5_evidence),
    ):
        new_evidence_groups[label] = tuple(
            selected_by_key[_row_key(item)]
            for item in selected_rows
            if predicate(item)
        )

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "late_raw_trades": len(rows),
        "late_raw_control_reproduced": len(rows) == EXPECTED_LATE_RAW,
        "late_selected_trades": len(selected_rows),
        "late_selected_control_reproduced": (
            len(selected_rows) == EXPECTED_LATE_SELECTED
        ),
        "structural": {
            "deadline_states": dict(sorted(deadline_states.items())),
            "entry_states": dict(sorted(entry_states.items())),
            "state_transitions": dict(sorted(transitions.items())),
            "any_opposed_since_deadline": sum(
                item.any_opposed_since_deadline for item in rows
            ),
            "any_aligned_since_deadline": sum(
                item.any_aligned_since_deadline for item in rows
            ),
            "new_completed_m5_evidence": sum(
                item.new_completed_m5_evidence for item in rows
            ),
            "no_new_completed_m5_evidence": sum(
                not item.new_completed_m5_evidence for item in rows
            ),
        },
        "selected_economics_descriptive": {
            "deadline_state": _economic_dimension(
                selected_by_key,
                selected_rows,
                field="deadline_state",
            ),
            "entry_state": _economic_dimension(
                selected_by_key,
                selected_rows,
                field="entry_state",
            ),
            "state_transition": _economic_dimension(
                selected_by_key,
                selected_rows,
                field="state_transition",
            ),
            "any_opposed_since_deadline": {
                key: {
                    "trades": len(value),
                    "metrics": _metrics(value),
                }
                for key, value in any_opposed_groups.items()
            },
            "any_aligned_since_deadline": {
                key: {
                    "trades": len(value),
                    "metrics": _metrics(value),
                }
                for key, value in any_aligned_groups.items()
            },
            "new_completed_m5_evidence": {
                key: {
                    "trades": len(value),
                    "metrics": _metrics(value),
                }
                for key, value in new_evidence_groups.items()
            },
        },
        "per_market_structural": {
            str(item["symbol"]): {
                "late_raw_trades": int(item["late_raw_trades"]),
                "deadline_states": item["deadline_states"],
                "entry_states": item["entry_states"],
                "state_transitions": item["state_transitions"],
                "any_opposed_since_deadline": int(
                    item["any_opposed_since_deadline"]
                ),
                "any_aligned_since_deadline": int(
                    item["any_aligned_since_deadline"]
                ),
            }
            for item in sorted(reports, key=lambda value: str(value["symbol"]))
        },
        "state_semantics_identity": "QORE_CAPITALIZER_V3_M5_DIRECTIONAL_STATE_V1",
        "structural_states_outcome_free": True,
        "outcome_aware_descriptive": True,
        "outcome_used_for_state": False,
        "outcome_used_for_admission": False,
        "post_result_diagnostic_only": True,
        "strategy_mutated": False,
        "rule_promotion_allowed": False,
        "fresh_holdout_claimed": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-nine-market-v3-wait5-late60-carry-context-forensics-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("late60_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("context_root", type=Path)
    matrix.add_argument("late60_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, rows = build_market_report(
            args.late60_root,
            args.m1_root,
        )
        write_market(report, rows, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(
        args.context_root,
        args.late60_root,
    )
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
