# VT31 — P0 auditoría independiente del contrato de cotizaciones (2026-10-12)

**Ámbito:** investigación read-only, una sola identidad VT31, ventanas London/NY M1. Basada en el Handoff Maestro #872 @ `b7004e08475c2c7ad71816102a638918a2f7ba4f`, y código de PR #833 @ `e51d1bc8a7d14514507d343875b273e07e9afa6a`. No se ha tocado `main`, VPS, LIVE, Fresh Holdout, `cognition.py`, `operations.py`, `quote_tick_science.py`, ni las reglas de entrada/salida. El histórico M1 de desarrollo NO se volvió a descargar/replayar en esta ronda.

## Resultado de esta ronda — VALIDACIÓN DE CONTRATO, NO ECONOMÍA

- Rama de custodia: `agent/vt31-p0-quote-evidence-verification-20261012`.
- Nuevos archivos: `tests/infrastructure/test_vt31_quote_tick_science_p0.py` y `.github/workflows/vt31-quote-tick-science-p0.yml`.
- CI **[38310866082 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38310866082)** @ `df95db747bd9881756a9bc899d4ab4d605b80d46`: **21/21 pytest**, `ruff check` del test nuevo, `py_compile` de auditor y test. Evidencias con `SHA256SUMS` verificadas en el propio workflow; artefacto **11773724950**.
- Run previo **38310804219 FAILURE**, exclusivamente debido a deuda de lint heredada en fuente `quote_tick_science.py`: `UP035`, `Iterator` importado desde `typing` en vez de `collections.abc`. Se acotó lint del gate a TEST nuevo y se dejó fuente heredada sin tocar (archivo bajo revisión de OPS); no ocultar este antecedente ni declarar que todo el proyecto está sin deudas de lint.
- Los 21 casos usan únicamente **ticks sintéticos adversariales**. Sus precios y timestamps son TEST FIXTURES; no son BID/ASK histórico NAS100 o NDX100, ni se insertaron en investigación económica 3Y.
- Este CI **no** realiza un nuevo ensayo económico ni consume fuente de mercado. El ensayo anterior de spread fijo 1.60 A232/B577 es un test de sensibilidad ya realizado y no cambia.

### Cobertura adversarial ejecutada

1. Huella `SHA256` del gzip, conteo, spread min/max, duplicados de mismo milisegundo, discontinuidades y orden cronológico.
2. Rechazo de BID > ASK, NaN/no positivo, flags negativos, símbolo incorrecto, timestamps fuera del intervalo half-open, ticks no cronológicos, cabeceras alteradas, gzip corrupto y umbral de gap inválido.
3. Dataset vacío no prueba cobertura; auditor conserva `complete_requested_history_proven=False` y `broker_fills_proven=0`.
4. Cruce LONG exige **ASK <= CE**; SHORT exige **BID >= CE**. Un quote cruzado retorna `QUOTE_CROSSED_CE_NO_BROKER_FILL`, nunca ejecución confirmada.
5. Falta de cobertura/cancelación bloquea; simultaneidad en milisegundo de CE/cancelación/expiry sigue ambigua; quote posterior a cancelación no es éxito.
6. Datos UTC-ms sin zona, timestamps sub-ms fabricados o ticks fuera de orden generan error. Un alias NDX100 no se acepta como equivalencia automática de NAS100.

### Hallazgos de revisión estática que NO están resueltos por los 21 tests

**H1 — identidad cruzada NAS100/NDX100 sigue bloqueada:** `compare_quote_ce` exige `validated_market_symbol == source_symbol` y además `ticks[].symbol == validated_market_symbol`. Por tanto actualmente no puede aceptar una fuente NDX100 como sustituto del source NAS100, **incluso si posteriormente existiera una revisión documental externa**. Es fail-closed conveniente hoy, pero el futuro puente de equivalencia deberá tener un contrato auditado con prueba externa verificable, no sólo un string `validated_market_symbol` suministrado por el caller. OPS debe decidir diseño, sin abrir el gate por comodidad.

**H2 — cobertura temporal no certificada:** `coverage_prevalidated` es un boolean suministrado por caller a `compare_quote_ce`; `audit_quote_gzip` mantiene explícitamente `complete_requested_history_proven=False`. Hace falta evidencia independiente de calidad/cobertura a escala de las ventanas y 619 cronologías, incluyendo gaps de market-hours, periodos sin sesión y orden de ticks de igual milisegundo. Un argumento booleano no es auditoría.

**H3 — tick quote ≠ fill:** `compare_quote_ce` no consume confirmaciones de broker ni tiene reconciliación de oferta→ACK→fill/cancel→posición→exit. Sólo detecta observación de precio lateral durante un intervalo aparentemente elegible. Un cruce puede coexistir con rechazo, fill parcial, latencia, slippage o cancelación previa.

**H4 — contrato monetario insuficiente:** `TickSourceContract` identifica tick_size/point/contract_size, pero no prueba tick_value monetario oficial, cambio de divisa, step de lote, comisión dinámica, swap/slippage ni validez NAS100↔NDX100. Tampoco fuente del precio M1 de 3Y MID/BID/ASK. Ejemplo MT5 0.01 lot y spread 1.60 son snapshots, NO contrato oficial.

**H5 — same-millisecond ≠ secuencia decidible:** `audit_quote_gzip` registra el número de pares coincidentes pero no demuestra precedencia broker de eventos de idéntico `time_msc`. Preservar indeterminación si no hay orden nativo verificable; no usar orden de filas para fingir secuencia.

**H6 — deuda de calidad menor pendiente OPS:** ruff `UP035` heredado en el módulo de ticks. El CI nuevo lo identifica sin tocar código de otro arquitecto ni abrir PR productiva.

## Gates y decisión a esta fecha

| Control | Resultado |
|---|---|
| 21 pruebas negativas/positivas del contrato pasivo | PASS (fixtures, sólo unit tests) |
| Serie histórica Bid/Ask NAS100/NDX100 del mismo instrumento/servidor | NO DISPONIBLE / NO VERIFICADA |
| 619 same-M1 y 51 geometrías A/B resueltas con secuencia subminuto | NO |
| Preregistro B indeterminados ≤10% | FAIL anterior, 670/2140=31.31% |
| ACK/fills, net PnL, PF/DD, Sharpe/Sortino | NO CALCULABLE |
| Doctrina original ICT / formalización QORE revisada por dos arquitectos | PENDIENTE |
| Holdout/liberación MAIN/VPS/LIVE | SELLADO / PROHIBIDO |

**Veredicto P0: INSUFICIENTE_EVIDENCIA_POR_DATOS; no constituye retiro inmediato ni certificación.** No hacer filtros nuevos, no optimización de PnL y no reasignar los 670 UNKNOWN a wins o fills.

## Siguientes acciones delimitadas (responsabilidades y orden)

**OPS P0-1 — fuente auténtica:** recuperar fuera del repositorio sensible un export autorizable MT5/cTrader de ticks nativos BID/ASK timestamp UTC ms con `symbol, time_msc, bid, ask, flags`, rangos reales y evidencia de hash. Antes de usarlo, archivar metadatos públicos de instrumento y reconciliar NAS100 fuente ↔ NDX100 broker (o declarar incompatibilidad). No usar captura instantánea como 3Y.

**OPS P0-2 — cobertura independiente:** emitir reporte de periodos disponibles/missing, sesiones DST, tramos ilíquidos, timestamps duplicados/simultáneos, y una prueba positiva explícita de cobertura por cada ventana relevante; rehacer los tests con fixtures corruptos y datasets auténticos NO públicos donde corresponda. Solamente tras esto se podrá pasar `coverage_prevalidated=True` en caller auditable.

**COG/OPS P0-3 — libro causal pareado:** inmovilizar 2,140 IDs; sobre todo 619 coincidencias en M1 de CE e invalidación/target y 51 geometrías no demostradas. Definir en la mesa de doctrina qué constituye MSS válido, protected swing y stop; distinguir regla ICT textual vs normalización QORE vs rama experimental B. No alterar umbrales preregistrados.

**OPS P0-4 — ciencia económica:** simular PAPER con etiquetado `SIMULATED_EXECUTION` separado de `EXTERNAL_EXECUTION_ACK` y libro de una sola VT31. Procesar cronológicamente spread variable, lotes, fees, slippage y stops/targets; reportar densidad, expectativa neta, PF, maxDD y robustness contra todos los 2,140 IDs (no sólo subgrupo ganador). Si datos siguen insuficientes, cerrar estudio bajo `INSUFICIENTE_EVIDENCIA_POR_DATOS` con alcance y limitación.

**ARCH — gobernanza:** nada en MAIN, ninguna orden de broker, ningún accesso al Fresh Holdout. Comunicar los cambios por Issue #727 (cuerpo viejo del Issue pertenece a VT31 legacy; las últimas comunicaciones cleanroom y el handoff prevalecen). Las variaciones de regla de riesgo o ejecución requieren preregistro y aprobación cruzada previa.

## Referencias de custodia

- [Handoff Maestro VT31 #872](https://github.com/mezas3238-hue/qore-core/pull/872).
- [Módulo `quote_tick_science.py` en PR #833](https://github.com/mezas3238-hue/qore-core/blob/e51d1bc8a7d14514507d343875b273e07e9afa6a/src/qore/infrastructure/traders/vt31_ict_cleanroom/quote_tick_science.py).
- [CI 21/21](https://github.com/mezas3238-hue/qore-core/actions/runs/38310866082) y [CI primer intento — falla UP035](https://github.com/mezas3238-hue/qore-core/actions/runs/38310804219).
- [Coordinación ARCH #727](https://github.com/mezas3238-hue/qore-core/issues/727).

**No confundir esta aprobación local de sintéticos con evidencia positiva de retorno de VT31.**
