# QORE CORE — CIBO MASTER CONTINUITY HANDOFF

## MAXIMUM CEILING DISCOVERY · HISTORICAL MECHANICS TRANSFER · FULL NATIVE COGNITION · CONTROLLED DRAWDOWN

**Owner / CEO:** Sergio Meza  
**Repositorio fuente de verdad:** `mezas3238-hue/qore-core`  
**Branch de trabajo:** `agent/cibo-causal-expectation-leakage-fix-001`  
**HEAD técnico inmediatamente anterior a este handoff:** `c953d38b13026b0b4a0198724d3690c054a93420`  
**Último Trader Lab verificado:** run `37593219576` — SUCCESS  
**Artifact:** `11469243731`  
**Artifact digest:** `sha256:30dc29ce7fc8f9ef8c7b7a1dd557e85bdb93ca468a677e344c9b61e0a6fce892`

---

# 0. DIRECTIVA SOBERANA — LEER ANTES DE TOCAR CÓDIGO

Este handoff sustituye resúmenes parciales anteriores para esta línea de investigación.

La misión NO es "llegar a 8.000% y detenerse".

## 8.000% NO ES EL TECHO

El **+8.000% en aproximadamente 36 meses** es sólo una **base mínima de referencia de ceiling discovery**.

Desde USD 60, +8.000% equivale aproximadamente a USD 4.860 de capital final.

Pero **USD 4.860 NO es el objetivo final ni un cap artificial**.

La misión real es:

> **DESCUBRIR LA MÁXIMA ALTITUD ECONÓMICA REAL DE CIBO, Y DONDE CORRESPONDA DE SHARED, SIN IMPONER UN TECHO PREVIO, MANTENIENDO EL DRAWDOWN TOTAL CONTROLADO EN UN MÁXIMO DE 20–25%.**

Ejemplos ilustrativos, NO targets codificados:

- +10.000%
- +20.000%
- +50.000%
- o cualquier cifra superior que el edge, la cognitiva y la economía causalmente permitan.

El siguiente arquitecto NO debe detener investigación porque se alcance 8.000%.

**8.000% es piso de ambición para 36 meses, no techo.**

El techo debe descubrirse empíricamente.

El drawdown máximo tolerado durante ceiling discovery debe quedar **≤25%**. El corredor de estrés deseado es aproximadamente **20–25% máximo**. Un DD menor es válido si no se está sacrificando innecesariamente el ceiling.

---

# 1. MÉTODO DE TRABAJO OBLIGATORIO

Existe un banco de prueba rápido en GitHub:

## Trader Lab

Workflow:

`.github/workflows/cibo-trader-lab-three-mode-ceiling.yml`

Motor:

`src/qore/infrastructure/trader_lab/cibo_three_mode_capital_lab.py`

Runner:

`scripts/cibo_trader_lab_three_mode_ceiling.py`

Tests:

`tests/infrastructure/trader_lab/test_cibo_three_mode_capital_lab.py`

La superficie canónica de replay tiene:

- 3.368 decisiones/oportunidades
- 3.305 decision epochs
- ventana histórica aproximada: 1 julio 2019 → 29 junio 2022
- aproximadamente 36 meses
- capital inicial: USD 60

Artifact canónico full walk-forward:

- artifact `11451743578`
- digest `sha256:d439957f21e2f79148b5a2fb75a53db6fa448698f17aeb6978f379ed3547f7ea`

El Trader Lab es el banco de prueba de iteración.

## Ciclo obligatorio del siguiente arquitecto

No quedarse escribiendo teoría.

No esperar workflows soberanos largos para cada hipótesis.

Trabajar así:

1. detectar un cuello concreto;
2. reparar UNA capa causalmente identificable;
3. lanzar Trader Lab;
4. esperar a que ese replay termine;
5. leer logs + artifact + sensores;
6. comparar capital, DD, densidad, MEDIUM, ATTACK y attribution;
7. conservar sólo lo que mejora el frontier;
8. reparar la siguiente capa;
9. volver a lanzar replay;
10. repetir sin detenerse hasta encontrar una configuración favorable y luego seguir subiendo el ceiling.

La directiva del owner es literalmente:

> **TRABAJAR → PROBAR → LEER RESULTADOS → REPARAR → PROBAR OTRA VEZ. NO DETENERSE.**

El core matemático del replay es de segundos. GitHub Actions puede añadir overhead de infraestructura, pero no se debe usar ese overhead como excusa para pausar investigación.

No usar VPS para esta línea salvo orden explícita del owner.

No tocar LIVE.

No mutar el runtime soberano como parte de una hipótesis de ceiling antes de que la mecánica esté estabilizada en Trader Lab.

---

# 2. OBJETIVO ECONÓMICO SOBERANO

CIBO debe utilizar conjuntamente:

1. BANK
2. Sizing
3. CIBO Compound
4. Compound Portfolio
5. Adaptive Leverage para ATTACK
6. la cognitiva Native completa de CIBO

La arquitectura actual es mejor que el control histórico porque las funciones económicas ya pueden trabajar a partir de cognitiva.

La investigación NO debe degradar esa ventaja.

## BANK

BANK es tesorería/seeder.

BANK NO es un trader.

BANK NO debe consumir oportunidades como si fuera un mode final de operación.

Regla congelada:

- seed dinámico por entrada MEDIUM = 4% del capital actual
- USD 60 → envelope indicativo USD 2,40 por entrada
- USD 600 → envelope indicativo USD 24 por entrada
- múltiples entradas válidas pueden tener envelopes independientes sujetos a capital físico real

La corrección crucial ya realizada:

> **el 4% es seed/provenance/working-capital trigger; NO debe volver a ser un hard cap que exija que todo stop risk + provider cost quepa dentro del 4% antes de permitir que Sizing trabaje.**

## Sizing + CIBO Compound

Son el motor principal de MEDIUM.

Sizing debe convertir:

- capacidad actual
- riesgo
- margen
- provider geometry
- Native cognition
- Portfolio state
- provenance

en exposición executable.

CIBO Compound liquida MEDIUM, recicla capital y produce nueva capacidad.

## Compound Portfolio

Debe:

- acumular la parte de beneficio destinada a Portfolio;
- preservar una reserva reutilizable;
- decidir cuándo una oportunidad merece escalamiento ATTACK;
- no convertirse en un filtro que mata el flujo completo;
- no agotar todo el cushion en uno o pocos eventos;
- medir la contribución incremental real de ATTACK.

## Adaptive Leverage

Sólo actúa después de que Portfolio habilita ATTACK.

No debe inventarse un cap marginal interno que reemplace a Portfolio.

Portfolio es autoridad económica de ATTACK.

Adaptive Leverage transforma el capital liberado en multiplicador físicamente executable bajo:

- provider capacity
- risk capacity
- margin capacity
- capital disponible

---

# 3. COGNITIVA — REGLA CENTRAL

El control histórico consiguió aproximadamente USD 60 → USD 1.141,71 (~+1.803%) con una arquitectura previa a la integración cognitiva moderna que estamos intentando explotar ahora.

El sistema actual tiene una superficie Native mucho más rica.

El full walk-forward ya posee sensores por decisión:

- NATIVE_PERCEPTION
- MISSION_DIRECTOR
- FUNCTIONAL_COORDINATOR
- CF01–CF19
- WORLD_MODEL
- ATTENTION_CONTEXT
- REASONING_ROUTING
- CALIBRATION
- SCENARIO_ENGINE
- CAUSAL_REASONING
- METACOGNITION
- COGNITIVE_INTEGRATION
- EXECUTIVE_SYNTHESIS

Por eso la economía nueva NO debe operar con un simple booleano aislado.

La cognitiva debe servir para determinar tratamiento e intensidad:

- DEFER
- DEFENSIVE / MINIMUM
- MEDIUM
- STRONG MEDIUM
- ATTACK-ELIGIBLE

sin usar outcome futuro.

## Invariante

Las 3.368 oportunidades deben ser **trabajadas** por la economía.

"Trabajada" no significa que todas deban recibir capital.

Puede significar:

- analizada;
- diferida causalmente;
- tratada defensivamente;
- ejecutada MEDIUM;
- escalada ATTACK.

Lo prohibido es que desaparezcan silenciosamente antes de que la economía las procese.

---

# 4. CONTROL HISTÓRICO — REFERENCIA QUE NO SE DEBE PERDER

Branch histórica:

`agent/cibo-ceiling-retry-001`

Commit:

`0dd651d26134a6f7e052c06b46e3aef25b9f25a6`

Workflow histórico:

`.github/workflows/cibo-sovereign-ceiling-economic-retry.yml`

Run:

`37452573311` — SUCCESS

Artifact:

`11409086692`

Digest:

`sha256:eeffdc99a736b82bd965ff646b8ca9bf084f50ae414e56e9b3d82961169d7187`

Frozen input:

`11389331836`

Input digest:

`sha256:30177639f660c9647ab70257c2d12c541bdade49ab5582347a3890f920070fee`

Resultados históricos:

- capital inicial: USD 60
- final: USD 1.141,7060488
- peak: USD 1.168,4669670
- net: +USD 1.081,7060488
- crecimiento: aproximadamente +1.803%
- settlements: 1.216
- winners: 537
- losers: 679
- win rate: ~44,16%
- gross gains: ~USD 4.329,90
- gross losses: ~USD 2.912,64
- provider costs: ~USD 335,55
- max DD reconstruido: ~20,1%

No es certificación.

Es control de ceiling.

## Mecánica histórica recuperada

El sizing histórico real usaba `CAPABILITY_MAXIMUM`.

Ley central:

```python
total_loss_per_volume = stop_loss_per_volume + provider_cost_per_volume_usd
by_risk = hard_risk_headroom / total_loss_per_volume
by_margin = margin_headroom / margin_per_volume
raw = min(by_risk, by_margin, opportunity.maximum_volume)
steps = floor(raw / volume_step)
volume = steps * volume_step
```

Es decir:

> **máxima capacidad step-aligned dentro de riesgo + margen + broker/provider max.**

La arquitectura luego reducía esa capacidad mediante:

Executive Brain  
→ Full Economic Twin  
→ GEN-C11  
→ Portfolio / Adaptive Leverage  
→ competition  
→ Sizing / Compound  
→ CIBO CMA  
→ QORE Risk

El concepto que se debe preservar es:

> **CAPITAL → GANANCIA REALIZADA → NUEVA CAPACIDAD → NUEVA GANANCIA → NUEVA CAPACIDAD**

No copiar ciegamente:

- 100x margin-capacity de research
- riesgo extremo permitido por la antigua demo
- protected_capital=0
- 4x-or-0 como lenguaje final
- dependencia de un outlier XAU
- cualquier bypass de Compound o Portfolio

---

# 5. TRABAJOS REALIZADOS EN ESTA ETAPA

## 5.1 Se verificó y reactivó Trader Lab

Se forzó un replay puramente operativo sin cambiar reglas económicas:

Commit:

`4b3ae6bd2644818fe5779221e56845da56a7e651`

Run:

`37566741667` — SUCCESS

Artifact:

`11458799314`

Digest:

`sha256:e0c3ec4b85d328c69dd7beb6e29aafcb453ad1dae91e1d558332474828f1f0d0`

Ese replay confirmó que el banco de prueba estaba otra vez operativo.

Baseline de ese momento:

- 3.368 oportunidades
- 1.804 filtradas antes de economía
- 1.564 admitidas
- Sizing evaluó 1.332
- aprobó 117
- rechazó 1.215
- MEDIUM 117
- ATTACK 4
- capital final USD 102,30
- DD 15,34%

Problema identificado:

- filtro upstream por `context_allowed`
- expected edge positivo
- seed 4% usado como hard exposure cap

## 5.2 Se eliminó el descarte upstream artificial

Commit:

`13b61be1cd64089752ca9c1b545bf8aeb0542acf`

Cambio principal:

- `context_allowed` y positive-edge dejaron de ser admission gates
- las oportunidades con provider capacity >0 entran a economía
- seed 4% dejó de ser cap directo del multiplier
- se introdujo intensidad Native inicial

Replay:

`37567690333` — SUCCESS

Artifact:

`11459890825`

Resultado:

- 3.368 / 3.368 llegan a economía
- upstream filtered = 0
- final trades = 245
- capital final = USD 64,45
- DD = 28,24%
- ATTACK = 0
- Sizing rechazó 2.635

Conclusión:

> abrir intake era correcto, pero ejecutar demasiado MEDIUM sin reconstruir la autoridad de capital histórica drenaba Sovereign.

## 5.3 Se detectó la asimetría contable de MEDIUM

Con reparto positivo 50/50:

- ganancias positivas: 50% Sovereign / 50% Portfolio
- pérdidas MEDIUM: 100% Sovereign

Si se obliga demasiada densidad sin recuperación previa de pérdidas, Sovereign se drena.

No inventar un reparto de pérdidas nuevo sin directiva del owner.

La respuesta implementada en la lane histórica fue recuperar primero pérdida/deficit antes de dividir nueva producción positiva.

Commit clave:

`008bb505c47781fae91bf3871438295ba6bee3bc`

Mensaje:

`exp(trader-lab): split Compound net production after loss recovery`

## 5.4 Se cargó superficie Native completa

Commit:

`19b281acd4cbde6dd5bb70ef507f662405ac4f00`

Mensaje:

`feat(trader-lab): load full Native cognitive intensity profile`

El runner ahora extrae del full replay:

- executive synthesis
- reasoning routing
- calibration
- confidence band
- scenarios
- metacognition
- attention
- Native maximum intelligence flag
- full semantics consumed

## 5.5 Se probó escalar MEDIUM directamente con confidence

Commit:

`7951032ca43ffd82b5f92cd2afc35769b3d4e448`

Resultado: destructivo.

Se revirtió inmediatamente:

`c44c7e8daef9edbaac48d00806ca7aafa97c0d34`

Mensaje:

`revert(trader-lab): keep Native confidence out of ordinary MEDIUM`

Lección:

> confidence NO debe inflar mecánicamente MEDIUM. Debe participar en selección, tratamiento, Portfolio y ATTACK de forma contextual.

## 5.6 Se recuperó revolving capital de Portfolio

Commit:

`b01864cc8ac7dddb3220a86d63b468ec6f52e628`

Mensaje:

`fix(trader-lab): recycle settled ATTACK capital in Portfolio Compound`

La reserva ATTACK deja de ser one-shot.

Al cerrar un ATTACK:

- principal reservado se libera
- PnL queda reflejado en cushion
- capital libre vuelve a quedar disponible

Esto produjo el mejor salto de crecimiento moderno observado hasta ahora.

Run:

`37569751093` — SUCCESS

Lane:

`HISTORICAL_PRIOR_NATIVE_TRANSFER`

Resultado:

- 3.368 admitidas a economía
- upstream filtered = 0
- Sizing rejected = 0
- Sizing deferred = 1.233
- MEDIUM = 1.554
- ATTACK = 92
- total trades = 1.646
- capital final = USD 478,7565
- Sovereign = USD 478,3676
- Portfolio = USD 0,3889
- max multiplier = 308x
- ATTACK sovereign breach = 0
- max DD = 49,57%

Esta configuración demostró potencia, pero NO es aceptable por drawdown.

## 5.7 Se diagnosticó ATTACK

Se descubrió:

- parte de ATTACK escalaba aun cuando current Native context-quality era ABSTAIN;
- Portfolio podía liberar demasiado cushion;
- multiplicadores de hasta 308x;
- el cushion se consumía casi completamente;
- el DD total explotaba.

Se introdujeron guardas de Native y drawdown.

Commit:

`c7a3b2fab24f4d8417a457820c20160c03f15aa3`

Mensaje:

`exp(trader-lab): gate ATTACK with Native context and drawdown reserve`

## 5.8 Se presupuestó ATTACK desde headroom de drawdown

Commit:

`f02c05293f8940999008a3d9bb850d817c2778ed`

Mensaje:

`exp(trader-lab): budget ATTACK from Portfolio drawdown headroom`

La intención correcta:

> no limitar ATTACK por utilidad marginal inventada, sino hacer que Portfolio libere sólo la cantidad compatible con el presupuesto de drawdown.

## 5.9 Se corrigió medición de drawdown

Commit:

`17701afccff0e3afefc336d860d2938516a184b7`

Mensaje:

`fix(trader-lab): measure drawdown against contemporaneous peak`

No medir DD contra un peak futuro.

Toda guardia debe usar sólo el peak conocido hasta ese instante.

## 5.10 Se reconstruyó MEDIUM alrededor del envelope histórico

Commits:

`59b984f7589f85d7d574e873ddf06a2e8599b5f3`  
`exp(trader-lab): restore historical MEDIUM risk envelope`

`63af094376deb978622078eef251fa73efe946c4`  
`exp(trader-lab): keep MEDIUM active with drawdown-scaled risk`

`2a04321994bc84b9f64c752292a4b55f5a519999`  
`exp(trader-lab): preserve minimum MEDIUM inside drawdown headroom`

La investigación intentó conservar MEDIUM activo sin reintroducir el antiguo filtro binario.

## 5.11 Current Native puede sobreescribir un defer histórico

Commit:

`3e52ed4d80f2b9ec3367540723253763d777005d`

Mensaje:

`exp(trader-lab): let current Native override historical defer`

Principio:

> el prior histórico es evidencia, no autoridad soberana sobre la cognitiva actual.

## 5.12 Se importaron receipts causales del sizing histórico

Commits:

`004bac44a6122d755a6a86a919373be796a1cd63`  
`feat(trader-lab): import causal historical sizing receipts`

`c80024222c76992821345f18d83ce5f2b570e520`  
`exp(trader-lab): size MEDIUM from historical causal risk prior`

`c953d38b13026b0b4a0198724d3690c054a93420`  
`chore(trader-lab): load historical control sizing receipts`

Objetivo:

> dejar de imitar el control histórico con reglas aproximadas y recuperar su envelope causal real, para después mejorarlo con Native actual.

---

# 6. ESTADO MÁS RECIENTE VERIFICADO

HEAD técnico antes de este handoff:

`c953d38b13026b0b4a0198724d3690c054a93420`

Run:

`37593219576` — SUCCESS

Artifact:

`11469243731`

Digest:

`sha256:30dc29ce7fc8f9ef8c7b7a1dd557e85bdb93ca468a677e344c9b61e0a6fce892`

## Lane CAUSAL_BASELINE_THREE_MODE

- capital final: USD 54,5759
- DD: 24,7999%
- MEDIUM: 36
- ATTACK: 1
- trades: 37
- max multiplier: 25
- upstream filtered: 0
- Sizing rejected: 0
- Sizing deferred: 2.843

## Lane HISTORICAL_PRIOR_NATIVE_TRANSFER

Estado más importante para continuidad:

- capital inicial: USD 60
- capital final: USD 61,2469435
- DD: 24,7794%
- MEDIUM: 151
- ATTACK: 1
- trades totales: 152
- Sizing rejected: 0
- Sizing deferred: 2.728
- upstream filtered: 0
- max multiplier: 21
- ATTACK sovereign breach: 0

Interpretación:

> El control de DD ya funciona demasiado bien, pero se pagó con una destrucción de densidad y crecimiento.

La frontera actual tiene dos extremos:

### Extremo A — potencia

`b01864c...`

- USD 478,76
- 1.646 trades
- 92 ATTACK
- DD 49,57%
- max multiplier 308x

Potente, pero inválido por DD.

### Extremo B — control

`c953d38...`

- USD 61,25
- 152 trades
- 1 ATTACK
- DD 24,78%

DD válido, pero casi sin crecimiento.

## La misión inmediata

> **Encontrar el frontier entre esos dos estados y luego superarlo.**

No volver al extremo A.

No quedarse en el extremo B.

---

# 7. PROBLEMAS ACTUALES

## P1 — exceso de DEFER

El último estado difiere 2.728 oportunidades en la lane histórica.

Eso es demasiada pasividad.

El objetivo NO es volver a ejecutar todo ciegamente.

El objetivo es que Native distinga:

- verdadero defer
- minimum defensive
- normal MEDIUM
- strong MEDIUM
- ATTACK candidate

con mucha más resolución.

## P2 — Portfolio se convirtió en cuello dominante

Último run, lane histórica:

- `COMPOUND_PORTFOLIO` blocked capital ≈ USD 5.769
- restriction count = 3.305

Portfolio está conservando el DD, pero estrangulando la capacidad.

Hay que convertir la guardia de DD de una pared binaria a una asignación dinámica.

## P3 — ATTACK está casi apagado

Última lane histórica:

- ATTACK = 1

Eso no sirve para descubrir techo.

Pero volver a 92 ATTACK con 308x tampoco sirve.

Necesitamos:

> **más ATTACK de alta calidad + menor capital por ATTACK + capacidad de reciclaje + re-escalado cuando el cushion crece.**

## P4 — current Native aún no está explotando toda su riqueza

Actualmente la economía ya consume más del profile Native que antes.

Pero todavía hay demasiada dependencia de:

- executive recommend/abstain
- confidence
- historical prior

El siguiente arquitecto debe aprovechar mejor:

- reasoning routing
- metacognition
- scenario abstention
- attention breadth
- regime
- volatility
- liquidity
- correlation
- path adversity
- expected capital time
- historical causal edge
- current expected edge

para formar una verdadera intensidad económica multidimensional.

## P5 — MEDIUM no ha recuperado todavía la curva histórica

El control viejo hizo 1.216 settlements y USD 1.141.

El estado actual DD-safe hace sólo 152 trades y USD 61.

Antes de buscar +8.000% o más, hay que conseguir que la nueva arquitectura con cognitiva:

1. iguale el mecanismo del control;
2. supere USD 1.141 con DD ≤25%;
3. siga escalando.

## P6 — no confundir "trabajar una oportunidad" con "ejecutarla"

Las 3.368 deben recibir tratamiento económico.

Eso NO obliga a 3.368 trades.

Un DEFER puede ser legítimo si está justificado por cognitiva y preserva capital para mejores oportunidades.

Lo que no se acepta es un filtro upstream ciego.

## P7 — no optimizar al outcome

Toda intensidad debe derivar sólo de evidencia disponible al decision_at.

Prohibido:

- usar PnL futuro
- usar post-entry path
- usar outcome
- usar knowledge de cuál trade gana

Toda mejora debe conservar causalidad.

---

# 8. SENSORES OBLIGATORIOS

Mantener y ampliar sensores para:

## Sizing

- capital antes
- seed recibido
- risk headroom
- margin headroom
- provider max
- Native profile
- prior histórico
- requested multiplier
- authorized multiplier
- reason de defer/reduction
- capital source
- provenance

## CIBO Compound

- PnL settlement
- recovery deficit antes
- recovery aplicado
- net new production
- split Sovereign / Portfolio
- capital reciclado
- turnover
- contribución acumulada

## Compound Portfolio

- cushion antes
- credit available
- drawdown headroom
- Native ATTACK grade
- release requested
- release approved
- withheld capital
- motivo de no ATTACK
- cushion después

## Adaptive Leverage

- provider cap
- risk cap
- margin cap
- Portfolio funding cap
- selected multiplier
- binding cap
- realized contribution ATTACK

## Métricas globales

- final capital
- peak capital
- net PnL
- DD
- MEDIUM count
- ATTACK count
- DEFER count
- physical non-executable count
- capital velocity
- turnover
- Portfolio utilization
- Sovereign utilization
- ATTACK PnL
- Compound PnL
- contribution per function
- profit generations
- survival / breach
- Sharpe
- Sortino
- expectancy
- profit factor

No declarar ceiling sin attribution.

---

# 9. PRÓXIMO TRABAJO — PRIORIDAD INMEDIATA

## Paso 1

Construir una política de intensidad Native más granular.

No usar un threshold único.

Una propuesta de investigación:

### DEFER

Sólo cuando convergen múltiples señales de debilidad:

- executive abstain
- metacognition insufficient
- scenarios abstained
- context ABSTAIN
- edge histórico/current negativo
- regime adverso

### MINIMUM / DEFENSIVE MEDIUM

Para señales mixtas.

Debe permitir que oportunidades "no ideales" sean trabajadas con capital pequeño cuando físicamente sea razonable.

### NORMAL MEDIUM

Native recommend + evidencia causal suficiente.

### STRONG MEDIUM

Recommend + alta consistencia de escenarios + buena calibration + velocidad de capital razonable.

### ATTACK ELIGIBLE

Sólo cuando:

- Portfolio tiene cushion;
- Native actual permite;
- context quality ALLOW;
- régimen permite;
- drawdown headroom permite;
- edge robusto causal;
- no se agota cushion.

## Paso 2

Reemplazar el hard drawdown wall con un **drawdown budget allocator**.

Ejemplo conceptual:

- DD bajo → Portfolio puede liberar mayor fracción
- DD acercándose a 20% → reduce release
- DD 20–25% → casi no abre ATTACK nuevo
- >25% → configuración inválida

Pero NO hardcodear una cifra sólo por intuición.

Probar varias curvas en Trader Lab.

## Paso 3

Mantener Portfolio revolving.

No volver a one-shot credit.

## Paso 4

Recuperar densidad de MEDIUM sin repetir el error de ejecutar todo a 1x.

Objetivo intermedio:

- subir de 151 MEDIUM hacia cientos / >1000
- sin exceder DD
- observar dónde reaparece el crecimiento compuesto

## Paso 5

Una vez superado el control histórico USD 1.141 con DD ≤25%, seguir subiendo.

NO detenerse.

Siguiente referencia:

- +8.000% = base mínima
- después seguir ceiling discovery sin límite artificial

---

# 10. ABLATIONS OBLIGATORIAS CUANDO HAYA UNA CONFIGURACIÓN PROMETEDORA

Comparar:

1. Full CIBO
2. sin Adaptive Leverage
3. sin adaptive Sizing
4. sin CIBO Compound
5. sin Compound Portfolio
6. sin Native economic cognition
7. sin profit recycling
8. sin ATTACK reserve
9. sin historical causal prior
10. combinaciones relevantes

El objetivo es saber quién realmente crea capital.

No aceptar una curva final donde no sepamos cuál función hizo el trabajo.

---

# 11. FRESH HOLDOUT — NO TODAVÍA

No abrir Fresh Holdout sólo porque una replay curve se vea bonita.

Primero:

1. reconstrucción estable;
2. sensores completos;
3. frontier capital/DD;
4. ablations;
5. ceiling discovery;
6. estabilidad paramétrica;
7. luego Fresh Holdout;
8. finalmente certificación.

---

# 12. REGLAS QUE NO DEBEN REGRESAR

PROHIBIDO volver a:

- filtrar 1.804 oportunidades antes de economía;
- usar `context_allowed` como admission gate global;
- usar expected edge >0 como admission gate global;
- usar 4% seed como hard exposure cap;
- convertir BANK en trader;
- hacer que ATTACK arriesgue Sovereign;
- eliminar revolving Portfolio;
- escalar MEDIUM directamente sólo porque confidence sea alto;
- usar outcome futuro;
- usar una cifra objetivo como techo artificial;
- confundir ceiling research con certificación.

---

# 13. CONDICIÓN DE ÉXITO DEL SIGUIENTE ARQUITECTO

No es "hacer un commit".

No es "pasar tests".

No es "llegar a 8.000%".

El éxito es demostrar un frontier causal donde:

- 3.368 / 3.368 oportunidades reciben tratamiento económico;
- upstream discard = 0 salvo imposibilidad física real;
- BANK sigue siendo treasury;
- Sizing + Compound hacen el trabajo principal de MEDIUM;
- Portfolio acumula y recicla capital;
- ATTACK funciona con frecuencia suficiente;
- ATTACK no invade Sovereign;
- DD total ≤25%;
- capital supera el control histórico;
- luego supera +8.000%;
- y la investigación continúa hasta descubrir el techo real.

## Techo abierto

Si la arquitectura permite:

- +10.000%
- +20.000%
- +50.000%
- o más

con causalidad y DD ≤25%, continuar.

**NO DETENERSE EN 8.000%.**

---

# 14. FRASE DE CONTINUIDAD PARA EL NUEVO CHAT

Copiar al nuevo arquitecto:

> Repositorio `mezas3238-hue/qore-core`, branch `agent/cibo-causal-expectation-leakage-fix-001`. Leer íntegramente `docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_MAXIMUM_CEILING_DISCOVERY.md` y continuar desde el HEAD indicado allí. Usar GitHub Trader Lab como banco de prueba rápido. Ciclo obligatorio: reparar → replay → leer sensores → reparar → replay. +8.000% en 36 meses es sólo la base mínima de referencia, NO el techo. Descubrir la máxima altitud real de CIBO/Shared con drawdown total ≤25%, sin límite artificial de rentabilidad.

---

# 15. RESUMEN EJECUTIVO FINAL

La investigación ya resolvió el problema de intake: 3.368/3.368 llegan a economía.

También demostró que:

- abrir todo sin autoridad de capital destruye Sovereign;
- Native confidence no debe inflar MEDIUM linealmente;
- revolving Portfolio aumenta potencia;
- ATTACK sin presupuesto de drawdown genera crecimiento pero DD inaceptable;
- hard guarding del DD controla riesgo pero mata densidad y crecimiento;
- el próximo salto está en una asignación continua/inteligente de intensidad, no en filtros binarios.

El mejor crecimiento moderno observado hasta ahora fue aproximadamente:

**USD 60 → USD 478,76**, pero con **49,57% DD**.

El estado DD-safe más reciente quedó aproximadamente:

**USD 60 → USD 61,25**, con **24,78% DD**.

La misión del siguiente arquitecto es cerrar esa brecha y después superar ampliamente el control histórico de USD 1.141, continuar hacia +8.000% como base, y seguir hasta descubrir el techo real sin imponer un límite superior.

