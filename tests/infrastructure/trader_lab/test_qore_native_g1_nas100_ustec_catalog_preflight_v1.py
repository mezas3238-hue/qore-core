"""No-network tests for exact NAS100 vs USTEC broker catalog only."""
from __future__ import annotations

from dataclasses import dataclass
from inspect import getsource

import pytest

from qore.infrastructure.trader_lab import qore_native_g1_nas100_ustec_catalog_preflight_v1 as s
from qore.kernel.result import Success


@dataclass
class Fake:
    symbolName: str
    symbolId: int
    enabled: bool


def test_ustec_alias_is_historical_frozen_hint_not_equivalence():
    assert s.ALLOWED == {"NAS100", "USTEC"}
    assert s.CANONICAL_ALIAS_HINTS["NAS100"] == "USTEC"
    assert s.IDENTITY.startswith("QORE_NATIVE_G1_NAS100_USTEC_")


def test_ustec_only_is_unverified_candidate():
    result = s.classify((Fake("USTEC", 1234, True), Fake("US500", 233, True)))
    assert result["catalog_exact_candidates"] == {"USTEC": 1234}
    assert result["status"] == "USTEC_ALIAS_CANDIDATE_NEEDS_CONTRACT_EQUIVALENCE"
    assert result["alias_equivalence_verified"] is False


def test_exact_nas100_still_needs_contract():
    result = s.classify((Fake("NAS100", 55, True),))
    assert result["status"] == "EXACT_NAS100_ENABLED_CONTRACT_STILL_UNVERIFIED"


def test_two_alias_candidates_prohibit_auto_selection():
    result = s.classify((Fake("NAS100", 55, True), Fake("USTEC", 89, True)))
    assert result["status"] == "BOTH_NAMES_ENABLED_AMBIGUOUS_NEEDS_CONTRACT_AUDIT"
    assert len(result["catalog_exact_candidates"]) == 2


def test_missing_alias_is_not_evidence_of_zero_quotes():
    result = s.classify((Fake("US500", 50, True), Fake("USTEC", 10, False)))
    assert result["status"] == "NAS100_USTEC_NOT_ENABLED_OR_ABSENT"
    assert result["historical_execution_contract_verified"] is False


def test_duplicate_provider_name_or_invalid_symbol_id_fail_closed():
    with pytest.raises(s.SourceBlock, match="DUPLICATE"):
        s.classify((Fake("USTEC", 22, True), Fake("USTEC", 23, True)))
    with pytest.raises(s.SourceBlock, match="INVALID_PROVIDER"):
        s.classify((Fake("NAS100", 0, True),))


def test_detail_request_contains_no_orders_and_no_quote_download():
    class Symbol:
        symbolId = 13
        digits = 1
        lotSize = 100
        minVolume = 1
        stepVolume = 1

    class Response:
        symbol = (Symbol(),)

    class Client:
        account_id = 42
        def request(self, message_name, fields, *, client_msg_id, timeout_seconds):
            assert message_name == "ProtoOASymbolByIdReq"
            assert fields == {"ctidTraderAccountId": 42, "symbolId": [13]}
            return Success(Response())

    report = s._details(Client(), 13)
    assert report["symbol_id"] == 13
    assert report["digits"] == 1
    assert report["historical_original_CIBO_contract_equivalence_proven"] is False
    assert "ProtoOAGetTickDataReq" not in getsource(s.inspect)
    assert "ProtoOANewOrderReq" not in getsource(s.inspect)
