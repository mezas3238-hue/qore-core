# HANDOFF MAESTRO — QORE NATIVE: TRES TRADERS PROPIETARIOS
## Visión, estado verificable, trabajo completado, riesgos y órdenes de investigación para el siguiente arquitecto

**Corte de información:** 2026-10-11. **Repositorio:** [mezas3238-hue/qore-core](https://github.com/mezas3238-hue/qore-core). **Issue director:** [#789](https://github.com/mezas3238-hue/qore-core/issues/789). **Rama independiente de traspaso:** research/qore-native-three-traders-master-handoff-20261011. **Estado científico:** G0 FUENTE M1 EJECUTADO; G1–G6 POR HACER; **0/3 traders certificados**, **0/3 engines de entrada creados**, **0 PF/Sharpe/Sortino demostrados**, **NO LIVE / NO VPS / NO MT5**.

> **MISIÓN DEL SIGUIENTE ARQUITECTO:** investigar, desarrollar, falsar y —solo si la evidencia lo justifica— certificar HASTA TRES metodologías DE QORE, nativas, diferentes y robustas. Debe descubrir **fuentes de ventaja de mercado**, no copiar señales de TTrades/ICT, dividir un mismo indicador en tres marcas, ni crear una cognitiva espectacular alrededor de una esperanza negativa. El resultado científico 0, 1, 2 o 3 metodologías certificables es legítimo. Cada paso debe realizarse y documentarse **en GitHub/Trader Lab**, con código, test, Actions, hashes, resultados negativos y estado de bloqueo. No delegar creando únicamente issues ni afirmar pruebas que no se ejecutaron.

---

## 1. VISIÓN DEL PRODUCTO FINAL: ¿QUÉ QUEREMOS CONSTRUIR?

### 1.1 Ecosistema Core con tres especialistas verdaderamente independientes

El objetivo **NO** es tres traders que "acierten mucho"; es un **portafolio de tres fuentes de retorno potencialmente complementarias**, sometidas a riesgos comunes que Shared y CIBO puedan controlar. Una ventaja debe ser **condicional, causal, neta de costes, reproducible y suficientemente robusta**. Un nombre, una arquitectura cognitiva, una media de PF sin control y un backtest de un año NO constituyen un edge.

- **QORE DRIVE (N1)**: busca **continuación** cuando el mercado incorpora información/flujo y un desplazamiento conocido antes de decidir presenta persistencia adicional. Especialista hipotético en mercados direccionales. NO confundir con barrido de Asia, CISD/MSS ni perseguir cada breakout.
- **QORE RESET (N2)**: busca **reversión** de presiones temporales de precio, con anclaje económico a ventanas/flujo verificables —por ejemplo ciertos fixings FX— en las que el desplazamiento observado puede deshacerse. NO confundir "cualquier high roto" con manipulación/edge.
- **QORE RELATIVE (N3)**: busca **reversión estadística de un residual** entre instrumentos con factores comunes, estimando beta solo de pasado y considerando ejecución de DOS piernas y exposición neta a monedas/factores. NO confundir correlación alta con cointegración o ventaja ni con SMT TTrades.

**Diversidad real, no cosmética:** DRIVE y RESET pueden acabar tomando riesgos similares durante volatilidad extrema; RELATIVE puede concentrar USD/JPY incluso con una cobertura aparente. Exigir correlación de pérdidas, exposición a factores, pérdidas simultáneas y contribución marginal de riesgo/rendimiento al portafolio Core. Si convergen hacia el mismo shock, limitar presupuesto común como una sola familia.

### 1.2 Qué debe tener CADA trader una vez certificado (diseño futuro, no estado actual)

1. **Identidad e hipótesis nativa versionada:** mecanismo económico, mercados/horas permitidos, qué comportamiento explota, baseline vencido, fuente de datos y fecha de aprobación.
2. **Sensores de mercado causales:** retornos/rangos/volatilidad/estados de sesión/residual propios calculados con información PREVIA o confirmada al instante; incertidumbre y procedencia. Prohibido "volumen institucional" inferido de OHLC sin datos de órdenes, velas futuras y pivotes ex-post.
3. **Cognitiva propia pero auditable:** interpreta contexto, decide **ENTRAR / ESPERAR / ABSTENERSE**, justifica evidencia concreta y puede gestionar salida dentro de límites **solo si** cada razón y estado pueden reconstruirse con el dato disponible. Un módulo ML o LLM debe fijar modelo/prompt/feature/version y prueba temporal; no dar permiso para inventar señales dinámicas en un backtest.
4. **Máquina de estados operativa:** DETECT → VALIDATE → WAIT_CONFIRMATION → SIGNAL → MANAGE → EXIT/INVALIDATE, con event_time/available_at UTC, precio de referencia, horizonte, invalidación y reason codes. No aceptar señales retrospectivas.
5. **Motor económico individual separado:** cálculo neto de costes, sizing propuesto dentro de contrato, exposición y límite de pérdida, calidad de fills/stop, comportamiento de simultaneidad, y explicación de oportunidad rechazada.
6. **Contratos de Core:** trader **propone** señal justificada; **Shared** verifica riesgos globales/integridad y puede vetar; **CIBO** decide presupuesto/asignación compuesta según cartera; **QDLE** resuelve restricciones de ejecución/fills. **No transferir soberanía de capital** al trader. Las capas cognitivas pueden agregar valor, pero no convierten una distribución sin edge en otra rentable por magia.
7. **Telemetría de certificación:** cada ejecución/abstención reproducible; expectativa neta, PF, Sharpe/Sortino sobre series compatibles, DD en R y %, frecuencia, exposición, drift, slippage, costes, defectos de dato, cambios de régimen, incidentes y versiones con trazabilidad GitHub.

### 1.3 Qué NO prometemos

No prometer 3 estrategias con ganancias, cierta tasa de acierto, ingresos mensuales ni manejo de cuentas enormes en esta fase. La robustez requiere evidencia cronológica independiente, resultados bajo condiciones adversas y capacidad de ejecución/calidad de riesgo; una IA avanzada no garantiza edge. El objetivo es **encontrar evidencia de mercado que permita construir lo anterior**, no agregar "cognitiva" a un indicador sin poder predictivo.

### 1.4 Roles de trabajo

- **Arquitecto ChatGPT**: diseña hipótesis y controles, escribe implementación, ejecuta GitHub Actions y valida artefactos, audita bugs/fuente/causalidad y reporta tanto fracasos como resultados alentadores.
- **DeepSeek Expert**: auditor externo adversarial cuando sea disponible por canal autorizado; formular y registrar preguntas concretas, someter datos, hipótesis, código y dudas, pedir críticas con razonamiento. No es fuente autoral ni árbitro de PF; **no afirmar que hubo consulta o acuerdo** sin evidencia en issue/comentario.
- **Mercado + datos no vistos + gates congelados**: único árbitro de rendimiento. La opinión coincidente de dos IA no equivale a validación OOS.
- **Shared / CIBO / QDLE**: etapas de integración posteriores a certificación y PAPER, sin tocar hoy sus códigos productivos ni importar decisiones a los descubrimientos.

---

## 2. MAPA EXACTO DE GITHUB: DÓNDE CONTINUAR

| Elemento | Enlace y responsabilidad |
|---|---|
| **Programa rector** | [Issue #789](https://github.com/mezas3238-hue/qore-core/issues/789): objetivo 3 candidatos; lectura inicial obligatoria |
| **DRIVE** | [Issue #792](https://github.com/mezas3238-hue/qore-core/issues/792): continuación causal; preregistro G1 pendiente |
| **RESET** | [Issue #793](https://github.com/mezas3238-hue/qore-core/issues/793): reversión de flujo; preregistro G1 pendiente |
| **RELATIVE** | [Issue #794](https://github.com/mezas3238-hue/qore-core/issues/794): residual entre pares; preregistro G1 pendiente |
| **Carta estratégica inicial** | [PR DRAFT #790](https://github.com/mezas3238-hue/qore-core/pull/790), [charter](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-three-traders-research-charter-20261011/docs/research/QORE_NATIVE_THREE_TRADERS_RESEARCH_CHARTER_2026-10-11.md). **Rama distinta de G0, NO asumir merge** |
| **Implementación G0 realmente ejecutada** | [PR DRAFT #791](https://github.com/mezas3238-hue/qore-core/pull/791), rama research/qore-native-g0-native-m1-coverage-20261011 |
| **Prerregistro G0 fechado antes de resultados** | [Prerregistro](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-g0-native-m1-coverage-20261011/docs/research/QORE_NATIVE_G0_M1_SOURCE_INTEGRITY_PREREG_2026-10-11.md), commit 1e14b4480c6f9f0e83563604282864004377300f |
| **Motor G0 independiente de señales** | [Código Python](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-g0-native-m1-coverage-20261011/src/qore/infrastructure/trader_lab/qore_native_g0_m1_integrity_v1.py) |
| **Tests G0** | [Tests](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-g0-native-m1-coverage-20261011/tests/infrastructure/trader_lab/test_qore_native_g0_m1_integrity_v1.py) |
| **CI G0** | [Workflow](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-g0-native-m1-coverage-20261011/.github/workflows/qore-native-g0-nine-market-m1-source-audit.yml) |
| **Ejecución definitiva G0** | [GitHub Actions #38166675573 — SUCCESS, 11/11 jobs](https://github.com/mezas3238-hue/qore-core/actions/runs/38166675573), código ejecutado commit fb22970798a2bd93f097f1327ce9c864eec0bb9c |
| **Resultados fuente G0** | [JSON agregado, artifact #11712187623](https://github.com/mezas3238-hue/qore-core/actions/runs/38166675573/artifacts/11712187623) más nueve artefactos individuales por mercado en run; **artefactos con retención 90 días**, prever conservación autorizada antes de expirar |
| **Informe G0 verificado** | [Auditoría G0, informe completo](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-g0-native-m1-coverage-20261011/docs/research/QORE_NATIVE_G0_NINE_MARKET_NATIVE_M1_EXECUTED_AUDIT_2026-10-11.md), commit documentación 5d90dcd1fd33eb4d344ae9decbb4398b46967777 |
| **Datos M1 originales** | [Run #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), origen SHA 18c338aedd5013ce65a6cb6408ffbc2e904a6217, por mercado artifact qore-capitalizer-cibo-10y-native-m1-SYMBOL-SHA |
| **Estudio Londres ajeno** | [Issue #785](https://github.com/mezas3238-hue/qore-core/issues/785), [handoff TTrades específico](https://github.com/mezas3238-hue/qore-core/pull/786): investigación **PARALELA**, no trasvasar detectores u outcomes |

**Importante sobre ramas:** PR #790 (charter) y PR #791 (código G0) están en **ramas diferentes, ambas DRAFT**; la rama de este handoff deriva de G0 para que el código y el reporte ya existan en su árbol. El siguiente arquitecto debe reconciliar planes con respeto a otros trabajos concurrentes, sin merge ciego a main o a la base de Scalper. No usar las ramas de estudios antiguos como indicador de certificación.

---

## 3. LO QUE REALMENTE SE HIZO HASTA AHORA — TESTIGOS Y ALCANCE

### 3.1 Fase de diseño completada

1. Se creó [Issue #789](https://github.com/mezas3238-hue/qore-core/issues/789) para investigación propietaria y [PR #790](https://github.com/mezas3238-hue/qore-core/pull/790) con la carta científica inicial: tres mecanismos independientes, G0–G6, no tocar VPS/live.
2. Se abrieron los **tres issues de investigación individual**: DRIVE #792, RESET #793, RELATIVE #794. Cada uno describe hipótesis nula, universo posible, controles y STOP, pero **ninguno contiene resultados predictivos o trades autorizados**.
3. G0 recibió prerregistro de métricas y contratos de proveedor antes de crear el motor analítico y mirar su output. Se programó el auditor de fuente M1 y siete pruebas para order/duplicate/gap/15/60 coverage, sin importar V49 como señal ni leer un trade ledger.
4. Primer CI falló por import de test no usado (Ruff); se corrigió y lanzó otro run. **La ejecución válida es #38166675573**, NO presentar el run fallido preliminar #38166625800 como validación o edge.
5. **Segundo CI #38166675573 SUCCESS**: contrato/tests + nueve market jobs + cross_market = **11/11 jobs con éxito**. Se comprobó presencia nativa M1, manifesto, hashes fuente, linealidad de timestamps, precios y M15/H1 observadas, gaps dentro de fecha UTC, y tres intersecciones de minuto exacto entre símbolos. Se publicó informe y comentarios con resultados a los cuatro issues.

### 3.2 Resultado EXACTO G0 por mercado, 2025-09-17 a 2026-09-17 [UTC end exclusive]

El conjunto tiene **3.297.154 velas M1 realmente observadas** en nueve símbolos. **Estructura de origen válida bajo las comprobaciones G0**; TODOS tienen bloques M15 activos parciales. **No se certificó el calendario real por sesión, H4, costes, ni ejecución**.

| Instrumento | M1 nativas observadas | Días hábiles UTC con registros | M15 completas de 15/15 | M15 parciales (1–14 M1) | H1 completas / H1 activas |
|---|---:|---:|---:|---:|---:|
| EURUSD | 369.903 | 260 | 23.717 | 1.131 | 5.524 / 6.213 |
| GBPUSD | 369.833 | 260 | 23.906 | 942 | 5.572 / 6.213 |
| USDJPY | 369.672 | 260 | 23.856 | 991 | 5.624 / 6.213 |
| AUDUSD | 369.269 | 260 | 23.642 | 1.205 | 5.576 / 6.213 |
| AUDJPY | 371.156 | 260 | 24.168 | 677 | 5.673 / 6.213 |
| GBPJPY | 371.465 | 260 | 24.244 | 604 | 5.681 / 6.213 |
| XAUUSD | 353.355 | 259 | 23.086 | 534 | 5.381 / 5.909 |
| USDCAD | 368.740 | 260 | 23.599 | 1.248 | 5.461 / 6.213 |
| NAS100 | 353.761 | 260 | 23.384 | 221 | 5.689 / 5.907 |

- Un bloque "M15 parcial" es uno que tiene **al menos una M1** pero menos de quince; **NO** implica corrupción. Puede incluir rollover, cierres normales, falta de liquidez, problemas de fuente. Separar por sesión/calendario antes de atribuir causa.
- G0 no comprueba que M15 o H1 del futuro se puedan utilizar al cierre en una estrategia concreta; solo disponibilidad de minutos. La lógica first-online del trader está PENDIENTE.
- **Fuente M1 examinada previamente por QORE**. No renombrar el año 2025–26 "holdout nuevo", aunque un investigador de esta rama no haya visto ese resultado particular.
- Los hashes del manifest y de las particiones están en artefactos G0 por mercado; recomprobarlos al leer de nuevo, no confiar en números copiados de este documento.

### 3.3 Sincronización literal de minutos entre mercados: RELATIVE

| Par | Minutos M1 UTC comunes | Solo primer par | Solo segundo par | Jaccard entre minutos observados |
|---|---:|---:|---:|---:|
| EURUSD / GBPUSD | **368.289** | 1.614 | 1.544 | **99,150 %** |
| AUDUSD / GBPUSD | **367.835** | 1.434 | 1.998 | **99,076 %** |
| AUDJPY / GBPJPY | **370.858** | 298 | 607 | **99,757 %** |

Los tres pares tienen coincidencia de **algún minuto** en 312 fechas UTC; eso NO implica que esas 312 fechas estén completas. No hubo rellenado, interpolación, ffill ni comparación de retornos futuros. **Jaccard >99% demuestra posibilidad material de estimar relaciones sincronizadas, NO cointegración, reversión, edge o fills de dos órdenes.**

### 3.4 Qué no se ha hecho

| Trabajo | Estado comprobable |
|---|---|
| Investigación G1: ¿hay continuación condicionada DRIVE? | **NO EJECUTADA** |
| Investigación G1: ¿hay reversión condicionada RESET? | **NO EJECUTADA** |
| Investigación G1: ¿hay residual convergente RELATIVE? | **NO EJECUTADA** |
| Motores causales de entrada/salida de esos traders | **NO IMPLEMENTADOS** |
| Stops/targets económicos calibrados y costes broker | **NO IMPLEMENTADOS/NO VERIFICADOS** |
| Preregistros económicos individuales y número de intentos | **PENDIENTES** |
| Walk-forward y validación OOS realmente no inspeccionada | **NO ACREDITADA** |
| PF, Sharpe, Sortino, DD de QORE Native | **NO MEDIDOS**, no inventar |
| Cognitivas propias DRIVE/RESET/RELATIVE operativas | **NO IMPLEMENTADAS** |
| Integración en Shared/CIBO/QDLE, PAPER, VPS, MT5 o live | **NO AUTORIZADA** |

**Conservar este semáforo.** Un handoff no es un resultado científico y una prueba de calidad de datos no autoriza una señal.

---

## 4. REGLAS INQUEBRANTABLES DE INVESTIGACIÓN

### R01 — VERDAD SOBRE LA ORIGINALIDAD
No importar CISD, MSS, FVG, protected swings, Asia sweep, TTrades o señales V49 y rebautizarlas como "nativas". Se pueden investigar fenómenos universales conocidos en literatura, pero las **reglas concretas, criterios y tests deben originarse de nuestras hipótesis + datos**, con trazabilidad. Literatura es motivo para investigar, no performance nuestra: Moskowitz/Ooi/Pedersen 2012 (momentum), Gao/Han/Li/Zhou 2018 (intraday momentum), Krohn/Mueller/Whelan BoC 2021 (FX fixing), Gatev/Goetzmann/Rouwenhorst 2006 (pairs principalmente acciones), Bailey/López de Prado (múltiples pruebas / deflated Sharpe). No transponer conclusiones de acciones/futuros a spot FX/CFD.

### R02 — UN EDGE POR MOTOR
Cada una de las tres hipótesis tiene un **primary endpoint único**, un conjunto de controles y un número registrado de intentos. No mezclar 7 variantes de DRIVE y elegir la que tiene mejor PF como un ensayo único. Los resultados de candidatos anteriores no se mezclan para producir artificialmente un trader ganador.

### R03 — FIRST-ONLINE REAL
Toda feature tiene event_time, available_at, timeframe completo, fuente y validez. Decisión en t SOLO puede leer barras cerradas <=t y estado computable entonces. Tests de prefix invariance: añadir mañana nunca cambia la decisión de hoy. No usar MFE/MAE/maximum excursion futura en filtros pretrade. Si una vela llega parcialmente, NO se reconstruye su high/low futuro.

### R04 — SENSIBILIDAD DE DATOS
No excluir a posteriori fechas malas solo porque empeoran edge. Precongelar política de cobertura, festivos, DST, rollover y proveedor, y publicar n censuradas por regla. La ausencia de H4 en otro proyecto no demostró por sí sola "mercado roto"; aquí M15 parciales tampoco.

### R05 — CALIDAD DE VALIDACIÓN
Periodo 2025-09→2026-09 está **contaminado para confirmación nueva** por exploraciones previas de QORE. Úsese solo como DESARROLLO si el protocolo lo permite, registrando reutilización; reservar material verdaderamente no inspeccionado (otros años/proveedor autorizado o adquisición futura, si se dispone). Walk-forward con embargo por solapamiento, sin recalibrar tras mirar holdout; si no hay holdout, dictamen INCONCLUSIVE/OOS_BLOCKED, no "certificado".

### R06 — COSTES Y EXECUCIÓN
Para detectar patrón estructural bastan OHLC confiables; para estimar **capturabilidad neta**, cada estrategia necesita costes de su mercado/horario/venue, comisiones, slippage, bid/ask cuando disponible, swaps/funding si aplica. RELATIVE paga costes de dos piernas. M1 stop y target tocados en la misma vela = resultado intraminuto DESCONOCIDO sin fuentes más finas; reportar bounds/escenarios, no inventar fill. Llamar ASSUMED a costes supuestos, BROKER_OBSERVED solo a comprobados.

### R07 — RIESGO COMPUESTO
Medir DD individual **y** combinado bajo simultaneidad, exposición USD/JPY/CFD, cola compartida, correlación bajo estrés, margen, sizing y capacidad. Tres estrategias con el mismo factor no implican diversificación. Core debe poder apagar una familia si hay drift o pérdida de integridad sin permitir al propio trader alterar presupuesto.

### R08 — FALSACIÓN Y REPRODUCIBILIDAD
Fecha+SHA de prereg ANTES de leer outcome, source manifest hash, GitHub Actions run + artifact, informe de números positivos/negativos y bugs. Si falla un gate => STOP, no rescate de umbral hasta nuevo experimento/prereg con corrección de multiplicidad. Evitar HARKing; ningún reanálisis es replicación OOS. Un DeepSeek crítico puede ayudar, pero no reemplaza una prueba.

---

## 5. TAREAS DEL SUCESOR POR ORDEN DE PRIORIDAD: P0 HASTA CERTIFICAR

### P0 — TOMA DE CONTROL / CONGELACIÓN (PRIMERA ACCIÓN)

**Trabajo:** leer Issue #789, charter PR #790, código y reporte G0 PR #791, issues 792/793/794 y este documento. Verificar estado concurrente de PRs/runs/branch antes de editar, puesto que hay arquitectos trabajando en repositorio a la vez. Crear una rama nueva propia por gate, sin merge automático a main, no tocar producción.

**Entregable:** mensaje de inicio en #789 con SHA base, inventario de todos los sources y cuatro columnas por trader: hipótesis / datos elegibles / test planeado / bloqueo. Marcar G0 ejecutado, G1–G6 pendientes.

**STOP si:** no puede verificar el archivo G0, fuente o manifest/sha. En ese caso restaurar trazabilidad sin inventar un resultado.

### P1 — G0B: CALENDARIOS DE SESIÓN, VENUE Y CALIDAD CAUSAL POR INSTRUMENTO

**Trabajo obligatorio inmediato:**
1. Determinar la naturaleza real de los instrumentos (**NAS100 CFD vs índice vs futuros; XAUUSD spot/CFD; FX spot**) y origen de barras M1, timezone broker/UTC, DST y días festivos/cierres, horarios open/close/trading breaks. **No inventar horario nominal NAS100 24/7**.
2. A partir de los nueve bitmaps G0, cuantificar **cobertura esperada vs observada por hora operable** de cada mercado y por 15/60min, ratio de minutos faltantes **dentro** de hora operativa y de cortes de mercado, fragmentación por fechas, outages y proveedor. No confundir hours normales cerradas con gaps.
3. Inspeccionar M15/H1 solo a partir de M1 15/15 o 60/60 si eso requiere una feature; para volatilidad derivada M15 suficiente según contrato congelado sin backfill. Definir tratamiento de FVG/volumen solo si fuente existente, sin generar test económico.
4. Auditar calendario oficial/venue de fixing FX para RESET y trades near open para DRIVE, con Europe/London / America/New_York y DST, y simultaneidad de minuto para RELATIVE. Causas de datos ausentes deben quedar documentadas o etiquetadas UNKNOWN, no adjudicadas especulativamente.
5. Preparar inventario de costes conocidos/inexistentes por mercado y ventana; sin priorizar ticks como bloqueo de G1 descriptivo, pero sí de certificación física neta.

**Entregable:** PR G0B con matriz symbol→venue→calendar/provenance→M1 expected/observed→eligible days/windows→spread source→reason-codes + GitHub Actions + fixtures DST y gaps; informe SOURCE_OK / PARTIAL / BLOCKED por mercado/ventana. Publicar en Issues 792/793/794. **Sin medir todavía retornos condicionados.**

**Riesgos:** G0 reportó 1.248 buckets M15 parciales en USDCAD y 1.205 en AUDUSD, 221 en NAS100; nada prueba que estén en ventanas de trading exigidas. Determinar distribución antes de escoger filtros y N.

### P2 — G1-A DRIVE: DESCUBRIMIENTO DIRECCIONAL DE MERCADO

**Hipótesis independiente:** después de observar un desplazamiento/impulso durante un intervalo completamente cerrado, hay **persistencia futura condicionada** superior a tomar la misma dirección/hora sin señal, neta de fricciones razonables. No asumir esta hipótesis verdadera.

**Mercados candidatos:** NAS100, XAUUSD, EURUSD, GBPUSD. NO elegir "mercado ganador" después de cuatro resultados y ocultar los otros.

**Antes de abrir returns:** congelar símbolo principal y orden de replicación, sesión real, longitud ventana de observación y siguiente horizonte, medida de shock/impulso predecisional, normalización de volatilidad basada solo en pasado, si se exige aceptación de cierre, controles de misma hora/volatilidad y noticia/regímenes, MDE/N y presupuesto de tests. Direccionalidad observada antes del próximo open.

**Test G1 descriptivo:** comparación de distribución condicional del forward return desde **siguiente instante operable** (no desde la vela que construyó trigger), frente a baseline sin filtro en mismo symbol/hour/risk, pseudo-entradas y dirección opuesta; confusores noticia, días extremos, missingness y estabilidad por régimen. Calcular IC por fecha. Aún no diseñar stop/TP óptimo.

**STOP:** si no supera baseline con precisión útil, si la ventaja desaparece desplazando entrada una vela, o surge exclusivamente tras lookahead/eventos ex-post/spread inviable.

**Entregable:** prereg DRIVE G1, código/fixtures, run, JSON de cohortes, comparación/CI, conclusión DRIVE_G1_GO/STOP/INCONCLUSIVE en #792. Si STOP, NO construir la cognitiva de DRIVE.

### P3 — G1-B RESET: PRESIÓN TRANSITORIA Y REVERSIONES SIN FALSAS MANIPULACIONES

**Hipótesis independiente:** movimientos a horas económicas/fixing de FX pueden tener componente temporal y revertir después. Debe diferenciarse de retorno normal de hora/mean reversion genérica y no depender de información intra-vela que todavía no existe.

**Mercados:** EURUSD, GBPUSD, USDJPY. Calendarizar fixing/ventana contra fuente fiable y DST antes de ver resultados; distinguir anuncios macro, spreads amplios y huecos de feed.

**Antes de returns:** congelar anchor horario, formación de movimiento antes del evento, entrada en vela siguiente después de confirmación, orientación preentrada, ventana post-evento, placebo de misma sesión/hora, días sin shock vs con shock, N/MDE y modo de censura. N de oportunidades por fecha sin duplicar opciones horarias.

**Test G1:** diferencias de retornos después de presión observada vs misma franja sin ella y placebo, sensibilidad a regime/news, delays +1 M1 y modelo de costes por ventana (preliminar). No afirmar que la causalidad de FX fixing sea observable desde OHLC solamente; puede ser hipótesis de flujo.

**STOP:** si no discrimina o reversión está dominada por spreads/noticias/missingness. **Entregable:** prereg+CI+testigos G1 y dictamen en #793. Si STOP no encender una cognitiva para compensar.

### P4 — G1-C RELATIVE: PROBAR RELACIÓN RESIDUAL, NO CORRELACIÓN

**Hipótesis independiente:** desviación en residual entre dos instrumentos sincronizados retorna por encima de un control neutral y de un benchmark sin predictibilidad. G0 NO probó esto.

**Preselección de parejas de fuente G0:** EURUSD/GBPUSD; AUDUSD/GBPUSD; AUDJPY/GBPJPY. Definir UNA pareja primaria antes de returns y las otras como replicaciones (evitar escoger ganadora tras mirarlas). Igualdad de timestamps por intersección de minute-bitmaps; si una pierna falta, **NO crear precio con forward fill**.

**Antes de returns:** método de beta/hedge estimado en ventana histórica previa, transformación de retornos o log-prices consistente, control de denominaciones y factores monetarios, ajuste por inversión nominal, test de estabilidad/regime drift, límite de hedge error y reglas para no estacionariedad. Evitar regresión estática entrenada incluyendo el periodo de cierre de trade. Estimar coste DOS piernas incluyendo slippage/correlación de ejecución y riesgo open mismatch.

**Test G1:** comprobar si spread residual presenta reversión condicional más allá de un random walk/control neutral de factor y coste; comparar error OOS de predicción, tamaños y regímenes. Bootstrap por fechas sincronizadas, estrés beta adversa. No confundir señal de spread grande con trade rentable.

**STOP:** beta inestable, residual no retorna, timing/no-sync demasiado alto, oportunidad muere con costes dobles. **Entregable:** prereg + test G1 + informe por pareja y veredicto #794.

### P5 — G2: MOTORES Nativos FIRST-ONLINE SOLO PARA CANDIDATOS GO

Si uno o varios candidatos superan G1:
- Crear namespaces separados dentro Trader Lab: qore_native_drive_*, qore_native_reset_*, qore_native_relative_*; lector neutro de M1 permitido, reutilización de sensores V49/ICT/TTrades NO.
- Contrato de entradas/espera/abstención, expiración, prioridad múltiples señales, stop estructural o estadístico basado exclusivamente en información previa, target basado en distribución de investigación **sin escoger óptimo tras inspeccionar test**; reglas de time exit, neutralidad, trading blackout si datos.
- First-online: event_time, available_at, source_id, decision state, barra identificada y reason-code; prefix invariance + tests de último minuto, gaps, DST, duplicated bars, no future candle, regresión de señales en replay incremental vs batch, SL/TP same-bar.
- Para RELATIVE: máquina ATÓMICA de 2 piernas, fill partial, hedge drift, colateral/margen, reconciliación de error y stop global por residual; un trade no puede considerarse neutral si falla uno de los fills.
- Separación básica de señal (motor) y cognitiva: primero probar señal determinista. Solo añadir capa cognitiva si demuestra valor incremental causal con prueba A/B congelada (sin lookahead ni usar resultado de test para "razonar" mejor).

**Entregable:** motor/tres contratos separados según aprobados, suite CI causal, registros pretrade y reporte de integración de fuentes. Failure=NO PROMOTION.

### P6 — G3 Y G4: BACKTEST ECONÓMICO, WALK-FORWARD, HOLDOUT Y FALSACIONES

**Preregistro INNEGOCIABLE antes de evaluar:** señal/config SHA, símbolos, ventanas horarias, tamaño, stop/TP/trailing/time exit, costes por instrumento/franja, tracking P&L y abstenciones, OOS, N/MDE, baseline, endpoints, selección de uno entre pruebas posibles y corrección por multiplicidad. Registrar todas variantes DEV y su presupuesto.

- **G3 economía:** PF NETO, EV neta R/trade, pérdida bruta, DD R, tasa WIN/LOSS, duración, frecuencia por mes/año, MAE/MFE SOLO descriptivos posttrade, Sharpe/Sortino en retornos periódicos de cartera definidos (cuidado con inflación por operaciones), riesgo y nominal consistente. Costes 1× /1.5× /2× + slippage y missed fills; bajo M1 dual touch, escenarios stop-first/target-first y límite de ejecución.
- **G4 ciencia:** validación walk-forward cronológica, embargo por etiqueta/horizonte solapado, holdout realmente nunca consultado, sensibilidad missingness y fuente, leave-regime-out, control de shocks/gap, aumento de costes, calendario, placebo, dirección contraria, superioridad frente a baseline; CI95 por fecha y block bootstrap emparejado si instrumentos USD correlacionados; multipruebas y deflated Sharpe si aplica.
- OOS virgen es **BLOQUEO ACTUAL**. Un periodo anterior de la misma base explorada NO revive virginidad. Si no se puede conseguir fuente cronológica genuinamente no utilizada, reportar OOS_BLOCKED, conservar ensayos como exploratorios.
- BARRERAS PROPUESTAS (NO políticas oficiales Core): PF neto >1,30 y evidencia de EV neta >0 frente a baseline (su IC de diferencia no debe ser compatible con ventaja nula para promover), estrés de costes no catastrófico, Sharpe/Sortino con n y periodos, DD bajo techo de riesgo prefijado. El umbral de DD y mínimos de Sharpe/Sortino deben acordarse y congelarse con el propietario ANTES de ejecutar, no inventar retroactivamente. **PF por sí solo no aprueba un trader**.
- Si hay menos operaciones de lo que permite detectar MDE relevante, resultado UNDERPOWERED, no positivo ni refutación universal. Si el ensayo es negativo bajo definición fija, cerrar ESA HIPÓTESIS y no optimizar de forma ilimitada para rescatarla.

**Entregable:** un PR/replay único y un informe económico por candidato con evidencias Actions/artefactos y veredicto NET_EDGE_SUPPORTED_IN_TESTED_SCOPE / NO_EDGE_IN_TESTED_SCOPE / INCONCLUSIVE / DATA_BLOCKED / OOS_BLOCKED / COST_UNRESOLVED.

### P7 — G5 / G6: PORTAFOLIO COMBINADO, COGNITIVAS Y PREPARACIÓN PAPER

**Solo tras certificación individual, no antes**:
1. Congelar versiones y construir series de retornos por día con mismo calendario, posiciones, nominal, acceso y exposiciones. Correlaciones en normal y en cola, riesgo dólar/yen/índice/oro, overlapping trade windows, drawdown conjunto, contribución marginal de diversificación.
2. Comparar conjunto DRIVE+RESET+RELATIVE con cada trader por separado, con combos parciales y benchmark cartera a riesgo total igual. Si el portfolio con tres empeora DD o comparte beta, limitar/desactivar uno aunque tenga PF individual >1.
3. Pruebas capacidad/costes al aumentar órdenes/tamaño, márgenes, eventos de baja liquidez, órdenes simultáneas y error de reconciliación. Adaptación de tamaño de posición **no** puede violar riesgo del presupuesto de Core.
4. Integración futura: Trader recomienda con pruebas y telemetría, **Shared** arbitra integridad y riesgo conjunto, **CIBO** decide presupuesto, **QDLE** filtra y ejecuta; ensayos A/B sin destruir ventajas individuales, freeze modelo y risk budget. La cognitiva de cada trader debe explicar por qué abstuvo/entró y sus cambios sin aprender del futuro. Rechazar si añade discrecionalidad no reproducible.
5. PAPER y telemetría sostenida, kill switches/alertas/data drift; criterios objetivos para solicitar más adelante autorización separada para VPS/live. **Este handoff NO autoriza VPS, ni MT5 live, ni cuenta real**.

**Entregable:** evaluación conjunta con capital y límites fijados, test de riesgo de cola, arquitectura interfaz Core y resultados PAPER cuando proceda. Estado FINAL por trader CERTIFIED_RESEARCH / PAPER_ELIGIBLE / NOT_CERTIFIED; la certificación para escala institucional exigiría trabajo adicional.

---

## 6. PRIORIDAD DE RIESGOS Y PREGUNTAS ABIERTAS

| Prioridad | Riesgo no resuelto | Qué debe comprobar el sucesor |
|---|---|---|
| P0 | **Confundir datos con señales** | G0 no calculó futuro; no presentar 3,3 M velas como tres edges |
| P0 | **Calendarios/GAPS parcial de M15/H1** | Segmentar por mercado, apertura/cierre real, 1–14/15, DST, proveedor |
| P0 | **No hay OOS virgen** | Reservar/acreditar periodo o feed NO inspeccionado; no reciclar el anual |
| P0 | **Hipótesis todavía sin definición única** | Prereg por estrategia antes de ver forward returns; una primaria y controles |
| P0 | **Mercados correlacionados USD** | Bootstrap fechas y portfolio por factor, no operaciones independientes ficticias |
| P1 | **DRIVE oportunista en noticias/breakouts** | Sesgo de hora, spread, latencia de cierre, delays y shock controls |
| P1 | **RESET identifica reversión ex-post** | Fijar fixing, entrada sólo después de confirmar, ver placebo y news |
| P1 | **RELATIVE falsa cointegración** | beta t calculada sólo con pasado, diferencia residual estable, dos piernas costeadas |
| P1 | **Profit Factor engañoso** | EV neta, DD, Sharpe/Sortino con CI y costes/sesiones auténticas |
| P1 | **Overfitting de tres familias × mercados × umbrales** | Registrar familywise attempts y multiplicidad, no ocultar negativos |
| P1 | **Calidad de broker/capturabilidad física** | Precio negociable, spread, comisión, fill, slippage, same-M1 stops |
| P1 | **Cognitiva opaca o no causal** | A/B precongelado para filtro/regime, reason codes, log del modelo |
| P1 | **Capacidad y riesgo de Core compuesto** | Margen, correlación de cola, stress, pérdidas simultáneas, control Shared/CIBO |
| P2 | **Expiración de GitHub artifacts (90 días)** | Conservar manifests/logs/snapshots legal y eficientemente; no meter datos sensibles gigantes al git |
| P2 | **Conflicto entre arquitectos/branches** | Commits y ramas aislados, no merges sobre VPS/Main sin autorización |

### Hallazgo técnico especial para RELATIVE que merece alerta

- 368.289 min M1 comunes EUR/GBP son minutos UTC **disponibles**, no una serie de spreads ejecutables simultáneos ni una prueba de que ambos brokers ejecutan a ese mid. Considerar delays, horarios y cambios de beta. La correlación interpar positiva se puede deber solo al dólar estadounidense.
- No utilizar EURUSD/GBPUSD porque los anteriores proxies Londres divergían bajo RECLAIM/ACCEPTED: esa línea falló promoción [#775](https://github.com/mezas3238-hue/qore-core/issues/775), no un descubrimiento positivo reutilizable.

---

## 7. ENTREGABLES MÍNIMOS, DEFINITION OF DONE Y FORMATO PARA COMUNICAR AVANCES

Cada paso exige **hechos en GitHub**, no solo ideas:
- **PRERREG:** pregunta primaria + NULL + mecanismo causal + universo/fechas/horas/variable conocida + presupuesto de intentos + baseline + MDE/potencia + bloqueos/calidad + STOP/GO + hash del prereg **antes de outcomes**.
- **CÓDIGO:** commit/PR DRAFT separado de main y de ramas live; definición de filtros sin future data; tests de intervalos, edge cases y reproducibilidad.
- **RUN:** GitHub Actions ejecutado con SHA, logs SUCCESS o razón de failure y artifact verificable; **NO copiar números de una ejecución que falló**.
- **REPORTE:** N de observaciones válidas y censuradas, comparación baseline, intervalos, costes/hipótesis de broker, diversidad de regímenes, sensibilidades, efectos positivos y negativos; conservar registro de intentos y grados de libertad.
- **VEREDICTO POR CANDIDATO:** PASS exploratorio / STOP / INCONCLUSIVE / BLOCKED antes de la siguiente puerta. El reporte publicado debe explicar qué sobrevive y QUÉ NO prueba.
- **ENLACES DE CONTINUIDAD:** comentar issue respectivo #792/#793/#794 y actualizar programa #789 con PR/run/file SHA/artifact.
- **SIN EJECUCIÓN EN PRODUCCIÓN:** no VPS, MT5 live, órdenes reales, alteración de V49, de Shared/CIBO/QDLE ni de otras metodologías del Core.

Formato sugerido breve para comentarios del sucesor:
**GATE | SHA PREREG | SHA CÓDIGO | RUN/ARTIFACT | DATOS/COBERTURA | PRIMARY EFFECT/CI/BENCHMARK | COSTES | BLOQUEOS | STOP/GO | PRÓXIMA ACCIÓN**.

## 8. PRIMERAS INSTRUCCIONES DEL PRÓXIMO ARQUITECTO (ORDEN INMEDIATO)

**PRIMER TRABAJO VERIFICABLE:** realizar G0B, **NO programar ya un robot con señales**. Reabrir artefacto G0 y validar hash de fuente; mapear calendarios/horarios de mercado y cobertura exacta en ventanas candidatas sin leer retornos. Publicar PR con Actions y reporte y decidir si cada candidato tiene datos suficientes. Ya existen 9 artefactos por mercado más un agregado.

**SEGUNDO:** crear TRES prerregistros separados de G1 para DRIVE #792, RESET #793 y RELATIVE #794; para cada uno especificar primary endpoint, baseline, instrumento primario, ventanas, N/potencia, inferencia y test STOP/GO. Registrar fuentes económicas como PRIOR, sin copiar edge supuesto.

**TERCERO:** ejecutar observaciones de G1 (cada una con CI y controles), publicar incluso los negativos. No desarrollar cognitiva de un candidato que no supera G1.

**CUARTO:** para los candidatos GO, crear motores first-online G2 y test de economía G3; luego holdout genuino G4 y cartera G5. Hacer documentación y pruebas en GH, no VPS. No contaminar cohortes test con tuning y no certificar sin costes.

**QUINTO:** una vez haya evidencia neta realmente independiente, diseñar cognitiva y contrato con Shared/CIBO/QDLE y estudiar PAPER. Se requiere autorización expresa posterior para cualquier despliegue.

**Principio terminal:** la visión de QORE son *hasta tres especialistas inteligentes con ventajas genuinas y complementarias*, no una fábrica de etiquetas o un triple backtest que muestra ganancia por casualidad. La certificación solo existe cuando datos, ejecución, estadística y riesgo de cartera concuerdan.
