# CIBO RiskShield G4 — constrained post-entry bootstrap stop research

Date: 2026-10-08. G4 isolated branch `agent/cibo-riskshield-bootstrap-initial-stop-g4-001`, based on G2 verified commit `1ef9abcc9d21079cf3dcd1f0fe21131b87a071ed`. Preserve canonical other-architect branch and live runtime unchanged.

## Goal
The user needs a replay-verified max DD <=22%, capital floor USD 582,440.03 untouched and ideally no degradation from current USD 671,596.01, 3368/3368 Trader entries, no reject/defer, no ATTACK sovereign breach, non-worsening gross losses. Holdout dataset reused for research only; fresh unseen 3-year holdout sealed until scientific certification. Separately investigate nonzero sovereign_floor_breach_usd ~84.617 in control.

## Current best verified lineage
G1 37.6659826629% max DD, capital USD 671,596.019535, GL USD 942,631.991968. G2 [run 37756517100](https://github.com/mezas3238-hue/qore-core/actions/runs/37756517100) improved with MEDIUM bootstrap partial 0.4020 to **37.65314425098159% max DD**, capital **USD 671,596.006759**, total GL **USD 942,631.969109**, ATTACK GL USD 941,071.852293, all gates against floor-based strict Pareto. No <=22% yet.

## Causal hypothesis
G2 micro tuning 0.400→0.402 improves 2019 MEDIUM bottleneck only marginally. G4 tests a **second post-entry-only MEDIUM bootstrap initial stop cap** using the already implemented causal M5 lifecycle engine and existing bootstrap gates:
- MEDIUM only; multiplier <=2; live total capital <=USD 100; live DD >=10% or 15%/20%; at least one settled Trader loss streak; available expected R <=0.10, causal.
- Existing `ADVERSE_PARTIAL_REDUCTION` fraction 0.4020 retained.
- Add `DEFENSIVE_INITIAL_STOP_CAP` as an optional **additional** lifecycle feature through `--lifecycle-bootstrap-override-feature`, with R caps -0.25, -0.22, -0.20, -0.18, -0.15, -0.12 at DD 10%; -0.15 at DD 15% and 20%.
- Original 7 windows and additive 8th ATTACK window intact, original portfolio shock controls, four economic engines intact. All Trader entries executed; CIBO can only administer after entry.
- Workflow [run 37757768704](https://github.com/mezas3238-hue/qore-core/actions/runs/37757768704), `.github/workflows/cibo-riskshield-bootstrap-initial-stop-g4.yml` 9 replays including exact `g2-p4020-control`. Ranking compares cap, DD, gross losses, PF, W7/8 bind counts and exact baseline parity, and asserts 3368 entries and sovereign ATTACK breach zero.

## Scientific caution
- This is an experimental stop **hypothesis** not a guaranteed hard max DD cap, especially under slippage/gaps.
- Earlier broad ATTACK post-entry partials harmed winners and reduced DD performance and wealth; MEDIUM selective boots may also destroy compound winners. Decline economic regression.
- DD improvement in 2019 merely migrates to the next 2020/2021 episode unless cross-regime protective logic is effective.
- Do not overfit 2019 dates or Trader identities; no outcome labels before decision.
