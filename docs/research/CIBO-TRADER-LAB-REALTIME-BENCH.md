# CIBO Trader Lab — Standalone Real-Time Test Bench

## Purpose

This bench runs the three fixed one-year research groups directly on a machine
that has QORE Core and the retained evidence on local disk.

It does **not** invoke GitHub Actions, `gh`, a broker, cTrader, VPS, LIVE,
Production, or real capital.

Each run executes:

```
GROUP_1 ─┐
GROUP_2 ─┼─ in parallel
GROUP_3 ─┘

Inside each group:
7 frozen Traders together
  → one chronological stream
  → shared USD60
  → shared CIBO
  → shared sovereign QORE Risk
  → Core
  → Compound
  → Compound Portfolio
  → leverage 1x/2x/3x/4x
  → WFO 5-fold + 6-fold
  → Monte Carlo
  → provider-cost stress
  → adverse-slippage stress
  → remove-best-1/2/3 concentration stress
  → chronological block stability
  → per-Trader + portfolio scientific report
  → CIBO function-behavior report

After all three groups:
canonical all-seven-positive 3x1Y sensor
```

The Trader methodologies remain frozen. The study target is CIBO.

## Local evidence layout

The config points to local paths. No artifact IDs are required at runtime.

Required files:

```
assembly/
  GROUP_1/seven-trader-cibo-batch.json
  GROUP_2/seven-trader-cibo-batch.json
  GROUP_3/seven-trader-cibo-batch.json

provider/
  provider-numeric-execution-freeze.json

regime/
  AUDJPY/.../symbol-consumption-manifest.json
  EURUSD/.../symbol-consumption-manifest.json
  GBPJPY/.../symbol-consumption-manifest.json
  GBPUSD/.../symbol-consumption-manifest.json
  XAUUSD/.../symbol-consumption-manifest.json
```

The regime roots must also contain the retained Market Atlas M5 ledgers
consumed by the canonical historical-regime loader.

## Commands

Run the bench's own workflow-independent self-test:

```bash
python scripts/cibo_trader_lab_realtime_bench.py selftest
```

The self-test does not execute market evidence. It validates the local runner,
event persistence, three-way parallel topology and the absence of GitHub,
Actions or broker commands from the execution path.

Validate all local dependencies:

```bash
python scripts/cibo_trader_lab_realtime_bench.py \
  --config docs/research/CIBO-TRADER-LAB-REALTIME-BENCH-CONFIG.json \
  doctor
```

Run immediately in the terminal:

```bash
python scripts/cibo_trader_lab_realtime_bench.py \
  --config docs/research/CIBO-TRADER-LAB-REALTIME-BENCH-CONFIG.json \
  run
```

Every event is emitted as one JSON line while the run is active.

Start the local dashboard:

```bash
python scripts/cibo_trader_lab_realtime_bench.py \
  --config docs/research/CIBO-TRADER-LAB-REALTIME-BENCH-CONFIG.json \
  serve --host 127.0.0.1 --port 8765
```

Open:

```
http://127.0.0.1:8765
```

The dashboard uses Server-Sent Events (SSE) and shows the three group stages,
live process output, the persisted run state, and the final canonical sensor.

## Persistent run record

Each execution is written under:

```
<workspace>/runs/<run-id>/
```

with:

- `status.json`
- `events.jsonl`
- `GROUP_1/lab/*`
- `GROUP_1/group-result.json`
- `GROUP_2/...`
- `GROUP_3/...`
- `sensor.json`

A machine restart does not erase completed run evidence.

## Scientific boundary

These three holdouts are explicitly adaptive/burned research surfaces. The
bench can be used to investigate and repair CIBO, but its results do not become
Fresh OOS merely because the bench is standalone.

The canonical stop gate still requires the same CIBO configuration fingerprint
to pass all required gates across all three groups, including positive CIBO
economics for each of the seven Traders.

## Why this is a real bench

The bench owns execution and observability locally:

- no workflow queue;
- no Actions runner availability;
- no artifact upload/download during a run;
- three groups run concurrently;
- deterministic local inputs;
- live events;
- persisted results;
- canonical sensor runs immediately after the third group completes.

GitHub remains source control, but GitHub Actions is not part of the execution
path.


## Mandatory scientific battery per CIBO candidate

Every leverage candidate in every group must emit the same complete battery for:

- CORE;
- COMPOUND_INCREMENTAL;
- COMPOUND_TOTAL;
- COMPOUND_PORTFOLIO_INCREMENTAL;
- COMPOUND_PORTFOLIO_TOTAL.

Each lane includes:

- P/L, Profit Factor, expectancy and max drawdown;
- chronological five-block and six-block stability;
- expanding chronological WFO with five and six folds;
- Monte Carlo with deterministic seed;
- provider-cost stress at 1.25x, 1.50x and 2.00x;
- adverse-slippage stress at +25%, +50% and +100% of frozen provider cost;
- remove-best-1, remove-best-2 and remove-best-3 concentration stress;
- losses-first and winners-first drawdown ordering stress.

The final sensor is fail-closed if the complete battery is missing. Leverage is
only one dimension of the experiment; it never substitutes for Compound,
Portfolio, WFO, Monte Carlo or stress testing.
