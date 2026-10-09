# QORE CIBO P0 — Trader Lab 3,368 Native MAX + QDLE: resultados, diagnóstico y continuación postfill

**Fecha:** 2026-10-09  
**Repositorio:** `mezas3238-hue/qore-core`  
**Feature branch:** `agent/cibo-p0-replay-qdle-persistence-20261009`  
**PR:** https://github.com/mezas3238-hue/qore-core/pull/747 (**DRAFT / NO LIVE**)  
**Integrador:** PR #745

## 1. EVIDENCIA REPLAY COMPLETO, SIN RECICLAR EL ANTERIOR

- GitHub Actions [Trader Lab #37957631672](https://github.com/mezas3238-hue/qore-core/actions/runs/37957631672) — **SUCCESS**
- SHA exacto: `fb400ac27c4139c3446de33c8fa25e4d747ee970`
- Artefacto único: [#11630019202](https://github.com/mezas3238-hue/qore-core/actions/runs/37957631672/artifacts/11630019202)
- Auditoría retrospectiva del artefacto **sin reejecutar el mercado ni retocar ninguna decisión**: [#37975507006](https://github.com/mezas3238-hue/qore-core/actions/runs/37975507006) — **SUCCESS**.

### Alcance cognitivo, económico y físico

| Medida auditada | Valor |
| --- | ---: |
| Señales originales del manifiesto SHA-sellado | 3.368 |
| Consultas CF01–CF19 y episodios Native MAX **recomputados** | 3.368 |
| Fallos de reconstrucción Native MAX | 0 |
| Solicitudes registradas por QDLE persistente | 3.368 |
| Evaluaciones con cuatro motores completos | 3.344 |
| Votos formales de motores emitidos | 13.376 |
| Oportunidades sin cotización financiera válida | 24: 20 geometría, 4 Atlas M5 |
| Volumen físico cero de QDLE | 3.098 |
| Operaciones PAPER hipotéticas abiertas | 246 |
| Operaciones PAPER hipotéticas cerradas | 246 |
| PAPER abiertas sin ruta de cierre | 0 |

No afirmar 4 motores en cada una de las 24 oportunidades *sin cotización*;
los votos declarados como aplicables son 13.376, no 13.472.

### Finanzas exclusivamente research PAPER

- Capital PAPER inicial: **$60**
- Caja PAPER residual: **$18,28819135577912932542614806**
- Pérdida neta hipotética de cierres: **−$41,71180864422087067457385194**
- Profit factor cerrado hipotético: **0,6212241152145416819042741769**
- Win rate de los 246 cierres: **35,772357723577%**
- Máximo drawdown **sobre caja cerrada**, NO equity-MTM: **75,727443444526%**
- Drawdown portfolio intratrade real: **NO MEDIDO**
- Broker fills autenticados: **0**
- Bid/ask históricas 2019–2022 auténticas: **NO**, se usaron
  offsets de spread constante de screenshots 2026 en Atlas OHLC.
- Sin estrategia certificada, sin órdenes reales.

### La causa del 92% de BANK quedó delimitada, no plenamente explicada

| Modo elegido por episodio Native MAX | Recibidas | Abiertas | Sin lote | Sin precio |
| --- | ---: | ---: | ---: | ---: |
| BANK | 3.086 | 67 | 2.996 | 23 |
| MEDIUM | 233 | 131 | 101 | 1 |
| ATTACK | 49 | 48 | 1 | 0 |

- Native MAX emite `BANK=1,25%`, `MEDIUM=2,5%`, `ATTACK=5%` NAV máximo
  solicitado, aunque QDLE mantiene techo absoluto soberano 5%.
- En una caja inicial de $60, BANK propone **$0,75** de riesgo.
- De los 3.098 `QDLE_NO_FINANCEABLE_LOT`, **3.097** declaran
  `REQUESTED_USD` como limitación vinculante, no un bloqueo financiero
  misterioso. Hay 1 caso principalmente de margen/leverage.
- Motivos individuales de BANK (forecast frío, provisional, utilidad esperada
  no positiva, abstención epistémica, drawdown) **NO pueden inferirse solo de
  la etiqueta BANK**. No imputar a una causa sin el receipt de calibración.

Los nuevos cambios de instrumentación agregan a cada receipt:
`native_calibration_confidence`, `native_abstention_required`,
`native_calibration_note`, `native_reasoning_route`,
`native_decision_gate_codes` y mínimos de riesgo para 0,01 lotes
(stop+comisión) comparados con el presupuesto nativo. Esto NO altera
volúmenes ni resultados económicos, solo aporta explicación causal.
Nuevo replay con instrumentación: verificar la ejecución que corresponda
al commit más reciente, **no mezclar resultados con el run anterior**.

### Atribución de pérdidas PAPER sobre cierres

Por modo: BANK **−$9,7130**, MEDIUM **−$25,1390**,
ATTACK **−$6,8598**.

Por mercado: AUDJPY **−$7,9900**, EURUSD **−$4,1250**,
GBPJPY **−$8,6949**, GBPUSD **−$5,4800**,
NDX100 **−$9,4925**, XAUUSD **−$5,9294**.

Motivo de salida: 112 `STOP_FIRST_OR_SL_ONLY`,
60 `DEFENSIVE_CLOSE_NEXT_OPEN`, 67 `TAKE_PROFIT`,
7 `GAP_OPEN_STOP`.

Esto señala el siguiente riesgo: **el contrato de salida BANK/MEDIUM/ATTACK
continúa aplicando plantillas sin ejecutar una deliberación Native MAX
nueva a lo largo de la posición**.

## 2. P0 postfill: código nuevo, alcance probado y límite actual

Se implementó en
`src/qore/infrastructure/cibo_managed_exit_replay.py`:

- `CiboPositionCloseObservation`: solo datos de vela cerrada, lotes,
  stop vigente, dirección, precio executable y R observado.
- `CiboCognitivePostfillAction`: contrato tipado
  `HOLD` / `EXIT_NEXT_OPEN` / `PARTIAL_NEXT_OPEN` /
  `TIGHTEN_STOP_NEXT_OPEN`, timestamp y digest Native MAX.
- `replay_cibo_managed_position(..., postfill_decider=...)`: invoca el
  callback cognitivo **al cierre**, registra su evidencia y aplica acciones
  **únicamente en la apertura siguiente**. Nunca ensancha SL, nunca omite
  requisitos del min-lot y nunca inventa fills. Si callback falla, la
  simulación no sustituye la cognitiva por la plantilla vieja.

Se implementó en `scripts/cibo_p0_native_postfill_director.py`:

- `CiboNativeMaxPostfillResearchDirector`: invoca de nuevo CF01–CF19
  y `run_native_maximum_intelligence` en el cierre causal usando
  datos actuales de posición + `ResearchAccountAtClose`.
- Emite orden de gestión en función del episodio reciente, R observado
  y margen/riesgo actuales; se trata de un **mapeo de investigación
  todavía heurístico**, NO de una estrategia autónoma certificada.
- Pruebas unitarias con Native MAX *verdadero*, bid/ask OHLC, acción a
  siguiente apertura, rechazo de timestamp inválido, rechazo de ampliación
  de stop, ausencia de fallback y ausencia de ejecución LIVE.
- [CI PAPER #37976190466](https://github.com/mezas3238-hue/qore-core/actions/runs/37976190466): **SUCCESS**,
  incluido el recorrido real Native MAX -> contrato postfill ->
  replay aislado de una posición.

**NOTA:** el run completo #37957631672 **no utilizó todavía**
`postfill_decider`: sus salidas se produjeron bajo las antiguas
plantillas. El gestor nuevo se ha validado como microreplay y está preparado
para conectarse a una agenda global multi-activo: NO afirmar 246 salidas
cognitivas sin ese cableado.

## 3. Bloqueos para la siguiente integración

1. **Agenda UTC única:** cada vela M5, llamada de Native MAX y saldo QORE
   debe ocurrir tras los eventos de apertura/cierre anteriores y antes
   de otras señales posteriores; el replay actual precalcula ruta futura
   por operación para agendar settlement, que no es gestión global auténtica.
2. **Postfill portfolio-causal:** alimentar el director por cada oportunidad
   con riesgo/reservas/caja/equity actualizado de QDLE; jamás con una
   instantánea aislada de cuenta inventada.
3. **DD MTM:** contabilizar flotante y stops de TODOS los activos, no solo
   caja cerrada. Reconocer gaps, costes, broker-floors y cierres pendientes.
4. **Inspeccionar nueva telemetría:** separar 3.086 BANK por causas
   cognitivas. No forzar 0,01 lotes ni 5% en entradas donde el riesgo
   all-in real excede el presupuesto. Si se evalúa una política alternativa,
   ejecutar en brazo de investigación A/B en el mismo corpus.
5. **No haircut heredado:** `THREE_SETTLED_LOSSES_HAIR_CUT` eliminado
   del código canónico de CIBO Compuesto; jamás reintroducirlo en merge.

**VPS, MT5 LIVE, broker order_send no se han tocado.** PR #747 sigue
DRAFT / NO LIVE, integrador #745 debe mantener esa condición hasta
validación científica.
