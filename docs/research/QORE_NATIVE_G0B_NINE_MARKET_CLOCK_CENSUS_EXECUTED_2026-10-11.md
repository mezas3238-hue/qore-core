# QORE NATIVE — G0B ejecutado: relojes IANA, presencia M1 por ventana y sincronía estricta

**Fecha:** 2026-10-11. **Estado:** `G0B_OBSERVABILITY_EXECUTED / PROVIDER_CALENDAR_UNVERIFIED / G1_NOT_EXECUTED`. **No edge ni datos de rentabilidad, no VPS/MT5/live.**

**Prerregistro ANTES del censo:** [G0B prereg](../research/QORE_NATIVE_G0B_CALENDAR_DST_COVERAGE_PREREG_2026-10-11.md) commit `8e61751dc31f5ec1af540f2dffb698360ec8b270`. **Ejecución:** [GitHub Actions #38168771260](https://github.com/mezas3238-hue/qore-core/actions/runs/38168771260), commit `788e9c6f1f57e29e342a909d8397f76f6e3ea1e6`. `clock_contract` SUCCESS, `nine_market_observability` SUCCESS; **6/6 tests PASS**. [Artifact #11713790030](https://github.com/mezas3238-hue/qore-core/actions/runs/38168771260/artifacts/11713790030), JSON + CSV diario (3.393 cohortes fecha-ventana/instrumento; 90d retention).

**Origen:** bitmaps G0 de nueve fuentes M1, [G0 SUCCESS run #38166675573](https://github.com/mezas3238-hue/qore-core/actions/runs/38166675573), commits y 9 digests de entrada archivados dentro del JSON. Ninguna consulta de OHLC/precios, trades, forward returns ni PF.

**SHA256 de resultados G0B:**
- JSON `qore-native-G0B-calendar-observability.json`: `fb58044033c5eaf46d5f42c971f52b2f7b3f4f751166461eeb608b2f541c9eba`
- CSV `qore-native-G0B-per-day-window-census.csv`: `dad68a0b3368184025673a4516be3f4f1233c393a97e169a2ee727fd9e75c062`

## 1. DRIVE — ventana NOMINAL 09:30–11:00 Nueva York

261 fechas locales nominales lunes–viernes × 90 minutos = 23.490 minutos teóricos cada símbolo. Es **presencia de datos**, no horario de negociación certificado.

| Símbolo | M1 presentes / nominal | Cobertura | Fechas 100% | M15 cerradas 15/15 / M15 contenidas | H1 cerradas 60/60 / H1 contenidas |
|---|---:|---:|---:|---:|---:|
| EURUSD | 23.310 / 23.490 | 99,2337% | 259/261 | 1.554 / 1.566 | 259/261 |
| GBPUSD | 23.310 / 23.490 | 99,2337% | 259/261 | 1.554 / 1.566 | 259/261 |
| NAS100 | 23.220 / 23.490 | 98,8506% | 258/261 | 1.548 / 1.566 | 258/261 |
| XAUUSD | 23.220 / 23.490 | 98,8506% | 258/261 | 1.548 / 1.566 | 258/261 |

Ausencias de toda la ventana: todos los símbolos 2025-12-25 y 2026-01-01; además NAS100 y XAUUSD 2026-04-03. **Causa no certificada**: no clasificar como problema ni festivo de broker sin calendario y evidencia contractual.

## 2. RESET — ventana NOMINAL 15:45–16:15 Londres

261 días × 30 = 7.830 minutos nominales por símbolo. EURUSD, GBPUSD, USDJPY: **7.770/7.830 (99,2337%)**, **259/261 días 100%**; 518/522 buckets M15 contenidos cerrados 15/15. Dos días enteramente ausentes: 2025-12-25 y 2026-01-01. No hay bucket H1 totalmente contenido en media hora, por diseño; **0/0**, no es defecto de H1.

La metodología oficial WMR documenta el *benchmark* de 16:00 Londres, NO la rentabilidad de un trade ni su ventana de ejecución. Auditoría nominal usa Europe/London y DST sin offset fijo.

## 3. RELATIVE — sincronía exacta de dos M1 por minuto, sin forward fill

Londres nominal 08:00–12:00, 261×240=62.640 minutos por pareja:

| Pareja | Intersecciones / nominal | Cobertura | Días 100% | Ausencia solo A / solo B / ambas |
|---|---:|---:|---:|---:|
| EURUSD / GBPUSD | 62.136 / 62.640 | 99,1954% | 256/261 | 2 / 0 / 502 |
| AUDUSD / GBPUSD | 62.137 / 62.640 | 99,1970% | 257/261 | 1 / 0 / 502 |
| AUDJPY / GBPJPY | 62.138 / 62.640 | 99,1986% | 258/261 | 0 / 0 / 502 |

NY nominal 09:00–11:00, 261×120=31.320 minutos por pareja: **31.080/31.320 (99,2337%)** en las tres, **259/261 días 100%**, 240 minutos no observados simultáneamente. Sin forward fill, sin inferir hedge beta o cointegración.

### Fechas para adjudicar, no eliminar ex-post

- 2025-12-25 y 2026-01-01: ausencia de todo el tramo en los instrumentos/parejas seleccionados.
- 2026-04-03: NAS100 y XAUUSD faltan 90/90 en NY DRIVE; en Londres RELATIVE EURUSD/GBPUSD faltó 1/240.
- 2025-10-24: AUDUSD/GBPUSD Londres faltó 1/240.
- 2025-12-26: EURUSD/GBPUSD Londres faltó 1/240.
- 2026-06-15: EURUSD/GBPUSD y AUDUSD/GBPUSD Londres presentaron 218/240 minutos comunes (22 ausentes). **Revisar evidencia original y fuentes por cada minuto** antes de clasificar causa.

Los 502 minutos de ausencia simultánea Londres contienen fechas y huecos potencialmente regidos por calendarios, pero no se atribuye causalidad con bitmaps únicamente. El denominador usa *todos* los días locales lunes–viernes, sin excluir feriados: un festivo broker certificado podría cambiar la cobertura esperada; esa corrección requiere preregistro de regla y fuente independiente, nunca borrar una fecha porque reduce porcentajes.

## 4. Qué demostró G0B y qué NO demostró

**Acreditado:** lectura y recuento consistente de los nueve bitmaps; IANA `America/New_York` y `Europe/London` manejan DST (NY 2026-03-06 09:30→14:30 UTC y 2026-03-09→13:30 UTC; London 2026-03-27 16:00→16:00 UTC y 2026-03-30→15:00 UTC); conteo de días y M15/H1 contenidos; emparejado al minuto exacto sin rellenar; dos jobs SUCCESS y seis tests.

**No acreditado:** calendario de negociación real de *este* proveedor; identidad contractual NAS100/XAUUSD CFD/spot/futuros; festivos/cierres del proveedor; bid/ask, spreads por hora, slippage, coste dos piernas; capacidad de ejecución; ninguna hipótesis G1, método de entrada, ventaja, PF/Sharpe/DD; OOS genuinamente virgen. Horario GC o MNQ de CME **no** certifica feed NAS100/XAUUSD de un CFD.

**Veredicto:** `G0B_CLOCK_CENSUS_PASS` técnico, `PROVIDER_SESSION_CERTIFICATION_PENDING`; estado por símbolo/ventana `SOURCE_PARTIAL_PROVIDER_UNVERIFIED`. **0/3 traders certificados, 0/3 motores nativos, 0 resultados económicos.**

## 5. Órdenes técnicas para el siguiente paso

1. Obtención y fijación SHA de ficha de contrato exacta/broker por símbolo, zona de timestamp, horario efectivo y feriados de 2025-09–2026-09 (incluidos NAS100/XAUUSD); auditar y atribuir missingness, con `UNKNOWN` donde no haya prueba. Antes de mover calendar gate, informe por día/cierre y política de censura fija.
2. Comprobar los 22 minutos de 2026-06-15 en fuente G0, y los puntos únicos de 2025-10-24, 2025-12-26 y 2026-04-03. Separar incidencia multiactivo de hora de cierre sin declarar outage por inferencia.
3. Preservar SHA, JSON, CSV y bitmaps frente a vencimiento de artifacts. Archivo actualmente reproducible con run y hashes, pero 90 días de retención no es conservación permanente.
4. Escribir **tres prerregistros independientes G1** (DRIVE, RESET, RELATIVE), elegir una primaria y sus comparaciones antes de mirar retornos. No hacer backtest condicionado hasta fijar calendario/censura y evidencia de proveedor.
5. Definir por mercado fuente de costes reales observados, documentar futuros costes asumidos como `ASSUMED`, bloquear certificación con `OOS_BLOCKED` hasta obtener época o proveedor verdaderamente no inspeccionados.

**Fuentes institucionales de referencia, sin transponer a broker:** WMR https://www.refinitiv.com/content/dam/marketing/en_us/documents/methodology/wm-refinitiv-methodology.pdf ; CME MNQ https://www.cmegroup.com/articles/faqs/micro-e-mini-equity-index-futures-frequently-asked-questions.html ; COMEX GC https://www.cmegroup.com/markets/metals/precious/gold.timeAndSales.html .
