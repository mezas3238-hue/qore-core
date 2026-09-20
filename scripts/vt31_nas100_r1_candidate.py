"""Frozen NAS100 specialist candidate for the VT-31 AM Silver Bullet program.

The implementation deliberately returns to the source-anchored R2.2 setup and
uses consumed CIBO Atlas evidence only to remove two demonstrated R8 drifts:
fixed-2R destination substitution and premature M1 protected-swing trailing.
It never opens data, places orders, or authorizes live/production trading.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import UTC
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _metrics,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

CANDIDATE_ID = "VT31_NAS100_R1"
MARKET = "NAS100"
FRICTION = Decimal("0.05")
LIFECYCLE_MINUTE = 16 * 60
THRESHOLDS = tuple(Decimal(x) for x in ("0.25", "0.5", "1", "1.5", "2", "2.5", "3"))
CIBO_BASE_SHA = "6dc334723de5b7dca187e12b3a8ff531f4f1045e"
CIBO_EIGHT_LEDGER_RUN_ID = 35175782935
CIBO_EIGHT_LEDGER_ARTIFACT_ID = 10478487667
CIBO_EIGHT_LEDGER_DIGEST = "sha256:17c8d1909152d87ed67a05cd986fa9cca39b2ac92598d36822c38e8afccde192"
CIBO_GAP_RUN_ID = 35149220431
CIBO_GAP_ARTIFACT_ID = 10468701836
R8_DEFINITIVE_ARTIFACT_ID = 10440468729


def contract_payload() -> dict[str, object]:
    """Return the immutable NAS100 R1 contract before any new holdout opens."""
    policy = Vt31R22ExecutionPolicy()
    return {
        "candidate_id": CANDIDATE_ID,
        "market": MARKET,
        "timezone": "America/New_York",
        "reference": "09:00-10:00-frozen-M1",
        "setup_window": "10:00-11:00-AM-Silver-Bullet",
        "source_model": "ttrades-am-silver-bullet-nq-r2.2",
        "raid": "strict-first-side;both-sides-swept-abstain",
        "confirmation": "post-raid-structural-close-source-formalization",
        "entry_families": ["breaker", "fair-value-gap", "order-block"],
        "execution_policy_fingerprint": policy.fingerprint(),
        "entry_price": "r2.2-versioned-zone-translation;fail-closed-ambiguity",
        "initial_stop": "source-methodological-swing-extreme-no-buffer",
        "target": "opposite-frozen-09-reference-boundary",
        "management": "source-3R-boundary-then-single-breakeven;no-protected-swing-trailing",
        "pending_expiry": "11:00-America/New_York",
        "filled_lifecycle": "16:00-America/New_York",
        "same_bar_policy": "censor-unresolved-stop-target-path;3R-arms-BE-next-bar",
        "gap_policy": "censor-open-trade-on-M1-discontinuity",
        "cross_index": "telemetry-only-not-entry-filter",
        "r8_empirical_quality_filters": "not-inherited",
        "friction_r_per_trade": format(FRICTION, "f"),
        "holdout_order": "freeze->one-intact-1Y-holdout->permanently-consume->unchanged-WFO",
        "holdout_retuning": False,
        "holdout_gates": {
            "terminal_sample": ">=30",
            "stressed_mean_r": ">0",
            "stressed_profit_factor": ">=1.10",
            "stressed_max_drawdown_r": "<=20",
            "positive_quarters": ">=3-of-4-eligible",
            "monte_carlo_positive_terminal_probability": ">=0.70",
            "monte_carlo_p95_max_drawdown_r": "<=20",
        },
        "consumed_evidence_binding": {
            "cibo_base_sha": CIBO_BASE_SHA,
            "eight_ledger_run_id": CIBO_EIGHT_LEDGER_RUN_ID,
            "eight_ledger_artifact_id": CIBO_EIGHT_LEDGER_ARTIFACT_ID,
            "eight_ledger_digest": CIBO_EIGHT_LEDGER_DIGEST,
            "specialist_gap_run_id": CIBO_GAP_RUN_ID,
            "specialist_gap_artifact_id": CIBO_GAP_ARTIFACT_ID,
            "r8_definitive_artifact_id": R8_DEFINITIVE_ARTIFACT_ID,
        },
        "research_only": True,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def contract_fingerprint() -> str:
    encoded = json.dumps(contract_payload(), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _touch(bar: object, price: Decimal) -> bool:
    return _d(getattr(bar, "low")) <= price <= _d(getattr(bar, "high"))


def _local_minute(bar: object) -> int:
    opened = getattr(bar, "opened_at")
    local = opened.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York"))
    return local.hour * 60 + local.minute


def _favorable_adverse(bar: object, side: str, entry: Decimal, risk: Decimal) -> tuple[Decimal, Decimal]:
    high = _d(getattr(bar, "high"))
    low = _d(getattr(bar, "low"))
    if side == "long":
        favorable = (high - entry) / risk
        adverse = (entry - low) / risk
    else:
        favorable = (entry - low) / risk
        adverse = (high - entry) / risk
    return max(Decimal(0), favorable), max(Decimal(0), adverse)


def _terminal_r(side: str, entry: Decimal, stop: Decimal, risk: Decimal) -> Decimal:
    return (stop - entry) / risk if side == "long" else (entry - stop) / risk


def _simulate(day_bars: tuple[object, ...], setup: Vt31R22ExecutableSetup) -> dict[str, object]:
    side = setup.side.value
    entry = setup.entry_price
    initial_stop = setup.stop_price
    target = setup.target_price
    three_r = setup.three_r_price
    risk = setup.initial_risk
    if risk <= 0:
        return {"status": "censored-invalid-risk"}

    fill_index: int | None = None
    for index, bar in enumerate(day_bars):
        if getattr(bar, "opened_at") < setup.decision_at:
            continue
        if _local_minute(bar) >= 11 * 60:
            break
        if _touch(bar, entry):
            fill_index = index
            break
    if fill_index is None:
        return {"status": "no-fill"}

    first = day_bars[fill_index]
    stop_hit = _d(getattr(first, "low")) <= initial_stop if side == "long" else _d(getattr(first, "high")) >= initial_stop
    target_hit = _d(getattr(first, "high")) >= target if side == "long" else _d(getattr(first, "low")) <= target
    if stop_hit or target_hit:
        return {"status": "censored-fill-bar-path"}

    current_stop = initial_stop
    be_armed = False
    max_favorable = Decimal(0)
    max_adverse = Decimal(0)
    mfe_at = getattr(first, "closed_at")
    thresholds_hit: dict[str, bool] = {format(level, "f"): False for level in THRESHOLDS}
    previous = first
    filled_at = getattr(first, "closed_at")
    exit_reason: str | None = None
    exit_at = None
    terminal: Decimal | None = None

    for index in range(fill_index + 1, len(day_bars)):
        bar = day_bars[index]
        if _local_minute(bar) >= LIFECYCLE_MINUTE:
            break
        if getattr(bar, "opened_at") != getattr(previous, "closed_at"):
            return {"status": "censored-gap-after-fill"}
        previous = bar
        favorable, adverse = _favorable_adverse(bar, side, entry, risk)
        if favorable > max_favorable:
            max_favorable = favorable
            mfe_at = getattr(bar, "closed_at")
        max_adverse = max(max_adverse, adverse)
        for level in THRESHOLDS:
            if favorable >= level:
                thresholds_hit[format(level, "f")] = True

        high = _d(getattr(bar, "high"))
        low = _d(getattr(bar, "low"))
        hit_stop = low <= current_stop if side == "long" else high >= current_stop
        hit_target = high >= target if side == "long" else low <= target
        if hit_stop and hit_target:
            return {"status": "censored-same-bar-stop-target"}
        if hit_stop:
            terminal = _terminal_r(side, entry, current_stop, risk)
            exit_reason = "breakeven-stop" if current_stop == entry else "initial-stop"
            exit_at = getattr(bar, "closed_at")
            break
        if hit_target:
            terminal = abs(target - entry) / risk
            exit_reason = "structural-target"
            exit_at = getattr(bar, "closed_at")
            break

        if not be_armed:
            touched_three_r = high >= three_r if side == "long" else low <= three_r
            if touched_three_r:
                be_armed = True
                current_stop = entry

    if terminal is None:
        eligible = [bar for bar in day_bars[fill_index:] if _local_minute(bar) < LIFECYCLE_MINUTE]
        if not eligible:
            return {"status": "censored-no-lifecycle-close"}
        final = eligible[-1]
        close = _d(getattr(final, "close"))
        terminal = (close - entry) / risk if side == "long" else (entry - close) / risk
        exit_reason = "16:00-lifecycle"
        exit_at = getattr(final, "closed_at")

    target_r = abs(target - entry) / risk
    return {
        "status": "terminal",
        "local_date": _day(setup.decision_at).isoformat(),
        "side": side,
        "signal_at": setup.decision_at.astimezone(UTC).isoformat(),
        "filled_at": filled_at.astimezone(UTC).isoformat(),
        "exit_at": exit_at.astimezone(UTC).isoformat(),
        "entry_family": setup.selected_family.value,
        "candidate_families": [family.value for family in setup.candidate_families],
        "entry": format(entry, "f"),
        "initial_stop": format(initial_stop, "f"),
        "structural_target": format(target, "f"),
        "planned_target_r": format(target_r, "f"),
        "three_r_boundary": format(three_r, "f"),
        "breakeven_armed": be_armed,
        "exit_reason": exit_reason,
        "r_multiple": format(terminal, "f"),
        "mfe_r": format(max_favorable, "f"),
        "mae_r": format(max_adverse, "f"),
        "mfe_at": mfe_at.astimezone(UTC).isoformat(),
        "minutes_fill_to_mfe": str(int((mfe_at - filled_at).total_seconds() // 60)),
        "minutes_fill_to_exit": str(int((exit_at - filled_at).total_seconds() // 60)),
        "excursion_reach": thresholds_hit,
    }


def _monte_carlo(trades: list[dict[str, object]]) -> tuple[dict[str, object], dict[str, bool]]:
    values = [Decimal(cast(str, trade["r_multiple"])) for trade in trades]
    n = len(values)
    if not values:
        return (
            {"paths": 10000, "positive_terminal_probability": "0", "p95_max_drawdown_r": "0"},
            {"positive_terminal_probability_at_least_0_70": False, "p95_max_drawdown_at_most_20r": True},
        )
    domain = b"qore:vt31-nas100-r1:moving-block-bootstrap-v1"
    terminals: list[Decimal] = []
    drawdowns: list[Decimal] = []
    for path_index in range(10000):
        sampled: list[Decimal] = []
        block_index = 0
        while len(sampled) < n:
            digest = hashlib.sha256(domain + b":" + str(path_index).encode() + b":" + str(block_index).encode()).digest()
            start = int.from_bytes(digest, "big") % n
            sampled.extend(values[(start + offset) % n] for offset in range(5))
            block_index += 1
        equity = Decimal(0)
        peak = Decimal(0)
        dd = Decimal(0)
        for value in sampled[:n]:
            equity += value - FRICTION
            peak = max(peak, equity)
            dd = max(dd, peak - equity)
        terminals.append(equity)
        drawdowns.append(dd)
    terminals.sort()
    drawdowns.sort()
    probability = Decimal(sum(value > 0 for value in terminals)) / Decimal(10000)
    p95_dd = drawdowns[(len(drawdowns) - 1) * 95 // 100]
    report = {
        "algorithm": "sha256-domain-separated-moving-block-bootstrap-v1",
        "paths": 10000,
        "block_length": 5,
        "positive_terminal_probability": format(probability, "f"),
        "p05_terminal_r": format(terminals[(len(terminals) - 1) * 5 // 100], "f"),
        "p50_terminal_r": format(terminals[(len(terminals) - 1) * 50 // 100], "f"),
        "p95_max_drawdown_r": format(p95_dd, "f"),
    }
    gates = {
        "positive_terminal_probability_at_least_0_70": probability >= Decimal("0.70"),
        "p95_max_drawdown_at_most_20r": p95_dd <= Decimal(20),
    }
    return report, gates


def replay(evidence_path: Path) -> dict[str, object]:
    """Replay the frozen NAS100 specialist over one evidence file."""
    series, account, evidence, checked, evidence_sha, provider = load_market_evidence(evidence_path)
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("VT31_NAS100_R1 requires NAS100 evidence only")
    by_day: dict[object, list[object]] = defaultdict(list)
    for bar in series:
        by_day[_day(getattr(bar, "opened_at"))].append(bar)

    trades: list[dict[str, object]] = []
    status_counts: Counter[str] = Counter()
    source_setups = 0
    executable_setups = 0
    policy = Vt31R22ExecutionPolicy()

    for local_day in sorted(by_day):
        day_bars = tuple(by_day[local_day])
        reference = tuple(bar for bar in day_bars if (9, 0, 0) <= _wall(getattr(bar, "opened_at")) < (10, 0, 0))
        session = tuple((index, bar) for index, bar in enumerate(day_bars) if (10, 0, 0) <= _wall(getattr(bar, "opened_at")) < (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status_counts["day-incomplete-reference-or-session"] += 1
            continue
        prefix = list(reference)
        selected: Vt31R22ExecutableSetup | None = None
        for _, bar in session:
            prefix.append(bar)
            evaluation = evaluate_vt31_r2_2_source(
                instrument=getattr(bar, "instrument"),
                as_of=getattr(bar, "closed_at"),
                m1_candles=cast(Any, tuple(prefix)),
                evidence_fingerprint=evidence,
            )
            if evaluation.setup is None:
                continue
            source_setups += 1
            executable, _ = make_executable_setup(evaluation.setup, policy)
            if executable is None:
                status_counts["source-setup-not-executable"] += 1
                break
            selected = executable
            executable_setups += 1
            break
        if selected is None:
            status_counts["no-executable-setup"] += 1
            continue
        outcome = _simulate(day_bars, selected)
        status = cast(str, outcome["status"])
        status_counts[status] += 1
        if status == "terminal":
            trades.append(outcome)

    trades.sort(key=lambda trade: cast(str, trade["signal_at"]))
    aggregate = _metrics(trades)
    stress = _metrics(trades, friction=FRICTION)
    side_stress = {
        side: _metrics([trade for trade in trades if trade["side"] == side], friction=FRICTION)
        for side in ("long", "short")
    }
    family_stress = {
        family: _metrics([trade for trade in trades if trade["entry_family"] == family], friction=FRICTION)
        for family in ("breaker", "fair-value-gap", "order-block")
    }
    quarters: dict[str, dict[str, object]] = {}
    for trade in trades:
        date = cast(str, trade["local_date"])
        month = int(date[5:7])
        key = f"{date[:4]}-Q{(month - 1) // 3 + 1}"
        quarters.setdefault(key, {})
    for key in list(quarters):
        quarters[key] = _metrics(
            [
                trade
                for trade in trades
                if f"{cast(str, trade['local_date'])[:4]}-Q{(int(cast(str, trade['local_date'])[5:7]) - 1) // 3 + 1}" == key
            ],
            friction=FRICTION,
        )
    eligible_quarters = [value for value in quarters.values() if cast(int, value["sample"]) >= 5]
    mc, mc_gates = _monte_carlo(trades)
    holdout_gates = {
        "terminal_sample_at_least_30": cast(int, aggregate["sample"]) >= 30,
        "stressed_mean_positive": Decimal(cast(str, stress["mean_r"])) > 0 if trades else False,
        "stressed_profit_factor_at_least_1_10": bool(trades)
        and stress["profit_factor"] is not None
        and Decimal(cast(str, stress["profit_factor"])) >= Decimal("1.10"),
        "stressed_max_drawdown_at_most_20r": bool(trades)
        and Decimal(cast(str, stress["max_drawdown_r"])) <= Decimal(20),
        "three_of_four_eligible_quarters_positive": len(eligible_quarters) >= 4
        and sum(Decimal(cast(str, value["mean_r"])) > 0 for value in eligible_quarters) * 4 >= len(eligible_quarters) * 3,
        **mc_gates,
    }
    excursions = {
        format(level, "f"): {
            "count": sum(bool(cast(dict[str, bool], trade["excursion_reach"])[format(level, "f")]) for trade in trades),
            "rate": format(
                Decimal(sum(bool(cast(dict[str, bool], trade["excursion_reach"])[format(level, "f")]) for trade in trades)) / Decimal(len(trades)),
                "f",
            )
            if trades
            else "0",
        }
        for level in THRESHOLDS
    }
    return {
        "schema": "qore.trader_lab.vt31_nas100_r1.v1",
        "candidate_id": CANDIDATE_ID,
        "contract": contract_payload(),
        "contract_fingerprint": contract_fingerprint(),
        "evidence": {
            "market": MARKET,
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
            "bar_count": len(series),
            "first_opened_at": getattr(series[0], "opened_at").astimezone(UTC).isoformat(),
            "last_closed_at": getattr(series[-1], "closed_at").astimezone(UTC).isoformat(),
        },
        "market_days": len(by_day),
        "source_setups": source_setups,
        "executable_setups": executable_setups,
        "status_counts": dict(sorted(status_counts.items())),
        "aggregate": aggregate,
        "stress_0_05r": stress,
        "side_stress": side_stress,
        "entry_family_stress": family_stress,
        "quarter_stress": quarters,
        "excursion_reach": excursions,
        "monte_carlo": mc,
        "holdout_gates": holdout_gates,
        "passes_holdout_gates": all(holdout_gates.values()),
        "trades": trades,
        "research_only": True,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def self_test() -> None:
    contract = contract_payload()
    assert contract["candidate_id"] == CANDIDATE_ID
    assert contract["market"] == MARKET
    assert contract["target"] == "opposite-frozen-09-reference-boundary"
    assert contract["management"] == "source-3R-boundary-then-single-breakeven;no-protected-swing-trailing"
    assert contract["holdout_retuning"] is False
    assert contract["live_authorized"] is False
    assert contract["production_authorized"] is False
    assert len(contract_fingerprint()) == 64


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--self-test"]:
        self_test()
        print(json.dumps({"candidate_id": CANDIDATE_ID, "contract_fingerprint": contract_fingerprint()}, sort_keys=True))
        return 0
    if len(args) != 1:
        print("usage: vt31_nas100_r1_candidate.py NAS100_MARKET_EVIDENCE_JSON | --self-test")
        return 2
    print(json.dumps(replay(Path(args[0])), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
