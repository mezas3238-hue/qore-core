# P0 · Costos reales observados en MT5 FundedNext — 5 posiciones cerradas y conciliación de cuenta

**2026-10-09** · **PR #745** · Fuente directa: captura de historial MT5 suministrada por titular en esta conversación, SHA256 del archivo de imagen: `914072741b2301ee5e69c7c3bb9228292db38f0ca93a9d47da86a8b2efdf54b0`. No publicar nombres de cuenta, tickets, credenciales ni la imagen original en el repositorio.

## 1. Prueba de tarifas de una cuenta real frente a los antiguos supuestos de replay
En **Historial → Posiciones** (todos los símbolos), la captura muestra **cinco operaciones cerradas** de 0,01 lote con comisión agregada por posición:

| Símbolo | Lado | Volumen | Precio apertura → cierre | P&L de precio mostrado | Comisión registrada en posición | Net posición |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| EURUSD | SELL | 0,01 | 1,13455 → 1,13439 | +$0,16 | −$0,07 | +$0,09 |
| GBPJPY | BUY | 0,01 | 209,522 → 209,503 | −$0,12 | −$0,07 | −$0,19 |
| AUDJPY | BUY | 0,01 | 110,471 → 110,454 | −$0,11 | −$0,07 | −$0,18 |
| XAUUSD | BUY | 0,01 | 4185,46 → 4185,11 | −$0,35 | −$0,07 | −$0,42 |
| NDX100 | BUY | 0,01 | 30852,60 → 30848,08 | −$0,45 | **$0,00** | −$0,45 |
| **Total** | | | | **−$0,87** | **−$0,28** | **−$1,15** |

**Balance conciliado exactamente:** `$2.000,00 inicial + (-$0,87) PnL de precio + (-$0,28) comisiones + $0 swap = $1.998,85` saldo reportado; no aportes posteriores registrados en el tramo mostrado. El resumen MT5 de la captura dice `Comisión -0.28` y `Balance 1 998.85`. La cifra de `Beneficio 1 999.13` en el encabezado incluye la operación de depósito del historial; no reinterpretarla como $1.999,13 de ganancia comercial.

### Precios, valores por contrato, comisiones
- **EURUSD SELL:** `(1.13455 - 1.13439) * 100,000 * 0.01 = +$0.16`, exacto. Comisión total mostrada `$0.07`, compatible con `$7/lote` por apertura.
- **XAUUSD BUY:** `(4185.11 - 4185.46) * 100 oz * 0.01 lote = -$0.35`, exacto. Comisión FAQ oficial `4185.46 * 100 * 0.01 * 0.000016 = $0.06696736`, redondeada a **$0,07**, igual al historial. El replay *legacy* multiplicaba por dos: el cargo agregado observado en esta operación **NO coincide** con el doble.
- **NDX100 BUY:** `(30848.08 - 30852.60) * 10 USD/punto/lote * 0.01 lotes = -$0.452` → **−$0.45** al centavo, igual al historial. Comisión total **$0**, contra el supuesto arbitrario histórico de `$20 por lote`.
- **GBPJPY y AUDJPY:** con contrato `100,000` y pip `0.01 JPY`, el valor pip es `1000 / USDJPY(t)` USD/lote. La **otra captura** de cotizaciones muestra USDJPY en torno a 158,34 en 2026-10-09, por tanto ~$6,32/pip/lote; caídas de 1,9 y 1,7 pips en 0,01 lotes producen aproximadamente −$0,12/−$0,11 registrados. **La captura de USDJPY NO es tick sincronizado del instante de los fills**, por eso solo es corroboración aproximada, no demostración de tipo FX causal exacto.
- **GBPUSD:** no aparece entre las cinco posiciones cerradas de esta captura. Sigue habiendo evidencia de la **página oficial** para su tarifa pública $7/lote; NO afirmar comprobación directa de una operación GBPUSD de esta cuenta.

### Qué se ha demostrado / qué no
**Demostrado para estas cinco operaciones:** comisiones agregadas por símbolo de 0,01 lote, coincidencia con modelo de tarifa FundedNext Stellar Instant Help, valoración de USD/XAU/NDX por contract size mostrado previamente y balance final del historial. El snapshot de precios y la página oficial se complementan.

**NO demostrado solo con la vista «Posiciones»:** qué deal exacto debitó la comisión, separación OPEN/CLOSE, vigencia futura para todos los tamaños/modalidades, otras tasas de financiación nocturna, profundidad de mercado o precio ejecutable de 2019–2022, comisión GBPUSD observada en cuenta, tick USDJPY histórico en cada entrada, desempeño gestionado por CIBO, DD intratrade de la muestra ni DD/PF de las 3.368 señales. Obtener `History → Transactions` / `history_deals_get` para distinguir apertura y cierre cuando se necesite evidencia por pata.

## 2. Integración en el código y control de calidad
- `src/qore/infrastructure/qdle_mt5_history_fee_audit.py` añade `ClosedMT5PositionEvidence` y `reconcile_mt5_closed_history`: valida timestamps, identidad simbólica, comisión por símbolo redondeada a centavo, PnL en activos denominados USD, conversión JPY aproximada etiquetada y conciliación de capital/fees; **solo READ, jamás order_send**.
- `tests/infrastructure/test_qdle_mt5_history_fee_audit.py` transcribe exclusivamente valores financieros mostrados y horas, **sin tickets ni datos identificadores**. Casos negativos detectan Forex $0.14 para 0.01, XAU doble comisión, NDX falsa comisión, desvío de PnL/contrato, desbalance y duplicados.
- `.github/workflows/qdle-stellar-instant-3368-fee-reprice.yml` ahora ejecuta pruebas de evidencia real **antes** del rerun de costos de 3368 señales y publica `actual-mt5-5-closed-trades-commission-reconciliation.json` junto a los 3 modelos comparativos.
- El motor de tarificación del replay **ya había sido corregido al modelo oficial** en el run SUCCESS [#37943757745](https://github.com/mezas3238-hue/qore-core/actions/runs/37943757745), que devolvió 2102 QDLE quotes contra 1961 legacy. Esta nueva captura **verifica su plausibilidad real** en cinco operaciones; no autoriza cambiar el resultado histórico a fills.

## 3. Separación innegociable de capital y drawdown
**$2.000 broker** en la captura, no **$60 NAV propio QORE** de la investigación CIBO. Estas cinco posiciones son historia del terminal pero **no prueban decisiones CIBO Native MAX ni el replay de 3.368**. Nunca inyectarlas como `CIBO_SETTLED` ni como ganancias/pérdidas del gestor histórico, ni usar su DD para certificar a CIBO.

El siguiente replay podrá verificar que los precios y comisiones de los cinco ejemplos realmente coinciden con las fórmulas. **El NAV/dd/PF de CIBO sobre las 3.368 señales permanece `null`** sin trayectorias históricas completas o recibos de ejecución/gestión de esas posiciones. Distinguir un test real de microestructura y comisiones de un test de rentabilidad.

**Fuente de la tarifa pública comparada:** [FundedNext Stellar Instant FAQ](https://help.fundednext.com/en/articles/11641300-what-are-the-commission-charges-for-the-stellar-instant-account); cobra Forex $7/lot, XAU 0.0016% del nocional, índices $0. Aún existen ambigüedades con reglas generales `per side`, ahora mitigadas por la muestra histórica de la cuenta para los cinco trades, pero no universalmente resueltas.
