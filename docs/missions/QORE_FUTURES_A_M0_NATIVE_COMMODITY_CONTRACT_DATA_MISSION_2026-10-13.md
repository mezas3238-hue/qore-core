# QORE FUTURES A — Misión M0: fuentes nativas y causalidad antes del primer PnL

**Estado a 2026-10-13:** M0 INICIADA, investigación de disponibilidad/licencias; **NO HAY FUENTE CONTRATOS AUTÉNTICOS INGESTADA NI BACKTEST ECONÓMICO**. [Issue rector #894](https://github.com/mezas3238-hue/qore-core/issues/894).

## Mandato explícito y separación de QORE Native

Usuario autorizó comenzar una investigación nueva tras el cierre científico de FX carry en [ADR #893](https://github.com/mezas3238-hue/qore-core/pull/893); la misión es **futuros de materias primas negociados**, estrategia eventual diaria/semanal, NO FX, NO CFD, NO scalping sin libro de órdenes. Este documento NO abre las hipótesis previamente cerradas ni reutiliza como OOS la partición FX: ningún dato económico o retorno posterior a 2024-09-16 de QORE Native se leerá. No se compran datasets ni se habilitan brokers sin autorización del propietario.

**Enfoque M0 de un solo ciclo:** verificar derechos de uso, términos exactos y disponibilidad contractual. Si falta un insumo, retornar `BLOCKED_DATA_OR_LICENSE` y parar, no improvisar proxies ni iniciar una cadena de “preflights”.

## Universo fijo para cualificación

| Segmento | CME root | Venue | Producto | Exigencia |
|---|---|---|---|---|
| Energía | CL | NYMEX | WTI light sweet crude | contratos nativos por mes |
| Energía | NG | NYMEX | natural gas | contratos nativos por mes |
| Metales | GC | COMEX | gold | contratos nativos por mes |
| Metales | HG | COMEX | copper | contratos nativos por mes |
| Granos | ZC | CBOT | corn | contratos nativos por mes |
| Granos | ZS | CBOT | soybean | contratos nativos por mes |

No sumar más mercados porque los resultados sean adversos. La serie ajustada continua puede usarse **solo como visualización de referencia**; nunca reemplaza `exchange+native_contract+expiration` para curva, señal ni cash flow. Contratos con meses de vencimiento específicos, tick, multiplicador, divisa, settlement, volumen, OI, notificación de entrega de bolsa **cuando corresponda**, último trading day y cutoff de liquidación que impone el broker verificados por período real. **No presumir que first-notice es anterior al último día de negociación para todos los productos**. Mantener el shape UMI-05 (`FuturesContractTerms`), pero no inferir que UMI-05 o adaptadores PAPER contienen una fuente histórica fiable ni están autorizados a operar.

## Fuente prioritaria realmente comprobada (catálogo, NO cuenta/licencia)

**CME DataMine**, [portal oficial](https://www.cmegroup.com/datamine.html), ofrece datasets históricos de *Settlements* y futures/options. [CME Settlement FAQ](https://www.cmegroup.com/articles/faqs/access-to-cme-group-settlement-data-faq.html) distingue disponibilidad y retraso de web versus MDP y DataMine, indica adquisiciones/licencias; nunca deducir que la vista gratuita de web cubra años completos con timestamp histórico de primera publicación. [Settlement contract glossary](https://www.cmegroup.com/trading/about-settlements.html) advierte que algunos precios de contratos sin OI ni volumen no derivan de operaciones reales y que OI puede corresponder a día previo según fase del boletín.

Para catalogar, elegir dataset mínimo **contract-by-contract EOD** con settle por `trade_date, contract_year_month, venue`, volumen, OI y, si están publicados, datos de expiración/listado, roll calendars, tick/multiplier y *first notice*. **No comprar Continuous Price Series para usarla como cash return tradable**: CME [Continuous Price Series](https://datamine.new.cmegroup.com/catalog?category=COPR&sort=name%3Aasc) define ACTIVE con selección basada en análisis histórico, mientras FRONT tiene su propio roll; ambos tienen riesgo de roll retrospectivo/cadena ajustada. Solo native contract bars/settlements admitidos.

CME DataMine es **candidato**, no contrato validado ni feed habilitado. Precio, licencia, derechos de descarga y retención, y permisos de uso algorítmico redistributivo deberán obtenerse por escrito. **Presupuesto de compra autorizado = $0**; el propietario debe aprobar coste monetario/periodo antes de adquisición. Evitar citar un precio genérico como cotización de seis productos.

La CFTC dispone de [COT histórico](https://www.cftc.gov/es/node/128971); USDA [WASDE archives](https://usda.azureedge.us/about-usda/general-information/staff-offices/office-chief-economist/commodity-markets/wasde-report) ofrece registros agrícolas. **NO incluir COT ni WASDE en la primera hipótesis**; necesitarían pruebas separadas de lag de publicación y controles de vintage. Prohibido meter señales alternativas para salvar una curva adversa.

## M0 — criterios verificables: cada uno obligatorio

- **A. Legal/cadena:** licencia expresa que permita descarga histórica, investigación y almacenamiento interno; evidencia de fuente/entitlement y retention/redistribution, cuenta que el usuario controle; sin credenciales ni datos raw en GitHub. Identificar proveedor, dataset_id, versión, ruta/fecha del snapshot, SHA-256 original y derechos.
- **B. Contract geometry:** `venue, root, native contract id, contract-month, last trading day, FND o criterio de delivery cutoff, tick_size, multiplier, currency` por fila/instrumento; no mezclar CFD/spot o *continuous adjusted synthetic* con futuros físicos. Transiciones de contrato especificadas antes de leer PnL y roll **antes del primer aviso/vencimiento** cuando aplique; confrontar cambio de especificaciones histórico.
- **C. Primera y segunda pata de curva:** misma *trade_date* con precio settle nativo y procedencia para al menos dos contratos diferentes elegibles del mismo root, expiry en orden, volumen y OI con referencia exacta. Distinguir sesiones festivas/sin trading, revisiones y precios indicativos sin volumen. La regla económica futura no puede consumir OI/tasa hasta su timestamp de publicación real.
- **D. Reloj causal:** conservar tanto `exchange_trade_date` como `first_published_at` UTC o fuente demostrable conservadora (p. ej. embargo hasta el siguiente día tras publicación documentada). Información usable únicamente si `published_at <= timestamp_decision`. Trading usando settlement del día d y llenado al mismo settle d **prohibido**. Datos revisados deben llevar versión/fecha de revisión.
- **E. Contabilidad real:** valor del tick, USD-PnL por `(exit_price-entry_price)×contract_multiplier×contracts`, entradas/salidas/roll de patas como operaciones reales, costos exchange/broker/clearing/market-data + spread/slippage y margen/liquidez/riesgo. Roll gap de dos contratos **no es retorno**. Valores negativos WTI son legales: 20-abr-2020 May CL settle **−$37.63/bbl**, según [CFTC](https://www.cftc.gov/PressRoom/PressReleases/8315-20); log-retornos sobre precios <=0 prohibidos. El motor eventual debe funcionar por diferencia de precio y PnL USD, no retornos log forzados.
- **F. Historia/cobertura:** intervalo candidato **2012-01-01→2024-09-16**, no promesa de existencia. Para primer cálculo mínimo: >= 8 años de 6 root completos por trading day relevantes y 2 vencimientos eligible; un catálogo no acredita 8 años. Segmentos DEV/DIAG/HOLDOUT se fijarán antes del primer PnL, sin usar el holdout FX de 2024-09-17 en adelante. Cualquier ausencia de fuente histórica, licencia o costes => STOP M0. No bajar requisitos tras observar economía.

### Salida formal M0

`SOURCE_READY_FOR_PREREG` **solo tras verificar fuente auténtica y recibo de datos efectivamente disponibles**, cobertura y una muestra causal con contratos completos, licencia y costes. El checker sintético solo demuestra que la **FORMA del contrato de fuente** es auditable; ejecutarlo sobre mocks jamás convierte M0 en listo.

`BLOCKED_DATA_OR_LICENSE` si el proveedor/derechos/contratos/costos no están acreditados. Fuente candidata no es fuente disponible. Bajo el estado vigente: **M0_SOURCE_NOT_YET_ACQUIRED**.

## Una sola hipótesis económica posterior (CONDICIONAL, NO probada ni preregistrada todavía)

Mecanismo candidato: exposición diaria/semanal a *pendiente term structure / backwardation vs contango* usando first+second verdaderamente disponibles, fechas de entrega, riesgo normalizado **con PnL de contratos**, y regla de roll causal. No elegir señal, pesos, risk target, stop/target, fechas, denominador ni el umbral de rentabilidad mediante backtesting preliminar. La aprobación M0 dará derecho a **un preregistro cerrado nuevo**, no a una búsqueda de muchas variantes.

**Regla de paro de recursos:** finalizar M0 en una única decisión de compra/fuente por el propietario. Sin licencia/dataset nativo válido: NO PnL, NO optimización ni descarga “free” de proxies fabricados. Si adquirido: congelar hipótesis antes de mirar retornos y usar holdout nuevo nunca consultado.

## Estado separado e invariantes

- QORE Native FX carry: [ADR #893](https://github.com/mezas3238-hue/qore-core/pull/893) vigente; 0/3 nuevos traders certificados. No reinterpretar CFD M5 previo como futures.
- Componentes existentes QORE futures: `src/qore/infrastructure/derivative_contract_semantics.py` y docs UMI-05 son **semántica**, los adaptadores paper/sim no son feed de CME.
- No MT5, VPS, CIBO, Shared, QDLE, LIVE, órdenes, datos licenciados públicos, compras, ni credenciales. Esta fase no alcanza ni modifica capital real.

**Handoff arquitecto siguiente:** verificar fuente/derecho contractual CME exacto, obtener presupuesto explícito, correr checker con datos reales en almacenamiento privado y **decidir GO/NO-GO una vez**. Un archivo con mocks y 10 tests PASS no constituye licencia, cobertura ni edge.

### Enmienda M0 pre-económica — semántica de aviso / cutoff (13 octubre 2026)

El [aviso oficial de CME Clearing de mayo 2026](https://www.cmegroup.com/content/dam/cmegroup/notices/clearing/2026/05/chadv26-192.pdf) indica expresamente para **CL junio 2026** último trading **19 mayo**, aviso **21 mayo**, y para **NG junio 2026** último trading **27 mayo**, aviso **28 mayo**. Una validación universal `first_notice_date <= last_trade_date` habría rechazado contratos perfectamente legítimos (en ambos casos notice ocurre DESPUÉS de last trade). Corregido **ANTES de cualquier dataset real o PnL**: el checker distingue `exchange_first_notice_date` (opcional, cuando aplique) de `risk_liquidation_cutoff_date` (obligatorio; debe ser a más tardar último trade y, si existe notice, antes de notice). Un broker puede imponer un corte más temprano; verificar condiciones reales, no inventarlas por algoritmo. Si no se conoce un cutoff autorizado: **BLOCKED_DATA_OR_LICENSE**.
