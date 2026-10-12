# QORE Native — Decisión arquitectónica NO-NEWS / estado de hipótesis y nuevo espacio viable

**2026-10-11 · GOVERNANCE ONLY · rama de investigación.** Motivo: auditoría externa y restricción de riesgo expresada para QORE; énfasis en NO exponer nuevos traders de QORE Native a shocks macro programados. **No activa filtros en producción ni modifica CIBO, Shared, VPS, MT5, QDLE o Traders existentes**. Requerirá aprobación específica para adoptar cualquier política de ejecución en el sistema general.

## 1. EVENT-MACRO: CIERRE POR POLÍTICA, NO FALSACIÓN

- Evidencia G0: 119 CPI con encabezados oficiales contrastados, 113 ventanas NAS100/USTEC de 71/71 timestamps M1 completos, fecha y horario BLS [PR #807](https://github.com/mezas3238-hue/qore-core/pull/807), [PR #810](https://github.com/mezas3238-hue/qore-core/pull/810).
- Pre-G1: no se verificó consenso CPI PIT, coste ejecutable durante CPI, primer fill ni varianza del estimando, y no se midió PnL del modelo [PR #813](https://github.com/mezas3238-hue/qore-core/pull/813). El estudio PRE-G1 queda documentalmente `BLOCKED_NOT_EVALUABLE_INFRASTRUCTURE`; ninguno de sus resultados autoriza trading.
- **Nueva decisión de diseño QORE Native**: `EVENT_MACRO_EXECUTION_CLOSED_BY_RISK_POLICY`. **NO ejecutar un G1 de sorpresa CPI/operativa durante anuncio**, ni contratar ahora TE/Bloomberg/coste-evento para ese propósito. No existe `CPI_NO_EDGE`, `CPI_UNTRADABLE_PROVEN`, ni `REJECTED_BY_BACKTEST`.
- Si más adelante cambia la política, debe abrirse **nueva revisión formal**, restaurar el contrato económico PIT/costes/potencia y contar los tests previos; nunca reutilizar las 113 fechas como OOS virgen. Mantener los 119 testimonios para **calendario de exclusión de riesgos**, no para predecir dirección.
- Dispersión de spread «20–50 pts», vol «3–5×» y «stop de 15 pts inevitable» son **supuestos no medidos** para NAS100 IC Markets; evitar registrarlos como dato probado. «Los costes destruyen todo» es demasiado fuerte. Opción: excluir por asimetría de riesgo aun cuando no podamos cuantificar ese régimen.

## 2. No operar noticias: contrato exclusivo para nuevos traders Native en investigación

- Intención: los traders nuevos no deben **abrir ni mantener exposición direccional sin control a través de comunicados de alto impacto** relevantes a sus factores (USD, inflación, empleo, tipos, bancos centrales). Otros miembros de Core no cambian su política por este documento.
- **Candidato de exclusión PRE-REGISTRO** para ensayos exploratorios: no abrir desde **30 min antes** hasta **60 min después** de un comunicado listado como alto impacto y verificable con fuente as-of; política provisional, NO regla live certificada. Una posición anterior no debe cruzar el instante de un evento de alto impacto sin protocolo específico: diseño paper `EXIT_OR_ABSTAIN_PRE_EVENT` con cutoff de seguridad aún por fijar. **No inventar que el cierre se realiza a mid ni sin slippage**.
- Preservar metadatos históricos de calendario con distinción `KNOWN_ASOF / RETROSPECTIVELY_IDENTIFIED / UNSCHEDULED / UNKNOWN`; sin calendario as-of, no etiquetar retrospectivamente como «pre-evento conocido». Las sorpresas no programadas no pueden prevenirse con un calendario; deben gestionarse con un gobernador de riesgo independiente y circuit breakers, no prometer protección completa.
- Toda idea de cambiar la ventana de exclusión o aplicar política a live exige aprobación de ingeniería, controles de posición existente y simulación causal histórica antes de ejecutar.

## 3. Pre-RELATIVE: GATE económico y de operabilidad ANTES de explorar PnL

La [puerta de magnitud PR #806](https://github.com/mezas3238-hue/qore-core/pull/806) continúa vigente: para cartera relativa de dos piernas, ventaja bruta >=3× coste conservador RT de ambos legs, LCB95 delta >2 bps y LCB95 beneficio neto absoluto >0, más power/multiplicidad/OOS. **RELATIVE sigue en `ON_HOLD`** si faltan costes: no convertir una correlación en reversión ni abrir 3 parejas y seleccionar la mejor.

**Condiciones medibles propuestas**, que requieren fuente de costes compatible con broker, tamaño y slot de entrada:
1. `COST_PIT_VERIFIED`: BID/ASK o histórico spread del broker + comisión RT + deslizamiento prudente del **par exacto y ambas piernas** a la hora de ejecución; si fuente inexistente, solo `GROSS_DISCOVERY`, no `G1_NET_VALID`.
2. `STOP_SPREAD_SURVIVABILITY`: stop sobre precio **ejecutable** (lado BID/ASK correspondiente) y riesgo en R, no mid-OHLC. Exigir que el **coste conservador total roundtrip sea <=10% del riesgo monetario definido por stop** como guardrail inicial de cribado; no es garantía de supervivencia. También evaluar que una ampliación de spread P99 por hora (observada en datos históricos) no active stop *por sí sola*; sin spread P99 => `UNKNOWN`, no PASS. Evitar elegir ancho stop después de inspeccionar trades.
3. `NORMAL_REGIME_ASOF`: volatilidad solo de pasado (ej. ATR rolling hasta vela cerrada anterior), spread hora/sesión frente a distribución pasada y calendario macro disponible entonces. Para el cribado inicial **excluir volatilidad > percentil 90 del historial pasado** en la misma franja y símbolo (umbral provisional congelado ANTES de PnL; análisis de sesgo de selección obligatorio). Calibrar con **datos de desarrollo únicamente**, nunca con holdout/futuro; si no hay suficiente historial por reloj, `ABSTAIN`.
4. `ECONOMIC_MAGNITUDE`: expectativa plausible por mecanismo >=3× fricción del mismo nocional, suficiente N independiente para LCB neto y estabilidad régimen/activo; si la estimación de edge es inferida de los retornos OOS ya vistos, **NO** usar para abrir nueva familia como prereg.
5. `NO_NEWS_COMPLIANCE`: no ejecutar en los segmentos del blackout seleccionado para Native, ni operar posición abierta sin autorización de seguridad explícita.

**No afirmar que P90 volatilidad o RT<=10% stop sean leyes universales**. Son filtros de *cribado propuestos* que necesitarán reevaluación en papel y consistencia de unidades; no convertirlos en estrategia certificada ni ejecutable por sí solos.

## 4. Nueva investigación con 33 símbolos planeados: NO equiparar 33 a 33 verificados

**Contexto del propietario**: 12 activos ya presentes; **21 descargándose** desde cTrader IC Markets, todos para investigación. Total **33 planeados, no 33 archivos íntegros confirmados**. El universo no autoriza selección ex post del mejor activo ni una cuadrícula de parámetros indiscriminada.

**Puerta G0 de inventario antes de cualquier señal**:
- identidad símbolo canon/broker, ISIN/underlying cuando corresponda, CFD vs futuro; tick/contract, sesiones reales, calendario/roll/corporate actions, precio relativo vs absoluto, DST y calidad;
- M1/M5/M15/H1/D1 efectivamente presentes (no inferir que cada feed incluye todas), hashes de original, rango y faltantes, huecos sistemáticos, duplicate/out-of-order, festivos/mercado cerrado; bifurcar original/download/en validación/fail;
- riesgo de múltiple test: declarar tamaño total universe y registrar **todas** familias, mercados, relojes, variantes y resultados, incluyendo datos ya consumidos vs OOS sellado;
- test de potencia para cada **mecanismo prediseñado**, sin extrapolar unidad observacional «millones velas» al N efectivo.

**Orden propuesto** (no es orden económico optimizado tras resultados):
1. **G0 universo 33**, sin outcomes de PnL ni selección por rendimiento.
2. **Mecanismos de varias horas a varios días** en horario normal, una familia ex ante a la vez: persistencia por régimen (H4/D1, tendencia temporal), tendencia relativa entre sectores/índices con cobertura de exposición, reversiones de mercado tras shocks NO programados solo si ocurren bajo política de exclusión y gobierno de riesgo, y ciclos intradiarios sin ventanas de noticias; ningún mecanismo es ya un edge probado.
3. RELATIVE solo si su modelo económico **de dos legs** pasa filtros de fricción y materialidad ex ante; no forzar la «tercera plaza».
4. **Evaluación de futuros** como estudio de infraestructura separado: comparar NAS100 CFD contra **MNQ/NQ futuros equivalentes** solo con datos licenciados, brokers, comisiones, horquilla bid/ask medida, profundidad, impacto, márgenes y expi/roll. CME confirma **MES tick 0,25 índice = $1,25, MNQ tick 0,25 índice = $0,50, ES tick 0,25 índice = $12,50**; *tick-size ≠ spread ejecutado ≠ coste roundtrip*. **NO** afirmar «ES 0,25 pts = 1,25 bps»: tick-bps = `(0,25 / precio_ES_actual) × 10000`, depende de cotización; ni asumir futures=5× más baratos o compatibles con las cuentas MT5/CFD.

## 5. Preservar honestidad de falsación y regla de parada

- RESET G1 M5 delta −0,692bps e IC cero; RESET G2 M1 delta −0,521bps, mismo mecanismo/fechas (NO independientes). DRIVE G1 NAS100 +0,587bps CI cruza cero. **Estas implementaciones no demostraron ventaja bruta fiable.** No se probó que tuvieran *edge positivo que se pierde por costes*; tampoco se probó que **todo** intradía carezca de oportunidades.
- Macro CPI G0/G0B no son ensayos económicos: fueron operaciones de fuentes/metadata. No contarlos como cuatro o seis estrategias «fallidas».
- Dar salida `NO_SUPPORT_SPECIFIC_PREDECLARED_HYPOTHESIS`, `NO_EVALUABLE_SOURCE/COST`, `INCONCLUSIVE_UNDERPOWERED`, `STOP_BY_PORTFOLIO_RISK_POLICY` o `CERTIFIABLE_CANDIDATE` según evidencia, sin confundir clases.
- Si el inventario G0, la cobertura de fricción y potencia no permiten hallar **ninguna** hipótesis identificable con margen económico, dictamen `INFRASTRUCTURE_UNSUITABLE_AT_CURRENT_COSTS`, **no** inventar tres sistemas rentables ni declarar mercados globalmente sin edge.
- P0 aprobado aquí: cambiar **dirección del programa Native en Github research**; ninguna orden, no software de live, nada con Shared/CIBO ni VPS, no cierre de PR históricos que resguarden evidencia. Evento G0C-G0D pasa a `DEFERRED_CLOSED_BY_RISK_POLICY`, sin borrar los artefactos previos.

## 6. Próxima misión verificable

Inventariar exactos 12 existentes y estado de 21 descargándose; **no afirmar 33/33 completo** sin fuente/sha. Al conocer cobertura abrir un único prereg de fenómeno de H4/D1 con hipótesis causal, control, magnitud económica estimable, σ/potencia, fechas de conocimiento, y 1 universo/símbolo predefinido. 0 traders certificados, ninguna modificación en producción por este documento.
