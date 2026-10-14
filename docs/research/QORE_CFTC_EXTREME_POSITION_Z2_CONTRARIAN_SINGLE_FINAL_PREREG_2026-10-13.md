# QORE Futures A — H-COT-2: EXAMEN ÚNICO y FINAL de posicionamiento extremo contrario

**PREREGISTRO INDEPENDIENTE Y ANTERIOR A TODA EJECUCIÓN DEL RESULTADO H-COT-2.**
**Modo:** examen de asociación exploratoria **no negociable**. **Cero mercado OOS reservado.**
**Universo:** EXCLUSIVAMENTE WTI CL `067651` y Natural Gas NG `023651`, CFTC Disaggregated **Futures Only**; precios de referencia EIA F1 existentes (no OHLCV ni fills).
**Presupuesto:** USD 0. Sin nuevos proveedores, sin GC/HG/ZC/ZS en este examen, sin LIVE/MERGE.

## 1. Estado previo y fundamento

El H-COT-1 anterior de **cambio a 4 semanas** sobre WTI/NG terminó `NO_SUPPORT`; ese resultado no se reinterpreta ni se retoca. H-COT-2 tiene un mecanismo **distinto**: cuando la posición neta de Managed Money alcanza una desviación histórica extrema, la reversión del precio referencial F1 a seis semanas puede exceder un equilibrio direccional simétrico. Es una hipótesis falsable, **no** una consecuencia universal de la literatura: Managed Money puede seguir tendencias y no siempre precede reversión. Véase Boos & Grob, *Tracking speculative trading*, Journal of Financial Markets (2023); CFTC Disaggregated Explanatory Notes y calendario oficial (martes de posición → reporte por lo general viernes 15:30 ET).

Al fijar este examen, DEV/DIAG EIA de 2012–2021 ya se habían usado en otras preguntas: **NO están frescos ni proporcionan OOS independiente**. Solo sirven como diagnóstico cerrado. Aunque el resultado fuera favorable, no se afirmaría edge monetizable.

## 2. Datos inmóviles

- CFTC código `067651` (WTI) / `023651` (NG), `M_Money_Positions_Long_All`, `M_Money_Positions_Short_All`, `Open_Interest_All`, `As_of_Date_In_Form_YYMMDD`; años **2012–2021**. Los 10 SHA256 oficiales de archivo permanecen fijados en `.github/scripts/qore_futures_a_cftc_managed_money_one_shot_screen_v1.py`.
- EIA WTI `RCLC1d.xls` SHA256 `a55a70d2438ebdc600a77f9d3f9c46be1e2f480ac5ffec3bb753c61cf21db0c9`; EIA NG `RNGC1d.xls` SHA256 `1e71a774943c00cdba337c8be1c9888ea1d56b175c446527cc0d94f7dc2b03f1`. Usar exclusivamente parser previo que trunca **antes del 2022-01-01**.
- Si cualquier checksum, mercado, campo o formato difiere: `BLOCKED_SOURCE`; no relajar hash ni cambiar periodos, no inspeccionar el holdout para resolverlo.

## 3. Señal: Z-score extremo y contrario, sin selección ex post

1. `p_t=(MM_long_t-MM_short_t)/open_interest_t`; open_interest positivo; semanas ordenadas por fecha original, sin revisión por retorno.
2. Para cada raíz, calcular `z_t=(p_t-mean(p[t-104:t])) / stdev_sample(p[t-104:t])`; exactamente **104 informes PREVIOS**, excluir t del estimador. Si desviación típica = 0, omitir; no usar ventanas futuras, normalización full-sample ni z de cambio a 4 semanas.
3. Extremo alcista `z_t >= +2.0` ⇒ hipótesis **BAJISTA** a futuro; extremo bajista `z_t <= -2.0` ⇒ hipótesis **ALCISTA**. Igualdad al umbral incluida.
4. Capturar solo primera **entrada en extremo**: `z[t-1]` debe estar fuera de ese mismo extremo (ej.: nuevo cruce alcista requiere `z[t-1] < +2`). Si no existe Z[t−1] histórico, no es cruce elegible. No capturar cada una de las semanas consecutivas de un extremo.
5. **Separación causal anti-solape:** aceptar como máximo **un evento por raíz cada 8 informes** tras último aceptado, y descartar si el primer día EIA previsto de entrada sería anterior o igual a la fecha de salida del evento anterior. No optimizar selección por rentabilidad.
6. Blackouts de publicación heredados, fijados **antes de este resultado**: rechazar observaciones CFTC con fecha as-of dentro de `2013-09-01..2013-11-30` y `2018-12-01..2019-04-30`. El siguiente evento elegible se decide cronológicamente; no mover blackouts tras ver PnL.
7. Lag conservador de disponibilidad: primer precio referencial EIA en **o después de t + 21 días naturales** de la fecha CFTC as-of. La CFTC suele publicar viernes 15:30 ET sobre posiciones martes; 21 días supera retrasos ordinarios, pero NO demuestra historiales exactos de first-publication.
8. Salida: primer precio diario EIA en o después de **fecha de entrada + 42 días naturales** (exactamente horizonte seis semanas). No probar 4, 5, 7, 8 semanas como alternativas. Si entrada o salida no están en la misma ventana DEV/DIAG, excluir.
9. Respuesta binaria `y=1` si F1 salida < F1 entrada tras extremo +2, o F1 salida > F1 entrada tras extremo −2. `y=0` si contrario. Empates F1=F1 se excluyen. El valor negativo WTI se conserva y no se log-transforma. No calcular PnL ni retornos.
10. Un informe extremo puede producir como máximo un evento; `z[t-1]`, media, varianza y comparación temporal se calculan solo con posiciones históricas previas.

## 4. Una única familia y criterio estadístico congelados

- **Hipótesis:** `Pr(reversión correcta|nuevo cruce z>=+2 o z<=−2) > 0.5` a 42 días, test binomial unilateral EXACTO por mercado y por ventana.
- Dos raíces (WTI y NG) son dos pruebas en **una sola familia**; Bonferroni con `alpha <= 0.025` por raíz. El mismo criterio debe cumplirse **separadamente en DEV y DIAG**; DEV no selecciona parámetros, DIAG no se usa para tuning.
- **Mínimo efectivo:** **8 eventos no superpuestos por raíz y ventana**, de los cuales al menos **2 eventos de cada signo extremo** (≥2 de z≥+2 y ≥2 de z≤−2). Si falta: `INCONCLUSIVE_INSUFFICIENT_INDEPENDENT_EXTREMES`, no un NO_EDGE.
- **Tamaño económico-diagnóstico mínimo de señal:** tasa de aciertos de reversión ≥ **65%** (15 puntos porcentuales por encima de 50%), simultáneamente con p ≤0.025. Esto es un criterio para un *test referencial*, NO break-even de futuros.
- **DEV:** informe CFTC y entrada/salida EIA contenidos en `2014-01-01..2018-12-31` (2012–2013 sólo warmup del Z); **DIAG:** los tres hitos dentro de `2019-01-01..2021-12-31`. Excluir bordes que cruzan ventanas, sin moverlos.
- **Éxito de familia:** WTI y NG pasan tanto DEV como DIAG; de lo contrario `NO_SUPPORT_FINAL_CFTC_FAMILY_FOR_QORE` si hay muestras suficientes, o `CLOSED_INCONCLUSIVE_LOW_POWER` si faltan.
- La conclusión operativa en cualquiera de los dos casos negativos/inconclusos es **PAUSAR/CERRAR la familia CFTC para QORE**: no extender a GC/HG/ZC/ZS, no buscar otros Z thresholds ni añadir comerciales ni rehabilitar 4-week changes. Un inconcluso NO refuta universalmente a todos los modelos de posicionamiento.
- Incluso en éxito, `PRELIMINARY_REFERENCE_ASSOCIATION_NOT_TRADABLE`; habría que recertificar con datos de precios negociables por vencimiento, costos, fechas as-of verificadas y holdout independiente **solo bajo autorización adicional**.
- Nunca reducir p a .05, ni cambiar extremo z=2, lookback=104, salida=42d, cooldown=8 semanas, ventanas, ni mínimos tras ver las observaciones.

## 5. Límites del test y cronología

El archivo CFTC disponible es una descarga **actual** de reportes históricos: no da ni certifica timestamp histórico individual de cada publicación; algunos fueron corregidos o publicados tarde. El retraso 21 días **no** sustituye un archivo point-in-time auditado. El precio EIA rank F1 cambia de contrato, no es un fill replicable. Binomial 0.5 supone probabilidad simétrica bajo nulo; sesgos tendenciales podrían violar esa simplificación, de modo que resultado positivo requeriría falsificación adicional, no trader promovido. Eventos de WTI y NG pueden tener shocks comunes; NO sumar sus p o muestras en un pseudo-N independiente.

**Gobernanza inmutable:** prereg commit en rama hija ANTES de subir runner de resultados, Git ancestry y blob fijo en CI, US$0, no merge, no mercados extra, sin OOS reservado ni LIVE.
