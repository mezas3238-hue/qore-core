# Deterministic Trading Signal Methodologies — Trend / Mean Reversion / Breakout

Demo/research scope. Each methodology is a **deterministic experimental hypothesis**, not an
execution order, not Risk authorization, and never profitable by assertion. All three share one
computation boundary shape (`ResearchDecisionEvaluatorProtocol`) and one signal model (§3).

## Shared notation and arithmetic contract

- Bars arrive in **canonical chronological order** and each bar is appended **exactly once**. The
  producer never re-sorts, re-orders, deduplicates, or buffers across `available_at`; it trusts the
  upstream observation contract. Let the arrival-ordered closed bars be `b_0, b_1, …, b_k`, where
  `b_k` is the newest ("current") bar decided at evaluation step `k`. For bar `b_i`:
  `close_i`, `high_i`, `low_i` are positive finite floats; `closed_at_i ≤ available_at_i ≤ simulated_now`.
- **Exact arithmetic.** Every market float `f` is converted exactly once as `Decimal(str(f))`. Config
  thresholds are already exact `Decimal`. Every derived quantity is `Decimal`. **No decision predicate
  uses division or float epsilon.** All predicates are reduced to exact cross-multiplied forms over
  finite `Decimal` values and exact `int` lookbacks, so `Decimal` context rounding is never observable
  in a decision. Non-finite results are impossible (positive finite inputs, positive integer divisors,
  positive denominators); any unexpected non-finite fails closed (raise; emit nothing).
- **Tie rule (global).** Every directional predicate is a **strict** inequality. Equality at any
  boundary resolves to `ABSTAIN`. Nothing depends on input order or epsilon.
- **Bounded state.** The retained window is a fixed-size immutable `tuple` (length `0..N` for the
  largest lookback). Append pushes one element; if length would exceed the cap, the oldest (index 0)
  is evicted. Evaluation arithmetic is `O(N)` with `N` a config-fixed constant. No unbounded
  accumulation.

## §1 Chosen rule set

### 1.1 Trend / Momentum — family `qore.trader.trend`, kind `virtual-trader.trend-momentum`

**1. Configuration** (carried as `strategy_binding.manifest.parameters`, each a
`ResearchStrategyParameter` whose `value` is `str | bool | int | Decimal`):

| field | type | validation |
|---|---|---|
| `short_lookback` | exact `int` (reject `bool`) | `1 <= short_lookback` |
| `long_lookback` | exact `int` (reject `bool`) | `1 <= long_lookback` and `long_lookback > short_lookback` |
| `min_strength` | `Decimal` | finite and `min_strength > 0` |

The evaluator re-validates these exact fields at construction (exact `type()` checks, not
`isinstance`), and fails closed on any missing, unknown, or invalid field. `min_strength ≥ 1` is
accepted (it simply makes BUY/SELL unreachable ⇒ permanent `ABSTAIN`); only non-finite/negative/zero
is rejected.

**2. Lookback.** `N = long_lookback` (denoted `L`; `S = short_lookback`). The current bar is
included in both summaries, so `L` closed bars suffice. Bars `0..N-1` (fewer than `L` bars): **no
decision is emitted** (empty `FunctionalDecision` tuple; fail closed). At exactly `N` bars
(`b_{L-1}`): first `BUY`/`SELL`/`ABSTAIN` is emitted.

**3. Predicate** (exact, division-free). Let `short_sum = Σ_{i=k-S+1}^{k} close_i`,
`long_sum = Σ_{i=k-L+1}^{k} close_i` (exact `Decimal` sums over the most recent `S`/`L` bars,
current included). Define the exact comparison quantities

```
lhs = short_sum * L − long_sum * S          # signed momentum × S·L
rhs = min_strength * long_sum * S           # ≥ 0 (long_sum > 0, S ≥ 1, min_strength > 0)
```

- `BUY`   iff `lhs > +rhs`
- `SELL`  iff `lhs < −rhs`
- `ABSTAIN` otherwise (i.e. `−rhs ≤ lhs ≤ +rhs`; equality at `±rhs` ⇒ `ABSTAIN`).

Intuitive (report-only) form: `momentum = (short_mean − long_mean) / long_mean`, BUY iff
`momentum > +min_strength`, SELL iff `momentum < −min_strength`. The predicate above is its exact
cross-multiplied equivalent.

**4. Reason codes and evidence.**

| code | side | meaning |
|---|---|---|
| `trend.buy` | `buy` | `lhs > +rhs` |
| `trend.sell` | `sell` | `lhs < −rhs` |
| `trend.abstain.insufficient-strength` | `abstain` | `−rhs ≤ lhs ≤ +rhs` |

Reason attributes (all canonical fixed-point strings `format(d.normalize(), "f")`):
`short_sum`, `long_sum`, `lhs`, `rhs`, `short_lookback`, `long_lookback`, `min_strength`,
`bars_used`.

**5. State transition.** `exact_content` is an immutable `TraderSignalStateContent` holding a bounded
`bars` → `tuple` of `(close, high, low)` floats (oldest first; length `0..L`), a timezone-aware
`last_closed_at` (`datetime | None`), and the exact `config_fingerprint`. Per evaluation: (a) append
the current bar, evicting the oldest if length > `L`; (b) compute the predicate over the updated
window; (c) emit the next state. A bar whose `closed_at` is not strictly greater than the retained
`last_closed_at` raises (chronology fail-closed). No future material is consulted: only bars already
present in the window (all with `available_at ≤ simulated_now`).

**6. Insufficient / flat / ambiguous.** Constant series ⇒ `short_sum/L == long_sum/L` ⇒
`lhs == 0`, `−rhs ≤ 0 ≤ +rhs` ⇒ `ABSTAIN`. Zero variance never produces a direction. Fewer than
`L` bars ⇒ no decision emitted. A valid window whose momentum lies inside the `±min_strength` band ⇒
`ABSTAIN`.

**7. No-lookahead.** The decision for `b_k` uses only `b_k` and earlier bars, all closed and visible
(`closed_at ≤ available_at ≤ simulated_now`). `min_strength` is config, not data. No future bar
enters the window, and no bar's value is used before it is appended.

**8. Tie handling.** Strict `>`/`<` only; `lhs == ±rhs` ⇒ `ABSTAIN`. Exact `Decimal` equality; no
epsilon.

**9. Bounded arithmetic.** Window ≤ `L` entries; each evaluation sums ≤ `L` `Decimal`s. No float
accumulation, no division in predicates, no non-finite path.

**10. Compatibility.** Reads only `OhlcSnapshot.close` (plus `instrument`, `closed_at` for identity/
ordering). Emits `BUY`/`SELL`/`ABSTAIN` via `metadata.attributes["side"]` + reason codes. Never uses
`datetime.now`, `uuid4`, RNG, sleeps, threads, global mutable state, provider IO, or execution
authority.

### 1.2 Mean Reversion — family `qore.trader.meanreversion`, kind `virtual-trader.mean-reversion`

**1. Configuration.**

| field | type | validation |
|---|---|---|
| `lookback` | exact `int` (reject `bool`) | `1 <= lookback` |
| `deviation_threshold` | `Decimal` | finite and `deviation_threshold > 0` |

`deviation_threshold ≥ 1` is accepted (BUY side becomes unreachable ⇒ that side permanently
`ABSTAIN`); non-finite/negative/zero rejected.

**2. Lookback.** `N = lookback + 1` (denoted `K = lookback`). The equilibrium needs `K` **prior**
closes plus the current close. Bars `0..N-1` (fewer than `K` prior bars): **no decision emitted**.
At exactly `N` bars (`b_K`, with prior `b_0..b_{K-1}`): first `BUY`/`SELL`/`ABSTAIN`.

**3. Predicate** (exact, division-free). Let `equil_sum = Σ_{i=k-K}^{k-1} close_i` (prior `K` bars,
current excluded). Exact comparison quantities:

```
BUY  iff  close_k * K  <  equil_sum * (1 − deviation_threshold)
SELL iff  close_k * K  >  equil_sum * (1 + deviation_threshold)
else ABSTAIN
```

Intuitive (report-only) form: `equilibrium = equil_sum / K`, `deviation = (close_k − equilibrium) /
equilibrium`; BUY iff `deviation < −deviation_threshold`, SELL iff `deviation > +deviation_threshold`.
Dispersion is **not used** in the minimal rule, so the "refuse zero/invalid dispersion" clause is
vacuously satisfied; zero-variance series is handled by §6.

**4. Reason codes and evidence.**

| code | side | meaning |
|---|---|---|
| `meanreversion.buy` | `buy` | `close_k·K < equil_sum·(1 − threshold)` |
| `meanreversion.sell` | `sell` | `close_k·K > equil_sum·(1 + threshold)` |
| `meanreversion.abstain.within-deviation` | `abstain` | neither strict bound holds |

Reason attributes: `equil_sum`, `current_close`, `deviation_threshold`, `lookback`, `bars_used`.

**5. State transition.** `exact_content` is an immutable `TraderSignalStateContent` holding a bounded
`bars` → `tuple` of `(close, high, low)` floats (oldest first; length `0..K`), a timezone-aware
`last_closed_at`, and the exact `config_fingerprint`. Per evaluation: (a) compute the predicate from
the **prior** window plus `close_k`; (b) append the current bar, evicting the oldest if length > `K`;
(c) emit the next state. The current bar is never in its own equilibrium window; chronology is
enforced fail-closed.

**6. Insufficient / flat / ambiguous.** Constant series ⇒ `equil_sum/K == close_k` ⇒
`close_k·K == equil_sum` ⇒ both strict inequalities false ⇒ `ABSTAIN`. Zero variance ⇒ `ABSTAIN`.
Fewer than `K` prior bars ⇒ no decision emitted. `deviation` inside `±threshold` ⇒ `ABSTAIN`.

**7. No-lookahead.** Equilibrium for `b_k` uses only `b_{k-K}..b_{k-1}` (strictly earlier, all
visible). `close_k` is compared against a reference that excludes itself and every future bar.

**8. Tie handling.** Strict inequalities; `close_k·K == equil_sum·(1 ∓ threshold)` ⇒ `ABSTAIN`.
Exact `Decimal` equality.

**9. Bounded arithmetic.** Window ≤ `K`; sum ≤ `K` terms; predicates are multiplication-only
(no division). No non-finite path.

**10. Compatibility.** Reads `OhlcSnapshot.close` only (plus `instrument`, `closed_at`). Emits side +
reason codes; same prohibitions as 1.1 §10.

### 1.3 Breakout / Volatility — family `qore.trader.breakout`, kind `virtual-trader.breakout-volatility`

**1. Configuration.**

| field | type | validation |
|---|---|---|
| `lookback` | exact `int` (reject `bool`) | `1 <= lookback` |
| `breakout_margin` | `Decimal` | finite and `breakout_margin > 0` |
| `require_min_range` | exact `bool` (reject `int` 0/1) | must be `bool` |
| `min_range` | `Decimal` | finite and `min_range > 0` (present always; used only when `require_min_range` is true) |

`breakout_margin ≥ 1` is accepted (lower threshold ≤ 0 ⇒ SELL unreachable; BUY still reachable);
non-finite/negative/zero rejected.

**2. Lookback.** `N = lookback + 1` (denoted `K = lookback`). Bars `0..N-1` (fewer than `K` prior
bars): **no decision emitted**. At exactly `N` bars (`b_K`): first `BUY`/`SELL`/`ABSTAIN`.

**3. Predicate** (exact, division-free). Let `prior_high = max(high_i)`,
`prior_low = min(low_i)` over `b_{k-K}..b_{k-1}` (current **excluded**).
`prior_range = prior_high − prior_low`.

```
if prior_range == 0:                                   ABSTAIN (breakout.abstain.zero-range)
elif require_min_range and prior_range < min_range * prior_low:
                                                       ABSTAIN (breakout.abstain.insufficient-range)
upper = prior_high * (1 + breakout_margin)
lower = prior_low  * (1 − breakout_margin)
BUY  iff close_k > upper
SELL iff close_k < lower
else ABSTAIN (breakout.abstain.no-breakout)
```

**4. Reason codes and evidence.**

| code | side | meaning |
|---|---|---|
| `breakout.buy` | `buy` | `close_k > upper` |
| `breakout.sell` | `sell` | `close_k < lower` |
| `breakout.abstain.no-breakout` | `abstain` | `lower ≤ close_k ≤ upper` |
| `breakout.abstain.zero-range` | `abstain` | `prior_high == prior_low` |
| `breakout.abstain.insufficient-range` | `abstain` | `prior_range < min_range · prior_low` |

Reason attributes: `prior_high`, `prior_low`, `prior_range`, `upper`, `lower`, `current_close`,
`breakout_margin`, `min_range`, `require_min_range`, `lookback`, `bars_used`.

**5. State transition.** `exact_content` is an immutable `TraderSignalStateContent` holding a bounded
`bars` → `tuple` of `(close, high, low)` floats (oldest first; length `0..K`), a timezone-aware
`last_closed_at`, and the exact `config_fingerprint`. Per evaluation: (a) compute the predicate from
the **prior** window plus `close_k`; (b) append the current bar, evicting the oldest if length > `K`;
(c) emit the next state. The current bar is never in its own threshold window; chronology is
enforced fail-closed.

**6. Insufficient / flat / ambiguous.** Zero prior range (`prior_high == prior_low`) ⇒ `ABSTAIN`
always. Constant series ⇒ zero range ⇒ `ABSTAIN`. `close_k` exactly on `upper`/`lower` ⇒ `ABSTAIN`.
Fewer than `K` prior bars ⇒ no decision emitted.

**7. No-lookahead.** The threshold for `b_k` is built only from `high/low` of `b_{k-K}..b_{k-1}` —
bars strictly earlier than `b_k`. **The current bar's own `high`/`low`/`close` are never used to
define its own `upper`/`lower` threshold**; only `close_k` is compared against a reference formed
from prior bars. No future bar contributes.

**8. Tie handling.** Strict `>`/`<`; `close_k == upper` or `== lower` ⇒ `ABSTAIN`. Exact `Decimal`
equality.

**9. Bounded arithmetic.** Window ≤ `K`; `max`/`min` over ≤ `K` terms; multiplications only. No
non-finite path.

**10. Compatibility.** Reads `OhlcSnapshot.close`, `high`, `low` (plus `instrument`, `closed_at`).
Emits side + reason codes; same prohibitions as 1.1 §10.

## §2 Falsification

### 2.1 Trend / Momentum

| # | Adversarial input | Output |
|---|---|---|
| 1 | Constant series `close = 1.0` forever, any config | `short_sum/L == long_sum/L` ⇒ `lhs == 0` ⇒ `ABSTAIN` (`trend.abstain.insufficient-strength`). |
| 2 | Boundary equality: `S=1, L=2, min_strength=0.01`, closes `[1.00, 1.01]` ⇒ `short_sum=1.01, long_sum=2.01` ⇒ `lhs=1.01·2 − 2.01·1 = 0.01`, `rhs=0.01·2.01·1 = 0.0201` ⇒ `lhs < +rhs` and `lhs > −rhs` ⇒ `ABSTAIN` (not BUY). | Equality at the momentum band ⇒ `ABSTAIN`. |
| 3 | One-bar spike then flat: `S=2, L=4`, closes `[1.00, 1.00, 1.00, 1.05]` ⇒ `short_sum=2.05, long_sum=4.05` ⇒ `lhs=2.05·4 − 4.05·2 = 0.10`, `rhs=min_strength·4.05·2`. With `min_strength=0.01` ⇒ `rhs=0.081` ⇒ `lhs>rhs` ⇒ `BUY`. The spike enters the window only after it is visible; next bar `1.00` rolls it out deterministically. | Validates roll-in/roll-out and no-lookahead. |
| 4 | `min_strength = NaN`, `long_lookback = 0`, `long_lookback == short_lookback`, or `short_lookback = True` | Config construction raises (fail closed). |

**Corrected weaknesses.** (i) Naive `momentum = (short_mean − long_mean)/long_mean` compared in
`Decimal` division depends on the ambient `Decimal` context (global mutable state, non-exact tail) →
replaced by division-free cross-multiplied `lhs vs ±rhs`. (ii) Naive non-strict `short_mean ≥
long_mean` fires `BUY` on any infinitesimal positive tilt → replaced by a strict symmetric
`±min_strength` band with equality ⇒ `ABSTAIN`. (iii) Absolute price-difference strength is
instrument-scale dependent → normalized by `long_sum` (dimensionless `min_strength`).

### 2.2 Mean Reversion

| # | Adversarial input | Output |
|---|---|---|
| 1 | Constant series `close = 1.0` ⇒ `equil_sum/K == close_k` ⇒ both strict bounds false ⇒ `ABSTAIN` (`meanreversion.abstain.within-deviation`). | Zero variance ⇒ `ABSTAIN`. |
| 2 | Boundary equality: `K=1, deviation_threshold=0.01`, prior `[1.00]`, current `close=0.99` ⇒ `close_k·K = 0.99`, `equil_sum·(1−0.01) = 0.99` ⇒ `0.99 < 0.99` false ⇒ `ABSTAIN` (not BUY). | Equality at `−threshold` ⇒ `ABSTAIN`. |
| 3 | Monotonic climb `[1.00, 1.01, 1.02, …]`, `K=2, threshold=0.005` ⇒ equilibrium lags; `close_k` above equilibrium ⇒ SELL every bar. This is the hypothesis's honest behavior (fades a trend), not a bug — the rule remains deterministic. | Documents fade-in-trend behavior; no edge claimed. |
| 4 | `deviation_threshold = −0.1` (negative) or `lookback = False` | Config construction raises. |

**Corrected weaknesses.** (i) Naive equilibrium **included** the current close (self-referential) →
equilibrium now uses only the `K` **prior** closes; `close_k` never shapes its own reference. (ii)
Naive deviation used `Decimal` division → division-free cross-multiplied predicates. (iii) A
dispersion gate (stddev/range) was considered and **dropped**: constant/zero-variance series already
yield `deviation == 0 ⇒ ABSTAIN`, so the gate added no falsifiable power and only extra config.

### 2.3 Breakout / Volatility

| # | Adversarial input | Output |
|---|---|---|
| 1 | Zero prior range: prior window all `high == low == 1.0`, current `close = 1.05` ⇒ `prior_range == 0` ⇒ `ABSTAIN` (`breakout.abstain.zero-range`) even though `close` is far above. | Zero range ⇒ `ABSTAIN`. |
| 2 | Boundary equality: `K=1, breakout_margin=0.01`, prior `[high=1.00, low=0.90]`, current `close=1.01` ⇒ `upper = 1.00·1.01 = 1.01` ⇒ `close > upper` false ⇒ `ABSTAIN` (`breakout.abstain.no-breakout`), not BUY. | Equality at breakout ⇒ `ABSTAIN`. |
| 3 | Self-reference probe: `K=1`, current bar is `high=2.0, low=0.5, close=1.9`. If the current bar's own high/low were used, `upper = 2.0·1.01 = 2.02` ⇒ no breakout. With the correct prior-only window, the prior bar's high/low (not the current bar's) define `upper`/`lower` ⇒ `close=1.9` is judged against the **prior** range only. The rule cannot use `2.0`/`0.5` to set its own threshold. | Current bar excluded from its own threshold. |
| 4 | `breakout_margin = 0`, `breakout_margin = ∞`, `require_min_range = 1` (int) | Config construction raises. |

**Corrected weaknesses.** (i) Naive prior range **included the current bar** in `prior_high`/
`prior_low` (self-threshold lookahead) → prior window is strictly `b_{k-K}..b_{k-1}`. (ii) Naive
`close ≥ upper` bought exactly on the boundary → strict `>`/`<` with equality ⇒ `ABSTAIN`. (iii)
`min_range` compared as a ratio via division → cross-multiplied `prior_range < min_range·prior_low`.

## §3 Shared signal model

**Side representation (minimal, closed).** `Side = BUY | SELL | ABSTAIN` — exactly three members,
nothing else. It is a first-class value, never a bit or a stringly enum. The canonical machine
field on every emitted `FunctionalDecision` is:

```
metadata.attributes["side"] ∈ {"buy", "sell", "abstain"}   # mandatory, exactly one
```

The reason code (`*.buy`, `*.sell`, `*.abstain.*`) is the structural/
human channel and must agree with `side` (invariant: `side == "buy"` ⇔ code is a `*.buy` code, etc.).
Warmup (fewer than the required lookback bars) emits **no decision**, so no warmup reason code is
ever emitted.

**Outcome semantics (authorization/status, NOT trade side).** The `DecisionOutcome` is emitted by a
**non-mechanical** mapping from "did a determinate direction get produced":

| outcome | emitted when | never means |
|---|---|---|
| `APPROVED` | a determinate directional signal was emitted — **both `BUY` and `SELL`** | "approve a buy" |
| `BLOCKED` | explicit no-signal — `ABSTAIN` (flat/ambiguous/zero-range) | "blocked sell" |
| `REJECTED` | **never emitted** by these three producers (config/state failure raises, does not emit) | — |
| `DEGRADED` | **never emitted** by the minimal rule set (reserved for future quality-gated signals) | — |

This deliberately refuses `BUY→APPROVED, SELL→REJECTED, ABSTAIN→BLOCKED`: `SELL` is also `APPROVED`
because "approved" means "a determinate directional signal was emitted", never "approve the buy
direction". `side` is carried separately, so outcome never encodes direction.

**Per-decision fields (all three methodologies).**

- `decision_type = "qore.trader.research-signal"`; `status = RESOLVED`; `priority = NORMAL`.
- `timestamp = simulated_now` (the only "now" the producer may use).
- `decision_id` is a deterministic `DecisionId` derived from a SHA-256 digest over a fixed domain,
  the run-binding fingerprint, the evaluation sequence number, the side, and the canonical evidence
  — **never `uuid4`**.
- `metadata.correlation_id` is a deterministic `CorrelationId` derived from a SHA-256 digest over the
  run-binding fingerprint; `causation_id = None`.
- Exactly one `DecisionReason` per decision. Its `summary` is a fixed constant per reason code (no
  float repr interpolation); all metrics live in `reason.attributes` as canonical strings.
- `state_schema_version = "v1"`; `evaluation_sequence_number` starts at `0` and increments by exactly
  1 each `evaluate`.

Determinism invariant: same config + same evidence ⇒ byte-identical `next_state` and decisions (same
`side`, same reason codes, same canonical evidence, same deterministic IDs).

## §4 Identity and config

| methodology | `family` | `schema_version` | `software_revision` | specialist `kind` |
|---|---|---|---|---|
| Trend / Momentum | `qore.trader.trend` | `v1` | `qore.trader.trend.v1` | `virtual-trader.trend-momentum` |
| Mean Reversion | `qore.trader.meanreversion` | `v1` | `qore.trader.meanreversion.v1` | `virtual-trader.mean-reversion` |
| Breakout / Volatility | `qore.trader.breakout` | `v1` | `qore.trader.breakout.v1` | `virtual-trader.breakout-volatility` |

All identities satisfy the existing regex contracts (`family` `[a-z][a-z0-9]*(\.[a-z][a-z0-9]*)*`;
`schema_version` `v\d+(\.\d+)*`; `software_revision` `[A-Za-z0-9][A-Za-z0-9._/+:-]*`; `kind`
`[a-z][a-z0-9.-]*`). `kind` also satisfies the `virtual-trader.*` namespace rule required by
`ResearchAnalysisSpecification`.

Config is expressed as `ResearchStrategyParameter` entries (name `[a-z][a-z0-9._-]{0,79}`). Exact
names and types:

**`qore.trader.trend`**: `short_lookback` int, `long_lookback` int, `min_strength` Decimal.

**`qore.trader.meanreversion`**: `lookback` int, `deviation_threshold` Decimal.

**`qore.trader.breakout`**: `lookback` int, `breakout_margin` Decimal, `require_min_range` bool,
`min_range` Decimal.

Construction-time validation (fail closed, raise — never emit a `REJECTED` decision):
- int lookbacks: exact `int`, `>= 1`, reject `bool` (and any `bool`-as-int laundering);
- Decimal thresholds: finite and `> 0`, reject negative/zero/NaN/Inf;
- `require_min_range`: exact `bool`, reject `int` 0/1;
- ordering: `long_lookback > short_lookback`;
- unknown/duplicate parameter names rejected.
