# VT08 CRT R8 — preregistro de cotejo contra QUALITY LEDGER original del productor Atlas

Fecha 2026-10-16. Pre-registered before opening the original AUDUSD/USDJPY annual quality rows on GitHub Actions; read-only and immutable V1/V2/V3/G-M4. No sizing, trades, PnL, fills, capital, broker credentials or new price source.

## New verified lead
Original producer commit ab782b8e9f890f86a2b6500070f0556b4b685e3d, `src/qore/infrastructure/trader_lab/cibo_market_atlas_10y_m5_consumer_v1.py`, implemented `unresolved_gap_records` for adjacent M5 with fields: schema/identity/market/kind=UNRESOLVED_CLOSURE_OR_MISSING_DATA, previous_bar_at, next_bar_at, gap_start, gap_end_exclusive, calendar_slots_without_bars, spans_weekend, market_open_expected=None. Its QUALITY_LEDGER files were SHA-backed in yearly manifests. This proves what producer RECORDED, not whether venue was actually open/closed.

## Frozen scope and acceptance
- Three precise prior gaps only: AUDUSD 2025-04-25 21:00Z and USDJPY 2025-02-12 22:30Z / 2026-06-19 21:00Z. Pair each with R7/G-M4 case ID. No selection from outcomes.
- Read CIBO original run #35166210458 artifacts AUDUSD 10475697610, USDJPY 10475389415. Confirm original source producer SHA, symbol manifest SHA, yearly partition SHA and `DATA_QUALITY_LEDGER/{year}.jsonl` hash **before** examining rows, using existing fail-closed original reader and _ledger/_verified. No brokering/alternate provider.
- For each gap, match exactly one producer gap row with gap_start <= missing < gap_end_exclusive, exact prior bar and first next bar per currently available SHA-backed raw M5. Producer field `market_open_expected` must remain null: don't reinterpret it as verified market-close. Check count equals lattice difference, identity correct, kind correct, source schema correct. Validate `spans_weekend` for observed interval but don't promote this classifier to market calendar proof.
- Assert midweek 2025-02-12 USDJPY 22:30 is exactly one M5 absent, same producer gap record (adjacent 22:25 and 22:35), with `spans_weekend=false`. For Friday gap confirm producer's next real M5 and long interval; may be Monday/Sunday, verify from actual data, never invent.
- Emit provenance-only summary JSON, R8 case ledger JSONL, internal SHA manifest, CI logs; no OHLC price output, source outcomes or approved trade. Distinguish producer_ledger_signed_by_sha=true from provider_historical_market_schedule_authenticated=false. No modifications to original data, quality ledgers, V3, G-M4 or G7.
- Unit tests reject tampered quality checksum, forged market identity, duplicate matches, source/raw boundary mismatch, fabricated field market_open_expected=true, and ambiguous overlapping gaps. Quality Ruff/mypy/pytest and AUDUSD/USDJPY original Atlas replay must all PASS.

## Valid inferential outcomes
(a) all 3 correspond to checksum-verified producer gap rows: absence comes from CIBO's 2026-09-17 source ingest, not a downstream replay bug. Still one midweek source gap and 2 probable weekly closures, without broker-specific schedule authorization; 5 UNKNOWN unchanged, 108 WAIT unchanged. (b) any unmatched/ambiguous/tampered row: FAIL and investigate producer/reader mismatch, never conceal error. No reinterpretation of GM4 outcome under any branch.

G-M1..4 PARTIAL, G-M5 NOT ISSUED, Global NOT CERTIFIED, no sizing in VT08 (CIBO Risk sovereign), PR #626 draft/no orders/no merge.
