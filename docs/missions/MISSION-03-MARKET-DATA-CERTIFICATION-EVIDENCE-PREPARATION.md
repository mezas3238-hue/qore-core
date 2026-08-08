# MISSION-03 — Market Data Certification Evidence Preparation

Status: **PREPARATION READY — OPERATIONAL OANDA EVIDENCE STILL REQUIRED**

This document defines the deterministic historical-coverage and evidence-package preparation that can be completed while the real OANDA Practice market is unavailable.

It does **not** start, close, or certify `QORE-MARKET-DATA-CERTIFICATION-001` operationally. The real authenticated OANDA Practice evidence required by `QORE-LIVE-MARKET-FEED-ACTIVATION-001` remains the external gate.

## Purpose

Prepare a reusable, provider-neutral certification evidence path so that future real OANDA Practice market data can be evaluated without changing QORE Core architecture or creating a second normalization path.

The preparation path is:

`HistoricalOhlcWindow -> HistoricalOhlcRequestPlan -> canonical OhlcSnapshot -> HistoricalOhlcCoverageReport -> MarketDataCertificationPreparationReport -> MarketDataCertificationPreparationEvidence`

Provider-specific wire data must still enter through the existing adapter, decoder, and `MarketDataIngestionFlow` before it can participate in this path.

## Historical coverage contract

`HistoricalOhlcCoverageReport` compares one existing deterministic `HistoricalOhlcRequestPlan` with canonical `OhlcSnapshot` values.

A complete coverage report requires:

- every planned interval to exist exactly once;
- no unexpected interval;
- no duplicate snapshot identity;
- no duplicate interval;
- the exact expected market-data source;
- the canonical instrument, timeframe, opened-at, and closed-at tuple to match a planned request.

Stable sanitized finding codes are emitted for:

- `source-mismatch`;
- `duplicate-snapshot-id`;
- `duplicate-interval`;
- `unexpected-interval`;
- `missing-interval`.

The evaluator performs no network I/O and executes no retry, reconnect, scheduler, thread, or hidden polling behavior.

## Certification preparation evidence package

`MarketDataCertificationPreparationEvidence` combines:

- the existing `MarketDataCertificationPreparationReport`;
- one historical coverage report for every required symbol/timeframe series;
- one explicit timezone-aware evidence generation timestamp.

The required historical coverage matrix must match the preparation policy exactly. Missing, duplicate, or unexpected series are structural failures and no package is produced.

A produced package has only two states:

- `prepared`: the general preparation report has no findings and every historical coverage report is complete;
- `blocked`: at least one deterministic preparation or historical coverage finding exists.

There is deliberately no `certified` state in this package.

## Mission-03 target matrix

The intended future OANDA Practice market-data certification matrix is:

- instruments: `EUR_USD`, `GBP_USD`;
- timeframes: M5, M15, H1, H4;
- canonical timeframe seconds: 300, 900, 3600, 14400.

The infrastructure remains provider-neutral: those values are supplied by the future certification policy rather than hardcoded into the generic evidence package.

## Public evidence schema

Schema:

`qore.market-data-certification-preparation-evidence.v1`

The deterministic JSON package contains only public/sanitized fields:

- schema and preparation status;
- generated/evaluated timestamps;
- source adapter/source UUIDs and market-data port name;
- required symbols and timeframe seconds;
- quote/OHLC counts;
- sanitized preparation finding codes;
- historical window bounds, expected interval counts, observed snapshot counts, coverage status, and sanitized coverage findings.

It accepts no token, Authorization header, account ID, secret material, credential reference, or provider request payload.

## Operational boundary

This preparation does not prove:

- OANDA authentication succeeds;
- OANDA Practice is reachable;
- real EUR_USD or GBP_USD pricing was received;
- historical OANDA candles were downloaded;
- the provider timestamp is operationally current;
- market data is operationally certified.

Those claims require real external OANDA Practice evidence.

## Sunday activation sequence

When the market and Practice account are available:

1. provision `QORE_OANDA_PRACTICE_ACCOUNT_ID` and `QORE_OANDA_PRACTICE_TOKEN` only in GitHub Actions secrets;
2. manually execute `QORE OANDA Practice Market Feed Probe` from `main`;
3. require the workflow self-audit to pass before artifact upload;
4. audit the real sanitized artifact and close the live-market-feed activation gate only if valid;
5. open `QORE-MARKET-DATA-CERTIFICATION-001` formally;
6. obtain real canonical historical samples for the required symbol/timeframe matrix;
7. compare each real series against its deterministic historical request plan;
8. run the existing general certification-preparation checks;
9. build and audit the deterministic preparation evidence package;
10. only then evaluate the operational certification closure criteria.

Production endpoints, LIVE accounts, real capital, autonomous orders, automatic corrective trading, and productive deployment remain closed.