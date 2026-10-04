# QORE SHARED LAB — Data Reality & Sensor Laboratory 001

Status: laboratory construction only. No trading, sizing, risk, production, certification or protected-holdout authority.

## Boundary

PROVIDER -> RAW EVIDENCE -> PROVENANCE -> CANONICAL IDENTITY -> MARKET HOURS ->
TIMESTAMP/CHRONOLOGY -> FRESHNESS -> QUALITY -> COMPLETENESS -> SENSOR OUTPUT -> LAB RECEIPT.

This lane consumes, but does not rewrite, the Shared Lab core/tool contracts.

## Evidence laws

- A valid timestamp alone never proves market reality.
- Provider lineage must identify the exact source, raw SHA-256, decoder and mapping revision.
- Canonical identity is economic identity; provider symbol spelling is not.
- Predecision evidence must satisfy observed_at <= available_at <= decision_at <= consumed_at.
- Any future evidence before decision is an automatic laboratory failure.
- Quality is per required capability; pooled rescue is forbidden.
- Critical sensor loss can require abstention even when unrelated sensors are healthy.
- Golden traces are engineering fixtures only and never the final fresh 7-trader x 2-year holdout.
- Fault families are parameterized through SharedLabToolRegistry rather than one-off scripts.

## Current executable coverage

Golden trace determinism; alias resolution; ambiguous identity; wrong asset class; market-open/closed contradiction;
value validity; coverage/usable ratios; stale/duplicate/out-of-order metrics; provider disagreement; sensor fault injection;
chronology positive offsets (+1ms, +10ms, +1s, +30s, +5min); missing/duplicate/out-of-order timestamps;
future-leakage detection; fail-degraded classification; registry cross-product expansion.

## L10 known-failure contract

The lane deliberately injects missing evidence, duplicates, ordering damage, stale/future timestamps,
malformed values, wrong asset class, provider disconnect, delay and intermittency. A known injected failure
that produces no observable mutation/detection is a laboratory failure.

## Authority

All receipts are scientific evidence only. productive authority remains false by construction.
