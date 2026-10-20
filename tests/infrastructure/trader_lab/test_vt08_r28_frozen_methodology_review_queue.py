"""VT08 R28: frozen methodological sample integrity and WAIT behavior."""
import pytest

from qore.infrastructure.trader_lab.vt08_r28_frozen_methodology_review_queue import (
    build_methodology_queue,
)


def test_rejects_non_frozen_blind_sample():
    with pytest.raises(ValueError, match="integrity drift"):
        build_methodology_queue(
            {"market": "EURJPY", "review_packets": []},
            market="EURJPY",
        )


def test_rejects_unauthorized_market():
    with pytest.raises(ValueError, match="unauthorized market"):
        build_methodology_queue({}, market="BTCUSD")
