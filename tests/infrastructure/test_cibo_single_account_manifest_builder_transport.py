from qore.infrastructure.cibo_single_account_manifest_integrity import (
    validate_single_account_manifest_sha256,
)
from scripts.cibo_single_account_7trader_maximum_capability_manifest import (
    build_manifest,
)


_TRADERS = (
    ("VT08_FOREX", "EURUSD"),
    ("R34_XAUUSD", "XAUUSD"),
    ("R38_EURUSD", "EURUSD"),
    ("R43_GBPUSD", "GBPUSD"),
    ("R38_GBPJPY", "GBPJPY"),
    ("R42_AUDJPY", "AUDJPY"),
    ("VT31_NAS100", "NAS100"),
)


def _trace() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for index, (trader_id, symbol) in enumerate(_TRADERS):
        rows.append(
            {
                "decision_epoch_id": "epoch-1",
                "market_decision_at": "2026-01-05T14:30:00+00:00",
                "trader_id": trader_id,
                "qore_symbol": symbol,
                "signal_fingerprint": f"signal-{index}",
                "decision_evidence_sha256": "sha256:" + "b" * 64,
                "trader_opportunity": {"provider_symbol": symbol},
                "market_predecision_state": {"state": "causal"},
                "expectation": {
                    "expected_net_value_usd": str(index + 1),
                    "expectation_evidence_sha256": "sha256:" + "c" * 64,
                },
                "context_quality": {
                    "context_allowed": True,
                    "uncertainty_penalty": "0.1",
                },
                "ce2i": {"runtime_receipts": []},
                "evaluation_outcome": {
                    "net_pnl_usd": "999",
                    "not_available_to_predecision": True,
                },
            }
        )
    return {
        "trace_sha256": "sha256:" + "a" * 64,
        "opportunities": rows,
    }


def test_manifest_preserves_causal_expectation_and_context_quality() -> None:
    manifest = build_manifest((_trace(),))

    assert validate_single_account_manifest_sha256(manifest) == manifest[
        "manifest_sha256"
    ]
    assert len(manifest["opportunities"]) == 7

    first = manifest["opportunities"][0]
    assert first["expectation"] == {
        "expected_net_value_usd": "1",
        "expectation_evidence_sha256": "sha256:" + "c" * 64,
    }
    assert first["context_quality"] == {
        "context_allowed": True,
        "uncertainty_penalty": "0.1",
    }
    assert first["settlement_outcome_research_only"]["net_pnl_usd"] == "999"
    assert first["outcome_available_to_predecision"] is False
