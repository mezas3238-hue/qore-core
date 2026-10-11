# QORE SCALPER — AUDITORÍA XIV / P0 A/B ECONOMÍA PREREGISTRADA

**Repositorio**: mezas3238-hue/qore-core, branch agent/scalper-architect-b-methodology-20261010, PR #759 DRAFT. **Estado**: investigación GitHub-only, NO LIVE, NO MERGE, NO nuevas reglas de admisión a V49, NO expansión World Model.

## Tesis adjudicada y precauciones

La pregunta correcta NO es sólo si el evento CISD existe, sino si una selección incremental causal-first cambia los resultados económicos cuando se respetan SL estructural M15, target H1 disponible as-of, stop-first, salida de sesión y MAX3 global. El estudio anterior encontró 1090/2876 cierres/familias iniciales distintos de V49 (381/2876 era la comparación con un único snapshot); ventaja direccional a 15/30 min en subcohorte modificada NO equivale a rentabilidad o edge neto. Probabilidades subjetivas 30%/45%/20%/5% de auditor no sustituyen resultados ni sirven para escoger variantes.

## Diseño A/B congelado antes de conocer la economía nueva

**Libro y ventana**: V49 fuente inmutable n=2876, nueve mercados, 2025-09-17 hasta 2026-09-17, fuente proveedor M1 nativa read-only verificada GH run 35548099334 (SHA 18c338...). Original control V49 run 38053946695 (SHA e356...). Primer detector incremental completo run 38099916845 (SHA 82e5...), que no lee outcome ni futuro H1.state_until. Todos los identificadores `source_id` conservados.

**Control V49**: reconstruir por cada fuente el trade original desde M1 y exigir igualdad total de dataclass con el registro económico congelado. FALLO => NO CALCULAR alternativa. Después recuperar EXACTO n=2020 selección original global MAX3, n=1167 ganadores y net bruto -233.2693270763665099166092077R. No modificar control ni usar outcome para elegir estrategia.

**Alternativa investigación causal-first SOURCE-ANCHORED**:
1. Mantener cada H1/M15 parent, dirección, protected swing price y universo fuente V49 original. Esto es diseño pareado limitado, **no regenera todo el universo H1/M15 en streaming** y es una limitación metodológica obligatoria de reporte.
2. Sustituir la familia y `entry_at` por la primera emisión M1 incremental `online_discovered_at` de cada original source ID, sin retroceder la entrada a un timestamp de confirmación identificado posteriormente.
3. Precio de entrada = close de M1 nativo recién cerrado en `online_discovered_at`. Requerir source H1 as-of ya confirmado, M15 parent confirmado, mismo día/sesión operativa, SL M15 en lado estructural correcto.
4. Recalcular **sin outcome** el **mismo** target H1 causal V49 mediante `_untouched_h1_target_fast` con el propio nuevo instante/entry price, usando el historial exacto de lookback congelado V49 de **14 días**, NO 15. Si no existe un H1 objetivo delante, etiqueta `NO_UNTOUCHED_H1_OBJECTIVE`; si SL es inviable, `INVALID_M15_STOP`. NO inventar trade, no imputar PnL 0 a casos inválidos ni declarar veto metodológico.
5. Reejecutar `_replay_one` de V49: STOP_FIRST si mismo minuto toca SL+TP, luego TARGET, y SESSION_EXIT en último close de sesión. Agrupar todos los nueve mercados, MAX3 primero por close cronológico + símbolo + familia **sin seleccionar por PnL**.
6. Publicar PF bruto, DD bruto en R, wins/losses/flat, densidad elegible pre/post-MAX3, swaps y descomposición de 381/1090; registrar comparación total con V49 original. Cualquier exclusión de elegibilidad es limitación del experimento y NO un filtro comercial aprobado.
7. **No existe serie física BID/ASK/volumen de ejecución/fees de broker verificada** dentro del artifact M1: el esquema `CapitalizerM1Bar` representa sólo OHLC + volumen. Por tanto no se pueden afirmar ni PF neto de broker ni DD de equity % real. Requerir stream sincronizado de BID/ASK y comisiones especificadas por activo/lote/horario para replay físico. No vender un spread supuesto como medido.
8. Sólo si paso bruto demuestra mejora y se valida causalmente generación **completa** H1/M15/POI y estado heredado, construir replay no source-anchored y revalidar objetivos author-liquidity sin elegir cambios por resultados. Antes de nueva operación LIVE/OOS, preservar holdout y confirmación autor.

## P0 H1 111 y POI vela opuesta

El primer censo H1 XIII utilizó `DEV_WINDOW_START - 15 dias`, mientras V49 source constructor usa **14 días** (`DEFAULT_LOOKBACK`). Esta diferencia es un **defecto de reproducibilidad del auditor**: eventos y POI históricos pueden cambiar por distinto conjunto de candles. Se modificó sólo el test H1 para reproducir ventana exacta, no V49; rerun de nueve mercados para reclasificar los 111 antes de afirmar causas.

Fuente TTrades (15-Nov-2025): https://ttrades.com/understanding-candle-2-closures-within-the-fractal-model/ : C2 reversal exige barrido extremo, cierre de regreso al rango y POI HTF; en ausencia de swings y FVG, contempla vela opuesta. V49 sólo construye POI SWING/FVG H1. Por tanto **la ausencia de la variante vela opuesta NO puede explicar por sí misma un falso-negativo al re-ejecutar los mismos eventos que V49 sí generó**; sí revela una posible omisión de oportunidades del modelo del autor fuera del universo fijo de 2876.

No modificar parámetros ni pasar H1.state_until futuro a puerto cognitivo; pendiente verificar POI de timeframe superior y M15 swing protegido con fuente independiente del detector QORE.

## Implementación

- `src/qore/infrastructure/trader_lab/capitalizer_scalper_a2_fourteenth_causal_first_economics_v1.py`
- `tests/infrastructure/trader_lab/test_capitalizer_scalper_a2_fourteenth_causal_first_economics_v1.py`
- `.github/workflows/qore-scalper-a2-fourteenth-causal-first-gross-replay.yml`

Resultados se adjuntarán sólo con CI real **GREEN 11/11**; nunca inferir PF/DD por valor esperado de 15/30 minutos.

---

## RESULTADOS MEDIDOS DEL ENSAYO XIV (NO MODIFICAR PREREGISTRO RETROSPECTIVAMENTE)

### A. [GH Actions #38102352779 — 11/11 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38102352779): PF/DD bruto sobre nueve mercados

El replay de TODAS las **2876 fuentes originales** concilió completamente operaciones económicas V49 con las originales para cada símbolo, antes de evaluar candidata causal-first. 2876 IDs source conservados; **1090/2876** con primera familia/close online distintos, **381/2876** subcohorte estática original.
- Candidatas source-anchored **2816 elegibles**, **36** nuevo precio invalida lado del SL M15 y **24** no tienen objetivo H1 disponible delante; 60 sin lifecycle alternativo. Esto NO son vetos que se hayan aplicado a V49 ni evidencia de que el autor prohíba operar ese parent: son estados no ejecutables bajo el contrato de precios/stop/objetivo congelado para esta comparación.
- MAX3 global original **2020** vs MAX3 alt **1997**. No atribuir igualdad de densidad a la variante online; son **23 trades menos**.
- **BASELINE bruto V49** n2020, wins1167, losses852, flat1, PF **0.6644630742216047**, gross total **-233.2693270763665R**, DD máximo **236.1342843563359R**, gross winners mass +461.9427618322289R, gross losses -695.2120889085954R.
- **PRUEBA causal-first SOURCE-ANCHORED** n1997, wins1154, losses841, flats2, PF bruto **0.8425240504779709**, gross total **-109.0553894526897R**, DD máximo **114.7990990562515R**, beneficio bruto +583.4655306223729R, pérdidas brutas -692.5209200750626R.
- Diferencia PF **+0.178061** (+26.8% relativo), delta drawdown **-121.335185R** (-51.4%), delta neto **+124.2139376236768R**; ganancias+ pérdidas son trayectoria bruto sin spreads ni comisión.

**Veredicto económico P0:** mejora BRUTA real medida bajo política fijada SIN seleccionar por outcomes. El PF **permanece <1** y el neto **permanece NEGATIVO**. No declarar edge rentable ni probabilidad de certificación; tampoco atribuir todo el efecto al orden solo, porque 60 oportunidades pasan a no-elegibles y 23 salen del MAX3 en esta alternativa. Falta re-generación H1/M15/M1 full-online sobre población no condicionada y precio físico BID/ASK. NO CERTIFICABLE.

### B. [GH Actions #38102633581 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38102633581): retención por identidad, no por PF

- Baseline MAX3 original 2020; alternativa MAX3 1997. Identidades de MAX3 preservadas **1947**, perdidas **73**, añadidas **50**.
- De los **1167 ganadores originales**, **1137** siguen seleccionados (97.4%). Sus resultados originales positivos suman **449.7112689147351R** de **461.9427618322289R** (97.352%); esto es masa original preservada, no PnL de la variante.
- De los 1137 ganadores originales que continúan seleccionados, **1105** siguen ganando y **32** pierden bajo nuevo price/time/SL/TP.
- Requisitos owner `934 winners` y `415.74848565R` cumplidos, ambos PASS como restricciones de preservación de identidad; son objetivos internos, **NO reglas TTrades ni certificación económica**.

### C. [GH Actions #38102351044 — 11/11 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38102351044): los 111 H1 faltantes eran artefacto de ventana del AUDITOR

Al recrear los ORIGINALES con mismo exact `DEFAULT_LOOKBACK=14 días` de V49 y mismo stream nativo M1:
- Candle2 n2638, 2638 geometrías con POI interno fuente atestadas;
- Candle3 n238, 238 geometrías con POI interno fuente atestadas;
- **2876/2876** evento/POI QORE nativamente reconciliados, **0** source originales faltantes.
- **2372** de 2876 IDs con dos H1 pertinentes exactamente 60/60 minutos; **504** no alcanzan testigo exacto 60/60. No invalidar por ausencia de trading en algunos M1 ni certificar automáticamente las 504.
- El anterior resultado `111 sin reconstruir` se explica por la auditoría que utilizó 15 días de history (un día más) en un detector con POI persistentes: la diferencia de lookback es suficiente para cambiar las etiquetas seleccionadas. No imputar estos 111 a POI de vela opuesta, porque V49 no genera variantes de vela contraria.
- Sigue UNRESOLVED fidelidad POI HTF autor, M15 protected swing auténtico e integridad del H1 parcial, aun cuando 2876 eventos coinciden consigo mismos.

### D. Límite económico físico

La única serie M1 provider-native sellada aquí proporciona OPEN/HIGH/LOW/CLOSE y no pares BID/ASK sincronizados, swaps, comisión por volumen o fills MT5. **PF0.8425 y DD114.80R son brutos**, no PF/DD netos. No se puede deducir si un coste no-negativo arreglaría el PF bajo esta ruta; introducir costes de broker no mejora el resultado bruto ya negativo salvo cambios de ejecución físicos favorables no demostrados. La próxima etapa necesita evidencia real BID/ASK antes de certificar, no un spread supuesto.

**PR #759 DRAFT, no merge, no VPS, no MT5 LIVE, World Model congelado; CIBO/Shared sin cambios.**


## E. Fuente H1 con 14 días idénticos a V49

La comprobación final de GitHub Actions #38102651079 terminó correctamente: 2.876/2.876 orígenes H1 reconstruidos; 2.372 con dos velas completas 60/60; 504 sin dicha cobertura. Se detectaron 152 cierres H1 fuera de HH:00, y en ninguno de esos 152 la confirmación M15 ni la entrada M1 precedieron al cierre horario programado. Las estadísticas anteriores de 111 eventos sin reconstruir y 151 cierres no horarios, obtenidas con 15 días de historial, quedan sustituidas por las cifras de esta ejecución con los 14 días originales. Sigue pendiente la fidelidad de POI HTF y el OHLC de velas incompletas.
