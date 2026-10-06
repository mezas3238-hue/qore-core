from pathlib import Path

import pytest

from qore.infrastructure.cibo_phase22_vt31_v4_fresh_source import (
    _price,
    load_phase22_vt31_m1,
)


def test_vt31_relative_price_projection_is_exact() -> None:
    assert _price(443730000, 2) == "4437.30"


def test_vt31_source_fails_closed_without_sealed_artifact() -> None:
    with pytest.raises(ValueError, match="artifact incomplete"):
        load_phase22_vt31_m1(Path("does-not-exist"))
