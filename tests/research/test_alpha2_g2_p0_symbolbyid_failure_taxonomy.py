"""All tests are synthetic fail messages, never broker/API runs."""
import pytest

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiConnectionError,
    CTraderOpenApiDependencyError,
    CTraderOpenApiProtocolError,
)
from qore.kernel.result import Failure, Success
from qore.research.alpha2_g2_p0_symbolbyid_failure_taxonomy import (
    CATEGORIES,
    classify_failure,
)


@pytest.mark.parametrize(("error", "expected"), [
    (CTraderOpenApiProtocolError("HISTORY_ONLY_MESSAGE_NOT_ALLOWED"),
     "LOCAL_REQUEST_NOT_WHITELISTED"),
    (CTraderOpenApiProtocolError(
        "cTrader request message is not admitted by this runtime"),
     "LOCAL_SDK_REQ_UNADMITTED"),
    (CTraderOpenApiDependencyError("absent sdk binding"),
     "LOCAL_SDK_REQ_UNADMITTED"),
    (CTraderOpenApiProtocolError("invalid cTrader request field: symbolId"),
     "LOCAL_PROTO_FIELD_INVALID"),
    (CTraderOpenApiProtocolError("cTrader response could not be decoded"),
     "LOCAL_RESPONSE_DECODE_FAILURE"),
    (CTraderOpenApiProtocolError("cTrader request rejected: ACCOUNT_BLOCKED"),
     "BROKER_PROTOCOL_REJECTED_CODE_ONLY"),
    (CTraderOpenApiConnectionError("cTrader request timed out"),
     "TRANSPORT_TIMEOUT"),
    (CTraderOpenApiConnectionError("cTrader DEMO TLS connect timed out"),
     "TRANSPORT_TIMEOUT"),
    (CTraderOpenApiConnectionError("cTrader request failed"),
     "TRANSPORT_OR_SESSION_FAILURE"),
    (CTraderOpenApiProtocolError("unexpected app auth"), "UNKNOWN_FAILURE"),
    (RuntimeError("untrusted arbitrary exception"), "UNKNOWN_FAILURE"),
])
def test_fixed_strict_categories(error, expected):
    code = classify_failure(Failure(error))
    assert code == expected
    assert code in CATEGORIES


@pytest.mark.parametrize("malicious", [
    "cTrader request rejected: token_should_NOT_leak",
    "cTrader request rejected: CLIENT_ID=abcdef",
    "cTrader request rejected: lowercase",
    "cTrader request rejected: " + "A" * 65,
    "cTrader request rejected: ACCOUNT_BLOCKED account=1234",
    "cTrader response could not be decoded secret=ABCDE",
    "SECRET-RAW-SESSION-IDENTIFIER",
    "P0_SYMBOLBYID_SINGLE_REQUEST_FAILED",
])
def test_no_secrets_or_unsupported_codes_leak(malicious):
    code = classify_failure(Failure(CTraderOpenApiProtocolError(malicious)))
    assert code == "UNKNOWN_FAILURE"
    assert malicious not in code
    assert "SECRET" not in code and "token" not in code
    assert code in CATEGORIES


def test_unknown_exception_does_not_get_reported():
    secret = "DEMO_API_ACCOUNT_ID_123456789_STAY_PRIVATE"
    code = classify_failure(Failure(RuntimeError(secret)))
    assert code == "UNKNOWN_FAILURE"
    assert secret not in code


@pytest.mark.parametrize("input_value", [
    None, True, False, 0, 1, object(), "FAILURE", {"status": "success"},
])
def test_unrelated_input_does_not_become_broker_source(input_value):
    assert classify_failure(input_value) == "NOT_A_FAILURE"


def test_success_is_not_a_failure_and_not_a_contract_approval():
    assert classify_failure(Success(None)) == "NOT_A_FAILURE"
    assert classify_failure(Success("FULL_BROKER_CONTRACT")) == "NOT_A_FAILURE"


def test_fixed_labels_have_no_source_values():
    for value in CATEGORIES:
        assert value.isupper()
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ_" for c in value)
