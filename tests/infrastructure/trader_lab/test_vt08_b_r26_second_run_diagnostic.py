from decimal import Decimal
import pytest
from qore.infrastructure.trader_lab.vt08_b_r26_second_run_diagnostic import inspect

def bars():
    x=[("100","101","99","99.5"),("99.5","100","98","99"),
       ("99","101","97.9","100.5"),("99","100","97.8","98.5"),
       ("98.5","101","98","100.5")]
    x += [("100","101","99","100")] * 5
    return x

def test_second_run_is_geometry_not_authority():
    result=inspect(bars(),3,Decimal("98"))
    assert result["status"]=="ONE_GEOMETRIC_CISD"
    assert result["first_breach"]==3
    assert result["runs"][0]["confirm_index"]==4
    assert result["trade_authorized"] is False
    assert result["author_validated"] is False

def test_no_new_low():
    b=bars()
    b[3]=("99","100","97.9","99")
    assert inspect(b,3,"98")["status"]=="NO_NEW_LOW"

@pytest.mark.parametrize("invalid",[
    [],[("1","2","0","1")]*10,
    [("1","0.5","0.8","1")]*10,
])
def test_bad_bars_fail_closed(invalid):
    with pytest.raises(ValueError):
        inspect(invalid,3,"98")
