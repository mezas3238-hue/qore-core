# CIBO G2 — MEDIUM adverse partial closeout and continuation

**Research date:** 2026-10-08. Independent research lane; not deployment and not certification.

## G2 completed / evidence

- Repo `mezas3238-hue/qore-core`, branch `agent/cibo-riskshield-medium-bootstrap-g2-001`. [Run 37756517100](https://github.com/mezas3238-hue/qore-core/actions/runs/37756517100) SUCCESS, artifact **11541140276**, 9 replay results all checked; exact G1 control parity.
- Frozen G1 benchmark: case `w8-p4000-control`, max DD **37.66598266290644%**, capital **USD 671,596.019535245**, total GL **USD 942,631.991968356**, ATTACK GL **USD 941,071.852293155**; W7 binds 3, W8 binds 10, 3,368/3,368 entries.
- Best G2 STRICT PARETO research candidate `w8-p4020`: increase MEDIUM bootstrap adverse partial fraction 0.4000→**0.4020**; max DD **37.65314425098159%**, final capital **USD 671,596.006759014** (~USD 0.013 smaller), total GL **USD 942,631.969109101** (~USD 0.023 smaller), ATTACK GL unchanged, PF almost same, 3,368 entries. Pass STRICT vs frozen capital floor USD 582,440.03, **not full economic dominance** vs G1 capital.
- `w8-p4010`: DD 37.65956345694%, capital USD 671,596.013147, GL USD 942,631.980539, strict research pass but capital marginally lower.
- MEDIUM partial 0.405 through 0.410 caused discontinuous path branch and slashed final capital ~USD 665,736 while total GL increased to USD 955,328 and ATTACK GL increased to USD 953,764. Rejected. `0.398` increased DD vs control despite a tiny terminal capital increase; no strict pass.
- G2 best DD still has dominant **2019-07-19→2019-08-12 MEDIUM** episode. Next action is finer micro-ridge near 0.403–0.405 alongside causal adverse-signal early triggers. No memorized dates or Trader exclusions.

## Other architect comparison

Main concurrent canonical run [37755900609](https://github.com/mezas3238-hue/qore-core/actions/runs/37755900609) `ctx-s050` has DD ~37.6550378674%, capital USD 670,938.6019, loss delta USD -6,573.746 from the earlier 37.7721% source. Its DD is better than frozen G1 37.66598%, but G2 p4020 currently better on both DD and terminal capital. **Do not merge policies without controlled replay**.

## Sovereign gates

No Trader entry veto: 3,368/3,368. Zero ATTACK sovereign breach and MEDIUM Sizing reject/defer. Unresolved `sovereign_floor_breach_usd~84.617` remains separate; investigate before certification. Withheld unseen OOS three-year holdout. Milestone <=22% not reached. Do not declare “Trabajo cumplido”.

## Engineering sequence G3

1. Fresh isolated branch from G2 verified source, keep W8 (cap USD 35–65k, ATTACK 5000–10000x, 0.90 multiplier taper) and original W1–W7.
2. Replay an exact `w8-p4020` control; 2019 MEDIUM loss-cut condition `ADVERSE_PARTIAL_REDUCTION` bound to closed M5 causal evidence; vary only adverse partial fraction near phase transition (0.402–0.405) and alternative closed-bar loss-cut threshold -0.40→-0.38/-0.35/-0.30. Strict compare against best G2, capital and losses.
3. Observe negative results and damage to winners before committing; do not widen caps blindly. Use top-ten episode report to check bottleneck migration.
