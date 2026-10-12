# QORE EVENT-MACRO — CONTRATO DE VIABILIDAD PRE-G1 (POWER / PIT / COSTE / DECISIÓN)

**2026-10-11, investigación únicamente.** Hijo de [PR #810](https://github.com/mezas3238-hue/qore-core/pull/810) y [issue #808](https://github.com/mezas3238-hue/qore-core/issues/808). El objetivo es responder **«¿podemos medir un edge neto CPI con nuestro archivo?»**, no «¿existe edge?». Este escrito es ANTERIOR a cualquier retorno G1. No cambia RESET/DRIVE ni autoriza G1, broker, VPS o LIVE.

## 1) Qué existe, qué NO está verificado

**Acreditado**: 119 originales CPI existentes con fecha, referencia y embargo 08:30 ET verificados en los encabezados BLS ([G0B exact head #38191275999](https://github.com/mezas3238-hue/qore-core/actions/runs/38191275999)); 113/119 fechas con 71/71 timestamps M1 NAS100/USTEC CIBO ([G0 #38189483643](https://github.com/mezas3238-hue/qore-core/actions/runs/38189483643)). Esas son fechas de comunicados archivados, **no garantía de que el calendario era conocido T-1**, ni de expectativa conocida T-5, ni de precio ejecutable a T0.

**Desconocido y bloqueante**: una serie completa de consenso **con verdadero vintage anterior** (`G0C`), costes de ejecución históricos **a la hora exacta del CPI para el mismo CFD** (`G0D`), desviación estándar del estimando neto de estrategia, potencia realizable y OOS virgen. El archivo CIBO M1 conserva OHLC pero **no sustituyen bid/ask/ticks ni fills**. No confundir ausencia de coste auditado con coste cero.

## 2) Auditoría concreta del proveedor (sin contratar por documentación)

[Trading Economics Point-in-Time API](https://docs.tradingeconomics.com/economic_calendar/point-in-time/) afirma conservar estados históricos, pero los ejemplos muestran consultas con fechas `initDate/endDate` de eventos y campos `Actual, Forecast, TEForecast, LastUpdate`. **No demuestran que `Forecast` representara exactamente el consenso observable a T-5 minutos** para CPI de 2016–2026; `LastUpdate` puede ser posterior al release. Su [documentación de snapshot](https://docs.tradingeconomics.com/economic_calendar/snapshot/) distingue `Forecast` (consenso) y `TEForecast` (pronóstico propio). La [página de precios/API](https://tradingeconomics.com/api/pricing.aspx) contiene planes/trial y límites; no se han verificado condiciones específicas de consulta CPI vintage ni licencia que permita preservar los 119 testimonios en GitHub.

La verificación requiere **respuesta escrita o demo con 3 eventos preregistrados** (uno 2016, uno 2020, uno 2025 extraordinario) y capturas firmadas/archivadas legalmente de campo `Forecast`, autoría, UTC de primera captura y revisiones a T−24h y T−5min. **No** consultar valores en repositorio abierto hasta derechos de uso y sanitización. Verificar que PIT es realmente **snapshot del estado disponible en esa fecha/hora**, no filtro de publicación histórica; comprobar comparabilidad `headline MoM SA` y `core MoM SA`, población de panel, media/mediana, fecha de referencia y vintage. Si el proveedor no puede demostrar estado anterior: `PIT_NOT_PROVEN` y NO usar para sorpresa retrospectiva.

Fuente B debe ser independiente **en origen de panel y distribución** (p. ej. Econoday / Reuters archivado con timestamp pre-release); dos webs que republlican la misma estimación no son dos muestras independientes. La muestra CONGELADA de 24 eventos ya está en `docs/research/QORE_NATIVE_EVENT_CPI_G0C_TWO_SOURCE_24_EVENT_PIT_COMPARISON_PREREG_2026-10-11.md`; no modificar fechas por diferencias. Regla >=23/24 con tolerancia absoluta <=0,05 pp en headline/core y 24/24 procedencias auditables es **screen de comparabilidad, no estimación de fiabilidad al 95%**. Acuerdo de consensos con redondeo a 0,1 pp no prueba exactitud, una discrepancia puede ser legítima por cobertura/panel/update. Discrepancia obliga adjudicación de definición/timestamp; no concluye que ambos proveedores sean falsos.

**Tres salidas de G0C**: `PIT_VERIFIED_TWO_INDEPENDENT_SOURCES`, `PIT_PARTIAL_OR_UNPROVEN`, `PIT_NOT_ACCESSIBLE_OR_LICENSE_BLOCKED`. Las últimas dos bloquean G1 económico; la primera permite diseñarlo, no supone edge.

## 3) Reloj congelado PARA AUDITAR COSTES — no señal de trading

**Única ventana de estudio de viabilidad G0D**: liberación BLS **08:30 NY**, potencial decisión first-online **08:35 NY**, posible salida **09:05 NY**. Ambas horas fijas pre-retornos para buscar spreads históricos y liquidez del MISMO CFD `NAS100/USTEC` de la cuenta cTrader IC Markets, en hora Nueva York IANA y con DST. **Este contrato congela únicamente el horario para obtener fricción/ejecución, no selecciona un lado, regla de sorpresa, stop/target ni backtest**. Si proveedor no documenta bid/ask en 08:35/09:05 o primer fill realista (latencia + mercado), `COST_WINDOW_UNVERIFIED`; no pivotar a T+60s o T+15m según movimientos que luego se conozcan. Cambiar ventana exigiría *nuevo prereg* y corrección de multiplicidad.

**Evidencia mínima**: timestamp UTC sincronizado, spread BID/ASK válido en entrada y salida, contrato/tick-value/nocional/currency conversion, órdenes min lote, comisión RT, slippage y latencia de eventos/condiciones de mercado y discontinuidades en ventanas CPI. Etiquetar LIVE/DEMO separado; una cotización DEMO actual no acredita historial LIVE. Modelo de ejecución conservador con bandas **1×/1,5×/2×** coste CPI verificado; si no hay fills históricos, marcar `MODEL_COST_NOT_REAL_FILL`, no promover como PnL certificado.

No asumir como históricos los ejemplos «10–20× spread», «3–8 bps», ni velocidad de HFT de comentarios de auditor; son supuestos que requieren telemetría específica.

## 4) Potencia: escalar correctamente y concluir sin falsos negativos

**Sin leer retornos**, sensibilidad por desviación estándar hipotética `σ` del **estimando primario pareado** (NO volatilidad del NAS100, ni amplitud total de velas) en bps. Suponiendo n eventos independientes, alfa 5% bilateral y potencia objetivo 80%, `MDE≈(z_0.975+z_0.8)σ/√n≈2.8016 σ/√n`. No incorpora distribución pesada, heterocedasticidad CPI, clustering, múltiples pruebas, selección por signo, costes ni incertidumbre del forecast: es **límite optimista de planificación**, no power audit PASS.

| Eventos efectivos supuestos | σ=20 bps | σ=40 bps |
|---|---:|---:|
| 113 CPI cubiertos (techo, no n final) | 5,27 | 10,54 |
| 56 CPI después de separar por un lado (solo escenario) | 7,49 | 14,98 |
| 560 eventos macro hipotéticos homogéneos (NO disponibles ni combinables) | 2,37 | 4,74 |

Con n=113 y efecto VERDADERO 5 bps, potencia aprox **75,7% si σ=20** y **26,4% si σ=40**; 10 bps produce ~100% y **75,7%** respectivamente. La potencia para `IC95 inferior neto >0` o `>2 bps` requiere margen **adicional** y será inferior a la de un simple test contra cero en zonas próximas al umbral. El efecto mínimo detectable debe compararse al **umbral de materialidad neto**: entrada/salida/coste CPI, riesgo y capacidad.

**No concluir `POWER_INSUFFICIENT` definitivamente hasta tener fuente as-of, estrategia/estimando, hipótesis de varianza defendible SIN usar futuras observaciones de validación, n efectivo y coste.** Hoy el estado es `POWER_CONDITIONAL_SENSITIVITY_ONLY`. Si no existen estas entradas: `FEASIBILITY_BLOCKED_DATA`. Si existen pero potencia estimada <80% para el beneficio mínimo económicamente necesario: `NOT_WORTH_G1_UNDERPOWERED`; un eventual resultado no significativo = `INCONCLUSIVE_UNDERPOWERED`, **NUNCA `NO_EDGE`**.

## 5) Política CPI frente a agregación de noticias

**CPI ONLY = única familia económica autorizable para primer G1.** Si CPI fracasa por G0C/G0D o falta de potencia, no añadir NFP/PCE/PPI/FOMC automáticamente y volver a probar el mismo patrón sin prereg. Cada fuente nueva empieza con su **propio G0 de calendario real, consenso as-of, costos y reloj**.

Futura investigación de *familia macro combinada* solo si se preregistra mecanismo común justificable entre sorpresas normalizadas por desv. estimada **exclusivamente con pasado**, dependencia entre releases, tratamiento diferente de horarios FOMC vs 08:30 y modelo jerárquico/event-type effects con heterogeneidad. El aumento de n de 113 a 560 nominales reduce incertidumbre ideal solo `sqrt(560/113)≈2,23×`, no la multiplica 5× en evidencia. La decisión de pool es previa al PnL y no puede «rescatar» un CPI fallido sin revelar multiplicidad.

## 6) Único contrato de decisión del arquitecto

`G1_ECONOMICS_ALLOWED` requiere SIMULTÁNEAMENTE:
1. `119/119 archived actual releases` y cohortes de calendario definidas, 71/71 M1 por cada evento seleccionado (G0/G0B source pass; n usable <=113);
2. consenso headline/core MoM SA con versión PRE-08:30 verificable y dos fuentes comparadas, definición de sorpresa y normalización solo pasado;
3. `08:35→09:05 NY` con coste específico del mismo broker/símbolo y simulación first-online, no un spread genérico;
4. estrategia única, lado, umbral, baseline no-evento, regla as-of y unidades de retorno neto preregistrados **antes de mirar retornos G1**;
5. potencia 80% para *umbral económicamente relevante* y control de multiplicidad, además de periodo no abierto OOS para certificación.

Si falta 2 o 3: `BLOCKED_NOT_EVALUABLE_INFRASTRUCTURE`. Si falta 5: `BLOCKED_OR_INCONCLUSIVE_POWER`. En ningún caso `NO_EDGE`. **Estado al escribir**: `G0B_PASS / G0C_BLOCKED / G0D_BLOCKED / POWER_CONDITIONAL / G1_NOT_AUTHORIZED`.

No actividad en producción, QDLE, Shared, CIBO, VPS o MT5. 0 traders certificados.
