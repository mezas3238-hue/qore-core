from __future__ import annotations

import pytest

from qore.infrastructure import cibo_trader_lab_authority as authority
from qore.infrastructure.trader_lab import vt08_index_r59_candidate_freeze as r59
from qore.infrastructure.traders import vt08_index_specialist_contract as contract
from qore.infrastructure.traders.evaluators import Vt08Crt4hAmd


def _generic_vt08_values() -> dict[str, str]:
    evaluator = Vt08Crt4hAmd()
    methodology_id, methodology_version, methodology_fingerprint = (
        evaluator.methodology()
    )
    return {
        "trader.code": evaluator.trader_code,
        "trader.config_fingerprint": evaluator.config_fingerprint().value,
        "trader.instrument": "NAS100",
        "trader.methodology_fingerprint": methodology_fingerprint.value,
        "trader.methodology_id": methodology_id.value,
        "trader.methodology_version": methodology_version.value,
    }


def test_r63_specialist_contract_binds_exact_r58_freeze() -> None:
    assert contract.CANDIDATE_ID == r59.CANDIDATE_ID
    assert contract.CONFIG_FINGERPRINT == r59.CANDIDATE_RULE_FINGERPRINT
    assert contract.FREEZE_ID == r59.FREEZE_ID
    assert len(contract.METHODOLOGY_FINGERPRINT) == 64


def test_r63_specialist_cibo_projection_preserves_three_markets() -> None:
    values = dict(contract.manifest_parameters())
    assert authority._derived_qualified_timeframes(values) == ("M15", "H4")
    markets = authority._derived_qualified_markets(values)
    assert tuple(item.value for item in markets) == ("NAS100", "SP500", "US30")


def test_r63_specialist_manifest_drift_fails_closed() -> None:
    values = dict(contract.manifest_parameters())
    values["trader.config_fingerprint"] = "0" * 64
    with pytest.raises(
        authority.CiboTraderLabAuthorityValidationError,
        match="does not match frozen R58 identity",
    ):
        authority._derived_qualified_timeframes(values)


def test_r63_generic_vt08_contract_remains_unchanged() -> None:
    values = _generic_vt08_values()
    assert authority._derived_qualified_timeframes(values) == ("M5", "H4")
    markets = authority._derived_qualified_markets(values)
    assert tuple(item.value for item in markets) == ("NAS100",)


def test_r63_specialist_cibo_timeframe_refs_use_canonical_order() -> None:
    values = dict(contract.manifest_parameters())
    refs = authority._canonical_qualified_timeframes(values)
    assert tuple(item.value for item in refs) == ("h4", "m15")
    assert set(item.value for item in refs) == {"h4", "m15"}
