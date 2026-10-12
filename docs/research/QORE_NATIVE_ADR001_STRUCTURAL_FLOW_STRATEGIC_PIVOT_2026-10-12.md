# ADR-QN-001 — Decisión estratégica: detener micro-patrones de precios; investigar flujo exógeno forzado

**Fecha:** 2026-10-12 (UTC)  
**Estado:** DECIDED / RESEARCH FEASIBILITY ONLY / NO NEW PNL PERMITTED  
**Ámbito:** QORE Native, repositorio `mezas3238-hue/qore-core`. Esta ADR es una decisión de arquitectura, **no** una afirmación de rentabilidad o una nueva hipótesis probada.

## Decisión tomada

**Elegimos OPCIÓN 1: cambiar de clase de hipótesis a eventos discretos de flujo exógeno/forzado.**  
**Adoptamos la OPCIÓN 3 de manera acotada:** suspender la **familia operativa ensayada** de patrones pequeños de precio intradía con extrapolación direccional a minutos/horas sobre CFD OHLC. No afirmar haber demostrado la imposibilidad universal de todas las estrategias de reversión, momentum o barrido.
**OPCIÓN 2 — futuros:** mantener como **estudio de viabilidad de instrumento y fricción**, condicionado a encontrar primero mecanismo económico y a medir datos propios de bid/ask, comisión, slippage, profundidad y roll; jamás trasladar un backtest CFD a futuros ni asumir coste 0.5–1 bp/lado como probado.

**CONGELAR los 33 mercados G0 (24.377.420 M5)** y NO ampliar el universo de CFDs ni backtestear otro patrón simple dentro de Native hasta nueva ADR explícita, con revisión independiente y justificación de *clase* diferente. No liberar embargo 2024-09-17→2026-09-17. Fuente G0 no autoriza G1 neto. No reiniciar la captura ya cerrada y no modificar producción, VPS, MT5, CIBO, Shared, QDLE ni LIVE.

## Evidencia concreta, límites y lenguaje permitido

Los cuatro ensayos QORE Native bajo disciplina preregistro y control fueron todos **NO_SUPPORT**:

| ID | Prereg / test | Núcleo de hipótesis | Resultado que cierra |
|---|---|---|---|
| H4-GROSS-01 | [PR #822](https://github.com/mezas3238-hue/qore-core/pull/822) | EURUSD, continuación desplazamiento H4 12h vs 4h | Delta dev +0.743 bp CI95 [-0.142,+1.645]; diag -0.258 CI95 [-1.716,+1.221] |
| H4-GROSS-02 | [PR #825](https://github.com/mezas3238-hue/qore-core/pull/825) | XAUUSD, reversión desplazamiento 12h vs 4h | Delta dev -0.436 bp y diag -0.112 bp, CI97.5 ambos cruzan 0 |
| OPEN-DRIVE-03 | [PR #827](https://github.com/mezas3238-hue/qore-core/pull/827) | NAS100, 09:30–10 NY drive vs premarket | Gross dev +2.457 bp / diag +2.852 bp; **delta vs control** dev +0.422 CI98.333 [-4.666,+5.659]; diag +2.646 CI98.333 [-6.699,+12.518] |
| GROSS-PANEL-04 | [PR #830](https://github.com/mezas3238-hue/qore-core/pull/830) | 33 símbolos sweep/reclaim vs baseline contrarian | Dev 13,989 eventos delta -0.033 CI98.75 [-1.296,+1.219], diag 4,680 delta +0.146 CI98.75 [-2.102,+2.683], costes RT hipotéticos 1bp dejan gross negativa |

**Nota de procedencia:** RESET y DRIVE pertenecen a la genealogía económica indicada por auditor/owner; sin recuperar aquí sus PRs, preregistros y testigos exactos **no los contaremos como dos falsaciones QORE Native prospectivamente independientes**. Familias conceptuales relacionadas ≠ pruebas estadísticas independientes. Son cuatro ensayos Native preregistrados confirmados por Actions; seis o más propuestas históricas relacionadas pueden acumular preocupación metodológica, no reemplazan el registro por commit.

**Importante: la objeción de correlación NO fue omitida completamente.** En GROSS04 el código `sample_panel_weeks` (`src/qore/infrastructure/trader_lab/qore_native_gross04_panel33_sweep_reclaim_v1.py`) re-muestreó **semanas UTC sincronizadas para TODOS los mercados a la vez**, preservando los shocks contemporáneos de EUR/GBP/JPY e índices en cada semana; el estimando da **igual peso a cada símbolo** y el CI fue calculado en unidades de semanas, **313 dev y 105 diag**, no suponiendo 18,669 fechas de trade independientes. [Reporte ejecutado](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-33-panel-liquidity-sweep-gross04-20261012/docs/research/QORE_NATIVE_GROSS04_ALL33_EXECUTED_NO_SUPPORT_2026-10-12.md).

**LIMITACIONES reales del IC:** dependencia a través de *varias* semanas, heterogeneidad/factores latentes, signo y ponderaciones de co-movimientos, 2,000 resamples e intervalos extremos, y la equivalencia económica entre diferentes cuentas broker requieren pruebas adversariales. **La afirmación numérica «33 equivalen a 5–8 factores; n efectivo 3–5k; CI ±3–4bp» es una HIPÓTESIS NO ESTIMADA**, no resultado de ese CI; no corregir intervalos multiplicando arbitrariamente la SE. Si se audita posteriormente la inferencia, hacerlo **solo con eventos y outcomes ya publicados de GROSS04**, manteniendo criterio NO_SUPPORT, con sensibilidad de bloques multisemana / HAC, exposición a factores y diseño de clusters pre-especificados, sin excusa para abrir nuevos precios ni rescatar una estrategia.

**NAS100 2–3bp:** ese número describe MEDIA BRUTA de una señal OHLC de CFD, **no** ventaja media pareada validada, y en su test el IC gross también cruzó cero (dev [-0.939,+5.637]; diag [-3.140,+8.779]bps, CI98.333). Caso de interés/posible discusión para futures, pero **H3 permanece NO_SUPPORT y no se reabre**. El CFD USTEC no representa un contrato MNQ, tiene distinto libro, roll, tick y sesión. Ningún coste real MNQ específico ha sido auditado para la cuenta del dueño. CME confirma MNQ = **USD 2 × índice Nasdaq-100**, tick de **0.25 índice = USD 0.50**; las comisiones y la fricción por órdenes no se desprenden de ese multiplicador. Fuente oficial: https://www.cmegroup.com/markets/equities/nasdaq/micro-e-mini-nasdaq-100.contractSpecs.html .

**Afirmación autorizada:** “QORE Native ha cerrado sin soporte económico robusto cuatro implementaciones de la clase precio intradía → pequeño movimiento a continuación; no hay rentabilidad NET certificada”.
**Afirmación NO autorizada:** “todas las estrategias de precio están matemáticamente falsadas”, “33 mercados son 33 observaciones independientes”, “el efecto NAS100 es 2.8bp netos replicados”, “MNQ garantiza un spread de 0.5bp por lado”, “suficiente infraestructura equivale a un trader”.

## Primera línea de negocio científico distinta: reconstituciones Nasdaq-100

**Pregunta de viabilidad estructural — no hipótesis ya aceptada:** ¿el rebalanceo de fondos pasivos y carteras ligadas al **Nasdaq-100** en altas/bajas **anunciadas antes de su fecha efectiva** genera una presión de subasta o inventario que pueda identificarse causalmente frente a empresas control?

**Razón exógena:** el cambio de composición/ponderación del índice obliga a los vehículos que lo replican a ajustar posiciones; la fecha de anuncios y la fecha de efectividad son entidades observables **externas al patrón de precios**. Por ejemplo, Nasdaq anunció el 12/12/2025 un cambio de integrantes efectivo antes de la apertura del 22/12/2025: https://ir.nasdaq.com/news-releases/news-release-details/annual-changes-nasdaq-100-indexr-2 . Cambios anuales anteriores verificables: 09/12/2022 https://ir.nasdaq.com/news-releases/news-release-details/annual-changes-nasdaq-100-index-10 y 11/12/2020 https://ir.nasdaq.com/news-releases/news-release-details/annual-changes-nasdaq-100-index-9 . **Estos enlaces prueban que existen eventos publicados, NO que la presión predice un beneficio**. Metodología index Nasdaq fue actualizada en 2026: **no aplicar retrospectivamente reglas actuales** a años previos; registrar metodología y timestamp as-of de cada anuncio. https://www.nasdaq.com/newsroom/nasdaq100-index-methodology-update-why-now .

**Advertencia operacional:** los 33 CFD M5 **NO contienen** acciones constituyentes, precios de subasta, flujo de ETF o libros de futuros. Sirven como **factores/controles de mercado**, no como tratamientos del evento. No añadir en masa otros CFDs para simular acciones. Esta línea empieza con una **puerta de factibilidad de DATOS PIT** y NO con un backtest ni con autorización para descargar décadas de precios.

### Gate E0 — FEASIBILITY, sin consultar retornos ni traders

Recolectar un **ledger de anuncios y cambios** a nivel de empresa y fecha, con prueba del enlace oficial original, `published_at_utc`, `effective_at_utc`, ticker/ID estable (cambios corporativos), signo add/delete, contexto de metodología vigente y `known_at` para el algoritmo; nunca rellenar anuncio con reconstrucción ex post. Mínimo requerir una tabla de anuncios fechados y cambios por año en la ventana 2016–2023; si ausente/mala procedencia: **SOURCE_BLOCKED**, no se estiman retornos.

Pedir/revisar antes de licenciar: **precios acciones/volumen/closing auction y quotes históricos por constituyente**, corporate actions point-in-time, costes efectivos por mercado y datos de ejecución del instrumento propuesto. Distinguir open/close de subasta de fills reales. La fecha efectiva es generalmente preopen del lunes siguiente al tercer viernes de diciembre (según anuncio particular): **no inventar fecha de ejecución; validar la de cada aviso histórico**. Separar período entre anuncio→efectividad y fecha/cierre reconstitución. Eventos anuales ofrecen **pocos años independientes** (~8 años en el intervalo hoy previsto), incluso si hay decenas de nombres; no tratar 50 constituyentes como 50 eventos macro autónomos.

**Salida GATE E0 obligatoria:** informe con cobertura conocida-as-of por año, número de años de anuncio independientes, número de adds/deletes y control candidates, costes documentados, factibilidad de licencias y riesgos de supervivencia/ticker delistado; conclusiones `DATA_READY_FOR_PREREG`, `SOURCE_BLOCKED` o `STRUCTURAL_MECHANISM_NOT_TESTABLE`. **SIN trade PnL, sin calibración, sin abrir embargo 2024-2026.**

### Gate E1 — solo SI E0 pasa y ante un NUEVO prereg previo al outcome

Hipótesis de signo y horizonte explícitos, con presión de flujos y reversión posterior distinguibles, y **grupo control ex ante** de empresas no afectadas similar por sector, liquidez, tamaño/volatilidad, sin seleccionar por retorno posterior. Clusters principales = fecha de rebalanceo/año de anuncio, no empresa independiente; sensibilidad a presión compartida por sector y benchmark, bootstrap multiaño por eventos, prueba placebo en fechas no reconstitución, control de splittings/survivorship, imposibilidad de arbitraje en subasta y costes confirmados. Cálculo de potencia respecto de CLUSTERS AÑOS, NO 33 símbolos / 24M barras. Si es insuficiente: **NO TEST** con conclusiones de falta de potencia.

**Acciones permitidas ahora:** E0 metadata/PIT, evaluación independiente de acceso/contratos de datos y ADR detallada; NO backtest de anuncios sin E1, NO escaneo de variantes, no análisis de PnL ex ante, NO operar durante macro impact news. E1 requiere aprobación separada del owner/revisor para acceder a returns/outcomes.

## Gate F0 — futuros como estudio de ejecución contingente, no rescate de H3

Si interesa MNQ/NQ: obtener cotizaciones BID/ASK timestamped reales, comisiones y tasas por broker/cuenta, 0.25pts tick, slippage, latencia y rollover, horarios y subastas; estimar RT en dólares, ticks y bps respecto del nocional **en función del nivel de índice y el tamaño**, con intervalos de distribución, no un valor constante garantizado de 0.5–1bp/lado. Nunca mezclar PnL del CFD NAS100 con ejecución futures; exigir estudio independiente en datos de futuro y prereg de transferencia. **H3 no se reclasifica de NO_SUPPORT**.

## Reglas de paro, ownership y responsabilidad

1. **STOP PRICE-PATTERN:** ningún GROSS05 ni quinto patrón de precio/minutos-horas ni barrido 33 mercados dentro de QORE Native sin nueva ADR de clase y aprobación explícita. No usar `2024-09-17→2026-09-17` reservado para variantes de H1–H4.
2. **STOP UNSUPPORTED ECONOMICS:** si no hay transacciones/quotes reales, `NET_CERTIFIED=false`; los precios OHLC y costes hipotéticos no soportan declararlo. Necesario calendario noticias known-as-of y política #814 antes de cualquier futura orden.
3. **STOP INDEPENDENCE FICTION:** auditor puede revisar regresores latentes y block bootstrap original, pero **sin reclamar n_eff numérico inventado** ni convertir un resultado negativo en positivo tras modificar error estándar.
4. **STOP DATA HUNT:** 33 originales congelados y SHA; nuevos datos SOLO los estrictamente necesarios para probar E0 en event/constituent/quote y con procedencia, licencia y presupuesto trazables. No añadir futuros/acciones de forma masiva “por si acaso”.
5. **STOP FALSE CERTIFICATION:** 0/3 Native traders certificados, CIBO/Shared/MT5/VPS/LIVE intactos. Arquitecto puede consultar a DeepSeek Expert como auditor externo de diseño, no como prueba de causalidad.

## Decisión con puntos de control

- **Ahora:** Clase de precio intradía = `CLOSED_NO_SUPPORT_FOR_TESTED_IMPLEMENTATIONS`; fuentes M5 33/33 = `G0_SOURCE_PASS`.
- **Siguiente entregable:** `STRUCTURAL_EVENT_PIT_FEASIBILITY_V1`, catálogo de eventos verificables Nasdaq-100 y control de fuente, **sin PnL**.
- **GO a E1:** SOLO si E0 acredita origen/fecha de anuncio/conjunto controles/precios/ejecución/potencia, con nuevo prereg y acuerdo de datos. De lo contrario, registrar `SOURCE_BLOCKED` y detenerse.
- **GO LIVE:** imposible ahora; requiere resultados net, costs measured y política noticias, stops, drawdown/robustez y certificaciones separadas. Ninguna de las ramas research actuales integra producción.
