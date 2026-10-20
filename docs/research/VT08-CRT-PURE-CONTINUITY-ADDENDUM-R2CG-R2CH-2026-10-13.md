# VT08 CRT PURE — MASTER CONTINUITY ADDENDUM R2-CG/R2-CH — 2026-10-13

**Read with original:** `docs/research/VT08-CRT-PURE-MASTER-HANDOFF-2026-10-13.md` and `docs/research/VT08-CRT-PURE-CONTINUITY-ADDENDUM-R2CE-R2CF-2026-10-13.md`.

**Repository:** `mezas3238-hue/qore-core` · **PR:** #626 · **Branch:** `agent/vt08-crt-pure-source-identity-001` · **Status:** research-only; no merge, deployment or certification promotion.

## 1. New work

### R2-CG — WHY 2016 / 2023 and hard WAIT capacity

- Frozen pre-result spec: `docs/research/VT08-CRT-PURE-R2CG-FAILURE-ATTRIBUTION-WAIT-CAPACITY-FREEZE-001.md`.
- Source: `src/qore/infrastructure/trader_lab/vt08_crt_pure_r2cg_wait_capacity_forensics.py` and matching tests.
- Workflow: `.github/workflows/vt08-crt-pure-r2cg-wait-capacity-forensics.yml`.
- CI final **38446929784**: quality, AUDUSD, USDJPY all **SUCCESS**. Reproduced original R2-CF each OOS fold and pooled, trade count, PF, R, DD, DOA, per-cost stress, source reports.
- Full result: `docs/research/VT08-CRT-PURE-R2CG-FAILURE-ATTRIBUTION-WAIT-CAPACITY-RESULT-001.md`.

**Hard structural limit:** under the frozen initial cognitive decisions and only one-M15 WAIT, max theoretical cumulative trades across OOS years = **AUDUSD 1,671/11Y = 151.91/year; USDJPY 967/8Y = 120.875/year**. Both below research threshold 170/year **even if all remaining viable WAIT trade**. These counts do not reflect profitability or concurrency. No possibility of meeting 170 purely by retuning the second-WAIT decision; ABSTAIN resurrection is prohibited.

**AUDUSD OOS-2016 degradation** R2-CF vs control = **-10.96495970R**. All difference from 48 CONTROL_ONLY_EXECUTE favorable delayed trades (+10.96495970R) downgraded to UNKNOWN/WAIT due historical early-warmup cell-support limitation. Do not loosen 4Y warmup post hoc.

**USDJPY OOS-2023 degradation** R2-CF vs control = **-9.83056095R**. 42 NESTED_ONLY_EXECUTE lost -8.22413807R; 3 CONTROL_ONLY_EXECUTE +1.60642288R disappeared. The 27 `CLOSE_NEG_050_TO_0R | KNOWN | WAIT->EXECUTE` in USDJPY lost **-8.50289355R**. This is bad prior-history generalization, not an authorized ban on negative M15 states.

### R2-CH — archived new independent source hypothesis census

- Frozen pre-result spec: `docs/research/VT08-CRT-PURE-R2CH-ARCHIVED-SOURCE-NOVELTY-CENSUS-FREEZE-001.md`.
- Source: `src/qore/infrastructure/trader_lab/vt08_crt_pure_r2ch_archived_source_novelty.py` and matching tests.
- Workflow: `.github/workflows/vt08-crt-pure-r2ch-archived-source-census.yml`.
- CI final **38447732371**: quality, AUDUSD, USDJPY all **SUCCESS**. R2-F archived original counts validated, original selected ledgers SHA256 identified; ambiguity-safe structural-key comparison.
- Full result: `docs/research/VT08-CRT-PURE-R2CH-ARCHIVED-SOURCE-NOVELTY-CENSUS-RESULT-001.md`.
- Scope strictly **2024-09-21 to 2026-09-21** original R2-F (two years). **Do not extrapolate** into R2-CF 11Y/8Y OOS.

R2-F reported:
- AUDUSD 563 source events, 325 later, 217 source events with body confirmation/next slot; 107 later-confirmed of which **43 structurally unmatched** with long-history original selected-source ledger, over **33 parents**.
- USDJPY 528 source events, 305 later, 191 body-confirmed/next slot; 89 later-confirmed of which **32 structurally unmatched**, over **23 parents**.
- Ambiguous timestamp-key joins: 0 for both. Still a limited join, because exact source reference IDs differ across ledgers.
- **No economic signal, no multiple-entry authority and no new trade.** R2-F has `competition_policy_frozen=false`. These 43/32 are only unmatched source events, not proved independent profitable executions.

## 2. Current research finding and why not to chase old filters

Current one-WAIT density cannot meet research target without a genuinely different opportunity source population, independent hypothesis, or preregistered source/methodology evolution. R2-CH indicates that other causal source candidates exist but does **NOT** authorize accepting any and does **NOT** prove enough unique entries or expectancy. R2-CE USDJPY profitability did not survive strict R2-CF, and AUDUSD remains fragile at costs.

Avoid: repeating static filters, same-source ABSTAIN fallback, post-hoc excluding 2016/2023, changing min support after outcomes, third WAIT without separate causal preregistration, or economically multiplying outcomes by volume.

## 3. Next architect mission — R2-CI source/competition boundary

**This is the next task, not an already green gate.**

1. Audited primary CRT source rule review: whether later independently generated source events may become candidate entries in one C3, and whether one-entry-per-parent is an engineering rule versus primary strategy authority.
2. Build R2-F-to-R2-CC/CD equivalence tests at exact `(market,C3,source M15,reference IDs)` where reference mapping exists; classify unmatched-with-unknown-reference `PARTIAL`, not `PROVEN_NOVEL`.
3. Causal event availability: source candle closed at M15 end, confirmation body close established before next contiguous M15 entry, same parent original C3 expiry; no knowledge of later observations at source creation.
4. Deterministic parent competition/identity contract before any new economic replay; separate hypothesis generation, precedence, OCO, supersede vs invalidate and repeat entry semantics; no same-source resurrection.
5. Apply archived two-year census only as characterization; to validate density at original research horizon need equivalent full AUDUSD 11Y / USDJPY 8Y source histories with immutable PIT evidence.
6. Only after frozen legitimate source and competition contract, execute economic model with normalized R, original stop, target and STOP_FIRST, costs, broader OOS, positive-year breadth, then untouched holdout and gates.
7. If source authority or historical evidence is missing, leave `BLOCKED_PARTIAL`; never invent source semantics to force density.

## 4. Required unchanged owner rules

- **VT08 CRT PURE NEVER decides sizing, lot, volume, leverage, capital allocation or portfolio risk.** Trader gives hypotheses/cognition; CIBO/QORE Risk own risk and volume externally.
- No merge; no VPS, DEMO, LIVE, funded trading, production or real capital.
- BTCUSD is market-level research certified, remains frozen. Global certification still FALSE.
- Failed/thin candidates remain research-only; no claims of profitability not justified by real post-cost causal data.

## 5. Audit checkpoints

- R2-CG [CI 38446929784](https://github.com/mezas3238-hue/qore-core/actions/runs/38446929784).
- R2-CH [CI 38447732371](https://github.com/mezas3238-hue/qore-core/actions/runs/38447732371).
- Original R2-F [CI 35811162435](https://github.com/mezas3238-hue/qore-core/actions/runs/35811162435).
- Original R2-CF [CI 38442593863](https://github.com/mezas3238-hue/qore-core/actions/runs/38442593863).

No silent backfill of broker data; all tests above consumed archived GitHub files.

---

## 6. Subsequent R2-CI closure (authoritative continuity update, 2026-10-13)

R2-F's original `competition_policy_frozen=false` was **historical**; R2-G subsequently froze a `NEWEST_SUPERSEDES_CONFIRMATION_FIRST` model and max-one-trade-attempt-per-parent. Do not treat R2-F's older OPEN status as current freedom to execute additional source hypotheses.

A third, **preregistered** non-economic archival source audit now exists:

- [R2-CI freeze](VT08-CRT-PURE-R2CI-THREE-LEDGER-IDENTITY-FREEZE-001.md)
- [R2-CI final results](VT08-CRT-PURE-R2CI-THREE-LEDGER-IDENTITY-RESULT-001.md)
- [CI run 38448705957](https://github.com/mezas3238-hue/qore-core/actions/runs/38448705957) — quality, AUDUSD and USDJPY SUCCESS.
- Source: `src/qore/infrastructure/trader_lab/vt08_crt_pure_r2ci_three_ledger_identity.py`; tests and read-only triple-archive workflow `.github/workflows/vt08-crt-pure-r2ci-three-ledger-audit.yml`.

Exactly matching R2-F sources to R2-G selected entries by **C3 + source M15 + reference IDs** showed:

| R2-CH structurally unmatched later-confirmed sources | AUDUSD | USDJPY |
|---|---:|---:|
| Reproduced candidate source-slot records | 43 | 32 |
| Selected already by R2-G NEWEST | **0** | **0** |
| Selected by other R2-G policy only | 4 | 4 |
| Not selected by ANY historical R2-G policy | 39 | 28 |
| Exact reference-ID ambiguous or unmapped selected R2-G trades | 0 | 0 |

Interpretation: those historical sources exist, but they were **not admissible winning entries under frozen NEWEST selection**. The 39/28 are not executable permissions and cannot be summed with the one-WAIT capacity; some were competed away under one-entry-per-parent. R2-G evaluated alternative policies already and competition alone was economically insufficient.

**Current actionable scientific frontier:** authority/causal audit of genuinely new unique independent *parent and source* opportunities, if the original CRT strategy supports them. Do NOT create a new economic replay of these 39/28 as though no prior competition policy existed. Source/methodology authorization, causal entry, independent source identity and one-attempt/C3 rule must be reconciled first. If absent, close as `NO_SUPPORT` or `BLOCKED_PARTIAL`; do not alter the trader's sizing/volume authority.

**Current new end-of-turn checkpoint:** consult PR #626 head after writing this addendum; no merge or deployment.
