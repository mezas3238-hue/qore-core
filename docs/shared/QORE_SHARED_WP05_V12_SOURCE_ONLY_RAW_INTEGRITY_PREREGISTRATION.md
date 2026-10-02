# QORE Shared WP-05 V12 — Source-Only Raw Integrity Preregistration

Identity:

`QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_SOURCE_ONLY_INTEGRITY_001`

## 1. Scope

This audit is permitted only after the frozen R8 historical BID/ASK acquisition
has completed and before any target-aware V12 representation discovery.

Frozen upstream evidence:

- full-acquisition run: `36454372776`;
- acquisition Git SHA:
  `a54e7a3fe2708607be1da10a92ae44bc9479ee86`;
- manifest SHA256:
  `2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191`;
- global acquisition dataset SHA256:
  `ebbe30a887867bb917f0992b15e1600f9f06eccb07562b9625fcb9517fb381c8`;
- logical shards: 16/16;
- manifest windows: 2948/2948;
- retained BID ticks: 13,603,333;
- retained ASK ticks: 13,593,775;
- immutable provider pages: 6,781.

The audit may read only the immutable raw acquisition artifacts and their
source-only reports. It may not read target/outcome labels, R6/R5, any WP-05
fresh holdout, or the final Shared certification holdout.

## 2. Why this audit exists

The full-acquisition reducer proves exact window ownership, non-empty BID/ASK
coverage and deterministic dataset identity. It does not, by itself, prove that
every raw gzip page is internally self-consistent or that duplicate/conflict
metrics were actually measured.

Therefore no V12 scientific representation may be admitted until the raw
artifacts have been independently re-read and audited.

## 3. Frozen raw-page checks

Every `historical_quote_side_shard.v2` gzip page must satisfy all of the
following:

1. valid gzip + JSONL framing;
2. exactly one header before tick rows;
3. schema exactly
   `qore.shared.wp05.v12.historical_quote_side_shard.v2`;
4. side is BID or ASK and agrees with its path;
5. manifest/window index is within `0..2947`;
6. page index is non-negative;
7. request timestamps and retrieval timestamp are timezone-aware;
8. request interval is positive;
9. every provider event timestamp is timezone-aware and chronological inside
   the page;
10. every provider event lies inside the page request interval;
11. every provider event is not later than retrieval time;
12. every reconstructed relative price is a positive integer;
13. stored tick count equals the actual number of tick rows;
14. stored content SHA256 is recomputed from the exact canonical tick rows;
15. stored provenance SHA256 is recomputed from the exact header provenance;
16. filename provenance digest agrees with the recomputed provenance digest.

Any failure is a hard source-integrity failure.

## 4. Frozen duplicate/conflict definitions

These metrics must be computed from the raw data; they must never be hardcoded.

### 4.1 Page-key duplicate

Page key:

`(quote_side, window_index, page_index)`

If the same page key appears more than once with the same content hash, count
it as a page-key duplicate.

Required for admission: **0**.

### 4.2 Page-key conflict

If the same page key appears more than once with different content hashes,
count it as a page-key conflict.

Required for admission: **0**.

### 4.3 Strict page-time overlap

Within one `(quote_side, window_index)`, pages are reconstructed in event-time
order. If a later chronological page begins before the previous page ends,
count a strict page-time overlap.

Equal boundary timestamps are not automatically a conflict because cTrader may
contain multiple provider updates in the same millisecond.

Required for admission: **0 strict overlaps**.

### 4.4 Exact boundary-row repeat

If adjacent chronological pages share the same boundary timestamp and the exact
same canonical tick row, record it as a boundary-row repeat.

This is measured and reported. A non-zero value blocks automatic admission
until explained; it must not be silently deduplicated.

### 4.5 Same-timestamp provider updates

Multiple rows at one provider millisecond are explicitly legal. They are
measured as source diagnostics and must not be mislabeled as conflicts.

Exact canonical-row repeats inside the same timestamp group are reported
separately. They are not silently deleted.

### 4.6 Repeated page content across different page keys

Repeated content hashes across different page keys are diagnostic because
different acquisition windows can legally contain overlapping source evidence.
They are measured but are not automatically called provider duplicates.

## 5. Frozen full-dataset checks

The audit must independently prove:

- exactly 16 raw acquisition artifacts from run `36454372776`;
- every artifact is bound to acquisition SHA
  `a54e7a3fe2708607be1da10a92ae44bc9479ee86`;
- artifact `SHA256SUMS` verification passes before analysis;
- exactly 16 logical shard reports exist;
- re-reduction reproduces global dataset SHA256
  `ebbe30a887867bb917f0992b15e1600f9f06eccb07562b9625fcb9517fb381c8`;
- raw page count equals the reducer's immutable page-shard count;
- raw BID/ASK tick totals equal the reducer totals;
- every manifest window has positive raw BID and ASK evidence;
- exact page keys are unique;
- no strict page-time overlap exists;
- no raw-page structural/hash/provenance violation exists.

## 6. Source-only diagnostics for the next freeze

Without outcomes, the audit will report per-side distributions for:

- ticks per minute;
- leading evidence gap from requested window start;
- trailing evidence gap to requested window end;
- maximum observed inter-event gap within each window;
- same-millisecond multi-update groups;
- same-millisecond distinct-price groups;
- exact same-timestamp canonical-row repeats;
- repeated content hashes across different page keys.

These diagnostics may be used only to freeze the subsequent V12 preprocessing,
staleness, missingness and sampling laws. They may not be tuned against
target/outcome performance.

## 7. Admission consequence

A GREEN source-integrity audit authorizes the next **source-only representation
freeze**. It does not scientifically admit any V12 sensor representation.

R8 target/outcome discovery remains closed until preprocessing, staleness,
missingness, sampling, spread-construction rules, candidate feature families,
representation identity and information-gain protocol are separately frozen.

R6/R5 remain closed until the final V12 representation is frozen.

WP-05 fresh holdout and the final Shared certification holdout remain closed.

## 8. Sovereignty

This work is observation and scientific-governance infrastructure only.

Shared receives no Trader methodology authority, CIBO sizing/capital authority,
Risk authority, order authority or Execution authority.
