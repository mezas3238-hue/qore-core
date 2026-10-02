# QORE CORE — HANDOFF MAESTRO DE CONTINUIDAD

## ARQUITECTO B — CIBO PROVIDER / RISK / CMA / FORWARD / CAPITAL TRUTH

**Checkpoint revalidado contra GitHub:** 30-SEP-2026  
**Repositorio fuente de verdad:** `mezas3238-hue/qore-core`  
**PR principal CIBO:** #651 — DRAFT / UNMERGED  
**PR hijo Arquitecto B:** #661 — DRAFT / UNMERGED / MERGEABLE  
**Rama exclusiva B:** `agent/cibo-certification-architect-b-integration-001`  
**HEAD B al congelar este handoff:** `2b13c4395e4bf8dc0d47118040a6915e3df5911c`  
**Estado PR #661:** 114 commits, 70 archivos cambiados, +8889 / -132 líneas.

---

# 0. IDENTIDAD DEL SIGUIENTE ARQUITECTO

Este handoff corresponde **exclusivamente al ARQUITECTO B de CIBO**.

Su misión es continuar y cerrar, sin detenerse a pedir instrucciones después de cada
pequeño avance, todos los workstreams B:

```text
T01
T02
T03
T11
T16
T17
T20
PROVIDER_ECONOMICS
FORWARD_QUALIFICATION
FRESH_OOS
RISK_INTEGRATION
CMA_FOUNDATION_INTEGRATION
LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK
USD60_CAPABILITY_PROGRAM
INTEGRATED_CAPITAL_TRUTH
```

Arquitecto B NO debe absorber los workstreams científicos GEN-C / Compound propiedad
de Arquitecto A, ni modificar el ledger/gate final de A para fabricar cierres.

Arquitecto B sí debe producir toda la evidencia provider/Risk/CMA/forward/capital-truth
que A y el Integrador necesiten para la certificación final.

---

# 1. GOBERNANZA INNEGOCIABLE

1. GitHub es la fuente de verdad.
2. PRs permanecen DRAFT / UNMERGED hasta orden del Owner.
3. No LIVE, producción, capital real ni mutaciones de broker/VPS sin orden explícita.
4. No tocar retroactivamente:
   - `CIBO_PHASE20_FULL_SURFACE_FORWARD_CANDIDATE_V3`
   - code SHA `edf96722fd0505711aa88bc1d15296b09e6dba6f`
   - frozen `2026-09-28T04:26Z`.
5. No abrir para desarrollo/tuning:
   - `CIBO_USD60_6M_HOLDOUT_2017H1_V1`
   - 2017-01-01 inclusive → 2017-07-01 exclusive
   - estado `SEALED_UNTOUCHED`.
6. No fabricar provider economics, slippage, hedge, options, margin, covariance,
   execution costs, terminal causes, releases o capital truth.
7. Si falta evidencia real, el sistema debe permanecer `UNKNOWN`, `NOT_READY`,
   `ABSTAIN` o fail-closed según el contrato.
8. Nunca confundir:
   - account HEDGED con hedge económico T16;
   - nombres de símbolos con opciones/spreads T17;
   - PnL negativo con stop estructural T02;
   - quote cost con realized execution cost T11;
   - capacidad liberada con realized profit;
   - Source Ledger realized profit + Compound realized profit como cantidades aditivas.

---

# 2. ESTADO ACTUAL DEL CI

En el HEAD `2b13c439...` GitHub había creado **23 workflows**, todos todavía
`queued` al congelar este handoff.

Entre los gates B relevantes están:

- QORE CIBO T02 Forward Structural OOS
- QORE CIBO T20 Capital Release Evidence
- QORE CIBO cTrader DEMO Account Capability
- QORE CIBO cTrader DEMO Provider Economics Calibration
- QORE CIBO B Provider Forward Tool Readiness
- QORE CIBO Architect B Forward Economic Manifest
- QORE CIBO Integrated Capital Forward Binding
- QORE CIBO Calibration Freeze Manifest
- QORE CIBO Pre-Holdout Checkpoint
- QORE CIBO USD60 Pre-Exam Readiness
- QORE CIBO Risk Integration Closure
- QORE CIBO CMA Compound Authority Boundary
- QORE CIBO Legacy Stack Quarantine
- QORE CIBO Zero Open Work Gate

**Primer trabajo del siguiente B:** revalidar este HEAD exacto y reparar cualquier
workflow B rojo antes de continuar agregando superficie.

No asumir GREEN por implementación local. No promover workstreams con CI pendiente.

---

# 3. TRABAJOS B QUE YA ESTÁN MECÁNICAMENTE CERRADOS

## T01 — Minimal Seed

Estado B:

`MECHANICAL_CLOSURE_PROVEN`

Ya existe:

- Trader opportunity volume-free;
- CIBO crea minimum executable seed;
- CIBO crea el `CiboRiskRequest`;
- `strategy_requested_risk_usd=None`;
- Trader no recupera sizing authority.

Referencia principal:

- `docs/research/CIBO-ARCH-B-T01-MINIMAL-SEED-MECHANICAL-CLOSURE-V1.md`

Recomendación para A/Integrador después de CI:

`COMPLETED_AND_PROVEN`.

## RISK_INTEGRATION

Estado B:

`MECHANICAL_AUTHORITY_AND_DOWNSIZE_CLOSURE_PROVEN`

La suite demuestra:

- mínimo válido → Risk `ALLOW`;
- CIBO pide demasiado → Risk `REDUCE`;
- sólo si ni el mínimo cabe → Risk `REJECT`.

No debilitar este comportamiento.

## CMA_FOUNDATION_INTEGRATION

Estado B:

`MECHANICAL_AUTHORITY_ACCOUNTING_BOUNDARY_PROVEN`

Frontera:

```text
Trader opportunity
→ CIBO sizing
→ Risk ALLOW/REDUCE/REJECT
→ Execution
→ CMA settlement
→ Compound únicamente después de realización
```

## LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK

Estado B:

`QUARANTINED_CURRENT_RUNTIME_DECOUPLED`

El legacy stack puede existir para research/history, pero no puede recuperar autoridad
productiva ni introducir imports actuales no gobernados.

---

# 4. TRABAJOS B PENDIENTES — PRIORIDAD DE EJECUCIÓN

## PRIORIDAD 1 — CERRAR CI DEL HEAD ACTUAL

Revalidar #661 y los 23 workflows.

Si aparece rojo:

1. leer log exacto;
2. corregir causa raíz;
3. no bajar el gate;
4. no falsificar evidencia;
5. volver a validar sobre el nuevo HEAD.

Especial atención a:

- provider economics;
- T02;
- T11;
- T20;
- integrated capital binding;
- calibration freeze;
- pre-holdout checkpoint;
- USD60;
- manifest B;
- cTrader capability.

---

## PRIORIDAD 2 — PROVIDER_ECONOMICS + EMPIRICAL EXECUTION MODEL

### Ya construido

Existe evidencia cTrader DEMO real point-in-time:

`docs/research/CIBO-B-CTRADER-DEMO-PROVIDER-ECONOMICS-EVIDENCE-2026-09-30.json`

Esa evidencia:

- fue observada vía cTrader DEMO read-only;
- cubre AUDJPY, EURUSD, GBPJPY, GBPUSD, NAS100 y XAUUSD;
- congela términos actuales;
- no afirma términos históricos 2017;
- no muta broker;
- no usa holdout;
- no es target-aware.

También existen:

- `cibo_ce2i_provider_economics_component_freeze.py`
- `cibo_ce2i_provider_execution_calibration.py`
- `scripts/cibo_phase20_provider_execution_calibration.py`

La calibración de ejecución usa:

```text
pre-decision provider quote
→ reconciled weighted real fill
→ signed slippage
→ adverse slippage
→ USD/volume slippage
→ decision→fill latency
→ fill→risk reconciliation latency
```

### Falta cerrar

1. Ejecutar la calibración sobre la **población Phase20D real**.
2. Alcanzar cobertura real suficiente por símbolos.
3. Congelar el SHA de esa calibración.
4. Promover:
   - `empirical_slippage_frozen=true`
   - `execution_model_frozen=true`
   únicamente cuando el gate real lo demuestre.
5. Reemitir provider component freeze ya sin:
   - `EMPIRICAL_SLIPPAGE_NOT_FROZEN`
   - `EXECUTION_MODEL_NOT_FROZEN`.

No proyectar esos resultados al holdout 2017.

---

## PRIORIDAD 3 — T11 EXECUTION COST / EFFICIENCY

### Ya construido

T11 ya tiene:

- provider pre-decision cost binding;
- executed-risk population;
- realized slippage population;
- provider fill calibration;
- nueva calibración lineal por símbolo:
  `cibo_ce2i_t11_execution_cost_calibration.py`.

El coste lineal observado se define como:

```text
p95 quoted spread cost / volume
+ p95 commission cost / volume
+ p95 adverse realized slippage cost / volume
```

### Falta cerrar

T11 sigue fail-closed porque todavía debe resolver:

- `T11_GROSS_EDGE_MODEL_NOT_IDENTIFIED`
- `T11_MARKET_IMPACT_MODEL_NOT_IDENTIFIED`
- población real de ejecución suficiente;
- causal marginal utility de desplegar exposición adicional después de costes;
- decisión terminal T11 bajo fresh OOS.

No convertir el modelo lineal en `t11_policy_ready=true` mientras falten edge/impact.

---

## PRIORIDAD 4 — T02 STRUCTURAL LEVERAGE OOS

### Ya construido

Existe:

- burned calibration previa;
- `cibo_ce2i_t02_terminal_reason_evidence.py`;
- `cibo_ce2i_phase20_t02_structural_oos.py`;
- tests/workflow/documentación.

Regla crítica ya implementada:

**PnL negativo != structural stop.**

La clasificación debe venir de terminal-reason evidence explícita y typed.

### Falta cerrar

1. Acumular terminal-reason evidence real post-freeze.
2. Cumplir el mínimo de outcomes fresh por lineage definido por T02.
3. Demostrar mejora de stop incidence en fresh OOS.
4. Demostrar que p95 loss no empeora.
5. Después ejecutar el provider-bound leverage economic ablation.
6. Sólo entonces proponer terminalización de T02.

No usar 2017H1 para este trabajo.

---

## PRIORIDAD 5 — T03 MARGIN EFFICIENCY

### Ya construido

Existe `cibo_ce2i_phase20_t03_margin_population.py`.

Prueba términos actuales de margin/provider observados antes de decisión.

### Falta cerrar

1. Completar población frozen forward real.
2. Identificar expresiones económicamente equivalentes dentro del universo real del
   provider.
3. Medir si alguna reduce margin sin cambiar el riesgo económico de forma ilegítima.
4. Realizar causal equivalent-expression economic utility.
5. Si no existe alternativa real, cerrar T03 por resultado empírico/falsificación,
   no dejarlo eternamente OPEN y no inventar instrumentos.

---

## PRIORIDAD 6 — T16 / T17 PROVIDER CAPABILITY

### Ya construido

Existe:

- account capability probe read-only;
- account mode HEDGED/NETTED/UNKNOWN;
- symbol catalog hash;
- fail-closed capability registry;
- no-promoción automática.

### Falta T16

Necesita evidencia real de:

- hedge instrument;
- basis risk;
- coste;
- correlación;
- execution feasibility;
- fresh OOS hedge utility.

Si el provider no ofrece un hedge económico válido, cerrar la hipótesis correctamente;
no confundir HEDGED account mode con T16.

### Falta T17

Necesita provider-verified instrument class para:

- option;
- defined-risk spread;
- o estructura equivalente realmente soportada.

Un símbolo llamado “OPTION” no sirve como evidencia.

Si el catálogo real no soporta la estructura T17, cerrar/falsificar según gobernanza;
no inventar capacidad.

---

## PRIORIDAD 7 — T20 CAPITAL RELEASE

### Ya construido

Existe cadena:

```text
CIBO requested capacity
→ Risk authorized capacity
→ actually executed capacity
→ partial authoritative release
→ terminal settlement
→ terminal full release
```

Con:

- hash chain;
- generation CAS;
- restart validation;
- stop-risk reconciliation;
- margin capacity reconciliation.

### Falta cerrar

Acumular población forward real donde los eventos de release sean provider/Execution
authoritative.

No inferir release sólo porque apareció un terminal close.

T20 debe reconciliar exactamente:

- executed risk;
- executed margin;
- partial releases;
- final release;
- settlement;
- timestamps;
- capital minutes.

---

## PRIORIDAD 8 — FORWARD_QUALIFICATION / PHASE20D

### Ya construido

Existe manifest B→A:

- `cibo_arch_b_forward_economic_manifest.py`
- exporter durable-store:
  `scripts/cibo_phase20_arch_b_forward_economic_manifest.py`.

El manifest ahora se endureció para que no pueda declararse scientific-ready
manualmente con población insuficiente.

### Umbrales congelados

Debe cumplir como mínimo:

- ≥80 decision epochs;
- ≥200 candidate outcomes;
- ≥60 selected outcomes;
- ≥28 calendar days;
- ≥20 trading days;
- ≥7 lineages;
- ≥8 outcomes por lineage;
- 4 contiguous folds;
- candidate outcome coverage ≥95%;
- selected coverage 100%;
- baseline-selected coverage 100%;
- pre-freeze decisions = 0.

### Falta cerrar

La población real debe alcanzar todos esos umbrales.

No sustituir datos reales por fixtures.
Fixtures sólo prueban mecánica del gate.

Cuando se alcance:

1. exportar manifest real;
2. verificar SHA;
3. correr provider execution calibration real;
4. correr T02/T03/T11/T20 real population gates;
5. entregar el paquete a A.

---

## PRIORIDAD 9 — INTEGRATED_CAPITAL_TRUTH

### Ya construido

Existe:

- five-store capital truth;
- source ledger;
- transaction store;
- scope store;
- recovery;
- component adapter;
- nuevo `cibo_integrated_capital_forward_binding.py`;
- workflow `QORE CIBO Integrated Capital Forward Binding`.

El forward binding exige igualdad exacta entre:

```text
manifest terminal settlement tuples
==
Compound Cycle settlement population
```

y después exige Source Ledger ↔ Compound admission equivalence.

### Falta cerrar

1. Ejecutar contra la población cronológica real.
2. Crear/bindear source IDs reales; **no inventarlos**.
3. Reconciliar cada positive realized settlement con su admission lot GEN-C.
4. Demostrar aggregate realized profit equality.
5. Demostrar zero double counting.
6. Demostrar recovery/restart con esa misma población.
7. Sólo entonces marcar scientific consumption readiness.

Capacidad liberada T20 no es realized profit.

---

## PRIORIDAD 10 — FRESH_OOS / CALIBRATION FREEZE / PRE-HOLDOUT

### Ya construido

Existe:

- dynamic calibration freeze manifest;
- workflow `QORE CIBO Calibration Freeze Manifest`;
- dynamic bridge al pre-holdout gate;
- workflow `QORE CIBO Pre-Holdout Checkpoint`.

El historical calibration matrix queda como provenance inmutable.

El terminal manifest puede superseder blockers históricos sólo si está sellado y
binds exactamente:

- Phase20D forward manifest SHA;
- provider economics freeze SHA;
- T01..T20 terminal evidence refs.

### Falta cerrar

1. Terminalizar los tools B pendientes.
2. Recibir los terminal evidence refs de los tools propiedad A.
3. Construir exactamente T01..T20 en orden canónico.
4. T16/T17 sólo pueden quedar disabled si existe provider-bound evidence explícita.
5. Sellar calibration freeze manifest real.
6. Demostrar Phase20D causal gate PASS.
7. Recibir/validar Phase21 policy freeze sealed.
8. Ejecutar pre-holdout checkpoint real.

El gate puede llegar a `READY_TO_UNSEAL_2017H1` sólo después de todo lo anterior.

**No abrir 2017H1 antes.**

---

## PRIORIDAD 11 — USD60_CAPABILITY_PROGRAM

### Ya construido

Existe:

- robust target-free USD60 capacity;
- frozen six-month experiment protocol;
- pre-exam readiness gate;
- holdout registry sealed.

### Falta cerrar

Antes del examen:

- forward manifest scientific-ready;
- provider economics freeze final;
- Integrated Capital Truth real population binding;
- T01..T20 terminal readiness;
- Fresh OOS / Phase21 validations;
- Phase21 policy freeze;
- holdout todavía untouched.

Después, y sólo mediante autoridad de holdout:

- ejecutar el six-month USD60 exam;
- registrar resultado sin retuning;
- si falla, no reabrir el mismo holdout para adaptar política.

El pre-exam gate **nunca** otorga por sí mismo:
- holdout access;
- certification;
- LIVE;
- production;
- real capital.

---

# 5. ZERO OPEN WORK / FRONTERA CON A

Arquitecto B no debe modificar el classifier final de A sólo para ponerse GREEN.

Existe:

`docs/research/CIBO-ARCH-B-CROSSBOUNDARY-REQUEST-002.md`

A/Integrador debe clasificar todas las superficies B bajo sus workstreams correctos.

Cuando aparezcan nuevas superficies B, actualizar el request B→A; no apropiarse del
gate de A.

El Zero Open final sólo puede quedar GREEN cuando A+B+Integrador hayan reconciliado
todos los workstreams reales.

---

# 6. LO QUE NO DEBE HACER EL SIGUIENTE B

No debe:

- empezar otra arquitectura paralela;
- duplicar engines ya existentes;
- tocar GEN-C de A para “ayudar” sin frontera;
- bajar thresholds porque falta población;
- marcar `COMPLETED_AND_PROVEN` para quitar rojos;
- usar fixtures como evidencia empírica;
- abrir 2017H1;
- proyectar provider economics 2026 a 2017;
- inferir slippage desde PnL;
- inferir T02 stop desde pérdida;
- inferir T16/T17 por nombres;
- tratar floating PnL como realized capital;
- sumar Source Ledger + Compound cuando representan el mismo profit;
- ejecutar broker mutations;
- tocar VPS.

---

# 7. ORDEN DE TRABAJO RECOMENDADO — SIN DETENERSE

El siguiente B debe trabajar continuamente en este orden:

```text
1. Revalidar HEAD + CI #661
2. Reparar cualquier workflow B rojo
3. Provider execution calibration real
4. T11 empirical execution-cost closure
5. T02 terminal-reason fresh population + ablation
6. T03 forward margin/equivalent-expression closure
7. T16/T17 account/provider capability closure
8. T20 real release population closure
9. Phase20D full real population qualification
10. Integrated Capital Truth real chronological binding
11. Seal B terminal evidence package
12. Build/validate Calibration Freeze Manifest with A evidence
13. Pre-Holdout Checkpoint
14. USD60 Pre-Exam Readiness
15. Handoff final B → Integrador/A
```

Si un paso queda temporalmente bloqueado por acumulación de población forward, **no
detenerse**: avanzar simultáneamente en los demás workstreams B que no requieran esa
evidencia.

---

# 8. CRITERIO DE “B TERMINADO”

Arquitecto B sólo está terminado cuando:

1. todos los workflows B del HEAD terminal están GREEN;
2. T01/T02/T03/T11/T16/T17/T20 tienen disposición terminal defendible;
3. provider economics está congelado con ejecución empírica cuando corresponda;
4. forward qualification alcanzó thresholds reales;
5. Integrated Capital Truth está bound a la población real;
6. Fresh OOS / calibration freeze B están listos;
7. USD60 pre-exam prerequisites B están completos;
8. no quedan archivos B huérfanos;
9. A/Integrador recibieron manifest + evidence refs + SHAs;
10. el holdout continúa sellado hasta la autoridad correcta;
11. no existe trabajo B “suelto” fuera del master ledger/reconciliation package.

**No confundir “infraestructura implementada” con “workstream certificado”.**

---

# 9. ESTADO DE CERTIFICACIÓN EN ESTE CHECKPOINT

CIBO **NO está certificado** por este handoff.

Arquitecto B ha reducido gran parte del problema desde arquitectura pendiente hacia
**evidencia real pendiente**. Los principales bloqueos restantes son:

- población Phase20D real;
- empirical execution/slippage final;
- T02 structural-terminal population;
- T03 equivalent-expression evidence;
- T11 gross-edge + market-impact causal closure;
- T16/T17 provider capability/utility;
- T20 authoritative release population;
- Integrated Capital Truth real chronology;
- terminal T01..T20 calibration freeze;
- Phase21 freeze;
- USD60 governed exam.

El siguiente Arquitecto B debe empezar por GitHub, revalidar el HEAD real y **seguir
trabajando sin detenerse hasta cerrar todo lo que corresponda a B**.
