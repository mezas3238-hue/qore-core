import pytest

from qore.infrastructure.core_stack_v2.shared_lab_data_reality import CanonicalIdentity
from qore.infrastructure.core_stack_v2.shared_lab_identity_harness import assess_identity, validate_contract_identity


@pytest.mark.parametrize(
    ("symbol", "asset_class", "identity"),
    [
        ("XAUUSD", "METALS", CanonicalIdentity("METAL:XAUUSD", "METALS", "XAU", quote_currency="USD")),
        ("WTI", "ENERGY", CanonicalIdentity("ENERGY:WTI", "ENERGY", "WTI", quote_currency="USD")),
        ("CORN", "AGRICULTURE", CanonicalIdentity("AGRI:CORN", "AGRICULTURE", "CORN", quote_currency="USD")),
        ("BTCUSD", "CRYPTO", CanonicalIdentity("CRYPTO:BTCUSD", "CRYPTO", "BTC", quote_currency="USD")),
        ("NAS100", "INDEX", CanonicalIdentity("INDEX:NAS100", "INDEX", "NAS100", quote_currency="USD")),
    ],
)
def test_multiasset_identity_is_not_fx_hardcoded(symbol: str, asset_class: str, identity: CanonicalIdentity) -> None:
    receipt = assess_identity(symbol, asset_class, {symbol: (identity,)})
    assert receipt.passed


def test_futures_roll_identity_distinguishes_contract_months() -> None:
    dec = CanonicalIdentity("FUT:ES:202612", "FUTURES", "ES", venue="CME", maturity="2026-12", contract_month="Z6", multiplier=50)
    mar = CanonicalIdentity("FUT:ES:202703", "FUTURES", "ES", venue="CME", maturity="2027-03", contract_month="H7", multiplier=50)
    assert dec.economic_id != mar.economic_id
    assert validate_contract_identity(dec, requires_maturity=True, requires_venue=True, requires_multiplier=True)
    assert validate_contract_identity(mar, requires_maturity=True, requires_venue=True, requires_multiplier=True)
