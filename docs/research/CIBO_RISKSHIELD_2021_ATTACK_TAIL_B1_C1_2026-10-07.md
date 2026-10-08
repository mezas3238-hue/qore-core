# CIBO RiskShield — causal 2021 ATTACK tail, B1 forensic and C1 experiment

**Date:** 2026-10-07 (America/Asuncion). **Status:** reused-holdout research only; NOT certification. **Owner:** independent RiskShield engineering lane. **Base commit:** `ebbfacc6d28c26c32e76fb3bb6043e9d55f32dec` from canonical `agent/cibo-causal-expectation-leakage-fix-001`. **Isolation:** `agent/cibo-dd-riskshield-highmult-capital-c1-001` — do not overwrite concurrent architect branch.

## Sovereign rules
- Trader submits and executes every entry; CIBO post-entry financial administration only.
- 3,368/3,368 decisions/trades, zero Sizing rejection/defer, zero ATTACK sovereign breach; four economic engines preserved.
- Frozen terminal capital floor USD 582,440.0252953678696769360345. Favor greater capital and lower max DD/gross losses (STRICT PARETO); do not promote a worse variant.
- The current 3-year period is repeatedly used for research; no claim of unbiased OOS certification or a guaranteed 20% future DD.

## Frozen control (37.772111615%)
- Run family: [37716702999](https://github.com/mezas3238-hue/qore-core/actions/runs/37716702999).
- Reproduced in B1 [37717684638](https://github.com/mezas3238-hue/qore-core/actions/runs/37717684638), artifact ID `11524622662`.
- Capital USD 668,910.439682713; max DD 37.77211161548658%; total gross loss USD 957,225.911831171; ATTACK gross loss USD 955,665.772155971; PF 1.698738334823; 3,368/3,368, no breaches.
- The dominant episode is 2021-02-09T06:55Z peak capital **USD 61,696.5397732549** → 2021-02-26T15:10Z trough **USD 38,392.4539072080**, about USD 23,304.09 lost.
- Largest negative settlements in this episode: ATTACK 8,106x USD −9,565.08 (R43_GBPUSD), ATTACK 5,000x USD −5,980.56 (R42_AUDJPY), ATTACK 5,000x USD −3,862.30 (R42_AUDJPY). Trader IDs are attribution, never blacklists.
- Core economy bind counts in frozen control: state-pressure lane1 = 1; state-pressure lane2 = 0; window7 low-capital = 3; portfolio shock = 67; ATTACK window4 = 39, window5 = 46, window6 = 11.
- Pivotal scientific caveat: these are realized negative settlements, not proof that one cap/stop can eliminate them without cutting important winners.

## B1 completed — hypothesis falsified
- [RiskShield 2021 Causal Pressure Context B1](https://github.com/mezas3238-hue/qore-core/actions/runs/37717684638) SUCCESS, 10/10 replays; comparisons formally asserted 3,368 entries and other invariants.
- All 8 risk-pressure2 target/risk/capital tuning variants reproduced identical 37.772111615% DD, USD 668,910.43968 terminal capital, USD 957,225.91183 total gross loss. Corresponding lane2 bind count is **ZERO**; adjustment was non-binding for the observed path.
- Transferring MEDIUM bootstrap partial 0.42 from earlier A1 worsened DD to **40.653416%**, terminal capital USD 661,549.44; REJECT.
- No B1 variant qualifies as STRICT PARETO improvement. Keep frozen control; do not promote.

## C1 underway — broad causal high-multiplier hypothesis
- [RiskShield High Multiplier Capital C1](https://github.com/mezas3238-hue/qore-core/actions/runs/37718339097) workflow: `.github/workflows/cibo-trader-lab-riskshield-highmult-capital-c1.yml`.
- Run 9 cases testing high multiplier bands 4,800–6,000x, 5,000–10,000x, 7,000–10,000x, capital windows USD 35–65k or 45–65k, current DD windows, and mild 0.99/0.95/0.90 attenuation. All use pre-decision risk state and broad bands; no future outcome or Trader name conditions.
- **Controlled confound:** The existing CLI has window7 already assigned to a useful USD 1k–1.3k/100x–170x guard (3 binds). C1 temporarily *repurposes* window7 as a surgical test to observe high-multiplier tail sensitivity; includes both frozen baseline and neutralized-old-window7. This is **research only**. Even if C1 produces a strict candidate, it CANNOT be promoted as a drop-in replacement: implement a separate, optional 8th causal window or equivalent isolated gate, restore original window7, rerun and verify full economic invariants.
- C1 ranking script reports exact capital, DD, total/ATTACK gross loss, PF, 3,368 decisions/executions, zero sovereign breach, window7 binds, max-DD peak/trough, top 3 negative settlements, and economic dominance.

## Structural Next Steps
1. Identify whether C1 high-multiplier cap gates the 2021 top-loss cluster. Analyze windows that actually bind, not merely numerical DD.
2. If test is promising, implement window8 as opt-in on an isolated branch, retaining original window7 and all 4 economic engines. Only then repeat strict comparisons.
3. Build real correlated portfolio projected-risk headroom telemetry from causally available information, **not a fictional guaranteed DD cap**. Include winners harmed by any taper and loss sensitivity to execution slippage.
4. Preserve sealed fresh 3-year OOS until architecture freeze and scientific gates.
