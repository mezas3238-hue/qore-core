# QORE CORE — CIBO MASTER CONTINUITY HANDOFF

## TRUE CEILING FROZEN → STRICT-PARETO DD / GROSS-LOSS COMPRESSION → 20% IDEAL / 25% MAX TOLERABLE → SCIENTIFIC CERTIFICATION

**Owner / CEO:** Sergio Meza  
**Repositorio fuente de verdad:** mezas3238-hue/qore-core  
**Branch canónico:** agent/cibo-causal-expectation-leakage-fix-001  
**Documento canónico de continuidad:** docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_TRUE_CEILING_DD_AND_ATTACK_LOSS_COMPRESSION.md  
**HEAD inmediatamente anterior a este handoff:** f25888f76f6def9f702922f0f3dafabf5353f209  
**Capital inicial canónico:** USD 60  
**Holdout de investigación reutilizado:** 3.368 entradas / aproximadamente 36 meses  
**Estado:** investigación activa; CIBO NO está certificado  

---

# 0. DIRECTIVA SOBERANA — LEER ANTES DE TOCAR CÓDIGO

Este documento sustituye el estado operativo anterior del handoff y es la referencia de continuidad para el siguiente arquitecto.

La fase de búsqueda del techo ya no gobierna el trabajo. El **techo mínimo de referencia está congelado** y la prioridad absoluta ahora es:

> **REDUCIR EL DRAWDOWN HASTA EL MÁXIMO POSIBLE SIN DEGRADAR EL TECHO Y, EN PARALELO, REDUCIR DE FORMA SUSTANCIAL LA PÉRDIDA BRUTA.**

Objetivo de drawdown del Owner:

- **ideal: 20% o menor**;
- **tolerable como máximo: 25%**;
- **más de 25%: todavía no está en la zona objetivo**;
- 38%, 35%, 30% son solamente escalones intermedios, no metas finales.

No detenerse al romper 40%, 35% o 30%. El ciclo obligatorio continúa hasta llegar a <=25% si la arquitectura causal lo permite sin destruir el techo.

Reglas soberanas que NO se negocian:

1. El Trader decide y ejecuta la entrada. **CIBO no tiene potestad para rechazar la entrada del Trader.**
2. CIBO administra financieramente todas las entradas después de ejecutadas.
3. Deben mantenerse **3.368 / 3.368 entradas**.
4. Cero reject, defer o withheld financiero de Sizing.
5. Cero ATTACK sovereign breach.
6. SIZING + ADAPTIVE_LEVERAGE + CIBO_COMPOUND + COMPOUND_PORTFOLIO deben permanecer trabajando conjuntamente.
7. No usar outcome leakage ni información futura.
8. No hardcodear Traders concretos como defensa. El Trader culpable cambia entre episodios.
9. Toda mejora debe validarse mediante Trader Lab con replay causal.
10. La metodología obligatoria es:
   **forensics → hipótesis causal → modificación → replay → STRICT PARETO → conservar o rechazar → repetir**.

Una defensa que baja DD pero cae por debajo del techo congelado es **RECHAZADA como solución final**, aunque sea útil como evidencia forense.

---

# 1. BENCHMARK CONGELADO — SUELO ECONÓMICO QUE NO SE DEBE DEGRADAR

El benchmark congelado que gobierna la fase actual es:

- capital inicial: **USD 60**;
- capital final mínimo aceptable: **USD 582.440,0252953678696769360345**;
- ganancia total aproximada: **+970.633,38%**;
- max DD original: **65,1041975924%**;
- ATTACK cap del benchmark: **10.000x**;
- entradas: **3.368 / 3.368**;
- sovereign breach: **0**;
- total gross loss original: **USD 1.444.736,060362508738067914772**;
- ATTACK gross loss original: **USD 1.443.117,897425126985300959340**;
- ATTACK gross profit original: aproximadamente **USD 2.025.323,73**;
- total PF original: aproximadamente **1,40310478936**;
- ATTACK PF original: aproximadamente **1,403436**.

IMPORTANTE:

**USD 582.440,03 es el piso congelado de aceptación, no un techo absoluto metafísico.**  
Si una variante produce más capital y menor DD/loss, ese capital adicional se usa como headroom para seguir comprimiendo DD.

---

# 2. MEJOR ESTADO ACTUAL — NUEVO STRICT PARETO 38,4621%

El mejor candidato de investigación confirmado al momento de este handoff es:

## p30-cg600-1500-f95

Run decisivo: **37692116415 — SUCCESS**  
Workflow: **QORE CIBO Carrier39 P30 Capital-Gated Window6 Fast**  
Artifact: **11514255866**  
Digest: **sha256:552a31bc9cb44d2de27c04425dbab5d2379176ac0a774f04c3aa0a0e6b543a16**

Resultados exactos:

- capital final: **USD 668.085,9185341914931181005054**;
- ganancia total desde USD 60: aproximadamente **+1.113.376,53%**;
- max DD: **38,4621082823%**;
- total gross loss: **USD 960.833,3801149893950274727244**;
- ATTACK gross loss: **USD 959.269,4507748429533595932652**;
- total profit factor: **1,69525677642**;
- ATTACK profit factor: **1,69616846660**;
- entradas: **3.368 / 3.368**;
- all entries preserved: **true**;
- ATTACK sovereign breach: **0**.

Mejora contra el benchmark congelado:

- DD: **65,1042% → 38,4621%**;
- reducción absoluta de DD: **26,6421 puntos porcentuales**;
- reducción relativa importante, pero TODAVÍA insuficiente para el objetivo 20–25%;
- total gross loss: **USD 1.444.736,06 → USD 960.833,38**;
- reducción de total gross loss: **USD 483.902,68**, aproximadamente **-33,49%**;
- ATTACK gross loss: **USD 1.443.117,90 → USD 959.269,45**;
- reducción ATTACK gross loss: **USD 483.848,45**, aproximadamente **-33,53%**;
- capital final queda aproximadamente **USD 85.645,89 por encima** del suelo congelado.

Este es el **carrier principal de investigación** que debe usar el siguiente arquitecto salvo que encuentre en GitHub un commit posterior con un STRICT PARETO mejor.

NO llamar este resultado “certificado”. Todo esto sigue siendo investigación sobre holdout reutilizado.

---

# 3. PROGRESIÓN REAL DEL DRAWDOWN CONSEGUIDA

La trayectoria de compresión ya demuestra que el problema no es monolítico. Se ha ido desplazando de episodio en episodio:

| Etapa | Capital aprox. | Max DD | Lectura |
|---|---:|---:|---|
| benchmark congelado | 582.440 | 65,10% | punto de partida |
| primer band Pareto | 663.395 | 64,02% | 2.000–3.999x era destructivo |
| carrier DD selectivo | 687.903 | 51,15% | ventana 800–1.900x |
| segunda ventana | 689.841 | 48,37% | aparece piso bootstrap temprano |
| tercera ventana low-mult | 687.114 | 46,25% | 2–20x bajo DD |
| cuarta ventana high-mult | 688.634 | 44,05% | 4.800–5.200x |
| democión exacta 2x | 690.681 | 43,85% | sólo 2x, no 3x/4x |
| high-left window | 689.672 | 41,73% | fuga 4.4k–4.8k |
| expected-R partial | 667.465 | 40,0058% | piso MEDIUM casi roto |
| carrier39 | 667.459 | 39,6850% | 40% roto |
| capital-gated window6 | 668.086 | 39,1742% | 50–170x localizado |
| **p30 + capital-gated window6** | **668.086** | **38,4621%** | mejor actual |

La lección central:

> **Cada vez que se comprime un episodio dominante, el max DD migra a otro episodio distinto. Por tanto no existe una sola “perilla de DD”; hay que hacer forensics del nuevo máximo después de cada carrier aceptado.**

---

# 4. ARQUITECTURA EXACTA DEL CARRIER 38,4621%

La arquitectura que llevó al mejor carrier combina defensas causales localizadas, no un derisking global.

## Núcleo económico

- distributed ATTACK frontier;
- coordinated economic group;
- ceiling discovery mode de laboratorio;
- ATTACK cap base: 10.000x;
- MEDIUM cap: 14x;
- medium drawdown intensity trigger: 0,05;
- bootstrap cushion share: 1,00;
- growth leverage slope: 10;
- ATTACK single-trade risk fraction: 0,20;
- same-Trader ATTACK loss-streak trigger: 3;
- loss-streak taper: 0,75;
- Portfolio shock trigger: 0,05;
- Portfolio shock taper: 0,50;
- lifecycle base: DEFENSIVE_INITIAL_STOP_CAP;
- lifecycle base sólo MEDIUM 1x;
- defensive stop base: -0,20R;
- lifecycle Trader loss streak trigger: 2;
- lifecycle min stop-risk fraction trigger: 0,03.

## Capa selectiva por multiplier/risk

- ATTACK multiplier band 2.000–3.999x;
- taper fraction: 0,20;
- ATTACK risk-fraction band 0,025–0,05;
- taper fraction: 0,50.

## Ventanas DD causales acumuladas

Ventana 1:
- DD 0,10–0,30;
- multiplier 800–1.900x;
- taper 0,40.

Ventana 2:
- DD 0,10–0,35;
- multiplier 350–450x;
- taper 0,60.

Ventana 3:
- DD 0,15–0,50;
- multiplier 2–20x;
- taper 0,80.

Ventana 4:
- DD 0,15–0,50;
- multiplier 4.800–5.200x;
- taper 0,90.

Ventana 5:
- DD 0,10–0,50;
- multiplier 4.400–4.799x;
- taper 0,85.

## Democión causal muy estrecha

- low-multiplier demotion upper: **2x**;
- activa desde DD: **0,15**;
- democión 2x → MEDIUM 1x;
- ampliar a 3x/4x fue perjudicial y quedó rechazado.

## Bootstrap lifecycle causal con expected-R

- feature: ADVERSE_PARTIAL_REDUCTION;
- requiere expectativa causal disponible;
- expected-R ceiling: **0,10**;
- adverse loss cut: **-0,40R**;
- partial fraction: **0,30** en el mejor carrier;
- capital ceiling: **USD 100**;
- DD trigger: **0,10**;
- same-Trader loss streak trigger: **1**;
- MEDIUM max multiplier: **2**.

## Ventana 6 capital-gated — hallazgo más reciente

- DD: **0,05–0,45**;
- multiplier: **50–170x**;
- taper: **0,95**;
- capital floor: **USD 600**;
- capital ceiling: **USD 1.500**.

Esta última capa es importante porque el taper 50–170x global destruía capital; al limitarlo al episodio económico real, se volvió útil.

---

# 5. NUEVO MAX DRAWDOWN DEL CARRIER 38,4621% — PRIORIDAD P0 DEL SIGUIENTE ARQUITECTO

El max DD actual ya NO es el episodio ATTACK de 2020/2021.

Ahora el episodio dominante es **MEDIUM temprano**, en 2019.

Datos exactos:

- peak: **2019-07-19 06:45 UTC**;
- peak capital: **USD 79,7639386081**;
- trough: **2019-08-12 11:25 UTC**;
- trough capital: **USD 49,0850461704**;
- pérdida peak-to-trough: **USD 30,6788924377**;
- max DD: **38,4621082823%**;
- modo neto del episodio: **MEDIUM = -USD 30,6788924377**;
- ATTACK no domina este nuevo máximo;
- multiplier 1x net: aproximadamente **-USD 26,6207**;
- multiplier 2x net: aproximadamente **-USD 4,05815**.

Gross loss dentro del episodio por multiplier:

- 1x: aproximadamente **USD 48,3391**;
- 2x: aproximadamente **USD 4,05815**.

Atribución neta por Trader dentro del episodio:

- R43_GBPUSD: aproximadamente **-USD 10,001**;
- VT31_NAS100: aproximadamente **-USD 6,162**;
- R38_GBPJPY: aproximadamente **-USD 5,5097**;
- R42_AUDJPY: aproximadamente **-USD 5,1919**;
- R38_EURUSD: aproximadamente **-USD 2,254**;
- R34_XAUUSD: aproximadamente **-USD 1,758**;
- VT08_FOREX: aproximadamente **+USD 0,198**.

Esto demuestra otra vez por qué NO se debe blacklistar un Trader: el daño está distribuido y cambia con el episodio.

Estado del trough relevante:

- Sovereign bank: aproximadamente **USD 29,32**;
- Portfolio cushion: aproximadamente **USD 19,76**;
- open margin: 0;
- open stop risk: 0;
- el episodio termina por pérdida realizada, no por riesgo abierto pendiente.

Rachas en el trough:

- VT31: 7;
- R38_GBPJPY: 3;
- R42_AUDJPY: 3;
- R38_EURUSD: 1;
- otros variables.

## Conclusión forense P0

El próximo gran problema no se puede arreglar reduciendo multiplicador por debajo de 1x.  
**MEDIUM 1x ya está en la intensidad mínima permitida sin rechazar la entrada.**

Por tanto, para bajar de 38,46% hacia 25% hay que estudiar profundamente:

- lifecycle post-entry causal;
- partial reduction inteligente;
- expected-R / confidence previa a decisión;
- deterioro intratrade observable sólo con barras ya cerradas;
- same-Trader / portfolio loss state;
- duración underwater;
- recuperación parcial;
- riesgo de cerrar demasiado pronto trades que luego recuperan;
- diferencias entre direct-to-stop losers y posiciones que primero tuvieron excursión favorable;
- posibilidad de reducir cola negativa sin cortar winners.

NO repetir stops rígidos globales: ya se probó que destruyen compounding.

---

# 6. FORENSICS PROFUNDO OBLIGATORIO DEL DRAWDOWN

El Owner exige un estudio a profundidad de los factores que ocasionan DD. El siguiente arquitecto debe trabajar por episodios y construir un **atlas causal del drawdown**.

Para cada uno de los top 10 episodios de DD registrar, como mínimo:

## A. Estado económico antes de cada trade

- capital total;
- peak capital;
- drawdown vivo;
- Sovereign bank;
- Portfolio cushion;
- capital generation;
- recycled generation;
- reserved cushion;
- open margin;
- open stop risk;
- requested multiplier;
- approved multiplier;
- cap que hizo bind;
- risk fraction propuesta y aprobada;
- Compound state;
- Portfolio credit/release/recycle state.

## B. Estado causal del Trader

- Trader ID únicamente para atribución, no como regla fija;
- últimos 1/2/3/5 outcomes ya liquidados;
- same-Trader loss streak;
- rolling net PnL;
- rolling gross loss;
- rolling gross profit;
- rolling PF;
- shock magnitude;
- tiempo desde último shock;
- recuperación desde último shock;
- causal expected-R;
- causal confidence / dispersion;
- régimen;
- volatilidad;
- spread / liquidity state si está disponible.

## C. Estado cross-portfolio

- posiciones simultáneas;
- overlap de stop risk;
- clustering same asset;
- clustering cross asset;
- clustering same Trader;
- correlación de pérdidas;
- varias pérdidas liquidadas en ventana corta;
- si CIBO volvió a escalar antes de recuperar cushion.

## D. Lifecycle

Para cada gran perdedor:

- initial stop;
- MFE antes de pérdida;
- MAE;
- si alcanzó +0,25R / +0,5R / +1R;
- si cayó directo a stop;
- si hubo señal causal de deterioro previa al stop;
- cuánto habría ahorrado una partial reduction;
- cuánto profit futuro habría sacrificado;
- si el mismo patrón aparece en winners.

## E. Atribución de motores

Registrar cuál de los cuatro motores aportó a la intensidad económica:

- SIZING;
- ADAPTIVE_LEVERAGE;
- CIBO_COMPOUND;
- COMPOUND_PORTFOLIO.

No aceptar explicaciones del tipo “ATTACK perdió” sin identificar qué estado económico permitió el tamaño y por qué.

---

# 7. PÉRDIDA BRUTA — SEGUNDO OBJETIVO SOBERANO

El Owner pidió explícitamente reducir también la pérdida bruta.

Situación original:

- total gross loss: **USD 1.444.736,06**;
- ATTACK gross loss: **USD 1.443.117,90**.

Mejor carrier actual:

- total gross loss: **USD 960.833,38**;
- ATTACK gross loss: **USD 959.269,45**.

Reducción ya conseguida:

- total gross loss: aproximadamente **-33,49%**;
- ATTACK gross loss: aproximadamente **-33,53%**.

Esto es una mejora grande, pero **no se considera terminado**.

La meta no es minimizar gross loss a cualquier costo. Una defensa que corta USD 300k de pérdidas pero también destruye USD 500k de gross profit queda rechazada.

Siempre reportar simultáneamente:

- terminal capital;
- gross profit;
- gross loss;
- net;
- PF;
- max DD;
- número de trades;
- entradas preservadas;
- sovereign breach;
- binds de cada defensa.

---

# 8. DESCUBRIMIENTOS CAUSALES ACEPTADOS

## 8.1 Banda ATTACK 2.000–3.999x

Primer gran breakthrough post-ceiling.

Caso histórico decisivo:
- b2000-3999-f25;
- capital ~USD 663.394,79;
- DD ~64,02%;
- total GL ~USD 1.302.694,09.

Demostró que ciertas zonas de intensidad ATTACK son económicamente destructivas: reducirlas puede **subir capital y bajar pérdidas a la vez**.

## 8.2 Risk-fraction band 0,025–0,05

Mejoró capital y gross loss, aunque el DD bajó poco. Se conservó como bloque complementario.

## 8.3 Ventanas DD × multiplier

Hallazgo fundamental:

El derisking global mata compounding; las ventanas causales estrechas pueden comprimir episodios concretos.

Ventanas útiles descubiertas:

- 800–1.900x;
- 350–450x;
- 2–20x;
- 4.800–5.200x;
- 4.400–4.799x.

## 8.4 Democión exacta 2x

Demover sólo 2x durante DD fue útil.

Ampliar a 3x/4x fue demasiado agresivo.

## 8.5 Expected-R + adverse partial reduction

El gating causal por expected-R permitió reducir el piso MEDIUM sin destruir el capital.

El área útil es estrecha. Cambios agresivos en expected-R ceiling o partial fraction pueden romper la trayectoria.

## 8.6 Capital-gated sixth window

El rango 50–170x era destructivo sólo en un tramo de capital concreto.

Taper global 50–170x: RECHAZADO.  
Taper limitado a capital aproximadamente 600–1.500: ÚTIL.

Esto confirma que el **estado de capital debe formar parte de la causalidad de DD**, no sólo multiplier y live-DD.

---

# 9. HIPÓTESIS / DEFENSAS RECHAZADAS — NO REPETIR CIEGAMENTE

Quedan rechazadas como arquitectura final, aunque algunas sirvieron como evidencia:

- rechazar entradas;
- Sizing rejection / defer;
- fixed Trader blacklist;
- global ATTACK taper amplio;
- hard DD budget global desde peak;
- broad multiplier taper sin state gating;
- confidence-only global;
- stress-confidence global fuerte;
- Portfolio shock one-shot amplio;
- broad lifecycle stop compression;
- ATTACK-only adverse loss cut global;
- high-risk lifecycle post-entry global;
- democión low-multiplier amplia 10x/20x/50x/100x;
- democión 3x/4x;
- MEDIUM 1x lifecycle ampliado globalmente;
- bootstrap lifecycle stop rígido;
- ultra-tight MEDIUM stop;
- global 50–170x window6;
- 50–150x taper global;
- early-capital DD budgets que estrangulan el crecimiento;
- cualquier defensa que caiga por debajo de USD 582.440,03.

Patrón observado repetidamente:

> **Cuanto más global es la defensa, más fácil es bajar pérdida bruta y DD, pero mayor es el daño al compounding. La solución debe ser causal, localizada y reversible.**

---

# 10. TRADER LAB — BANCO OFICIAL DE PRUEBAS

El laboratorio de pérdidas + Drawdown está incorporado en Trader Lab de GitHub. No crear un laboratorio separado.

Core principal:

- src/qore/infrastructure/trader_lab/cibo_three_mode_capital_lab.py
- scripts/cibo_trader_lab_three_mode_ceiling.py
- src/qore/infrastructure/cibo_position_lifecycle.py

Trader Lab mide conjuntamente:

- terminal capital;
- max DD;
- total gross loss;
- ATTACK gross loss;
- total PF;
- ATTACK PF;
- entradas 3.368/3.368;
- rejection/defer;
- sovereign breach;
- drawdown attribution;
- multiplier attribution;
- Trader attribution;
- lifecycle;
- causal expectation;
- confidence;
- binds de ventanas y risk controls;
- engineering trace;
- trade receipts;
- epoch receipts.

Capacidades añadidas durante esta fase:

- multiplier-band taper;
- risk-fraction-band taper;
- múltiples ventanas DD×multiplier;
- segunda/tercera/cuarta/quinta/sexta ventana causal;
- low-multiplier exact demotion;
- recent-Trader loss pressure;
- state-gated lifecycle override;
- distinct bootstrap lifecycle features;
- expected-R gating;
- peak/capital state gating;
- early-capital Trader shock;
- capital-band DD budget;
- full causal receipts;
- **capital floor/ceiling para window6**.

Últimas implementaciones relevantes:

- feat(cibo): capital-gate sixth causal DD multiplier window  
  commit **67ee5aecd64c887c4a556669070c09cdffd5667f**
- cli(cibo): expose capital-gated sixth DD window  
  commit **3b9db9ff7e7a7601860490256aea3c7c81f71da5**
- exp(cibo): capital-gate 50x-170x defense on 39pct carrier  
  commit **ccb017f63f824e55c598b0f8a97ebaa982d34f63**
- exp(cibo): pair p30 MEDIUM floor with capital-gated window6  
  commit **339cf8747c6b73e724b59036c26be7c4cda5350d**
- exp(cibo): micro-gate 140x-150x ATTACK stress confidence  
  commit **f25888f76f6def9f702922f0f3dafabf5353f209**

Micro stress-confidence 140–150x no mejoró el carrier: los casos quedaron esencialmente iguales al base 39,685%. No priorizar esa línea salvo nueva evidencia.

---

# 11. RUNS CLAVE QUE EL SIGUIENTE ARQUITECTO DEBE CONOCER

Referencias recientes:

- 37662670595 — ATTACK Multiplier Band Frontier — primer gran STRICT PARETO.
- 37663346696 — ATTACK Risk-Fraction Band Frontier.
- 37663861074 — multiplier-band fine ridge.
- 37663937350 — Pareto band + DD compression.
- 37664970209 — residual DD multiplier window.
- 37665136328 — Band05 sub60 DD.
- 37665838598 — dual carrier residual DD.
- 37669012561 — dual carrier two DD windows.
- 37669404090 — recent Trader loss pressure.
- 37669717694 — MEDIUM1x DD defense — rechazado.
- 37669937494 — low-multiplier demotion.
- 37670103941 — sub40 bootstrap demotion.
- 37670289160 — layered sub40 ridge.
- 37670671920 — localized bootstrap MEDIUM defense.
- 37675317327 — bootstrap 46% fine ridge.
- 37675905414 — carrier46 fourth window.
- 37677062833 — exact2x demotion ridge.
- 37677997932 — high-left fifth window, 41,73%.
- 37683996926 — expected-R micro ridge.
- 37683815572 — peak-latched initial stop.
- 37684905114 — mid-low window6 global, evidencia de por qué hacía falta capital gating.
- 37689995899 — ultra-tight MEDIUM bootstrap stop — no solucionó el problema.
- 37691976414 — capital-gated window6, **39,1742%**.
- 37692116415 — p30 + capital-gated window6, **38,4621% BEST ACTUAL**.
- 37692140731 — micro stress-confidence — sin mejora.

---

# 12. PLAN INMEDIATO PARA BAJAR DE 38,46% A 25%

## P0 — Congelar carrier 38,4621% como baseline de investigación actual

No “certificarlo”. Usarlo como carrier para la siguiente forensia.

Guardar siempre:

- exact CLI;
- commit;
- run;
- artifact;
- digest;
- capital;
- DD;
- GL;
- PF;
- binds;
- entry preservation;
- breaches.

## P1 — Forensics profundo del episodio MEDIUM 2019

Ésta es la prioridad técnica inmediata.

Responder cuantitativamente:

1. ¿Cuántas de las pérdidas 1x/2x son direct-to-stop?
2. ¿Cuántas tuvieron MFE positiva antes de caer?
3. ¿Qué winners del mismo estado serían dañados por cada defensa?
4. ¿Expected-R separa losers de winners?
5. ¿Confidence/dispersion añade información incremental?
6. ¿Same-Trader streak ayuda o sólo llega tarde?
7. ¿El deterioro en barras M5 cerradas aparece con suficiente antelación?
8. ¿La partial reduction óptima debe ser 20%, 25%, 30% u otra?
9. ¿Hay una combinación causal de MFE + adverse bar + expected-R que reduzca pérdidas sin cerrar winners?
10. ¿El efecto depende del capital absoluto, peak capital o generation?
11. ¿R43/VT31/R42 aparecen porque son malos o sólo porque coinciden con ese régimen? No hardcodear ID.
12. ¿Se puede preservar recuperación dejando un “runner” tras partial reduction?

## P2 — Diseñar defensa MEDIUM 1x post-entry no destructiva

Restricción difícil:

1x ya es mínimo. No se puede bajar sizing sin rechazar o mutilar la entrada.

Por eso evaluar:

- conditional partial reduction;
- adverse excursion threshold;
- recovery-aware partial;
- profit-protected runner;
- time-underwater + expected-R;
- closed-bar deterioration;
- peak-capital/generation gating;
- causal regime gating;
- partial fraction adaptativa.

NO usar stop duro global.

## P3 — Recalcular atlas después de cada mejora

Cuando el DD 2019 deje de ser el máximo, inmediatamente identificar el nuevo episodio.

No seguir afinando un episodio que ya dejó de gobernar max DD.

## P4 — Escalones de control

Usar hitos intermedios:

- <38%;
- <35%;
- <32%;
- <30%;
- <27,5%;
- <=25%;
- ideal <=20%.

Pero NO congelar como meta ninguno de los escalones intermedios.

## P5 — Mantener gross loss bajo control

Cada reducción DD debe comprobar que no reintroduce pérdida bruta.

Objetivo: continuar por debajo de ~USD 960k total GL y seguir comprimiendo.

---

# 13. CRITERIO STRICT PARETO VIGENTE

Una variante es aceptable como nuevo carrier de investigación sólo si:

1. capital final >= **USD 582.440,0252953678696769360345**;
2. max DD mejora contra el carrier que se está intentando reemplazar;
3. total gross loss no se degrada materialmente y, preferiblemente, mejora;
4. ATTACK gross loss no se degrada materialmente;
5. 3.368 / 3.368 entradas;
6. zero Sizing rejection;
7. zero Sizing deferral;
8. zero ATTACK sovereign breach;
9. reglas causales;
10. zero outcome leakage;
11. ninguna alteración a la autoridad del Trader para entrar.

Para la fase final de DD:

> **20% es ideal. 25% es máximo tolerable.**

Una solución de 26% sigue sin cumplir la directiva final.

---

# 14. QUÉ FALTA PARA CERTIFICAR CIBO

CIBO sigue NO CERTIFICADO.

Llegar a 20–25% DD es condición necesaria de arquitectura, pero no suficiente para certificación.

Después de cerrar DD/gross-loss engineering todavía falta:

## A. Freeze de arquitectura

- congelar policy;
- congelar parámetros;
- congelar calibration;
- congelar expected-R/confidence models;
- hash/commit reproducible;
- documentar toda autoridad económica.

## B. Accounting / provenance / conservation

Demostrar formalmente:

- conservación de capital;
- provenance de cada dólar;
- cero double counting;
- cero double spend;
- reservations correctas;
- releases correctos;
- recycling correcto;
- reconciliación Sovereign/Portfolio/Compound;
- semántica de Sovereign negativo si existe;
- invariantes de generations.

## C. Ablations

Ablar individual y conjuntamente:

- SIZING;
- ADAPTIVE_LEVERAGE;
- CIBO_COMPOUND;
- COMPOUND_PORTFOLIO;
- lifecycle;
- DD windows;
- expected-R;
- shock protection.

Demostrar qué aporta cada componente y que ninguno es decorativo.

## D. Robustez temporal

- chronological folds;
- walk-forward;
- temporal replication;
- diferentes regímenes;
- años/semestres separados;
- no depender de un solo periodo favorable.

## E. Monte Carlo / path stress

- reorder compatible con causalidad;
- Monte Carlo;
- loss clustering;
- tail stress;
- p05 PnL;
- p95 DD;
- probability positive;
- probability of ruin;
- recovery-time distribution.

## F. Cost / execution stress

- spread stress;
- slippage stress;
- cost x2;
- margin compression;
- provider constraints;
- latency si aplica;
- fill degradation.

## G. Concentration stress

- por Trader;
- por asset;
- por régimen;
- remover best 1 trade;
- remover best 2 trades;
- remover best 3 trades;
- burst losses;
- simultaneous correlation stress.

## H. Failure engineering

Hard invariants:

- ZERO DOUBLE-SPEND;
- ZERO DUPLICATE AUTHORITY;
- ZERO SILENT SOURCE CREATION;
- ZERO RELEASE BEFORE RECONCILIATION.

Probar:

- restart;
- duplicate event;
- duplicate reservation;
- partial settlement;
- ledger crash;
- reconciliation mismatch;
- stale snapshot;
- provider unavailable;
- concurrent allocation;
- idempotency;
- recovery after interruption.

## I. Forward qualification

- periodo forward separado;
- gates predefinidos;
- sin retune;
- observabilidad completa;
- zero-open al cierre.

## J. Fresh sealed OOS

Holdout protegido mencionado por governance:

**CIBO_USD60_6M_HOLDOUT_2017H1_V1**

NO abrirlo antes del freeze y prerequisites.

## K. Exámenes finales

Pendientes:

1. Worst-Trader Rescue Exam;
2. Final Integrated Certification Exam;
3. World Cup Maximum Capability Exam;
4. fresh OOS;
5. zero-open closure;
6. final certification candidate.

Cuando CIBO llegue al rango **20–25% DD**, debe entrar a la batería científica completa antes de declararlo certificado.

---

# 15. COSAS QUE EL SIGUIENTE ARQUITECTO NO DEBE HACER

- No volver a descubrir el ceiling desde cero.
- No tratar 8.000% como ceiling; era sólo base histórica.
- No degradar deliberadamente el capital por una cifra bonita de DD.
- No rechazar entradas.
- No quitar autoridad al Trader.
- No blacklistar R34, R42, R43, VT31 o cualquier Trader por identidad.
- No usar resultados futuros para decidir una entrada actual.
- No confundir reused holdout con certificación.
- No reabrir defensas globales ya rechazadas salvo que exista una hipótesis causal nueva.
- No optimizar sólo ATTACK: el max DD actual es MEDIUM 1–2x.
- No olvidar gross loss mientras baja DD.
- No apagar Compound/Portfolio/Leverage/Sizing para “resolver” riesgo.
- No declarar CIBO certificado por alcanzar un buen replay.

---

# 16. ARCHIVOS CLAVE

Motor de laboratorio:

- src/qore/infrastructure/trader_lab/cibo_three_mode_capital_lab.py
- scripts/cibo_trader_lab_three_mode_ceiling.py
- src/qore/infrastructure/cibo_position_lifecycle.py

Handoff canónico:

- docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_TRUE_CEILING_DD_AND_ATTACK_LOSS_COMPRESSION.md

Protocolos de certificación:

- docs/research/CIBO-FINAL-INTEGRATED-CERTIFICATION-EXAM-PROTOCOL-V1.md
- docs/research/CIBO-INTEGRATED-CERTIFICATION-SEQUENCE-AMENDMENT-V1.md
- docs/research/CIBO-USD60-6M-MAXIMUM-REAL-CAPABILITY-CERTIFICATION-V1.md
- docs/research/CIBO-WORST-TRADER-RESCUE-EXAM-CONTRACT-V1.md

Workflows recientes que contienen la arquitectura moderna:

- .github/workflows/cibo-trader-lab-carrier39-capital-gated-window6-fast.yml
- .github/workflows/cibo-trader-lab-carrier39-p30-capital-gated-window6-fast.yml
- .github/workflows/cibo-trader-lab-carrier39-micro-stress-confidence.yml
- .github/workflows/cibo-trader-lab-carrier40-midlow-window6-ridge.yml
- .github/workflows/cibo-trader-lab-carrier40-expected-r-micro-ridge.yml
- .github/workflows/cibo-trader-lab-carrier40-peak-latched-initial-stop.yml
- .github/workflows/cibo-trader-lab-carrier43-exact2x-demotion-ridge.yml
- .github/workflows/cibo-trader-lab-carrier43-high-left-fifth-window.yml
- .github/workflows/cibo-trader-lab-dual-carrier-two-dd-windows.yml

---

# 17. FRASE DE CONTINUIDAD PARA COPIAR AL SIGUIENTE CHAT

> Continuar CIBO en mezas3238-hue/qore-core, branch agent/cibo-causal-expectation-leakage-fix-001. Leer primero el handoff canónico docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_TRUE_CEILING_DD_AND_ATTACK_LOSS_COMPRESSION.md. El ceiling mínimo congelado es USD 582.440,03 desde USD 60. El mejor STRICT PARETO de investigación al cierre del handoff es p30-cg600-1500-f95, run 37692116415: USD 668.085,92, DD 38,4621%, total gross loss USD 960.833,38, ATTACK gross loss USD 959.269,45, PF total ~1,6953, 3.368/3.368, cero sovereign breach. La prioridad absoluta es seguir reduciendo DD sin degradar el ceiling; ideal <=20%, máximo tolerable <=25%. El max DD actual ya es MEDIUM 1–2x en julio–agosto de 2019, peak USD 79,76 → trough USD 49,09. Hacer forensics profundo de ese episodio y diseñar protección post-entry causal, no stop global. Seguir forensics → modificación → Trader Lab replay → STRICT PARETO → repetir. No certificar con reused holdout. Tras llegar a 20–25% ejecutar batería científica, accounting/provenance, ablations, Monte Carlo, stress, temporal replication, forward, fresh sealed OOS, Rescue Exam, Final Integrated Exam y World Cup Maximum Capability Exam.

---

# 18. RESUMEN EJECUTIVO FINAL

CIBO ya demostró que puede preservar las 3.368 entradas, mantener un techo superior al benchmark congelado y reducir simultáneamente DD y pérdida bruta.

Estado original:
- capital USD 582.440;
- DD 65,10%;
- gross loss USD 1,445M.

Estado actual:
- capital **USD 668.086**;
- DD **38,46%**;
- gross loss **USD 960,8k**.

La investigación ha eliminado aproximadamente:

- **26,64 puntos porcentuales de DD**;
- **USD 483,9k de gross loss**.

Pero la misión todavía NO está terminada.

El próximo arquitecto debe considerar **38,46% como un carrier intermedio**, no como éxito final.

**Objetivo soberano: ideal 20% DD; máximo tolerable 25%, sin degradar el ceiling.**

Cuando ese rango esté alcanzado de forma causal y reproducible, recién entonces congelar la arquitectura y someter CIBO a la batería científica de certificación.
