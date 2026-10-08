# CIBO Arquitecto 1 — Evidencia MT5 observada (capturas usuario, 2026-10-08)

**Rama propietaria:** `agent/cibo-architect-1-cognitive-trade-ops-20261008` · **Issue:** #737 · **PR:** #742.  
**Clase de evidencia:** capturas de pantalla de especificaciones instrumentales en una aplicación MT5 móvil facilitadas por el propietario. Esta transcripción NO es una llamada autenticada `symbol_info`/`account_info`, una cotización activa, una comprobación de comisión al cerrar ni una confirmación de FundedNext sobre reglas del proveedor. No se publican imágenes ni datos de acceso o cuentas del propietario en el repositorio público.

## Observaciones legibles en la primera serie de diez capturas

| Propiedad mostrada | XAUUSD | NDX100 (NAS100) | EURUSD | GBPJPY |
|---|---|---|---|---|
| Contract size / 1 lote | 100 | 10 | 100.000 | No visible en recorte |
| Tick size | 0,01 | 0,01 | No visible | No visible |
| Tick value por 1 lote | USD 1 | USD 0,10 | No visible | No visible |
| Profit currency | USD | USD | USD | No visible |
| Margin currency | USD | USD | EUR | No visible |
| Volume min / max / step | 0,01 / 50 / 0,01 | 0,01 / 40 / 0,01 | 0,01 / 40 / 0,01 | No visible |
| Spread | Flotante | Flotante | Flotante | No visible |
| Estimado margen BUY en USD por 1 lote (pantalla) | ~53.637,48 | ~61.481,98 | ~3.735,03 | ~4.407,40 |
| Estimado margen SELL en USD por 1 lote | ~53.629,68 | ~61.478,78 | ~3.734,77 | ~4.407,40 |
| Swap long mostrado, en puntos | -107,151 | -372,912 | -13,472 | Recortado / no usar |
| Swap short mostrado, en puntos | -46,917 | -57,6 | +0,107 | -44,278 |
| Multiplicador swap triple | Miércoles | Viernes | Miércoles | Miércoles |
| Comisión de entrada visible | 0,0016% en USD por lote (BASE INDETERMINADA) | NO VISIBLE | USD 7/lote, `transacciones de entrada` | USD 7/lote, `transacciones de entrada` |

Los márgenes monetarios por 0,01 lote derivados linealmente de los valores aproximados de la pantalla serían XAU BUY USD536,3748, NDX BUY USD614,8198, EUR BUY USD37,3503 y GBPJPY BUY USD44,0740. **Son referencias visuales redondeables, NO cotizaciones ejecutables; el cálculo oficial del margen es `order_calc_margin` / `order_check` en el momento causal**. Verificar caso netting/hedging, crédito, posiciones simultáneas y reglas de FundedNext.

### Condiciones de negociación visibles

- XAUUSD: precisión 2, compra/venta por mercado, modos Todo/Nada y Todo/Parte, órdenes Market/Limit/Stop/Stop-Limit/SL/TP. Sesiones de *trading* de lunes a viernes 01:15–24:00 (hora del servidor **no identificada**), cotización 01:00–24:00.
- NDX100: precisión 2, mercado, Todo/Nada y Todo/Parte, tipos Market/Limit/Stop/Stop-Limit/SL/TP; trading lunes 01:15–24:00, martes–jueves 00:00–00:00 y 01:15–24:00, viernes 01:15–24:00, **tal como se muestra**, sin interpretar la semántica de 00:00–00:00 sin comprobación del servidor.
- EURUSD: precisión 5, trading lunes–viernes 00:15–23:55, cotización 00:00–24:00; contrato 100.000, divisa margen EUR, beneficio USD; modos Todo/Nada y Todo/Parte.
- GBPJPY: la captura solo alcanza comisión, swaps y margen; falta transcripción de propiedades/tipo de contrato/min/max y cambio de divisa.

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
- Capturas faltantes de AUDJPY y GBPUSD y propiedades completas de GBPJPY (si no están accesibles, no inventar).
- MT5 deal-history autenticado para certificar fills, partials, realized PnL y costes.

**Estado:** evidencia SCREENSHOT_OBSERVED / LIVE_AUTHENTICATION_PENDING / FINANCIAL_CERTIFICATION_REJECTED. PR #742 permanece DRAFT / NO LIVE.
