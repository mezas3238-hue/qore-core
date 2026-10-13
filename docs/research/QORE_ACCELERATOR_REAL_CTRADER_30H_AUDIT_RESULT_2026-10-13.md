# QORE Accelerator — audited cTrader REAL-source 30h qualification (2026-10-13)

## Conclusion: SOURCE_QA_PASS / EXECUTABLE_EDGE_NOT_ASSESSED

Independent GitHub Actions run:
https://github.com/mezas3238-hue/qore-core/actions/runs/38425782083

Signed aggregate report artifact:
https://github.com/mezas3238-hue/qore-core/actions/runs/38425782083
(artifact name begins qore-accelerator-ustec-real-30h-QA-NOT-EDGE).

Upstream authenticated sources, no raw bytes checked into public Git:
- Pilot 6 hours, artifact 11801205225, raw ZIP SHA256
  7c599294f3853c684f05ee17941b530f35b80bee832e115f51d3d5ff6c3c6f03.
- Follow-on 24 hours, artifact 11801263502, raw ZIP SHA256
  a0cb3e62f2c889b414e7283d7d426576468e753b34f60351d0c9aa1965fc1edf.
- Parent PR #899 and #901 document cTrader IC Markets DEMO provenance.
- Every included file is checked against the source SHA256SUMS record; decoded
  decimal price is also compared with native integer price x 1e5 and UTC
  timestamps are checked against the preregistered one-hour window.

30 noncontiguous development hours, 10 days, 3 session windows per day:
- 241,538 original BID tick-side observations.
- 241,565 original ASK tick-side observations.
- 483,103 total original observations.
- 240,550 accepted AS-OF quote states at frozen <=250ms side staleness.
- 2,004 candidate states quarantined as stale and **0 accepted crossed quotes**.
- 30/30 independent normalized manifests ingested and reverified in an
  ephemeral local content-addressed lake during the successful workflow.
- Source results include no orders, no broker fill acknowledgments, no
  accessed fresh OOS holdout, no Profit Factor and no USD PnL.

One controlled parity benchmark, first 1,500 source records PER SIDE,
independent O(n^2) reference versus indexed as-of runner:
- Reference 0.090778 sec; accelerated 0.002814 sec.
- Speedup measured **32.26x ON AS-OF JOIN, NOT ENTIRE TRADER LAB**.
- Bit-exact quote state and quarantine-count parity PASS.
- Runtime measurements depend on runner hardware/cache.

The validated probe is SHA signed, with reproducible source ZIP inputs,
preregistered max stale 250ms, expected quantities and independent baseline.
Signed metadata is stored as a 90-day GitHub Actions artifact; original raw
files remain in preexisting expiring artifacts. No LICENSE authorization for
public raw storage has been demonstrated. Do not store source bytes in repo.

## Operational integration

Code: src/qore/infrastructure/research_accelerator/real_source.py
Workflow: .github/workflows/qore-accelerator-real-ustec-30h.yml

Run offline with exact source ZIPs:

    python -m qore.infrastructure.research_accelerator.real_source \
      --pilot6 pilot6.zip --wave24 wave24.zip --report out/real-source-30h.json

Result is a signed report and hash sidecar. Output arrays give per-window
quarantine and spread measurements. Workflow downloads upstream GitHub Actions
archives with GITHUB_TOKEN, makes data lake transiently, checks it, and
destroys/unpublishes raw files. Only aggregate QA goes to Actions artifact.
Use artifact evidence for source qualification; never claim 3Y quote coverage.

## Scientific/economic conclusions

- SOURCE_QA = PASS for those 30 selected development hours.
- FAST_ASOF_REFERENCE_PARITY = PASS on sample of 1,500 ticks per side.
- FULL_TRADER_BACKTEST_FAST_FORWARD_PARITY = NOT_ASSESSED.
- PnL_PROFIT_FACTOR_DRAWDOWN = NOT_ASSESSED.
- EXECUTION_FILL_BROKER_PARITY = NOT_ASSESSED.
- NAS100 / USTEC venue & contract equivalence = BLOCKED.
- 3 years continuous BID/ASK historical coverage = BLOCKED.
- Persisted private raw data lake with approved licence = BLOCKED.

Next architect must solve those scientifically without consuming holdouts,
claiming historic alias equivalence, or changing Trader Lab authority.
No LIVE, no capital, no merge without explicit Owner instruction.
