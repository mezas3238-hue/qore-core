# QORE Scalper — séptima auditoría: H1 → M15 → M1, descomposición exacta de hitos

**Fecha:** 2026-10-10. Arquitecto B metodología, PR #759, issue #757; coordinación arquitecto A PR #758, issue #756; PR #623. **Estado investigación; NO VPS/LIVE/merge/certificación.**

## 1. Estado probado ANTES del ensayo

El baseline H1 same-direction random sobre el mismo libro V49 9/9 [#38067672878](https://github.com/mezas3238-hue/qore-core/actions/runs/38067672878) encontró **-12.55pp** a 30m para las entradas V49 contra relojes H1 emparejados; CI bootstrap agrupado por operating date [-14.53,-10.37]pp. Es evidencia de que **la selección H1+M15+M1 produce entradas temporalmente menos favorables que el grupo aleatorio condicionado a H1**. *NO identifica por sí sola a M1*: el nulo carecía de POI y protected swing M15, stop válido y CISD exigidas a las entradas reales.

**Aserción causal de código verificada antes de medir:** `capitalizer_high_frequency_capacity_census_v49.py::_earliest_m1_trigger` devuelve `confirmed_at` y el precio `confirmation_close` del observador CISD; `materialize_trade_intent` usa exactamente la misma fecha de entrada en el libro V49. Por construcción del **simulador** CISD→entry delay **0 minutos**. No es una afirmación sobre latencia física de MT5 (fuera de este replay). Alguien que diagnostique demora después de CISD en V49 debe probar un caller distinto, no inferirla de PF.

## 2. Diseño causal, 9 activos nativos, sin HARKing

**Fuente de resultados inmóvil:** original V49 source+trade `#38053946695`, provider-native M1 `#35548099334`. N=2876 SOURCE ID, MAX3 N=2020, 1167 positivos, gross -233.269327R. Se comprueba identidad de símbolo, fecha, M15 stop, target, entrada y dirección antes de extraer fases. Re-ejecutar observador V48 exacto **solo hasta la CISD original**; cualquier diferencia de ruta o hora **invalida** el ledger, jamás se elimina el trade.

Para cada una de las 2876 oportunidades guardar:

- **M15_SETUP_CONFIRMED**: `m15_setup_confirmed_at`, protegida la tesis M15 desde esa confirmación. Se toma como ancla superior, no como trade M1 ejecutable.
- **LIQUIDITY_SWEEP_CISD**: `sweep_at` (cierre de vela barrido), `causal_series_ended_at` (fin serie de velas M1 opuestas), `confirmed_at` (cierre CISD), `ORIGINAL_ENTRY_EXECUTED` (mismo cierre). **P0 de epistemología:** el observador Sweep no produce un M1 protected swing separado con `confirmed_at`; su sweep extreme no debe denominarse protected swing confirmado. En esa ruta dejar `M1_PROTECTED_SWING_BECOMES_VALID` explícitamente ausente, NO inventado.
- **FVG_RETRACE_CISD**: `fvg_confirmed_at` al cerrar tercera vela, `fvg_interaction_at` al cierre del primer retrace, `swing_occurred_at` reconstruido mediante `observe_first_structural_cisd` del **contexto local original**, etiquetado `PIVOT_BAR_CLOSE_UNPROTECTED`; el pivot solo se vuelve protected en `cisd_confirmed_at`. El CISD confirma y la entrada original ocurre el mismo instante, sin retardo pos-CISD.
- En cada hito realmente emitido, usar último cierre M1 disponible `<= stage_confirmed_at`, si no existe precio M1 realmente observado registrar `NULL` en vez de imputar.
- Etiquetas retrospectivas **+15/+30/+60 min** a favor del H1 original, requiriendo nativas M1 completas en sesión NY/DST, SIN imputar huecos, sin leer vela incompleta o final H1. Son evaluaciones hipotéticas de direccionalidad si uno **hubiera observado** en aquel hito, NO entradas TTrades antes de CISD, ni P&L/edge monetizable.

**Hipótesis descriptivas preregistradas**: diferencias de probabilidad favorable de `SWEEP_CONFIRMED_BAR` a `CISD_CONFIRMED` por fuente pareada, o `FVG_FORMATION_CONFIRMED` a `CISD_CONFIRMED`. Se evalúa por familia, 3 sesiones y 9 activos; registrar cobertura, parejas disponibles y **duración** M15→CISD, barrido/FVG→CISD. Etiquetas H1, familia y tiempos no se deben usar como filtros in-sample.

**Importante:** comparar el resultado a 30 minutos de un timestamp más temprano con el de un timestamp posterior implica ventanas distintas y una selección retrospectiva de escenarios. No prueba que tomar el trade antes sea una alternativa legítima con el mismo stop, target ni riesgo, porque el setup M1 puede no existir en aquel instante. Si el desfase descriptivo identifica un sitio problemático, se abre una intervención única con fuente más OOS y un replay físico distinto; no se habilita a poner órdenes antes de confirmation.

## 3. Confusores y fuente Candle 3 (sin cambios en el trader)

La sexta auditoría ya observó que el grupo de precio en el último tercio del **rango H1 parcial as-of** rindió +30m **47.2%** frente al primero **29.8%**. La hipótesis DeepSeek de 'first 55%, last 35%' **no coincide con el censo medido**. Tampoco es lo mismo tercio de la hora H1 que tercio del precio H1 parcial. Fuente y liquidación de instrumentos no se atribuyen a M1 sin controlar H1-age, hora NY, mercado y volatilidad.

Los tests `test_capitalizer_scalper_h1_c2_c3_primary_source_characterization_v1.py` describen dos artículos de TTrades potencialmente divergentes en Candle 3 (2025-12 vs 2026-01). Se mantienen ambas interpretaciones catalogadas como SOURCE_AMBIGUITY. **No cambiar C3 mientras esta prueba M1 está en marcha**, no seleccionar definición C3 por PF, no mutar 2.876 fuentes originales. A/B de definiciones C3 requiere su propio preregistro, decisiones as-of, nueve activos, periodo independiente y separación explícita del siguiente ensayo M15/M1.

**Código nuevo**: `src/qore/infrastructure/trader_lab/capitalizer_scalper_m1_stage_chain_forensic_v1.py`, pruebas `tests/infrastructure/trader_lab/test_capitalizer_scalper_m1_stage_chain_forensic_v1.py`, ejecución exclusiva GitHub `.github/workflows/qore-scalper-a2-seventh-m1-stage-chain.yml`. Las salidas JSONL por source_id no contienen decisiones nuevas.

**Veredicto prerregistro:** hipótesis CISD→entry post-delay incompatible con simulador V49; causa del deterioro conjunto H1+M15+M1 NO resuelta aún. Registro exacto de hitos y validación causal exigidos antes de sacar conclusiones.

## 4. RESULTADO FINAL — 9/9 nativos M1 originales, ninguna regla cambiada

**Corrida** [GitHub Actions #38068938682](https://github.com/mezas3238-hue/qore-core/actions/runs/38068938682): **11/11 SUCCESS** (contrato + 9 mercados + agregado). La reconstrucción con los observadores **reales** Sweep/FVG de V49 conciliaba exactamente las **2876 oportunidades SOURCE, 2020 MAX3**, **1167 positivas**, -233.269327R. Ninguna fuente se perdió en el join, todas pasaron `confirmed_at original == confirmed_at reconstruido`, `decision_reference_price == close M1`, `M15 protected stop == source stop`. El muestreo depende exclusivamente del M1 nativo del proyecto y no usa outcomes para seleccionar eventos. **No se creó una sola operación contrafactual autorizada**.

| Medida H1-aligned favorable +30m | Sweep+CISD (n 954 seleccionados) | FVG_RETRACE_CISD (n 1066 seleccionados) |
|---|---:|---:|
| M15 setup confirmado | 419/943 = **44.43%** | 555/1060 = **52.36%** |
| Sweep candle cerrada | 480/915 = **52.46%** | n/a |
| Serie opuesta M1 finalizada | 484/913 = **53.01%** | n/a |
| FVG M1 confirmada | n/a | 513/1045 = **49.09%** |
| Retest al FVG, vela cerrada | n/a | 567/1041 = **54.47%** |
| Pivot M1: cierre de vela, aún NO protected | n/a | 666/1036 = **64.29%** |
| **CISD M1 confirmada / EXEC original** | **362/901 = 40.18%** | **477/1023 = 46.63%** |

**Contraste PAREADO preregistrado, solo mismos source ID con datos M1+30 completos en ambos hitos:**
- **Sweep candle → CISD**: **N=900**, 475 favorables si se observa al cierre sweep frente a 362 al cierre CISD; cambio **-12.5556 puntos porcentuales** en favorabilidad de dirección H1 a +30m. El cierre Sweep es *no ejecutable según la metodología original* porque todavía falta confirmar CISD, por lo que la diferencia NO equivale a R perdido ni demuestra que entrar en sweep sea mejor con stop/target.
- **FVG formó → CISD**: **N=1023**, 506 favorables en cierre FVG contra 477 al cerrar CISD; delta **-2.8348 pp**. Este pareado tiene menos pérdida que la ruta Sweep según ancla FVG *formación*, pero el FVG aún no había sido testeado y tampoco es setup confirmado.
- Pivote FVG a +30m **64.29%** sobre 1036 con cobertura; posterior cierre CISD **46.63%** sobre 1023; **no comparar esas dos tasas como pareja exacta** porque tienen denominadores distintos, aunque es un indicio de concentración temporal post-pivote para fase posterior preregistrada.
- Mediana **M15 CISD setup→M1 CISD: 17m**, y mediana **evento Sweep/FVG formación→CISD: 6m**. Por familia, Sweep 15m M15→CISD y 4m Sweep→CISD; FVG 19m M15→CISD y 9m FVG→CISD.
- **En las 2020 operaciones, CISD→entrada fue exactamente CERO minutos**; no existe demora extra tras la CISD en este *simulador*, aunque no mide slippage ni latencia MT5.

**Fuente y trazabilidad**: `src/qore/infrastructure/trader_lab/capitalizer_scalper_m1_stage_chain_forensic_v1.py` reconstruye cada ruta con el mismo `observe_first_m1_cisd` u `observe_first_m1_fvg_cisd_continuation` de V48/V49. Cada fila registra stage, timestamp, precio M1 al cierre y outcomes forward *POST-HOC, NEVER ENTRY*. El observador Sweep **no emite** un protected M1 swing individual: el extremo barrido no fue relabelled 'protected'. En FVG el pivot se observa primero en M1 pero solo pasa a protected al cierre CISD; nunca se antepone confirmación estructural a su existencia. El M15 protected swing de V49 queda independiente de estos hitos.

### Interpretación técnica, NO parametrización

**Localizado con evidencia**: el desfase desfavorable del procedimiento de selección temporal ocurre ya dentro de la secuencia Sweep→CISD y parece relevante alrededor de FVG retrace/pivot→CISD, **no** en una ejecución retrasada después de la CISD. Sin embargo no es prueba de error literal de autor TTrades: los hitos anteriores carecen de confirmación de entrada, y la ventaja medida depende del comportamiento *futuro* de un subconjunto seleccionado porque finalmente sí generó CISD. No basta para adelantar la entrada (lookahead) ni para alterar protected swings. Sigue viva la hipótesis de mala selección del POI, interacción H1 edad/regímenes, riesgo M15, y una metodología fuente fiel pero poco rentable con esta estrategia. NO ha sido demostrado que el 'M1 CISD por sí solo' destruya un edge operable.

**Contradicción C3** sigue UNRESOLVED, sin cambios del generador. Para A/B formal diciembre/enero deben generarse por separado nuevos universos de eventos H1 con todo lo demás congelado, prereg y compararse frecuencias, direccionalidad y economía SIN elegir ganador por PF in-sample. Aun si cambia H1, esa prueba es otra hipótesis upstream, no se mezclarán simultáneamente cambios M1.

**Cobertura temporal real de estos últimos replays:** `DEV_WINDOW_START=2025-09-17` a `DEV_WINDOW_END=2026-09-17` (12 meses). La solicitud de contrastar régimen 2023/2024/2025 **no puede declararse cumplida con este único universo V49**; requiere dataset fuente preservado y periodos OOS antes de concluir estabilidad de años múltiples.

### Veredicto certificado

**SCALPER: NO CERTIFICABLE.** Ningún filtro, stop, target, regla de edad H1 ni anticipación de CISD fue añadido al trader. La selección MAX3, ganadoras 1167, R original y todo el universo siguen congelados. No hay simulación con spreads/comisión MT5, no se ha verificado intervención A1 Master Frame, ni ensayos independientes OOS. El diagnóstico permanece marcado **RESEARCH ONLY**, PR de continuidad DRAFT y sin merge.
