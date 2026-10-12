# QORE Native — PREREG técnico del Gate E1 pre-decisión (P0 #863)

**Fecha:** 2026-10-12. **Alcance:** investigación, rama aislada; **no** activa órdenes, VPS, MT5, LIVE, CIBO, Shared ni QDLE.

## Hipótesis de ingeniería, no hipótesis de rentabilidad

El documento original G1 validó 373.611 oportunidades E1 de siete métodos en 33 mercados (33 ZIP de investigación firmados, fuente E1 `dfe78f115957a40f4188c30e78bd7f88c2ce6c42`). La columna `reference_entry_utc` es un **reloj reconstruido de oportunidad**. El horizonte de 15/120/240 minutos es un **cierre teórico M5**; no están demostrados señal previa, autorización, orden ni ejecución. Se prohíbe inferir esos campos a partir de un timestamp E1.

**Predicción antes de ejecutar el auditor:** con solo el ledger clock-only de G1, **0 de las 373.611 oportunidades tienen un testigo pre-decisión independiente**. Por tanto, el auditor nuevo debe devolver 373.611 `BLOCKED`, 0 órdenes autorizadas y 0 PnL NET, independientemente de qué retorno gross tuvo cada evento. No es una evaluación nueva del edge.

## Contrato inmutable del código

- Fuente: `docs/research/QORE_NATIVE_E1_SOURCE_CLOCK_BUDGET/audit.py` restaura 33 ZIP E1 originales desde Actions, comprueba hashes y estados, y genera `original_E1_event_clocks_only.jsonl.gz`; el módulo nuevo **solo lee ese clock-only** y valida su estructura exacta. El archivo original con outcomes no es consultado por el código nuevo.
- Módulo: `src/qore/infrastructure/trader_lab/qore_native_g1_e1_predecision_failclosed_v1.py`.
- Todas las identidades deben coincidir con SHA256 de `E1_SHA|method|symbol|UTC-clock`. Siete métodos y 33 mercados son inmutables; 373.611 filas, 231 celdas, sin IDs duplicados; embargo desde 2024-09-17.
- Formato rechazado si aparecen campos añadidos de outcomes, `real_broker_fill=True`, flags falsificados, timestamps ingenuos/no UTC, identidad cambiada, ventana temporal violada o contrato de cohorte alterado.
- El ledger derivado por fila solo conserva ID, mercado, método, relojes de estudio y motivos de bloqueo. Siempre `entry_order_eligible_at_utc=null`, `exit_decision_time_utc=null`, `broker_fill=false`, `orders_authorized=false`, `NET_authorized=false`.
- La función `assess_predecision_shape()` valida **solamente la estructura** de un eventual testigo: cierre de barra y recepción de features antes de la decisión; decisión antes de elegibilidad; elegibilidad antes de caducidad; side definido; SHA de testigo con formato correcto; UTC y embargo. Incluso en PASS estructural mantiene `witness_verified=false`, `source_quotes_verified=false`, `contract_verified=false`, `order_authorized=false` y `historical_NET_authorized=false`. La función **no valida autenticidad criptográfica del testigo externo**.

## Aceptación y falsaciones

1. Tests sintéticos cubren identidad, duplicación, fugas de outcomes, timestamps no UTC, información futura, caducidad, embargos, contrato y output determinista.
2. CI recupera E1 firmado desde archivos con SHA, corre auditor de source clocks, verifica los 373.611/33/231 y ejecuta el nuevo puente sin acceder a signos ni retornos.
3. Segundo control verifica `research_clocks_rejected_as_orders == 373611` y `predecision_witnesses_verified == executable_trades_proven == certified_traders == 0`, NET false.
4. Publicar artefactos de reloj-only, summary, digest SHA y código exacto. ZIP de Actions sigue siendo temporal, no `Data Vault` duradero.
5. Si cualquier control falla, FAIL total; **no** modificar E1 original ni seleccionar subconjuntos por retornos para pasar Gate.

## Después de esta entrega — P0 aún abiertos

- **#863:** construir emisor de evidencia de decisión desde reglas de señales realmente disponibles antes del orden; congelar disponibilidad de barras, secuencia de eventos, stop/target/expiración, orden/fill/salida y contraste scalar-vs-Ultra Fast; autenticar bytes y SHA del testigo independiente. No adjudicar automáticamente en función del reloj E1 ni del resultado futuro.
- **#837:** permiso del proveedor y vault privado duradero con restore SHA de 33 M5 + M1; los 12 Atlas originales expiran antes de los 21 nuevos.
- **#857:** cuenta original, contratos y costes históricos; el cotejo 12/12 provider ID y precisión actual DEMO **no** demuestra contrato exacto.
- **#856:** semántica cero BID=ASK y calidad broker. Prohibida imputación gratuita sin justificación.
- Fuente quote: solo cuando lo anterior tenga pruebas, evaluar last-known BID/ASK as-of y coste con stop, fill, slippage, commission, swap, noticias PIT, moneda/lot. E1/E2/E3 = 231 gross sin edge positivo replicado; **0/3 traders certificados**.
- Investigación/holdout: DEV y DIAG están expuestos; tramo desde 2024-09-17 en embargo económico.

**Importante:** un test sintético aprobado valida la lógica del filtro; **no** certifica operaciones, contratos ni estrategias. Un reporte de 373.611 rechazos tampoco prueba que todos sean operaciones imposibles: únicamente prueba falta de evidencia pre-decisión en el esquema E1 anterior.

Fuente: [Handoff integral PR #855](https://github.com/mezas3238-hue/qore-core/pull/855), [source clocks PR #867](https://github.com/mezas3238-hue/qore-core/pull/867), [Issue #863](https://github.com/mezas3238-hue/qore-core/issues/863).
