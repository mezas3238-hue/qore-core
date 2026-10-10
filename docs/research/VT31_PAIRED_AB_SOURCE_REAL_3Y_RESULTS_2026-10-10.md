# VT31 ICT cleanroom — VERIFIED 3Y MATCHED A/B SOURCE OUTCOMES

**Report:** 2026-10-10 · **Architect 1 / COG**, collaborative OPS review pending. **Scientific state:** completed SOURCE-M1 research, not executable-trade economics. **No trading rule was changed.**

## Execution evidence and preregistration integrity

- **[GitHub Actions #38040127136 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38040127136)**, exact measured code commit **`f794f509c12ad886def540b73bbc8a3e238214a4`**, 29 existing cleanroom tests passed, Ruff/compile + adversarial A/B selftests (strict later opposite MSS→FVG, boundary expiry and CE intrabar unknown), plus complete byte-verified owner-consumed 3Y NAS100 M1 source **1,059,784 M1**. [Full machine-readable paired evidence artifact #11664804507](https://github.com/mezas3238-hue/qore-core/actions/runs/38040127136) includes **all 2,140 original candidate IDs**, A and B outcome per candidate, original as-of timestamps, protected swing and qualified opposite MSS→FVG times, input SHA and source Git SHA.
- **Preregistered source-only primary rule BEFORE the above 3Y result** in commit [`d4db56fb45228d74a065349a97e562f2fbc6f657`](https://github.com/mezas3238-hue/qore-core/commit/d4db56fb45228d74a065349a97e562f2fbc6f657): net gain **at least +5.0 percentage points** in paired unambiguous source M1 CE overlap, **AND B indeterminate ≤10%** of ALL 2,140 original first FVG candidates. Both clauses mandatory. It is NOT an economic PF/expectancy/certification gate; economic evaluation needs actual historical quote/execution evidence.
- A = *untouched* jointly verified `VT31Trader` native COG+OPS source decisions. B = one passive `Shadow` with the **same original 3-M1 FVG**, CE and DOL. Only the source invalidation meaning changes: most recent opposing **three-M1 swing** confirmed *before original MSS break M1*, plus first qualifying opposite directional FVG **at OR AFTER** a native displaced opposing MSS, in exactly the original ICT time window. If last protected price is not a valid stop side relative to CE, B is **INDETERMINATE** (not admitted). One `VT31`, 2 internal models (London, New York), 3 NY-local windows (03:00–04:00; 10:00–11:00; 14:00–15:00) and M1 actual structure/FVG source.
- Original frozen input source `VT31_NAS100_OWNER_3Y_BASE_001`, SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, 2023-10-01 to 2026-10-01 exclusive, immutable source artifact `11459859004`, holdout SEALED. 2,286 complete 60-M1 source hours; **1,059,784** market-M1, **137,160** actual COG/OPS source evaluations, original first FVG **766 London / 721 NY AM / 653 NY PM = 2,140** exactly unchanged in both paired arms, no duplicate candidate IDs; **pending-without-valid-COG stays 0**.

## Locked primary endpoint: FAILED (despite more source CE opportunities)

| All original FVG candidate IDs | A — actual original | B — opposite swing shadow |
|---|---:|---:|
| Exactly matched source candidate IDs | 2,140 | 2,140 |
| **Unambiguous OHLC-M1 price overlap of original CE** (not fill) | **301** | **789** |
| Source valid CE % of all 2,140 | **14.07%** | **36.87%** |
| **Indeterminate** (not invalidated and not fill) | **637 / 29.77%** | **670 / 31.31%** |
| Invalidation before CE observation | 1,132 | 512 |
| Target reached before CE observation (distinct, no entry) | 53 | 111 |
| Original source window expired before CE observation | 17 | 58 |

**Actual matching:** **B-only** `VALID_CE` **496**; **A-only** `VALID_CE` **8**; both VALID_CE **293**; net **+488 source M1 CE overlaps**, equal **+22.803738 percentage points** on 2,140. The precommitted ≥+5pp **effect** clause is met, but B's **31.308411% indeterminate rate violates the ≤10% bound**. **PRIMARY TWO-PART SOURCE GATE: NOT MET. Do NOT promote B.** The A unknown rate was also high (29.77%), a market-evidence-resolution problem shared by both.

### Complete *pooled* paired contingency (mutually exclusive, same candidate ID; N=2,140)

| A result ↓ / B result → | B valid CE | B invalidated | B indeterminate | B target before CE | B expired | A total |
|---|---:|---:|---:|---:|---:|---:|
| **A valid CE** | 293 | 0 | 8 | 0 | 0 | **301** |
| **A invalidated** | 233 | 512 | 287 | 58 | 42 | **1,132** |
| **A indeterminate** | 263 | 0 | 374 | 0 | 0 | **637** |
| **A target before CE** | 0 | 0 | 0 | 53 | 0 | **53** |
| **A expired** | 0 | 0 | 1 | 0 | 16 | **17** |
| **B totals** | **789** | **512** | **670** | **111** | **58** | **2,140** |

The **263** A-indeterminate/B-valid cells represent recovered *source labels* whose A same-M1 ordering was ambiguous; do not pronounce the market orders as realized missed fills. The **233** A-invalid/B-valid are research CE opportunities preserved through a changed structural policy, still not broker fills. The opposite **8** A-valid/B-indeterminate cases are not secretly deleted.

### Three sessions — SECONDARY DESCRIPTIVE, not three independent optimizations

| Source window | Original FVGs | A valid CE | B valid CE | Net gain | Net gain pp | A indeterminate | B indeterminate | B unknown % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| London 03–04 NY | 766 | 115 | 263 | +148 | +19.321 | 230 | 237 | 30.940% |
| New York AM 10–11 | 721 | 110 | 282 | +172 | +23.856 | 216 | 223 | 30.929% |
| New York PM 14–15 | 653 | 76 | 244 | +168 | +25.727 | 191 | 210 | 32.159% |

The pooled entire-Trader source-only paired contrast is **the sole primary endpoint**, not whichever individual window happens to show the largest source effect. Preregistered exploratory multiple-testing familywise Bonferroni alpha **0.05/3 = 0.0166667**, if later any justified inferential tests are carried out. NO naive independent-day p-values were manufactured from repeated temporal market observations.

## Actual B terminal cause taxonomy vs same-M1 UNKNOWN

- B qualified first opposing displaced MSS followed by first opposing original-window M1 FVG: **510 definitive source invalidations** (London 191, NY AM 153, NY PM 166). Plus **174 instances where opposing-FVG occurred on same M1 as another conflicting source event**, which correctly have an indeterminate B terminal, so **684 first qualified opposite MSS/FVG events** were timestamped in matched source records. Of these, **122** qualified on the SAME M1 close as opposing MSS, and **562** on a LATER closed M1 still in the original window. No post-expiry opposite FVG was accepted.
- **B total source-terminal INDETERMINATE 670** = **619** same-M1 CE and cancellation/target/path conflicts (222 London, 209 NY AM, 188 NY PM) **plus 51** pre-MSS known opposite swing points not on a valid stop side of CE (15 London, 14 NY AM, 22 NY PM). **No missing protected pivot** was falsely replaced with a fabricated stop in this consumed source set.
- **B target-before-CE 111** (59 LON, 43 NY AM, 9 NY PM), classified as hypothesis fulfilled without source entry; not directional stop loss.
- **B expiry before CE 58** (16 / 19 / 23).
- **B unambiguous CE source overlaps 789** (263 / 282 / 244).
- **B full-FVG-close without prior eligible CE 2** (0 / 1 / 1).
- **B protected swing close breach as FIRST terminal 0** on this *specific counterfactual source classification*: that is a warning to audit **precedence and geometry** before interpreting protected pivots as a validated risk model. Do not conclude "protected swings never break". They may be hidden by earlier CE/opposite-FVG events and same-M1 ambiguous overlaps. The prototype's precedence is a declared algorithmic choice and cannot be retuned to improve B results after inspection.

## Destination of the extra B-only CE observations — PRICE-ONLY, NOT trades

For the **496 B-only source CE overlaps** (NOT 496 trades or 'recovered fills'), the later within-window M1 price evidence was:

| First subsequent source-only price observation | Count |
|---|---:|
| Mid-price wick touched the *experimental protected stop* before target in a later M1 | **340** |
| Mid-price wick reached selected native DOL target before protected stop in a later M1 | **32** |
| Neither stop nor target proven in remaining original hour | **124** |
| **Total B-only clean CE** | **496** |

**All B clean CE overlaps** (including A-and-B common 293): later OHLC **519** stop-level first, **54** target-level first, **216** unresolved at source-window end. These numbers are **conditional path observations** using synthetic theoretical levels, not broker matching and not actual trading win rate. A limit fill may never have happened on BID/ASK; a stop/target could both trade inside an earlier M1 in an unknown order. The source interval ends at the original Silver Bullet hour, but positions could legitimately remain managed later: unobserved outcomes are NOT losses.

**Risk-relevant insight:** A +22.80pp improvement in opportunity volume does NOT establish financial edge, and the many post-CE stop-price touches give *no basis* to claim the relaxed B rule is superior. The preregistered unknown-rate gate already FAILED, preventing cherry-picked promotion.

## Source fidelity vs measured behavior — separate conclusions

| Source-fidelity / methodology | Empirical finding from 3Y OHLC |
|---|---|
| ICT time-window + M1 FVG retracement concepts are source-consistent; this is not an ICT certification of QORE's exact 3-M1 protected swing or CE-only formalization | 2,140 identical source FVGs; B has 789 clean price-only CE overlaps vs A 301 |
| Opposite MSS must satisfy native M1 displacement and actual swing break; B's first opposite FVG may close in same or later M1 but MUST remain within original window, not arbitrary later-day FVG | 684 opposite MSS+first FVG timestamps, 562 explicitly after MSS on a later M1; same window all |
| A 3-M1 opposing pivot is an **algorithmic hypothesis**, not an ICT-specified universal stop | 51 B candidates have stop-side geometry invalid; counted as unknown |
| `TARGET_BEFORE_CE` is not a structural stop/loss, same-bar CE+event is UNKNOWN | B: 111 no-entry target completions and 619 same-M1 chronological ambiguities |
| No actual broker quote/tick or ACK was in 3Y consumed M1 source | **0** verified executions; cannot calculate genuine PF, drawdown, Sharpe, Sortino, net win rate or lot/risk |

## Decision, governance and next scientific work

1. **B source primary precommitted criterion FAILED**, even though the +5pp effect clause passed: ~31% unknown vs max 10%. Do NOT alter the 10% threshold after seeing results, add branches, tune pivot or reclassify unknown as invalid.
2. Architect OPS to peer-review paired `paired_candidate_records[]` and original 2023 ICT protected-swing / FVG structural invalidation definitions before changing **any native policy**. Reassess event precedence (why 0 first-terminal protected breaches) as forensic quality control, not strategy optimization.
3. Obtain **historical timestamped BID/ASK quote ticks and actual broker order/ACK history**, NAS100↔NDX100 specification/contract/point value, spread/fees and execution timing. Without that the first true economic endpoint cannot be evaluated. Historical 0.01-lot screenshot is not a backfilled 3Y quote stream.
4. Future real quote-based *predeclared* economic gate: B net PF at least 95% of A, absolute chronological DD no worse than A, positive net expectancy, and independent window stability. Fresh Holdout remains SEALED. Run full causal quote-order stop/target trade lifecycle and counterfactual only after true historical data is present, not paper fantasy.
5. EXACTLY ONE `VT31`, two internal models London/NY, M1 actual FVG/MSS source. No old VT31 algorithm, no live/VPS or financial authority, no CIBO/QDLE exposure, no certification.

**Authoritative artifacts:** [CI 38040127136](https://github.com/mezas3238-hue/qore-core/actions/runs/38040127136) / artifact **11664804507**, frozen source SHA and full 2,140 paired records. Preregistration commit [d4db56fb4](https://github.com/mezas3238-hue/qore-core/commit/d4db56fb45228d74a065349a97e562f2fbc6f657) predates CI tested run `f794f509c12ad886def540b73bbc8a3e238214a4`. **Not realized trades, no PF.**
