"""Author positional entry density upper bound, no fake post-open CISD."""
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_5m_a_positional_density_gate_audit_v1 import (
    c2_preconfirmed_positional_shape,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

T = datetime(2026, 1, 14, 9, tzinfo=UTC)


def bar(start, o, hi, lo, cl, minutes=15):
    return Vt08B01Bar(
        opened_at=start, closed_at=start + timedelta(minutes=minutes),
        open=Decimal(str(o)), high=Decimal(str(hi)),
        low=Decimal(str(lo)), close=Decimal(str(cl)),
    )


def base():
    c1 = bar(T - timedelta(hours=4), 100, 110, 95, 100, 240)
    first = bar(T, 99, 101, 94, 96)
    second = bar(T + timedelta(minutes=15), 96, 105, 96, 104)
    later = tuple(
        bar(T + timedelta(minutes=15 * i), 104, 105, 104, 104)
        for i in range(2, 16)
    )
    ltf = (first, second) + later
    c2 = bar(T, 99, 105, 94, 104, 240)
    c3_open = bar(c2.closed_at, 104, 105, 103, 104)
    return c1, c2, ltf, c3_open


def audit(c1=None, c2=None, ltf=None, c3_open=None):
    a, b, c, d = base()
    return c2_preconfirmed_positional_shape(
        c1=c1 or a, c2=c2 or b, c2_m15=ltf or c,
        owner_open_at=c3_open or d,
    )


def test_position_at_new_h4_open_not_wait_for_future_new_cisd():
    r = audit()
    assert r["reversal_closure"] is True
    assert r["m15_cisd_ps_count"] == 1
    assert r["cisd_confirmed_at"] == (T+timedelta(minutes=30)).isoformat()
    assert r["decision_at"] == (T+timedelta(hours=4)).isoformat()
    assert r["risk_oriented"] is True
    assert r["source_htf_poi_verified"] is False
    assert r["position_entry_authorized"] is False


def test_no_future_c2_m15_can_be_used():
    _, c2, ltf, pos = base()
    tampered = replace(ltf[-1], closed_at=ltf[-1].closed_at+timedelta(minutes=15))
    with pytest.raises(ValueError, match="must close"):
        audit(c2=c2, ltf=ltf[:-1]+(tampered,), c3_open=pos)


def test_missing_or_reordered_c2_m15_fails_closed():
    _, _, ltf, _ = base()
    delayed = replace(ltf[1], opened_at=ltf[1].opened_at+timedelta(minutes=15))
    with pytest.raises(ValueError, match="gap/reorder"):
        audit(ltf=(ltf[0], delayed) + ltf[2:])


def test_duplicated_ps_stays_ambiguous_not_nearest():
    a, b, ltf, d = base()
    sequence = list(ltf)
    sequence[3] = bar(T+timedelta(minutes=45), 104, 104, 100, 102)
    sequence[4] = bar(T+timedelta(minutes=60), 102, 105, 102, 105)
    # Resets series; the second opposing low 100 does NOT sweep C1 low 95;
    # it must NOT become a protected swing for B01.
    sequence[5] = bar(T+timedelta(minutes=75), 105, 105, 104, 104)
    for i in range(6,16):
        sequence[i] = bar(T+timedelta(minutes=15*i), 104, 105, 104, 104)
    candle = replace(b, high=Decimal("105"), close=Decimal("104"))
    r = audit(c1=a, c2=candle, ltf=tuple(sequence), c3_open=d)
    assert r["m15_cisd_ps_count"] == 1


def test_double_sweep_not_normal_positional_branch():
    a, b, ltf, d = base()
    b = replace(b, high=Decimal("111"))
    ltf = (replace(ltf[0], high=Decimal("111")),) + ltf[1:]
    r = audit(c1=a, c2=b, ltf=ltf, c3_open=d)
    assert r["reversal_closure"] is False
    assert r["m15_cisd_ps_count"] == 0


def test_price_open_inside_wrong_risk_side_not_order():
    _, _, _, d = base()
    d = replace(d, open=Decimal("93"), high=Decimal("105"), low=Decimal("92"))
    r = audit(c3_open=d)
    assert r["m15_cisd_ps_count"] == 1
    assert r["risk_oriented"] is False
    assert r["position_entry_authorized"] is False


def test_no_reversal_close_not_promoted():
    a, b, ltf, d = base()
    b = replace(b, close=Decimal("94.5"))
    last = replace(ltf[-1], close=Decimal("94.5"), low=Decimal("94"))
    r = audit(c1=a, c2=b, ltf=ltf[:-1]+(last,), c3_open=d)
    assert r["reversal_closure"] is False
