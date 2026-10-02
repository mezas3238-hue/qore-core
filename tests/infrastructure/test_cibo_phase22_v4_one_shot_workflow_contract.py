from __future__ import annotations

from pathlib import Path


WORKFLOW = Path(".github/workflows/cibo-phase22-v4-sovereign-one-shot.yml")


def test_v4_one_shot_workflow_has_single_authorization_trigger() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert "docs/research/CIBO-PHASE22-V4-EXECUTION-AUTHORIZATION.json" in source
    assert "workflow_dispatch:" not in source
    assert "schedule:" not in source
    assert "QORE CIBO Phase22 V4 Execution Build" in source
    assert "V4 branch advanced before claim; one-shot activation refused" in source


def test_v4_one_shot_workflow_is_broker_nonmutating() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    forbidden = (
        "ProtoOANewOrderReq",
        "ProtoOAClosePositionReq",
        "ProtoOACancelOrderReq",
        "ProtoOAAmendOrderReq",
        "ProtoOAAmendPositionSLTPReq",
    )
    for token in forbidden:
        assert token not in source


def test_v4_one_shot_workflow_uses_only_v4_claim_and_consumption_paths() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert "CIBO-PHASE22-V4-ONE-SHOT-CLAIM.json" in source
    assert "CIBO-PHASE22-V4-CONSUMPTION-RECEIPT.json" in source
    assert "CIBO-PHASE22-V2-CONSUMPTION-RECEIPT.json" not in source
    assert "CIBO-PHASE22-V3-CONSUMPTION-RECEIPT.json" not in source
    assert "cibo_phase22_v3" not in source
    assert "phase22-v3" not in source


def test_v4_lane_population_is_non_fail_fast_and_forensically_preserved() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert "fail-fast: false" in source
    assert source.count("if: always()") >= 4
    for trader_id in (
        "VT08_FOREX",
        "R34_XAUUSD",
        "R38_EURUSD",
        "R43_GBPUSD",
        "R38_GBPJPY",
        "R42_AUDJPY",
        "VT31_NAS100",
    ):
        assert trader_id in source
