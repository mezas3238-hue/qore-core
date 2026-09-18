from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_eurusd_r35_loss_sequence_governor as r35,
)


def test_r35_gate_is_fixed() -> None:
    assert r35.MIN_TRADES == 350
    assert r35.MIN_PF_010 == Decimal("1.90")
    assert r35.MAX_DD_010 == Decimal("6.0")


def test_r35_preserves_f235_and_never_reintroduces_f1() -> None:
    assert r35.FAMILY_SETS == {"R35_F235_FROZEN": (r35.F2, r35.F3, r35.F5)}
    assert r35.F1 not in r35.FAMILY_SETS["R35_F235_FROZEN"]


def test_loss_sequence_scale_is_pretrade_and_resets_externally() -> None:
    p=r35.LOSS_SEQUENCE_GOVERNORS["L1_075_L2_050_L3_025"]
    assert r35._loss_sequence_scale(0,p)==Decimal("1")
    assert r35._loss_sequence_scale(1,p)==Decimal("0.75")
    assert r35._loss_sequence_scale(2,p)==Decimal("0.50")
    assert r35._loss_sequence_scale(9,p)==Decimal("0.25")
