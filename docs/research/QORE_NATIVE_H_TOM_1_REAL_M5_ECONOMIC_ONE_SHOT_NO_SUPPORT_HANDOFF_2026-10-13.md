# QORE CORE — H-TOM-1: ÚNICO EXAMEN ECONÓMICO CON M5 REAL — NO_SUPPORT

**Checkpoint local:** 13-Oct-2026 Paraguay; ejecución GitHub Actions 14-Oct-2026 UTC.
**Repositorio soberano:** `mezas3238-hue/qore-core`.
**PR:** [#923](https://github.com/mezas3238-hue/qore-core/pull/923), DRAFT / NO MERGE.
**Branch:** `research/qore-native-tom-index-single-exam-20261013`.
**Prereg científico (ANTES de códigos con resultados):** commit `358d2d0e9691a95bbd9c121ea62b0075c2182975`; documento `docs/research/QORE_NATIVE_US_INDEX_TOM_H1_SINGLE_ECONOMIC_GROSS_PREREG_2026-10-13.md`.
**Rama fuente madre:** `research/qore-native-master-handoff-g1-33-sources-addendum-20261012` / PR #855.
**Economía NET no verificada, NO LIVE/DEMO/capital real/VPS/MERGE.**

## 1. Hipótesis causal económica única — no más censos

**H-TOM-1:** flujos institucionales/carteras y aportaciones/rebalanceos obligatorios de cambio de mes impulsan precios de los índices US lo suficiente para que comprar antes de fin de mes y vender en la tercera sesión del mes entrante genere **retorno bruto superior** a una ventana igual de sesiones de mitad de mes.

**Literatura documentada contradictoria antes del resultado:** Laura Han, Yufeng Han y Shirley Tian, Finance Research Letters (2025), *The disappearing turn-of-month effect*, DOI `10.1016/j.frl.2024.106461`, argumenta desaparición desde 2001; artículo Journal of International Financial Markets, Institutions and Money, vol. 109, junio 2026, DOI `10.1016/j.intfin.2026.102309`, describe efecto contemporáneo en 30 países asociado a rebalances poco frecuentes y diferimiento de riesgo. No acreditar esto como rentabilidad CFD.

**Línea distinta** de CFTC, FX carry, RESET London fix y NAS100 cash-open, y no un sweep de horario, ICT, Turtle ni optimización de velas.

## 2. Diseño congelado antes de los outcomes

- Tres índices G0 existentes; **SP500 (proveedor US500) PRIMARY**, US30 y NAS100 (USTEC) replicadores fijos. Histórico 2016–2026 original CIBO Atlas cTrader DEMO, fuente run `35166210458` con SHA de archivos originales anuales y fuente agregada `47f5763d7ea2c10dd32fa40a84d7480c8124f1a512b623c1299ef2ba7b8c51c2`. Confirmados todos los años (11 particiones) por cada índice **antes de computar el efecto**.
- `America/New_York` IANA DST, sesión cash 09:30–15:55; mínimo 60 velas de 78 por día, apertura de vela 15:55 NY como precio de referencia, no orden real.
- Para cada mes: último día de sesión cash anterior (entrada) -> tercera sesión del mes (salida); control **10ª→13ª sesión** del mismo mes. Ambos movimientos separan tres sesiones. 1 evento emparejado por mes y mercado, sin selección retrospectiva de activos, días u hora.
- **DEV noviembre 2016 a agosto 2022, DIAG octubre 2022 a agosto 2024**; septiembre 2022 fuera de las dos poblaciones, aunque su final cash puede ser entrada calendárica de octubre. **Desde 17-sept-2024 todas las filas OHLC ignoradas**, sin evaluar retornos; originales 2016–2024 de QORE Native ya se usaron antes y NO son OOS nuevo.
- Min 40 meses DEV y 16 DIAG por mercado. Principal SP500 en AMBOS períodos: `mean(TOM_gross)>15bps`, `mean(TOM−control)>15bps`, `bootstrap_unilateral_95%_inferior(excess)>0`, bootstrap circular de 3 meses, 4000 draws, seed 20261013. US30 y NAS100 como réplicas: exceso medio >5 bps en ambos períodos. Todos los criterios fijados ex ante, sin umbral cambiado tras resultado.
- Estrés **ilustrativo** RT 5/10/20bps no es costo de intermediario medido. No se calculan profit factor, Sharpe, Sortino, max drawdown NET, precio Ask/Bid, comisión, swap ni deslizamiento.

## 3. Resultado ECONÓMICO VERIFICADO, no solo CI

[**GitHub Actions #38502188181 SUCCESS**](https://github.com/mezas3238-hue/qore-core/actions/runs/38502188181), commit de código probado `be77998d185165ff0d2cce320d015981c8a8c631`. Prereg ancestry y blob comparado en Git; **10/10 controles sintéticos PASS**, Ruff subset F/E PASS, los **tres jobs de índices PASS**, un único agregador PASS.

**[Artefacto final #11866267480](https://github.com/mezas3238-hue/qore-core/actions/runs/38502188181/artifacts/11866267480)**, ZIP SHA256 `2beb1a1d43084eb3b2fbe4caf7693f05eff423452c14ec8e30e78fdcdfc99986`; recibo lógico `447550d70c6c75a37ff6adb3831cfc23bfb56ab3a7eba15e6c896a3f031a87e1`.

| Índice | Ventana | Meses | TOM gross mean bps | Control gross mean bps | Delta paired bps | Bootstrap lower 95% delta bps | Dictamen de la celda |
|---|---|---:|---:|---:|---:|---:|---|
| **SP500 PRIMARY** | DEV | 70 | **+50.99** | +4.44 | **+46.55** | **−9.90** | NO_SUPPORT |
| **SP500 PRIMARY** | DIAG | 23 | **−3.09** | −15.07 | **+11.98** | **−57.57** | NO_SUPPORT |
| US30 | DEV | 70 | **+54.36** | −7.21 | **+61.57** | **+4.31** | PRELIMINARY_SUPPORT replicate threshold |
| US30 | DIAG | 23 | **−11.95** | +0.42 | **−12.37** | **−71.72** | NO_SUPPORT |
| NAS100 | DEV | 70 | **+50.73** | +15.37 | **+35.36** | **−30.65** | PRELIMINARY_SUPPORT replicate threshold only |
| NAS100 | DIAG | 23 | **−0.22** | −14.87 | **+14.65** | **−93.78** | PRELIMINARY_SUPPORT replicate threshold only |

Notas:
- El **NAS100 se marca preliminary support en réplicas** porque su criterio prereg era **solo delta media >+5bps**, NO porque tuviera un intervalo de confianza favorable (ninguna de sus dos ventanas lo tiene). Nunca tratarlo como fuente individual validada de edge.
- Al primary SP500 le falla CI inferior incluso en DEV; en DIAG cae TOM gross por debajo de cero, por lo que no cumple señal neta simple aun antes de costes.
- US30 muestra reversión del signo de excess en DIAG, de manera que falla la condición de replicación.
- Las tres series de índices son correlacionadas: **93 meses de oportunidades por instrumento, no 279 experimentos independientes**.
- El origen de index CFD difiere de CME nativo, y falta contrato histórico VERIFIED EXACT para trading; el precio RTH M5 15:55 OPEN es un benchmark indicativo. El protocolo no incluye un calendario NYSE PIT independiente: última sesión mensual inferida de datos M5, no validación definitiva de decisión desplegable.

**DICTAMEN CONJUNTO:** `NO_SUPPORT_UNDER_PREREG`.
**Orden de cierre:** `CLOSE_H_TOM_1_NO_PARAMETER_SEARCH`.
**Gates:** `EDGE_CERTIFIED_FALSE`, `CERTIFIED_TRADERS_0`, `NO_NET_HISTORICAL`, `NO_OOS_2024_09_17_PLUS`, `PRODUCTION_UNTOUCHED`.

## 4. Qué SÍ se hizo y qué no

**Hecho:** se pasó de censo a hipótesis económica falsable, se formuló comparador de retorno contemporáneo y criterio binario, se preregistró en Git antes de resultados, se auditaron de nuevo fuentes M5 SHA de tres índices, se calcularon outcomes 70+23 meses c/u y robustez por bloques, se probó costo bruto hipotético, se cerró correctamente al fallar SP500 y US30. Costo de datos nuevo = USD0.

**No hecho:** no se ha demostrado edge, ningún test usa BID/ASK y swap reales de cada posición, no puede llamarse profit neto ni certificación; no se abrió holdout 2024-09-17+. El mero hecho de que CI sea GREEN no cambia adjudicación NO_SUPPORT.

## 5. Lo que sigue: STOP, no nueva cadena

El owner indicó un último examen económico antes de revisar el método. Se cumplió: **H-TOM-1 es el examen económico concreto** y su respuesta bajo reglas fijas es NO_SUPPORT. No hacer TOM sobre solo NAS100, no cambiar SP500 por US30, no seleccionar el trimestre favorecido, no reducir bootstrap/p/umbral ni buscar otras duraciones/días tras ver el resultado. No crear H-TOM-2 de rescate con mismo panel.

**Conclusión estratégica:** con recursos actuales QORE puede ejecutar tests económicos exploratorios causales, pero la combinación de dataset previamente explorado, variación temporal y falta de datos ejecutables NET continúa impidiendo demostrar una ventaja nueva. Recomiendo revisar formalmente **el proceso de descubrimiento de alpha y la calidad real de ejecución disponible** antes de autorizar otra familia de trading. No significa incapacidad universal del mercado; sí insuficiencia de evidencia para certificar otro trader. Proteger M5 y source manifests como activos de investigación.

**No merge, NO LIVE, no dinero; la PR permanece DRAFT.** Este informe se escribió DESPUÉS del resultado y no modifica prereg ni reglas.
