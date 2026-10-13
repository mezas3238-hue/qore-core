# QORE Alpha2 / #868 — prereg fixed error taxonomy for offline SymbolById Failure fixtures

**Date** 2026-10-12. Previous fail-closed V1–V3 source attempts are finished. **Do not reattempt the broker query.** This artifact implements no client requests, no account access, no network, no orders. It is a pure safe classifier of already constructed QORE `Failure(error)` objects for **future** use only after a different owner-approved new source-run protocol. No retroactive attribution to old V1–V3, whose raw errors were discarded.

Preimplementation fixed taxonomy:

- `LOCAL_REQUEST_NOT_WHITELISTED`: typed protocol error with exact `HISTORY_ONLY_MESSAGE_NOT_ALLOWED`.
- `LOCAL_SDK_REQ_UNADMITTED`: typed protocol error with exact `cTrader request message is not admitted by this runtime` or typed SDK dependency error.
- `LOCAL_PROTO_FIELD_INVALID`: typed protocol error with `invalid cTrader request field: ...` prefix (no field value output).
- `LOCAL_RESPONSE_DECODE_FAILURE`: typed protocol error with exact `cTrader response could not be decoded`.
- `BROKER_PROTOCOL_REJECTED_CODE_ONLY`: typed protocol error with provider-error prefix `cTrader request rejected:`, only if remainder is 1–64 uppercase alphanumeric/underscore; no error-code echo in public reports.
- `TRANSPORT_TIMEOUT`: typed connection error containing the fixed `timed out` suffix; `TRANSPORT_OR_SESSION_FAILURE` for other connection errors.
- `UNKNOWN_FAILURE`: all other typed and untyped Failures, no raw message propagation.
- `NOT_A_FAILURE`: Success or unrelated input; never admit a successful contract from a classifier.

For every category the return value is **one fixed harmless string**, never raw `str(error)`, stack trace, broker login, account ID, env var, access token, alias map, provider bytes or code from remote party. Inputs can contain intentionally hostile raw strings and must not contaminate output. Fail-closed tests require all categories, secret substrings, malformed provider codes, unknown errors, booleans and fake error types. No monkeypatching live classes. CI should execute **only synthetic fixtures** with Ruff/Pytest and no GitHub source download or broker secret. The old `P0_SYMBOLBYID_SINGLE_REQUEST_FAILED` remains explicitly **UNKNOWN ROOT CAUSE**, because no typed error was retained in old signed artifacts. The new helper MUST NOT update the old result files, source W1/W2/W3 or the production market data client.

Retains #868 original Atlas12 contract gate, #852 net PIT cost/OOS gate and #837 licensed archive gate; no paper/live/VPS/MT5/CIBO/Shared/QDLE/main.
