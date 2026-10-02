import pytest

from scripts.cibo_phase22_turtle_fresh_corpus_patch import (
    PATCHES,
    patch_source,
)


@pytest.mark.parametrize("trader_id", tuple(PATCHES))
def test_patch_removes_only_exact_historical_length_guard(
    trader_id: str,
) -> None:
    rule = PATCHES[trader_id]
    source = (
        "def run(evidence, provenance):\n"
        f"{rule.old}\n"
        f'        raise ValueError("unexpected {rule.symbol} corpus")\n'
        "    return methodology(evidence)\n"
    )

    patched, report = patch_source(source, trader_id=trader_id)

    assert rule.old not in patched
    assert rule.new in patched
    assert "return methodology(evidence)" in patched
    assert report["methodology_parameters_changed"] is False
    assert report["entry_logic_changed"] is False
    assert report["stop_logic_changed"] is False
    assert report["target_logic_changed"] is False


def test_patch_fails_closed_on_unrecognized_source() -> None:
    with pytest.raises(ValueError, match="corpus guard drift"):
        patch_source("def run(): pass\n", trader_id="R38_GBPJPY")
