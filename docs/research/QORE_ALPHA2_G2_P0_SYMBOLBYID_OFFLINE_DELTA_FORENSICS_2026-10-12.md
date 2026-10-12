# QORE-Alpha 2 / #868 — offline SymbolById failure differential, NO broker retry

**2026-10-12.** Research/DRAFT PR #840, not live. This is an **offline source-code and past GitHub Actions log comparison**, not a new protocol request. In particular, there is **no identified proven root cause** of current failures. Do not remove STOP rule by claiming one.

## Reproducible comparison from immutable upstream evidence

1. QORE Native original read-only alias [run #38284304699](https://github.com/mezas3238-hue/qore-core/actions/runs/38284304699), exact code HEAD `716996e0f893af0aeb2b990ac11d644cf62a5c5f`, concluded **SUCCESS**; source module `src/qore/infrastructure/trader_lab/qore_native_g1_nas100_ustec_catalog_preflight_v1.py`, Native PR #850. Demonstrated an authentic DEMO broker source of current **USTEC** detail primitives (`symbolId=10014`, digits2, pipPosition1, lotSize raw100, minVolume10, stepVolume10), no historical NAS100 equivalence.
2. Alpha2 V3 current DEMO [run #38301475947](https://github.com/mezas3238-hue/qore-core/actions/runs/38301475947), exact code HEAD `adae3dded6a213b38f6f601366bfb36c70ac2fcf`, synthetic PASS but broker job **FAIL**. Sanitized log: `P0_SYMBOLBYID_SINGLE_REQUEST_FAILED`, `canonical_count=0`, `exact_enabled_names=[]`, no raw provider error category published. No metadata approved, NO actual broker contract.
3. V2 [run #38301197700](https://github.com/mezas3238-hue/qore-core/actions/runs/38301197700) returned `P0_FULL_SYMBOL_RESPONSE_FAILURE` after catalog reuse. Earlier V1 [#38300858851](https://github.com/mezas3238-hue/qore-core/actions/runs/38300858851) a redundant `ProtoOASymbolsListReq` failed. These three attempts are exhausted; avoid blind repetition.
4. Both Native and Alpha2 construct the same kind of cTrader read-only protobuf `ProtoOASymbolByIdReq` with fields `ctidTraderAccountId=<authenticated DEMO ID>, symbolId=[<positive broker catalog ID>]`, 35s request timeout. Original `_ReadOnlyIcMarketsHistoryClient` signed at blob `77e266a3a2d15709851c7126139930de2f4331b3` explicitly allows `ProtoOASymbolByIdReq` in `_HISTORY_ONLY_REQUEST_NAMES`. The Alpha2 `ReadOnlySpotClient` subclass extends the original request allowlist *only* by `ProtoOASubscribeSpotsReq` and adds spot bindings; it does **not intentionally remove** `SymbolById`. Thus **a missing request allowlist permission is not supported as the proven explanation**.
5. **Material difference, still hypothesis only**: Native alias probe creates the DEMO client, authenticates it, makes a fresh `ProtoOASymbolsListReq` on **the same broker session**, then calls `SymbolById` for returned IDs. Alpha2 V2/V3 reuses an independently authenticated `probe_catalog()` result, then creates/authenticates another client and immediately submits `SymbolById` without a `SymbolsList` call on that second session. The potential **same-session catalog prerequisite** has **not** been shown by cTrader documentation or broker response; current evidence is also consistent with rate limit/transport/provider-side state/authorization or SDK response decoding issues. V1 redundant SymbolsList failed, so do not assume adding it is a reliable fix.
6. Native's USTEC is one current source observation at one time; this **does not** prove Alpha2's account or provider endpoint at V3 was in identical state, nor does it prove Original CIBO NAS100 equals USTEC.

## Scientific/technical decision from the audit

**Root cause: UNDETERMINED; no more queries allowed on available evidence.** Same request *shape* in source only disproves some naïve static hypotheses, not backend differences. Existing safe exception sanitizer collapses all `Failure` into one code, therefore it cannot distinguish provider ERROR enum, local protocol whitelist, timeout, malformed message, missing binding, or response decode fault.

### Minimum evidence before approval of any future bounded DEMO probe

- Maintain one immutable broker/app SDK version and source code HEAD; snapshot package versions, hash of request schema (only schema, no account or secrets), exact request endpoint/response class and bounded timing.
- Add a **purely offline** classifier with synthetic `Failure` fixtures to produce a fixed nonsecret category: `LOCAL_REQUEST_NOT_WHITELISTED`, `LOCAL_SDK_REQ_UNADMITTED`, `LOCAL_RESPONSE_DECODE_FAILURE`, `BROKER_PROTOCOL_REJECTED_CODE_ONLY`, `TRANSPORT_TIMEOUT`, `UNKNOWN`. Never serialize raw `Failure` text or tokens.
- Compare these six categories, current vs Native ancestor, and confirm correct account scope/SDK/proto version locally. Do not require or create new account credentials.
- Only after documentation and separate approval of broker/account API access, define a **new bounded source-only prereg** selecting one exact symbol, request count and timeout, success+failure exits, zero order methods and no token refresh. **Not authorized by this report.** An empirical same-session sequence should not be called a confirmed fix until actual source evidence independently proves it.
- Even full current DEMO `SymbolById` success would leave original Atlas12 historical contract equivalence and all NET/PIT/UTC001 gates **BLOCKED**.

## Safety / evidence status

Prior root cause attempts: **3 source variants**, all fail-closed; new source requests this audit: **0**. This report consumes no raw quote ZIP and no held-out 2026 prices. No W1/W2/W3 reoptimization or PnL, no MT5/VPS/CIBO/Shared/QDLE/PAPER/LIVE/MAIN. Continue #837 legal private archive P0, #868 current/historical contract identity, #852 full broker economics.
