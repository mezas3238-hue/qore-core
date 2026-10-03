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
  → per-Trader + portfolio scientific report

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
