from qore.infrastructure.core_stack_v2.shared_lab_data_reality import CanonicalIdentity
from qore.infrastructure.core_stack_v2.shared_lab_identity_harness import assess_identity, validate_contract_identity


def test_fx_aliases_converge_to_one_economic_identity() -> None:
    fx = CanonicalIdentity("FX:EURUSD", "FX", "EUR", quote_currency="USD")
    aliases = {"EURUSD": (fx,)}
    for symbol in ("EURUSD", "EUR/USD", "EUR_USD"):
        assert assess_identity(symbol, "FX", aliases).passed


def test_futures_identity_requires_contract_fields() -> None:
    fut = CanonicalIdentity("FUT:ES:202612", "FUTURES", "ES", venue="CME", maturity="2026-12", contract_month="Z6", multiplier=50)
    assert validate_contract_identity(fut, requires_maturity=True, requires_venue=True, requires_multiplier=True)
    bad = CanonicalIdentity("FUT:ES", "FUTURES", "ES")
    assert not validate_contract_identity(bad, requires_maturity=True, requires_venue=True, requires_multiplier=True)
