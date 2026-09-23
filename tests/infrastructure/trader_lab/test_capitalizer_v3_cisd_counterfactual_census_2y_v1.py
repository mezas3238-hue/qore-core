import json

from qore.infrastructure.trader_lab.capitalizer_v3_cisd_counterfactual_census_2y_v1 import (
    EXPECTED_CISD_FIRST_BLOCKERS,
    IDENTITY,
    MATRIX_IDENTITY,
    _load_bottleneck_rows,
    _load_microstructure_rows,
)


def test_census_contract_is_frozen() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_CISD_COUNTERFACTUAL_CENSUS_2Y_V1"
    assert MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_CISD_COUNTERFACTUAL_CENSUS_2Y_V1"
    )
    assert EXPECTED_CISD_FIRST_BLOCKERS == 3007


def test_bottleneck_loader_filters_only_cisd_first_blockers(tmp_path) -> None:
    summary = {
        "identity": "QORE_CAPITALIZER_M3_MSS_BOTTLENECK_FORENSICS_2Y_V1"
    }
    (tmp_path / "capitalizer-eurusd-m3-mss-bottleneck-forensics-2y-v1.json").write_text(
        json.dumps(summary),
        encoding="utf-8",
    )
    ledger = tmp_path / (
        "capitalizer-eurusd-m3-mss-bottleneck-forensics-2y-v1-closebacks.jsonl"
    )
    ledger.write_text(
        "\n".join(
            (
                json.dumps({"first_blocker": "CISD", "closeback_at": "a"}),
                json.dumps({"first_blocker": "SWING_BREAK", "closeback_at": "b"}),
                json.dumps({"first_blocker": "CISD", "closeback_at": "c"}),
            )
        )
        + "\n",
        encoding="utf-8",
    )

    rows = _load_bottleneck_rows(tmp_path)

    assert [row["closeback_at"] for row in rows] == ["a", "c"]


def test_microstructure_loader_preserves_raw_signature(tmp_path) -> None:
    ledger = tmp_path / (
        "capitalizer-eurusd-v3-m3-microstructure-context-2y-v1-rows.jsonl"
    )
    ledger.write_text(
        json.dumps(
            {
                "closeback_at": "2026-09-22T10:00:00+00:00",
                "microstructure_signature": "LOW_RAID_REJECTION",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rows = _load_microstructure_rows(tmp_path)

    assert rows == {
        "2026-09-22T10:00:00+00:00": "LOW_RAID_REJECTION"
    }
