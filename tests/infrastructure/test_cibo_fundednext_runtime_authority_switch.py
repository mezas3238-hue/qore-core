"""FundedNext runtime must never restore Trader-owned sizing authority."""
# ruff: noqa: I001

from pathlib import Path


RUNTIME = Path("scripts/qore_fundednext_runtime.py")
VT31 = Path("scripts/vt31_nas100_runtime_adapter.py")
LEGACY_VT08 = Path(
    "src/qore/infrastructure/vt08_forex_fundednext_sizing.py"
)


def test_fundednext_runtime_removes_all_legacy_trader_sizing_calls() -> None:
    source = RUNTIME.read_text(encoding="utf-8")

    forbidden = (
        "build_certified_vt08_forex_cibo_request(",
        "build_r34_risk_request(",
        "build_r38_risk_request(",
        "build_r43_risk_request(",
        "build_r38_gbpjpy_risk_request(",
        "build_r42_audjpy_risk_request(",
    )
    for call in forbidden:
        assert call not in source

    assert "vt08_forex_fundednext_sizing" not in source


def test_fundednext_runtime_all_traditional_traders_use_cibo_seed() -> None:
    source = RUNTIME.read_text(encoding="utf-8")

    required = (
        "build_fundednext_vt08_opportunity(",
        "build_r34_opportunity(",
        "build_r38_opportunity(",
        "build_r43_opportunity(",
        "build_r38_gbpjpy_opportunity(",
        "build_r42_audjpy_opportunity(",
    )
    for call in required:
        assert call in source

    # VT08 + five Turtle Soup lineages.
    assert source.count("build_fundednext_cibo_seed(") >= 6


def test_fundednext_vt31_uses_cibo_seed_and_keeps_certified_risk_as_telemetry() -> None:
    source = VT31.read_text(encoding="utf-8")

    assert "build_risk_request(" not in source
    assert "build_vt31_opportunity(" in source
    assert "build_fundednext_cibo_seed(" in source
    assert '"sizing_authority": "CIBO_CMA"' in source
    assert '"legacy_certified_risk_r": str(resolution.final_risk_r)' in source
    assert "certified_risk_r=resolution.final_risk_r" not in source


def test_fundednext_runtime_position_base_risk_comes_from_cibo_seed() -> None:
    source = RUNTIME.read_text(encoding="utf-8")

    # R34, R38 EURUSD, R43, R38 GBPJPY and R42 retain base-risk state
    # semantics, but the amount now comes from the actual CIBO seed.
    assert source.count("base_risk_usd = seed.plan.stop_risk_usd") == 5


def test_legacy_vt08_sizing_remains_baseline_only_not_runtime_authority() -> None:
    legacy = LEGACY_VT08.read_text(encoding="utf-8")
    runtime = RUNTIME.read_text(encoding="utf-8")

    assert "R315_BASE_RISK_BPS" in legacy
    assert "build_certified_vt08_forex_cibo_request" in legacy
    assert "build_certified_vt08_forex_cibo_request" not in runtime
