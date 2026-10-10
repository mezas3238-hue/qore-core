"""Per-market deep replay forensics and falsification for QORE Capitalizer.

This layer consumes the immutable three-session replay cell ledgers. It is outcome-aware by
design because it is *post-replay forensic research*, never a decision-time strategy input.

The purpose is to falsify broad/universal assumptions before any stop, target, confidence, or
market-selection rule is proposed. Results are diagnostic only and may not be promoted directly
to source methodology or used as a fresh holdout.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
    allowed_markets,
)

IDENTITY = "QORE_CAPITALIZER_MARKET_DEEP_FALSIFICATION_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_FALSIFICATION_MATRIX_V1"
NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class CapitalizerForensicCohort:
    key: str
    trades: int
    wins: int
    losses: int
    flats: int
    total_gross_r: str
    profit_factor: str | None
    stop_exits: int
    target_exits: int
    session_exits: int


@dataclass(frozen=True, slots=True)
class CapitalizerFalsificationClaim:
    claim_id: str
    statement: str
    status: str
    evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in {"SUPPORTED_IN_PROXY", "FALSIFIED_IN_PROXY", "NOT_TESTABLE"}:
            raise ValueError("unsupported falsification status")
        if not self.claim_id or not self.statement or not self.evidence:
            raise ValueError("falsification claim requires identity, statement and evidence")


@dataclass(frozen=True, slots=True)
class CapitalizerDrawdownEpisode:
    peak_at: str | None
    trough_at: str
    drawdown_r: str
    recovery_at: str | None


@dataclass(frozen=True, slots=True)
class CapitalizerMarketDeepFalsificationReport:
    identity: str
    symbol: str
    session: str
    trades: int
    total_gross_r: str
    profit_factor: str | None
    max_drawdown_r: str
    max_losing_streak: int
    stop_exits: int
    target_exits: int
    session_exits: int
    ambiguous_stop_first_exits: int
    operating_sessions: int
    operating_sessions_over_max3: int
    max_candidates_one_operating_session: int
    max_drawdown_episode: CapitalizerDrawdownEpisode
    by_side: tuple[CapitalizerForensicCohort, ...]
    by_event_family: tuple[CapitalizerForensicCohort, ...]
    by_ny_hour: tuple[CapitalizerForensicCohort, ...]
    by_weekday: tuple[CapitalizerForensicCohort, ...]
    by_calendar_year: tuple[CapitalizerForensicCohort, ...]
    by_planned_reward_band: tuple[CapitalizerForensicCohort, ...]
    by_holding_band: tuple[CapitalizerForensicCohort, ...]
    falsification_claims: tuple[CapitalizerFalsificationClaim, ...]
    outcome_aware_forensics: bool = True
    decision_time_feature_allowed: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    fresh_holdout_claimed: bool = False
    source_methodology_modified: bool = False

    def __post_init__(self) -> None:
        if not self.outcome_aware_forensics:
            raise ValueError("deep falsification is explicitly post-outcome forensic research")
        if (
            self.decision_time_feature_allowed
            or self.rule_promotion_allowed
            or self.economic_candidate
            or self.fresh_holdout_claimed
            or self.source_methodology_modified
        ):
            raise ValueError("forensics cannot grant strategy/promotion authority")


@dataclass(frozen=True, slots=True)
class CapitalizerNineMarketFalsificationMatrix:
    identity: str
    markets: tuple[CapitalizerMarketDeepFalsificationReport, ...]
    complete_nine_market_universe: bool
    falsified_claim_counts: tuple[tuple[str, int], ...]
    markets_above_owner_dd_envelope: tuple[str, ...]
    markets_with_max3_binding: tuple[str, ...]
    markets_with_session_exit_residual: tuple[str, ...]
    markets_with_same_m5_ambiguity: tuple[str, ...]
    outcome_aware_forensics: bool = True
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if not self.outcome_aware_forensics:
            raise ValueError("matrix must remain outcome-aware research")
        if self.rule_promotion_allowed or self.economic_candidate or self.trader_certified:
            raise ValueError("falsification matrix cannot certify/promote Capitalizer")


def _profit_factor(values: tuple[Decimal, ...]) -> str | None:
    gross_profit = sum((value for value in values if value > 0), Decimal("0"))
    gross_loss = -sum((value for value in values if value < 0), Decimal("0"))
    if gross_loss == 0:
        return None
    return str(gross_profit / gross_loss)


def _cohort(key: str, rows: tuple[dict[str, Any], ...]) -> CapitalizerForensicCohort:
    values = tuple(Decimal(str(row["realized_gross_r"])) for row in rows)
    return CapitalizerForensicCohort(
        key=key,
        trades=len(rows),
        wins=sum(value > 0 for value in values),
        losses=sum(value < 0 for value in values),
        flats=sum(value == 0 for value in values),
        total_gross_r=str(sum(values, Decimal("0"))),
        profit_factor=_profit_factor(values),
        stop_exits=sum(row["exit_reason"] == "STOP" for row in rows),
        target_exits=sum(row["exit_reason"] == "TARGET" for row in rows),
        session_exits=sum(row["exit_reason"] == "SESSION_EXIT" for row in rows),
    )


def _group(
    rows: tuple[dict[str, Any], ...],
    key_fn: Any,
) -> tuple[CapitalizerForensicCohort, ...]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(key_fn(row))].append(row)
    return tuple(
        _cohort(key, tuple(grouped[key]))
        for key in sorted(grouped)
    )


def _operating_date(entry_at: datetime, session: CapitalizerSession) -> str:
    local = entry_at.astimezone(NEW_YORK)
    if session is CapitalizerSession.ASIA and local.hour < 2:
        return (local.date() - timedelta(days=1)).isoformat()
    return local.date().isoformat()


def _reward_band(row: dict[str, Any]) -> str:
    value = Decimal(str(row["planned_reward_r"]))
    if value < 1:
        return "LT_1R"
    if value < Decimal("1.5"):
        return "1_TO_LT_1_5R"
    if value < 2:
        return "1_5_TO_LT_2R"
    if value < 3:
        return "2_TO_LT_3R"
    return "GE_3R"


def _holding_band(row: dict[str, Any]) -> str:
    bars = int(row["bars_held"])
    if bars == 1:
        return "1_BAR"
    if bars <= 3:
        return "2_TO_3_BARS"
    if bars <= 6:
        return "4_TO_6_BARS"
    return "GE_7_BARS"


def _drawdown(
    rows: tuple[dict[str, Any], ...],
) -> tuple[Decimal, int, CapitalizerDrawdownEpisode]:
    equity = Decimal("0")
    peak = Decimal("0")
    peak_at: datetime | None = None
    current_streak = 0
    max_streak = 0
    max_dd = Decimal("0")
    dd_peak_at: datetime | None = None
    dd_peak_equity = Decimal("0")
    dd_trough_at: datetime | None = None

    for row in rows:
        value = Decimal(str(row["realized_gross_r"]))
        at = datetime.fromisoformat(str(row["exit_at"]))
        equity += value
        if equity > peak:
            peak = equity
            peak_at = at
        drawdown = peak - equity
        if drawdown > max_dd:
            max_dd = drawdown
            dd_peak_at = peak_at
            dd_peak_equity = peak
            dd_trough_at = at
        if value < 0:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0

    if dd_trough_at is None:
        dd_trough_at = datetime.fromisoformat(str(rows[-1]["exit_at"]))

    recovery_at: datetime | None = None
    if max_dd > 0:
        equity = Decimal("0")
        target_peak: Decimal | None = None
        for row in rows:
            value = Decimal(str(row["realized_gross_r"]))
            at = datetime.fromisoformat(str(row["exit_at"]))
            equity += value
            if at == dd_trough_at:
                target_peak = dd_peak_equity
                continue
            if target_peak is not None and at > dd_trough_at and equity >= target_peak:
                recovery_at = at
                break

    return (
        max_dd,
        max_streak,
        CapitalizerDrawdownEpisode(
            peak_at=None if dd_peak_at is None else dd_peak_at.isoformat(),
            trough_at=dd_trough_at.isoformat(),
            drawdown_r=str(max_dd),
            recovery_at=None if recovery_at is None else recovery_at.isoformat(),
        ),
    )


def _load_trade_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(root.rglob("capitalizer-*-three-session-replay-cell-v1-trades.jsonl"))
    if len(paths) != 1:
        raise ValueError(f"market forensics requires exactly one replay ledger, got {len(paths)}")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("replay trade row must be object")
            if raw.get("outcome_used_for_selection") is not False:
                raise ValueError("forensic input must originate from non-outcome-selected replay")
            rows.append(raw)
    if not rows:
        raise ValueError("market forensics requires at least one replay trade")
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                datetime.fromisoformat(str(row["entry_at"])),
                str(row["symbol"]),
            ),
        )
    )


def _universal_claims(
    *,
    report_symbol: str,
    max_dd: Decimal,
    by_side: tuple[CapitalizerForensicCohort, ...],
    by_event: tuple[CapitalizerForensicCohort, ...],
    by_hour: tuple[CapitalizerForensicCohort, ...],
    by_weekday: tuple[CapitalizerForensicCohort, ...],
    by_year: tuple[CapitalizerForensicCohort, ...],
    session_exits: int,
    ambiguities: int,
    sessions_over_max3: int,
) -> tuple[CapitalizerFalsificationClaim, ...]:
    def universal_positive(
        *,
        claim_id: str,
        statement: str,
        cohorts: tuple[CapitalizerForensicCohort, ...],
    ) -> CapitalizerFalsificationClaim:
        nonpositive = tuple(
            item.key
            for item in cohorts
            if Decimal(item.total_gross_r) <= 0
        )
        status = "SUPPORTED_IN_PROXY" if not nonpositive else "FALSIFIED_IN_PROXY"
        return CapitalizerFalsificationClaim(
            claim_id=claim_id,
            statement=statement,
            status=status,
            evidence=(
                f"cohorts={len(cohorts)}",
                f"nonpositive={','.join(nonpositive) if nonpositive else 'NONE'}",
            ),
        )

    return (
        CapitalizerFalsificationClaim(
            claim_id="OWNER_DD_ENVELOPE_LE_6R",
            statement=f"{report_symbol} proxy geometry remains within the Owner 6R DD ceiling.",
            status="SUPPORTED_IN_PROXY" if max_dd <= Decimal("6") else "FALSIFIED_IN_PROXY",
            evidence=(f"max_drawdown_r={max_dd}", "owner_ceiling_r=6"),
        ),
        universal_positive(
            claim_id="EVERY_CALENDAR_YEAR_POSITIVE",
            statement="Every consumed calendar-year cohort is gross-positive.",
            cohorts=by_year,
        ),
        universal_positive(
            claim_id="BOTH_DIRECTIONS_POSITIVE",
            statement="Every observed trade direction is gross-positive.",
            cohorts=by_side,
        ),
        universal_positive(
            claim_id="EVERY_EVENT_FAMILY_POSITIVE",
            statement="Every observed event-family cohort is gross-positive.",
            cohorts=by_event,
        ),
        universal_positive(
            claim_id="EVERY_NY_HOUR_POSITIVE",
            statement="Every observed New York clock-hour cohort is gross-positive.",
            cohorts=by_hour,
        ),
        universal_positive(
            claim_id="EVERY_WEEKDAY_POSITIVE",
            statement="Every observed weekday cohort is gross-positive.",
            cohorts=by_weekday,
        ),
        CapitalizerFalsificationClaim(
            claim_id="ALL_CANDIDATES_RESOLVE_STRUCTURALLY_INTRASESSION",
            statement=(
                "Every proxy candidate resolves by structural stop or target "
                "before session end."
            ),
            status="SUPPORTED_IN_PROXY" if session_exits == 0 else "FALSIFIED_IN_PROXY",
            evidence=(f"session_exits={session_exits}",),
        ),
        CapitalizerFalsificationClaim(
            claim_id="NO_SAME_M5_PRECEDENCE_AMBIGUITY",
            statement="No proxy candidate has same-M5 stop/target precedence ambiguity.",
            status="SUPPORTED_IN_PROXY" if ambiguities == 0 else "FALSIFIED_IN_PROXY",
            evidence=(f"same_m5_ambiguities={ambiguities}",),
        ),
        CapitalizerFalsificationClaim(
            claim_id="MAX3_NEVER_BINDS_WITHIN_MARKET",
            statement=(
                "A single market never produces more than MAX3 proxy candidates "
                "in one session."
            ),
            status=(
                "SUPPORTED_IN_PROXY"
                if sessions_over_max3 == 0
                else "FALSIFIED_IN_PROXY"
            ),
            evidence=(
                f"operating_sessions_over_max3={sessions_over_max3}",
                f"max3={MAX_EXECUTIONS_PER_SESSION}",
            ),
        ),
    )


def build_market_report(root: Path) -> CapitalizerMarketDeepFalsificationReport:
    rows = _load_trade_rows(root)
    symbols = {str(row["symbol"]) for row in rows}
    sessions = {str(row["session"]) for row in rows}
    if len(symbols) != 1 or len(sessions) != 1:
        raise ValueError("one market forensic report requires one symbol/session")
    symbol = next(iter(symbols))
    session = CapitalizerSession(next(iter(sessions)))
    if symbol not in allowed_markets(session):
        raise ValueError("market/session assignment drifted from frozen Capitalizer universe")

    values = tuple(Decimal(str(row["realized_gross_r"])) for row in rows)
    max_dd, max_streak, dd_episode = _drawdown(rows)
    session_exits = sum(row["exit_reason"] == "SESSION_EXIT" for row in rows)
    stop_exits = sum(row["exit_reason"] == "STOP" for row in rows)
    target_exits = sum(row["exit_reason"] == "TARGET" for row in rows)
    ambiguities = sum(bool(row["same_bar_stop_target_ambiguity"]) for row in rows)

    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        entry_at = datetime.fromisoformat(str(row["entry_at"]))
        counts[_operating_date(entry_at, session)] += 1
    sessions_over_max3 = sum(
        count > MAX_EXECUTIONS_PER_SESSION for count in counts.values()
    )

    by_side = _group(rows, lambda row: str(row["side"]))
    by_event = _group(
        tuple(
            {
                **row,
                "_event_family": event,
            }
            for row in rows
            for event in tuple(row["event_labels"])
        ),
        lambda row: str(row["_event_family"]),
    )
    by_hour = _group(
        rows,
        lambda row: f"{datetime.fromisoformat(str(row['entry_at'])).astimezone(NEW_YORK).hour:02d}",
    )
    by_weekday = _group(
        rows,
        lambda row: datetime.fromisoformat(str(row["entry_at"]))
        .astimezone(NEW_YORK)
        .strftime("%A")
        .upper(),
    )
    by_year = _group(
        rows,
        lambda row: datetime.fromisoformat(str(row["entry_at"])).year,
    )
    by_reward = _group(rows, _reward_band)
    by_holding = _group(rows, _holding_band)

    claims = _universal_claims(
        report_symbol=symbol,
        max_dd=max_dd,
        by_side=by_side,
        by_event=by_event,
        by_hour=by_hour,
        by_weekday=by_weekday,
        by_year=by_year,
        session_exits=session_exits,
        ambiguities=ambiguities,
        sessions_over_max3=sessions_over_max3,
    )

    return CapitalizerMarketDeepFalsificationReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session.value,
        trades=len(rows),
        total_gross_r=str(sum(values, Decimal("0"))),
        profit_factor=_profit_factor(values),
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        stop_exits=stop_exits,
        target_exits=target_exits,
        session_exits=session_exits,
        ambiguous_stop_first_exits=ambiguities,
        operating_sessions=len(counts),
        operating_sessions_over_max3=sessions_over_max3,
        max_candidates_one_operating_session=max(counts.values(), default=0),
        max_drawdown_episode=dd_episode,
        by_side=by_side,
        by_event_family=by_event,
        by_ny_hour=by_hour,
        by_weekday=by_weekday,
        by_calendar_year=by_year,
        by_planned_reward_band=by_reward,
        by_holding_band=by_holding,
        falsification_claims=claims,
    )


def write_market_report(
    report: CapitalizerMarketDeepFalsificationReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-market-deep-falsification-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        f"# QORE Capitalizer — {report.symbol} Deep Falsification V1",
        "",
        f"- Session: {report.session}",
        f"- Proxy trades: {report.trades}",
        f"- Gross PF: {report.profit_factor}",
        f"- Total gross R: {report.total_gross_r}",
        f"- Max proxy DD: {report.max_drawdown_r}R",
        f"- Max losing streak: {report.max_losing_streak}",
        (
            "- Stops / targets / session exits: "
            f"{report.stop_exits} / {report.target_exits} / {report.session_exits}"
        ),
        f"- Same-M5 ambiguities: {report.ambiguous_stop_first_exits}",
        f"- Operating sessions >MAX3: {report.operating_sessions_over_max3}",
        "",
        "## Universal falsification claims",
        "",
        "| Claim | Status | Evidence |",
        "|---|---|---|",
    ]
    for claim in report.falsification_claims:
        lines.append(
            f"| {claim.claim_id} | {claim.status} | {'; '.join(claim.evidence)} |"
        )
    (output / f"{stem}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _load_market_reports(root: Path) -> tuple[CapitalizerMarketDeepFalsificationReport, ...]:
    paths = sorted(root.rglob("capitalizer-*-market-deep-falsification-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"nine-market falsification matrix requires 9 reports, got {len(paths)}")
    reports: list[CapitalizerMarketDeepFalsificationReport] = []
    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("identity") != IDENTITY:
            raise ValueError("unexpected market falsification identity")
        reports.append(
            CapitalizerMarketDeepFalsificationReport(
                **{
                    **raw,
                    "max_drawdown_episode": CapitalizerDrawdownEpisode(
                        **raw["max_drawdown_episode"]
                    ),
                    "by_side": tuple(CapitalizerForensicCohort(**x) for x in raw["by_side"]),
                    "by_event_family": tuple(
                        CapitalizerForensicCohort(**x) for x in raw["by_event_family"]
                    ),
                    "by_ny_hour": tuple(
                        CapitalizerForensicCohort(**x) for x in raw["by_ny_hour"]
                    ),
                    "by_weekday": tuple(
                        CapitalizerForensicCohort(**x) for x in raw["by_weekday"]
                    ),
                    "by_calendar_year": tuple(
                        CapitalizerForensicCohort(**x) for x in raw["by_calendar_year"]
                    ),
                    "by_planned_reward_band": tuple(
                        CapitalizerForensicCohort(**x)
                        for x in raw["by_planned_reward_band"]
                    ),
                    "by_holding_band": tuple(
                        CapitalizerForensicCohort(**x) for x in raw["by_holding_band"]
                    ),
                    "falsification_claims": tuple(
                        CapitalizerFalsificationClaim(**x)
                        for x in raw["falsification_claims"]
                    ),
                }
            )
        )
    return tuple(sorted(reports, key=lambda item: item.symbol))


def build_matrix(root: Path) -> CapitalizerNineMarketFalsificationMatrix:
    reports = _load_market_reports(root)
    expected = {
        symbol
        for session in CapitalizerSession
        for symbol in allowed_markets(session)
    }
    observed = {report.symbol for report in reports}
    if observed != expected:
        raise ValueError("nine-market falsification matrix universe mismatch")

    claim_ids = sorted(
        {claim.claim_id for report in reports for claim in report.falsification_claims}
    )
    counts = tuple(
        (
            claim_id,
            sum(
                claim.status == "FALSIFIED_IN_PROXY"
                for report in reports
                for claim in report.falsification_claims
                if claim.claim_id == claim_id
            ),
        )
        for claim_id in claim_ids
    )
    return CapitalizerNineMarketFalsificationMatrix(
        identity=MATRIX_IDENTITY,
        markets=reports,
        complete_nine_market_universe=True,
        falsified_claim_counts=counts,
        markets_above_owner_dd_envelope=tuple(
            report.symbol
            for report in reports
            if Decimal(report.max_drawdown_r) > Decimal("6")
        ),
        markets_with_max3_binding=tuple(
            report.symbol
            for report in reports
            if report.operating_sessions_over_max3 > 0
        ),
        markets_with_session_exit_residual=tuple(
            report.symbol for report in reports if report.session_exits > 0
        ),
        markets_with_same_m5_ambiguity=tuple(
            report.symbol
            for report in reports
            if report.ambiguous_stop_first_exits > 0
        ),
    )


def write_matrix(report: CapitalizerNineMarketFalsificationMatrix, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-nine-market-falsification-matrix-v1.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# QORE Capitalizer — Nine-Market Falsification Matrix V1",
        "",
        "- Post-replay forensic evidence only.",
        "- No cohort becomes a strategy rule from this artifact.",
        "- No outcome-aware ranking is allowed into decision-time cognition.",
        "",
        "| Market | Session | Trades | PF | Total R | Max DD | LS | >MAX3 sessions |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for market in report.markets:
        lines.append(
            f"| {market.symbol} | {market.session} | {market.trades} | "
            f"{market.profit_factor} | {market.total_gross_r} | "
            f"{market.max_drawdown_r} | {market.max_losing_streak} | "
            f"{market.operating_sessions_over_max3} |"
        )
    lines.extend(
        [
            "",
            (
                "- Markets above Owner 6R DD envelope: "
                f"{', '.join(report.markets_above_owner_dd_envelope)}"
            ),
            f"- Markets with MAX3 binding: {', '.join(report.markets_with_max3_binding)}",
            (
                "- Markets with session-exit residual: "
                f"{', '.join(report.markets_with_session_exit_residual)}"
            ),
            (
                "- Markets with same-M5 ambiguity: "
                f"{', '.join(report.markets_with_same_m5_ambiguity)}"
            ),
        ]
    )
    (output / "capitalizer-nine-market-falsification-matrix-v1.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Capitalizer deep market falsification")
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("input_root", type=Path)
    market.add_argument("output", type=Path)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        market_report = build_market_report(args.input_root)
        write_market_report(market_report, args.output)
        print(
            json.dumps(
                {
                    "symbol": market_report.symbol,
                    "trades": market_report.trades,
                    "profit_factor": market_report.profit_factor,
                    "max_drawdown_r": market_report.max_drawdown_r,
                    "max_losing_streak": market_report.max_losing_streak,
                    "falsified_claims": sum(
                        claim.status == "FALSIFIED_IN_PROXY"
                        for claim in market_report.falsification_claims
                    ),
                },
                sort_keys=True,
            )
        )
        return

    matrix_report = build_matrix(args.input_root)
    write_matrix(matrix_report, args.output)
    print(
        json.dumps(
            {
                "identity": matrix_report.identity,
                "markets": len(matrix_report.markets),
                "markets_above_owner_dd_envelope": list(
                    matrix_report.markets_above_owner_dd_envelope
                ),
                "markets_with_max3_binding": list(
                    matrix_report.markets_with_max3_binding
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
