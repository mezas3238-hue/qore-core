# CIBO — Trader Lab speed repair (2026-10-08)

## Source of truth and scope

- Repository: `mezas3238-hue/qore-core`
- Target research branch: `agent/cibo-causal-expectation-leakage-fix-001`
- Implemented via PR #728, merge commit `74ee781d2299d30306daa58f0639bc345524d23b`
- New runner: `scripts/cibo_trader_lab_batch_runner.py`
- Research only. Never promote reused holdout to fresh OOS/certification.

## Root cause confirmed from GitHub Actions timestamps

Runner provisioning took ~1–2 s; artifact recovery ~20–31 s.
The heavyweight experimental Python phase took 254–362 s. Legacy
workflows spawned 8–11 standalone interpreters, all independently
reading/parsing the same six symbols' RAW_M5 histories (and sometimes
building lifecycle maps several times per case). Oversubscription
increased contention. The independent Trader Lab Fast prepared-ledger
lane was much faster, but it does not automatically run these same
research-specific sweep arguments.

## Verified remediation

Each migrated Bash `run_case` now emits exactly the original standalone
CLI arguments as one JSON array line in `$RUNNER_TEMP/cibo-cases.jsonl`.
It then runs once:

```bash
python scripts/cibo_trader_lab_batch_runner.py \
  --cases "$RUNNER_TEMP/cibo-cases.jsonl" \
  --workers 2
```

The runner validates input/output/source identity, preloads the six
SHA256-custodied RAW_M5 source trees just once, and forks bounded Linux
workers using copy-on-write memory. The worker invokes the unchanged
`cibo_trader_lab_three_mode_ceiling.main()`, so CLI economics,
decisions, and output paths remain unchanged. Any child failure
fails the whole workflow. No cross-run pickle/trust boundary was added.

## A/B historical results (GitHub Actions end-to-end wall times)

| Suite | Legacy run | Legacy | Optimized run | Optimized | Replay row parity |
| --- | --- | ---: | --- | ---: | --- |
| H4M5 loss cluster, eight cases | 37739069539 | 298 s | 37755530387 | 86 s | 8/8, all 26 fields match exactly |
| Floor seeking accelerated, eleven cases | 37738952819 | 394 s | 37755554687 | 109 s | 11/11, all 25 fields match exactly |

Preload was 25.7–26.2 s, with typical isolated child case
~8.6–8.9 s. Outcomes include capital, DD, gross losses, and
strict-Pareto flags with zero differences.

## Mandatory rule for future heavy experiments

Do **not** introduce new concurrent invocations of
`python scripts/cibo_trader_lab_three_mode_ceiling.py ... &`
with the same six source histories. Use the JSONL batch runner with
bounded workers and verify strict parity to a known-good control.
Conserve SHA256-validated input recovery and decision count; never
silently change stop, leverage, compound or portfolio economics.
Avoid treating a 3.2-second cached microbenchmark as an estimate for
full lifecycle M5 research sweeps.

## Remaining scope

The two named 37772 workflows are migrated and tested. Other legacy
research workflows may still use the old subprocess pattern; migrate
those that are actively reused on a case-by-case basis, with before/after
timings and strict JSON field parity. No assertion of having modified
all historical workflows is justified.
