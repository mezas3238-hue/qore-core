# QORE NATIVE RESET — G1 preregistro de presión y reversión del fixing Londres (DESARROLLO CONSUMIDO)

**Fecha:** 2026-10-11. **Programa:** #789, RESET #793. **Tesis precursora:** PR #799. **No son entradas reales ni certificación.** Este protocolo se congela ANTES de ejecutar el primer cálculo de retornos condicionado de RESET en la línea presente.

## Identificación y corrección de la fuente: memoria CIBO 12 mercados (no solo G0 nueve)

- **CIBO Market Atlas 10Y**: [Actions run #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458), **12/12 artefactos M5 + agregado**, 8.726.985 M5, ventana solicitada `2016-09-17T00:00:00Z` a `2026-09-17T00:00:00Z` exclusiva. Aggregate artifact **#10476615509**, Git SHA del nombre de artefacto `ab782b8e9f890f86a2b6500070f0556b4b685e3d`. Para EURUSD artifact **#10475354631**, **745.458 barras M5**, primera 2016-09-18T21:00Z, última 2026-09-16T23:55Z. Agregado `CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1`; padre `CIBO_MARKET_ATLAS_20Y_V1`. No inventar 20 años efectivos.
- **12 símbolos exactos:** AUDJPY, AUDUSD, EURUSD, GBPJPY, GBPUSD, NAS100 (provider USTEC), SP500 (US500), US30, USDCAD, USDJPY, XAGUSD, XAUUSD. **EURJPY y USDCHF no están en este conjunto**.
- **G0 diferente:** [run #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334) tiene M1 nativa retenida para nueve símbolos, G0 cubre 2025-09→2026-09. No confundir M5 CIBO con esas velas M1 ni rebautizar series. Los artefactos con 10 años llevan `research_evidence_consumed=true`, por ello **NUNCA OOS VIRGEN**.
- El propietario identifica la fuente histórica como **cTrader de IC Markets**; los manifests inspeccionados muestran `provider_symbol`, `provider_symbol_id` y `UNVERIFIED_PROVIDER_SESSION_CALENDAR`, pero no prueban por sí solos el servidor/nombre de broker ni conservan bid/ask negociable en cada M5. La identidad exacta broker/cuenta/servidor, sesiones, spread/commission/fills y rollovers quedan `PROVIDER_VERIFICATION_PENDING`. No negar que el usuario dispone de esos datos; localizarlos o conservar evidencia positiva adicional.
- Fuentes selladas: solo leer los artefactos citados (ninguna captura nueva, VPS o live); manifest + SHA256 RAW_M5_LEDGER y fechas as-of. No alterar fuentes ni seleccionar años por su P&L.

## Fuente causal propuesta

La demanda institucional de cobertura/rebalanceo alrededor del benchmark WMR 16:00 Europe/London podría crear una presión transitoria de precio. **No observamos las órdenes desde OHLC**: únicamente un proxy direccional antes del evento. Probar primero si la geometría del retorno posterior depende de esa presión por encima de una hora placebo. **Cualquier efecto bruto puede ser inaccesible económicamente.**

## Test primario congelado — UNA definición, cero barridos de parámetros

- **Activo primario:** EURUSD. GBPUSD y USDJPY son replicaciones *posteriores*, no selección del mejor resultado. Moneda/base consistente, retornos en bps de precio, SIN P&L ni sizing.
- **Reloj:** `Europe/London` IANA y calendario local lunes–viernes, DST GMT/BST automático, fechas 2016-09-17 a 2026-09-17 exclusiva. Sin eliminación de feriados basándose en P&L; solo censura de M5 efectivamente ausente. El benchmark económico es 16:00 Londres (NO tratamos 16:00 como fill).
- **Formación primario (FIX):** OHLC M5 completas en opens locales 15:30, 15:35, 15:40, 15:45, 15:50. Proxy de presión = `10000 * log(close_M5_15:50 / open_M5_15:30)`, conocido a las **15:55** local, antes del inicio de la post-fix measurement.
- **Formación placebo de otra hora:** 13:30, 13:35, 13:40, 13:45, 13:50; presión análoga, conocida 13:55 local.
- **Clasificador causal:** alta presión si `abs(proxy_bps) >= percentil 75` calculado **solo con los 120 últimos días locales con formación M5 completa** de ESA franja, anteriores a la fecha evaluada; mínimo 120 observaciones de formación históricas, sin usar outcomes ni fills futuros para cambiar el cuantil. Una presión cero no produce dirección y se censura con motivo. No ajustar 75%, 120 días ni horario después de inspección.
- **Retorno de reversión FIX:** entrar hipotéticamente al `open` M5 de 16:05 Londres, cerrar al `open` M5 de 16:30. **16:05 ya queda después del benchmark nominal** pero falta cotejar ventana oficial WMR y ejecución real. Retorno firmado en bps `-sign(pressure)*10000*log(exit_open / entry_open)`. Precio abierto M5 es **proxy**, no fill broker. Para placebo usar 14:05→14:30, horizonte idéntico de 25 minutos. Sin stop/target optimizados.
- **Cohorte común:** una observación potencial por día local. Se requiere formación válida, histórico previo completo, entry/exit M5 en **ambas** franjas. Sin ffill, interpolación, OHLC inventado, ni retención asimétrica de una rama del control. Registrar todos los días/códigos de descarte y periodo, incluso ceros.
- **Endpoint primario único:** diferencia de diferencias (bps brutos)
  `D = (E[rev_FIX | high_FIX]-E[rev_FIX | low_FIX]) - (E[rev_PLACEBO | high_PLACEBO]-E[rev_PLACEBO | low_PLACEBO])`.
  Impide confundir mean reversion genérica de movimientos fuertes con un efecto específico del fixing. Un placebo solo no establece causalidad macro, pero reduce falsa atribución horaria.
- **Incertidumbre:** bootstrap 2000 remuestreos de bloques ISO-semana (mismo día y shock se remuestrean juntos), RNG determinista semilla `941102`, intervalo percentil 95%. Reportar conteos high/low por franja, tasas de datos faltantes, distribución por año, tamaño medio bps de cuatro brazos y CI. `UNDERPOWERED` si cualquier celda tiene menos de 50 observaciones o menos de 300 fechas comunes; reportar, no rescatar.
- **Falsación:** `DEV_GROSS_NO_SUPPORT` si CI95 de D incluye 0 o D<=0; `DEV_GROSS_POTENTIAL` solo si CI95 inferior >0 con suficiente muestra. **Ninguno implica edge neto**. La familia se rechaza económicamente si precios ejecutables y costes realistas eliminan el rendimiento, el efecto es previo a la entrada, no sobrevive delay+1 M5, desaparece fuera de sample o empeora frente a benchmarks predefinidos.
- **Controles secundarios no seleccionables:** exploración descriptiva por año calendario (NO elegir año ganador); 1 M5 delay de entrada 16:10→16:30 y placebo 14:10→14:30; resumen divergencia por fijaciones de fin de mes. No cambiar endpoint primario ni threshold por esos resultados.
- **Multiplicidad:** no seleccionar mejor de las doce fuentes; primario es EURUSD. Sus réplicas tienen prioridad GBPUSD, luego USDJPY, solo tras test EURUSD y con reglas idénticas; todas las comparaciones deben reportarse. No reinterpretar pruebas de tres mercados como un único ensayo sin ajuste.

## Barreras de promoción irreductibles

Resultado G1 = **desarrollo exploratorio previamente consumido**; el CI no corrige investigación anterior del mismo dataset. Debe quedar estado `OOS_BLOCKED` hasta obtención de feed/periodo cronológico realmente no inspeccionado. Como M5 carece de BID/ASK operable por orden, se prohíbe convertir retorno bruto en Profit Factor real, Sharpe, Sortino o drawdown de cuenta. Para certificación: fuente exacta cTrader IC Markets con detalle de trading hours y spreads/comisiones/bid-ask reales, reglas de cierre/días festivos, prueba bajo coste 1x/1.5x/2x, y luego nuevo OOS. G1 puede mostrar que no hay relación sin medir costes, no su viabilidad económica.

## Entregables en GitHub (sin VPS/producción)

`qore_native_reset_fix_g1_v1.py` neutral lector M5 firmado; fixtures causales no lookahead/DST/missingness; workflow Actions leyendo artefactos `#10475354631` y agregado `#10476615509` con sha exactos; resultados JSON CSV y reporte con Action run, SHA, veredicto sobrio. No tocar CIBO, QDLE, Shared, MT5 ni código productivo. Fuente original solamente lectura; tests de invariancia por prefijo.
