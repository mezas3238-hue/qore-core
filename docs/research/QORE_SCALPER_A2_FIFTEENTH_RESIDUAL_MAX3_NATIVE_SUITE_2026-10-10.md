# QORE Scalper — Decimoquinta auditoría, suite residual sobre 1.997 MAX3

**Repositorio**: mezas3238-hue/qore-core, branch agent/scalper-architect-b-methodology-20261010, PR #759 DRAFT. **Permisos**: GitHub-only / investigación, 0 nuevos vetos, 0 modificación de baseline, 0 cambios del World Model, 0 VPS/MT5/live.

## 1. Universo y control congelados antes de diagnósticos

- Fuente original nueve mercados, 2025-09-17 a 2026-09-17: **2.876 oportunidades**.
- Baseline económico V49 reconstruido al 100% desde M1 nativo: **2.020 MAX3**, PF bruto **0,664463**, DD **236,134284R**, neto **−233,269327R**.
- Alternativa experimental primera señal M1 online, parent H1/M15 todavía V49: **2.816 elegibles**, **1.997 MAX3**, PF bruto **0,842524**, DD **114,799099R**, neto **−109,055389R**. Siguió siendo **perdedora** incluso antes de BID/ASK/comisiones; no certificar.
- Entrada diferente **1.090/2.876**, de las cuales el subgrupo viejo **381** representa solo snapshot al cierre V49. Universo no regenerado en streaming H1/M15.
- Retención original **1.137/1.167 ganadores**, **449,711269R** de masa ORIGINAL 461,942762R. No confundir masa original con retorno realizado por variante.
- Reglas NO optimizables en esta ronda: H1 direction y POI QORE congelados, stop estructural M15, target H1 seleccionado as-of, STOP_FIRST, cierre de sesión, MAX3. No expandir World Model y no usar outcome para selección.

## 2. Cohortes forenses completadas — GH Actions #38104619725 SUCCESS

**Script**: capitalizer_scalper_a2_fifteenth_residual_anatomy_v1.py. ID preservado entre V49 y alternativa. Etiquetas de familia/mercado/sesión son características de fuente o selección online, NO justifican filtrar retrospectivamente.

| Grupo | Asia | Londres | Nueva York | Total |
|---|---:|---:|---:|---:|
| Incompatible nuevo SL M15 | 13 | 11 | 12 | **36** |
| Objetivo H1 no disponible delante | 8 | 4 | 12 | **24** |
| MAX3 original pierde identidad | 28 | 17 | 28 | **73** |
| MAX3 nuevo incorpora identidad | 22 | 6 | 22 | **50** |
| Ganadora original preservada se convierte en perdedora | 9 | 9 | 14 | **32** |

- 60/60 fuentes inviables tienen decisión online distinta al V49 original. Los 36 stops inviables se reparten entre 30 primeras rutas Sweep+CISD y 6 FVG+CISD. Los 24 objetivos faltantes se reparten entre 19 FVG+CISD y 5 Sweep+CISD.
- 73 salen y 50 entran, dejando 1.947 operaciones con misma identidad entre 2.020/1.997. De las 50 nuevas, 32 entran como Sweep y 18 FVG.
- Las 32 ganadoras convertidas a perdedoras entraron ANTES que V49; mediana de adelanto 33 min; M15 protected stop nunca cambió, objetivo H1 cambió en 20. Salida TARGET→STOP 25, TARGET→SESSION_EXIT 4, SESSION_EXIT→STOP 2, SESSION_EXIT→SESSION_EXIT 1. Fuente: el motor cambia tiempo de exposición a SL, no solo etiqueta direccional.
- Desagregación PF bruto original vs online según trigger family: Sweep 0,592391→0,853120; FVG 0,747983→0,823623. NO comparación causal manteniendo las mismas identidades, porque familias y MAX3 se reordenan. No autorizar veto ni ponderación.
- Media de ganancia por winning trade: **0,395838R → 0,505603R**; media de magnitud perdida: **0,815977R → 0,823449R**. Mediana R objetivo planificado **0,442623 → 0,537037**; objetivos previstos ≥1R: **451→549**; objetivos <0,5R: **1.104→935**. Estas son descripciones, no prueba de que solo el timing explique la mejora: precio de target nuevo y composición MAX3 también cambian.

**Cierre matemático**: PF0,8425 con n1997 no satisface PF>1 bruto. No transformar una estimación del win rate de break-even en una garantía de mejora; cambiar 84 resultados altera trayectorias, no preserva distribución de wins/losses ni costos. No tocar reglas por estos valores.

## 3. Reejecución nativa de los diagnósticos históricos sobre MAX3

**Código**: capitalizer_scalper_a2_fifteenth_native_forensics_v1.py, test homónimo, GH workflow qore-scalper-a2-fifteenth-native-reaudit-nine-market.yml.

**Entradas selladas**: source V49 GH #38053946695, native M1 GH #35548099334, alternativa GH #38102352779, selección 1997/2020 por ID GH #38104905157 (idéntico libro económico, manifest explícito 1.997). Cada símbolo observa los M1 exactos de la fuente; no hay BID/ASK ni interpolación.

Pre-registro de métricas de investigación:

1. **MFE/MAE**: reconstruir M1 de TODAS las operaciones verdaderamente seleccionadas (V49 2020 vs online 1997), distinguir máxima excursión previa a vela de cierre (causalidad OHLC sin orden intrabar), excursión con última vela como cota, MFE ≥0,5R y ≥1R para operaciones perdedoras; comparar distribución y no solo media.
2. **H1 aleatorio**: para cada una de las 1997 decisiones online, seleccionar uniformemente 32 instantes M1 del mismo estado H1/sesión original (o mismo tercio de 20min) con semilla fija por source ID; NO usar futuro `h1_state_until`, ni conocer outcomes para escoger. Comparar únicamente signo del CLOSE+15/30/60 de posición original frente a los nulos aleatorios. Una etiqueta favorable no es un trade ni PF.
3. **Sweep/FVG→CISD**: reconstruir sobre el nuevo instante online el primer sweep o FVG nativo y el cierre CISD de cada fuente seleccionada, calcular favorable 15/30/60 de ambos momentos con pares por ID; los casos sin recibo estructural se reportan como NO COVERED, nunca se sustituyen por una confirmación retrospectiva V49. Esto recalcula el fenómeno de caída 12,56pp si la cobertura es suficiente.
4. **Stop/target**: la geometría de STOP M15 se conserva tal como quedó materializada en el replay bruto; se ha vuelto a medir mediana de target R, win/loss/STOP/SESSION_EXIT y objetivo >=1R. Un factorial M1-stop/ruido 2x2 requiere replay experimental aislado sin elegir arm por PnL. El código histórico que sirve como fuente es capitalizer_scalper_stop_noise_factorial_v1.py y puede reejecutarse sobre la selección 1997 si se mantiene fijo el tiempo/target y se etiquetan faltantes.
5. **Familias y mercados**: todos los anteriores se reportan sin filtros, con n exacto y coverage, para no presentar un sesgo de supervivencia o etiquetar mejora económica positiva como rentable.

**Estado**: MFE/MAE, aleatorio H1 y etapa Sweep/CISD son experimentos de nueva run; no escribir métricas inventadas hasta que el workflow complete 11/11. Cada limitación documentada NO CERTIFICABLE. Fuente POI HTF de TTrades, 504 H1 sin testigo 60/60 y el swing M15 siguen sujetos a certificación independiente.

---

## 4. Resultados del recálculo sobre MAX3 real, [GitHub Actions #38104940494 SUCCESS 11/11](https://github.com/mezas3238-hue/qore-core/actions/runs/38104940494)

**Conciliación**: 9 mercados, 2020 V49, 1997 causal-first (ninguna operación sintética nueva), y 1997/1997 recibos causales de etapa CISD reconstruidos desde M1 nativo. Las etiquetas MFE/MAE y +H son EX-POST, no decisiones.

### MFE/MAE desde entrada hasta vela previa al cierre

| Métrica R o N | V49 n2020 | Causal-first n1997 |
|---|---:|---:|
| MFE media preterminal | **0.3436439303R** | **0.4492380416R** |
| MAE media preterminal | 0.4655322672R | 0.4739126085R |
| MFE media de ganadoras | 0.3692437538R | 0.4792047209R |
| MFE media de perdedoras | 0.3079751033R | 0.4084761432R |
| Perdedores con MFE preterminal >=0.5R | 138 | **189** |
| Perdedores con MFE preterminal >=1R | 39 | **59** |
| Media neta realizada por trade | -0.1154798649R | -0.0546096091R |

La MFE tiene mayor recorrido favorable, pero el mayor número de perdedoras que ANTES mostraron +0.5/+1R demuestra que retorno disponible ex-post no garantiza salida capturable. MFE/MAE terminal incluían máximos y mínimos intrabar de última vela solo como **cotas**, no se infiere orden secuencial real de hits; 3 casos de empate stop/target STOP-FIRST en ambos libros.

### Nulo temporal H1 mismo estado (sin H1.until futuro)

Para cada trade causal-first elegido realmente MAX3 se compara precio firmado CLOSE+H con **32 muestras deterministas por ID** de instantes M1 permitidos por el mismo estado H1/sesión, antes de conocer cada outcome. Dos nulos: instantes uniformes y mismo tercio de 20 min del reloj. No son fills ni arriesgan dinero; los denominadores son observaciones con cobertura completa y no 1997*32 necesariamente.

| H | Causal-first favorable | H1 nulo uniforme favorable | H1 nulo tercio de 20 min |
|---|---:|---:|---:|
| +15m | 942/1961 = **48.04%** | 33208/62565 = **53.08%** | 33234/62671 = 53.03% |
| +30m | 894/1909 = **46.83%** | 33432/61136 = **54.68%** | 34661/61258 = 56.58% |
| +60m | 878/1815 = **48.37%** | 33520/58113 = **57.68%** | 34217/58115 = 58.88% |

El nulo H1 supera al selector causal-first todavía, **no** es un nulo de rentabilidad y está condicionado a selección fuente V49 de su estado H1. No usar su ventaja para colocar trades al azar ni aprobar un filtro optimizado.

### Punto de destrucción de Sweep/FVG hacia CISD (nuevo dataset, NO V49)

No se interpolaron precios, ni se aceptó un stage faltante. Para cada source-ID se mide POSITIVO de CLOSE+H del bar de barrido/FVG inicial y del bar final CISD, y se empareja sólo si ambos horizontes están completos. **1997 de 1997** entradas online tienen etapa reconstruida.

| Familia | H | Emparejados | Stage temprano positivos | CISD positivos | CISD - temprano |
|---|---:|---:|---:|---:|---:|
| Sweep+CISD | 15 | 1096 | 670 | 520 | **-13.6861pp** |
| Sweep+CISD | 30 | 1068 | 623 | 506 | **-10.9551pp** |
| Sweep+CISD | 60 | 1017 | 563 | 486 | **-7.5713pp** |
| FVG+CISD | 15 | 864 | 445 | 422 | **-2.6620pp** |
| FVG+CISD | 30 | 840 | 422 | 388 | **-4.0476pp** |
| FVG+CISD | 60 | 797 | 406 | 392 | **-1.7566pp** |

La degradación Sweep sigue siendo material tras corregir la primera selección (comparar con fenómeno histórico de ~12.56 pp sin asumir mismo n); el grupo FVG tiene degradación menor. Esto NO demuestra que entrar prematuramente en un sweep sea causalmente ejecutable ni que un nuevo stop/target con coste real sobreviva. Debe evitarse optimización post-outcome de entrada temprana.

### Diagnóstico residual y condiciones de paso

- **PF0.8425 y -109.055R BRUTO**; no rentable/certificable, tampoco BID/ASK físico. Las dos familias contribuyen; la ganancia media aumentó por timing+target+composición.
- No se puede afirmar que el problema de los stops haya desaparecido: stop original M15 conserva riesgo -1R al hit, y hay 189 perdedoras que antes tuvieron excursion >=0.5R. Hace falta factorial stop M15/M1 sin hard-veto nuevo.
- La generación H1/M15 original y el POI autor siguen condicionando el universo 2876; no reconstruir fuera de esas fuentes hasta tener suite completa. World Model congelado.

---

## 5. Factorial stop M15/M1 + ruido 2×2 fijo — [GH Actions #38105126886 SUCCESS 11/11](https://github.com/mezas3238-hue/qore-core/actions/runs/38105126886)

**Protocolo:** 1997 source IDs inmutables ya seleccionadas por causal-first MAX3. No modificar entrada, familia, H1 objetivo, sesión, ni cronología MAX3. Stop original M15, o STOP M1 de pivote causal as-of detectado por `analyze_source_geometry` existente. Los brazos con ruido exigen condición PRESPECIFICADA 4–8× respecto al rango local M1 de V50-G; no optimizar parámetros ni elegir el brazo por PF. Todos los resultados son BRUTOS, sin BID/ASK o comisiones, y los subconjuntos con menor cobertura no son carteras reconstituidas.

| Brazo fijo | N con stop y ruido disponible | PF bruto | R bruto | N fuera de cobertura de las 1997 |
|---|---:|---:|---:|---:|
| M15_NOISE_OFF | **1997** | 0.842524 | -109.055389R | 0 |
| M1_NOISE_OFF | **1778** | 0.914294 | -99.363079R | 219 |
| M15_NOISE_VETO | **52** | 1.180295 | +1.845016R | **1945** |
| M1_NOISE_VETO | **52** | 1.786036 | +11.831383R | **1945** |

El pivote M1 estructural está disponible para **1778/1997**, falta testigo para 219, y la condición 4–8× se cumple en 52. Aunque el M1 no-veto mejora el PF vs stop M15, **sigue debajo de 1** y aún registra casi -100R en este subconjunto. Los 52 con condición 4–8× exhiben PF>1 en el development, pero un veto que excluye **97,4% de operaciones** destruye densidad y carece de nueva selección MAX3, de costes y OOS. **No se autoriza integrarlo como filtro/stop en CORE**. Son resultados de investigación, no modelo certificado.

Especialmente, no comparar PF de 52 oportunidades con PF de 1997 como si fueran universos equivalentes o asumir que los 52 conservarían desempeño en producción. El código, su test y el workflow son:
- `capitalizer_scalper_a2_fifteenth_online_stop_factorial_v1.py`;
- `test_capitalizer_scalper_a2_fifteenth_online_stop_factorial_v1.py`;
- `qore-scalper-a2-fifteenth-online-stop-factorial.yml`.

### Veredicto final de auditoría XV

1. Las diferencias 60/73/50/32 y mejor target R quedan **CLASSIFIED**, no filtradas.
2. La reejecución de la suite H1 RANDOM + MFE/MAE + Sweep/FVG→CISD en n1997 queda **MEASURED**. **El problema Sweep→CISD sigue (-13.69pp a 15min), y el signo de retorno online sigue inferior al H1 RANDOM uniform** a 15/30/60.
3. La ablation stops 2×2 queda **MEASURED pero no ejecutable como regla**: 1778 n pivote con PF0.914 y 52 en 4–8× PF>1 sin densidad ni OOS.
4. Faltan: regeneración COMPLETA y no anclada de H1/M15/M1 desde datos causales, fidelidad HTF POI y swing M15 al autor, monitorización de integridad 504 H1 con cobertura parcial, y ensayo financiero físico BID/ASK cuando la variante amplia supere PF bruto 1 antes de costes.
5. **NO CERTIFICABLE**, World Model congelado, V49 original intacto y ningún veto nuevo, PR #759 DRAFT, no MT5/VPS/LIVE.

**NOTA**: no diseñar retroactivamente el próximo ensayo para rescatar PF 0.843 con el umbral 4–8× ya visto en development; se requeriría justificación fuente previa y datos de validación independientes.
