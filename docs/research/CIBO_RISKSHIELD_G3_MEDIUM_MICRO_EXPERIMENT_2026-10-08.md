# QORE CIBO G3 — causal MEDIUM cliff ridge

Date 2026-10-08. Research only. Branch `agent/cibo-riskshield-medium-micro-g3-001`. Parent confirmed G2 control commit `1ef9abcc9d21079cf3dcd1f0fe21131b87a071ed`. Do not merge without replay gates.

## Exact source-of-truth G2
- Successful run [37756517100](https://github.com/mezas3238-hue/qore-core/actions/runs/37756517100), artifact `11541140276`, nine historical replay cases PASS.
- `w8-p4020`: **DD 37.65314425098158957349679852%**, capital **USD 671596.0067590138091295810742**, total GL **USD 942631.9691091010943759051208**, ATTACK GL **USD 941071.8522931553193062988046**, PF **1.71240529577**.
- Compared G1 p4000, lower DD by 0.0128384119pp and lower gross loss USD 0.02286; capital lower USD 0.012776. The candidate passes floor-based STRICT Pareto but NOT strict full capital dominance.
- W7 original still binds 3, W8 10. All 3368 entries remain, 0 ATTACK sovereign breach, 0 Sizing reject/defer. `sovereign_floor_breach_usd` about 84.617 remains independently unresolved.
- Narrow width: fractions >=0.4050 in G2 caused gross losses to jump and capital to decrease about USD 5859, so escalation must be treated as risky.

## G3 research
[GitHub Actions run 37757591148](https://github.com/mezas3238-hue/qore-core/actions/runs/37757591148), commit `3fb32f8e2922ce899be9cd50b9ed41b299534f45` in isolated branch, workflow `.github/workflows/cibo-riskshield-medium-micro-g3.yml`.

Exact G2 `p4020` control plus 8 causally valid hypotheses, W8 cap 0.9000 intact, all 7 original windows kept:
- p4030/p4040/p4045/p4048/p4049 at the same -0.40 closed-bar adverse R threshold.
- p4020 with adverse R thresholds -0.38/-0.35/-0.30; all actions from closed bars at subsequent M5 open.
- No Trader identity constraints, no outcomes used before settlement, no blocked Trader entries.
- Ranker asserts 3368 trades and entries, zero ATTACK breach, zero Sizing reject/defer, exact control parity at 100 decimal precision; conditional success requires DD less than G2 and terminal capital above sovereign economic floor with non-worsening total/ATTACK GL. Stronger goal is capital >=671596.006759.

## Scientific next work
1. Inspect G3 bind counts, loss and DD, and cliff behavior. Never keep a lower DD with a destroyed growth ceiling.
2. For 2019 37.65% MEDIUM drawdown (~USD30 loss from USD79 peak), 22% would require reducing loss to USD17.5 if peak unchanged. Tuning 0.4 partial by tiny thousandths cannot plausibly achieve full remaining ~15.65pp; this is a **local fine ridge**, not the structural multi-epoch solution.
3. Isolate causal 2019 MEDIUM adverse events with timestamp-safe M5 closed-bar and predecision estimated risk. Develop additional post-entry economics that preserve winners, loss at stop and compounding, and show top-10 episodes at every iteration; analyze 2020 ATTACK episodes too.
4. Reused historical dataset is research only. Do not unseal fresh 3-year OOS until architecture and policy frozen.
5. No statement 'Trabajo cumplido' until verified <=22% with all gates.
