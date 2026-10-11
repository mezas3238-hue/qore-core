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
