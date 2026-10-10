"""Causal Core capital-intelligence frontier for VT08 Cognitive Expansion 5M.

Architecture is borrowed from VT31's governed capital-allocation research, not
its NAS100 rules or parameters.

The frontier:
- preserves every admitted VT08 trade;
- derives only decision-time/source-known causal features;
- learns coarse state quality on the chronological 70% development partition;
- freezes one bounded exposure policy;
- applies it unchanged to the final 30% OOS partition;
- reports both equal-risk and capital-weighted economics.

Terminal PnL is used only inside the governed development fit. Runtime/OOS
classification consumes the frozen state table and never sees the trade outcome.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Final

from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    ExpansionTrade,
    load_market_evidence,
    metrics,
    model_trade,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    Vt08ExpansionCandidate,
    evaluate_expansion_at_entry_indexed,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
    program_fingerprint,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_core_allocation_frontier.v1"
TRAIN_FRACTION: Final = Decimal("0.70")
MIN_STATE_SAMPLE: Final = 8
POSITIVE_STATE_PF: Final = Decimal("1.20")
NEGATIVE_STATE_PF: Final = Decimal("0.80")
SUPPORTIVE_MULTIPLIER: Final = Decimal("1.20")
MIXED_MULTIPLIER: Final = Decimal("0.75")
CAUTIOUS_MULTIPLIER: Final = Decimal("0.50")

_AXES: Final = (
    "anchor",
    "side",
    "risk_ref_band",
    "c2_body_band",
    "protected_swing_age_band",
    "reference_body_alignment",
)


@dataclass(frozen=True, slots=True)
class CausalTradeRow:
    trade: ExpansionTrade
    anchor: str
    side: str
    risk_ref_band: str
    c2_body_band: str
    protected_swing_age_band: str
    reference_body_alignment: str

    def state(self, axis: str) -> str:
        if axis not in _AXES:
            raise ValueError(f"unsupported causal axis: {axis}")
        return str(getattr(self, axis))


@dataclass(frozen=True, slots=True)
class FrozenStateQuality:
    axis: str
    state: str
    sample: int
    profit_factor: Decimal | None
    mean_r: Decimal
    vote: int

    def payload(self) -> dict[str, object]:
        return {
            "axis": self.axis,
            "state": self.state,
            "sample": self.sample,
            "profit_factor": (
                None
                if self.profit_factor is None
                else format(self.profit_factor, "f")
            ),
            "mean_r": format(self.mean_r, "f"),
            "vote": self.vote,
        }


def _band(value: Decimal, *, low: Decimal, high: Decimal) -> str:
    if value < low:
        return "LOW"
    if value > high:
        return "HIGH"
    return "MID"


def _alignment(candidate: Vt08ExpansionCandidate) -> str:
    reference = candidate.reference_h4
    if reference.close == reference.open:
        return "FLAT"
    bullish = reference.close > reference.open
    with_side = (
        bullish
        if candidate.side is DemoTradingSetupSide.LONG
        else not bullish
    )
    return "WITH_SIDE" if with_side else "AGAINST_SIDE"


def _causal_row(
    candidate: Vt08ExpansionCandidate,
    trade: ExpansionTrade,
) -> CausalTradeRow:
    setup = candidate.setup
    risk = abs(setup.entry_price - setup.invalidation_price)
    reference_range = candidate.reference_h4.high - candidate.reference_h4.low
    candle2_range = candidate.candle2.high - candidate.candle2.low
    if risk <= 0 or reference_range <= 0 or candle2_range <= 0:
        raise ValueError("VT08 causal allocation requires positive geometry")

    risk_ref = risk / reference_range
    c2_body = abs(candidate.candle2.close - candidate.candle2.open) / candle2_range
    age_minutes = Decimal(
        str(
            (
                candidate.decision_at - candidate.protected_swing.confirmed_at
            ).total_seconds()
            / 60
        )
    )
    if age_minutes < 0:
        raise ValueError("protected swing confirmation cannot be in the future")

    return CausalTradeRow(
        trade=trade,
        anchor=str(candidate.entry_anchor_hour),
        side=candidate.side.value,
        risk_ref_band=_band(
            risk_ref,
            low=Decimal("0.25"),
            high=Decimal("0.75"),
        ),
        c2_body_band=_band(
            c2_body,
            low=Decimal("0.33"),
            high=Decimal("0.66"),
        ),
        protected_swing_age_band=(
            "FRESH" if age_minutes <= Decimal("60") else "MATURE"
        ),
        reference_body_alignment=_alignment(candidate),
    )


def causal_rows(path: Path) -> tuple[CausalTradeRow, ...]:
    _, symbol, _, _, bars = load_market_evidence(path)
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("VT08 capital frontier market outside 5M universe")
    bars_by_open = {item.opened_at: item for item in bars}
    candidates_by_day: dict[date, list[Vt08ExpansionCandidate]] = defaultdict(list)

    for bar in bars:
        local = bar.opened_at.astimezone(
            __import__("zoneinfo").ZoneInfo("America/New_York")
        )
        if local.minute != 0 or local.hour not in ANCHORS_NY:
            continue
        evaluation = evaluate_expansion_at_entry_indexed(
            symbol=symbol,
            bars_by_open=bars_by_open,
            decision_at=bar.opened_at,
        )
        if evaluation.candidate is not None:
            candidates_by_day[local.date()].append(evaluation.candidate)

    rows: list[CausalTradeRow] = []
    for local_day in sorted(candidates_by_day):
        candidates = candidates_by_day[local_day]
        if len(candidates) != 1:
            continue
        candidate = candidates[0]
        trade = model_trade(candidate, bars_by_open=bars_by_open)
        if trade is not None:
            rows.append(_causal_row(candidate, trade))
    return tuple(sorted(rows, key=lambda row: row.trade.signal_at))


def _state_quality(
    rows: tuple[CausalTradeRow, ...],
    *,
    axis: str,
    state: str,
) -> FrozenStateQuality:
    selected = tuple(row.trade for row in rows if row.state(axis) == state)
    if not selected:
        return FrozenStateQuality(axis, state, 0, None, Decimal(0), 0)
    result = metrics(selected)
    pf_raw = result["profit_factor"]
    pf = None if pf_raw is None else Decimal(str(pf_raw))
    mean = Decimal(str(result["mean_r"]))

    vote = 0
    if len(selected) >= MIN_STATE_SAMPLE and pf is not None:
        if pf >= POSITIVE_STATE_PF and mean > 0:
            vote = 1
        elif pf <= NEGATIVE_STATE_PF and mean < 0:
            vote = -1
    return FrozenStateQuality(axis, state, len(selected), pf, mean, vote)


def fit_state_table(
    train: tuple[CausalTradeRow, ...],
) -> tuple[FrozenStateQuality, ...]:
    fitted: list[FrozenStateQuality] = []
    for axis in _AXES:
        states = sorted({row.state(axis) for row in train})
        fitted.extend(
            _state_quality(train, axis=axis, state=state)
            for state in states
        )
    return tuple(fitted)


def _vote_map(
    table: tuple[FrozenStateQuality, ...],
) -> dict[tuple[str, str], int]:
    return {(item.axis, item.state): item.vote for item in table}


def classify_context(
    row: CausalTradeRow,
    table: tuple[FrozenStateQuality, ...],
) -> tuple[str, int]:
    votes = _vote_map(table)
    score = sum(votes.get((axis, row.state(axis)), 0) for axis in _AXES)
    if score >= 2:
        return "SUPPORTIVE", score
    if score <= -2:
        return "CAUTIOUS", score
    return "MIXED", score


def _multiplier(context: str) -> Decimal:
    if context == "SUPPORTIVE":
        return SUPPORTIVE_MULTIPLIER
    if context == "CAUTIOUS":
        return CAUTIOUS_MULTIPLIER
    if context == "MIXED":
        return MIXED_MULTIPLIER
    raise ValueError(context)


def _weighted_trade(row: CausalTradeRow, multiplier: Decimal) -> ExpansionTrade:
    return replace(
        row.trade,
        r_multiple=row.trade.r_multiple * multiplier,
    )


def _weighted_metrics(
    rows: tuple[CausalTradeRow, ...],
    table: tuple[FrozenStateQuality, ...],
) -> tuple[dict[str, object], dict[str, int], list[dict[str, object]]]:
    weighted: list[ExpansionTrade] = []
    contexts: dict[str, int] = defaultdict(int)
    audit: list[dict[str, object]] = []
    for row in rows:
        context, score = classify_context(row, table)
        multiplier = _multiplier(context)
        contexts[context] += 1
        weighted.append(_weighted_trade(row, multiplier))
        audit.append(
            {
                "signal_at": row.trade.signal_at.isoformat(),
                "anchor": row.anchor,
                "side": row.side,
                "risk_ref_band": row.risk_ref_band,
                "c2_body_band": row.c2_body_band,
                "protected_swing_age_band": row.protected_swing_age_band,
                "reference_body_alignment": row.reference_body_alignment,
                "context": context,
                "context_score": score,
                "risk_multiplier": format(multiplier, "f"),
                "raw_r": format(row.trade.r_multiple, "f"),
                "capital_weighted_r": format(
                    row.trade.r_multiple * multiplier,
                    "f",
                ),
            }
        )
    return (
        metrics(tuple(weighted)),
        dict(sorted(contexts.items())),
        audit,
    )


def replay(path: Path) -> dict[str, object]:
    rows = causal_rows(path)
    if len(rows) < 2:
        raise ValueError("VT08 capital frontier requires at least two terminal trades")
    split = int(Decimal(len(rows)) * TRAIN_FRACTION)
    split = max(1, min(split, len(rows) - 1))
    train = rows[:split]
    oos = rows[split:]
    table = fit_state_table(train)

    train_weighted, train_contexts, _ = _weighted_metrics(train, table)
    oos_weighted, oos_contexts, audit = _weighted_metrics(oos, table)
    train_equal = metrics(tuple(row.trade for row in train))
    oos_equal = metrics(tuple(row.trade for row in oos))

    return {
        "schema": SCHEMA,
        "program_fingerprint": program_fingerprint(),
        "market": rows[0].trade.symbol,
        "research_only": True,
        "split": {
            "train_fraction": format(TRAIN_FRACTION, "f"),
            "train_count": len(train),
            "oos_count": len(oos),
            "split_signal_at": oos[0].trade.signal_at.isoformat(),
        },
        "frozen_policy": {
            "min_state_sample": MIN_STATE_SAMPLE,
            "positive_state_pf": format(POSITIVE_STATE_PF, "f"),
            "negative_state_pf": format(NEGATIVE_STATE_PF, "f"),
            "supportive_multiplier": format(SUPPORTIVE_MULTIPLIER, "f"),
            "mixed_multiplier": format(MIXED_MULTIPLIER, "f"),
            "cautious_multiplier": format(CAUTIOUS_MULTIPLIER, "f"),
            "axes": list(_AXES),
        },
        "state_table": [item.payload() for item in table],
        "train": {
            "equal_risk": train_equal,
            "capital_weighted": train_weighted,
            "context_counts": train_contexts,
        },
        "oos": {
            "equal_risk": oos_equal,
            "capital_weighted": oos_weighted,
            "context_counts": oos_contexts,
        },
        "oos_audit_rows": audit,
        "governance": {
            "trade_admission_changed": False,
            "trade_count_changed": False,
            "entry_changed": False,
            "initial_stop_changed": False,
            "target_changed": False,
            "lifecycle_changed": False,
            "fit_uses_train_terminal_pnl": True,
            "oos_runtime_uses_terminal_pnl": False,
            "oos_runtime_uses_future_bar": False,
            "oos_runtime_uses_fold_identity": False,
            "oos_runtime_uses_calendar_date_as_edge_feature": False,
            "market_specific_fit": True,
            "policy_promoted": False,
            "demo_eligible": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def to_json(path: Path) -> str:
    return json.dumps(
        replay(path),
        sort_keys=True,
        separators=(",", ":"),
    )
