# CIBO — WALK-FORWARD DAMAGE ATTRIBUTION

## Baseline causal autopsy after full replay completion

Date: 2026-10-06  
Repository: `mezas3238-hue/qore-core`  
Branch: `agent/cibo-causal-expectation-leakage-fix-001`  
Primary completed replay: `37508688637`  
Replay head: `3819c9a504fd38178138bd07ce5171ced24375d1`  
Research status: NON-CERTIFYING / POSTDECISION ATTRIBUTION ONLY

---

## 1. Purpose

This note answers one narrow question:

**Which part of the causal CIBO chain caused the USD 60 account to deteriorate to approximately USD 0.14646?**

The objective is not to blame a component by correlation. The objective is to separate:

1. opportunity/forecast selection error;
2. Sizing;
3. Portfolio / Adaptive Leverage;
4. Compound / Capital Science;
5. QORE Risk;
6. provider friction;
7. Trader-specific contribution.

No postdecision result in this document is allowed to become same-trade predecision evidence.

---

## 2. Frozen baseline facts

Run `37508688637` completed successfully end-to-end.

Population:

- 3,368 opportunity decisions;
- 3,305 decision epochs;
- 35 cold starts;
- 3,333 causal walk-forward forecasts;
- 0 decoded-before-exit;
- 0 future outcome use;
- 0 capital-PnL use for forecast;
- 0 external AI calls.

Economic result:

- initial capital: USD 60;
- peak capital: ~USD 72.39560484;
- ending capital: ~USD 0.14646376;
- net PnL: ~USD -59.85353624;
- cumulative return: ~-99.7559%;
- authorized/settled trades: 39;
- all 39 QORE Risk decisions: ALLOW;
- no REDUCE decisions.

---

## 3. The strongest common cause: every destructive authorization used a provisional forecast

All 39 authorized trades had walk-forward observation counts between:

- minimum: 5;
- maximum: 19;
- median: 9.

Therefore:

**0 / 39 authorized trades had a mature 25-observation forecast.**

The current maturity contract defines 25 observations as the first point at which the five chronological blocks can each contain at least five completed observations.

This is not an outcome-derived profitability target. It is an estimator-maturity condition.

The old baseline had no productive cognitive gate preventing provisional walk-forward forecasts from reaching capital deployment.

The 39 deployed opportunities all had positive expected structural R, with mean expected structural R approximately +0.653R, but the realized selected set was economically negative.

For the broader provisional positive-net forecast surface:

- 51 provisional opportunities had positive expected net value at minimum executable size;
- the 39 that the old CIBO chain selected produced approximately USD -18.2125 at 1x/minimum-size equivalent;
- the 12 that were not selected produced approximately USD +0.4135 at the same minimum-size equivalent.

So the early ranking/selection layer did **not** rescue the weak provisional forecasts. On this small burned early sample it selected a materially worse subset.

This identifies the first upstream defect:

> **CIBO treated an estimator with insufficient causal history as capital-ready and allowed cognition/portfolio optimization to rank opportunities using unstable estimates.**

---

## 4. Adaptive Leverage / Portfolio was the dominant damage amplifier, not the sole root cause

Observed final multipliers on the 39 authorized trades:

- 37 decisions requested Adaptive Leverage 4x;
- 2 decisions requested Adaptive Leverage 2x.

Final executable volume versus minimum executable volume:

- 33 trades executed at 4x minimum volume;
- 4 trades executed at 3x minimum volume because downstream capacity capped the requested 4x;
- 2 trades executed at 2x minimum volume.

Actual total net PnL:

- ~USD -59.85353624.

Postdecision linear minimum-size counterfactual using the exact same 39 trades and the same realized outcomes, but scaling each trade back to 1x minimum executable volume:

- estimated net PnL: ~USD -18.21254062;
- estimated ending capital: ~USD 41.78745938.

Therefore the additional loss associated with 2x–4x amplification on those already-bad selections was approximately:

- **USD -41.64099561**;
- approximately **69.57% of the observed total account loss**.

This is a postdecision attribution, not a certification claim.

The correct interpretation is:

> **Forecast/selection error created the negative set; Portfolio / Adaptive Leverage multiplied the consequence of that error.**

Adaptive Leverage is therefore a major damage amplifier, but disabling it alone would not repair the upstream intelligence defect: the same selected trades at 1x still lose approximately USD 18.21.

---

## 5. Sizing was aggressive upstream, but usually not the binding final actuator

All deployed decisions used:

`sizing_mode = CAPABILITY_MAXIMUM`.

Sizing often proposed volumes much larger than the final authorized volume.

Across the 39 settlements:

- 37 / 39 final volumes were reduced below the raw Sizing proposal by downstream Portfolio / Adaptive Leverage / capacity logic;
- only the final 2 scarcity-era trades had Sizing proposal equal to final authorized volume;
- the median raw-Sizing-to-final-volume ratio was approximately 13.5x;
- the maximum observed ratio was approximately 76.5x.

Example from an early AUDJPY authorization:

- Sizing proposed volume: 0.64;
- Sizing stop risk: ~USD 56.66;
- Portfolio / Adaptive Leverage selected 4x minimum;
- final authorized volume: 0.04;
- final authorized stop risk: ~USD 3.54.

Therefore:

> **Raw CAPABILITY_MAXIMUM Sizing is dangerously aggressive as an upstream proposal, but it was not the binding cause of 37/39 realized trades. Downstream Portfolio / Adaptive Leverage materially reduced it.**

Sizing remains a required ablation target later, but it is not the principal explanation for this baseline collapse.

---

## 6. Compound / Capital Science is not the source of the baseline collapse

Among the 39 authorized trades:

GEN-C5:

- 31: `INSUFFICIENT_REALIZED_PROFIT_CAPACITY`;
- 8: `HOLD_CURRENT_STATE`.

GEN-C7:

- 39: `UNAVAILABLE_MISSING_EVIDENCE`.

GEN-C8:

- 31: `GENC5_CANONICAL_INPUT_UNAVAILABLE`;
- 8: `DEFENSIVE`.

GEN-C12:

- 39: `CRISIS_ENVELOPE_ALLOWS_CAPITAL`.

These were DEMO `OPEN_CAPABILITY_MAX` deployments, not successful incremental Compound expansion decisions funded by proven profit.

Therefore:

> **CIBO Compound did not create the destructive exposure in this baseline and must not be blamed for these losses.**

Compound still needs its later independent ceiling study, but it is not the present P0 culprit.

---

## 7. QORE Risk did not select the bad trades, and it did not resize them

For all 39 executed decisions:

- `risk_decision = ALLOW`;
- authorized volume == requested volume;
- authorized stop risk == requested stop risk.

So QORE Risk did not originate the forecast or ranking error and did not amplify the request after receipt.

However, it also did not rescue the account from an economically poor but mechanically admissible request.

Interpretation:

> **Risk behaved as a hard governor over the request it received. The economic-quality defect occurred upstream.**

Whether an additional independent survival envelope belongs in Risk is a separate architectural question and must not be mixed with forecast repair.

---

## 8. Provider friction is material but not the root cause

Across the 39 executed trades:

- total provider friction: ~USD 13.5052;
- gross structural PnL before provider friction: ~USD -46.3483;
- net PnL: ~USD -59.8535.

Thus provider friction contributed approximately 22.56% of the observed loss.

At the 1x minimum-volume counterfactual:

- structural selected-trade loss: ~USD -14.63095;
- provider friction: ~USD -3.58159;
- total: ~USD -18.21254.

No observed selected trade was transformed from gross-positive to net-negative solely by provider cost.

Therefore provider economics worsened the outcome, but the selected structural outcomes were already negative in aggregate.

---

## 9. Trader contribution: concentration of damage, not proof of defective Trader edge

Observed net PnL contribution in the 39-trade collapsed baseline:

- R34_XAUUSD: ~USD -33.92 across 7 settlements;
- VT31_NAS100: ~USD -17.58 across 10 settlements;
- R43_GBPUSD: ~USD -6.44 across 3 settlements;
- R38_GBPJPY: ~USD -3.3752 across 8 settlements;
- R42_AUDJPY: ~USD +1.4616 across 11 settlements.

Two R34 losses alone contributed:

- ~USD -18.08;
- ~USD -12.04;

for a combined ~USD -30.12, approximately half of the total account loss.

But this must **not** be interpreted as proof that R34 or VT31 is inherently defective.

On the much larger mature walk-forward surface at 1x minimum executable size, positive-net mature forecasts are positive in aggregate for these same Traders, including R34 and VT31.

So the stronger diagnosis is:

> **CIBO deployed too aggressively during the immature-history phase and concentrated capital into early forecasts before their estimator had enough causal evidence.**

---

## 10. Capital death sequence

First important threshold crossings from initial USD 60:

- <=90% of initial:
  - 2019-07-30;
  - VT31_NAS100;
  - settlement ~USD -5.04;
  - capital ~USD 52.66.

- <=75%:
  - 2019-08-02;
  - R42_AUDJPY;
  - settlement ~USD -9.0083;
  - capital ~USD 40.73.

- <=50%:
  - 2019-08-02;
  - VT31_NAS100;
  - settlement ~USD -3.86;
  - capital ~USD 29.95.

- <=33%:
  - 2019-08-06;
  - R34_XAUUSD;
  - settlement ~USD -18.08;
  - capital ~USD 15.91.

- <=25%:
  - 2019-08-07;
  - R34_XAUUSD;
  - settlement ~USD -12.04;
  - capital ~USD 3.87.

Final destructive settlement:

- 2019-08-09;
- VT31_NAS100;
- multiplier 2x;
- settlement ~USD -3.72;
- ending capital ~USD 0.14646.

After this, later opportunities could not express executable capital and correctly failed closed.

---

## 11. Preliminary causal hierarchy

Current evidence supports this hierarchy:

### Root upstream defect — HIGH confidence

**Forecast maturity / cognition admission defect.**

CIBO had no effective rule preventing a 5–19 observation walk-forward estimator from being treated as capital-ready.

All 39 damaging authorizations occurred before estimator maturity.

### Primary amplification mechanism — HIGH confidence

**Portfolio / Adaptive Leverage.**

2x–4x exposure amplification accounts for approximately USD 41.64 of incremental loss relative to the same 39 realized trades at 1x minimum executable size.

### Secondary economic drag — HIGH confidence

**Provider friction.**

Approximately USD 13.51 of the observed net loss came from provider economics, but structural gross PnL was already negative.

### Concentration channel — HIGH confidence

**R34_XAUUSD + VT31_NAS100 early losses.**

These Traders supplied most of the realized loss in the early collapsed path, but the evidence does not establish that their mature edge is defective.

### Not supported as root cause

- CIBO Compound;
- GEN-C5 / GEN-C7 / GEN-C8;
- QORE Risk as selector;
- raw Sizing as final binding actuator on most trades.

---

## 12. Current repair hypothesis under active replay

A new causal forecast-maturity contract now exists:

- 5–24 observations: PROVISIONAL;
- >=25 observations: MATURE for capital consideration;
- cold start remains non-capital;
- maturity is computed only from information available before the decision;
- no future outcome or PnL enters the gate.

CF07 / native MAX cognition now treats a provisional walk-forward forecast as missing evidence and abstains before productive capital evaluation.

This repair directly targets the common property of all 39 destructive baseline trades.

The active full replay on the repaired branch must determine whether:

1. those 39 early destructive deployments disappear;
2. capital survives until mature forecasts become available;
3. mature forecasts remain economically useful under actual Portfolio / Leverage / Risk interaction;
4. a second downstream culprit becomes visible after the maturity defect is removed.

Do not declare the maturity repair sufficient until the completed full replay proves the resulting capital path.

---

## 13. Next attribution work after the repaired replay

Once the repaired full replay completes, compare it against run `37508688637` on:

1. first capital deployment timestamp;
2. first deployment observation count;
3. selected-trade count;
4. multiplier distribution;
5. capital path and drawdown;
6. per-Trader net contribution;
7. mature forecast calibration;
8. 1x vs actual-leverage counterfactual;
9. provider-friction contribution;
10. whether any mature but low-consensus / high-dispersion forecasts still receive 4x;
11. whether Portfolio ranking remains overconfident;
12. whether QORE Risk needs a separate survival envelope after upstream economics are repaired.

Only after this causal comparison should CIBO proceed to independent Sizing / Adaptive Leverage / Compound / Compound Portfolio ceiling studies.

---

## 14. Current conclusion

The account did not die because of one isolated module.

The evidence currently supports a **compound failure chain**:

**IMMATURE WALK-FORWARD FORECAST**
→ **NO COGNITIVE MATURITY ABSTENTION**
→ **POSITIVE EXPECTED-UTILITY RANKING ON WEAK EVIDENCE**
→ **PORTFOLIO / ADAPTIVE LEVERAGE 2x–4x**
→ **QORE RISK MECHANICALLY ALLOWS ADMISSIBLE REQUEST**
→ **EARLY LOSS CONCENTRATION**
→ **CAPITAL FALLS BELOW EXECUTABLE MINIMUM**
→ **ACCOUNT BECOMES ECONOMICALLY DEAD**

The strongest current root-cause candidate is the missing forecast-maturity gate.

The strongest current damage amplifier is Portfolio / Adaptive Leverage.

This conclusion remains research-only until the repaired full replay completes and is compared against the frozen baseline.

---

## 15. Maturity-repaired early-window result — second culprit exposed

A dedicated post-repair diagnostic completed successfully:

- workflow: `QORE CIBO Maturity Early Window`;
- run: `37513344544`;
- replay head: `cb89572c4d6e963a70c463421aea6b79227cf5de`;
- research window: 2019-07-01 through 2019-12-31;
- opportunities: 544;
- decision epochs: 537;
- certification claimed: false;
- future outcome used: false.

Economic result after enforcing forecast maturity:

- initial capital: USD 60;
- ending capital: ~USD 115.03596465;
- net PnL: ~USD +55.03596465;
- peak capital: ~USD 147.56573637;
- settlements: 186.

This is a direct causal contrast to the old early collapse.

The old baseline was effectively dead by 2019-08-09 at ~USD 0.14646.

With provisional forecasts blocked, the account survives and grows.

Therefore the missing maturity gate is no longer merely a hypothesis:

> **The provisional-forecast admission defect was a real causal contributor to the original account death.**

### 15.1 However, the maturity repair reveals a second major defect

The repaired 2019 path still suffered maximum drawdown of approximately:

- USD 51.94195640;
- peak-to-trough: ~USD 147.57 -> ~USD 95.62.

Every one of the 186 authorized trades reported:

- `adaptive_leverage_multiplier = 4`.

Final executable volume was:

- 4x minimum executable volume on 155 trades;
- 3x minimum executable volume on 31 trades because account/capacity constraints clipped the requested 4x.

Therefore the current so-called Adaptive Leverage is not materially adapting intensity across the mature sample.

### 15.2 Exact structural reason Portfolio tends to choose 4x

The current native Portfolio objective evaluates each candidate multiplier using:

`expected net utility * multiplier / expected capital minutes`

as its first optimization key, followed by total expected utility.

For any eligible opportunity with positive expected net utility, and absent a binding risk/margin constraint, utility increases linearly as the multiplier increases from 1 to 4.

Risk and margin are hard feasibility constraints and later tie-breakers; they are not a convex penalty that competes with the incremental expected utility.

Therefore, when:

- forecast net utility > 0;
- cognitive cap remains 4;
- account constraints permit 4;

the optimizer is structurally biased toward the maximum multiplier.

This exactly matches the observed repaired replay:

- 186 / 186 selected decisions requested 4x.

### 15.3 Forecast confidence quality is observed but not yet priced into capital intensity

After the maturity repair, cognition receives:

- observation count;
- maturity;
- positive/nonpositive block counts;
- block dispersion;
- median absolute deviation;
- evidence age;
- maturity fraction.

But the current productive behavior uses maturity primarily as a binary gate:

- provisional -> abstain;
- mature -> eligible.

The dispersion / MAD / block-consensus metrics are not currently converted into a nonzero economic uncertainty penalty that lowers Portfolio utility or multiplier.

The walk-forward manifest does not currently publish an `uncertainty_penalty_usd` derived from these confidence metrics, so the downstream economic adapter defaults that penalty to zero.

Thus a mature but uncertain forecast can still be economically treated almost like a mature high-confidence forecast for leverage purposes.

### 15.4 Postdecision 1x counterfactual of the repaired 2019 path

Using the exact same 186 selected trades and realized outcomes but scaling each settlement linearly back to 1x minimum executable volume:

Observed 3x/4x path:

- ending capital: ~USD 115.04;
- maximum drawdown: ~USD 51.94.

1x postdecision counterfactual:

- ending capital: ~USD 73.71;
- maximum drawdown: ~USD 13.88;
- minimum capital: ~USD 59.61.

Interpretation:

- 4x substantially amplified growth in this repaired sample;
- 4x also amplified drawdown from ~USD 13.88 to ~USD 51.94.

Therefore Adaptive Leverage is no longer correctly described only as a loss amplifier.

After maturity repair it is a **variance / drawdown amplifier**: it magnifies both valid edge and adverse clusters.

The architecture now needs to determine how much intensity the forecast confidence and survival state can actually support.

### 15.5 Drawdown concentration after maturity repair

The maximum drawdown segment contained 55 settlements.

Net contribution during the peak-to-trough segment:

- R38_GBPJPY: ~USD -30.66;
- R34_XAUUSD: ~USD -27.80;
- R42_AUDJPY: approximately flat;
- R43_GBPUSD: ~USD +1.48;
- VT31_NAS100: ~USD +5.03.

Largest individual losses in that drawdown included:

- R34_XAUUSD ~USD -15.88;
- R38_GBPJPY ~USD -9.52;
- R34_XAUUSD ~USD -8.24;
- R38_GBPJPY ~USD -7.24;
- R34_XAUUSD ~USD -7.12.

The worst R34 loss had:

- mature observation count: 71;
- positive chronological blocks: 4 / 5;
- expected structural R: ~+0.382R;
- realized structural outcome: -1R;
- authorized stop risk: ~USD 15.08;
- realized capital at decision: ~USD 113.69;
- stop risk / realized capital: ~13.3%.

This confirms the second problem cannot be solved merely by waiting for 25 observations.

### 15.6 Revised causal hierarchy after the repaired early replay

The evidence now supports:

1. **ROOT DEFECT #1 — CLOSED IN CURRENT REPAIR:** provisional forecast admitted to capital.
2. **ROOT DEFECT #2 — OPEN:** capital intensity does not sufficiently respond to forecast uncertainty / survival state once maturity is reached.
3. **DIRECT ACTUATOR:** Portfolio / Adaptive Leverage structurally prefers maximum multiplier for positive utility.
4. **DRAW-DOWN CONCENTRATION:** mature adverse clusters in R34 and R38_GBPJPY receive the same requested 4x intensity.
5. **NOT ROOT CAUSE OF THESE PATHS:** Compound.
6. **NOT SELECTOR:** QORE Risk; it authorizes the mechanically admissible request it receives.
7. **UPSTREAM PROPOSAL STILL REQUIRES LATER STUDY:** CAPABILITY_MAXIMUM Sizing.

The next P0 investigation must therefore test **confidence-aware Adaptive Leverage / Portfolio intensity** without outcome-aware tuning and without weakening QORE Risk.

This must be designed from causal predecision facts only, such as:

- observation maturity;
- block consensus;
- dispersion;
- median absolute deviation;
- evidence age;
- account drawdown / survival state;
- current risk/margin utilization;
- simultaneous opportunity competition.

Do not use realized future outcome to choose thresholds.

---

## 16. Full maturity-repaired replay — root cause #2 confirmed

The complete repaired walk-forward replay has now finished:

- workflow: `QORE CIBO Walk Forward Full Replay`;
- run: `37512709504`;
- replay head: `a4af979420effe2b1d4ae9039706de7ca12243a5`;
- result: SUCCESS;
- 3,368 decisions / 3,305 epochs;
- 292 Risk-authorized settlements;
- future outcome used: false;
- certification claimed: false.

Economic result:

- initial capital: USD 60;
- peak capital: ~USD 147.56573637;
- ending capital: ~USD 0.08028499;
- net PnL: ~USD -59.91971501;
- maximum peak-to-trough drawdown: ~USD 147.48545139.

Therefore the forecast-maturity repair is necessary but not sufficient.

It removes the original July/August 2019 death, allows the account to grow strongly, but the account is later destroyed by April 2020.

### 16.1 Portfolio / Adaptive Leverage is effectively pinned at maximum intensity

Across the 292 authorized mature decisions:

- 291 requested multiplier 4x;
- 1 requested multiplier 1x;
- 244 finished at 4x minimum executable volume;
- 47 were clipped to 3x by downstream capacity;
- 1 finished at 1x.

The historical Full Economic Twin currently publishes:

`("capital_intensity_cap", "4")`

as a fixed cognitive constraint.

The cognition binding only changes this cap to zero when the executive directive is not RECOMMEND. For a positive RECOMMEND it leaves the cap at 4.

Therefore cognition currently has only an effective binary intensity authority:

- 0x if abstain/block;
- up to 4x if recommend.

It does not translate bounded confidence, drawdown, dispersion, MAD, evidence age or scenario severity into 1x/2x/3x intensity.

The Portfolio objective then maximizes:

`expected_net_utility * multiplier / expected_capital_minutes`

before risk/margin tie-breakers.

For any positive net utility, with no binding capacity constraint, the objective is monotonic in the multiplier and therefore structurally prefers 4x.

This is not merely an empirical pattern. It is an architectural consequence of the current objective plus the hard-coded cap.

### 16.2 QORE Risk passes the resulting request unchanged

For all 292 authorized decisions:

- authorized volume == requested volume;
- authorized stop risk == requested stop risk;
- Risk decision = ALLOW.

The historical provider/Risk assumption currently permits:

- risk headroom = 1.0 * equity;
- maximum risk = 1.0 * equity.

This means the hard governor can legally admit very large fractions of account equity when upstream Portfolio proposes them.

Observed authorized stop-risk / realized-capital ratios:

- median: ~3.25%;
- 75th percentile: ~5.35%;
- 90th percentile: ~8.44%;
- 95th percentile: ~13.12%;
- maximum: ~91.18%.

There were:

- 82 trades at >=5% of realized capital;
- 21 trades at >=10%;
- 13 trades at >=15%;
- 7 trades at >=20%.

Those >=5% trades contributed approximately:

- net PnL: USD -54.11.

Those >=10% trades contributed approximately:

- net PnL: USD -101.43.

The negative number larger than total account loss is possible because other trades generated offsetting profits.

This shows that the capital death is highly concentrated in high-risk deployments.

### 16.3 Same selected mature trades at 1x do not kill the account

A postdecision same-sequence linear 1x counterfactual for the exact same 292 selected trades gives approximately:

- ending capital: USD 45.05;
- peak capital: USD 82.47;
- maximum drawdown: USD 37.42.

Actual 3x/4x path:

- ending capital: USD 0.08;
- peak capital: USD 147.57;
- maximum drawdown: USD 147.49.

Thus the same selected sequence is economically weak net of costs, but it is **not account-killing at 1x**.

The additional loss associated with the higher realized intensity is approximately:

- actual net: -USD 59.92;
- 1x same-sequence net: -USD 14.95;
- incremental damage associated with higher intensity: ~USD -44.97.

This is postdecision attribution only; it is not a tuned production multiplier recommendation.

### 16.4 Forecast economic calibration remains severely wrong after maturity

The 292 selected mature decisions had aggregate Portfolio expected net utility of approximately:

- **+USD 258.02**.

Their realized net result was approximately:

- **-USD 59.92**.

Aggregate forecast-to-realized error:

- ~USD 317.94.

All 292 selected opportunities had positive expected Portfolio utility, but only ~52.4% realized positive net PnL.

The highest quartile by expected Portfolio utility was especially damaging:

- expected utility sum: ~+USD 174.39;
- realized net PnL: ~-USD 78.63.

Correlation between expected Portfolio utility and realized net PnL was negative:

- Pearson: approximately -0.146;
- Spearman: approximately -0.019.

Expected structural R itself had effectively zero rank relationship with realized structural outcome on the selected set.

Therefore maturity alone does not establish calibration.

The current estimator is causally legal but its economic magnitude is not sufficiently calibrated for capital intensity.

### 16.5 Confidence metrics are not yet a valid leverage oracle

The repaired forecast now exposes:

- observation count;
- positive/nonpositive block count;
- block dispersion;
- median absolute deviation;
- evidence age;
- maturity fraction.

But on this burned sample, simple monotonic interpretations are not supported.

Selected decisions by positive chronological block count:

- 3/5 positive blocks:
  - 100 trades;
  - realized net ~+USD 69.19.
- 4/5 positive blocks:
  - 127 trades;
  - realized net ~-USD 111.20.
- 5/5 positive blocks:
  - 65 trades;
  - realized net ~-USD 17.91.

So it would be invalid to outcome-tune a rule like “more positive blocks => more leverage.”

Likewise dispersion and observation count do not show a reliable monotonic relationship with realized net PnL in the burned sample.

The correct architectural conclusion is not to derive a magic threshold from these outcomes.

The correct conclusion is:

> confidence information must enter capital intensity through a predeclared, causal, robust uncertainty/survival law and then be tested out-of-sample.

### 16.6 Provider friction is now proven to be a major root economic problem

Across the 292 selected mature trades:

- gross structural PnL before provider friction: ~+USD 32.81;
- provider costs: ~USD 92.73;
- realized net PnL: ~-USD 59.92.

Therefore the selected mature surface had positive aggregate structural edge, but the edge was too small to pay its real provider economics.

At 1x minimum-size equivalent:

- gross structural PnL: ~+USD 8.92;
- provider friction: ~USD -23.87;
- net PnL: ~USD -14.95.

Trader-level decomposition:

- R34_XAUUSD:
  - gross structural ~-USD 51.48;
  - provider cost ~USD 30.40;
  - net ~-USD 81.88.
- R38_GBPJPY:
  - gross structural ~+USD 17.44;
  - provider cost ~USD 22.85;
  - net ~-USD 5.41.
- R42_AUDJPY:
  - gross structural ~+USD 50.38;
  - provider cost ~USD 11.69;
  - net ~+USD 38.69.
- R43_GBPUSD:
  - gross structural ~-USD 27.84;
  - provider cost ~USD 10.08;
  - net ~-USD 37.92.
- VT08_FOREX:
  - gross structural ~+USD 5.39;
  - provider cost ~USD 0.12;
  - net ~+USD 5.27.
- VT31_NAS100:
  - gross structural ~+USD 38.93;
  - provider cost ~USD 17.60;
  - net ~+USD 21.33.

So the damage mechanisms differ by Trader:

- R34 and R43: selected structural outcomes themselves are net destructive;
- R38_GBPJPY: structural edge is positive, but provider economics consume it;
- R42, VT08 and VT31 are positive contributors in the maturity-repaired path.

This does not prove permanent Trader quality. It identifies where CIBO's selected capital actually lost money in this burned replay.

### 16.7 Current root-cause hierarchy

The full evidence now supports four distinct layers:

1. **Forecast maturity admission defect** — causal and already repaired.
2. **Forecast economic calibration defect** — OPEN.
   - expected utility materially overstates realized economic value.
3. **Portfolio / Adaptive Leverage intensity defect** — OPEN.
   - fixed cognitive cap 4 plus a monotonic positive-utility objective drives almost every recommendation to 4x.
4. **Survival-envelope defect** — OPEN.
   - total stop risk may approach the full equity envelope;
   - Risk passes admissible upstream requests unchanged.

Provider friction is not merely noise: it is a first-order economic constraint that the selected gross edge frequently fails to cover.

Compound remains unsupported as a cause of this collapse.

### 16.8 Immediate causal ablation now launched

A dedicated workflow has been added:

`.github/workflows/cibo-damage-attribution-ablation.yml`

It freezes the burned damage window through 2020-04-30 and runs two orthogonal matrices:

1. fixed Portfolio multiplier:
   - 1x;
   - 2x;
   - 3x;
   - 4x.

2. total Risk/provider envelope as fraction of equity:
   - 2%;
   - 3%;
   - 5%;
   - 10%;
   - 25%;
   - 100% baseline.

This is intended to distinguish:

- selection/calibration damage;
- leverage amplification;
- survival-envelope failure.

No result from this matrix may be treated as a tuned production threshold merely because it performs best on this burned period.

---

## 17. Causal ablation matrix — Portfolio intensity and survival envelope

The dedicated attribution workflow completed successfully:

- workflow: `QORE CIBO Damage Attribution Ablation`;
- run: `37516432478`;
- head: `5464332be9371cc113c2cae495230b60fced553c`;
- result: SUCCESS;
- burned research window: 2019-07-01 through 2020-04-30;
- maturity gate enabled;
- future outcome used: false;
- certification claimed: false.

This matrix reruns the causal system. These are not static rescalings of the old settlements.

### 17.1 Fixed Portfolio multiplier ablation

| Fixed multiplier | Selected / settled | Ending capital | Net PnL | Peak capital | Maximum drawdown |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1x | 456 | ~USD 188.30 | ~+USD 128.30 | ~USD 201.61 | ~USD 38.39 |
| 2x | 456 | ~USD 316.22 | ~+USD 256.22 | ~USD 343.21 | ~USD 75.82 |
| 3x | 448 | ~USD 358.78 | ~+USD 298.78 | ~USD 398.10 | ~USD 112.53 |
| 4x | 292 | ~USD 0.08 | ~-USD 59.92 | ~USD 147.57 | ~USD 147.49 |

The result is not a smooth degradation.

There is an observed **capital-intensity cliff** between the 3x and 4x research lanes on this burned window.

The same maturity-gated opportunity stream:

- survives and compounds at 1x;
- survives and compounds more strongly at 2x;
- survives and compounds more strongly again at 3x;
- collapses at 4x and then loses the ability to participate in later opportunities.

The falling selected count at 4x is a consequence of path-dependent capital destruction, not superior selectivity.

This establishes causally that the current maximum-intensity behavior is a direct account-killing actuator in this replay.

It does **not** establish that 3x is the production-optimal multiplier. That would be outcome-tuning on a burned sample.

### 17.2 Total Risk/provider envelope ablation

After aligning the historical Full Economic Twin with the effective provider/Risk capacity, the survival-envelope matrix also completed.

| Total risk envelope as fraction of equity | Selected / settled | Ending capital | Net PnL | Peak capital | Maximum drawdown |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2% | 297 | ~USD 104.46 | ~+USD 44.46 | ~USD 152.10 | ~USD 47.64 |
| 3% | 334 | ~USD 60.50 | ~+USD 0.50 | ~USD 108.24 | ~USD 47.75 |
| 5% | 366 | ~USD 42.47 | ~-USD 17.53 | ~USD 99.94 | ~USD 57.47 |
| 10% | 442 | ~USD 211.11 | ~+USD 151.11 | ~USD 254.63 | ~USD 65.92 |
| 25% | 451 | ~USD 423.08 | ~+USD 363.08 | ~USD 479.97 | ~USD 118.17 |
| 100% baseline | 292 | ~USD 0.08 | ~-USD 59.92 | ~USD 147.57 | ~USD 147.49 |

The relationship is deliberately **not** interpreted as monotonic or as a parameter search.

The 2%, 3%, 5%, 10% and 25% outcomes differ because changing the envelope changes the entire chronological path:

- which opportunities can be expressed;
- which settlements occur;
- how much capital exists later;
- which subsequent opportunities remain executable.

Therefore no burned-window threshold such as 10% or 25% may be promoted as a production setting.

What the matrix does establish is narrower and stronger:

> **The unconstrained 100%-of-equity research envelope is causally unsafe. A materially tighter survival envelope can prevent the account-killing trajectory.**

### 17.3 Root cause versus amplifier versus contributing factors

The causal hierarchy can now be stated more precisely.

#### Root defect A — forecast admission maturity

Status: repaired in current branch.

The original 39 destructive early trades all used 5–19 observations.

Blocking provisional forecasts removed the first account death and allowed capital to grow.

#### Root defect B — capital-intensity wiring

Status: OPEN.

The historical Twin publishes `capital_intensity_cap = 4`.

Cognition effectively outputs:

- 0x when it abstains;
- up to 4x when it recommends.

The current Portfolio objective is monotonic in multiplier for positive expected utility.

The fixed-multiplier reruns prove that this wiring is causal:

- 1x / 2x / 3x survive;
- 4x kills the account.

#### Root defect C — survival envelope

Status: OPEN.

The baseline historical QORE Risk/provider model permits total stop risk up to 100% of equity.

The envelope reruns prove that reducing this boundary materially changes survival and prevents the baseline death path.

The exact production law remains unknown and must not be selected from this burned matrix.

#### Root defect D — economic forecast calibration

Status: OPEN.

On the 292 selected mature trades:

- expected Portfolio utility was strongly positive;
- realized net PnL was negative;
- expected-return ranking had almost no useful relationship with realized outcome;
- expected capital duration was materially shorter than actual duration.

Thus the capital allocator is optimizing a forecast surface whose magnitude and capital-velocity estimates are not adequately calibrated.

#### Direct economic drag — provider friction

Status: OPEN economic constraint, not merely noise.

The selected mature surface had aggregate positive gross structural PnL but negative net PnL because provider friction exceeded the extracted structural edge.

Provider cost must therefore be part of robust admission/intensity economics, not only bookkeeping after selection.

#### Integration defect — crisis capital not universally binding

Status: OPEN.

At least one authorized `OPEN_CAPABILITY_MAX` decision had a GEN-C12 `PAUSE_NEW_CAPITAL` result but still reached Risk.

The sovereign runtime currently blocks on `capital_science.allow_incremental_compound` only when Sizing action is `EXPAND`.

Therefore a broad crisis no-new-deployment signal can fail to stop a DEMO capability opening.

This is a real wiring defect, though it is not the dominant cause of the 292-trade collapse.

### 17.4 What is now ruled out as the principal culprit

Current evidence does not support the following as the primary cause of the collapse:

- CIBO Compound;
- GEN-C5 as a profit-funded expansion engine;
- QORE Risk as the selector of economically bad opportunities;
- provider friction alone;
- raw Sizing alone.

Raw Sizing remains aggressive and must still be studied independently, but on the damaging path Portfolio / Adaptive Leverage was normally the binding final intensity actuator.

### 17.5 What must be repaired before ceiling discovery

Before CIBO ceiling discovery resumes, the capital path needs these causal closures:

1. Replace the hard-coded binary 0-or-4 cognition/intensity seam with a causal confidence/survival intensity contract.
2. Make Portfolio optimize robust economic utility, not utility that rises linearly with multiplier until a hard capacity wall.
3. Treat forecast uncertainty, duration uncertainty and provider friction as first-order economic costs.
4. Make a survival envelope visible consistently to Regime, Full Economic Twin, Capital Science, Portfolio and QORE Risk.
5. Make GEN-C12 `NO_NEW_DEPLOYMENT` / `PAUSE_NEW_CAPITAL` binding for every new deployment type, including `OPEN_CAPABILITY_MAX`.
6. Keep QORE Risk sovereign and independent.
7. Re-run the same burned diagnostics only for causal debugging; do not tune production thresholds from them.
8. Freeze the repaired candidate before any fresh holdout or certification claim.

### 17.6 Current strongest causal conclusion

The dominant account-killing mechanism is now supported by direct reruns:

**mature-but-miscalibrated economic forecast**
→ **cognition recommends without graded intensity**
→ **hard-coded 4x cap remains available**
→ **Portfolio objective drives positive opportunities toward maximum multiplier**
→ **100%-equity survival envelope permits oversized requests**
→ **provider costs + adverse clusters consume capital**
→ **capital path crosses a nonlinear survival cliff**
→ **later opportunities become unexecutable**
→ **account dies**.

The fixed 1x/2x/3x/4x matrix demonstrates that the 4x intensity behavior is causal, not merely correlated with the collapse.

The survival-envelope matrix independently demonstrates that the 100%-equity hard envelope is also causally unsafe.

Neither matrix authorizes choosing a final production multiplier or risk percentage from this burned period.

