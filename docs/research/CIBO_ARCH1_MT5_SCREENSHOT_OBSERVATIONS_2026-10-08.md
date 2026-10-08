# CIBO Arquitecto 1 — Evidencia MT5 observada (capturas usuario, 2026-10-08)

**Rama propietaria:** `agent/cibo-architect-1-cognitive-trade-ops-20261008` · **Issue:** #737 · **PR:** #742.  
**Clase de evidencia:** capturas de pantalla de especificaciones instrumentales en una aplicación MT5 móvil facilitadas por el propietario. Esta transcripción NO es una llamada autenticada `symbol_info`/`account_info`, una cotización activa, una comprobación de comisión al cerrar ni una confirmación de FundedNext sobre reglas del proveedor. No se publican imágenes ni datos de acceso o cuentas del propietario en el repositorio público.

## Observaciones visuales de MT5 — primera serie y ampliación de GBPJPY (tres capturas adicionales, reloj del teléfono ~20:06 sin zona verificada)

| Propiedad mostrada | XAUUSD | NDX100 (NAS100) | EURUSD | GBPJPY |
|---|---|---|---|---|
| Contract size / 1 lote | 100 | 10 | 100.000 | 100.000 GBP |
| Tick size | 0,01 | 0,01 | No visible | No visible |
| Tick value por 1 lote | USD 1 | USD 0,10 | No visible | No visible |
| Profit currency | USD | USD | USD | JPY |
| Margin currency | USD | USD | EUR | GBP |
| Volume min / max / step | 0,01 / 50 / 0,01 | 0,01 / 40 / 0,01 | 0,01 / 40 / 0,01 | 0,01 / 40 / 0,01 |
| Spread | Flotante | Flotante | Flotante | Flotante |
| Estimado margen BUY en USD por 1 lote (pantalla) | ~53.637,48 | ~61.481,98 | ~3.735,03 | ~4.410,30 (nueva captura) |
| Estimado margen SELL en USD por 1 lote | ~53.629,68 | ~61.478,78 | ~3.734,77 | ~4.409,90 (nueva captura) |
| Swap long mostrado, en puntos | -107,151 | -372,912 | -13,472 | -25,806 |
| Swap short mostrado, en puntos | -46,917 | -57,6 | +0,107 | -44,278 |
| Multiplicador swap triple | Miércoles | Viernes | Miércoles | Miércoles |
| Comisión de entrada visible | 0,0016% en USD por lote (BASE INDETERMINADA) | NO VISIBLE | USD 7/lote, `transacciones de entrada` | USD 7/lote, `transacciones de entrada` |

Los márgenes monetarios por 0,01 lote derivados linealmente de los valores aproximados de la pantalla serían XAU BUY USD536,3748, NDX BUY USD614,8198, EUR BUY USD37,3503 y GBPJPY BUY ~USD44,1030 según nueva captura (antes ~USD44,0740). **Son referencias visuales redondeables, NO cotizaciones ejecutables; el cálculo oficial del margen es `order_calc_margin` / `order_check` en el momento causal**. Verificar caso netting/hedging, crédito, posiciones simultáneas y reglas de FundedNext.

### Condiciones de negociación visibles

- XAUUSD: precisión 2, compra/venta por mercado, modos Todo/Nada y Todo/Parte, órdenes Market/Limit/Stop/Stop-Limit/SL/TP. Sesiones de *trading* de lunes a viernes 01:15–24:00 (hora del servidor **no identificada**), cotización 01:00–24:00.
- NDX100: precisión 2, mercado, Todo/Nada y Todo/Parte, tipos Market/Limit/Stop/Stop-Limit/SL/TP; trading lunes 01:15–24:00, martes–jueves 00:00–00:00 y 01:15–24:00, viernes 01:15–24:00, **tal como se muestra**, sin interpretar la semántica de 00:00–00:00 sin comprobación del servidor.
- EURUSD: precisión 5, trading lunes–viernes 00:15–23:55, cotización 00:00–24:00; contrato 100.000, divisa margen EUR, beneficio USD; modos Todo/Nada y Todo/Parte.
- GBPJPY (nuevas capturas): precisión 3, contrato 100.000 GBP por lote, moneda de margen GBP y de beneficio JPY, spread flotante, stops level 0, mínimo 0,01 / máximo 40 / step 0,01; órdenes Market/Limit/Stop/Stop Limit/SL/TP, ejecución por mercado, fill Todo/Nada y Todo/Parte, sesiones de cotización de lunes a viernes 00:00–24:00 y *trading* lunes–viernes 00:15–23:55, **hora de servidor por confirmar**. Swap largo -25,806 puntos, corto -44,278 puntos y multiplicador triple el miércoles. Nueva referencia de margen BUY ~USD4.410,30 y SELL ~USD4.409,90 por 1 lote; en la primera serie BUY/SELL ~USD4.407,40. La diferencia demuestra dos fotos de la interfaz en momentos distintos, NO una serie de márgenes autenticados. La captura de comisiones sigue indicando **USD7/lote para transacciones de entrada**, sin verificar cierre.


### Ampliación de GBPJPY: consecuencias matemáticas sin fabricar riesgo USD

- **Las dos capturas no presentan el mismo margen.** Primera serie: ~USD4.407,40 por 1 lote BUY/SELL. Captura posterior (reloj móvil ~20:06 sin fecha/zona de servidor): ~USD4.410,30 BUY y ~USD4.409,90 SELL. Diferencia visual BUY +USD2,90 por lote, que NO debe codificarse como margen estable ni como spread; validar por `order_calc_margin` justo al decidir.
- El tamaño del contrato corresponde a **100.000 GBP/lote**, pero ganancias y pérdidas de GBPJPY se producen en **JPY**, no en GBP ni necesariamente en USD. El riesgo USD al stop requiere valorar exactamente lado, precio previsto, SL, volumen, conversión JPY/USD y costes con `order_calc_profit` broker-native, además de fees. Incluso si se infiere valor JPY por pip en una fórmula Forex simple, no se debe convertir a USD con FX histórica inventada.
- Las tarifas USD7 por lote se muestran en el apartado de *transacciones de entrada*. **No afirmar USD7 round-trip** ni duplicar/cerrar tarifas sin prueba del broker. Swaps en puntos con triple miércoles no son USD y dependen de la posición, cambio de rollover y fecha servidor.
- Una captura de propiedad que indica 0,01 mínimo y 40 máximo NO autoriza cualquier lote: QDLE debe intersectar el presupuesto de riesgo por operación (5% del NAV QORE dinámico o menos), stops/costes, QORE Risk, margen libre MT5 y restricciones provider. CIBO solo administra la posición después de un fill real y emite propuestas; Trader gateway autentica ejecución.
- **Fuente de los tres valores adicionales:** tres capturas móviles de GBPJPY proporcionadas en la conversación; información documental, no `symbol_info` autenticado ni recibo de `order_send`. NO LIVE.

### Consecuencias para CIBO Arquitecto 1

1. CIBO comprueba **Bid para liquidación de BUY** y **Ask para liquidación de SELL**, sin usar el precio Bid del gráfico como precio favorable universal.
2. Diferencia exposición contractual, margen broker, volatilidad, riesgo hasta SL y coste de mantener la posición. Los swaps son **puntos**, NO importes USD por defecto.
3. Si spread o datos temporales son obsoletos, emite advertencia/revisión, no un SL/TP óptimo inventado. **No se puede prometer que SL limita pérdida real**: gaps/slippage y costes pueden superarlo.
4. Distingue `ORDER_SUBMITTED`, `PARTIAL`, `FILLED`, `MANAGED`, `CLOSED` usando recibos de broker; la presencia de fill modes Todo/Parte obliga al manejo de parciales. Tipo de ejecución de mercado NO confirma que una orden concreta se haya ejecutado.
5. Utiliza sólo las sesiones con zona/horario servidor verificado; no programar señales o cerrar posiciones con la hora 15:19 del móvil ni asumir que sea hora servidor.
6. Comisión EURUSD/GBPJPY USD7/lote **entrada** no demuestra tarifa round-trip USD7. El texto XAU “0,0016% en USD por lote” requiere base y cargos de ambas patas. **NDX sin comisión observada no equivale a comisión cero**.
7. Tras nuevos deals, recalcular riesgo a SL con valoración broker, patrimonio QORE reconciliado, cuatro decisiones económicas independientes y QDLE como autoridad única de lotaje.
8. Ningún valor económico de estas capturas certifica PnL del replay 2019–2022 ni el NAV final. La vigencia y autenticidad broker actual deben verificarse con consulta MT5 de solo lectura.

### Próxima adquisición obligatoria (Arquitectos 2/3)

- `account_info` seguro (sin secretos), `symbol_info` y `symbol_info_tick` para las seis especies reales; `order_calc_profit` BUY/SELL hasta SL y `order_calc_margin` con volúmenes legales.
- Tarifas de **entrada y salida**, spreads/ticks, swap conversión/rollover y NDX total fees; validación de base porcentual oro.
- Moneda/cuenta y reglas de pérdida diaria/máxima y piso FundedNext; no inferirlos del margen screenshot.
- Completar la validación read-only actual de AUDJPY y GBPUSD y contrastar la nueva ficha completa de GBPJPY con `symbol_info`, en particular `trade_tick_value_profit`/`loss` y conversión JPY→USD; no interpretar el dato como dólar fijo por pip.
- MT5 deal-history autenticado para certificar fills, partials, realized PnL y costes.

**Estado:** evidencia SCREENSHOT_OBSERVED / LIVE_AUTHENTICATION_PENDING / FINANCIAL_CERTIFICATION_REJECTED. PR #742 permanece DRAFT / NO LIVE.
