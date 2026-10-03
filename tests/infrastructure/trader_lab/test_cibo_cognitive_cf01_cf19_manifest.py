from __future__ import annotations

from pathlib import Path

CF01_CF19_TRADER_LAB_MANIFEST: tuple[tuple[str, str], ...] = (
    ("CF01", "tests/infrastructure/test_cibo/test_market_monitoring.py"),
    ("CF02", "tests/infrastructure/test_cibo/test_specialist_mesh.py"),
    ("CF03", "tests/infrastructure/test_cibo_trader_manager.py"),
    ("CF04", "tests/infrastructure/test_cibo_trader_development_review.py"),
    ("CF05", "tests/infrastructure/test_cibo/test_opportunity_search.py"),
    ("CF06", "tests/infrastructure/test_cibo/test_portfolio_intelligence.py"),
    ("CF07", "tests/infrastructure/test_cibo/test_economic_journals.py"),
    ("CF08", "tests/infrastructure/test_cibo/test_economic_journals.py"),
    ("CF09", "tests/infrastructure/test_cibo/test_economic_journals.py"),
    ("CF10", "tests/infrastructure/test_cibo/test_quantitative_intelligence.py"),
    ("CF11", "tests/infrastructure/test_cibo/test_research_director.py"),
    ("CF12", "tests/infrastructure/test_cibo/test_executive_recommendation.py"),
    ("CF13", "tests/infrastructure/test_cibo/test_core_health.py"),
    ("CF14", "tests/infrastructure/test_cibo/test_executive_planner.py"),
    ("CF15", "tests/governance/test_cibo/test_ceo_dialogue.py"),
    ("CF16", "tests/infrastructure/test_cibo/test_trader_voice.py"),
    ("CF17", "tests/infrastructure/test_cibo/test_economic_journals.py"),
    ("CF18", "tests/infrastructure/test_cibo/test_self_evaluation_learning.py"),
    ("CF19", "tests/infrastructure/test_cibo/test_self_evaluation_learning.py"),
)


def test_trader_lab_cognitive_manifest_is_exact_cf01_cf19() -> None:
    expected = tuple(f"CF{index:02d}" for index in range(1, 20))
    actual = tuple(code for code, _ in CF01_CF19_TRADER_LAB_MANIFEST)

    assert actual == expected
    assert len(set(actual)) == 19


def test_trader_lab_cognitive_manifest_targets_exist() -> None:
    missing = tuple(
        path
        for _, path in CF01_CF19_TRADER_LAB_MANIFEST
        if not Path(path).is_file()
    )

    assert missing == ()
