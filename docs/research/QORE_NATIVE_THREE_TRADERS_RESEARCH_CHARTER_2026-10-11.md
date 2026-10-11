# QORE Native: programa científico para tres traders propietarios

**Fecha:** 2026-10-11. **Issue rector:** https://github.com/mezas3238-hue/qore-core/issues/789
**Estado:** RESEARCH_DESIGN_ONLY. Sin estrategias implementadas, señales comprobadas, ganancias demostradas ni autorización de VPS/MT5/live.

## Objetivo

Descubrir hasta TRES metodologías originales de QORE derivadas de observaciones y pruebas empíricas, con fuentes de retorno distintas, ejecución programática causal y robustez fuera de muestra. Si ninguna sobrevive, la respuesta válida es CERO traders certificados. La originalidad se refiere a nuestras reglas empíricas, no a alegar que descubrimos la primera forma de momentum o reversión del mundo.

**No copiar** CISD/MSS, TTrades, ICT, ni sus variantes QORE anteriores. No reutilizar oportunidades V49, 458 rutas de Londres ni filtros RECLAIM/ACCEPTED como oráculos. Lógica independiente por trader; se permite reutilizar lectores de datos neutrales auditados. GitHub/Trader Lab exclusivamente; producción intacta.

## Tres programas candidatos

### N1 — QORE DRIVE / descubrimiento de precio y continuación

**Mecanismo que investigaremos:** si un impulso conocido en el instante de decisión expresa información/flujo que induce persistencia direccional superior a la del retorno horario normal, después de costes.

**Universo candidato:** NAS100, XAUUSD, EURUSD, GBPUSD (sujeto a disponibilidad homogénea y procedencia del proveedor). Features as-of: rendimiento inicial de ventana, cambios en volatilidad realizada respecto de lookback previo, persistencia del cierre, patrón de aceleración y régimen conocido de sesión. Nunca inferir intención institucional del OHLC.

**Experimento 1 descriptivo:** agrupar días/ventanas por condiciones calculadas sin futuro; medir retornos posteriores condicionados contra retornos de las mismas horas y volatilidades sin filtro, retorno placebo y dirección contraria. Congelar horizonte de observación y clase de features antes de analizar desenlaces.

**Contratos de falsación:** si el efecto no supera benchmark horario y costes, si desaparece retrasando entrada una vela, si depende de un único evento/noticia/mes, si la expansión es base rate, o si el resultado solo existe a spread irreal, STOP.

**Literatura como prior, no como evidencia QORE:** Time series momentum, JFE 2012 https://doi.org/10.1016/j.jfineco.2011.11.003; Market intraday momentum, JFE 2018 https://doi.org/10.1016/j.jfineco.2018.05.009. Sus universos/horizontes NO demuestran beneficios en nuestros instrumentos.

### N2 — QORE RESET / reversión de flujos temporales

**Mecanismo que investigaremos:** ciertos movimientos previos a eventos horarios de gestión y fixing de divisas son transitorios y revierten cuando disminuye presión de flujo. No catalogar «barrido de liquidez» como señal per se.

**Mercados candidatos:** EURUSD, GBPUSD, USDJPY. Calendario fuente oficial, reloj Europe/London/NY y DST, ventanas de estudio fijas; separarlas de la hora de ejecución real y medir spread/volatilidad.

**Experimento descriptivo:** medir retorno anterior y posterior al horario de fixing, con control idéntico de franja, volatilidad, dirección y noticia. Distintas condiciones de desequilibrio se investigarán solo en desarrollo. Entrada futura no puede anticipar el precio extremo que se sabrá luego.

**Falsación:** si no supera benchmark horario, si reversión se concentra en velas de spread/censura, si noticias convierten reversión en continuación, si costo/slippage supera desplazamiento esperado, STOP.

**Literatura como prior:** Bank of Canada, Foreign Exchange Fixings and Returns Around the Clock (2021) https://www.bankofcanada.ca/2021/10/staff-working-paper-2021-48/ . No es prueba de edge en el feed de Core.

### N3 — QORE RELATIVE / desviación relativa de mercados correlacionados

**Mecanismo que investigaremos:** una parte de las diferencias entre activos que comparten factor común puede ser temporal y retornar a una relación de equilibrio. Correlación no garantiza cointegración, estacionariedad ni convergencia explotable.

**Pares candidatos:** EURUSD/GBPUSD (factor USD), AUDUSD/GBPUSD y AUDJPY/GBPJPY (factor JPY). Cada combinación constituye un test registrado; ninguna se aprueba por correlación histórica alta. No confundir esta estrategia con SMT TTrades ni con «un par rompió Asia y otro no».

**Experimento descriptivo:** estimar solo con datos ANTERIORES al instante una beta de cobertura y spread residual; verificar estabilidad de hedge ratio, independencia de factor global, reversión del residual y pérdidas en rupturas persistentes. Timestamps sincronizados, exposiciones FX netas y rollover correctos.

**Falsación:** spread residual no estacionario/relación inestable, dos piernas comen el beneficio esperado, beta y correlación cambian drásticamente, un único par seleccionado tras muchos intentos explica todo, o no supera un control cubierto sin señal. Si no se puede neutralizar riesgo subyacente, STOP.

**Literatura como prior, principalmente ACCIONES, transferibilidad FX NO probada:** Gatev/Goetzmann/Rouwenhorst 2006, https://doi.org/10.1093/rfs/hhj020.

## Normas del laboratorio nativo

1. **Registro de experimentos:** toda hipótesis, intento, umbral, estudio negativo, versión de código, fuente, SHA y coste. Presupuesto de variantes finito y fechado. No seleccionar el ganador de cientos de reglas silenciosas.
2. **G0 Datos:** manifiesto M1/M5/M15/H1/H4 por símbolo/fuente/ventana, UTC/DST, OHLC timestamp, campos de precio, contigüidad/duplicados, rollover, gaps, disponibilidad de volumen, metadatos broker y costes estimados. El periodo 2025-09-17 a 2026-09-17 ya fue inspeccionado por QORE; NUNCA llamarlo OOS virgen.
3. **G1 Existencia del fenómeno:** estudio de distribución causal con baseline de misma sesión/horario/exposición/volatilidad; no partir de parámetros de stop y TP, ni de estados finales del precio. Si no existe señal condicional, cerrar el candidato antes de diseñar su «cognitiva».
4. **G2 Motor FIRST-ONLINE:** tres namespaces independientes, decisiones y barreras calculadas con available_at no posterior al instante de decisión; tests de prefix-invariance, calendarios, huecos, duplicados, barras HTF no cerradas y simultaneous stop+TP en misma OHLC.
5. **G3 Economics neta:** medir esperanza en R por trade, Profit Factor NETO, pérdidas brutas, drawdown en R; Sharpe/Sortino en serie de rentabilidad DIARIA de cartera real y comisiones/spread/slippage por activo/hora. Someter a escenarios 1x / 1.5x / 2x costes sin retocar umbral; comparar contra baseline de igual riesgo/tenencia/franja y estimar incertidumbre por fecha.
6. **G4 Robustez:** walk-forward cronológico con embargo para horizontes solapados; holdout futuro o proveedor realmente no utilizado. Registrar todas variantes y múltiples tests; Deflated Sharpe y controles de selección (Bailey/López de Prado 2014 https://doi.org/10.3905/jpm.2014.40.5.094). Medir IC de expectativa NETA; analizar crisis, tendencias/rangos, horarios, weekdays, missingness y shifts de volatilidad. La ausencia de independencia invalida claims confirmatorios.
7. **G5 Portfolio/capacidad:** evaluar correlación de retornos Y de pérdidas en la cola, shocks USD/JPY/NAS100/gold, notional, DD conjunto, colisión de entradas y dependencia de regímenes. Tres estrategias con mismo riesgo real no diversifican. Medir capacidad y coste creciente con volumen antes de hablar de capital enorme.
8. **G6 PAPER y Core:** tras superar gates científicos, habilitar PAPER con telemetría y presupuesto de riesgo previamente definido. Shared supervisa integridad/riesgo, CIBO asigna capital/posición y QDLE ejecuta; estos componentes no sustituyen edge propio ni autorizan VPS/live automáticamente.

### Borrador de barreras cuantitativas (no confundir con política oficial de certificación Core)

- PF neto por encima de un valor precongelado orientativo **1.30** y esperanza neta positiva con evidencia estadística; el **intervalo del 95% de mejora frente al baseline** es más informativo que PF aislado.
- Sharpe, Sortino, max drawdown, frecuencia, capital y precisión de cada estimador CON UNIDADES, periodo y riesgo normalizado: no inventar umbrales para escenarios no medidos. Definir objetivo DD y stress por trader/cartera antes de revisar P&L.
- Resiliencia ante 1.5× y 2× costes y pérdida de cobertura de fechas; al menos varias condiciones de mercado y fuente/cobertura verificables.
- Tamaño N de trades/folds requerido se fija mediante potencia/MDE y autocorrelación: **no** prometer que 200 trades alcanzan siempre ni rechazar sistemáticamente estrategias lentas por una cifra universal.
- Si tres sistemas superan P&L individual pero pierden simultáneamente, NO pasar G5; el portafolio debe aportar mejora marginal verificable.

### Roles

**ChatGPT (investigación/implementación):** hipótesis, preregistros, Data Vault, código, tests, resultados auditables y falsaciones propias en GitHub.

**DeepSeek Expert (auditor externo):** cuestionar mecanismos, detectar sesgos/lookahead, revisar hipótesis y ensayos. Respuestas externas NO sustituyen mercados/datos; los cambios después de resultados requieren nuevo preregistro y NO reutilizar holdout como si siguiera virgen.

**Criterio final:** hasta tres estrategias ORIGINALES, no tres copias ni tres ganancias prometidas. Mejor certificar UNA que introducir tres sin robustez. Nada de VPS/MT5 live mientras estemos en G0–G5.

## Primer entregable exigido, sin inventar resultados

- Tres fichas causales independientes, baselines y controles.
- Mapa real de datos disponibles, incluyendo periodo M1 ya consumido.
- Estudio G1 descriptivo de cada fenómeno con tests de fuente y remuestreo; tres conclusiones GO/STOP/INCONCLUSIVE.
- Solo después motores first-online para los candidatos que sobreviven, preregistro estadístico, walk-forward y holdout virgen.
- Actualizar Issue #789 con archivos/runs/hashes; esta carta es **plan de investigación**, no replay o certificación.
