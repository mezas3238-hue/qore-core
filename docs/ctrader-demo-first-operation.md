# cTrader DEMO first-operation runbook

This runbook is intentionally restricted to `demo.ctraderapi.com:5035` using
Protobuf over TLS. It does not authorize Production and it does not manufacture
a Risk approval or an eligible Trader decision.

## Required external inputs

- cTrader Open API application client ID and client secret.
- Trading-scope access token and refresh token.
- Exact numeric `ctidTraderAccountId`, confirmed by Open API as `isLive=false`.
- Exact symbol ID, name, digits, minimum volume, maximum volume and step volume
  for every enabled instrument.
- A canonical `ExecutionSubmission` already approved by the upstream pre-trade
  Risk boundary, with the execution safety switch enabled and unexpired.
- An explicit `MarketTestEnvironmentAuthorization` for the same DEMO account.

The application declares these secret identifiers without resolving or logging
their values:

- `ctrader-demo-client-id`
- `ctrader-demo-client-secret`
- `ctrader-demo-access-token`
- `ctrader-demo-refresh-token`

Install the provider runtime with `pip install -e '.[ctrader]'`. Secret material
must be injected by the deployment secret resolver into
`CTraderOpenApiCredentials`; it must never be placed in repository files,
command arguments, evidence JSON or logs.

## Mandatory gate sequence

1. Build `CTraderDemoRuntimeConfiguration` with environment `DEMO`, the numeric
   account reference and exact broker symbol constraints.
2. Build `CTraderDemoOperationalRuntime` with the matching credentials,
   environment authorization and market-data descriptor.
3. Call `connect()`. It authenticates the application, verifies trading scope,
   selects the exact account, rejects LIVE or ambiguous account evidence, and
   validates every symbol and volume constraint against the broker.
4. Read one quote through `runtime.market_data.read_quote(...)`. Do not proceed
   if the quote is stale, missing either side, crossed or outside the upstream
   market-data policy.
5. Obtain one already-authorized, minimal-size `ExecutionSubmission` from the
   Trader/Risk chain. The runtime accepts MARKET or LIMIT only through the
   canonical contracts; the first canary should use the smallest broker-valid
   MARKET quantity allowed by Risk.
6. Call `submit_authorized()` exactly once for its idempotency key. On any
   indeterminate transport outcome, do not resubmit: use the reconciliation path.
7. Record the returned provider order reference and fill evidence. Call
   `poll_and_reconcile()` until the canonical reconciliation is complete or the
   operational timeout/containment policy stops the canary.
8. Close the runtime session and attach only sanitized receipts, fill evidence,
   account fingerprint and quality-gate results to the DEMO evidence package.

## Fail-closed stop conditions

Stop before mutation when any credential is absent, the SDK TLS identity support
is unavailable, trading scope is missing, the account is LIVE/ambiguous, account
IDs differ, a symbol is disabled or mismatched, provider volume constraints do
not match configuration, Risk authorization is absent/expired, or the safety
switch is not enabled. After a possible mutation with an unknown response, block
resubmission and reconcile the original order.
