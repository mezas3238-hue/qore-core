"""VT31 clean-room cognitive I/O audit: real calls, causal inputs and effects."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.cognitive_telemetry import (
    COMPONENT_ROLES,
    CognitiveTelemetry,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    MethodologyDecision,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.trader import (
    UnifiedVT31Observation,
    VT31Trader,
)


def _bar(
    t: datetime, *, o: str = "100", h: str = "101",
    lo: str = "99", c: str = "100.5",
) -> M1Bar:
    return M1Bar(
        opened_at=t, closed_at=t + timedelta(minutes=1),
        open=Decimal(o), high=Decimal(h),
        low=Decimal(lo), close=Decimal(c),
    )


def _real_source_sequence() -> tuple[M1Bar, ...]:
    cash = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)
    asia = datetime(2026, 1, 5, 5, tzinfo=UTC)
    prev = tuple(_bar(
        cash + timedelta(minutes=i), o="110",
        h="150" if i == 33 else "114",
        lo="80" if i == 45 else "108", c="111",
    ) for i in range(390))
    asian = tuple(
        _bar(asia + timedelta(minutes=i))
        for i in range(180)
    )
    london = asia + timedelta(minutes=180)
    source = (
        _bar(london, o="100", h="103", lo="99", c="101"),
        _bar(london + timedelta(minutes=1),
             o="101", h="103", lo="100", c="100.5"),
        _bar(london + timedelta(minutes=2),
             o="101", h="105", lo="100", c="102"),
        _bar(london + timedelta(minutes=3),
             o="101", h="104", lo="100", c="101"),
        _bar(london + timedelta(minutes=4),
             o="101", h="104", lo="100", c="104"),
        _bar(london + timedelta(minutes=5),
             o="105", h="109", lo="105", c="108"),
    )
    return prev + asian + source


def _run(
    use_audit: bool,
) -> tuple[VT31Trader, UnifiedVT31Observation | None, CognitiveTelemetry | None]:
    observer = CognitiveTelemetry() if use_audit else None
    t = VT31Trader(cognition=VT31CleanroomCognition(telemetry=observer))
    last = None
    for item in _real_source_sequence():
        last = t.on_closed_m1(item)
    return t, last, observer


def test_instrumentation_is_passive_and_cannot_change_entry_candidate() -> None:
    raw, original, _ = _run(False)
    traced, observed, audit = _run(True)
    assert audit is not None
    assert original is not None and observed is not None
    assert original.operational_phase == observed.operational_phase
    assert raw.snapshot()["session_windows"] == traced.snapshot()["session_windows"]
    assert original.cognition == observed.cognition
    assert audit.closed_m1_seen == len(_real_source_sequence())
    # 390-M1 prior cash fixture includes its 10–11 and 14–15 NY source
    # windows (60 + 60), plus 6 Monday London source M1 = 126 calls.
    assert audit.cognition_calls == 126
    assert audit.ops_calls == 126
    x = audit.report()
    assert x["components"]["OPS_CANDIDATE"]["reached_first_suitable_FVG"] == 1
    assert x["candidate_causal_lineage_examples"][0]["draw_target"] == "150"
    assert x["candidate_causal_lineage_examples"][0]["broker_filled"] is False
    assert x["candidate_causal_lineage_examples"][0]["M1_MSS_confirmed_at"]
    assert x["candidate_causal_lineage_examples"][0]["cognitive_as_of"]
    assert x["trader_id"] == "VT31"
    assert x["fills_proven"] == 0
    assert x["entry_executions_proven"] == 0


def test_component_has_true_input_output_and_gate_counters() -> None:
    _, _, sensor = _run(True)
    assert sensor is not None
    report = sensor.report()
    c = report["components"]
    assert set(c) == set(COMPONENT_ROLES)
    assert c["M1_MARKET_FEED"]["calls_observed"] == 576
    assert c["M15_CONTEXT"]["calls_observed"] > 6
    assert c["H1_CONTEXT"]["output_present"] > 0
    assert c["H4_CONTEXT"]["runtime_status"] == "OBSERVED"
    assert c["NY_CASH_LIQUIDITY"]["output_present"] > 0
    assert c["ASIA_LIQUIDITY"]["output_present"] > 0
    assert c["M1_MSS_DISPLACEMENT"]["selected_for_decision"] > 0
    assert c["DOL_ARBITRATION"]["reached_first_suitable_FVG"] == 1
    assert c["COGNITIVE_DECISION"]["reached_first_suitable_FVG"] == 1
    assert c["OPS_M1_FVG"]["reached_first_suitable_FVG"] == 1
    assert c["BID_ASK_FILL"]["runtime_status"] == "NOT_CONNECTED"
    assert c["EXTERNAL_EXECUTION_ACK"]["calls_observed"] == 0
    assert c["CIBO_QDLE_ECONOMICS"]["calls_observed"] == 0
    assert report["reasoning_proof"].startswith("Deterministic")
    assert report["cibo_qdle_connected"] is False


def test_loss_of_cognitive_thesis_cancels_pending_source_p0() -> None:
    audit = CognitiveTelemetry()
    trader = VT31Trader(cognition=VT31CleanroomCognition(telemetry=audit))
    bars = _real_source_sequence()
    for b in bars:
        trader.on_closed_m1(b)
    # Sweeps NY cash high at 150 with a wick; closes at 110,
    # above selected long FVG zone, so OPS may remain pending.
    t = bars[-1].closed_at
    lost = trader.on_closed_m1(_bar(
        t, o="110", h="151", lo="106", c="110",
    ))
    assert lost.cognition is not None
    assert lost.cognition.decision is None
    # Cross-architect P0 is repaired in the merged OPS state machine:
    # COG revocation on later M1 MUST NOT leave the source pending.
    assert lost.operational_phase is MethodologyDecision.SOURCE_INVALIDATED
    assert sum(
        count for key, count in audit.by_session.items()
        if key.endswith("|P0_PENDING_WITHOUT_COG")
    ) == 0
    report = audit.report()
    assert report["p0_pending_without_cog_unique_candidate_sources"] == {}
    assert report["p0_pending_without_cog_examples"] == []



def test_m1_market_component_does_not_imply_broker_or_agent_reasoning() -> None:
    x = CognitiveTelemetry().report()
    assert all(z["calls_observed"] == 0 for z in x["components"].values())
    assert x["entry_executions_proven"] == 0
    assert "NOT independent counterfactual ablation" in x["influence_definition"]


def test_prior_closed_m1_mss_actually_influenced_later_fvg() -> None:
    """MSS from one M1, suitable FVG from the next closed M1."""
    base = _real_source_sequence()
    at = base[-1].opened_at
    first_mss = _bar(
        at, o="101", h="109", lo="101", c="107",
    )
    delayed_gap = _bar(
        at + timedelta(minutes=1),
        o="107", h="110", lo="105", c="109",
    )
    audit = CognitiveTelemetry()
    t = VT31Trader(cognition=VT31CleanroomCognition(telemetry=audit))
    for bar in (*base[:-1], first_mss, delayed_gap):
        t.on_closed_m1(bar)
    result = audit.report()
    assert result["components"]["OPS_CANDIDATE"]["output_present"] == 1
    assert result["components"][
        "M1_THESIS_REVALIDATION"
    ]["reached_first_suitable_FVG"] == 1
    assert result["candidate_causal_lineage_examples"][0]["M1_MSS_source"] == (
        "PRIOR_M1_REVALIDATED"
    )
    assert result["fills_proven"] == 0
