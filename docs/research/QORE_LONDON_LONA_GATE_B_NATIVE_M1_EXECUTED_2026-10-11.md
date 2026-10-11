# QORE London LON-A — Gate B: auditoría M1 REAL ejecutada sin replay

**Fecha:** 2026-10-11; **Issue rector:** [#785](https://github.com/mezas3238-hue/qore-core/issues/785); **PR:** [#788](https://github.com/mezas3238-hue/qore-core/pull/788).  
**Veredicto de Gate B:** `SOURCE_SHA_VERIFIED / UTC_COVERAGE_AUDITED / NATIVE_D1_H4_M15_NOT_CERTIFIED / NO_FRESH_HOLDOUT / NO_ECONOMIC_REPLAY`.

## 1. Procedencia y ejecución validada

- GitHub Actions [run #38168967976](https://github.com/mezas3238-hue/qore-core/actions/runs/38168967976): `SUCCESS`, jobs de contrato sintético y dos pares `SUCCESS`. SHA `31e443213bd14a7e4af469fe46120fbe59e251dc`.
- Artefactos resultados: [EURUSD #11713076175](https://github.com/mezas3238-hue/qore-core/actions/runs/38168967976/artifacts/11713076175), [GBPUSD #11713630694](https://github.com/mezas3238-hue/qore-core/actions/runs/38168967976/artifacts/11713630694).
- Origen INMUTABLE: [source run #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334); SHA `18c338aedd5013ce65a6cb6408ffbc2e904a6217`; artefactos M1 cTrader original EURUSD `10618547852`, GBPUSD `10618811910`. Se verificó la declaración `provider_native_m1=true`, `synthetic_m1=false`, `interpolated_m1=false`, `contradictory_m1=0` y los SHA-256 de particiones originales 2025/2026 a partir del manifiesto.
- Auditoría sola: fechas `2025-09-17T00:00Z`–`2026-09-17T00:00Z`, período histórico **YA CONSUMIDO** en investigaciones anteriores. No fetch de broker, ni trading. Un lector neutral decodifica el formato fuente de Capitalizer sin importar métodos/entradas de V48/V49/L1/L2.

## 2. Conteo real de cobertura estricta (bins con al menos un M1 observado)

| Métrica | EURUSD | GBPUSD |
|---|---:|---:|
| M1 originales presentes | 369.903 | 369.833 |
| M15 UTC observadas | 24.848 | 24.848 |
| M15 completas (15/15 M1) | 23.717 | 23.906 |
| M15 parciales | 1.131 | 942 |
| M15 completas / observadas | **95,4483%** | **96,2090%** |
| H4 UTC observadas | 1.607 | 1.607 |
| H4 UTC completas (240/240 M1) | 1.242 | 1.256 |
| H4 UTC parciales | 365 | 351 |
| H4 completas / observadas | **77,2869%** | **78,1581%** |
| D1 UTC observadas | 312 | 312 |
| D1 UTC completas (1440/1440) | **0** | **0** |
| M1 máximos en una D1 observada | 1.438 | 1.438 |

**Interpretación estricta:** la reconstrucción por fuente M1 y el contrato `todos los minutos del bin` no certifican ni una D1 completa. No significa que las 312 fechas carezcan de vela Daily operable: el proveedor puede no publicar barras sin transacciones; hay cierres de mercado/holidays y ventanas locales con anclas distintas. Ninguna de estas alternativas está adjudicada. Por tanto no se puede ni imputar OHLC faltante ni afirmar corrupción/ausencia del mercado.

Los porcentajes de M15 y H4 están calculados SOLO sobre **bins no vacíos**; no incluyen intervalos sin ningún M1. Por eso no prueban exhaustividad del calendario, del tick feed ni de las extremas/volumen reales. H4 UTC 00/04/08... **no está identificada como la temporalidad fuente del autor**.

## 3. Relojes alternativos: hipótesis, nunca regla TTrades certificada

Se añadió al censo una comprobación de anclajes NY `22/02/06/10/14/18` y `01/05/09/13/17/21`. Son hipótesis de datos con `America/New_York`, horarios DST variables (180/240/300 minutos reales por bloque cuando corresponde). La fuente londinense habla de 22:00 y 02:00 pero **no basta para adjudicar a priori una hora universal de entrada**. La alternativa 01/05 pertenece a otro perfil de fuente en el repositorio y no se importa como autoridad de LON-A.

**Segunda auditoría real finalizada:** [GitHub Actions run #38169272744](https://github.com/mezas3238-hue/qore-core/actions/runs/38169272744), `SUCCESS` en 3 jobs (contratos sintéticos y EUR/GBP), fuente idéntica y modo read-only.

| Reloj H4 AUDITADO (no canónico) | EURUSD completas/observadas | GBPUSD completas/observadas |
|---|---:|---:|
| UTC 00/04/08/... | 1.242/1.607 = **77,29%** | 1.256/1.607 = **78,16%** |
| NY 22/02/06/... | 1.178/1.608 = **73,26%** | 1.193/1.608 = **74,19%** |
| NY 01/05/09/... | 1.010/1.555 = **64,95%** | 1.017/1.555 = **65,40%** |

Los DENOMINADORES CAMBIAN al modificar el reloj; **no son una comparación causal de precisión de velas**, y cada bin observada puede incluir horarios de trading diferentes. Ambos relojes NY se verifican con conversión `America/New_York` y tests de frontera primavera/otoño. En el periodo real no aparecen bins observadas de 180/300 minutos: las transiciones DST ocurren durante cierres de mercado de estos pares, no porque se haya omitido implementar DST.

**Conclusión:** elegir ancla horaria solo porque produce un porcentaje mayor equivale a selección por calidad aparentemente favorable y NO adjudica el H4 del autor. Se necesita confirmación del reloj en la fuente y comparación con velas H4 nativas si se dispone de ellas. La métrica de cobertura NY, incluso si difiere de UTC, **no puede seleccionar el reloj autoral por maximización de la cobertura o del PF**.

## 4. Trabajo restante obligatorio

- Resolver zona horaria, NY DST, anchor Daily/H4 y cronología first-known del autor antes de permitir motor.
- Separar faltantes dentro de negociación regular de minutos cero-transacción, weekends, gaps de recuperación y feriados; auditar una muestra contra timeframe H4 y D1 **nativo** externo (sin asumir equivalencia).
- Observar cuánto sesgo introduce censurar las 365/351 H4 parciales y 1131/942 M15 parciales, *sin mirar performance*.
- Diagnosticar si los primeros/últimos minutos están consistentemente ausentes en D1, sin inventar interpolaciones.
- Obtener holdout realmente independiente: la data aquí usada es histórico consumido, no OOS.
- Vincular fuente autoral de CISD/swing, resolución de entradas/salidas y as-of antes de autorizar ensayo económico.

**No se han ejecutado operaciones, replays económicos, P&L, ni alteraciones en VPS, MT5, CIBO, Shared o producción.** Los flags de salida siguen `fresh_holdout_eligible=false`, `data_gate_b_certified=false`, `author_fidelity_certified=false`, `economic_replay_authorized=false`, `live_authorized=false`.
