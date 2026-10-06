from types import SimpleNamespace

from qore.infrastructure.cibo_single_account_manifest_integrity import (
    reseal_single_account_manifest,
)
from scripts import cibo_single_account_native_max_intelligence_preflight as preflight


def _row(*, trader: str, symbol: str, signal: str) -> dict[str, object]:
    return {
        "decision_epoch_id": "epoch-1",
        "market_decision_at": "2026-01-05T14:30:00+00:00",
        "signal_fingerprint": signal,
        "trader_id": trader,
        "qore_symbol": symbol,
        "trader_opportunity": {
            "provider_symbol": symbol,
            "side": "long",
            "entry_type": "market",
            "intended_entry": "100",
            "stop_loss": "99",
            "take_profit": "102",
            "stop_loss_per_volume": "1",
            "margin_per_volume": "10",
            "volume_step": "0.01",
            "minimum_volume": "0.01",
            "maximum_volume": "100",
            "minimum_execution_steps": 1,
            "decision_context": [],
        },
    }


def test_preflight_uses_full_simultaneous_epoch_surface(monkeypatch) -> None:
    manifest = reseal_single_account_manifest(
        {
            "schema": "qore.cibo.single-account-7trader-maximum-capability.v1",
            "opportunities": [
                _row(
                    trader="R34_XAUUSD",
                    symbol="XAUUSD",
                    signal="signal-a",
                ),
                _row(
                    trader="R38_EURUSD",
                    symbol="EURUSD",
                    signal="signal-b",
                ),
            ],
        }
    )
    regime_counts: list[int] = []
    consultation_surfaces: list[tuple[str, ...]] = []
    native_surfaces: list[tuple[tuple[str, ...], str]] = []

    def fake_regime(row, *, opportunity_count):
        regime_counts.append(opportunity_count)
        return SimpleNamespace(opportunity_count=opportunity_count)

    def fake_consult(*, decision_at, opportunities, regime_state):
        consultation_surfaces.append(
            tuple(item.signal_fingerprint for item in opportunities)
        )
        return SimpleNamespace(decision_at=decision_at)

    def fake_native(*, consultation, opportunities, target, regime_state):
        native_surfaces.append(
            (
                tuple(item.signal_fingerprint for item in opportunities),
                target.signal_fingerprint,
            )
        )
        return SimpleNamespace(
            native_only=True,
            external_ai_call_count=0,
            external_reasoning_provider_used=False,
            blocked_function_codes=(),
        )

    monkeypatch.setattr(preflight, "_regime", fake_regime)
    monkeypatch.setattr(
        preflight,
        "consult_cibo_economic_faculties",
        fake_consult,
    )
    monkeypatch.setattr(
        preflight,
        "run_native_maximum_intelligence",
        fake_native,
    )

    result = preflight.run(manifest)

    assert regime_counts == [2, 2]
    assert consultation_surfaces == [("signal-a", "signal-b")]
    assert native_surfaces == [
        (("signal-a", "signal-b"), "signal-a"),
        (("signal-a", "signal-b"), "signal-b"),
    ]
    assert result["decision_count"] == 2
    assert result["native_max_pass_count"] == 2
    assert result["native_max_blocked_count"] == 0
    assert result["maximum_intelligence_ready"] is True

def test_preflight_reconstructs_stale_archived_epoch_count() -> None:
    row = _row(
        trader="R34_XAUUSD",
        symbol="XAUUSD",
        signal="signal-a",
    )
    row["ce2i_predecision_evidence"] = {
        "runtime_receipts": [
            {
                "engine_name": "select_ce2i_tools_for_regime",
                "input_payload": {
                    "liquidity": "NORMAL",
                    "volatility": "NORMAL",
                    "correlation": "NORMAL",
                    "provider_condition": "HEALTHY",
                    "risk_utilization": "0",
                    "margin_utilization": "0",
                    "drawdown_utilization": "0",
                    "opportunity_count": 1,
                    "position_path_adverse": "false",
                    "evidence_stale": "false",
                },
            }
        ]
    }

    regime = preflight._regime(row, opportunity_count=3)

    assert regime.opportunity_count == 3
    assert regime.position_path_adverse is False
    assert regime.evidence_stale is False

