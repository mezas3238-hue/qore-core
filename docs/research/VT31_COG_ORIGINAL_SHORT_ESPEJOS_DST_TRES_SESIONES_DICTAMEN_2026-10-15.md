# VT31 — COG ORIGINAL SHORT: EST/EDT, tres sesiones y fallo de perfil TTrades

2026-10-15 · Orden Owner: CERTIFICACIÓN METODOLOGÍA + COGNITIVA, no PF, DD, Sharpe, Sortino ni ganancias. Esta ronda ejecuta el motor original `VT31CleanroomCognition` en M1 sintetizadas con fuentes completas, y entrega comportamientos razonados, contrafactuales y causas. El laboratorio no firma autoridad de trading.

## QA y evidencia reproducible
- PR #955 DRAFT https://github.com/mezas3238-hue/qore-core/pull/955; prereg antes del código commit `93d1bf72403e49cf56b3f290e149038215420709`.
- [CI #38708707140 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38708707140) SHA código/test **`666c419841525e3e70384cf11a49dadd3c6dc06c`**, **46/46 pytest** PASS, Ruff y Python compile PASS, 3 blobs G3 originales intactos.
- [Artifact #11960185549](https://github.com/mezas3238-hue/qore-core/actions/runs/38708707140/artifacts/11960185549) ZIP sha256 `0b32d306a86e50e924ab3a29d2f6b5dffe1242d383aff3970728b45552acafde`, JSON íntegro seis escenarios, JUnit, SHA internals y resumen.
- Primer intento #38708611473 falló antes de ejecutar tests por Ruff E501/B023, corregido solo formato y binding del helper anidado; no se cambió expectativa de COG ni datos fuente.

## Dictamen semántico original (sin PnL)
| Sesión G3 original | EST (enero) | EDT (julio) | DOL QORE |
|---|---|---|---|
| London 03–04 NY | SHORT | SHORT | prior NY cash LOW80 |
| NY AM 10–11 NY | SHORT | SHORT | prior NY cash LOW80 |
| NY PM 14–15 NY | SHORT | SHORT | prior NY cash LOW80 |

En cada uno, LOW confirmado M1 pivote96, vela de desplazamiento real close94, 80 queda 14 puntos debajo; al cambiar ÚNICAMENTE close94→97 se pierde el MSS y COG emite WAIT. Antes del MSS también WAIT. Después de barrer el LOW80 o cerrar encima del pivote96, no persiste el antiguo SHORT con destino80. Después de añadir M1 el sistema REJECT pedir una evaluación retroactiva. Estas respuestas demuestran juicio causal limitado de la lógica implementada y no equivalen a comprensión humana, fidelidad ICT autoral ni economía favorable.

**FALLO DE FIDELIDAD TTRADES NY AM, SHORT, TAMBIÉN en EST y EDT:** en el mismo escenario H1 09–10 HIGH110/LOW90 se barre primero HIGH111, COG confirma SHORT pero su destino DOL actual es LOW80 de cash anterior; el método específico TTrades AM requiere el LOW opuesto del 09h=90. El testigo independiente M1 fuente y V2 rechazan `DOL_NOT_OPPOSITE_9AM_H1_EXTREME`. Esta incompatibilidad SOLO alcanza el perfil TTrades NY AM 2025; Londres y NY PM pertenecen al ICT_GENERAL/QORE y no heredan regla de 09h.

## Estado y siguiente trabajo P0
- Certificado METODOLOGÍA = PENDIENTE por identidad del perfil, regla TTrades DOL, MSS QORE proxy, familias OB/Breaker y swing stop fuente ambigua. Ver PR #950 LONG y #955 SHORT: dos sentidos independientes muestran conflicto TTrades.
- Certificado COGNITIVA = PENDIENTE, pese a los ejemplos correctos LONG/SHORT/WAIT/REJECT en 3 ventanas con causalidad de fuentes. Faltan juicios de fuente autoral con explicaciones trazables, causas conflictivas y casos no sintéticos revisados por terceros.
- Próximo desarrollo científico: **perfil explícito y adaptación doctrinal SOURCE FIRST** en un módulo de investigación adicional de *un solo VT31*, nunca manipular G3 congelado o cambiar su selección DOL implícitamente; prerrregistrar y comparar en M1 cerrada sin elegir por beneficio.
- Firmas duales reales #897 COG/OPS pendientes. Sin MERGE, LIVE, OMS, VPS, FundedNext LIVE, órdenes, sizing propio Trader; CIBO CMA responsable volumen. Trader Lab financiero separado.