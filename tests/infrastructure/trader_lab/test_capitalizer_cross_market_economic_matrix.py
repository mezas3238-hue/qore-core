from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.capitalizer_cross_market_economic_matrix import (
    build_cross_market_economic_matrix,
)


def test_matrix_requires_reports(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no cross-market economic reports"):
        build_cross_market_economic_matrix(tmp_path)
