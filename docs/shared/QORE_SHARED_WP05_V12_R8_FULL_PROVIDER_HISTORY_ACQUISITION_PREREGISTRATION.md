# QORE Shared WP-05 — V12 R8 Full Provider-History Acquisition Preregistration

**Program:** QORE Meta-Cognitive Scientific Intelligence  
**PR:** #635  
**Issue:** #643  
**Identity:** `QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_R8_FULL_ACQUISITION_001`  
**Status:** PREREGISTERED / EXECUTION AUTHORIZED BY FULL COVERAGE PILOT  
**Scientific partition:** R8 only  
**R6/R5:** CLOSED  
**WP-05 fresh holdout:** CLOSED  
**Final Shared certification holdout:** CLOSED

## 1. Authorization evidence

The full acquisition is authorized only because the outcome-blind coverage pilot
completed GREEN on the frozen source-only manifest:

- acquisition-manifest SHA256:
  `2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191`;
- provider symbol: `USTEC`;
- coverage-pilot run: `36452997906`;
- coverage-pilot Git SHA:
  `f266893f2aa04533fbf584b89b215d49cc917a5b`;
- preregistered temporal sample:
  `[0, 736, 1473, 2210, 2947]`;
- coverage result: `full_bid_ask_history`;
- retained BID ticks: 50,200;
- retained ASK ticks: 50,307;
- immutable pilot shards: 16;
- pilot dataset SHA256:
  `06a145f763145eac5121878d4aa81c8c11bae86ea5a865eed9a7d6f5621d23e6`.

This evidence authorizes acquisition only. It does not admit a V12 scientific
representation.

## 2. Frozen population

The acquisition population is exactly every window in the frozen R8 manifest:

- source population: 6,804;
- merged acquisition windows: 2,948;
- provider symbol: `USTEC`;
- source range:
  `2016-04-20T14:00:00Z → 2018-05-18T19:30:00Z`;
- context around source events: `t-60m → t+15m`.

No target/outcome may alter, remove, rank, prioritize, retry selectively, or
otherwise choose an acquisition window.

## 3. Deterministic sharding law

The full acquisition uses exactly 16 logical shards.

For manifest window with integer `manifest_index`:

```text
logical_shard = manifest_index % 16
```

Properties:

1. every manifest index belongs to exactly one logical shard;
2. shard assignment depends only on source-manifest ordinal;
3. shard assignment is independent of target/outcome, market result, tick
   density, provider success, or any later scientific metric;
4. a failed shard may be rerun only as the same logical shard against the same
   frozen manifest and codec;
5. no failed window may be silently dropped.

Provider pressure is bounded by workflow `max-parallel: 2`. Each connection
retains the existing request interval at or below the frozen historical
5 requests/second/connection ceiling.

## 4. Acquisition contract

For every selected manifest window and for both BID and ASK independently:

1. resolve the exact authenticated DEMO provider identity;
2. request the exact manifest interval;
3. enforce the seven-day provider request bound;
4. paginate strictly backward while `hasMore=true`;
5. decode the first timestamp and price as absolute provider values;
6. decode subsequent timestamp and price fields as signed deltas accumulated
   from the preceding provider record;
7. permit zero timestamp delta for multiple updates in one millisecond;
8. reject non-causal timestamp progress or reconstructed non-positive prices;
9. retain provider wire timestamp/price values plus reconstructed absolute
   provider-relative price;
10. retain BID and ASK as independent streams;
11. preserve provider event time separately from retrieval time;
12. write immutable shard schema
    `qore.shared.wp05.v12.historical_quote_side_shard.v2`;
13. preserve provider order for same-millisecond quote events;
14. never synthesize the opposite quote side.

## 5. Full-acquisition completion gate

The reducer may declare `COMPLETE` only if all conditions hold:

- all 16 logical shard reports exist;
- exactly 2,948 unique manifest indices are reported;
- the sorted reported index set equals `range(2948)`;
- no manifest index appears in more than one logical shard;
- every reported window has BID count > 0;
- every reported window has ASK count > 0;
- every shard confirms the frozen manifest SHA256;
- every shard confirms R8-only acquisition;
- every shard confirms target/outcome unread;
- every shard confirms R6/R5 unread;
- every shard confirms fresh holdout unopened;
- every shard confirms no Shared methodology, sizing, Risk, order, or Execution
  authority;
- every shard dataset digest is valid SHA-256;
- the reducer produces a deterministic global dataset fingerprint from the
  ordered shard identities and content digests.

Any missing window, duplicated ownership, provider error, malformed page,
digest mismatch, governance mismatch, or incomplete BID/ASK evidence causes
the acquisition to fail closed.

## 6. Retry law

A technical failure is not scientific evidence.

Retry is permitted only when:

- the manifest is unchanged;
- logical shard identity is unchanged;
- acquisition semantics are unchanged;
- codec semantics are unchanged;
- no target/outcome has been inspected to decide the repair.

If codec semantics must change because provider wire evidence proves the
current codec false, the change must be documented and tested before rerunning
the affected fixed population.

## 7. Post-acquisition boundary

A COMPLETE acquisition authorizes only source-side R8 sensor engineering.

It does **not** authorize R6/R5 or any fresh holdout.

After COMPLETE, preprocessing, missingness, staleness, sampling, spread
construction, candidate feature families, representation identity and
information-gain protocol must be preregistered/frozen under R8 governance
before target-aware R8 discovery begins.

Only after the final V12 representation is frozen may R6 and R5 be opened once
against the unchanged WP-05 development gate:

- false structural-failure reduction >= 2000 bps independently;
- terminal detection preservation >= 9500 bps independently.

## 8. Sovereignty

This acquisition is observation infrastructure only.

It grants Shared no Trader methodology authority, no CIBO sizing/capital
authority, no Risk authority, no order authority and no Execution authority.
