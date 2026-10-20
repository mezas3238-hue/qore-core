# VT08 5M P0-A — Auditoría primaria M0 y contrato causal para Arquitecto B

Fecha: 2026-10-10 · Issue [#762](https://github.com/mezas3238-hue/qore-core/issues/762) · Partner [#763](https://github.com/mezas3238-hue/qore-core/issues/763) · PR padre [#634](https://github.com/mezas3238-hue/qore-core/pull/634).

**Estado verificable:** primera pasada fuente↔código + propuesta implementada y comprobaciones adversariales escritas. **No** es auditoría completa frame-by-frame, no replay nuevo, no aumento demostrado de densidad, no cambio de señal, no certificación. Se revisó el blog y PDF publicados en el sitio oficial; el video original descargado y su SHA-256 **no** se revalidaron. Los tiempos de video abajo son **marcadores de transcripción web secundaria**, pendientes de contraste independiente con video/frames.

## 1. Trazabilidad de fuente primaria

- Video oficial del autor: https://youtu.be/FAKWJ-1NlLE
- Artículo oficial de TTrades (20-09-2025): https://ttrades.com/trading-the-4-hour-power-of-3-open-high-low-close-strategy/
- PDF oficial, 14 páginas, especialmente pp. 6–12: https://ttrades.com/wp-content/uploads/2025/09/H4-PO3-TTrades-PDF.pdf
- Marcadores **secundarios, no verificación audiovisual completa**: https://2outube.com/watch?v=FAKWJ-1NlLE (00:35 AMD, 01:01 C2 shallow, 02:33 C3 continuation, 03:13 reversal, 03:38 horarios Forex, 04:54 M15, 05:28 recuperación en rango de ejemplo, 13:06 positional).
- Reconstrucción interna: `docs/research/trader-lab/VT08-R3-2-SOURCE-FREEZE.md`; adjudicación `docs/research/trader-lab/VT08-R3-9-FINAL-SOURCE-CONTRACT.md`.
- Video archivo histórico `1000854868.mp4` y SHA-256 `bfe76...cdf83271` **constan como declarados**, no rehash efectuado aquí.

### Matriz preliminar de fidelidad (no usar PnL para adjudicar)

| rule_id | Autor / evidencia | Código / documento | Clasificación inicial | Diferencia, efecto o decisión |
| --- | --- | --- | --- | --- |
| H4 PO3 OLHC/OHLC | PDF pp. 2–5; blog §PO3 | `vt08_source_kernel_r3_2.py` | SOURCE_EXPLICIT | Secuencia concuerda; pendiente auditoría gráfica de velas individuales. |
| C2 shallow / C3 deep | PDF pp. 6–10; blog §Identifying Candle Types; video secundario 01:01–03:13 | `vt08_b01_r3_8.py:367-377`, `vt08_b01_source_contract_r3_9.py` regla c2-c3-fractal | SOURCE_EXPLICIT cualitativa / SOURCE_INFERRED clasificación numérica | B01 solo C2 completado. C3 es identidad omitida; sin frontera máquina source-grounded. NO sustituir por ATR/pips. |
| C2 close inside previous H4 | Blog §Practical Example (ejemplo específico de retorno a rango); video secundario ~05:28 | `vt08_b01_r3_8.py:375-376`; `vt08_cognitive_expansion_5m_evaluator_v1.py:_candle2_reversal_side` | **UNRESOLVED / QORE_CONTAINMENT candidate** | No se encontró en el artículo/PDF una regla *universal* que obligue a close dentro del rango de C1; el vídeo ilustra retorno dentro en ejemplo. **3.987** first-fail históricos, no 3.987 trades recuperables. Requiere evidencia primaria para adjudicar, NO eliminar todavía. |
| Both-side C2 sweep | Fuente 4H no da resolución mecánica universal | `vt08_b01_source_contract_r3_9.py` regla both-sides-swept; `vt08_cognitive_5m_density_funnel_audit_v1.py:55-58` | UNRESOLVED / QORE_CONTAINMENT | 1.347 primeras exclusiones; mantener abstención hasta prioridad causal con respaldo fuente. |
| Protected swing + CISD | PDF pp. 7–10 diagramas CISD; blog §Using Lower Timeframes | `vt08_b01_r3_8.py:380+`; R3.9 PS | SOURCE_EXPLICIT (principio), SOURCE_INFERRED (detalles algoritmo) | Verificar nivel open, confirmación close-through y PS temporales por frame. No retroautorizar una entrada H4 anterior a la confirmación. |
| PS múltiples | Fuente no resuelve prioridad universal | R3.9 protected-swing-selection, B01 `len(swings)!=1` | QORE_CONTAINMENT / UNRESOLVED | 145 primeras exclusiones; no elegir retrospectivamente PS óptimo. |
| Daily bias / source-day | Blog §Practical Example y §Using LTF, requiere materiales oficiales específicos de PDH/PDL | B01 `resolve_bias`, `source_day_from_m15`; R3.9 daily-bias/source-day | SOURCE_INFERRED / QORE_CONTAINMENT | 2.071 bias unresolved. Cuatro casos y frontera 17→17 NY necesitan auditoría independiente en fuentes detalladas antes de mutar. |
| Timing Forex 13:00 | PDF oficial p. 11 (página PDF index 11): `17/21/01/05/09/13`; blog §LTF enumera 01/05/09 como relevantes | R3.2 SOURCE_COMPLETE `01/05/09/13`; R3.9 `SOURCE_ENTRY_ANCHORS_NY=(1,5,9)` y declara 13 no fuente-entry | **SOURCE_EXPLICIT como H4 timing**, OWNER_POLICY 01/05/09 para trading | **Inconsistencia documental:** 13 aparece en calendario oficial, pero su derecho como *entry* independiente aún necesita separar Timing vs entrada. **No habilitar 13** por inferencia. Owner 01/05/09 sigue vinculante. |
| M15 / M5 / M3 | Blog §Using LTF M15, conclusión recomienda combinaciones fractales 1h/5m y 30m/3m | R3.2 `VT08LtfProfile` | SOURCE_EXPLICIT M15, SOURCE_INFERRED extensiones | M5/M3 H4 independiente requiere ejemplos con fuente y su propio replay, sin fusión retrospectiva. |
| Positional H4 open | PDF pp. 7–10; secondary video ~13:06 | `vt08_cognitive_expansion_5m_evaluator_v1.py` + R3.9 | SOURCE_SUPPORTED / QORE_CONTAINMENT fill exact | Solo PS confirmado `<=` open; fill exacto sin costes es modelo QORE. |
| Entry families 6 | R3.2 fuente testigo: reversal, continuation, confident, positional, open, POI-continuation | `vt08_source_kernel_r3_2.py`; expansion evaluator solo positional | UNRESOLVED en entry/stop/TP de otras 5 | Identidades fuente declaradas; PDF 4H por sí solo no congela cinco bundles. No fills con geometría o retest únicamente. |
| Stop families 5 | R3.2 testigo cinco identidades; fuente 4H PS claro | Kernel R3.2 / B01 PS stop | SOURCE_EXPLICIT PS, UNRESOLVED combinaciones | No producto cartesiano SL por familia; stop offset es contención. |
| TP contextual | Video 4H muestra objetivos variados (secondary ~16:00 -1SD, ~19:48 2R); blog menciona previous day high | B01/expansion `2R` fijo | QORE_CONTAINMENT | El 2R exacto es experimento, no target universal autor. |
| H4 exit filled lifecycle | R3.2 dice cerrar en H4; R3.9 dice fundamentally unresolved | `vt08_b01_source_contract_r3_9.py` regla h4-filled-lifecycle | **SOURCE_CONTRACT_CONFLICT** | Mantener `CLOSE_NEXT_H4_QORE_CONTAINMENT`; adjudicar original antes de cambiar, separar orden pendiente y posición llena. |
| Per-market daily cap | Política explícita Owner, no regla fuente universal | expansion / funnel daily cardinality | OWNER_POLICY | 1 trade filled/mercado/fecha NY, mantener. 30 descartes históricos no justifican retirar. |

## 2. Línea de base verificable (histórica, **no** nueva reproducción)

Artefactos existentes: `VT08_COGNITIVE_EXPANSION_5M_DENSITY_ROOT_CAUSE_AUDIT_V1.md` basado en run `35939376821` y corpus run `35934924907` software SHA `b2d33e1b4829d8b4afc76983decca8a99131403c`.

```text
Observed H4 anchors  = 11,655
First failures       = 3,987 C2 close outside
                     + 2,071 daily bias unresolved
                     + 1,347 both-side C2
                     + 1,317 side/bias mismatch
                     + 1,085 no reference sweep
                     +   769 no Protected Swing
                     +   406 incomplete H4
                     +   145 multiple PS
                     +    40 incomplete source-day
                     = 11,167
Mechanical           = 488
TOTAL                = 11,655
488 candidates       = 457 terminal + 30 daily-cardinality + 1 incomplete exit
```

Por mercado (candidatos→terminal): EURJPY 88→82; USDCHF 88→77 (incluye 1 exit-incomplete); NZDUSD 126→114; CADJPY 88→86; USDCAD 98→98. Estos números están **reconciliados documentalmente**, no regenerados desde M15/M3. Para ejecutar el replay reproducible falta acceso a los 5 archivos raw inmutables del run 35934924907 y su ledger de anclas, más comparación SHA. La clase de descarte C2 más grande **no** autoriza relajación automática.

## 3. Primer artefacto ejecutable de intercambio A→B (propuesta, no freeze)

Nuevo `src/qore/infrastructure/trader_lab/vt08_5m_candidate_event_v1.py`:

- `Vt08CandidateEventV1` congelado, `source_payload()`, huella SHA256 determinística y `envelope()`.
- `from_narrow_b01_candidate()` hace proyección estricta desde el candidato B01 5M ya aprobado **sin alterar entry/SL/TP**.
- Solo reconoce `positional-entry` / `M15_STANDARD` / `C2_COMPLETED` y 5 mercados investigación. Las otras 5 source-entry identities quedan FAIL-CLOSED.
- `h4_anchor_at=decision_at=evidence_as_of`; opposing-series<CISD=PS<=C2 closed=decision; `01/05/09` NY con DST; pending expiry H4+4h; long/short precio/SL/2R; hashes evidencia/metodología obligatorios.
- Todos los cambios no respaldados de entry, stop, TP y H4-lifecycle son rechazados. Esas reglas B01 se etiquetan con honestidad como `QORE_CONTAINMENT`.
- Sin PnL futuro, resultado de trade, score/cognitiva, market authorization, quantity, risk sizing, órdenes live ni permisos ejecutables.
- `tests/infrastructure/trader_lab/test_vt08_5m_candidate_event_v1.py`: golden fixture sintética, verificación DST, 13:00 Owner block, cierre causal, rechazo PS futuro, reject otras familias/perfiles, invalidación, huella, no LIVE.

**Acuerdo pendiente de Arquitecto B #763:** validar nombres/campos/JSON canonicalizado, event-id, reloj de cierre, decisión ABSTAIN/WAIT/EXECUTE independiente y trace mínimo. El adaptador cognitivo NO puede marcar eventos como fills ni modificar su source economics; A no reescribe B. El contrato queda `PROPOSED_AWAITING_ARCHITECT_B_REVIEW` hasta revisión mutua en ambos issues.

## 4. Orden de continuación y bloqueos

1. Fuente primaria visual/audio/framebook y vídeo completo con hash revalidado: ubicar todas las referencias exactas de las seis familias, cinco stops y H4 lifecycle. Consultar otras publicaciones oficiales TTrades con fecha/procedencia si fuese necesario.
2. Ledger por anchor/event de first-failure+all-fail con attribution SOURCE vs OWNER vs QORE, 5 mercados por año y perfil independiente, con SHA de evidencia inmutable.
3. Documentar por separado qué restricciones cambian tras fuente; C3 y familias intracycle: SL/TP/order type/expiry y prioridad source/Owner antes de evaluar economics.
4. B revisar la interfaz; fusionar **solo** contrato aprobado por A/B, sin tocar runtime y sin sealed outcomes. Probar golden fixture con estados cognitivos y no resurrection.
5. Medir executes, fills, terminal, fecha NY única y raw PF/DD de cada pre-registrado en evidencia consumida; fijar umbral numérico de densidad con Owner antes de abrir holdout 7Y.
6. Revisar el `minimum_trades_per_market_2y=50` en freeze `vt08_cognitive_expansion_5m_v1.py`: ahora el Owner lo retiró; la especificación vigente debe reflejar **densidad gate pendiente de aprobación**, evitando que un evaluador lo use como certificación válida. No alterado en esta primera entrega.

**Prohibiciones:** no VPS, producción, DEMO/LIVE, sealed 7Y outcome, reoptimización de holdout, ni presentar tests de código o fixtures sintéticas como trades observados.
