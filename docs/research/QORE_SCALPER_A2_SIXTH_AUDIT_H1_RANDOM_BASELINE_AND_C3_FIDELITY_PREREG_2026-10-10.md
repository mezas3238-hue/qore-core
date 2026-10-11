# QORE Trader Scalper — sexta auditoría, H1 causal y benchmark aleatorio de timing M1

**Fecha** 2026-10-10. Arquitecto B metodología / PR #759 / issue #757; colega A cognitiva / PR #758 / issue #756; PR padre #623. Investigación únicamente, GitHub Actions, cero VPS, LIVE, despliegue, merge o aprobación de trader.

## 1. Evidencia congelada antes de leer resultados de ningún benchmark

- Control original V49: native M1 SHA `18c338aedd5013ce65a6cb6408ffbc2e904a6217` [GitHub Actions #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), libros V49 source+trade SHA `e356e7a52541e99533b25ecfef0ab9c4e9ce03c0` [#38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695). Exactas 2.876 oportunidades / 2.020 MAX3 (1.167 R positivos), PF 0.66446, -233.269R bruto. Sin modificar entradas, H1 bias, M15, stops, targets, ni timings.
- [Quinta auditoría #38063930894](https://github.com/mezas3238-hue/qore-core/actions/runs/38063930894), 11/11 GREEN, origin labels +15m 874/1975=44.25%, +30m 839/1924=43.61%, +60m 837/1824=45.89% favorables dentro de barras M1 **continuas** y sesión. Posición precio en rango H1 parcial: FIRST 158 trades, 29.8% positivo a +30m; LAST 1337 trades, **47.2%** positivo +30m. La hipótesis de DeepSeek 55% primer tercio vs 35% último tercio es **refutada descriptivamente por los datos existentes**; no deriva de ellos una regla de gate H1.
- Sus 44–46% NO establecen por sí solos si el **sesgo H1** carece de edge o si su **sistema de ejecución M1** empeora una tesis potencialmente buena. Un benchmark con tiempos randomizados puede comparar *timing condicional al estado H1*, no identificar por sí solo qué parte de la teoría TTrades es incorrecta.

## 2. Experimento PREREGISTRADO — mismo H1, misma sesión, mismo mercado

**Código**: `src/qore/infrastructure/trader_lab/capitalizer_scalper_h1_direction_random_baseline_v1.py`.  
**Unit tests**: `tests/infrastructure/trader_lab/test_capitalizer_scalper_h1_direction_random_baseline_v1.py`.  
**Workflow**: `.github/workflows/qore-scalper-a2-sixth-h1-bias-null.yml` y [GitHub Actions por PR #759](https://github.com/mezas3238-hue/qore-core/actions/workflows/qore-scalper-a2-sixth-h1-bias-null.yml).

### Tres controles PREDEFINIDOS

- **B0 REAL**: las mismas entradas originales M1, `entry_price` y direction derivadas de H1 en V49. Etiquetas retrospectivas de cierre de precio normalizadas por signo a +15m, +30m, +60m; ninguna toca la decisión ni simula gestión de stops o comisiones.
- **B1 UNIFORM_H1_STATE**: **32 draws/entrada V49**, semilla `sha256("A2_SIXTH_PREREG_20261010_SOURCE_SHA256_SEED_01"|source_id|mode)`; seleccionar de cierres M1 con mismo activo, sesión NY y fecha operativa, y **misma tesis H1 vigente causalmente en ese candidato**. Un candidato está en tesis si su reloj es posterior a `source.h1_state_from` (fecha confirmada antes de la entrada real) y no ha ocurrido una señal opuesta H1 confirmada hasta *ese* candidato. Lista de contraseñales reconstruida con detectores V49 _build_h1_bias_events sobre H1 provenientes del M1 nativo, con `event.confirmed_at <= candidate`. **Prohibido** usar `source.h1_state_until`, que codifica caducidad por un evento H1 futuro. Tampoco se permite consultar resultados futuros para generar la muestra, ni usar el SL/TP original para seleccionar.
- **B2 MATCHED_H1_CLOCK_THIRD**: mismas reglas que B1, 32 draws dentro del mismo tercio de **reloj H1** de la entrada V49 (0–20, 20–40, 40–60 minutos). Controla de manera parcial el sesgo por horario H1. NO iguala por edad, rango de precio o M15 estructura, y no debe confundirse con un experimento causal totalmente ajustado.
- **B3 RANDOM_DIRECTION_NEGATIVE_CONTROL**: en la fecha/hora original y precio original, aleatorizar el signo BUY/SELL por moneda al aire determinista 32 veces con semilla de fuente propia. Comprueba el ~50% esperado sin sesgo de dirección. **NO** es una estrategia física sin sesgo, puesto que no modela stops, spreads, ejecuciones, restricciones de cortos, ni pérdidas.

### Controles causales y estadísticos

- El candidato aleatorio siempre es **el cierre de una vela M1 realmente observada**, no el high/low final de un M1 en curso; no entra antes de estar confirmado el estado H1.
- M1 de futuro +15/30/60m se usa SOLO para los **resultados de investigación después de haber seleccionado las 32 muestras aleatorias**. Cada horizonte requiere todas sus velas nativas M1 contiguas dentro de la sesión; si hay hueco/salida de sesión, outcome = `None`, se reporta cobertura por separado. Comparación pareada se calcula únicamente para los source IDs con resultado real y al menos un sample random cubierto; las restantes operaciones siguen en la población pero su estimación de efecto se marca no disponible.
- Nula aserción de independencia por 2.020 trades correlacionados/repetidos. Intervalos preliminares de delta real – baseline mediante **1.000 bootstraps agrupados por `operating_date` en los nueve mercados**. El 95% CI no sustituye OOS, no justifica corte temporal ni búsqueda de la mejor semilla; 32 draws aproximan el nulo y generan varianza Monte Carlo adicional.
- Se informa diferencia de probabilidad de signo favorable a +15/+30/+60 y por segmento `session`, `market`, `family`, `bias_age`. Las dos comparaciones B1 y B2 son diagnósticas exploratorias; no aplicar ganancia/PF ni inferir que el mismo sesgo H1 aislado tendría PF distinto: las entradas random NO poseen SL/TP natural para ejecución real.
- Criterios EVIDENCE FAIL-CLOSED: 9 mercados, fuente 2.876 IDs exclusivos, MAX3 conjunto sin outcome 2.020, 1.167 ganadoras originales, P&L original exactamente -233.269327R. Cero cambio al libro V49. No eliminar variantes por resultado. Toda muestra de benchmark conserva su cobertura y contador de candidatos por episodio; no sustituir un denominador pequeño por eficacia falsa.
- Deliberadamente **NO** reclasifica R de winners, señales V49 ni mide PF para instantes aleatorios; la comparación de PF requeriría definir una política simulada completa ex ante y precio de ejecución real, por tanto es otra fase.

**Limitación conocida ex ante:** sampling de un episodio H1 completo es investigación offline; al escoger candidatos tras la entrada real se está describiendo estadísticamente el estado que resultó vigente, pero la elegibilidad de CADA candidato se determina únicamente por eventos H1 ya confirmados hasta ese momento. El hecho de conocer ex post todo el conjunto de candidatos no convierte ese test en un trader que conocía su duración futura. El emparejamiento B2 iguala tercio horario, no runway ni estructura M15 ni el POI. Correlación no es causalidad.

## 3. Auditoría upstream de la Candle 2/3 closure — dos fuentes primarias divergentes

Verificado directamente el código:
- `src/qore/infrastructure/trader_lab/capitalizer_source_observation_detectors_v2.py::detect_candle2_reversal_closure`: LONG `candle2.low < previous.low`, cierre vuelve dentro `previous.low < candle2.close <= previous.high`, POI presente; SHORT espejo. Esto **coincide en términos generales** con [TTrades Understanding Candle 2 Closures, 2025-11-15](https://ttrades.com/understanding-candle-2-closures-within-the-fractal-model/) y [TTrades CISD Confirms Swing Points, 2026-01-10](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/). Pero `point_of_interest_present` se alimenta por interacciones de múltiples POIs, no necesariamente la **secuencia exacta de velas que hizo sweep**; hay que verificar temporalidad y autenticidad del POI.
- `detect_candle3_confirmation` en V49: C3 debe quedar **dentro del high/low C2** y cerrar más allá del **BODY** C2, siempre que C2 no confirmara y POI exista. **SOURCE AMBIGUITY**: [TTrades Candle 3 Closure guide, 2025-12-03](https://ttrades.com/candle-3-closure-a-complete-guide-to-identifying-continuations-and-reversals/) exige que C3 NO barra el high/low C2 pero cierre sobre/bajo el body; eso es compatible con el detector V49. Sin embargo [TTrades CISD Confirms Swing Points, 2026-01-10](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/) habla de C3 que cierra sobre la apertura **y el rango** de C2, interpretación que choca con `c3.high <= c2.high`. También TTrades Best Trading Strategy 2026 (May) distingue C3 envolvente. **No dictar un cambio basado en una cita aislada**; registrar el conflicto, reconstruir casos visuales primarios y añadir fixture por interpretación antes de modificar la ruta C3.
- **Importante hallazgo potencial distinto**: [TTrades CISD confirms](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/) describe explícitamente que luego de la closure H1 se verifica un lower timeframe CISD para declarar protected swing. V49 genera H1 bias de C2/C3 + POI y posteriormente M15 swing+CISD; auditoría cruzada de la conexión H1 closure↔lower-TF CISD, especialmente para eventos C3 y transiciones de estado, sigue necesaria.
- **No modificar código fuente del generador ni retro-ajustar reglas** durante esta prueba de baseline. Una fuente discutida sin dataset de ejemplos no justifica invertir C3 de golpe en producción. Separar `SOURCE_EXPLICIT`, `SOURCE_CONFLICT`, `INTERPRETATION`, `QORE_ENGINEERING_RULE`, `UNRESOLVED`.

## 4. Gate para la fase siguiente

Sólo después de resultados B0/B1/B2/B3 y validación de fuente se podrá formular una intervención **única** causal, preregistrada y probada en datos independientes, con todas las reglas de conservación del Owner (≥934 ganadoras originales, ≥415.75R original winner mass, no menos de 500 como mínimo investigación, PF OOS >1.5, DD≤6R, costes reales bid/ask comisión y Master Frame cognitivo A1). Cualquier PF de baseline aleatorio sin replay físico está prohibido.

**Estado al preregistro:** no se conocen resultados del benchmark nuevo, en GitHub únicamente; Scalper sigue NO CERTIFICADO.

## 5. RESULTADOS — NULO H1 CON DIRECCIÓN IDÉNTICA, 9/9 mercados, versión congelada

**Run base del experimento [#38067672878](https://github.com/mezas3238-hue/qore-core/actions/runs/38067672878), SHA `c654a6847e380b3c4a61e566549a4f6a7d6f5e64`, 11/11 GREEN** (contrato + 9 mercados nativos + agregado). [Artifact agregado #11676370363](https://github.com/mezas3238-hue/qore-core/actions/runs/38067672878/artifacts/11676370363); nueve archivos por symbol, fuente/trade IDs, 32 réplicas y conteos de elegibilidad disponibles en esa corrida. La validación volvió a conciliar 2876 fuentes únicas, 2020 MAX3, 1167 ganadoras, -233.269327R de resultado ORIGINAL. **No es replay de entradas aleatorias con SL/TP, ni PF de trader aleatorio.**

| Horizonte fijo | Original a favor | Baseline B1 H1-state uniforme | Baseline B2 H1-clock-matched | Control B3 coinflip |
|---|---:|---:|---:|---:|
| +15m | **874/1975=44.253%** | **53.101%** | **53.200%** | 49.949% |
| +30m | **839/1924=43.607%** | **54.902%** | **56.161%** | 49.587% |
| +60m | **837/1824=45.888%** | **57.827%** | **58.612%** | 49.741% |

La estadística B1/B2 reportada es el promedio de proporciones nulas por **ID original y muestras cubiertas**, comparado con las mismas fuentes con datos reales válidos; es más apropiado para un **pareado condicionado a fuente** que sumar cada barra random como trade independiente. Los informes detallan cobertura y missing por grupo. No hay nuevas oportunidades ejecutadas.

**Diferencia ORIGINAL − NULO de dirección al +30m:**
- B1 sin ajustar reloj: **−11.295 puntos porcentuales**; bootstrap de 1000 resamples por fecha operativa NY en 9 mercados (313 clusters): intervalo 95% **[−13.427, −9.099] pp**.
- B2 mismo tercio reloj H1: **−12.554 puntos porcentuales**, intervalo 95% **[−14.534, −10.373] pp**.
- +15m B2 **−8.947pp**, intervalo **[−11.314, −6.610]pp**; +60m B2 **−12.723pp**, intervalo **[−14.624, −10.902]pp** (312 clusters).
- Intervenciones de muestra B1/B2 se definen **antes de comprobar desenlaces**, SHA/seed y 9/9 ledger reproducibles. La incertidumbre del estimador se calcula por cluster fecha para mitigar múltiples oportunidades correlacionadas, pero **no** demuestra causalidad ni robustez OOS, y 32 draws/registro aportan ruido Monte Carlo.

### Desglose por grupo al +30m, SIN FILTROS

| Grupo V49 | Original positivo 30m | B1 nulo H1 (%) | Diferencia Original−B1 (pp) |
|---|---:|---:|---:|
| Asia (725 ops totales) | 45.74% | 56.05% | −10.31 |
| Londres (573) | 42.64% | 54.04% | −11.40 |
| Nueva York (722) | 42.17% | 54.39% | −12.22 |
| FVG_RETRACE_CISD (1066) | 46.63% | 55.81% | −9.18 |
| LIQUIDITY_SWEEP_CISD (954) | **40.18%** | 53.87% | **−13.70** |
| Edad H1 <60min (69) | 55.88% | 58.21% | −2.33 (muestra insuficiente) |
| Edad H1 60–180min (1305) | 45.17% | 56.66% | −11.49 |
| Edad H1 ≥180min (646) | 38.77% | 50.67% | −11.91 |

Los nueve mercados presentan diferencia negativa a +30m en B1: AUDJPY −7.42 pp, AUDUSD −9.90, EURUSD −9.89, GBPJPY −14.69, GBPUSD −12.91, NAS100 −16.16, USDCAD −9.79, USDJPY −8.81, XAUUSD −10.26. **Ningún mercado queda redimido por este análisis, que sigue IN-SAMPLE y correlacional**.

### Dictamen de la prueba planteada por DeepSeek

El escenario observado es precisamente el de un sesgo H1 que, al tomar tiempos random **dentro del mismo estado confirmado**, presenta más avances direccionales que las entradas M1 reales. El control B3 en los timestamps originales no tiene >50%; esto sugiere **valor descriptivo de la información H1 cuando se evalúa en puntos distintos**, junto a una **penalización fuerte del timing o del mecanismo de admisión M15/M1**.

**Esto NO identifica todavía exactamente cuál componente causa la penalización**:
- B1/B2 comparan tiempos de la tesis H1, NO exigen que los tiempos random coincidan con protected swing M15 confirmado, CISD M1, POI actual, valor de volatilidad, spread, distancia al target, ni edad H1/rango parcial. La propia formación del setup de M15/M1 condiciona la selección observada y puede estar correlacionada con reversión.
- Aunque B2 controla tercio horario H1, no controla todos los componentes anteriores. B1 selecciona episodios que sabemos que generaron oportunidades V49, por lo que representa un benchmark **condicional a las tesis seleccionadas**, no la habilidad del sesgo en todos los estados H1 del mercado.
- Una fracción de cierres de precio positivos no es un PF, ni prueba que se hubiera podido ejecutar un stop estructural y un target HTF de forma rentable en esas velas elegidas al azar.
- La misma direccionalidad negativa en 9 mercados + bootstrap de 313 dates es evidencia de **problema transversal de timing/estructura en la IMPLEMENTACIÓN ACTUAL**, no una justificación para invertir automáticamente H1, eliminar Sweep, descartar M1 o fijar edad H1 arbitraria.

### 6. Paso siguiente estrictamente permitido

1. Congelar 9/9 baseline fuente `c654a... `, su resultado y semilla. No cambiar el replay original.
2. Auditar en código y con ejemplos originales el **emparejamiento H1 C2/C3 closure → protected M15 CISD → timing de M1**, comenzando por *cómo el POI se conserva/reutiliza* y por si el momento de confirmar el swing obliga a entrar tras el impulso. No sustituir ese análisis por un hard noise gate.
3. Contestar contradicción de fuentes C3 antes de modificar detector. Casos de carácter exactos en `tests/infrastructure/trader_lab/test_capitalizer_scalper_h1_c2_c3_primary_source_characterization_v1.py`, que identifican interpretación diciembre `inside-range body` y enero `beyond body/range` como `SOURCE_AMBIGUITY`. No asumir que la implementación actual es errónea por un único texto; tampoco declarar C3 fuente-fiel sin resolver conflicto.
4. Pedir a arquitecto A1 la auditoría transversal del Master Frame COGNITIVO, con H1 y M15 as-of, no `h1_state_until` futuro ni outcomes que el trader no sabía, y **sin introducir A1 como optimizador del mismo holdout**.
5. Próximo ensayo causal debe preregistrar UNA intervención sobre señal M15/M1 y comparar por **los mismos IDs y el periodo OOS independiente**; n≥500 NO sustituye criterios de conservación ≥934 winners/415.75R originales, PF OOS ≥1.5 y DD≤6R, broker costs físicos, prueba de estrés 9 mercados y estabilidad.

**Veredicto sexta ronda**: H1 no queda demostrado como inútil; la implementación del **timing M15/M1 necesita revisión prioritaria**. La dirección H1 es condicionalmente más favorable a tiempos random en los mismos estados, pero NO representa estrategia rentable por sí sola. NO CERTIFICADO; NO VPS/LIVE/MERGE.
