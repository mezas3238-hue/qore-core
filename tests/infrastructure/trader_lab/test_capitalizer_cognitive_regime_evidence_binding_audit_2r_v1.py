from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_regime_evidence_binding_audit_2r_v1 as regime,
)


def _rebase_row(
    *,
    symbol: str,
    entry_at: str,
    observations: list[str],
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "session": "ASIA",
        "operating_date": "2026-01-05",
        "entry_at": entry_at,
        "provenance": "CAUSAL_ARBITRATION_BASE",
        "source_microstructure_family": "CAUSAL_ARBITRATION_BASE",
        "microstructure_observations": observations,
    }


def _micro(
    *,
    symbol: str,
    closeback_at: str,
    signature: str = "LOW_ACCEPTANCE+LOW_BREAK_ATTEMPT",
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "session": "ASIA",
        "operating_date": "2026-01-05",
        "closeback_at": closeback_at,
        "side": "LONG",
        "first_blocker": "VALID",
        "valid_m3_within_h1": True,
        "microstructure_signature": signature,
        "body_fraction": "0.65",
        "close_location": "0.40",
        "previous_range_ratio": "1.25",
        "outcome_used_for_selection": False,
    }


def test_regime_binding_binds_only_causal_exact_closeback_matches() -> None:
    rows = (
        _rebase_row(
            symbol="AUDJPY",
            entry_at="2026-01-05T00:20:00+00:00",
            observations=[
                "M5_CLOSEBACK_AT:2026-01-05T00:15:00+00:00",
                "ENTRY_MODE:FVG_CE_50",
            ],
        ),
        _rebase_row(
            symbol="GBPJPY",
            entry_at="2026-01-05T00:20:00+00:00",
            observations=["ENTRY_MODE:FVG_CE_50"],
        ),
        _rebase_row(
            symbol="USDJPY",
            entry_at="2026-01-05T00:20:00+00:00",
            observations=[
                "M5_CLOSEBACK_AT:2026-01-05T00:25:00+00:00",
                "ENTRY_MODE:FVG_CE_50",
            ],
        ),
    )
    index = {
        ("AUDJPY", "2026-01-05T00:15:00+00:00"): _micro(
            symbol="AUDJPY",
            closeback_at="2026-01-05T00:15:00+00:00",
        ),
        ("USDJPY", "2026-01-05T00:25:00+00:00"): _micro(
            symbol="USDJPY",
            closeback_at="2026-01-05T00:25:00+00:00",
        ),
    }

    bound = regime._bind_rows(rows, index)

    assert len(bound) == 3

    first = bound[0]
    assert first.micro_context_match_found is True
    assert first.micro_context_causal is True
    assert first.regime_evidence_bound is True
    assert first.microstructure_signature == "LOW_ACCEPTANCE+LOW_BREAK_ATTEMPT"
    assert first.body_fraction == "0.65"
    assert first.regime_family_id is None
    assert first.regime_intelligence_supported is False
    assert first.outcome_visible_to_binding is False

    missing = bound[1]
    assert missing.m5_closeback_at is None
    assert missing.micro_context_match_found is False
    assert missing.regime_evidence_bound is False
    assert missing.microstructure_signature is None

    future = bound[2]
    assert future.micro_context_match_found is True
    assert future.micro_context_causal is False
    assert future.regime_evidence_bound is False
    assert future.microstructure_signature is None


def test_token_map_rejects_conflicting_causal_tokens() -> None:
    row = _rebase_row(
        symbol="AUDJPY",
        entry_at="2026-01-05T00:20:00+00:00",
        observations=[
            "M5_CLOSEBACK_AT:2026-01-05T00:10:00+00:00",
            "M5_CLOSEBACK_AT:2026-01-05T00:15:00+00:00",
        ],
    )

    try:
        regime._token_map(row)
    except ValueError as exc:
        assert "conflicting microstructure token" in str(exc)
    else:
        raise AssertionError("conflicting causal tokens must fail closed")
