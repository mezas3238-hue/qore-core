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
