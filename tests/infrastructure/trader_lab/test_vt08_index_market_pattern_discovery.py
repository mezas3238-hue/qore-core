from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_index_market_pattern_discovery import (
    discover,
)


def _row(
    *,
    symbol: str,
    signal_at: str,
    primary_r: str,
    raw_r: str,
    mfe: str,
    anchor: int = 6,
    poi: str = "fvg",
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "signal_at": signal_at,
        "primary_r": primary_r,
        "raw_r": raw_r,
        "mfe_r_conservative": mfe,
        "mae_r_conservative": "0.5",
        "anchor_hour_new_york": anchor,
        "side": "LONG",
        "model_kind": "same-c2-intracandle",
        "poi_kind": poi,
        "prior_h4_range_regime": "normal",
        "prior_h4_body_alignment": "aligned",
        "current_source_body_alignment": "aligned",
        "previous_source_body_alignment": "opposed",
        "peer_alignment_count": 2,
        "side_adjusted_relative_strength_rank": 3,
        "cisd_latency_minutes": 45,
        "post_cisd_latency_minutes": 30,
        "entry_timing_bucket": "q1_0_60",
        "stop_excursion_bucket": "not-stop" if raw_r != "-1" else "lt_0_5r",
        "duration_bucket": "le_2h",
    }


def _payload() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for index in range(24):
        rows.append(
            _row(
                symbol="NAS100",
                signal_at=f"2020-01-{(index % 24) + 1:02d}T14:00:00+00:00",
                primary_r="-1.05" if index < 16 else "1.95",
                raw_r="-1" if index < 16 else "2",
                mfe="0.3" if index < 16 else "2.2",
                poi="cisd",
            )
        )
    for index in range(24):
        rows.append(
            _row(
                symbol="SP500",
                signal_at=f"2020-02-{(index % 24) + 1:02d}T14:00:00+00:00",
                primary_r="1.95" if index < 16 else "-1.05",
                raw_r="2" if index < 16 else "-1",
                mfe="2.4" if index < 16 else "0.2",
                poi="fvg",
            )
        )
    return {
        "candidate_id": "VT08_INDEX_V7_TTRADES_SOURCE_CORRECTED_001",
        "rule_fingerprint": "fingerprint",
        "windows": [
            {
                "window_id": "w2020",
                "partition": {
                    "start_date": "2020-01-01",
                    "end_date_exclusive": "2021-01-01",
                },
            }
        ],
        "trades": rows,
    }


def _cross_market_payload() -> dict[str, object]:
    payload = _payload()
    rows: list[dict[str, object]] = []
    for index in range(12):
        rows.append(
            _row(
                symbol="NAS100",
                signal_at=f"2020-03-{index + 1:02d}T14:00:00+00:00",
                primary_r="-1.05",
                raw_r="-1",
                mfe="0.2",
                poi="fvg",
            )
        )
        rows.append(
            _row(
                symbol="SP500",
                signal_at=f"2020-03-{index + 1:02d}T15:00:00+00:00",
                primary_r="1.95",
                raw_r="2",
                mfe="2.4",
                poi="fvg",
            )
        )
    payload["trades"] = rows
    return payload


def test_discovery_is_market_specific_and_governed() -> None:
    report = discover(_payload())
    assert report["market_count"] == 2
    assert report["trade_count"] == 48
    markets = report["markets"]
    assert isinstance(markets, dict)
    nas = markets["NAS100"]
    sp = markets["SP500"]
    assert isinstance(nas, dict)
    assert isinstance(sp, dict)
    nas_fingerprint = nas["fingerprint"]
    sp_fingerprint = sp["fingerprint"]
    assert isinstance(nas_fingerprint, dict)
    assert isinstance(sp_fingerprint, dict)
    assert nas_fingerprint["performance"]["mean_r"] < "0"
    assert sp_fingerprint["performance"]["mean_r"] > "0"
    assert len(nas["loss_precursors"]) >= 1
    assert len(sp["expansion_precursors"]) >= 1
    governance = report["governance"]
    assert isinstance(governance, dict)
    assert governance["diagnostic_only"] is True
    assert governance["automatic_rule_promotion_forbidden"] is True
    assert governance["new_candidate_identity_required_for_any_rule_change"] is True
    assert governance["live_authorized"] is False


def test_cross_market_context_detects_behavior_dispersion() -> None:
    report = discover(_cross_market_payload())
    contexts = report["cross_market_same_context"]
    assert isinstance(contexts, list)
    assert contexts
    first = contexts[0]
    assert isinstance(first, dict)
    assert float(str(first["mean_dispersion_r"])) > 0
    markets = first["markets"]
    assert isinstance(markets, dict)
    assert set(markets) == {"NAS100", "SP500"}
