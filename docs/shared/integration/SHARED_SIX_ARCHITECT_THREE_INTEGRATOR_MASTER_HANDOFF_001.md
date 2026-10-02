# QORE CORE — SHARED HANDOFF MAESTRO DE REORGANIZACIÓN 6×3

**Fecha:** 2026-10-02  
**Owner:** Sergio Meza  
**Repositorio fuente de verdad:** `mezas3238-hue/qore-core`  
**PR soberano Shared:** #635 — DRAFT / UNMERGED  
**Master Shared observado al preparar este handoff:** `519447cb70e01702b76fc0520efee9a6839ce6d4`  
**Architect B observado:** `fbf40f35f2c662dbe55930e59ac4dab4937f5b6a`

> Este SHA es checkpoint, no un freeze. Cada arquitecto e integrador DEBE revalidar HEAD antes de trabajar.

## 1. Topología Owner-frozen

La arquitectura humana de Shared queda reorganizada así:

- **Arquitecto 1** — carril A / WP + MC cognitivo.
- **Arquitecto 2** — carril A / Shared↔Trader Intelligence (STI).
- **Arquitecto 3** — carril A / transversales + costura A↔B.
- **Arquitecto 4** — carril B, ownership interno definido por el handoff soberano de Architect B.
- **Arquitecto 5** — carril B, ownership interno definido por Architect B.
- **Arquitecto 6** — carril B, ownership interno definido por Architect B.

Integración:

- **Integrador 1 = Arquitecto 1 + Arquitecto 2**
- **Integrador 2 = Arquitecto 3 + Arquitecto 4**
- **Integrador 3 = Arquitecto 5 + Arquitecto 6**

Esta topología es una frontera de ownership. Nadie duplica trabajo de otro carril.

## 2. Leyes que no cambian

- GitHub es la fuente de verdad.
- PR #635 permanece DRAFT y UNMERGED salvo orden expresa del Owner.
- NO LIVE, NO producción, NO capital real, NO VPS.
- NO sizing, NO BUY/SELL authority, NO Risk authority, NO CIBO authority, NO broker mutation.
- NO abrir el holdout final Shared.
- NO outcome-aware tuning.
- CI GREEN no equivale a capability closure.
- Evidencia parcial no puede promoverse a COMPLETED_AND_PROVEN.
- Final Shared freeze y certificación sólo pueden ocurrir después de STRICT ZERO OPEN + pre-certification audit + autorización Owner.
- Shared observa y razona; Traders operan; CIBO capitaliza; Risk protege; Execution materializa.

## 3. Estado canónico ya cerrado — NO REABRIR

Según el master ledger actual, estos work IDs ya están terminales y no deben reconstruirse salvo regresión demostrada:

### WP cerrados
`WP-01 WP-02 WP-03 WP-04`

### MC cerrados
`MC-02 MC-03 MC-04 MC-06 MC-07 MC-09 MC-10 MC-15 MC-20 MC-21 MC-22`

### STI cerrado
`STI-13`

### Transversales cerrados
`X-04 X-11 X-13 X-17 X-18 X-19`

Architect B mantiene su propio ledger B-01..B-24 y hará su propia división soberana para Arquitectos 4/5/6.

## 4. División exacta del carril A

### Arquitecto 1 — WP + MC Cognitive Core

Ownership exclusivo de los abiertos:

**WP:**  
`WP-05 WP-06 WP-07 WP-08 WP-09 WP-10 WP-11 WP-12`

**MC:**  
`MC-01 MC-05 MC-08 MC-11 MC-12 MC-13 MC-14 MC-16 MC-17 MC-18 MC-19 MC-23 MC-24 MC-25 MC-26 MC-27`

No posee MC-28.

Objetivo: llevar cada capability a terminalidad científica real bajo Standard 006, con especial prioridad a:
1. reconciliar evidencia ya existente que sólo necesita closure audit;
2. cerrar MC-18 Counterfactual World;
3. cerrar MC-23 Meta-Learning;
4. desbloquear MC-26 Cognitive Arbitration;
5. completar WP-05..12 sin abrir holdout final.

### Arquitecto 2 — Shared↔Trader Intelligence

Ownership exclusivo:

`STI-0 STI-1 STI-2 STI-3 STI-4 STI-5 STI-6 STI-7 STI-8 STI-9 STI-10 STI-11 STI-12 STI-14 STI-15 STI-16`

`STI-13` está cerrado: no reabrir.

Prioridades:
1. closure audits donde ya existe evidencia verde;
2. reparar STI-5/STI-6 sin outcome-aware tuning;
3. completar causal replay / attribution / OOS / stress / temporal replication;
4. probar winner preservation, false/missed alerts y governed productive admission;
5. mantener Shared como cognition-only.

### Arquitecto 3 — Transversal + Cross-Lane Seam

Ownership exclusivo:

`MC-28`

Transversales abiertos de construcción:
`X-01 X-02 X-03 X-05 X-06 X-07 X-08 X-09 X-10 X-12 X-14 X-15 X-16`

Arquitecto 3 NO posee `X-20 X-21 X-22`; esos tres son gates finales de integración.

Prioridad de costura con B:
1. `MC-28` Core/Broker Cognition + Blindspot closure;
2. `X-14` global economic/market clock;
3. `X-15` data health;
4. `X-16` freshness/decay;
5. `X-12` second-order blindspot;
6. cross-market / lead-lag / latent factor / contradiction facts;
7. opportunity and journey transversals.

Architect 3 sólo consume hechos B que estén versionados, causales, timestamp-safe, provenance-bound y authority-free.

## 5. Gates finales reservados a integración

Los siguientes IDs NO pueden ser cerrados unilateralmente por Arquitecto 1/2/3/4/5/6:

- `X-20` Maximum Pre-Certification Audit
- `X-21` Final Shared Freeze
- `X-22` Seven-Trader Two-Year Certification Protocol

Ownership: **Consejo de Integradores 1+2+3**, con Owner como autoridad final.

## 6. Integrador 1 — Arquitectos 1 + 2

Integrador 1 tiene tres verbos obligatorios:

**INTEGRAR · REPARAR · AVANZAR**

No es un simple cherry-picker.

Responsabilidades:
- intake continuo de A1 y A2;
- revalidar HEAD master antes de cada slice;
- integrar sólo slices terminales o explícitamente gobernados;
- reparar incompatibilidades, typing, schemas, tests, workflows y regresiones;
- ejecutar master regression después de cada integración;
- reconciliar `shared_zero_open_work.py` con evidencia real;
- hacer closure audits cuando la evidencia ya existe y falta reconciliación;
- ayudar a A1/A2 en trabajo transversal dentro de sus carriles;
- no integrar Arquitecto 3;
- no abrir holdout final;
- no fusionar PR #635.

## 7. Integrador 2 — costura Arquitecto 3 + Arquitecto 4

Integrador 2 es el único lugar donde se reconcilian A3 y B4.

Arquitecto 4 será definido internamente por el handoff de Architect B. Este documento NO roba ownership B.

Contrato de entrada esperado desde Architect 4:
- provider-neutral identity / explicit UNKNOWN;
- temporal/calendar semantics;
- data-health/freshness semantics;
- relational eligibility;
- provenance/replay lineage;
- no trader logic;
- no execution or sizing authority.

Contrato de salida desde Architect 3:
- factual cross-market/transversal cognition;
- trader-consumable support facts sin metodología;
- timestamps <= decision time;
- uncertainty/UNKNOWN/ABSTAIN preserved;
- no hidden trade filter.

Integrador 2 debe reparar incompatibilidades de interfaces y avanzar la costura, no duplicar internals de A3/B4.

## 8. Integrador 3

Integrador 3 trabaja exclusivamente con Arquitectos 5 + 6 según el handoff futuro de Architect B.

No debe tocar A1/A2/A3 ni la costura A3+B4 salvo bug cross-boundary demostrado.

## 9. Branches recomendados

- `agent/shared-architect-1-cognitive-core-001`
- `agent/shared-architect-2-sti-001`
- `agent/shared-architect-3-transversal-seam-001`
- `agent/shared-integrator-1-a1-a2-001`
- `agent/shared-integrator-2-a3-b4-001`
- Architect B definirá A4/A5/A6 e Integrator 3.

## 10. Definition of Done por slice

Un slice es integrable sólo si:
- contract + implementation + tests están coherentes;
- CI del slice está GREEN;
- evidencia real requerida existe;
- provenance/hash/run/artifact están enlazados;
- anti-leakage PASS;
- no authority leakage;
- blockers restantes están explícitos;
- no se declara terminalidad por arquitectura sola.

## 11. Orden de arranque

1. Crear/revalidar branches desde el HEAD Shared actual.
2. A1 y A2 trabajan en paralelo.
3. Integrador 1 absorbe continuamente A1/A2.
4. A3 trabaja en paralelo pero NO entra en Integrador 1.
5. Architect B publica handoff A4/A5/A6.
6. Integrador 2 absorbe A3 + A4.
7. Integrador 3 absorbe A5 + A6.
8. Los tres integradores convergen sólo en master mediante slices pequeños, revalidados y sin merge final.
9. Cuando STRICT ZERO OPEN sea real, preparar pre-certification; no abrir holdout sin orden Owner.
