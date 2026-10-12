# QORE Native — pre-registro: UNA hipótesis TSMOM diaria, 33 mercados

**Fecha de congelación:** 12 octubre 2026. **Orden:** leer este documento antes de ejecutar el workflow. Este ensayo reemplaza la prioridad de reconstruir los 373.611 supuestos fills M5, no altera E1 ni production. Ningún cálculo del resultado diario nuevo se consultó al elegir esta especificación.

## Pregunta única

¿Una señal transversalmente homogénea de momentum direccional de los últimos **20 días de negociación completados**, sin optimización, ofrece retorno después de **1 bp supuesto por lado** positivo en el panel fijo de 33 mercados y Sharpe anualizado superior a 0,5 en la muestra histórica diagnóstica?

**Universo ex ante**: 33 activos de G0, tres índices, dos metales, siete FX mayores y veintiún cruces. Doce archivos originales Atlas CIBO DEMO, 21 originales nuevos IC Markets DEMO. **No está probada equivalencia histórica de contratos entre cohortes**, por lo que el panel es de series normalizadas y NO un portafolio broker ejecutable.

**No declarar edge robusto solo por Sharpe >0,5.** Un Sharpe diagnóstico por encima del umbral constituye evidencia exploratoria para iniciar una auditoría independiente con costes/holdout; no certificación. Comparar TSMOM con cash 0 y SP500 CFD como proxy direccional; correlación con S&P 500 cash SPX **no disponible**.

## Fechas y preservación del holdout

- DEV: `2016-09-17 ≤ fecha < 2022-01-01`.
- DIAG (ya expuesta): `2022-01-01 ≤ fecha < 2024-09-17`.
- **HOLDOUT reservado** desde `2024-09-17` hasta fin fuente 2026-09-17: se pueden verificar bytes fuente por SHA sin utilizar precios/retornos/selección ni resultados. **No** afirmar validación 2022–2026; esta requeriría autorización expresa para romper un embargo fijado por investigadores previos.
- Toda línea de fuente de 2025–2026 se comprueba criptográficamente sin parsear OHLC. En 2024 el código comprueba timestamp y no calcula retornos con velas desde 2024-09-17.

## Transformación M5 → jornada UTC, predeterminada

1. Verificar SHA256 del manifiesto y de todas las 11 particiones anuales RAW por símbolo original desde run Atlas #35166210458 (12) o IC Markets #38193802541 (21), proveedor, schema y cronología de M5. **No descargar fuente nueva del broker.**
2. Para cada fecha UTC lunes–viernes con ≥12 barras M5: guardar **solo en memoria** último precio de cierre M5 del día y primera apertura M5 de la fecha que sea a las 00:10 UTC o después; si no existe, excluir el día. Definir cierre disponible = última apertura M5 + 5 minutos. Este calendario UTC NO implica ser la vela D1 del corredor.
3. En apertura admisible del día operativo t, señal = `sign(close[t−1]/close[t−21] − 1)` sobre últimas 20 jornadas válidas, ambas observadas al cierre previo. No usar barras del día t para decidir signo.
4. Entrada simulada: primer `OPEN` M5 de día t a partir de 00:10 UTC; además, tras cierre completo de la barra M5 anterior +5 minutos adicionales de latencia de seguridad. El simulador atribuye ejecución a ese OPEN: **proxy de OHLC**, no fill broker real ni BID/ASK.
5. Salida/reevaluación: siguiente `OPEN` M5 elegible del siguiente día válido t+1, siempre en la misma partición DEV/DIAG. Si gap de fechas entre sesiones supera siete días, no se evalúa ese segmento. No stops, take profit ni filtros añadidos; exposición long/short de magnitud 1 por símbolo.
6. Costes: `0,0001 × abs(nueva_posición − posición_anterior)` por cambio en el símbolo: 1 bp para abrir/cerrar, 2 bps para invertir −1 a +1. Liquidar cada mercado al final de cada subperiodo: coste 1 bp. No comisión, financiación, swaps ni deslizamiento extra. **1 bp por lado es hipótesis favorable y NO tarifa del proveedor.**
7. Peso de cada mercado **1/33** del capital ex-ante; fechas sin observación = capital de ese mercado en efectivo con rendimiento cero. Marcar PnL por fecha UTC de salida; semana calendario lunes-viernes, 252 días para Sharpe y anualización. No hacer selección posterior ni inversión de signos por activo.

## Métricas esperadas, sin metas manipulables

Un reporte conjunto DEV y DIAG con: Sharpe anualizado (Rf=0, volatilidad diaria por desviación estándar muestral, factor √252), retorno geométrico anualizado por 252 fechas laborables, drawdown máximo sobre NAV a partir de 1, número de jornadas activas, 33 fuentes auditadas, número de cambios de lado, y correlación lineal diaria con el **SP500 CFD** del mismo archivo fuente, sin confundirlo con SPX. Resultados individuales 33/33 únicamente como diagnóstico y no para elegir ganadores.

**Interpretación pactada antes de mirar:** 
- DIAG Sharpe ≤0: no hay evidencia positiva bajo este proxy. Abandonar esta especificación de TSMOM-20, sin ajustarla mirando DIAG.
- 0 < DIAG Sharpe ≤0,5: indicio débil/no suficiente. No certificar ni continuar la optimización oportunista.
- DIAG Sharpe >0,5: hipótesis prometedora **sujeta a confianza por bloques, costes reales, robustez y holdout verdaderamente reservado**, no edge demostrado y menos trader certificado.
- Cualquier error de datos/manifiesto, leaks o falta de cobertura de un mercado -> **FAIL**, no eliminar malos mercados ni imputar retornos.
- En todos los casos retener benchmark de la señal original 20 días, no tunear hacia otro lookback.

**No ejecución / NO G1 certificado:** Un backtest favorable sobre OHLC D1 construido de M5 con comisión ficticia no demuestra slips, swaps, tradabilidad ni legalidad de custodia. No tocar CIBO, Shared, VT, MT5, VPS, QDLE, LIVE, ni modificar PR #871 o Gate E1. Cualquier nuevo método QORE Native requiere nueva prueba genuinamente independiente.
