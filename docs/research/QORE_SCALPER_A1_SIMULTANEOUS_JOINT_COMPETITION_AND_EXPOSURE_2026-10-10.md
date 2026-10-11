# QORE SCALPER A1 — Simultaneous Joint-Candidate Causal Constraints & Factor Exposure

**Date:** 2026-10-10  
**Owner:** A1 cognition, issue #756, PR #758  
**Independent methodological review:** A2 issue #757, PR #759  
**Parent:** PR #623; DRAFT / UNMERGED. Research-only GitHub branch `agent/scalper-architect-a-cognition-20261010`. **NO VPS, LIVE, production, broker connection, real risk authority or certification claim**.

## What was missing

Earlier A1 `capitalizer_a1_multi_hypothesis_research.py` preserved multiple H1→M15→M1 source opportunities per market/time and ran the actual nine-market `build_master_cognitive_frame` under independent candidate-specific as-of projections. Crucially, **other contemporaneous DECISION markets were temporarily FOCUSED per projection**, so an individual `PASS_TO_STRATEGY` was *not* evidence that simultaneous hypotheses were jointly consistent. Old `capitalizer_opportunity_competition.py` counts only one candidate per DECISION market, not all source opportunities. The candidate-count demand census fixed denominator accounting but did not reveal pair collisions.

## New implementation, A1-only

`src/qore/infrastructure/trader_lab/capitalizer_a1_joint_competition_research.py` is an **opt-in joint constraint ledger**, taking exactly one evidenced `A1MultiHypothesisBarrier` and the corresponding `A1MultiHypothesisEvidence`. It enforces source-ID set parity, strictly aligned time barrier, no future causal graph, no duplicate source exposure receipts and exact remaining session slots.

1. For every **individually PASS** pair, a deterministic, source-ID-sorted `A1JointPairEvidence` records both source IDs, markets and the causal relation. Same-market hypotheses are marked `SAME_MARKET_OVERLAPPING_HYPOTHESES`, **without killing either one**. Across markets, the actual `CapitalizerCrossMarketCausalGraph` relation and source-provided evidence tokens are used; missing/UNKNOWN graph edges remain `CAUSAL_RELATION_UNKNOWN`, **never silently INDEPENDENT**. REDUNDANT, MUTUALLY_INVALIDATING and other linked relations trigger a *review need*, not a new author-unproven universal filter.
2. `A1ProspectiveSourceExposure` can optionally provide source-identified, timezone-aware hypothetical side and `Decimal` risk R. Given **both** sides and positive hypothetical risk per pair, code uses the existing native `factor_exposures` function with open positions and both proposed tickets to show net/gross shared factors. This is a *scenario*, not broker volume, sizing authorization, real portfolio acceptance or a data-derived suggested risk amount. Missing inputs are explicitly flagged `PROSPECTIVE_EXPOSURE_UNAVAILABLE`, never fabricated or treated as 0.
3. One `A1JointCandidateEvidence` is emitted **for every original source ID**, including WAIT/ABSTAIN candidates (which are not silently removed from census). It retains each earlier cognitive WHY plus explicit joint-collision and unknown-relation peers; pair graph connects individually PASS candidates only. Global source-ID parity enforced.
4. `A1JointCompetitionEvidence` records **capacity demand against MAX3 session slots** and whether scientific source-policy arbitration is required. The immutable report enforces `selected_source_ids=()`, `changes_source_eligibility=False`, `changes_economic_admission=False`, `grants_capital_authority=False`, `uses_future_outcomes=False`. Source-author-certified ranking and executable selection remain P0 blockers, not implicitly decided by alphabetical IDs or surrogate scores.

## Falsification tests and official GitHub Actions

Commits:
- `e2d5aa20f1414f8514f62cd70389a8d4adc41acc`: new joint pairwise causal/exposure ledger.
- `15c89d74177df3b19eee0c4af04785bb1c03f032`: regression tests for exact three-source same-minute joint ledger, missing/unknown graph, authoritative cross-market REDUNDANT relation, explicit hypothetical FX legs, future graph, mismatched census, duplicated/future exposure, positive-risk validation, and dense nine-source source/permutation parity with **36** pairwise relationships and **one** available slot.
- `4c7ab270ce2dc2816700615bd396ff9d276dd2b8`, `e982e86ee44659a8c1e5b6e78611a70dbb92c386`: Ruff formatting/import cleanup.
- `7a6fcb9d26494294bb1fa9bdf559618498d46b56`: fix assertion that same-symbol AUDJPY/AUDJPY shares **AUD and JPY**, while AUDJPY/USDJPY shares **JPY**, proving factor accounting is asset-specific.
- `e5f35b5b83f5e7785576456bb9a020ac12118f8f`: Mypy variable-length evidence tuple annotation.

**Official latest code SHA `e5f35b5b83f5e7785576456bb9a020ac12118f8f` — [QORE Scalper Cognition A1 Audit #38056278638](https://github.com/mezas3238-hue/qore-core/actions/runs/38056278638) SUCCESS: Ruff full repo, Mypy `src tests` (1,627 source/test files), 46 focused pytest all PASSED.** Earlier quality failures during this development were diagnosed and fixed in the above commits; never cite a failed intermediate run as an acceptance result.

## Unresolved gaps and scientific honesty

- These tests use **constructed research fixtures**, not true synchronized historical nine-market M1 market feeds. The new evaluator restores pairwise simultaneous evidence visibility but is **not a proven/global winner selector, a QORE Risk evaluator or a real trading engine**.
- Pair graph labels represent observations, not an author-backed ICT/TTrades prioritization. Same-market collision does not give permission to reject the other candidate; unknown relation does not prove independent, and shared factor does not by itself mandate rejection.
- Tested R are *hypothetical scenario amounts*, not available broker capital or chosen lotage. Funding/commission/spread/slippage cannot be deduced from them.
- No selected/executed/settled broker receipts have been wired to causal memory; the earlier tests of prequential memory do not establish realized strategy edge.
- **Critical next integration:** authenticated nine-market native-M1 as-of snapshot construction, real H1→M15→M1 multi-candidate source census, source-methodologically validated **intra/inter-market selection policy** without source rejection on presentation, portfolio coexistence/exposure limits determined by QORE Risk, and actual chronological replay before any financial inference.
- Required full quality controls remain: exact baseline opportunity identity denominator, >=80% source winner-count and >=90% positive winner-R preservation, complete 9/9 market-session-era matrix, DD <=6R (target 3–5R), PF/expectancy/Sharpe/Sortino, provider-portable spread/commission/slippage stress, preregistered held-out results, independent A2 author evidence. **Owner-rejected 90-trade V50-G is not a promotion candidate.**

**Status:** simultaneous pairwise *constraint evidence* is built, CI GREEN; executable arbitration + real economic replay are **NOT COMPLETE**, Scalper **NOT CERTIFIED**. Keep master #623 and both architect PRs DRAFT/unmerged.
