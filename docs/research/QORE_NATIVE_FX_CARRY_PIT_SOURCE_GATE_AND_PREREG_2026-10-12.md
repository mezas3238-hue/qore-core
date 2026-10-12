# QORE Native — FX carry: preregistro económico condicionado a fuente forward/financiación PIT

**12 octubre 2026. Se congela una hipótesis nueva y un STOP de datos, NO se abre un cuarto backtest.** Motivación: evidencia publicada en Lustig–Roussanov–Verdelhan (RFS 2011, DOI 10.1093/rfs/hhr068). La literatura clasifica monedas por interés/forward premium y mide **retornos excedentes**. Las velas M5 spot de QORE NO incluyen por sí mismas tasas invertibles, puntos forward ni financiación histórica.

### Dictamen verificable en GitHub antes de cálculos

- Las 33 fuentes G0 originales verificadas contienen velas M5 spot/CFD; 28 símbolos FX, **solo 8 monedas distintas** (AUD, CAD, CHF, EUR, GBP, JPY, NZD, USD), todos los 28 cruces no ordenados posibles. Máximo siete grados independientes en factores de cambio de moneda tras fijar numeraire; los 28 pares NO equivalen a 28 apuestas independientes.
- [PR #870](https://github.com/mezas3238-hue/qore-core/pull/870) auditó 12 fichas de símbolos del broker actual: en ese snapshot faltan explícitamente `swapLong`, `swapShort`, `baseAssetId`, `quoteAssetId`; incluso si existieran hoy NO probarían tasas, costos o contratos históricos 2016–2024.
- Las búsquedas de archivos verificables del repo por `forward points`, `historical interest rates`, `FX carry`, `swap long`, `OIS daily` NO revelaron **serie histórica PIT original 1M con fecha de publicación/tenor/contrato, validada para ocho monedas o 28 pares**. Esto **NO** demuestra la inexistencia universal de esos datos, solo que NO tenemos evidencia para usarlos.
- Afirmar que `F_{t,1M}` está *implícito en el precio spot* no es matemáticamente posible: spot `S_t` es una variable, forward `F_t` otra, ligada a un diferencial no observado. Inferir F desde variación futura de S es lookahead. El forward premium sí puede estimarse CON una curva histórica observable de tasas al instante t y convenciones/tenores válidos, pero entonces debe llamarse *proxy sintético de tasas* y NO quote ejecutable del broker.
- Literatura no justifica declarar que los tres tests H1/H2/H3 fallaron **por** 28 FX. Es hipótesis plausible, no identificación causal; n=5 instrumentos no-FX no es un universo de futuros diversificado.

## Próxima hipótesis única H4 — no ejecutar hasta cumplir fuente

El usuario propuso long las seis monedas-pares de mayor interés relativo y short las seis de menor, mensual, coste 1 bp por lado. Formalización:

1. **Rank** los 28 FX G0 como pares `BASE/QUOTE` canónicos (ver catálogo en `qore_native_fx_carry_pit_gate_v1.py`). En cada decisión mensual, `carry_rank(BASE/QUOTE) = ln(spot_mid/forward_1M_mid)`, donde ambos son quotes reales de mismo tiempo/tenor base/quote; o, con fuente separada, diferencia de tasa de financiación de un mismo tenor/collateral y calendario (NO mezcla de tasa política y coste broker).
2. **Long 6** con carry mayor; **short 6** con menor; peso 1/12 en cada lado, neutral solo nocional en 28 pares, no neutral en las ocho monedas. Empates por símbolo alfabético. Congelar inicio del mes en la primera apertura elegible **después** del quote as-of; cotización usada fechada antes de orden (preferiblemente fin del día anterior), recibida antes de orden y edad máxima 7 días. Quotes BID/ASK de spot y forward 1M exacto y su `maturity_date` válidos por el tenedor durante todo el mes; si tenor no casa con salida mensual, documentar roll/settlement y NO etiquetar exceso retorno forward ejecutable.
3. Costes supuestos **1bp por lado de turnover de peso**, NO se certifican swap/borrow, slippage, margen, spread forward ni cross currency conversion. Reportar cartera USD financiada solo tras demostrar convenio de valoración por moneda y coste de carry, nunca restar o sumar diferencial dos veces. Un +Sharpe no certifica trader.
4. DEV hasta 2021-12-31, DIAG de 2022-01-01 a 2024-09-16. **Holdout 2024-09-17+ sellado.** Meses sin 28 quotes completos PIT = `BLOCKED` en vez de eliminar mercados o sustituir tasa histórica por tasa actual. Series editadas/revisadas ex post sin registro de versiones = `BLOCKED_PIT`. No optimizar número de mercados / plazo / 1bp.
5. Reporte definitivo una vez tengan fuentes: Sharpe neto de coste supuesto, CAGR, DD, turnover, riesgo concentración por moneda (suma longBASE-shortQUOTE por moneda), correlación con SP500 CFD (NO SPX), cobertura PIT, carry de financiamiento separado de retorno spot, CIs robustos por bloques y contraste con H1/H2/H3 **adaptativos**. Un Sharpe >0.5 sería solo **promising exploratory**, no edge certificado.

## Insumos externos obligatorios, archivados EN almacenamiento privado licenciado

Para cada mes/pareja durante 2016–2024: observación forward 1M real del instrumento (spot y forward BID/ASK, orientación, valor unidad, día/convención settlement, fecha observada/recibida, fuente comercial, SHA, revisión/versiones), o curvas históricas de tasas que fueran realmente conocidas al momento y permitan calcular diferencial 1M bajo convenios exactos. Aparte, condiciones históricas de rollover swap/fees y conversión a USD por contrato si el objetivo es retorno broker NET. El usuario no ha concedido licencia para publicar raw de broker en GitHub. **No descargar/upload raw comerciales al repo público**.

**Estado de primera ronda: `BLOCKED_NO_AUTHENTIC_PIT_CARRY_SOURCE`**, no cero o Sharpe negativo. No se ha ejecutado H4 económico, ni se ha leído PnL ni traspasado holdout. El instrumento de control sirve para impedir exactamente el cuarto falso edge: identificar si los registros suministrados son forwards PIT válidos sin leer futuros.

Referencias: [Lustig–Roussanov–Verdelhan RFS 2011](https://doi.org/10.1093/rfs/hhr068), [CME Covered Interest Parity y Forward FX Swaps 2024](https://www.cmegroup.com/articles/whitepapers/covered-interest-parity-implied-forward-foreign-exchange-swaps-cross-currency-basis-and-cme-estr-futures.html), [Verdelhan 2018 Forward and Spot Exchange Rates in a Multi-Currency World](https://doi.org/10.1093/qje/qjy018).

**Todos los módulos nuevo trabajo research-only**. No ejecución ni mutación de CIBO, Shared, MT5, VPS, LIVE, QDLE, ni certificación 0/3.
