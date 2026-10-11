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
