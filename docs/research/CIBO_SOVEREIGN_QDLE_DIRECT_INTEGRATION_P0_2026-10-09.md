# CIBO SOBERANO ↔ QDLE — IMPLEMENTACIÓN DIRECTA P0 (2026-10-09)

**ESTADO:** Integración de código y batería sintética end-to-end **APROBADAS EN SHADOW**. **NO LIVE, NO MT5 SEND, NO CERTIFICACIÓN FINANCIERA**.  
**REPOSITORIO:** `mezas3238-hue/qore-core`. **RAMA:** `agent/cibo-sovereign-integration-p0-20261008`. **PR:** [#745](https://github.com/mezas3238-hue/qore-core/pull/745) (DRAFT).  
**HANDOFF RAÍZ:** [CIBO P0 emergency](CIBO_P0_MASTER_EMERGENCY_HANDOFF_2026-10-09_NATIVE_MAX_COGNITION_QDLE_UNIVERSAL_NO_STRATEGIC_BLOCKS.md).

## Contrato ejecutado

```text
TradeOpsState.ECONOMICALLY_VALUED
      +
Native MAX cognitive evidence / causal decision
      +
CiboEconomicInstruction (CIBO owns source lane, stop, capital, direction)
      +
FourMotorObservation (reconciled QORE NAV, net fees, broker economics)
      |
      v
cibo_sovereign_integration.administer_native_cibo_qdle_shadow(...)
      |
      +--> Native MAX cognitive sensor plan (uncertainty, reason, metacognition)
      +--> CIBO risk request <= 5% of same-epoch QORE NAV
      +--> Sizing / CIBO Compound / Adaptive Leverage / Compound Portfolio votes
      +--> build_cibo_directed_qdle_intent(...)
      +--> ONLY QDLE.reserve_for_trader(...) computes broker lots
      +--> audit_cibo_qdle_lotage(...) checks stop + roundtrip fees, margin and source
      +--> TradeOpsState.ECONOMICALLY_FUNDED / UNFUNDABLE
               (filled_lots=0, no MT5 order, no commission debited)
```

### New integration code

- **`src/qore/infrastructure/cibo_native_sovereign_qdle.py`**: single contract for validated Native sensor receipts, pure `apply_native_qdle_risk_cap` and direct `administer_native_sovereign_qdle_shadow` orchestration. NO original legacy `CAPITAL_BLOCK` or `COGNITIVE_BLOCK` gate. Never manufactures CIBO decision/lane or cash source. Decided/observed/issued epoch, IDs and source digest checked. This is NOT cryptographically authenticated producer authorization.
- **`src/qore/infrastructure/cibo_sovereign_integration.py`**: canonical callable `administer_native_cibo_qdle_shadow` (Sovereign public ingress), delegating to the strictly no-send bridge.
- **`scripts/qdle_3368_dual_ledger_replay.py`**: now uses the SAME `apply_native_qdle_risk_cap` instead of independently implementing another cognitive-to-physical sizing rule. Still cannot use Trader control R to settle Native-managed positions.
- **`src/qore/infrastructure/cibo_p0_native_cognitive_management.py`**: existing causal sensor-derived research plan (mode, risk fraction and managed-exit policy), no old capital disposition authority.
- **`tests/infrastructure/test_cibo_native_sovereign_qdle_p0.py`**: 7 direct integration tests; changed Native MAX evidence modifies real QDLE lot quote on same USD60 physical broker scenario; verifies four motors, explicit CIBO lane/budget, old veto label inert, stale identity/time/digest fails, no SEND, no fake fill and **CONTROL history source rejected**.
- **`.github/workflows/cibo-p0-native-cognitive-management-fast.yml`**: verifies canonical ingress, typed cognitive adapter, bid/ask exit path adapter, physical lot invariants.
- **`.github/workflows/cibo-p0-native-max-manager-qdle-3368.yml`**: triggers updated 3368 fresh Native run whenever sovereign/QDLE integration code changes and runs direct sovereignty unit tests before both full scenarios.

### Verified GitHub evidence

**Fast CI:** [#37932304931](https://github.com/mezas3238-hue/qore-core/actions/runs/37932304931) **SUCCESS** on SHA `b41953ee0758f2a465e575138f984c6b4f9e767e`. Test groups **5 + 4 + 7 + 17 + 11 + 11 = 55 PASS**. Synthetic EURUSD, USD60 QORE NAV, USD14/lot roundtrip and unchanged margin broker simulation:

| Native sensor mode | QORE all-in budget request | QDLE physical research lot |
|---|---:|---:|
| BANK | $0.75 | 0.00 (min lot unfinanceable) |
| MEDIUM | $1.50 | 0.01 |
| ATTACK | $3.00 | 0.02 |

CIBO receives every signal even if a requested 0.01 minimum lot is physically impossible; no silent strategy veto. No direct or hidden order_send path was added.

**Full 3368 baseline verified before the direct-contract patch:** [#37915676547](https://github.com/mezas3238-hue/qore-core/actions/runs/37915676547) SUCCESS, artifact `11610487047`, 3368 received, 1961 physical QDLE PAPER quotes, 1407 no quote physically affordable, 0 CIBO-managed settled and 0 broker fills. PF / DD of CIBO managed strategy not measurable without complete bid/ask.

**Updated current-shared-contract 3368 fresh run:** [#37932270093](https://github.com/mezas3238-hue/qore-core/actions/runs/37932270093), started from revision `18d816f5`; pending at creation of this note (read result before declaring its success). The canonical bridge is separately tested at latest SHA.

### What this DOES NOT certify

- The new public entrypoint requires a **real CiboEconomicInstruction** and trustworthy, synchronized `FourMotorObservation`. It explicitly **does NOT synthesize** sovereign Bank/Cushion choices from old historic Trader outcomes or capital block labels. Native MAX sensor plan is a deterministic paper adapter, **not yet a fully signed native autonomous trade-management stream**.
- The 3368 replay exercises the shared physical QDLE risk cap but **does not have complete bid/ask trajectories** and cannot claim fills, realized performance or a functioning NAV compounding cycle. The independent price-path adapter only provides causal per-trade SHADOW exits for actually covered price paths; it is not wired into a certified global settlement scheduler.
- Real FundedNext/MT5 quotes, fees, profit conversion, margin, broker stop levels, AUTHENTICATED producer receipts and position lifecycle are still unverified. **Do not use for LIVE deployment** or loosen physical risk/margin/provider invariants.
- The forbidden `REPLAY_SETTLED:`/`REPLAY_PRIOR_CASHBOOK:`/`TRADER_CONTROL_ONLY:` source cashflows cannot be passed into this Native CIBO QDLE route. Genuine CIBO-managed settlements may enter only when reconciled. Do not remove all defensive rules globally; prevent stale provenance instead.

### Remaining steps toward production certification

1. Replace current research Native sensor map with fully provenance-authenticated per-trade **native CIBO management instruction**, per-position update stream and signed source/treasury authority, independent of old selection gates.
2. Read broker data into MT5 **read-only** QDLE snapshots for all six real symbols, min grid, SL min/freeze, opening+closing commissions, profit tick values, margin BUY/SELL, provider rules. Test pre-trade order_check where permissible. Never order_send without separately authorized transition.
3. Integrate complete historical executable bid/ask path scheduler, simulate partial closes and charge OPEN fee once, CLOSE fee per filled exit, swap, margin release, marks, defensives and source balances. Only genuine managed settlements can modify QORE NAV or subsequent compound votes.
4. Replay all 3368 received signals with separate counts (quoted, physically simulated, filled by model, settled and missing data); produce verified PnL, PF and MTM DD only where evidence supports them, certify OOS and kill-switch gates.
5. Refresh the exact latest run artifact, tests and PR #745; keep PR DRAFT until native/MT5 security and settlement complete.

**Engineering status:** direct CIBO↔QDLE SHADOW integration implemented and CI-validated. **LIVE-ready CIBO and the 3368 administered exit replay remain P0 OPEN.**
