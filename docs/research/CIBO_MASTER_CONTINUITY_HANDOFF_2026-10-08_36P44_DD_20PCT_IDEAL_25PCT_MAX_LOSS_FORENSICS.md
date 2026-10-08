# QORE CORE — CIBO MASTER CONTINUITY HANDOFF
## 2026-10-08 · CORTE DE ESTADO VERIFICADO EN GITHUB · DRAW­DOWN 36,4423% · 20% IDEAL / 25% MÁXIMO TOLERABLE

**TIPO:** Handoff maestro de ingeniería, investigaciones, pérdidas, drawdown, economía compuesta, riesgos, Trader Lab y pasos restantes para la certificación científica de CIBO.  
**ESTADO:** CIBO **NO CERTIFICADO**. La ejecución histórica investigativa **NO autoriza operar cuentas reales o fondeadas**.  
**Corte de verificación:** 2026-10-08 ~10:20 UTC. **Antes de continuar, comprobar workflows/HEAD posteriores a este corte**.  
**Repositorio:** `mezas3238-hue/qore-core`.  
**Rama exclusiva de ESTE handoff:** `agent/cibo-master-continuity-handoff-20261008-dd-forensics-001`.  
**Rama de trabajo del otro arquitecto — NO PISAR:** `agent/cibo-causal-expectation-leakage-fix-001`, último HEAD leído: `d893b9d48eb844d712f752a6b469d678980ad885`.  
**Rama de investigación G5 y auditor forense de este arquitecto:** `agent/cibo-loss-tail-causal-exposure-g5-001`.  
**Rama del informe forense completo de 3.368 operaciones:** `agent/cibo-complete-loss-forensics-3368-h1-001`.

---

# 0. DIRECTIVA SOBERANA DE CONTINUIDAD — LEER PRIMERO

**La misión actual es investigar exhaustivamente las causas del DRAWDOWN y reducirlo tanto como científicamente sea posible SIN DEGRADAR EL TECHO de rentabilidad compuesto alcanzado.** No basta con optimizar una cifra aislada; preservar la economía y administrar las grandes pérdidas es obligatorio.

**DRAWDOWN IDEAL = 20% o menor. DRAWDOWN MÁXIMO TOLERABLE = 25%.** El objetivo intermedio de ingeniería de la vigilancia automática es 22%, pero 22% **no sustituye** ni el ideal 20% ni el criterio de tolerancia ≤25%. DD >25% no cumple esta fase. Alcanzar 30%, 28%, 25% o incluso 22% no significa que se deba parar si se puede seguir reduciendo sin deteriorar el techo.

**Capital:** inicio histórico de USD60. El antiguo techo mínimo congelado es **USD582.440,0252953678696769360345**; es el suelo de investigación que no se debe violar. Las mejoras posteriores de capital **>USD673.000** forman parte de la frontera económica conseguida y se deben defender. La meta de 8.000% de rentabilidad fue **solo una base original para investigar**, nunca un techo fijo.

**Autoridad de entrada:** los Traders generan y ejecutan TODAS las señales. CIBO debe administrar **cada entrada** una vez ejecutada: Size, Leverage, ATTACK, CIBO Compound, Portfolio Compound y lifecycle. **Prohibido rechazar, bloquear, retrasar, aplazar, censurar o seleccionar operaciones del Trader.** Cada replay debe conservar las **3.368/3.368 entradas**.

**No elegir retrospectivamente los perdedores:** cualquier señal de pérdida o condición que dispare una defensa debe ser **causal**: estado disponible antes de la entrada, liquidaciones anteriores solamente, o M5 ya cerrada durante la posición y ejecución en apertura posterior modelada. Prohibido usar el resultado de la operación, una fecha histórica identificada por auditoría, un ID de Trader o el `signal_fingerprint` como discriminador de decisiones.

**Condición soberana:** `attack_sovereign_breach_usd=0` NO equivale a `sovereign_floor_breach_usd=0`. Se ha detectado una anomalía de este último indicador de ~USD85,42 en el mejor carrier forense. La certificación requiere corregirla o demostrar inequívocamente la conciliación exacta y cero violación real. No declarar fondos soberanos sanos sin auditarlos.

**Metodología:** `AUDITAR TODAS LAS PÉRDIDAS → clasificar causas + proteger ganadores → hipótesis causal → modificar CIBO (rama propia) → replay completo 3 años en Trader Lab → comprobar metrics/gates → promover solo mejora → reanalizar todos los episodios → repetir`. Evitar barridos ciegos de centésimas con daño al compuesto. Nunca sustituir investigación por narrativas sin replay.

# 1. ESTADO REAL VERIFICADO EN GITHUB — HAY MÁS DE UNA FRONTERA

¡ATENCIÓN! El usuario comunicó que el DD estaba en **36,50%**. Se revisaron los workflows de GitHub y la batería posterior [`37762724394`](https://github.com/mezas3238-hue/qore-core/actions/runs/37762724394) **SUCCESS** prueba variantes adicionales:

| Línea | Candidato | Max DD | Capital final USD | Gross loss total USD | ATTACK GL USD | PF total | Evidencia |
|---|---|---:|---:|---:|---:|---:|---|
| **Menor DD observado de estas ramas** | **`m1-2900`** | **36,44228532685719%** | **671.094,90121861** | **957.756,43254418** | **956.200,45130835** | **1,7006321** | [run 37762724394](https://github.com/mezas3238-hue/qore-core/actions/runs/37762724394), artifact **11542304451** |
| **Pareto estricto validado contra `carrier36509-tfb` en esa batería** | `m1-2925` | **36,45907191119630%** | **671.077,45396484** | **957.746,54148193** | **956.190,54685646** | **1,7006211** | [run 37762724394](https://github.com/mezas3238-hue/qore-core/actions/runs/37762724394) |
| Control de esa rama | `carrier36509-tfb` | 36,50943166421363% | 671.077,41379592 | 957.746,58165085 | 956.190,54685646 | 1,7006210 | Igual run |
| **Mejor balance DD/GL/riqueza en nuestra rama forense** | **`em-s06745`** | **36,91053924475216%** | **673.146,52545398** | **940.435,76305544** | **938.872,84954047** | **1,7157177** | [run 37759974174](https://github.com/mezas3238-hue/qore-core/actions/runs/37759974174), artifact **11542321736** |
| Máximo capital final entre estos carriers | `ex-s070` | 37,08176240501109% | **673.214,64480045** | 940.463,39861352 | 938.900,34852421 | 1,7157691 | [run 37759331934](https://github.com/mezas3238-hue/qore-core/actions/runs/37759331934) |

**Interpretación crítica:**
- `m1-2900` da el **menor drawdown medido** (36,4423%) pero **NO pasó el STRICT PARETO local** porque, respecto al control `carrier36509-tfb`, suben las pérdidas brutas total y ATTACK. NO presentarlo como mejora multiobjetivo completa.
- `m1-2925` sí figura entre los **`STRICT_PARETO_CASES` y `DOMINATES_CURRENT_CASES`** de la última batería, pero esto es **respecto a su control local**, no una dominancia mundial frente a `em-s06745`.
- `em-s06745` tiene ~USD2.051,62 más capital final y ~USD17.320,67 menos pérdidas brutas que `m1-2900`, a costa de DD ~0,4683pp mayor. **Ambos son alternativas de frontera; no borrar ninguno**.
- `ex-s070` añade ~USD68,12 sobre `em-s06745` con DD ~0,1712pp mayor y GL ~USD27,64 mayor. Considerar ambos para Pareto.
- `m1-2925` ahorra GL marginal frente al `carrier36509-tfb`, mientras `m1-2900` reduce más DD pero aumenta GL. Conservar opciones; decidir por análisis científico/certificación, NO solo por columna DD.
- A la fecha del corte **ninguno** de esos casos llega a ≤25%, ≤22% o ≤20%. No pronunciar «Trabajo cumplido».

El otro arquitecto puede lanzar nuevas pruebas mientras se lee este archivo: obtener el SHA de su rama y las últimas ejecuciones GitHub **antes de afirmar “nuevo récord” o fusionar policies**. Por compatibilidad, mantener ramas separadas.

# 2. HISTORIA DE INGENIERÍA / TECHO VERDADERO / PROGRESIÓN

1. Techo económico de investigación pasó por escalado, compound y multipliers hasta fijar un benchmark de **USD60 → USD582.440,0253**, con máximo DD alrededor **65,10%**. Ese capital quedó **congelado como piso**, no límite superior de CIBO.
2. Compresión de ATTACK y riesgos selectivos con 3.368 entradas dio mejoras a ~USD663k, DD64,02%, GL1,30M. Se identificaron drawdown windows específicas, pérdidas ATTACK concentradas, y beneficios netos de separar taper por multiplier/risk.
3. `p30-cg600-1500-f95`: **USD668.085,92** / DD**38,4621%** / total GL**USD960.833,38** / ATTACK GL**USD959.269,45** / PF~1,6953, [run 37692116415](https://github.com/mezas3238-hue/qore-core/actions/runs/37692116415); dejó el gran handoff del 07-Oct, cuya arquitectura y certificación siguen útiles aunque su métrica principal ya quedó superada.
4. `carrier37772-p4150`: USD668.910,44 / DD37,7721% / total GL957.225,91 / ATTACK GL955.665,77. La reducción del DD anterior migró de ATTACK hacia MEDIUM bootstrap.
5. **G1 aditiva W8**, branch `agent/cibo-riskshield-additive-window8-g1-001`, docs `docs/research/CIBO_RISKSHIELD_ADDITIVE_WINDOW8_G1_2026-10-08.md`, [run 37738207384](https://github.com/mezas3238-hue/qore-core/actions/runs/37738207384), commit docs `e641f63c62a931e7cfe061503c524e1d2019ffdc`: 9 replays, victoria **`w8-5k10k-f900`**. Octava ventana causal ATTACK 5.000–10.000x, capital USD35k–65k, DD hasta 45%, taper fraction 0.90, **10 binds W8** + **3 binds W7** sin reemplazar las 7 anteriores. Capital **USD671.596,019535**, DD**37,66598266%**, total GL**942.631,991968**, ATTACK GL**941.071,852293**, PF**1,7124053**; ahorro ~USD14.594 de GL contra control 37,7721 y crecimiento de ~$2.686. Éste fue un resultado **positivo real**.
6. **G2 MEDIUM bootstrap parcial**, rama `agent/cibo-riskshield-medium-bootstrap-g2-001`, doc `docs/research/CIBO_RISKSHIELD_MEDIUM_BOOTSTRAP_G2_2026-10-08.md`, [run 37756517100](https://github.com/mezas3238-hue/qore-core/actions/runs/37756517100), artifact **11541140276**: 9 replays. `w8-p4020` pasa STRICT-PARETO frente a piso económico congelado: DD**37,65314425%**, final **USD671.596,006759**, GL**942.631,969109**, ATTACK GL**941.071,852293**, PF**1,7124053**; capital solo ~USD0.0128 menor que G1. Corredor MEDIUM fracción 0.400→0.402 muy estrecho: sobre ~0.405 afecta severamente wealth/pérdidas.
7. **G3 `MEDIUM` micro-ridge** (rama `agent/cibo-riskshield-medium-micro-g3-001`, [run 37757591148](https://github.com/mezas3238-hue/qore-core/actions/runs/37757591148)): 9 replays SUCCESS pero **STRICT_PARETO_CASES=[]**. `p4020-r35` reduce DD a ~37,0297%, pero capital baja a **USD665.735,99** y GL sube a **USD955.333,35**. Rechazar esa falsa victoria de DD.
8. **G4 bootstrap stop**, rama `agent/cibo-riskshield-bootstrap-initial-stop-g4-001`, [run 37757768704](https://github.com/mezas3238-hue/qore-core/actions/runs/37757768704): 9 replays SUCCESS, **STRICT_PARETO_CASES=[]**. Stop inicial más duro incluso aumenta DD a **41,1098%** o degrada fuertemente riqueza. El mecanismo de stop puede cortar recoveries; descartar.
9. En paralelo, otro arquitecto obtuvo `ex-s070` (37,08176% / $673.214,64), `eb-s0675` (36,91390% / $673.146,52) y luego `em-s06745` (36,910539% / $673.146,53), [run 37759974174](https://github.com/mezas3238-hue/qore-core/actions/runs/37759974174). Control causal MEDIUM-context stop `-0.6745R`, ATTACK context-exit gates; todas 3.368 operaciones.
10. **G5 causal exposure post-entry ATTACK**, rama `agent/cibo-loss-tail-causal-exposure-g5-001`, workflow `.github/workflows/cibo-trader-lab-loss-tail-causal-exposure-g5.yml`, [run 37761586870](https://github.com/mezas3238-hue/qore-core/actions/runs/37761586870), artifact **11542947452**, **FINAL SUCCESS / 9 replays / STRICT_PARETO_CASES=[]**. Control exacto `em-s06745`: DD36,910539%, capital673.146,53, GL940.435,76. Los **8** niveles de `--lifecycle-attack-override-projected-open-stop-risk-fraction-trigger` (0.03–0.15) produjeron el **mismo DD** pero bajaron capital a **USD671.802,85** y aumentaron GL a **USD941.779,44** / ATTACK GL940.216,53. **RECHAZAR** todos los umbrales; la señal no aportó protección y destruyó crecimiento. No repetir el mismo barrido como si fuera un avance.
11. Posteriormente el otro arquitecto profundizó `carrier36509-tfb` DD36,50943%, capital671.077,41, GL957.746,58; [run 37762724394](https://github.com/mezas3238-hue/qore-core/actions/runs/37762724394) completó el **M1 micro ridge** con `m1-2900` (DD36,4423%, floor-valid pero NO strict) y `m1-2925` (DD36,4591% y strict local). El anterior `37.xx%` del handoff 07-Oct ya NO es el estado actual.
12. Nuevos intentos `Carrier36509 Narrow DD Budget` [37762060159](https://github.com/mezas3238-hue/qore-core/actions/runs/37762060159), `Two Band` [37762199165](https://github.com/mezas3238-hue/qore-core/actions/runs/37762199165), `Triggered` [37762660789](https://github.com/mezas3238-hue/qore-core/actions/runs/37762660789) y `Rescue Envelope` [37762433200](https://github.com/mezas3238-hue/qore-core/actions/runs/37762433200): SUCCESS de jobs pero **sin nuevo STRICT PARETO válido**, con varios candidatos desplomándose a capital <USD582.440 e incluso ~USD1.000. No repetir blind tuning ni declarar triunfo por DD aislado.

# 3. INFORME FORENSE PROFUNDO — TODAS LAS OPERACIONES, NO SOLO 1 EPISODIO

**Fuente P0 obligatoria:** `agent/cibo-complete-loss-forensics-3368-h1-001/docs/research/CIBO_MASTER_LOSS_FORENSICS_3368_2026-10-08.md`, commit de su última revisión `d99ea36776aca53279a962713216ddd80d385343`. Consta el análisis de **3.368/3.368 receipts** de G2 y un join **3.368/3.368 por `signal_fingerprint`** al manifest de 3.368 decisiones pre-ejecutadas del historical source artifact **11389331836**. **No convertir los resultados finales en señales de predicción**.

### 3.1 Pérdida absoluta (G2, porque hay libro de resultados y join completos)
- **1.637** settled trades perdedores, **1.731** ganadores.
- Gross loss total **USD942.631,9691**; gross profit **USD1.614.167,9759**, final USD671.596,0068 desde USD60 (reconciliado).
- ATTACK: **860** trades / **442** losers / GL **USD941.071,8523** (~**99,834%** de toda pérdida); los ganadores ATTACK también producen ~USD1.612.367 de profit bruto, por lo que cortar ATTACK masivo mata el techo.
- MEDIUM: **2.508** trades / **1.195** losers / GL **USD1.560,1168** (~0,166%); MEDIUM no explica la cola grande en USD, pero sí la peor caída porcentual cuando la cuenta es pequeña.
- Los **20** perdedores más grandes sumaron **USD457.209,57**, **48,50%** del GL; **100** concentran ~**89,17%**, **200** ~**99,33%**. La concentración se debe al crecimiento compuesto y altos niveles de riesgo; no sirve para excluir retrospectivamente ganadores y perdedores.
- Pérdidas individuales superiores a USD50k aparecen en 2022 con multiplicador 10.000x; hay señales de riesgo inicial casi igual a pérdida final, más costes/spread. Evitar stops mágicos imposibles y analizar exposición inicial, margin/slippage y costos.
- **ATTACK ≥8.000x** produjo enormes pérdidas pero también **~USD566.966** en ganancia bruta en G2: no desactivar por regla global.

### 3.2 Último carrier forense automatizado `em-s06745`
El pipeline independiente [run 37762140239](https://github.com/mezas3238-hue/qore-core/actions/runs/37762140239), artifact **11542074171**, descarga con digest verificado el artifact **11542321736** y ejecuta `scripts/cibo_loss_tail_forensics.py`. **PASS**, 3.368/3.368, GL recalculada exacta contra ledger, beneficio bruto + neto reconciliados, top20/50/100/200 y top10 DD episodios.

- **20 peores pérdidas = 48,716336158% del GL**, ~USD458.146 de USD940.436.
- Esos 20 trades tenían en conjunto stop-risk inicial ~USD442k y provider costs ~USD23k: por ende no basta reducir spreads; investigar **riesgo económico precomprometido** y stops posibles POST entrada.
- En este carrier los **10 peores DD históricos siguen por encima de 22%**.
- `attack_sovereign_breach_usd=0`; pero `sovereign_floor_breach_usd=85.41649567391081325466487569` (**ANOMALÍA NO RESUELTA**). `ending_sovereign_bank_usd ≈ -46.7267`. Verificar semántica y reconciliación del banco antes de certificar. NO transferir automáticamente esos números a otro carrier sin medir.

### 3.3 Top diez episodios DD para `em-s06745` — por PORCENTAJE, no por USD

**Nota:** fechas de episodios son solo etiquetas de auditoría hindsight; PROHIBIDO usar `fecha==2020` como disparador. La compresión de pérdida calculada supone peak de equity sin cambio y es solo intuición matemática; no asegura que un nuevo replay conserve peaks.

| Rank | Peak → trough observado | DD observado | Equity peak ~USD | Pérdida peak→trough ~USD | Ahorro requerido para DD22% con peak fijo |
|---:|---|---:|---:|---:|---:|
| 1 | 2019-07-19 → 2019-08-12 | **36,911%** | 79,76 | 29,44 | ~11,89 |
| 2 | 2020-04-03 → 2020-05-13 | **36,693%** | 720,98 | 264,55 | ~105,93 |
| 3 | 2020-06-24 → 2020-06-30 | **36,413%** | 4.288,72 | 1.561,64 | ~618,12 |
| 4 | 2020-08-19 → 2020-09-28 | **34,737%** | 12.541,29 | 4.356,47 | ~1.597,39 |
| 5 | 2021-02-09 → 2021-03-03 | **33,151%** | 62.653,34 | 20.770,08 | ~6.986,35 |
| 6 | 2020-01-31 → 2020-03-06 | 33,150% | 119,38 | 39,57 | ~13,31 |
| 7 | 2020-03-23 → 2020-03-26 | 32,185% | 577,82 | 185,97 | ~58,85 |
| 8 | 2020-05-21 → 2020-06-08 | 30,818% | 1.225,67 | 377,73 | ~108,08 |
| 9 | 2019-11-04 → 2019-12-11 | 30,153% | 96,25 | 29,02 | ~7,85 |
| 10 | 2019-09-24 → 2019-10-14 | 25,639% | 83,51 | 21,41 | ~3,04 |

El episodio 2019 tuvo **75 settlements en ventana de drawdown, 51 negativos, 24 ganadores**, net aproximadamente −USD30 (según G2), y TODAS son MEDIUM; más decisiones fueron registradas cerca del período pero liquidaron fuera de la ventana: **80 decisiones** no deben confundirse con **75 settlements**. Varias pérdidas −USD2 a −USD3 arruinan por porcentaje una cuenta de capital USD80. Es un **cluster de stop en capital bootstrap**, NO problema de 10.000x ATTACK ni simplemente de coste transaccional.

Después de mejorar 2019, el máximo DD **migra** a episodios ATTACK de 2020 y 2021. Diseñar **protección multi-época y multi-mode**. Para entrar en DD≤25%, hay que revisar TODOS los episodios restantes que exceden 25%. Para ideal20%, hay que seguir comprimiendo y comprobar el nuevo ranking recalculado en cada replay.

### 3.4 Riesgo y contexto causal: hipótesis, NO certezas predictivas
El join completo encontró en ATTACK ≥4.000x, 230 trades: escenario M5 volatility `compressed` con PF histórico ~1,08 vs `balanced` ~2,23; muestra estratificación de contexto, NO prueba causal. Objetivo proyectado bucket `q5:>2.5` tuvo PF~2,65 en 2021 (n8) pero PF~0,23 en 2022 (n21, 18 losers): fuerte inestabilidad de régimen; los años NO pueden funcionar como disparadores.

En MEDIUM, condición `M5 efficiency low + H1 compressed` activa más de 800 casos en corpus y **tiene PF >1**, de modo que filtrarla globalmente corta también winners. Señales `projected R <=0.5 + H1 compressed` registran PF<1 en general, pero apenas 4 operaciones coinciden con el episodio más profundo 2019; ni un oracle que elimine todas sus pérdidas arregla la caída de 11,89 USD requerida para 22%.

Ausencia de contexto: ~15/80 decisiones MEDIUM del episodio 2019 no tenían M5/H1/H4 completos y ~185/860 ATTACK en histórico no tienen contexto completo. Se necesita telemetría de cobertura y fallback causal, jamás reconstruir datos ausentes desde el futuro.

**Alerta de provenance:** los **3.368/3.368** registros históricos 2019–2022 tienen `market_predecision_state.provider_observation.observed_at=2026-10-01`. Puede ser un único snapshot estático del broker/contract/cost model usado retrospectivamente, **NO constituye por sí solo prueba de alpha lookahead**; sin embargo, no puede declararse observación contemporánea de 2019. Clasificar y excluir explícitamente ese timestamp de cualquier feature causal histórica que no corresponda; documentar supuestos de fees, margin, spread y compararlos con supuestos realistas en la certificación.

# 4. SISTEMAS DE CIBO Y QUÉ HACE CADA UNO

`Trader signal/entry → CIBO recepción incondicional → Sizing → CIBO Compound → Portfolio Compound → Adaptive Leverage → lifecycle causal → settlement/ledger → nueva decisión`.

Componentes:
- `src/qore/infrastructure/trader_lab/cibo_three_mode_capital_lab.py`: replay económico, state/ledger, capital, ventanas, exposición, attribution, y medición.
- `scripts/cibo_trader_lab_three_mode_ceiling.py`: CLI y runner, parámetros de política, proveniencia/datos de replay.
- `src/qore/infrastructure/cibo_position_lifecycle.py`: post-entry lifecycle de protección, stops parciales, timing M5 closed-bar, protecciones ATTACK/MEDIUM.
- `scripts/cibo_loss_tail_forensics.py`: nuevo auditor reproducible de pérdidas, rentabilidad, riesgos de stop, coste y top10 drawdowns.
- `.github/workflows/cibo-all-loss-forensics-g5.yml`: workflow auditor, digest del artefacto congelado, test exacto del PnL y DD.
- `.github/workflows/cibo-trader-lab-loss-tail-causal-exposure-g5.yml`: nine-case G5 post-entry risk threshold test, ya terminado negativo.
- `.github/workflows/cibo-trader-lab-carrier36509-medium-m1-micro-ridge.yml`: replay del nuevo DD36,4423%, 12 casos completos y comparador.
- `.github/workflows/cibo-trader-lab-carrier37082-medium-extreme-boundary-ridge.yml` y `...carrier36914-medium-extreme-microcliff-ridge.yml`: bases de alta riqueza/bajas pérdidas.

Sensores / engineering report: expected-R/confidence previa, regímenes H4/H1/M5, projected open stop risk, racha de pérdidas ya liquidadas, balance y max high-water DD, entry→exit, stop-risk, costos, MFE/MAE temporal, exposure/correlation, conteo de `binds` por ventanas W1..W7 y W8 si opera, allocators, profit factor y gross loss por multiplier, Trader y modo.

**Prohibido desactivar el grupo económico completo o permitir que Sizing/Leverage rechacen trades para bajar artificialmente DD.** CIBO debe administrar TODAS las entradas, incluso en contextos adversos, bajo las restricciones financieras reales del entorno.

# 5. COSAS QUE NO VOLVER A HACER / EXPERIMENTOS NEGATIVOS VALIOSOS

1. Barridos ciegos: modificar parámetros unos 0,0005 en un carrier sin investigar el mecanismo genera mejoras ~0,003pp que no eliminan caídas estructurales de 10–15pp.
2. Stops post-entry duros generalizados: G3/G4 y otros intentos muestran que más `stop` puede arruinar beneficios compuestos y aumentar DD por cambios de trayectoria/recuperación.
3. Demotion global de ATTACK o limitar 10.000x indiscriminadamente: capital y PF muchas veces se destruyen. Cada protección ha de demostrar ahorro de loss **y** preservación de winners.
4. `G5` risktaker gate basado solo en thresholds de projected-open-stop-risk `0.03..0.15`: todos = **DD36,9105% sin mejoría**, wealth −USD1.343,68, GL +USD1.343,68. Se sabe que NO basta. Rechazar/archivar, salvo nueva hipótesis realmente distinta.
5. Narrow/two-band/triggered/rescue DD budgets sobre otro carrier: muchas variantes producen USD <582k (hasta USD~1k), aunque dan métricas DD menores; en especial DD 35,83797% con capital USD1.294,76 **NO** cumple.
6. Fecha, Trader o símbolos de los peores trades **no** son predicados válidos. Pueden citarse en informe forense, no usarse como whitelist de entradas/rechazos.
7. Replays que terminan `SUCCESS` sin `STRICT_PARETO_CASES` nunca deben promocionarse.
8. No usar la última columna de DD sola para cambiar `best`: preservar y comparar la frontera `DD, capital, GL total, ATTACK GL, PF, 3368 entries, breach, causalidad`.
9. No reusar un supuesto `sovereign_floor_breach_usd=0` de ATTACK: analizar y corregir el banco soberano.
10. No fusionar ramas de distintos arquitectos ni reemplazar su workflow cuando están generando investigaciones simultáneas.

# 6. PROGRAMA INMEDIATO DEL SIGUIENTE ARQUITECTO — SIN PERDER TIEMPO

## Paso 0 — DESCUBRIR ESTADO REAL DE GITHUB (OBLIGATORIO)
Abrir `agent/cibo-causal-expectation-leakage-fix-001` y `agent/cibo-loss-tail-causal-exposure-g5-001`; comprobar HEAD actual, últimos runs completados y artefactos/rankings. El corte de este handoff NO prevalece sobre evidence nueva. Distinguir `m1-2900` (DD récord observado 36.442% sin strict local) de `m1-2925` (strict local 36.459%) y `em-s06745` (capital y pérdida mejores). Seleccionar un **control EXACTO reproducible** para cada hipótesis, no mezclar parámetros de configuraciones que nunca se probaron juntas.

## Paso 1 — AUDITAR TODAS LAS 3.368 OPERACIONES + TODAS LAS GRANDES PÉRDIDAS
Leer el archivo forense maestro (referencia §3) y el output del auditor `11542074171`. Producir `Loss Cause Atlas` completo, por **1.637 perdedores / 1.731 ganadores** en el G2 y volver a medir para nuevo carrier:
- Causa: `stop-risk` inicial, costos broker, gap/slippage vs stop, barras M5 durante MAE/MFE, duración, estrategia cognitiva, spread, liquidación forzada, correlación, posición simultánea, exposición conjunta, bootstrap.
- Identificar a qué DD epoch perteneció cada pérdida **por settlement**; clasificar si impacta gross loss absoluto, drawdown%, ambos o ninguno.
- Para cada gran perdedor, buscar **winning controls** emparejados por mercado/régimen, expected-R predecisión, multiplier, stop-risk, tipo de señal y estado de cartera ANTES de la entrada. Realizar ablation/simulación sin mirar future outcome a la hora de decidir.
- Medir ganancias perdidas de cada defensa, no solo pérdidas ahorradas.
- Resolver el dato anómalo de provider observation 2026-10-01 aplicado a 2019–2022 para costes, margen y causalidad.

## Paso 2 — TOP-TEN DD EPISODES + riesgo disponible en vivo
- Reconstruir `peak state → stop-risk de posiciones abiertas → cada entrada admitida → settlement → trough`.
- Identificar clusters `loss-streak`, pérdidas simultáneas same-market y correlacionadas, coste del proveedor, intensidad de reinversión, rearm de riesgo después de gains, ventanas activas.
- Definir un **DD headroom** causal respecto a HIGH-WATER MARK. Si 25% tolerable, pérdida económica total no puede superar 25% del máximo sin recuperar valor; si 20% ideal, 20%. Pero **una regla de stops teórica no garantiza** el DD bajo gaps/slippage/no fill. Modelar a posteriori **peores shocks aún abiertos** con incertidumbre realista, no hard clamp que falsea replay.
- Evaluar cómo las políticas afectan simultáneamente 2019 MEDIUM y 2020–2021 ATTACK. Evitar arreglar un único episodio y mover la pérdida a otro.

## Paso 3 — Inventar defensa SELECTIVA y CAUSAL de riesgo/stop
Prioridades:
1. **Portfolio occupancy / riesgo abierto:** telemetría de riesgo de stop vigente + nueva posición + posiciones correlacionadas, context-specific post-entry capital management. No prohibir entrada del Trader. Ajustar tamaño/exposición/stop tras la ejecución solo dentro de capacidades reales.
2. **Early loss containment por M5 closed-bar**: a partir de excursión adversa observable/fracaso recuperación/horizonte; mitigar stop de perdedores sin cortar ganadores. Reconocer límites de fills, spreads, gaps y comisiones.
3. **Bootstrap MEDIUM 1x:** con capital inicial USD60–100 ya no se puede reducir a <1x sin violentar el marco; mejorar administración post-entry de pérdidas encadenadas y recuperación sin cerrar de forma masiva.
4. **Cost-aware ATTACK**: pérdidas >USD5k, especialmente ciclos de reinversión; preservar winners grandes 5.000x–10.000x dentro de simulación y corregir inflación de loss de provider cost.
5. **Ablar motores económicos** conjuntamente: Sizing, Leverage, CIBO Compound y Portfolio Compound, para identificar quién crea riesgo y quién lo controla. Medir delta final neto de cada uno, no desactivar sin conocer externalidades.

Cada propuesta debe llevar trazabilidad de "por qué este contexto era observable antes", conteo `binds`, coste en ganancias, ahorro en pérdidas, impacto multi-epoch y sensibilidad temporal. **Primero prueba causal offline/walk-forward; luego replay único; después pequeñas variaciones justificadas.**

## Paso 4 — CICLO DE TRADER LAB (REPETIR SIN DETENERSE)
- Rama nueva aislada. No tocar rama del otro arquitecto.
- Tomar fuente HEAD/artefactos pinneados `SHA256` y obtener full 3-year replay con 3.368 trades.
- Control del ganador EXACTO y variante nueva deben compartir TODO salvo una sola hipótesis.
- Workflow de investigación debe correr en GitHub Trader Lab, preferiblemente usando mejoras UltraFast **comprobadas y sin invalidar caching/digest**; el usuario considera 5–11 minutos por trabajo demasiado lento. Registrar tiempo total de cache hit, fetch, replay, ranking, artifact; optimizar sobre trabajo medido, NO omitir gates para afirmar “ultrafast”.
- Leer output **JSON por caso**, no solo pantalla SUCCESS. Validar: número, capital, DD, GL total, ATTACK GL, gross profit, PF, peak/trough DD, gates soberanos, zero reject/defer, causal step provenance, estado de todos los motores.
- Ejecutar auditor de pérdidas y comparar top10, no solo DD1; comparar trade deltas para ganadores/perdedores.
- Cambiar de candidato SOLO si pasa condiciones multiobjetivo y no empeora los problemas de contabilidad.
- Guardar commit, runID, artifact ID, parámetros, control, resultado negativo/positivo, efectos y conclusión.

## Paso 5 — HITOS DD Y REGLA DE PROMOCIÓN
Escalones de investigación: `36% → 35% → 32% → 30% → 27,5% → 25% → 22% → 20%`. Un hito DD sin conservar economía es **solo un hallazgo**, NO promoción.
- Piso antiguo: capital final ≥ USD582.440,03.
- Preservación del **techo real**: idealmente no caer frente a la mejor frontera de USD673,2k; mantener un tablero de Pareto cuando hay tradeoffs pequeños, **nunca** desplazar la opción económica superior sin reporte explícito.
- Gross loss total y ATTACK no aumentar contra el control de promoción. Beneficio bruto y PF con checks explícitos.
- 3.368/3.368 entradas, cero rejection/defer, cero ATTACK sovereign breach, causalidad sin outcome leakage.
- Para certificación, `sovereign_floor_breach_usd` también debe ser **cero o haber sido formalmente reconciliado con prueba irrefutable** y pasar las auditorías de capital.
- Confirmación a 20% ideal, 25% tolerable; 22% como meta operativa más agresiva. **No afirmar que DD<25% garantiza un 25% hard cap en cuentas live**.

# 7. QUÉ FALTA PARA CERTIFICAR CIBO — BATERÍA CIENTÍFICA COMPLETA

**CIBO AÚN NO ESTÁ CERTIFICADO.** Conseguir 20–25% DD es condición de diseño, no evidencia suficiente de seguridad de producción. La secuencia es:

1. **Cerrar las pérdidas estructurales y DD**: máximo tolerable DD≤25%, ideal≤20%, control multi-regime, capital y GL defendidos. Pasar replay completo 3.368 entradas, registrar PF, gross profit y maxDD.
2. **Congelar la policy y source**: parámetros, modelos cognitivos, confident/expected-R, lifecycle, pesos de cada motor, no ajuste sobre el futuro; SHA del commit, hashes de manifests, SHA256 de artefactos, seeds, reproducibilidad bit a bit o explicar variación.
3. **Contabilidad y fondos soberanos — P0**: corregir/reconciliar `sovereign_floor_breach_usd~85.416` observado en `em-s06745`; validar `ending_sovereign_bank_usd~−46.7267`, ledger, provenance de cada USD, reservas, releases, recycling, misma suma de Portfolio/CIBO/Sovereign, cero double-spend/duplication, cero silent source creation; comparador `attack_sovereign_breach_usd` independiente.
4. **Temporal/causal data provenance**: congelar M5/H1/H4 histórica con closed-bar only, broker provider observation 2026-10-01 modelado estático, no filtrar futuro, no contaminación por respuesta del final de trade, documentación de dataset 3.368 y trade fill provenance.
5. **Ablation científica**: probar cada uno Sizing, Leverage, CIBO Compound, Portfolio Compound, cognitiva/expectation, ventanas DD, shocks, lifecycle y interacciones. Demostrar aporte y ausencia de lógica decorativa/contradictoria; conservar entradas.
6. **Robustez de régimen/tiempo**: chronological fold, walk-forward, períodos y activos separados, extremidades 2019/2020/2021/2022; anti-overfitting y no selección ex-post de fechas/trader.
7. **Monte Carlo y riesgo de ruina**: orden temporal compatible con causalidad, cluster/shock de pérdidas, distribuciones p05 capital, p95 drawdown, duration underwater, time-to-recovery, probabilidad ruin y sensib. al max gap.
8. **Stress costes y ejecución**: x2 fees, spread, slippage, gaps, errores de fills, latencia, profundidad, margin, lotaje y broker; documentar claramente qué 10.000x es simulación teórica, límites concretos MT5/funded account requieren verificación, no prometer ejecución.
9. **Concentración de resultados**: quitar 1–3 mejores ganadores; stress sin top3; por Trader, símbolo, régimen, same-symbol overlap, correlación, gross-loss clusters. Portafolio no puede depender de un único ganador fuera de mercado.
10. **Resilience/failure engineering**: reinicios, duplicate events, reservation duplicates, stale snapshot, lectura incompleta del mercado, desconexión VPS/broker, partial settlement, crash de ledger, reconcilia y recovery, idempotency, zero open work al cierre y kill switches. Sin pérdida de autoridad de Trader ni capital ficticio.
11. **Forward qualification** con gates predefinidos, sin reajuste oportunista por cada racha, telemetría completa y períodos independientes.
12. **Fresh sealed 3-year out-of-sample**: nunca usarlo para tuning; descongelar SOLO tras policy freeze; reportar replicabilidad/estabilidad, y si falla, reabrir investigación con nueva segregación científica.
13. **Rescue Exam**: escenarios de capital/reservas en crisis, MAE severa, clustering stop, high-water DD, restarts.
14. **Final Integrated Exam** de CIBO + Traders + Shared con sus versiones científicamente congeladas y coordinación real; reexplorar el techo integrado si cambia el ecosistema y luego volver a comprimir DD.
15. **World Cup / Maximum Capability Exam** como examen adicional de capacidad máxima y seguridad, no sustituto de robustez estadística.
16. **Preproduction VPS/MT5**: reconciliación fills/fees/slippage/broker, tamaño permitido, dry-run/shadow/permissions, fallback; no prometer ganancias ni movilizar capital real sin aceptación expresa de riesgos y conformidad regulatoria.

Resultado de certificación debe incluir gráficos y tablas de todos estos ensayos, no únicamente un equity curve con capital final.

# 8. TRADER LAB ULTRAFAST Y CONCURRENCIA — ESTADO / RIESGOS

- El usuario exige **laboratorio muy rápido (ideal segundos)**; muchos trabajos anteriores tardaban 5 a 11 min. Existen otros arquitectos trabajando en ramas `agent/cibo-trader-lab-ultrafast-...` y `agent/cibo-ultrafast-rank-artifact-integrity-001`.
- Hay comprobaciones `QORE CIBO Trader Lab Runtime Audit` con SUCCESS recientes, pero también `Zero Open Work Gate` con FAILURE y experimentos de cache fallidos; **NO afirmar** "todo Trader Lab ultrafast reparado" sin analizar causas de estos failures y medir p50/p95 exactos con cache hit/miss, artifact upload y cold start.
- Algunos replays grandes combinan múltiples jobs simultáneos; no inferir que el runner está colgado por falta de logs hasta verificar steps/progreso/tiempos de descarga y compute.
- Prioridad fiabilidad: no contaminar ranking si falla descarga o digest, no aceptar missing artifacts, no convertir resultados incompletos en wins. Verificar determinismo de inputs y cache keyed por content hash, modo temporal, policy version, baseline, metrics schema.
- El auditor loss-forensics independiente primero falló por comparar DD como porcentaje redondeado a 28 dígitos con representación original de 100 dígitos; se arregló y PASÓ en [run 37762140239](https://github.com/mezas3238-hue/qore-core/actions/runs/37762140239). Este incidente ilustra que precision/canonical serialization y baseline parity deben definirse explícitamente.

# 9. INVENTARIO DE REFERENCIAS Y EVIDENCIA (NO SUPRIMIR)

**Continuidad histórica completa:**
- [Handoff anterior](https://github.com/mezas3238-hue/qore-core/blob/agent/cibo-causal-expectation-leakage-fix-001/docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_TRUE_CEILING_DD_AND_ATTACK_LOSS_COMPRESSION.md) (947 líneas al 08-Oct; quedó desactualizado al carrier 38,4621 pero incluye matriz de certificación/historia).
- [Informe completo 3.368 operaciones / pérdidas y contexto](https://github.com/mezas3238-hue/qore-core/blob/agent/cibo-complete-loss-forensics-3368-h1-001/docs/research/CIBO_MASTER_LOSS_FORENSICS_3368_2026-10-08.md), revisión `d99ea36776aca53279a962713216ddd80d385343`.
- [Informe G5 de diez episodios, riesgo, ejecución y auditor](https://github.com/mezas3238-hue/qore-core/blob/agent/cibo-loss-tail-causal-exposure-g5-001/docs/research/CIBO_G5_ALL_LOSS_EPISODES_EXPOSURE_HEADROOM_2026-10-08.md).
- [Auditor automático SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/37762140239), artefacto `11542074171`.
- [G1 mejora ocho ventanas](https://github.com/mezas3238-hue/qore-core/actions/runs/37738207384); [G2 MEDIUM](https://github.com/mezas3238-hue/qore-core/actions/runs/37756517100); [G3 negativo](https://github.com/mezas3238-hue/qore-core/actions/runs/37757591148); [G4 negativo](https://github.com/mezas3238-hue/qore-core/actions/runs/37757768704); [G5 negativo](https://github.com/mezas3238-hue/qore-core/actions/runs/37761586870).
- [`ex-s070` riqueza máxima observada](https://github.com/mezas3238-hue/qore-core/actions/runs/37759331934); [`em-s06745` buena frontera capital/GL](https://github.com/mezas3238-hue/qore-core/actions/runs/37759974174); [`m1-2900` DD36,4423 y `m1-2925` strict local](https://github.com/mezas3238-hue/qore-core/actions/runs/37762724394).

**Insumos técnicos:** source artifact `11451743578`; historical full decision manifest artifact `11389331836`; historical control artifact `11409086692`; G2 replay artifact `11541140276`; carrier em-s06745 artifact `11542321736`; M1 result artifact `11542304451`; full loss audit artifact `11542074171`. Se debe conservar **SHA256 y provenance** de los artefactos usados en cada replay; consultar el workflow exacto para los checksums.

**Ramas que contienen trabajos concretos sin pisarse:**
- `agent/cibo-riskshield-additive-window8-g1-001`
- `agent/cibo-riskshield-medium-bootstrap-g2-001`
- `agent/cibo-riskshield-medium-micro-g3-001`
- `agent/cibo-riskshield-bootstrap-initial-stop-g4-001`
- `agent/cibo-loss-tail-causal-exposure-g5-001`
- `agent/cibo-complete-loss-forensics-3368-h1-001`
- `agent/cibo-causal-expectation-leakage-fix-001` (otro arquitecto)
- `agent/cibo-master-continuity-handoff-20261008-dd-forensics-001` (ESTE DOCUMENTO solamente).

# 10. FRASE DE ARRANQUE PARA EL SIGUIENTE ARQUITECTO

> «Retoma CIBO en GitHub `mezas3238-hue/qore-core` leyendo primero `docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-08_36P44_DD_20PCT_IDEAL_25PCT_MAX_LOSS_FORENSICS.md` de la rama `agent/cibo-master-continuity-handoff-20261008-dd-forensics-001`, junto al handoff anterior del 07-Oct y el informe de 3.368 pérdidas. Comprueba los HEAD y últimos runs GitHub antes de declarar nueva cifra. El dueño exige preservar todas las 3.368 entradas, no permitir que CIBO las rechace, y reducir el drawdown **≤25% máximo tolerable, ≤20% ideal** (22% como meta interna intermedia) sin degradar techo/capital compuesto ni aumentar pérdidas brutas. El suelo histórico congelado es USD582.440,0253 desde USD60, pero la mejor frontera ya exhibe capital >USD673k. El menor DD observado es m1-2900 **36,442285% con USD671.094,90 y GL957.756,43** (NO Pareto estricto local); m1-2925 **36,459072% con USD671.077,45 y GL957.746,54** (sí strict local); em-s06745 **36,910539% con USD673.146,53 y GL940.435,76** (mejor capital+gross loss); ex-s070 **37,081762% con USD673.214,64** (más capital). Analiza causas de TODAS las pérdidas y TODOS los episodios, riesgo abierto/compounding y winners no sacrificados, programa defensa causal POSTENTRADA por estado económico, replay de 3 años y STRICT PARETO; no usar fechas/símbolos/IDs de perdedores como filtro. G5 umbral projected risk falló (run 37761586870), archivado. Antes de certificar, corregir `sovereign_floor_breach_usd` ~85,42 (em-s06745), broker provider observation con timestamp 2026 sobre 2019–2022, holds de datos, ablations cuatro motores, temporal/Monte Carlo/fees/execution, resilience, fresh sealed 3-year OOS y batería científica integrada. No tocar la rama de trabajo del otro arquitecto. CIBO NO CERTIFICADO». 

# 11. RESUMEN FINAL PARA DECISIONES

**Trabajos terminados:** investigación de compuesto y techo económico, mitigación inicial DD65→38→37→36, octava ventana G1, micro G2, G3/G4 negativos documentados, G5 negativo completo, análisis de TODAS las 3.368 entradas y grandes pérdidas, join con manifest causal, auditor automático independiente PASS, nuevos carriers 36,44/36,46 y frontera rica de USD673k, handoff actualizado.

**Falta:** reducción profunda multi-episodio hasta ≤25%/ideal≤20%; defender techo >USD673k preferiblemente sin degradarlo; implementación causal nueva con prueba fuerte y sin cortar winners; corregir soberano y provider-cost provenance; certificación científica de todo el sistema y holdout sellado. 

**NO CLAIMS:** no hay prueba de que DD≤25% se haya alcanzado, no hay aprobación de VPS/MT5 live, ni garantía de ganancias, ni que 10.000x de simulación sea ejecutable real, ni evidencia de que el nuevo DD 36,4423 implique automáticamente la mejor rentabilidad o menores pérdidas. La investigación continúa y cada siguiente replay debe estar medido y publicado.

