# QORE Futures A — PREREGISTRO exploratorio nuevo: CFTC Managed Money

**Registrado ANTES de ejecutar cualquier resultado de correlación CFTC→EIA en esta línea.** Esta hipótesis es distinta de backwardation F1/F2 H1_WTI/H1_NG, ya cerradas NO_SUPPORT. **No se rehabilitan las hipótesis antiguas.**

**Tipo:** una asociación exploratoria, sin PnL, sin contrato negociable, sin Bid/Ask; NO edge certificable. Se permiten pruebas DEV 2012–2018 y DIAG 2019–2021 una sola vez. **Reserva EIA 2022-01 a 2024-04, y FX Native holdout desde 2024-09-17 NO se leen para resultados.**

## Fuente y universo congelados

- Predictor: [CFTC Disaggregated Futures Only histórico oficial](https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm), solamente `067651` NYMEX CL y `023651` NYMEX NG, de 2012–2021. El censo técnico de seis raíces ya fue ejecutado sin ver valores de posiciones ni retornos.
- Campos de fuente CFTC: `As_of_Date_In_Form_YYMMDD`, `CFTC_Contract_Market_Code`, `M_Money_Positions_Long_All`, `M_Money_Positions_Short_All`, `Open_Interest_All`. Una observación **agregada semanal por raíz**, no por expiración ni fill.
- Respuesta: EIA F1 (referencial), series WTI `RCLC1d.xls` y NG `RNGC1d.xls`, SHA256 respectivamente `a55a70d2438ebdc600a77f9d3f9c46be1e2f480ac5ffec3bb753c61cf21db0c9` y `1e71a774943c00cdba337c8be1c9888ea1d56b175c446527cc0d94f7dc2b03f1`. El parser ya sellado por fuente antigua excluye puntos >= 2022-01-01.
- Los ZIP CFTC deben coincidir con sus SHA256 exactos reportados por fuente auditada para años 2012–2021: 2012 `79db37521556a5aa8acc84bd3ca86aa6bf80fb4c5d4a8013dfb215fc760f1e95`; 2013 `c9bc647013b9b2f1c18e96fdaed95dc94af57c3a949e9fe7dd94aee06f3837bc`; 2014 `a29872d680f595078062130274374ecb38dc2a24d86f1531a59f52b8abca7eea`; 2015 `36aacb4389831a89996ba5366c91eedeaa32a55abca8265325bc52d74b06ca34`; 2016 `50f52674fd924d24c794b921c29342be7d35cbe0a241ac823925ccf43ca1a6d2`; 2017 `6fc467b989df527a4fbea4ba07185e8951f35cb72563f156488904a37c100e43`; 2018 `df4bf7d72e8984d6ea04087f793c9f2bf3503ea8c2149f4b01eedeef4fbe40a8`; 2019 `942a438bcc6f66e65aaf594a1a1fdb8c1505fe4a0feece77a1fd97270317e753`; 2020 `0aa03c0fd6360f56b6897b6eaff30e8dba774c826bf93cac61598312e19bd1cd`; 2021 `12d5d49a8963367fd3439050e3e20e6a5338757dfa083432795c5556827ff8ae`.

## Hipótesis congelada H-COT-1

**Mecanismo posible:** la acumulación persistente de exposición neta Managed Money refleja presión direccional/continuación en commodities líquidos y eleva la probabilidad de avance del precio referencial F1 durante los cinco siguientes días de observación.

- Posición semanal normalizada `P(t) = [MM_Long(t) - MM_Short(t)] / Open_Interest_All(t)`.
- Señal `X(t) = 1[P(t) - P(t-4 reportes) > 0]` versus `X(t)=0` si diferencia menor que cero; igualdad se excluye.
- Muestreo **un reporte por mes y raíz**: el primer informe CFTC cronológicamente dentro del mes cuya observación `P(t-4)` exista. Nunca elegir el mayor cambio ni la semana posterior a conocer el resultado.
- Disponibilidad aproximada conservadora: **entrada referencial** = primer día EIA en o después de **t+21 días calendario**, por el retraso típico CFTC desde martes a viernes, pero **no es certificación point-in-time**.
- Exclusiones fijas *antes de mirar outcomes*: report dates de **2013-09-01 a 2013-11-30** y **2018-12-01 a 2019-04-30**, ante retrasos extraordinarios de publicaciones CFTC/shutdown. No optimizar exclusiones según retornos.
- Respuesta primaria binaria `Y(t)=1[F1(día_entrada+5 observaciones EIA) > F1(día_entrada)]` y `0` si menor; diferencia nula se excluye. Dos reportes mensuales de raíces distintas son familias estadísticas distintas pero se corrigen conjuntamente.
- No calcular retorno simple o log en WTI por riesgo de precio negativo. No añadir variables de términos F1/F2 ni modificar ventanas.

## Estadística preregistrada

- Contraste unilateral Fisher exacto para cada raíz, `Pr(Y=1|X=1) > Pr(Y=1|X=0)`.
- Familia de 2 contrastes (CL y NG), Bonferroni `p <= 0.025` por raíz; efecto `P(up|X1)-P(up|X0) >= +0.10`, mínimo **8 eventos X1 y 8 eventos X0** en *cada* DEV y DIAG. Resultado preliminar favorable solo si ambas ventanas cumplen TODOS los criterios.
- DEV 2012-01-01 a 2018-12-31; DIAG 2019-01-01 a 2021-12-31; resultado a cinco observaciones también debe quedar dentro de su ventana.
- Si origen CFTC o EIA cambió SHA o faltan campos/series, resultado **BLOCKED_SOURCE** (no recomputar con datos corregidos, no sustituir proxy).
- Si no pasa, `NO_SUPPORT` para H-COT-1. Si pasa, `PRELIMINARY_DIAGNOSTIC_ASSOCIATION_ONLY`, NO rentable, no green económico, y requerirá otros datos/validaciones independientes.

## LIMITACIONES irrenunciables

Un SHA de archivo histórico CFTC no prueba su `first_published_at` original. El informe semanal se refiere al martes y generalmente se publica viernes 15:30 ET; festivos, revisiones y cierres pueden retrasar datos. El lag de 21 días y blackouts reducen, pero **NO eliminan**, ese riesgo. La serie EIA F1 cambia de contrato mensualmente y carece de fill/spread/expiry individuales; los precios históricos pueden ser revisados. DEV/DIAG de EIA ya se usaron por una hipótesis diferente; este nuevo screen debe etiquetarse exploratorio y jamás certificación OOS.

**Gobernanza:** USD0, no merge, no LIVE, no tamaño de posiciones de Trader, sin apalancamiento ni Risk/CIBO approvals, no abrir ningún holdout. Este documento se publica antes del runner de resultados; fijar el SHA del commit prereg en el código del futuro runner y demostrar Git ancestry en CI.
