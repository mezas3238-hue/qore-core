# QORE NQ AM TLR V3 — EXACT NQ FUTURES EVIDENCE FOUNDATION

Identity: `QORE_NQ_AM_TLR_V3_EXACT_NQ_EVIDENCE_V1`  
Tracker: #656  
Status: `IMPLEMENTED_FOUNDATION / PROVIDER_AUTH_NOT_CONFIGURED`

## Mission

Acquire read-only one-minute historical evidence for the actual NQ futures
contracts used by the source methodology, instead of assuming cTrader `USTEC`
CFD bars are contract-equivalent.

This component is evidence infrastructure only. It has no order endpoint and no
Execution, Risk, CIBO, DEMO or LIVE authority.

## Provider foundation

Provider: TradeStation API v3.

Official API documentation establishes that:
- the API supports futures;
- historical barcharts are available from
  `/v3/marketdata/barcharts/{symbol}`;
- `MarketData` is the market-data scope;
- access tokens expire after 20 minutes and may be renewed with a refresh token;
- minute history requests have a 57,600-bar per-request ceiling.

QORE therefore chunks exact NQ M1 reads into bounded windows below that ceiling.

## Contract identity — no guessing

QORE MUST NOT invent a TradeStation NQ symbol or silently use a generic proxy.

Acquisition requires an explicit contract manifest:

```json
{
  "provider": "tradestation-api-v3",
  "root": "NQ",
  "opened_at": "2024-08-13T00:00:00+00:00",
  "closed_at": "2025-08-13T00:00:00+00:00",
  "slices": [
    {
      "symbol": "PROVIDER_VERIFIED_CONTRACT_SYMBOL",
      "opened_at": "...",
      "closed_at": "..."
    }
  ]
}
```

The slices must be chronological, gap-free and non-overlapping over the requested
research interval. Exact provider contract symbols and roll boundaries must be
verified from the connected TradeStation account/provider before acquisition.

Bars retain their provider contract symbol. No back-adjustment, splice adjustment
or synthetic price transformation is permitted.

## Cross-contract rule

The future V3 replay must know when the provider contract changes. A source setup
whose prior-day reference would cross a contract boundary must fail closed unless a
separate preregistered continuous-contract normalization is introduced.

This prevents an artificial roll gap from being interpreted as an opening-range gap
or liquidity event.

## Authentication

Required GitHub/runtime secrets:

- `QORE_TRADESTATION_CLIENT_ID`
- `QORE_TRADESTATION_REFRESH_TOKEN`
- `QORE_TRADESTATION_CLIENT_SECRET` for standard Auth Code Flow keys

The collector refreshes one access token for the bounded acquisition session.
Secrets are never persisted in evidence artifacts.

The initial interactive authorization required to obtain the refresh token remains
an explicit human/provider step; QORE does not automate account login or consent.

## Evidence payload

Every retained bar binds:
- provider;
- exact provider contract symbol;
- UTC timestamp;
- M1 OHLC;
- volume where supplied;
- open interest where supplied;
- real-time flag.

The final payload binds:
- contract-manifest SHA-256;
- exact interval;
- bar count;
- first/last observed timestamps;
- duplicate/contradiction checks;
- `read_only=true`;
- `source_instrument_equivalence_target=NQ_FUTURES`;
- zero trading authority.

## Current blocker

The repository currently contains a deterministic non-production TradeStation
futures order-translation adapter, but no configured TradeStation market-data
credentials or provider-verified NQ contract manifest are present on this research
branch.

Therefore:

`EXACT_NQ_ACQUISITION_READY_IN_CODE != EXACT_NQ_EVIDENCE_ACQUIRED`

No exact-NQ result may be claimed until provider authentication and contract
identity are actually supplied and the acquisition artifact exists.

## Authority

`DEMO_ELIGIBLE=false`  
`LIVE_AUTHORIZED=false`  
`REAL_CAPITAL_AUTHORIZED=false`  
`PRODUCTION_AUTHORIZED=false`

No merge without explicit Owner order.
