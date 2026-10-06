from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from qore.infrastructure.cibo_single_account_manifest_integrity import (
    reseal_single_account_manifest,
)
from scripts import (
    cibo_enrich_single_account_vt08_3x1y_native_perception as enrichment,
)

NOW = datetime(2020, 7, 1, 9, 0, tzinfo=UTC)


def _manifest() -> dict[str, object]:
    return reseal_single_account_manifest(
        {
            "schema": "qore.cibo.single-account-7trader-maximum-capability.v1",
            "opportunities": [
                {
                    "decision_epoch_id": "epoch-1",
                    "market_decision_at": NOW.isoformat(),
                    "trader_id": "VT08_FOREX",
                    "qore_symbol": "GBPJPY",
                    "signal_fingerprint": "sha256:" + "a" * 64,
                    "trader_opportunity": {
                        "provider_symbol": "GBPJPY",
                        "side": "long",
                        "entry_type": "market",
                        "intended_entry": "133.192",
                        "stop_loss": "133.007",
                        "take_profit": "133.562",
                        "stop_loss_per_volume": "1",
                        "margin_per_volume": "1",
                        "volume_step": "0.01",
                        "minimum_volume": "0.01",
                        "maximum_volume": "100",
                        "minimum_execution_steps": 1,
                        "decision_context": [
                            ["family", "VT08_B01_R3_15"],
                        ],
                    },
                    "settlement_outcome_research_only": {
                        "exit_at": (
                            NOW + timedelta(hours=1)
                        ).isoformat(),
                        "gross_structural_outcome_r": "999",
                        "not_available_to_predecision": True,
                        "used_for_decision": False,
                    },
                    "outcome_available_to_predecision": False,
                }
            ],
        }
    )


def _candidate() -> SimpleNamespace:
    return SimpleNamespace(
        side=SimpleNamespace(value="long"),
        setup=SimpleNamespace(
            entry_price=Decimal("133.192"),
            invalidation_price=Decimal("133.007"),
            take_profit_price=Decimal("133.562"),
        ),
    )


def test_vt08_3x1y_enrichment_requires_exact_native_geometry(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        enrichment,
        "evaluate_b01_at_entry_indexed",
        lambda **kwargs: SimpleNamespace(
            candidate=_candidate(),
            abstain_reason=None,
        ),
    )
    monkeypatch.setattr(
        enrichment,
        "candidate_setup_context",
        lambda candidate: {
            "strategy_family": "VT08_B01_R3_8",
            "source_context_causal": "true",
            "planned_target_r": "2",
        },
    )

    result = enrichment.enrich(
        _manifest(),
        {"GBPJPY": {NOW: object()}},
        source_ids=("immutable-evidence.json",),
    )
    summary = result["vt08_3x1y_native_perception_enrichment"]
    assert summary["attempted"] == 1
    assert summary["enriched"] == 1
    assert summary["blocked_count"] == 0
    assert summary["outcome_files_read"] is False
    row = result["opportunities"][0]
    context = dict(row["trader_opportunity"]["decision_context"])
    assert context["family"] == "VT08_B01_R3_15"
    assert context["strategy_family"] == "VT08_B01_R3_8"
    assert context["cibo_native_perception_complete"] == "true"
    assert context["cibo_native_perception_version"] == (
        "vt08-b01-r3-8-max-intelligence-v1"
    )
    assert row["settlement_outcome_research_only"][
        "gross_structural_outcome_r"
    ] == "999"


def test_vt08_3x1y_enrichment_fails_closed_on_geometry_drift(
    monkeypatch,
) -> None:
    candidate = _candidate()
    candidate.setup.take_profit_price = Decimal("999")
    monkeypatch.setattr(
        enrichment,
        "evaluate_b01_at_entry_indexed",
        lambda **kwargs: SimpleNamespace(
            candidate=candidate,
            abstain_reason=None,
        ),
    )
    monkeypatch.setattr(
        enrichment,
        "candidate_setup_context",
        lambda candidate: {"source_context_causal": "true"},
    )

    result = enrichment.enrich(
        _manifest(),
        {"GBPJPY": {NOW: object()}},
    )

    summary = result["vt08_3x1y_native_perception_enrichment"]
    assert summary["enriched"] == 0
    assert summary["blocked_count"] == 1
    assert "geometry-drift" in summary["blocked"][0]["reason"]
