from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from qore.infrastructure.trader_lab.first_cohort_failure_analysis import (
    FirstCohortFailureAnalysisError,
)
from qore.infrastructure.trader_lab.first_cohort_research_dossiers import (
    _CODES,
    _SYMBOLS,
    _write_reports,
    build_research_reports,
)

_SHA = "b" * 40
_ACCOUNT = "demo-account-fingerprint"


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _profile(code: str, *, symbol: str | None = None) -> dict[str, object]:
    setup = []
    if symbol is not None:
        setup = [
            {
                "exit_at": f"2026-01-{index + 1:02d}T00:00:00+00:00",
                "return_rate": "0.01" if index % 2 == 0 else "-0.005",
            }
            for index in range(6)
        ]
    return {
        "profile": "production-default",
        "selected_by_in_sample_only": False,
        "config_fingerprint": f"config-{code}",
        "parameters": {},
        "methodology_identity": {
            "trader_version": "1.0.0",
            "methodology_id": f"method-{code}",
            "methodology_version": "1.0.0",
            "methodology_fingerprint": f"methodology-{code}",
            "timeframe": "M5",
            "session": "all",
        },
        "setups": setup,
        "decision_funnel": {"setup": len(setup), "filled": len(setup)},
        "classification_labels": ["sparse_opportunity"],
    }


def _rows(*, symbol: str | None = None) -> list[dict[str, object]]:
    return [
        {
            "trader_code": code,
            "methodology_component_map": {"ordered_components": ["signal"]},
            "profiles": [_profile(code, symbol=symbol)],
        }
        for code in _CODES
    ]


def _build_fixture(root: Path) -> tuple[Path, Path]:
    evidence = root / "evidence"
    aggregate = root / "aggregate"
    for symbol in _SYMBOLS:
        directory = evidence / symbol
        common = {"software_sha": _SHA, "symbol": symbol}
        _write(
            directory / "market-evidence.json",
            {
                "software_sha": _SHA,
                "symbol": {"symbol_name": symbol},
                "account_fingerprint": _ACCOUNT,
                "coverage": {
                    period: {
                        "span_seconds": 730 * 24 * 60 * 60,
                        "bar_count": 2,
                        "first_opened_at": "2024-01-01T00:00:00+00:00",
                        "last_closed_at": "2026-01-01T00:00:00+00:00",
                    }
                    for period in ("M5", "M15", "H4")
                },
            },
        )
        _write(directory / "backtest.json", common)
        _write(directory / "walk-forward.json", common)
        _write(
            directory / "characterization.json",
            {
                **common,
                "account_fingerprint": _ACCOUNT,
                "results": _rows(symbol=symbol),
            },
        )
        _write(
            directory / "failure-analysis.json",
            {
                **common,
                "account_fingerprint": _ACCOUNT,
                "results": [
                    {"trader_code": code, "failure_stage": "in_sample"}
                    for code in _CODES
                ],
            },
        )

    aggregate_common = {"software_sha": _SHA, "account_fingerprint": _ACCOUNT}
    _write(
        aggregate / "multi-pair-walk-forward.json",
        {
            **aggregate_common,
            "results": [
                {
                    "trader_code": code,
                    "robust_pass": False,
                    "pooled_in_sample": {"sample_size": 36},
                    "pooled_oos": {"sample_size": 12},
                    "pooled_stressed_oos": {"sample_size": 12},
                }
                for code in _CODES
            ],
        },
    )
    _write(
        aggregate / "characterization-aggregate.json",
        {**aggregate_common, "results": _rows()},
    )
    _write(
        aggregate / "failure-analysis-aggregate.json",
        {
            **aggregate_common,
            "results": [
                {"trader_code": code, "classification_labels": ["sparse_opportunity"]}
                for code in _CODES
            ],
        },
    )
    _write(
        aggregate / "hypothesis-register.json",
        {
            **aggregate_common,
            "hypotheses": [
                {"trader": code, "hypothesis_id": f"HYP-{code.upper()}-001"}
                for code in _CODES
            ],
        },
    )
    return evidence, aggregate


def test_builds_five_complete_dossiers_and_governed_reports(tmp_path: Path) -> None:
    evidence, aggregate = _build_fixture(tmp_path)

    first = build_research_reports(evidence, aggregate, software_sha=_SHA)
    second = build_research_reports(evidence, aggregate, software_sha=_SHA)

    assert first == second
    assert tuple(first) == (
        *(f"{code}-deep-characterization-dossier.json" for code in _CODES),
        "first-cohort-comparative-deep-characterization-report.json",
        "holdout-register.json",
        "promotion-report.json",
    )
    for code in _CODES:
        dossier = first[f"{code}-deep-characterization-dossier.json"]
        provenance = cast(dict[str, object], dossier["data_provenance"])
        battery = cast(dict[str, object], dossier["evaluation_battery"])
        monte_carlo = cast(dict[str, object], dossier["monte_carlo"])
        promotion = cast(dict[str, object], dossier["promotion"])
        governance = cast(dict[str, object], dossier["holdout_governance"])
        assert dossier["software_sha"] == _SHA
        assert provenance["minimum_required_days"] == 730
        assert battery["monte_carlo"] == "completed"
        assert monte_carlo["simulations"] == 1000
        assert promotion["demo_eligible"] is False
        assert governance[
            "consumed_holdout_cannot_certify_modified_strategy"
        ] is True
    assert first["promotion-report.json"]["demo_eligible_count"] == 0
    assert first["first-cohort-comparative-deep-characterization-report.json"][
        "five_dossiers_complete"
    ] is True

    output = tmp_path / "output"
    _write_reports(output, first)
    assert sorted(path.name for path in output.iterdir()) == sorted(first)
    assert all(path.read_bytes().endswith(b"\n") for path in output.iterdir())


def test_rejects_less_than_730_effective_days(tmp_path: Path) -> None:
    evidence, aggregate = _build_fixture(tmp_path)
    path = evidence / _SYMBOLS[0] / "market-evidence.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["coverage"]["M5"]["span_seconds"] -= 1
    _write(path, payload)

    with pytest.raises(FirstCohortFailureAnalysisError, match="less than 730"):
        build_research_reports(evidence, aggregate, software_sha=_SHA)


def test_rejects_mixed_software_sha_and_incomplete_cohort(tmp_path: Path) -> None:
    evidence, aggregate = _build_fixture(tmp_path)
    path = aggregate / "hypothesis-register.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["software_sha"] = "c" * 40
    _write(path, payload)
    with pytest.raises(FirstCohortFailureAnalysisError, match="exact software SHA"):
        build_research_reports(evidence, aggregate, software_sha=_SHA)

    _build_fixture(tmp_path)
    path = aggregate / "characterization-aggregate.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["results"] = payload["results"][:-1]
    _write(path, payload)
    with pytest.raises(FirstCohortFailureAnalysisError, match="identity/order"):
        build_research_reports(evidence, aggregate, software_sha=_SHA)
