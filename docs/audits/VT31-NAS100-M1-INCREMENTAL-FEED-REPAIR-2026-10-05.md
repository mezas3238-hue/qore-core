# VT31 NAS100 M1 incremental feed repair — 2026-10-05

## Scope and source truth

- Owner: Sergio Meza.
- Authorized environment: FundedNext DEMO account `12059127` on `vps-vrix`.
- GitHub `main` observed at mission start: `c98d486a760056d9a71173c7041cf6f0c58bd9e9`.
- Runtime lineage inspected and repaired: `agent/vps-runtime-boundary-hardening-001` at
  `5a30f39140b0e5a8030d58be1703b69347ba0ccb`.
- Repair branch: `agent/vt31-demo-m1-feed-repair-001`.
- The certified strategy identity remains
  `VT31_NAS100_STRUCTURAL_TARGET_V1`; no strategy rule or economic parameter changed.

## Forensic finding

The exception originated in `Vt31Nas100M1Cache._ingest`. The old cache:

1. converted MT5 rows to a canonical `OhlcSnapshot`;
2. marked a bar final solely when local observation time exceeded
   `bar_close_time + 2 seconds`;
3. compared the entire OHLC object on later reads;
4. raised the generic `VT31 contradictory completed M1 bar` for every post-seal
   difference;
5. discarded `tick_volume`, `real_volume`, `spread`, prior/current fingerprints and
   field-level differences from the failure evidence.

That model could not distinguish a causal late tick or provider settlement from an
incompatible historical rewrite. It also replaced the cached value before raising,
which made the failure self-clear on the next identical read without proving why the
revision was safe. Finally, the resident loop logged an incremental feed failure but
did not explicitly include feed health in the subsequent VT31 decision preflight.

The old production log contains only the generic message, so it is impossible to
recover the exact changed field for the 2026-10-05 events retrospectively. The repair
therefore does not invent that missing fact. The new receipt makes the exact field,
old value, new value and numeric difference mandatory for every future revision or
contradiction.

## Repair

The M1 cache now uses a deterministic reconciliation state machine:

- provider precision is read from `NDX100` `symbol_info().digits` and frozen for the
  cache lifetime;
- raw and precision-normalized OHLC are retained separately;
- `tick_volume`, `real_volume`, `spread`, source, sequence, first-seen time, seal time,
  revision count and cache version are retained;
- an in-progress revision is `LEGITIMATE_UPDATE`;
- a raw-only difference that collapses at provider precision is
  `PRECISION_NORMALIZED`;
- an identical repeat is idempotent;
- a post-seal revision is `LATE_TICK_RECONCILED` only within 30 seconds and only when
  it is a causal extension: open unchanged, high non-decreasing, low non-increasing,
  close inside the revised envelope, and volumes non-decreasing;
- every other post-seal revision is `TRUE_CONTRADICTION` and remains fail-closed;
- a true incremental feed failure now participates directly in VT31 preflight, so a
  decision cannot consume an older cache silently.

The runtime emits:

- `VT31_M1_BAR_RECONCILIATION`;
- `VT31_M1_BAR_ACCEPTED`;
- `VT31_M1_BAR_SEALED`;
- `VT31_DECISION` with `candidate=true/false` when strategy evaluation is reached.

Each reconciliation receipt includes provider/QORE symbols, broker raw timestamp,
broker wall time, UTC and New York time, open/close time, OHLC, previous OHLC,
volumes, spread, sources, sequence, fingerprints, revision count, cache version,
bar/cache/history/incremental/decision states, changed fields and numeric differences.

## Replay evidence

The focused replay covers the same causal shape that the old code misclassified:

1. an M1 bar evolves while open;
2. it receives its first completed representation;
3. it changes inside the 2-second decision window;
4. it is sealed;
5. a later tick increases volume and changes close without shrinking the OHLC
   envelope.

Old rule: the post-seal object inequality is `FAIL`.

New rule on the same sequence: `LATE_TICK_RECONCILED`, with deterministic rounded
close and a complete receipt.

An adversarial replay that decreases a sealed high remains
`TRUE_CONTRADICTION / FAIL_CLOSED` and reports both high and close deltas.

## Validation executed

- VT31 cache/runtime tests: `15 passed`.
- VT31 plus resident runtime contract tests: `30 passed` before the final preflight
  guard was added.
- Official VT31 workflow-focused selection after the final preflight guard:
  `58 passed`.
- Full repository suite: `7682 passed`, `8 warnings`, no failures.
- Ruff on changed Python files: PASS.
- Mypy strict on `vt31_nas100_live.py`: PASS.
- Python compilation and `git diff --check`: PASS.

## Safety invariants

- No LIVE activation was added or invoked.
- `order_submission_authorized` was not changed.
- `mode=shadow` was not changed.
- No order-send path was relaxed.
- Provider symbol remains `NDX100`; QORE symbol remains `NAS100`.
- The 2-second tick freshness and decision deadline remain unchanged.
- True contradictions remain fail-closed.

## VPS DEMO validation status

The execution environment used for this repair could resolve the GitHub repository
but could not resolve or connect to the SSH host alias `vps-vrix`; no native VPS
surface was exposed. Consequently, this document makes no claim that the patch is
already installed or observed on the VPS.

Physical completion still requires, on `vps-vrix` in SHADOW/NO-SEND mode:

1. check out the exact repair commit;
2. run the installer without `-ActivateLive` and without changing the activation
   artifact;
3. verify the runtime state SHA and account identity;
4. observe multiple new M1 bars;
5. count accepted, sealed, reconciled and true-contradiction receipts;
6. prove VT31 reaches `VT31_DECISION` with either candidate or valid `ABSTAIN`;
7. capture the exact old/new field differences if another contradiction occurs.

Until that physical observation exists, code/replay repair is PASS and VPS DEMO
operational closure is PENDING.
