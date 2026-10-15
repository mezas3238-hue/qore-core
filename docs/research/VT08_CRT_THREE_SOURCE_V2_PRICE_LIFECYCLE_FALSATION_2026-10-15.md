# QORE CORE — VT08 CRT THREE SOURCE V2
## FALSACIÓN CAUSAL DE DESTINO/INVALIDACIÓN EN 745 HIPÓTESIS, SIN SIZING NI PnL

**Fecha:** 15-OCT-2026 · **PR #626** DRAFT/sin merge · **Source:** original Atlas AUDUSD + USDJPY 296.372 M5.  
**Hipótesis V2 exacta CONGELADA ANTES de outcome:** [prereg V2](VT08_CRT_3_FUENTES_QORE_V2_PREREG_2026-10-15.md).  
**Metodología:** QORE síntesis tres fuentes **RomeoTPT, SpeculatorFL, TraderFlameseN**. No se exige regla exclusiva Romeo para decidir CRT QORE. No se certifica la metodología solo por coincidencias de OHLC.

## 1. Fuente inmutable, ejecuciones y denominadores

- **Generador V2:** `src/qore/infrastructure/trader_lab/vt08_crt_three_source_v2_full_h4_census.py` con [censo original #38711787794](https://github.com/mezas3238-hue/qore-core/actions/runs/38711787794), **HEAD ad190683b91298cf07b6b7aefe87779f56146401**, quality/AUDUSD/USDJPY SUCCESS. Exactos **745 casos conceptuales (353 AUDUSD y 392 USDJPY)**, 5.524 pares H4 completos, no 745 trades.
- **PRE-REGISTRO DE LIFECYCLE ANTES DE VER PATH:** [VT08_CRT_THREE_SOURCE_V2_LIFECYCLE_PREREG_2026-10-15.md](VT08_CRT_THREE_SOURCE_V2_LIFECYCLE_PREREG_2026-10-15.md), commit **1e1be8231fdd182859534c3570c9b6ae47d562df**.
- **Evaluador:** `src/qore/infrastructure/trader_lab/vt08_crt_three_source_v2_price_lifecycle.py`, tests `tests/infrastructure/trader_lab/test_vt08_crt_three_source_v2_price_lifecycle.py`. Reconstituye la V2 congelada desde la misma fuente original, reconcilia 353+392 source IDs, y **SOLO DESPUÉS DE CONFIRMACIÓN** observa el recorrido M5 hacia el destino H4 C1 midpoint o extremo invalidante de la M15 confirmadora. Si los dos se tocaron en la misma M5, se marca **INVALIDATION_FIRST_AMBIGUOUS**; si no hay cotización de apertura contigua o datos M5, UNKNOWN y nunca un fill inventado; último M15 justo en cierre H4 C3 expira sin trayectoria posterior.
- **CI [#38713036976](https://github.com/mezas3238-hue/qore-core/actions/runs/38713036976)** ejecutó calidad/AUDUSD/USDJPY **SUCCESS**. Código corrido en HEAD **1cc9a7fb2529eadd857bd6685df27a01a2cd4713**. Artefactos precio-only AUDUSD **11961063948**, USDJPY **11961720910** descargados y SHA256SUMS internos **3/3 PASS** cada uno. No se observaron datos monetarios ni se hizo sizing. Los bloqueos de Quality (Ruff) y error de decisión en cierre H4 de ejecuciones anteriores se repararon antes de este GREEN; NO esconder las fallas del historial de CI.

## 2. Estadística de trayectorias M5 (PRECIOS solamente)

| Estado de observación | AUDUSD 353 | USDJPY 392 | Total 745 |
|---|---:|---:|---:|
| `DESTINATION_FIRST` | 58 | 57 | **115** |
| `INVALIDATION_FIRST` | 248 | 290 | **538** |
| `INVALIDATION_FIRST_AMBIGUOUS_SAME_M5` | 0 | 2 | **2** |
| `EXPIRED_WITHOUT_TOUCH` | 30 | 27 | **57** |
| `EXPIRED_AT_C3_CLOSE_NO_POST_DECISION_WINDOW` | 3 | 3 | **6** |
| `UNKNOWN_ENTRY_ALREADY_BEYOND_BARRIER` | 5 | 5 | **10** |
| `UNKNOWN_MISSING_ENTRY_OPEN_PRICE` | 1 | 1 | **2** |
| `UNKNOWN_MISSING_M5_BEFORE_TERMINAL` | 8 | 7 | **15** |
| **Total** | **353** | **392** | **745** |

La observación comparó el primer toque del precio en el segmento **posterior al reloj de decisión**, hasta cierre H4 C3. **No** es resultado de trades; no dispone de spread BID/ASK ejecutable, confirmación de fills, comisiones ni política patrimonial. El midpoint H4 se midió sin elegir favorablemente el orden de stop/target en la misma M5. Los eventos close-at-boundary se declararon caducados, sin imputar trayectoria del próximo H4.

## 3. Dictamen científico: la densidad no crea ventaja

V1 generaba **54 candidatos**; V2, ampliando M15 dentro del H4, logró **745** (≈13,8×), pero el experimento de destino/invalidación sobre V2 congelada tiene **538 invalidaciones primeras vs 115 destinos primeros**, más casos terminales/desconocidos. **Es evidencia adversa para este diseño preciso de rango HTF, entrada conceptual y frontera de invalidación.** No permite afirmar valor esperado positivo ni certificado económico. No es válido inferir un PF o WR de trading de esos conteos. **No cambiar V2 para maquillar los 115/538.**

**Interpretación de límites:** la alta invalidación observada podría depender de la elección QORE de extremo M15 como frontera y de la disponibilidad del midpoint H4, no implica que TODO CRT carezca de edge. Pero mover target/invalidación tras conocer el resultado **define identidad nueva** y exige una nueva hipótesis, preregistro y otro conjunto OOS no explorado. No optimizar aquí.

**No usar 2024–2026 Atlas consumidos como OOS:** estos precios fueron usados para crear V1, V2 y examinar resultados. Todo este diagnóstico es DEV/IN-SAMPLE. La fuente original es OHLC M5 y no prueba ejecución BID/ASK, eficiencia real ni costes. Sin método fijo rentablemente falsable y coste PIT, no hay PF neto ni Sortino o DD de cuenta, incluso si V2 presentara 100% destinos.

## 4. Gates después del experimento

- **G-M1:** tri-source QORE autorizado por el Owner, pero siete contratos específicos de elegibilidad, jerarquía, secuencia micro, target, rearm/expiry siguen sin adjudicación fuente+ingeniería independiente completa. PARTIAL.
- **G-M2:** múltiples paquetes visuales de datos originales y resultados de diagnóstico reales; faltan actas independientes de evaluación verdadera del método sintético y casos con información causal ampliada. PARTIAL.
- **G-M3:** cognitiva fail-closed probada, pero no está integrada como razonamiento positivo válido a la generación de esos 745 V2. PARTIAL.
- **G-M4:** invariantes locales/CI verdes y ruta source WAIT, pero no flujo E2E aprobado de real first-admission, invalidación, expiración y authority externo. PARTIAL.
- **G-M5:** **NO EMITIDO**. Un acuerdo del Owner para usar tres fuentes no equivale a certificado firmado de método.
- **GLOBAL:** PF, DD, Sharpe, Sortino, expectancy, costes, WFO, estrés, Monte Carlo, fresh OOS, Risk/CIBO independientes **NO PASADOS**. No inventar números económicos. Si se exige DD monetario, únicamente CIBO/Risk externo, nunca un sizing propio o hipotético del Trader.

## 5. Pasos concretos para no perder el rumbo

1. **Conservar V2 exacta como diagnosticada, no retocar sus condiciones**. Registrar este verdict en la matriz de hipótesis consumidas y no usarlo para seleccionar la mejor versión posterior en mismo periodo.
2. Abrir una **nueva** hipótesis CRT de tres fuentes con causa identificable —p. ej. separar familias «journey», «reaction», «confirmation» de SpeculatorFL/TraderFlameseN— pero **predefinir contratos completos y sus barreras antes de resultado**; no combinarlas retrospectivamente en un ganador.
3. **Asegurar corpus nuevo OOS genuinamente no visto**, congelar reglas, costo/spread BID/ASK y simular ejecución causally con datos originales/external Risk/CIBO. Un precio "tocó" no es una orden ni una ganancia.
4. Hacer G-M1 a G-M4 con adjudicación metodológica/QORE, razón cognitiva y E2E. El método **no requiere coincidencia literal exclusiva de Romeo**. G-M5 solo con evidencia independiente y revisión real.
5. Economía/global: umbrales CRT PURE oficiales pre-registrados antes de datos nuevos, PF net, Drawdown patrimonial externo Risk/CIBO, Sharpe/Sortino, estabilidad, WFO, Monte Carlo, estrés, independencia. No cambiar estado `CERTIFIED` para premiar progreso de infraestructura.
6. **Issue #837 custodia Atlas12**, vencimiento 2026-12-16; respaldo privado licenciado y restore SHA autorizado, no push de fuente privada a repo público.

**No sizing, no merge, no orders, no VPS/DEMO/LIVE. CIBO soberano volumen/capital. Resultado V2: PRICE_PATH_NO_SUPPORT_FOR_V2_AS_DEFINED; no implica falsación universal de CRT.**
