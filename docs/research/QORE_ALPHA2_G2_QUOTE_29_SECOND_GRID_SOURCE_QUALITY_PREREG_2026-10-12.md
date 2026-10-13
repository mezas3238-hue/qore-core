# QORE-Alpha 2 — G2 source quote-quality second grid prereg, NO NET

2026-10-12, predefinido antes de medir la relación BID/ASK de las dos series para Alpha2. Única fuente run #38283737706 29 activos, HEAD f8262bd7cdea1fbfb2287c3c1fe0dae3be2b0efc; QA independiente Alpha2 [#38288561813](https://github.com/mezas3238-hue/qore-core/actions/runs/38288561813) verificó 37.430 BID + 37.342 ASK en 2020 y 2023, sin abrir precios 2026. Fuente de integridad alpha2_g2_29_real_bidask_reuse.py. Se deja íntegro W1/W2/W3 congelado.

Pregunta de calidad única: de 29 × 2 ventanas de 10min, en instantes fijos UNA VEZ POR SEGUNDO, ¿cuántas observaciones tienen BID y ASK cuyo último tick de cada lado ocurrió como máximo 5.000 ms antes del instante solicitado? Reunir sólo los últimos eventos con event_time_ms <= sample_clock_ms. Sin interpolar, sin atribuir available_at del mercado real ni simular fills. Si falta uno, clasificar MISSING_OR_STALE; si ambos disponibles, clasificar ASK < BID crossed, ASK == BID zero o ASK > BID positive. Nunca tratar spread cruzado o cero como ejecución gratis.

- Muestra exacta t=start_ms+k*1000 para k=0..599 en ventanas 2020-09-15 13:00–13:10 UTC y 2023-09-19 13:00–13:10 UTC. Incluir segundos sin ticks para evitar ocultar mala calidad. Edad del último tick <= 5000ms inclusivo. Eventos con mismo milisegundo conservan su secuencia nativa.
- Para spread positivo computar solo indicador descriptivo 10000*(ask-bid)/((ask+bid)/2) en bps; mediana y percentil95 por mercado/ventana. Sin afirmar precio ejecutable, BUY/SELL, comisión ni R. Conteos cero, cruzado, stale/missing, positivo deben sumar 600 por ventana.
- Exigir antes de leer las series la auditoría SHA completa de Alpha2 G2 índice 29; fuente mala => SOURCE_QUALITY_BLOCKED sin sustitución. Nunca abrir ventana 2026 ni activos heredados NZDUSD/XAGUSD/SP500/NAS100. No mezclar cuenta Atlas 12 con IC Markets DEMO actual.
- Precaución causal: timestamps de ticks históricos NO equivalen a disponibilidad causal en el terminal; este ensayo sólo usa as-of declarado por evento, NO verifica latencia ni fill, NET, macro PIT ni Sharpe/PF/DD.
- Reportar los 29 activos completos y cero selecciones por desempeño. W1/W2/W3 no poseen ventaja neta acreditada. UTC001 bloqueado hasta full source quote history en entradas y salidas, contrato/comisiones/slippage y OOS independiente.

Artefactos GitHub source-only, sin órdenes; VPS/MT5/Shared/CIBO/QDLE y Live intactos.
