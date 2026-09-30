import json
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_market_stop_family_stability_v1 import (
    IDENTITY,
    build_market_stability,
)


def _write_report(
    root: Path,
    *,
    trades: int,
    families: list[dict[str, object]],
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "identity": "QORE_CAPITALIZER_MARKET_STOP_STATE_FAMILY_LAB_V1",
        "symbol": "NAS100",
        "session": "NEW_YORK",
        "source_trade_count": trades,
        "family_key_uses_outcome": False,
        "families": families,
    }
    (
        root / "capitalizer-nas100-market-stop-state-families-v1.json"
    ).write_text(json.dumps(payload), encoding="utf-8")


def _family(
    state_id: str,
    *,
    trades: int,
    stop_rate: str,
    recovery: str,
    extra: str,
) -> dict[str, object]:
    return {
        "state_family_id": state_id,
        "trades": trades,
        "stop_rate": stop_rate,
        "target_recovery_after_stop_rate": recovery,
        "median_extra_stop_r_recovered": extra,
    }


def test_stability_audit_matches_exact_pretrade_families(tmp_path: Path) -> None:
    dev = tmp_path / "dev"
    hold = tmp_path / "hold"
    common = [
        _family(
            f"NAS100:STATE:{index}",
            trades=25 + index,
            stop_rate=str(0.40 + index * 0.01),
            recovery=str(0.10 + index * 0.01),
            extra=str(0.50 + index * 0.10),
        )
        for index in range(3)
    ]
    _write_report(dev, trades=100, families=common)
    _write_report(
        hold,
        trades=100,
        families=[
            _family(
                f"NAS100:STATE:{index}",
                trades=30 + index,
                stop_rate=str(0.42 + index * 0.01),
                recovery=str(0.12 + index * 0.01),
                extra=str(0.70 + index * 0.10),
            )
            for index in range(3)
        ],
    )

    report = build_market_stability(dev, hold)
    assert report.identity == IDENTITY
    assert report.common_family_count == 3
    assert report.development_common_trade_coverage == "0.78"
    assert report.consumed_holdout_common_trade_coverage == "0.93"
    assert report.family_key_uses_outcome is False
    assert report.fresh_holdout_claimed is False
    assert report.buffer_freeze_supported is False
    assert report.rule_promotion_allowed is False
    assert "SPREAD_AT_ENTRY" in report.missing_pretrade_dimensions
    dense = next(
        item for item in report.slices if item.min_trades_each_window == 20
    )
    assert dense.common_families == 3
    assert dense.stop_rate_correlation is not None
    assert dense.recovery_rate_correlation is not None
    assert dense.recovered_extra_r_correlation is not None
