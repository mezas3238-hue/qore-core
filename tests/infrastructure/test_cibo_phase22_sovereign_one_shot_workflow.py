from pathlib import Path

WORKFLOW = Path(".github/workflows/cibo-phase22-sovereign-one-shot.yml")


def _text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_sovereign_one_shot_has_only_explicit_activation_trigger() -> None:
    text = _text()
    assert "workflow_dispatch:" not in text
    assert "pull_request:" not in text
    assert "CIBO-PHASE22-V2-EXECUTION-AUTHORIZATION.json" in text
    assert "branches:\n      - agent/cibo-integrator-ab-001" in text


def test_sovereign_one_shot_has_non_cancellable_execution_lease() -> None:
    text = _text()
    assert "cancel-in-progress: false" in text
    assert 'expected-run-id "$GITHUB_RUN_ID"' in text
    assert 'expected-run-attempt "$GITHUB_RUN_ATTEMPT"' in text
    assert text.count("--expected-run-id") >= 5
    assert text.count("--expected-run-attempt") >= 5


def test_claim_precedes_all_fresh_lane_jobs() -> None:
    text = _text()
    assert "Commit the exact two-file irreversible claim" in text
    assert "needs: activate-claim" in text
    for trader_id in (
        "VT08_FOREX",
        "R34_XAUUSD",
        "R38_EURUSD",
        "R43_GBPUSD",
        "R38_GBPJPY",
        "R42_AUDJPY",
        "VT31_NAS100",
    ):
        assert trader_id in text
    assert "Prove durable lease before fresh access" in text
    assert "Prove durable lease before reading fresh lane artifacts" in text
    assert "Prove durable lease before reading fresh batch" in text


def test_workflow_uses_sealed_provider_model_without_broker_secrets() -> None:
    text = _text()
    assert "PHASE22_PROVIDER_NUMERIC_EXECUTION_FREEZE_RECEIPT" in text
    assert "QORE_CTRADER_" not in text
    assert "secrets." not in text
    assert "FundedNext" not in text
    assert "fundednext" not in text


def test_workflow_seals_claim_then_only_consumption_receipt() -> None:
    text = _text()
    assert text.count("CIBO-PHASE22-V2-ONE-SHOT-CLAIM.json") >= 2
    assert text.count("CIBO-PHASE22-V2-CONSUMPTION-RECEIPT.json") >= 5
    assert (
        'expected=" M docs/research/CIBO-PHASE22-V2-CONSUMPTION-RECEIPT.json"'
        in text
    )
    assert "contents: write" in text
    assert "actions: read" in text


def test_workflow_preserves_forensics_without_rerun_surface() -> None:
    text = _text()
    assert "scripts/cibo_phase22_execution_closure.py" in text
    assert "qore-cibo-phase22-v2-closure" in text
    assert "if: always()" in text
    assert "rerun" not in text.lower()
