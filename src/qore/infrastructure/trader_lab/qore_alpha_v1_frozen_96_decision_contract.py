"""QORE-alpha v1: FROZEN 96-factor search and STOP-before-PnL gates.

Independent QORE research, not TTrades-authentic/VT08, no LIVE.
Single GitHub reproducible experimental contract; not a backtest engine.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from itertools import product
from zoneinfo import ZoneInfo

SPACE_SCHEMA = "qore.alpha.v1.frozen_96_20261011"
NY = ZoneInfo("America/New_York")
ENTRIES = ("POSITIONAL_C3", "CISD_RETEST")
SESSIONS = ("ASIA", "LONDON", "NEW_YORK")
STOPS = ("PS", "EQ_M30", "BREAKER", "ATR_X1")
TARGETS = ("R1", "R2", "R3", "EXTERNAL_LIQUIDITY")
MARKETS = ("EURJPY", "USDCHF", "NZDUSD", "CADJPY", "USDCAD")
TRAIN_START = date(2022, 1, 1)
VALIDATE_START = date(2024, 7, 1)
TEST_START = date(2025, 7, 1)
TEST_END_EXCLUSIVE = date(2026, 7, 1)
PF_TRAIN = Decimal("1.40")
PF_VALIDATE = Decimal("1.30")
PF_TEST = Decimal("1.20")
PF_PAPER = Decimal("1.20")
MAX_DD_PCT = Decimal("20")
MAX_WINRATE_DELTA = Decimal("0.15")
RISK_PER_TRADE_PCT = Decimal("0.1")
BONFERRONI_FAMILY_ALPHA = Decimal("0.05")
BONFERRONI_PER_TEST_ALPHA = BONFERRONI_FAMILY_ALPHA / 96


@dataclass(frozen=True, slots=True)
class Variant:
    variant_id: str
    entry: str
    session: str
    stop: str
    target: str

    def as_dict(self) -> dict[str, str]:
        return {
            "variant_id": self.variant_id, "entry": self.entry,
            "session": self.session, "stop": self.stop,
            "target": self.target,
        }


VARIANTS = tuple(
    Variant(f"QALPHA-V{i:03d}", entry, session, stop, target)
    for i, (entry, session, stop, target) in enumerate(
        product(ENTRIES, SESSIONS, STOPS, TARGETS), start=1
    )
)
VARIANT_IDS = frozenset(x.variant_id for x in VARIANTS)
assert len(VARIANTS) == 96 and len(VARIANT_IDS) == 96


def frozen_manifest() -> dict[str, object]:
    """Deterministic content, no market data and no PnL consulted."""
    body = {
        "schema": SPACE_SCHEMA,
        "identity": "QORE-alpha v1 NOT TTrades source faithful",
        "features": {
            "mother": "M30_SINGLE_SWEEP_C2_CLOSURE",
            "confirmation": "M3_CISD_PROTECTED_SWING_CLOSED_BEFORE_C3",
            "entries": ENTRIES, "sessions": SESSIONS,
            "stops": STOPS, "targets": TARGETS,
        },
        "markets": MARKETS,
        "splits": {
            "TRAIN": [TRAIN_START.isoformat(), VALIDATE_START.isoformat()],
            "VALIDATE": [VALIDATE_START.isoformat(), TEST_START.isoformat()],
            "INTERNAL_TEST": [TEST_START.isoformat(), TEST_END_EXCLUSIVE.isoformat()],
        },
        "gates": {
            "train_pf_gross_strict_above": str(PF_TRAIN),
            "validate_pf_gross_strict_above": str(PF_VALIDATE),
            "train_min_fills": 50, "validate_min_fills": 25,
            "max_drawdown_percent_strict_below": str(MAX_DD_PCT),
            "max_winrate_difference_absolute": str(MAX_WINRATE_DELTA),
            "internal_test_pf_gross_min_inclusive": str(PF_TEST),
            "paper_pf_net_strict_above": str(PF_PAPER),
            "paper_calendar_months": 3,
            "live_start_risk_per_trade_percent": str(RISK_PER_TRADE_PCT),
            "risk_per_trade_percent_to_calculate_dd": str(RISK_PER_TRADE_PCT),
            "one_winner": True,
            "tie_break": "LEXICOGRAPHIC_VARIANT_ID",
        },
        "statistical_disclosure": {
            "pf_1_40_is_bonferroni_adjusted": False,
            "bonferroni_family_alpha": str(BONFERRONI_FAMILY_ALPHA),
            "bonferroni_each_alpha": str(BONFERRONI_PER_TEST_ALPHA),
            "p_values_not_predefined_no_fwer_claim": True,
        },
        "variants": [x.as_dict() for x in VARIANTS],
    }
    return {
        **body,
        "sha256": hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def session_of(opened_at: datetime) -> str | None:
    if opened_at.utcoffset() is None:
        raise ValueError("naive candle timestamp")
    local = opened_at.astimezone(NY)
    hm = (local.hour, local.minute)
    if (19, 0) <= hm <= (23, 59):
        return "ASIA"
    if (2, 0) <= hm < (5, 0):
        return "LONDON"
    if (8, 0) <= hm < (11, 0):
        return "NEW_YORK"
    return None


def segment_of(opened_at: datetime) -> str | None:
    if opened_at.utcoffset() is None:
        raise ValueError("naive candle timestamp")
    d = opened_at.astimezone(NY).date()
    if TRAIN_START <= d < VALIDATE_START:
        return "TRAIN"
    if VALIDATE_START <= d < TEST_START:
        return "VALIDATE"
    if TEST_START <= d < TEST_END_EXCLUSIVE:
        return "INTERNAL_TEST"
    return None


def validate_source_coverage(
    *,
    market: str,
    first_m3_open: datetime,
    last_m3_close: datetime,
    months_with_m3: frozenset[str],
    first_m15_open: datetime | None = None,
    last_m15_close: datetime | None = None,
) -> dict[str, object]:
    """Necessary coverage check only, not proof of gapless FX/tick dataset.

    January 1 may be a holiday. First raw trading M3 may occur Jan 2/3;
    accept first business-week opening (<= Jan 7) as necessary condition.
    """
    if market not in MARKETS:
        raise ValueError("market outside preregistered fixed five")
    clocks = (first_m3_open, last_m3_close)
    if any(x.utcoffset() is None for x in clocks):
        raise ValueError("source must have aware timestamps")
    first = first_m3_open.astimezone(NY)
    last = last_m3_close.astimezone(NY)
    requirements: list[str] = []
    if first.date() > date(2022, 1, 7):
        requirements.append("M3_TRAIN_2022_MISSING")
    if last.date() < date(2026, 6, 30):
        requirements.append("M3_INTERNAL_TEST_END_MISSING")
    cursor = date(2022, 1, 1)
    expected_months = set()
    while cursor < TEST_END_EXCLUSIVE:
        expected_months.add(cursor.strftime("%Y-%m"))
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    missing = sorted(expected_months - months_with_m3)
    if missing:
        requirements.append("M3_MONTHS_WITHOUT_ANY_BAR")
    if first_m15_open is None or last_m15_close is None:
        requirements.append("M15_INDEPENDENT_SOURCE_NOT_ATTESTED")
    elif (
        first_m15_open.astimezone(NY).date() > date(2022, 1, 7)
        or last_m15_close.astimezone(NY).date() < date(2026, 6, 30)
    ):
        requirements.append("M15_INDEPENDENT_PERIOD_INCOMPLETE")
    return {
        "schema": SPACE_SCHEMA,
        "market": market,
        "m3_first_open": first.isoformat(),
        "m3_last_close": last.isoformat(),
        "m15_first_open": first_m15_open.isoformat() if first_m15_open else None,
        "m15_last_close": last_m15_close.isoformat() if last_m15_close else None,
        "months_without_m3": missing,
        "status": "BLOCKED_DATA_COVERAGE" if requirements else "BOUNDARIES_ONLY_OK_MORE_QA_REQUIRED",
        "blockers": requirements,
        "history_source_complete_proven": False,
        "broker_bid_ask_fees_proven": False,
        "variants_backtested": 0,
        "holdout_accessed": False,
    }


@dataclass(frozen=True, slots=True)
class SegmentMetrics:
    variant_id: str
    segment: str
    pf_gross: Decimal
    trades: int
    max_dd_percent: Decimal
    win_rate: Decimal

    def validate(self) -> None:
        if self.variant_id not in VARIANT_IDS:
            raise ValueError("97th/unknown variant is prohibited")
        if self.segment not in ("TRAIN", "VALIDATE", "INTERNAL_TEST"):
            raise ValueError("unknown/holdout segment")
        if (
            self.trades < 0 or self.pf_gross < 0
            or self.max_dd_percent < 0
            or not (Decimal(0) <= self.win_rate <= Decimal(1))
        ):
            raise ValueError("invalid economic metrics")


class ScreeningStatus(StrEnum):
    NO_PASS_STOP = "NO_PASS_STOP_FEATURE_SET"
    ONE_WINNER_LOCKED = "ONE_WINNER_LOCKED_FOR_INTERNAL_TEST"
    REVIEW_REQUIRED = "THREE_PLUS_PASS_SPLIT_REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class ScreeningDecision:
    status: ScreeningStatus
    passing_variant_ids: tuple[str, ...]
    winner_id: str | None
    test_internal_authorized: bool


def screen_train_validate(
    train: tuple[SegmentMetrics, ...],
    validate: tuple[SegmentMetrics, ...],
    *,
    coverage_verified: bool,
    broker_cost_proven: bool,
) -> ScreeningDecision:
    """Filter all 96 only after data/cost gates. Deterministic choose ONE."""
    if not (coverage_verified and broker_cost_proven):
        raise ValueError("DATA_OR_PHYSICAL_COST_GATE_BLOCKED; do not score variants")
    for m in train + validate:
        m.validate()
    if (
        len(train) != 96 or len(validate) != 96
        or {m.variant_id for m in train} != VARIANT_IDS
        or {m.variant_id for m in validate} != VARIANT_IDS
    ):
        raise ValueError("must score exactly 96 variants on BOTH train and validate")
    if (
        len({m.variant_id for m in train}) != 96
        or len({m.variant_id for m in validate}) != 96
    ):
        raise ValueError("duplicated variant contaminates multiple testing")
    if any(m.segment != "TRAIN" for m in train) or any(
        m.segment != "VALIDATE" for m in validate
    ):
        raise ValueError("segment leakage/reassignment")
    validated = {m.variant_id: m for m in validate}
    qualified = [
        m.variant_id
        for m in train
        if (
            m.trades >= 50 and m.pf_gross > PF_TRAIN
            and m.max_dd_percent < MAX_DD_PCT
            and (v := validated[m.variant_id]).trades >= 25
            and v.pf_gross > PF_VALIDATE
            and v.max_dd_percent < MAX_DD_PCT
            and abs(m.win_rate - v.win_rate) <= MAX_WINRATE_DELTA
        )
    ]
    ranked = tuple(sorted(
        qualified, key=lambda x: (-validated[x].pf_gross, x),
    ))
    if not ranked:
        return ScreeningDecision(ScreeningStatus.NO_PASS_STOP, (), None, False)
    return ScreeningDecision(
        ScreeningStatus.REVIEW_REQUIRED if len(ranked) >= 3
        else ScreeningStatus.ONE_WINNER_LOCKED,
        ranked, ranked[0], len(ranked) < 3,
    )


def internal_test_decision(
    winner: SegmentMetrics,
    screening: ScreeningDecision,
) -> str:
    winner.validate()
    if (
        screening.status is not ScreeningStatus.ONE_WINNER_LOCKED
        or not screening.test_internal_authorized
        or winner.variant_id != screening.winner_id
        or winner.segment != "INTERNAL_TEST"
    ):
        raise ValueError("one-winner/three-plus-review/segment violation")
    return (
        "PAPER_3_MONTHS_PROSPECTIVE_REQUIRED"
        if winner.pf_gross >= PF_TEST else "INTERNAL_TEST_NO_GO_CLOSE_FEATURE_SET"
    )
