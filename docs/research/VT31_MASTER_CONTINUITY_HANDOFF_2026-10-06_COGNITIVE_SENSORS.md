# QORE CORE — VT31 NAS100 MASTER CONTINUITY HANDOFF

## COGNITIVE SENSOR DIAGNOSTICS → PLUMBING REPAIR → TRUTHFUL REPLAY → CERTIFICATION

**Owner / CEO:** Sergio Meza  
**Repository source of truth:** `mezas3238-hue/qore-core`  
**Working branch:** `agent/vt31-edge-position-cert-b-001`  
**Source snapshot before this handoff:** `50c87d51f8fbe14845b419bed9846b77fc81552b`  
**Snapshot message:** `ci(vt31): verify prior-history H4 context`  
**Fresh Holdout:** SEALED  
**VT31 certification state:** **NOT CERTIFIED**  
**LIVE / real-capital / production authority:** **NOT AUTHORIZED**

---

# 0. SOVEREIGN CONTINUITY DIRECTIVE

The next architect must continue from this handoff and the current branch state.

Do not restart the investigation from old summaries.

The immediate mission is:

> **MAKE VT31'S FULL COGNITION TRUTHFULLY OBSERVABLE AND FULLY ACTUATED, REPAIR THE SENSOR-PROVEN BLOCKERS, THEN REPLAY THE TRUTHFUL SYSTEM AND ONLY AFTER THAT RESUME EDGE RESEARCH.**

VT31 must use the maximum applicable intelligence available to it.

Certification is **PURE EDGE**.

It is prohibited to manufacture, improve or rescue certification with:

- position sizing;
- dynamic sizing;
- leverage;
- compounding;
- portfolio weighting;
- capital allocation;
- reduced monetary exposure;
- equity-dependent rescue;
- CIBO capital rescue;
- volume engineering.

Strategy-native R remains valid trader logic. Stops, trailing, break-even,
market-native exits, target extension and post-entry management may be used if
they are methodology-native and causally justified.

Observed maximum drawdown **<=6R is a HARD certification gate**.

Fresh Holdout stays sealed until every consumed/development gate, runtime/replay
parity gate, semantic audit and no-leakage gate passes.

---

# 1. WHY COGNITIVE SENSORS WERE INSTALLED

The economic work had reached a point where additional rules were not enough.

Comparator 009 had strong per-fold economics but failed the true continuous
path:

- stitched observed DD: approximately **10.149655R**;
- annualized Sharpe under the frozen eligible-session convention:
  approximately **1.276669**.

Comparator 010 live-context adverse exits were then tested in GitHub Trader
Lab.

Run:

`37533950795` — SUCCESS

The strongest variant only moved:

- stitched DD from ~10.1497R to ~9.8702R;
- Sharpe from ~1.27667 to ~1.27990.

It did not solve the certification blockers.

A rejected-structural-positive-edge audit also completed:

`37531798572` — SUCCESS

It found no robust cross-partition pool of rejected structural setups that
could simply be reopened to solve Sharpe.

The evidence therefore required a different question:

> Is the cognitive system receiving the right inputs, using them, emitting the
> right output and actually delivering that output to execution?

That led to the read-only cognitive sensor program.

---

# 2. SENSOR ARCHITECTURE INSTALLED

Canonical telemetry module:

`src/qore/infrastructure/traders/vt31_nas100_cognitive_telemetry.py`

Cross-fold audit:

`scripts/vt31_nas100_cognitive_sensor_audit_v1.py`

GitHub Trader Lab workflow:

`.github/workflows/vt31-cognitive-sensor-audit-v1.yml`

Parallel sensor directive:

`docs/research/VT31_COGNITIVE_SENSOR_PARALLEL_DIRECTIVE_001.md`

The observed chain is:

`INPUT -> COGNITION -> REASONING -> POSITION OUTPUT -> ACTUATION`

All sensors are read-only.

They have:

- no policy authority;
- no sizing authority;
- no terminal-outcome authority;
- no permission to modify admission, stop, target, leverage, size or capital.

## 2.1 INPUT SENSOR

Captures the complete causal post-entry observation and MarketFacts snapshot.

It detects:

- missing fields;
- UNWIRED;
- UNAVAILABLE;
- UNKNOWN;
- UNRESOLVED;
- UNCALIBRATED;
- NOT_EVALUATED.

It fingerprints:

- entry Situation;
- current Situation;
- current reasoning Situation.

Important observed inputs include:

- prior day;
- H4;
- H1;
- M15;
- premarket;
- cash open;
- prior-range location;
- range / volatility;
- raid depth;
- recent efficiency;
- overlap;
- reclaim age;
- last structure event;
- recent 10-minute liquidity count;
- displacement;
- DOL states;
- extension capacity;
- exhaustion;
- cross-index context;
- current_open_r;
- structural market facts.

## 2.2 COGNITION SENSOR

Captures:

- observed cognitive domains;
- actuated Situation fields;
- observation-only Situation fields;
- cognitive coverage ratio;
- full cognitive accounting status;
- maximum cognition status;
- maximum-intelligence blockers.

This sensor is what exposed that the old system could claim
`maximum_cognition_verified=true` even when declared H4 intelligence was
unavailable.

## 2.3 REASONING SENSOR

Captures:

- frozen entry reasoning action;
- current post-entry reasoning action;
- current reasoning fingerprint.

This makes it possible to distinguish:

- intelligence input unavailable;
- reasoning did not react;
- reasoning reacted but PositionAction did not;
- PositionAction reacted but actuation failed.

## 2.4 POSITION OUTPUT SENSOR

Captures the canonical full PositionAction:

- HOLD;
- TRAIL;
- EXTEND;
- EXIT;

plus:

- output reason;
- next stop;
- next target;
- whether the output requires actuation.

The action vocabulary also allows detection of other routed actions where
present, such as DOL_LOCK, BANK or REARM_REQUIRED.

## 2.5 ACTUATION SENSOR

Classifies the relationship between the canonical cognitive output and the
actual route.

Statuses:

1. `ALIGNED_NO_ACTION`
2. `OUTPUT_NOT_ROUTED`
3. `ROUTED_EXECUTION_UNOBSERVED`
4. `ROUTED_NOT_EXECUTED`
5. `ROUTED_AND_EXECUTED`
6. `UNEXPECTED_ROUTE_WHILE_HOLDING`

This sensor is critical because a correct cognitive decision is useless if the
action disappears between the brain and the simulator/runtime.

---

# 3. FIRST SENSOR AUDIT — PROBLEMS PROVEN

Initial audit findings were frozen in:

`docs/research/VT31_ARCH2_COGNITIVE_SENSOR_AUDIT_FINDINGS_001.md`

Initial sensor workflow:

`37543170256` — SUCCESS

Initial sensor head:

`9b97af8e22fcab45c1c3a9e5d4d8da870a608d4e`

Population:

- Comparator-009 trades: 109;
- cognitive calls: 3,279;
- average calls/trade: ~30.08;
- missing sensor calls: 0.

## 3.1 DEFECT — FALSELY GREEN MAXIMUM COGNITION

Initial sensor observation:

- H4 unresolved/unavailable: **1,142 calls**;
- affected trades: **23**;
- yet maximum cognition was reported green.

The reasoning engine declared H4 as a cognitive domain, but H4 unavailable was
not being promoted to a maximum-intelligence blocker.

This was a certification-integrity defect.

## 3.2 DEFECT — 10-MINUTE LIQUIDITY INPUT COMPLETELY UNWIRED

Initial observation:

`recent_liquidity_event_count_10m = None`

on all **3,279 calls**.

The repository already had the causal structure-event stream needed to
construct it.

This was a plumbing defect, not a data-source limitation.

## 3.3 DEFECT — CANONICAL POSITIONACTION SPLIT FROM ECONOMIC EXIT ROUTE

Initial canonical output:

- HOLD: 3,279;
- TRAIL: 0;
- EXTEND: 0;
- EXIT: 0.

But the frozen Comparator-003/009 sidecar pretarget logic routed EXIT on
**28 calls**.

Initial actuation mismatch:

- HOLD -> ALIGNED_NO_ACTION: 3,251;
- HOLD -> UNEXPECTED_ROUTE_WHILE_HOLDING: 28.

Therefore the validated economic exit and the canonical full-cognition
PositionAction were semantically split.

## 3.4 DEFECT — ZERO-CALL STRUCTURAL INVALIDATIONS

Initial audit found 17 trades with zero post-entry cognitive calls.

All were structural-invalidating raw -1R losses.

They could not be repaired by a rule that requires a fully closed post-entry M1
because no such decision point exists early enough.

This proved a separate **fill / order-lifecycle / observability problem**.

## 3.5 DEFECT — MARKET-NATIVE FAILURE FACTS WERE NOT CONSTRUCTED

The live research adapter supplied:

- `structure_invalidated=False`;
- `liquidity_failure_confirmed=False`;
- `regime_changed_against_thesis=False`.

The runtime interface supports these facts, but replay did not causally
construct them.

---

# 4. REPAIRS ALREADY IMPLEMENTED AFTER THE FIRST SENSOR AUDIT

Do not repeat these from scratch.

## 4.1 H4 NOW BLOCKS MAXIMUM COGNITION WHEN TRULY UNAVAILABLE

Key commit:

`bbe5c50c07727cce5233ce3045f88876ed043434`

Message:

`fix(vt31): block maximum cognition when H4 is unavailable`

Tests were added to lock this behavior.

A truthful missing H4 context must now surface:

`H4_CONTEXT_UNAVAILABLE`

instead of remaining falsely green.

## 4.2 COMPARATOR-009 ADVERSE EXITS WERE CANONICALIZED INTO POSITIONACTION

Predeclared gate:

`docs/research/VT31_ARCH2_COMP009_CANONICAL_POSITION_ACTION_PARITY_GATE_001.md`

Key commits:

- `6a94e7feb97e59f7d7d63d056ce54cfd59f1b08f`
  — canonicalize validated adverse exits;
- `48a7e3eece4729c027c693f1d0393418301607b6`
  — lock parity in tests;
- `003426ddac2da0a2ec2dbde46f557559312ac80a`
  — CI verification.

The runtime now mirrors only the already-validated Comparator-009 adverse exit
semantics into the canonical PositionAction.

No new economic threshold was introduced.

## 4.3 CAUSAL 10-MINUTE LIQUIDITY COUNT WAS WIRED

Canonical helper:

`src/qore/infrastructure/traders/vt31_nas100_cognitive_plumbing.py`

It counts only causal closed-M1:

- reference-liquidity-sweep;
- local-liquidity-sweep;

inside the existing trailing 10-minute semantic window.

Relevant commits include:

- `a2b28c8c1d672d6824e6f2ee834a0ca2948aa642`
- `0af319b302b7721dd082d857dc7a784677514cf6`
- `cff9ffbcd0159581bfdc3d0cca67ee009de3c6f3`
- `f66142349b5882b90a0abbdac93febc73c42ca9d`
- `d80c02b8aa5028e7022561afd78bd96756e9fa09`

The count was also persisted/reconstructed through the causal snapshot path.

## 4.4 H4 CARRY-FORWARD WAS REPAIRED

Predeclared gate:

`docs/research/VT31_ARCH2_CAUSAL_H4_CARRY_FORWARD_PLUMBING_GATE_001.md`

Relevant commits:

- `4d1fde77c10880532304cffff6123a7316119d9a`
  — carry forward last causal H4 context;
- `b3bd507e016e9a2922b2b0802c735cb7a153d5da`
  — source H4 from prior causal history;
- `5b54ae39de2dfde2521c9d31cf4fdf7e97cc6fa4`
  — tests;
- `50c87d51f8fbe14845b419bed9846b77fc81552b`
  — CI verification.

Semantics:

- use newest fully closed current H4 state if available;
- otherwise carry forward the valid frozen entry H4;
- entry H4 may use causal prior admitted-day history plus current-day closed
  bars;
- no future H4 and no partial H4;
- no synthetic imputation.

This repair materially changed the truthful causal replay population and must
not be reverted merely to recover old economics.

---

# 5. LATEST SENSOR AUDIT AFTER REPAIRS

Latest sensor workflow:

`37545857624` — **SUCCESS**

Latest sensor head:

`50c87d51f8fbe14845b419bed9846b77fc81552b`

Artifacts include:

- aggregate cognitive sensor audit;
- prepared sensor ledgers for R5, R6, R8 and recent consumed.

Current cross-fold sensor state:

- total trades: **109**;
- cognitive calls: **3,051**;
- average calls/trade: **27.9908256881**;
- minimum calls/trade: 0;
- maximum calls/trade: 239;
- missing sensor calls: **0**.

Calls by fold:

- R5: 1,305;
- R6: 657;
- R8: 581;
- recent consumed: 508.

## 5.1 H4 IS MOSTLY REPAIRED, BUT NOT FULLY

Current:

- full cognitive accounting verified: 3,051 / 3,051;
- maximum cognition verified: 3,047 / 3,051;
- H4_CONTEXT_UNAVAILABLE blockers: **4 calls**.

The four unresolved calls belong to two R8 Breaker SHORT losses:

- 2017-10-06 signal; unresolved post-entry observations at 14:26/14:27 UTC;
- 2017-10-11 signal; unresolved post-entry observations at 14:25/14:26 UTC.

Do not synthesize H4 merely to turn these green.

Determine whether valid earlier causal H4 history truly exists. If not,
fail-closed unavailability is correct.

## 5.2 LIQUIDITY SENSOR IS NOW ACTUALLY WIRED

The current audit no longer reports
`recent_liquidity_event_count_10m` as missing.

Observed count values span 0 through 10 across the 3,051 calls.

Therefore the earlier total-unwired liquidity defect has been repaired.

## 5.3 CANONICAL OUTPUT NOW EMITS EXIT

Current canonical PositionAction counts:

- HOLD: **3,026**;
- EXIT: **25**;
- TRAIL: 0 in this sensor path;
- EXTEND: 0 in this sensor path.

Output reasons:

- MARKET_STRUCTURE_REMAINS_VALID: 3,026;
- VALIDATED_ADVERSE_CONTEXT_EXIT: 25.

This is major progress versus the initial all-HOLD state.

## 5.4 ACTUATION IS STILL NOT FULLY OBSERVED

Current actuation status:

- HOLD -> ALIGNED_NO_ACTION: **3,026**;
- EXIT -> ROUTED_EXECUTION_UNOBSERVED: **25**.

There are no longer 28 HOLD-vs-sidecar mismatches.

However, the sensor still cannot prove that the 25 canonical EXIT outputs were
actually executed at the next valid M1 open.

This is an OPEN BLOCKER.

The next architect must wire the execution observer so the expected end state
becomes:

`EXIT -> ROUTED_AND_EXECUTED`

or a truthful failure such as:

`EXIT -> ROUTED_NOT_EXECUTED`.

## 5.5 MARKET-NATIVE FACTS ARE STILL EFFECTIVELY DEAD IN THE SENSOR PATH

Across all 3,051 latest calls the sensor sees:

- structure_invalidated: false on 3,051;
- liquidity_failure_confirmed: false on 3,051;
- regime_changed_against_thesis: false on 3,051.

Momentum deterioration is present, but the other three runtime-supported
market-native failure facts are still not causally reconstructed in this
research path.

This is an OPEN BLOCKER.

## 5.6 NEXT STRUCTURAL TARGET IS MISSING ON THE SENSOR PATH

Current input audit reports:

`market.next_structural_target` missing on 3,051 calls.

This may be expected for some pretarget paths, but before certification the
next architect must prove whether this is intentionally non-applicable or an
EXTEND-path plumbing gap.

Do not silently mark it resolved.

## 5.7 ZERO-CALL CLASS IS NOW 18 TRADES

Latest prepared ledgers contain **18** zero-call trades.

All 18 are:

- raw -1R;
- structural-invalidation exits.

Composition:

- Breaker: 17;
- Fair Value Gap: 1.

One remains the stitched-DD trough:

- 2023-05-01 Breaker LONG.

This class cannot be solved by later post-entry cognition because there is no
closed post-entry M1 observation early enough.

---

# 6. CRITICAL ECONOMIC CONSEQUENCE OF TRUTHFUL H4 REPAIR

This is the most important continuity point.

The old frozen Comparator-009 numbers must no longer be assumed to describe the
current truthful causal implementation.

Before the H4 source-completeness repair, Comparator 009 had approximately:

- R5: 34 trades, DD 5.0099R;
- R6: 23 trades, DD 5.3944R;
- R8: 21 trades, DD 5.0661R;
- recent: 31 trades, DD 5.1398R;
- stitched DD: 10.149655R;
- frozen annualized Sharpe: 1.276669.

After the H4 causal-history repair, the latest sensor ledgers at
`50c87d51...` contain:

### R5

- trades: 34;
- PF: **4.8979153506**;
- mean: **+2.1978178576R/trade**;
- observed DD: **5.0099030948R** — PASS.

### R6

- trades: 24;
- PF: **4.9011178213**;
- mean: **+2.5618766207R/trade**;
- observed DD: **5.3944444444R** — PASS.

### R8

- trades: 19;
- PF: **5.6798654039**;
- mean: **+2.7549187358R/trade**;
- observed DD: **5.8733333333R** — PASS, close to the 6R hard limit.

### Recent consumed

- trades: 32;
- PF: **2.3728346230**;
- mean: **+0.8888225510R/trade**;
- observed DD: **6.1897523703R** — **FAIL**.

### Chronologically stitched path

Using the same frozen 0.05R/trade baseline friction and the same eligible
NY-session daily-R convention:

- trades: 109;
- combined PF: **4.2467823755**;
- combined mean: **+1.9907947126R/trade**;
- stitched observed DD: **11.1996554651R** — **FAIL**;
- DD peak trade: 2022-02-08;
- DD trough trade: 2023-05-01;
- eligible sessions: 2,023;
- no-trade eligible sessions: 1,914;
- annualized Sharpe: **~1.2169280970** — **FAIL**;
- annualized Sortino: **~9.5615204049** — PASS;
- payoff ratio: **~9.3679022988** — strong.

These numbers were reconstructed from the latest
`37545857624` prepared sensor ledgers under the frozen metric conventions.

They must be re-confirmed by the formal scientific replay battery after the
remaining sensor/actuation repairs.

**Do not try to restore the old Comparator-009 numbers by disabling truthful H4
context.**

The current problem is harder but more real.

---

# 7. ZERO-CALL RESEARCH ALREADY CLOSED OR PREDECLARED

## 7.1 BROAD H4/H1 VETO WAS REJECTED

Pairwise zero-call study:

`docs/research/VT31_ARCH2_ZERO_CALL_STRUCTURAL_INVALIDATION_PAIRWISE_FINDINGS_001.md`

An absolute:

`H4 bearish + H1 bearish`

conjunction had six losses / zero winners in the observed sample, but it mixed
LONG conflict with SHORT alignment.

It was correctly **not promoted**.

## 7.2 SIDE-RELATIVE HTF VETO WAS ALSO REJECTED

Findings:

`docs/research/VT31_ARCH2_SIDE_RELATIVE_HTF_ALIGNMENT_AUDIT_FINDINGS_001.md`

The BOTH_AGAINST state still contained positive aggregate edge and a real
winner.

Conclusion:

Do not attack the zero-call class with a broad HTF directional veto.

## 7.3 FILL-TIME THESIS REVALIDATION IS PREDECLARED AND STILL PENDING

Gate:

`docs/research/VT31_ARCH2_CAUSAL_FILL_TIME_THESIS_REVALIDATION_GATE_001.md`

Observation:

the zero-call losses terminate by structural invalidation one M1 after actual
fill, before post-entry cognition has a usable closed M1 decision point.

The predeclared solution to test is:

> Immediately before accepting a prospective fill, rebuild the current causal
> Situation as of the fill opportunity and revalidate the frozen entry thesis
> with maximum entry/fill intelligence.

No arbitrary N-minute timer is allowed.

The rule must use only bars closed by the fill opportunity.

This is a P0 economic research task after plumbing truth is stable.

---

# 8. COMPARATOR 012 IS PREDECLARED BUT NOT YET A SURVIVOR

Gate:

`docs/research/VT31_ARCH2_COMP012_STALE_ENTRY_ZONE_FAILURE_GATE_001.md`

Observation-only discovery:

`closed_through_entry_zone_against_thesis && reclaim_bucket=STALE_8_14M`

was observed across all four consumed partitions with:

- 10 eventual losses;
- 0 eventual winners.

The thresholds are pre-existing; no new numeric boundary was invented.

However it is only a predeclared hypothesis.

It must be replayed unchanged across the truthful R5/R6/R8/recent baseline and
must pass the stitched DD + Sharpe gates.

Do not promote it from the observation alone.

---

# 9. DIRECTIVE FOR THE PARALLEL / OTHER ARCHITECT

The owner explicitly authorizes the other architect to install complementary
sensors.

Existing directive:

`docs/research/VT31_COGNITIVE_SENSOR_PARALLEL_DIRECTIVE_001.md`

The other architect should focus on:

- producer sensor for `structure_invalidated`;
- producer sensor for `liquidity_failure_confirmed`;
- producer sensor for `regime_changed_against_thesis`;
- exact causal timestamp when each fact becomes observable;
- producer call count;
- consumer call count;
- value entering PostEntryMarketFacts;
- resulting canonical PositionAction;
- route to next valid M1 actuator;
- actual execution acknowledgement.

The other architect **must reuse**
`vt31_nas100_cognitive_telemetry.py`.

Do not create a second decision engine.

Do not duplicate the canonical reasoning/PositionAction stack.

Both architects may inspect terminal outcome after the trade for attribution,
but outcome/date/fold may never become runtime authority.

---

# 10. P0 — URGENT WORK FOR THE NEXT ARCHITECT

Execute in this order.

## P0.1 FREEZE THE TRUTHFUL POST-PLUMBING BASELINE

The old Comparator-009 economic identity is no longer sufficient because the
H4 causal source repair changed the replay population/path.

Create an explicit truthful-baseline record at the current causal semantics.

Required:

- exact branch SHA;
- exact admitted identities by fold;
- exact terminal R rows;
- H4 source provenance;
- liquidity snapshot provenance;
- canonical PositionAction semantics;
- sensor version/fingerprint.

Then run the full consumed scientific battery.

Do not open Fresh Holdout.

## P0.2 CLOSE EXIT EXECUTION OBSERVABILITY

Current problem:

25 canonical EXIT outputs are:

`ROUTED_EXECUTION_UNOBSERVED`.

Repair the replay actuator telemetry so every routed action records:

- decision observation timestamp;
- expected next valid M1 open;
- route accepted/rejected;
- execution timestamp;
- execution price;
- actual action executed.

The cognitive audit must finish with either:

- ROUTED_AND_EXECUTED; or
- a truthful actionable failure.

No EXIT may remain execution-unobserved before certification.

## P0.3 CONSTRUCT THE THREE MISSING MARKET-NATIVE FACTS

Causally construct and sensor:

1. `structure_invalidated`;
2. `liquidity_failure_confirmed`;
3. `regime_changed_against_thesis`.

Constraints:

- closed data only;
- no terminal label;
- no future bar;
- no same-bar close used to execute at that same bar open;
- no date/fold lookup;
- no threshold mined only from known losers.

Then route the complete PositionAction result, not a sidecar boolean.

## P0.4 ADJUDICATE THE FOUR REMAINING H4-UNAVAILABLE CALLS

The two affected R8 trades are:

- 2017-10-06 Breaker SHORT;
- 2017-10-11 Breaker SHORT.

Determine whether earlier valid causal H4 history exists.

If yes, wire it.

If no, preserve fail-closed H4 unavailable.

Never fabricate a state merely to recover a trade.

## P0.5 IMPLEMENT FILL-TIME THESIS REVALIDATION

Use the already-predeclared gate.

Test at least:

- CONTROL;
- FILL_REVALIDATE_REASONING.

At fill opportunity T:

- only data closed <=T;
- frozen source/setup/family/thesis retained;
- current Situation rebuilt;
- current reasoning must remain EXECUTE;
- entry/fill-relevant maximum-intelligence blockers must be absent.

Report:

- accepted/rejected fills;
- rejected winners;
- rejected losses;
- zero-call structural losses removed/preserved;
- density;
- winner count/R preservation;
- PF;
- expectancy;
- fold DD;
- stitched DD;
- frozen Sharpe/Sortino.

## P0.6 RE-RUN THE COGNITIVE SENSOR AUDIT AFTER REPAIRS

Required assertions:

- missing sensor calls = 0;
- truthful H4 blockers only;
- liquidity field populated;
- no canonical action / route contradiction;
- no required action left execution-unobserved;
- producer/consumer counters for the three market-native failure facts;
- maximum cognition does not go green with declared mandatory inputs missing.

## P0.7 IMMEDIATELY RE-RUN A FULL ECONOMIC REPLAY

After P0.1-P0.6, run the same unchanged truthful system across:

- R5;
- R6;
- R8;
- recent consumed;
- chronological stitched aggregate.

Use GitHub Trader Lab as the research bank.

For repeated hypothesis work, prefer the prepared-ledger/hot-cache path rather
than rebuilding M1 every iteration.

A formal replay must report at minimum:

- trade identity/density;
- PF;
- expectancy;
- payoff;
- observed DD per fold;
- stitched DD;
- Sharpe;
- Sortino;
- Monte Carlo positive probability;
- MC p95 DD;
- half-year/era stability;
- degraded-cost PF;
- winner count/R preservation;
- cognition/actuation sensor diagnostics.

---

# 11. TRADER LAB CONTINUITY

An independent GitHub Trader Lab exists on:

`agent/github-trader-lab-001`

Its prepared-ledger hot path has previously measured roughly **3.2 seconds of
hot compute** for cached VT31-style multi-fold scientific work.

A VT31 ultrafast workflow was also repaired in this branch:

`.github/workflows/vt31-github-trader-lab-comp010-v1.yml`

Successful run:

`37533950795`

Its first execution was cold and rebuilt causal ledgers, so it was not yet the
desired hot-cache iteration path.

The next architect should not return to slow sovereign workflows for every
research idea.

Use:

- immutable evidence;
- prepared causal ledgers;
- cached upstream reconstruction;
- fast downstream candidate evaluation;
- stitched adjudication.

The sovereign workflow is for formal confirmation after a candidate survives,
not for every exploratory replay.

---

# 12. REMAINING ECONOMIC BLOCKERS

At the latest truthful causal snapshot, VT31 is not closeable for certification
because:

1. recent consumed observed DD is approximately **6.18975R >6R**;
2. stitched observed DD is approximately **11.19966R >6R**;
3. annualized Sharpe is approximately **1.21693 <1.50**.

Strong metrics such as combined PF, Sortino and payoff do not override these
hard failures.

Do not optimize already-strong metrics for their own sake.

The work must reduce genuine loss mass / improve genuine opportunity quality
without destroying winner tail or using capital engineering.

---

# 13. CERTIFICATION GATES STILL REQUIRED

Before Fresh Holdout can open, the unchanged final candidate must satisfy:

## Edge / risk

- each consumed era/fold PF >=1.50;
- combined PF >=1.70;
- expectancy >0;
- operational expectancy target >=+0.15R/trade;
- payoff >=1.20, preferred >=1.50;
- each observed partition DD <=6R;
- **stitched continuous observed DD <=6R**;
- no severe clustering;
- temporal/year/era/regime robustness;
- degraded 0.10R all-in friction PF >1.

## Risk-adjusted

Frozen eligible-session convention:

- one R observation per eligible NY session;
- eligible no-trade session = 0R;
- rf = 0;
- Sharpe uses sample standard deviation N-1;
- annualization sqrt(252);
- Sortino MAR = 0;
- downside denominator over all eligible sessions.

Gates:

- annualized Sharpe >=1.50;
- annualized Sortino >=2.00.

## Monte Carlo

- positive terminal probability >=90%, preferred >=95%;
- p95 max DD <=~15R robustness gate.

## Winner preservation

- winner count preservation >=80%;
- winner-R preservation >=90%.

## Cognition / architecture

- maximum applicable cognition used;
- no mandatory intelligence falsely green when unavailable;
- causal M15/H1/H4/structure/liquidity/regime/volatility inputs;
- canonical reasoning and PositionAction;
- complete routing and execution observability;
- research/runtime decision parity;
- no sidecar economic decision that bypasses canonical cognition.

## Semantic integrity

Still required before final freeze:

- audit categorical parsing in
  `vt31_nas100_position_intelligence.py`;
- eliminate any unsafe substring-state collisions if found;
- audit reasoning categorical/startswith semantics;
- prove exact-state behavior where economically meaningful.

## No leakage

Must prove:

- no future bars;
- no terminal PnL authority;
- no date identity;
- no fold identity;
- no hidden holdout access;
- next-open execution after closed-bar decisions.

---

# 14. FINAL PRE-HOLDOUT FREEZE STILL REQUIRED

Even after economics pass, do not immediately open Fresh Holdout.

First freeze:

- final candidate ID;
- exact code SHA;
- exact config;
- memory fingerprints;
- runtime/replay parity evidence;
- semantic parser audit;
- no-leakage audit;
- scientific battery artifacts;
- cognition sensor report;
- actuation sensor report;
- consumed evidence hashes.

Only then may Fresh Holdout be consumed exactly once.

A Fresh Holdout failure consumes that holdout and requires new independent
holdout evidence after further research.

---

# 15. RESEARCH THAT MUST NOT BE REPEATED

Do not repeat these as though they were unexplored:

- broad H4/H1 directional veto;
- side-relative HTF veto;
- Comparator-010 neutral-destination no-op;
- Comparator-011 old deep-giveback transfer;
- blind earlier fixed adverse-R exits;
- broad reopening of rejected structural setups;
- sizing/leverage rescue;
- arbitrary fill-delay timer;
- DGR threshold mining against known losers.

These avenues were rejected or shown insufficient.

---

# 16. CURRENT SOURCE-OF-TRUTH FILES

Important continuity files:

- `docs/research/VT31_ARCH2_COGNITIVE_SENSOR_AUDIT_FINDINGS_001.md`
- `docs/research/VT31_COGNITIVE_SENSOR_PARALLEL_DIRECTIVE_001.md`
- `docs/research/VT31_ARCH2_COGNITIVE_PLUMBING_REPAIR_GATE_001.md`
- `docs/research/VT31_ARCH2_COMP009_CANONICAL_POSITION_ACTION_PARITY_GATE_001.md`
- `docs/research/VT31_ARCH2_CAUSAL_H4_CARRY_FORWARD_PLUMBING_GATE_001.md`
- `docs/research/VT31_ARCH2_CAUSAL_FILL_TIME_THESIS_REVALIDATION_GATE_001.md`
- `docs/research/VT31_ARCH2_ZERO_CALL_STRUCTURAL_INVALIDATION_PAIRWISE_FINDINGS_001.md`
- `docs/research/VT31_ARCH2_SIDE_RELATIVE_HTF_ALIGNMENT_AUDIT_FINDINGS_001.md`
- `docs/research/VT31_ARCH2_COMP012_STALE_ENTRY_ZONE_FAILURE_GATE_001.md`
- `src/qore/infrastructure/traders/vt31_nas100_cognitive_telemetry.py`
- `src/qore/infrastructure/traders/vt31_nas100_cognitive_plumbing.py`
- `src/qore/infrastructure/traders/vt31_nas100_post_entry_cognitive_runtime.py`
- `scripts/vt31_nas100_cognitive_sensor_audit_v1.py`
- `.github/workflows/vt31-cognitive-sensor-audit-v1.yml`

---

# 17. FIRST COMMANDMENT FOR THE NEXT ARCHITECT

Do not ask:

> "How do I get the old Comparator-009 metrics back?"

Ask:

> "What does the fully wired, causally truthful, maximum-intelligence VT31
> actually do, where does its decision get blocked, and what pure-edge mechanism
> fixes the remaining loss mass while preserving winners?"

The sensor program exists specifically to answer that question.

Repair the wiring first.

Replay immediately after repair.

Then continue edge research only from the truthful baseline.

**VT31 remains NOT CERTIFIED. Fresh Holdout remains SEALED.**
