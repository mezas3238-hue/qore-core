# VT08 P0-A — PRERREGISTRO M30→M3 DE SWING Y POI CAUSALES

10-oct-2026 NY / 11-oct-2026 UTC. Pre-resultado; A PR #765, issues #762/#763. Investigación GitHub-only, 1095d M3 cTrader DEMO nativos run 35941643396 y M15 run 35934924907. Sin VPS / 7Y holdout / orders / PnL.

## A-fuente y ambigüedad decisiva

- https://ttrades.com/internal-external-liquidity-using-the-ttrades-fractal-model/ (22-ago-2026) define EXTERNAL swing high: high con highs inferiores a ambos lados; EXTERNAL swing low: low con lows superiores a ambos lados. Una vela derecha debe CERRAR antes de que exista el pivot.
- https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/ (10-ene-2026) requiere además HTF cierre C2/C3 y CISD inferior dentro de aquella vela para swing de reversión.
- https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/ (18-jul-2026): entre PS y rango actual, POI FVG primero, luego swing high/low, finalmente retest CISD. POI no es entrada.
- https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/ (30-jul-2025): 30M→3M + ejemplo long con stop BAJO EQ M30 y breaker low; stop SOLO PS del detector QORE no replica necesariamente fuente.
- https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/ (10-oct-2026): EQ C2 close-to-wick contra swing PREVALIDADO; haber encontrado pivot externo no demuestra automáticamente que es swing point válido para activar esta fórmula.

## Contrato experimento SIN mirar resultados

1. external_pivot(left,center,right,asof): velas H1 cerradas y contiguas, central estrictamente mayor que ambos highs = external HIGH, central estrictamente menor ambos lows = LOW; timestamp confirmado = right.closed_at <= asof. Si right pendiente → rechazar, empates → rechazar. La definición geométrica es A. Su selección para EQ C2 sigue D.
2. H1 es sensor C-QORE, no equivalencia directa de contexto HTF autor. Reconstruir 3 H1 acabadas ANTES DE C2.open exclusivamente a partir de 12 M15 cerradas; ambas fuentes M3/M15 deben coincidir para M30. Evaluar FVG tres velas ya cerrado y pivote H1 triple; marcar touched C2 solo a posteriori, NO estar adjudicado antes de touch. Tres H1 consecutivas estrictas; si incompletas dejar INCOMPLETE, no introducir barras futuras.
3. CisD/PS M3: contra extremo barrido M30 C1, origin series abierta dentro de C2 y cierre de vela M3 <=C2.closed_at, sin arrastrar PS fuera de C2. Doble sweep M30 → D, nunca escoger último CISD. Distinguir alta/baja central y direccionalidad de C2, no fingir POI autor. Registrar hit del FVG H1 y pivot relevante solo como contexto sensor, no SOURCE_COMPLETE.
4. Unidades: partir de los 8.982 setups mecánicos precedentes, mantener subtipo y separar evidencia previa H1 FVG, pivote confirmed-before-C2, touch C2, C2 PS confirmado. Publicar filas, hashes IDs estables, conteo días y motivos. NO sumar ni afirmar que hay nuevas entradas sobre 488 B01.
5. EQ intra-C2 NO habilitado por pivot geométrico H1 sin prueba swing point autor. Para ejemplo de stop con EQ M30 y breaker low, se puede probar flag geométrico: PS stop bajo ambos solo si EQ regime es conocido; si no, NOT_ATTESTED, no hacer filtro retroactivo ni afirmar seguridad.
6. Éxito científico: demostrar existencia o ausencia de POI previo y hora CISD, detectar fragilidad de lookahead; NO metrics PF/DD/Sharpe/Sortino. 7Y/VPS intactos y cero órdenes/fills.
