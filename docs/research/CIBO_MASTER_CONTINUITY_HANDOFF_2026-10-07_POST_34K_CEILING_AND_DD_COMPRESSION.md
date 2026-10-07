# QORE CORE — CIBO MASTER CONTINUITY HANDOFF

## POST-34K CEILING DISCOVERY → TRUE CEILING CLOSURE → DEEP DRAWDOWN FORENSICS → DD COMPRESSION WITHOUT CEILING DEGRADATION → CERTIFICATION

**Owner / CEO:** Sergio Meza  
**Repositorio fuente de verdad:** `mezas3238-hue/qore-core`  
**Branch canónico de CIBO:** `agent/cibo-causal-expectation-leakage-fix-001`  
**Fast Trader Lab branch:** `agent/github-trader-lab-001`  
**Capital inicial canónico:** USD 60  
**Ventana base de replay:** aproximadamente 36 meses, 2019-07-01 → 2022-06-29  
**Población canónica:** 3.368 entradas del Trader / 3.305 decision epochs  
**Estado del documento:** CONTINUIDAD SOBERANA / INVESTIGACIÓN / NO CERTIFICACIÓN

---

# 0. DIRECTIVA SOBERANA — LEER ANTES DE TOCAR CÓDIGO

Este documento sustituye como referencia de continuidad operativa los resúmenes parciales anteriores de esta línea.

La misión actual tiene DOS fases, en este orden:

1. **DESCUBRIR EL VERDADERO TECHO DE CIBO.**
2. **REDUCIR EL DRAWDOWN LO MÁXIMO POSIBLE SIN DEGRADAR ESE TECHO.**

El récord de aproximadamente **USD 34.019 desde USD 60 NO es el techo**.

El Owner corrigió expresamente cualquier interpretación que tratara USD 32k, USD 34k, +50.000% o cualquier cifra previamente observada como límite. Si una nueva arquitectura eleva el capital final sin empeorar materialmente el drawdown, significa que el ceiling todavía no fue encontrado.

Por tanto:

> **NO CONGELAR USD 34K COMO TECHO.**
>
> **SEGUIR INVESTIGANDO HASTA ENCONTRAR UNA MESETA / CLIFF / CAP FÍSICO-ECONÓMICO REAL.**

Después de descubrir ese techo verdadero, la prioridad absoluta pasa a ser:

> **COMPRIMIR DRAWDOWN HACIA 20–25% O MENOR SIN DEGRADAR EL TECHO DESCUBIERTO.**

No aceptar una “mejora” de drawdown que simplemente destruya la producción económica.

Ejemplo real ya observado:

- Portfolio DD Budget logró bajar DD hacia ~48,27%;
- pero redujo capital a ~USD 28.618;
- eso es científicamente interesante como defensa;
- pero **NO es aceptable como solución final si el ceiling vigente está por encima de USD 34k**.

La meta no es comprar DD bajo sacrificando la capacidad de CIBO.

---

# 1. REGLA SOBERANA DE AUTORIDAD — TRADER ENTRA, CIBO ADMINISTRA

Esta regla es absoluta.

## Trader

El Trader:

- identifica su setup;
- decide la entrada;
- ejecuta la entrada;
- NO tiene responsabilidad sobre la administración financiera posterior.

## CIBO

Una vez ejecutada la entrada:

- CIBO recibe la posición;
- CIBO administra capital, intensidad, compound, portfolio, leverage y lifecycle;
- CIBO NO puede rechazar, borrar, cancelar o convertir esa entrada en no-trade;
- CIBO NO puede usar BANK como eufemismo de rechazo;
- CIBO NO puede usar `DEFER`, `REJECT_ENTRY`, `BANK_NO_TRADE` o equivalentes como destino final de una entrada ya ejecutada.

CIBO sí puede:

- mantener la posición base;
- reducir únicamente exposición incremental;
- aplicar tratamiento defensivo;
- escalar MEDIUM;
- escalar ATTACK;
- proteger stop;
- hacer trailing;
- realizar parciales;
- extender target;
- liberar/reasignar capital;
- controlar Portfolio;
- controlar Adaptive Leverage;
- usar Compound;
- administrar lifecycle causal.

## Invariante del replay

La superficie actual debe conservar:

- oportunidades Trader: 3.368
- trades finales administrados: 3.368
- upstream filtered: 0
- Sizing rejected: 0
- Sizing deferred: 0
- Portfolio withheld before execution: 0

Toda hipótesis que reduzca DD eliminando entradas viola autoridad y queda rechazada.

---

# 2. REGLA ECONÓMICA — LOS CUATRO MOTORES DEBEN TRABAJAR JUNTOS

El Owner corrigió explícitamente una fase donde la investigación se concentraba demasiado en ATTACK.

Los cuatro motores económicos deben participar como grupo:

1. **Sizing**
2. **Adaptive Leverage**
3. **CIBO Compound**
4. **Compound Portfolio**

ATTACK es sólo una manifestación de escalamiento.

No se debe declarar mejora económica si:

- ATTACK hace todo el trabajo y Compound/Portfolio/Sizing quedan decorativos;
- Portfolio estrangula producción sin justificación;
- Sizing se convierte en admission gate;
- Adaptive Leverage suplanta autoridad del Portfolio;
- Compound no recicla capital;
- o cualquiera de los cuatro desaparece funcionalmente.

La arquitectura actual tiene handoff explícito:

`SIZING → CIBO_COMPOUND → COMPOUND_PORTFOLIO → ADAPTIVE_LEVERAGE`

---

# 3. 8.000% ES BASE, NO TECHO

El Owner corrigió esto múltiples veces.

**+8.000% significa GANANCIA TOTAL acumulada sobre USD 60, no “capital final = 8.000%”.**

Desde USD 60:

- +8.000% profit ≈ +USD 4.800;
- capital final ≈ USD 4.860.

Pero esa cifra era sólo la base mínima de ambición para ~36 meses.

No es cap.

Ejemplos como:

- +10.000%
- +20.000%
- +50.000%

son ilustrativos, no límites.

El replay ya demostró producción superior a +50.000%.

La investigación debe continuar hasta encontrar el techo real.

---

# 4. BANCO DE PRUEBA CANÓNICO

## Subject branch

`agent/cibo-causal-expectation-leakage-fix-001`

## Motor

`src/qore/infrastructure/trader_lab/cibo_three_mode_capital_lab.py`

## Runner

`scripts/cibo_trader_lab_three_mode_ceiling.py`

## Lifecycle causal

`src/qore/infrastructure/cibo_position_lifecycle.py`

## Fast bridge

`.github/workflows/cibo-trader-lab-fast-bridge.yml`

## Fast Trader Lab independiente

Branch:

`agent/github-trader-lab-001`

Profile:

`tools/github_trader_lab/profiles/cibo-three-mode-suite.json`

Suite:

`tools/github_trader_lab/suites/cibo-three-mode-current.json`

Adapter:

`tools/github_trader_lab/adapters/cibo_three_mode_suite_fast.py`

## Artifact fuente full walk-forward

- artifact: `11451743578`
- digest: `sha256:d439957f21e2f79148b5a2fb75a53db6fa448698f17aeb6978f379ed3547f7ea`

## Histórico Native source

- artifact: `11389331836`

## Histórico control

- artifact: `11409086692`

## Atlas M5

Se usan seis superficies causales:

- AUDJPY
- EURUSD
- GBPJPY
- GBPUSD
- NAS100
- XAUUSD

La regla causal es:

- observar barras cerradas;
- decisión en N;
- ejecución de acción a partir de N+1;
- cero outcome leakage;
- no usar exit futuro para inventar una salida defensiva.

---

# 5. BUCLE OPERATIVO OBLIGATORIO

Directiva del Owner:

> **MEJORAR → REPLAY → LEER SENSORES → REPARAR → REPLAY → REPETIR.**

No detenerse escribiendo teoría.

No esperar workflows largos si Fast Trader Lab puede responder la pregunta.

No hacer sweeps ciegos cuando una atribución causal puede reducir el espacio.

Cada iteración debe medir al menos:

- capital final;
- profit total;
- max DD;
- peak/trough del DD;
- DD por mode;
- DD por Trader;
- top negative settlements;
- ATTACK count;
- MEDIUM count;
- maximum multiplier;
- Sizing cap counts;
- Portfolio restrictions;
- Compound restrictions;
- Adaptive Leverage caps;
- all_entries_preserved;
- upstream filtered;
- rejected/deferred;
- Sovereign;
- Portfolio cushion;
- attack breach;
- capital recycled.

---

# 6. EVOLUCIÓN DEL CEILING — TRABAJOS Y DESCUBRIMIENTOS

## 6.1 Estado coordinado inicial

Con los cuatro motores económicos coordinados y 3.368/3.368 entradas:

- final ≈ USD 1.772;
- DD ≈ 51,13%.

Portfolio bootstrap 75% elevó a:

- final ≈ USD 1.811,80;
- DD ≈ 51,13%.

Ese benchmark ya está completamente superado como ceiling.

## 6.2 Techo bruto / growth staged

La investigación de crecimiento progresó por:

- fixed ceiling;
- growth-staged;
- upper;
- extreme;
- precision;
- exact ceiling.

La arquitectura growth-staged demostró que CIBO crece mucho más cuando el leverage económico escala con el capital en lugar de exponer el máximo desde el inicio.

Se observaron progresiones del orden de:

- ~USD 8.374;
- ~USD 12.833;
- ~USD 18.520;
- ~USD 23.956;
- ~USD 28.193.

El ridge exacto alrededor de 251x–259x encontró un máximo local bruto alrededor de:

- 257x;
- MEDIUM 14x;
- slope 10;
- final ≈ USD 28.337,59;
- DD bruto ≈ 86%.

Eso era un máximo local de la arquitectura sin las defensas posteriores, NO el techo definitivo de CIBO.

## 6.3 Single-ATTACK risk cap

Se introdujo un límite de riesgo por ATTACK individual.

Punto importante:

- single risk 8%:
  - final ≈ USD 23.868,56;
  - DD ≈ 59,70%.

Redujo DD de forma fuerte, pero sacrificó demasiado ceiling.

No es solución final.

## 6.4 Loss-streak taper

Se implementó taper causal después de rachas perdedoras ATTACK del mismo Trader.

No resolvió el problema por sí solo.

Sirvió como capa adicional, pero los DD seguían alrededor de 65–68% en variantes relevantes.

## 6.5 Selective MEDIUM protection

Se conectó lifecycle defensivo sólo a MEDIUM selectivo.

Resultados relevantes:

- ~USD 32.046,87 / DD ~52,72%;
- ~USD 32.638,27 / DD ~53,91%.

Este fue un salto muy importante porque demostró que **protección selectiva puede AUMENTAR el ceiling**, no sólo bajar riesgo.

Interpretación:

> evitar daño temprano puede dejar más capital vivo para Compound + Portfolio + Adaptive Leverage, aumentando el capital terminal.

## 6.6 MEDIUM Grade2

Se probó extender defensas a MEDIUM ≤2x.

Resultado:

- varias ramas destruyeron/exhausted la cuenta.

Conclusión:

> ampliar una defensa de forma indiscriminada puede matar compounding.

Rechazado.

## 6.7 Portfolio DD Budget

Se probó un presupuesto global de DD.

Punto útil:

- DD ≈ 48,27%;
- capital ≈ USD 28.618,51.

Esto demuestra que Portfolio puede bajar DD.

Pero degrada demasiado el ceiling frente a >USD 34k.

Por la directiva actual:

**RECHAZADO COMO SOLUCIÓN FINAL.**

## 6.8 Portfolio Shock Taper — NUEVO SALTO

Workflow:

`.github/workflows/cibo-trader-lab-portfolio-shock-taper-frontier.yml`

Run decisivo:

`37643372162` — SUCCESS

Artifact:

`11492589669`

Digest:

`sha256:f9f1aa247d35b532b2f4677470feb91874d71e2bc7d3b3154b20ceb190d02d7f`

La lógica:

- si el ATTACK inmediatamente anterior pierde al menos una fracción del capital pre-settlement;
- Portfolio reduce temporalmente el risk budget del siguiente ATTACK;
- no borra entrada;
- no apaga ATTACK;
- no usa outcome futuro;
- responde a un shock ya realizado.

### Nuevo récord

Variante:

`shock005-t050`

Parámetros principales:

- ATTACK cap: 257x;
- MEDIUM cap: 14x;
- MEDIUM live-DD intensity trigger: 5%;
- bootstrap cushion: 100%;
- growth slope: 10;
- single ATTACK risk fraction: 20%;
- ATTACK trader loss streak trigger: 3;
- ATTACK loss-streak taper: 75%;
- Portfolio shock trigger: 5%;
- Portfolio shock taper: 50%;
- lifecycle: DEFENSIVE_INITIAL_STOP_CAP;
- lifecycle defensivo MEDIUM 1x;
- stop defensivo: -0,20R;
- Trader loss-streak trigger: 2;
- minimum stop-risk fraction trigger: 3%.

Resultado:

- inicial: USD 60;
- final: **USD 34.019,19392799146**;
- ganancia total aproximada: **+56.598,66%**;
- max DD: **51,1604%**;
- ATTACK trades: **861**;
- max multiplier: 257x;
- shock taper binds: **53**;
- Sovereign final: aproximadamente **-USD 46,06**;
- Portfolio cushion: aproximadamente **USD 34.065,25**;
- all entries preserved: true;
- 3.368/3.368;
- no rejected;
- no deferred;
- no upstream filtering.

### Interpretación soberana

**USD 34k NO ES EL TECHO.**

La mejora de ~USD 32,6k a ~USD 34,0k ocurrió con DD todavía en la misma zona ~50–51%.

El Owner ordenó seguir buscando ceiling.

---

# 7. EVIDENCIA DE QUE USD 34K NO ES EL TECHO

En el caso `shock005-t050`:

- aproximadamente **804 ATTACK** quedaron limitados por `DISTRIBUTED_ATTACK_CAP`;
- aproximadamente **60 ATTACK** quedaron limitados por `CEILING_SINGLE_TRADE_RISK_CAP`;
- sólo ~2 se vieron limitados por cushion funding en la atribución observada.

Eso significa que aún hay una gran cantidad de decisiones que desean más intensidad económica pero están chocando con caps de investigación.

Además, el peor drawdown del caso USD 34k ocurre temprano:

- peak: ~USD 131,17;
- peak time: 2020-01-31;
- trough: ~USD 64,06;
- trough time: 2020-03-06;
- DD USD: ~67,11;
- DD fraction: ~51,16%.

En ese episodio los mayores ATTACK negativos usan multiplicadores pequeños/moderados:

- 3x;
- 7x;
- 20x;
- 11x;
- 4x;
- etc.

Esto es crucial:

> **el cap tardío 257x todavía NO determina el peor DD temprano.**

Con slope 10 y capital ~USD 131, el growth cap temprano está alrededor de ~21x.

Por eso existe una hipótesis muy fuerte:

> elevar el cap tardío por encima de 257x puede aumentar capital terminal SIN empeorar necesariamente el máximo DD temprano.

Esa hipótesis está actualmente bajo replay.

---

# 8. REPLAY DE CEILING ACTUALMENTE ABIERTO

Commit:

`25839c417c3876f375a02c4621b1acc52ca0c72f`

Mensaje:

`ci(trader-lab): extend shock-protected ceiling beyond 34k`

Workflow:

`QORE CIBO Shock Ceiling Expansion Fast`

Run:

`37644740113`

Objetivo:

probar la arquitectura ganadora de shock taper manteniendo:

- MEDIUM DD guard;
- lifecycle defensivo;
- Portfolio shock taper 5% / 50%;
- loss-streak taper;
- 3.368/3.368 entradas;
- Compound + Portfolio + Sizing + Adaptive Leverage activos;

y barrer:

- ATTACK cap: 257 / 275 / 300 / 325 / 350;
- single ATTACK risk: 20% / 22% / 24%;
- growth slope principal: 10;
- probes adicionales slope 11.

## Instrucción para el siguiente arquitecto

PRIMERA ACCIÓN:

1. verificar el estado final de `37644740113`;
2. descargar artifact;
3. ordenar casos por capital y DD;
4. identificar si alguno supera USD 34.019;
5. comprobar 3.368/3.368;
6. comprobar si el nuevo máximo DD sigue siendo el mismo episodio temprano;
7. comprobar binding caps;
8. si sube capital sin salto fuerte de DD, continuar hacia arriba.

NO congelar ceiling hasta encontrar evidencia de meseta/cliff.

---

# 9. CUÁNDO PODEMOS DECIR QUE ENCONTRAMOS EL TECHO

No declarar techo porque un caso individual parezca grande.

El ceiling debe cerrarse con evidencia de ridge.

Se necesita demostrar al menos:

1. varios puntos crecientes alrededor del máximo;
2. un máximo reproducible;
3. puntos por encima del máximo que:
   - no aumentan capital;
   - o degradan capital;
   - o chocan con provider/risk/margin físico;
4. estabilidad en parámetros vecinos;
5. binding-cap attribution que explique por qué no puede seguir creciendo;
6. conservación 3.368/3.368;
7. cero leakage;
8. cero admission filtering;
9. misma población;
10. comparación económica completa.

Si 350x sigue subiendo:

- extender 400x / 450x / 500x u otro rango físicamente justificable.

Si single-risk 22–24% aumenta ceiling pero aumenta DD temprano:

- separar el efecto de ceiling tardío del riesgo temprano;
- conservar 20% temprano y explorar una regla de riesgo que escale con capital/estado de Portfolio de forma causal.

NO subir riesgo global sólo para inflar terminal capital.

---

# 10. DRAWDOWN FORENSICS — PRIORIDAD INMEDIATA DESPUÉS DEL TRUE CEILING

Una vez encontrado el verdadero ceiling:

> **NO BUSCAR MÁS PROFIT TEMPORALMENTE.**
>
> **HACER UN ESTUDIO PROFUNDO DE QUÉ CAUSA EL DRAWDOWN.**

La pregunta ya no debe ser “qué parámetro bajo”.

Debe ser:

> **¿QUÉ MECANISMOS, MODOS, TRADERS, SECUENCIAS, MULTIPLICADORES Y ESTADOS DEL CAPITAL CREAN CADA EPISODIO DE DRAWDOWN?**

## No estudiar sólo el max DD

Construir un atlas de drawdowns:

- top 1;
- top 3;
- top 5;
- top 10 episodios.

Para cada episodio registrar:

### Tiempo

- peak_at;
- trough_at;
- recovery_at;
- underwater duration.

### Capital

- peak capital;
- trough capital;
- DD USD;
- DD %;
- open stop risk;
- Sovereign;
- cushion;
- reserved capital;
- deployed capital.

### Por mode

- ATTACK net;
- MEDIUM net.

### Por Trader

- R34_XAUUSD;
- R38_EURUSD;
- R38_GBPJPY;
- R42_AUDJPY;
- R43_GBPUSD;
- VT08_FOREX;
- VT31_NAS100.

### Por multiplicador

- pérdidas por 1x;
- 2x;
- 3x;
- ...
- high multiplier.

### Por motor económico

- Sizing selected;
- CIBO Compound state;
- Compound Portfolio release;
- Adaptive Leverage binding cap;
- growth slope;
- single risk cap;
- shock taper;
- loss-streak taper;
- DD taper;
- lifecycle defense.

### Por secuencia

- pérdidas individuales;
- loss streak;
- overlap;
- same-Trader clustering;
- cross-Trader clustering;
- correlation;
- regime;
- volatility;
- liquidity.

---

# 11. CAMBIO DE NATURALEZA DEL DD A LO LARGO DE LA INVESTIGACIÓN

No asumir que existe un único “culpable”.

## Benchmark coordinado temprano

El max DD ~51,13% era prácticamente **100% MEDIUM**:

- peak ~USD 81,96;
- trough ~USD 40,06;
- 2019-07-19 → 2019-08-12.

Esto llevó a investigar MEDIUM/lifecycle.

## Arquitectura de alto ceiling

Después de las protecciones selectivas y el crecimiento ATTACK:

el peor episodio puede pasar a ser ATTACK-dominante.

En el caso USD 34k:

- ATTACK en max DD ≈ **-USD 77,67**;
- MEDIUM ≈ **+USD 10,56**;
- net DD ≈ -USD 67,11.

Por Trader:

- R38_GBPJPY ≈ -USD 49,32;
- R34_XAUUSD ≈ -USD 21,05;
- VT08 ≈ -USD 2,10;
- VT31 ≈ -USD 3,83;
- otros aportan pequeñas compensaciones.

Conclusión:

> arreglar MEDIUM desplazó el cuello hacia ATTACK.

El siguiente arquitecto debe estudiar la arquitectura ACTUAL, no repetir conclusiones de un benchmark anterior.

---

# 12. BOTTLENECK ECONÓMICO ACTUAL

En el caso USD 34k, los sensores reportan aproximadamente:

## Compound Portfolio

- restriction count ≈ 2.888;
- capital pressure / destroyed sensor ≈ USD 79k.

## CIBO Compound

- restriction count ≈ 1.194;
- capital pressure ≈ USD 1,7k.

## Adaptive Leverage

- restricciones económicas finales: ~0 en la atribución agregada.

## Sizing

- restricciones económicas finales: ~0 como admission/rejection;
- mantiene caps de intensidad.

Interpretación:

**Compound Portfolio sigue siendo el principal regulador y principal lugar donde existe capacidad económica no capturada.**

Pero no liberar Portfolio ciegamente.

La misión es liberar más valor sin crear tail DD.

---

# 13. MECANISMOS DE PROTECCIÓN PROBADOS

## Global ADVERSE_LOSS_CUT

Variantes alrededor de -0,35R a -0,90R.

Resultado general:

- recorta winners;
- degrada capital;
- no lleva DD a 25%.

Rechazado como solución global.

## MEDIUM adverse partial reduction

Mejoró DD moderadamente.

Pero degradó capital y quedó lejos del objetivo.

No solución final.

## Drawdown-triggered partial defense

DD bajó algunos puntos.

Capital degradó.

No solución final.

## Broad initial stop cap

Aplicado indiscriminadamente:

- agotó la cuenta en variantes fuertes.

Lección:

> protección amplia ≠ protección inteligente.

## Selective initial stop cap

Mejor que broad defense.

Ejemplos históricos:

- ~USD 1.687 / DD 43,62%;
- ~USD 1.562 / DD 43,47%.

Útil para descubrir selectividad, pero ya superado por nuevas arquitecturas.

## MEDIUM ≤2x defense

Destructiva/exhausted.

Rechazada.

## ATTACK single-risk cap

Útil.

Pero demasiado bajo sacrifica ceiling.

Debe actuar en coordinación con Portfolio y shock logic.

## ATTACK loss-streak taper

Útil como señal causal.

No suficiente por sí sola.

## Portfolio DD budget

Reduce DD, pero sacrifica demasiado ceiling.

No final.

## Portfolio shock taper

Hasta ahora es la defensa más interesante porque:

- responde a daño REALIZADO;
- no usa futuro;
- no mata entradas;
- no desactiva ATTACK;
- puede aumentar capital final;
- mantiene el engine de compounding.

Debe seguir investigándose.

---

# 14. HIPÓTESIS DE PRÓXIMA GENERACIÓN PARA DD SIN DEGRADAR CEILING

Después de cerrar true ceiling:

## H1 — shock taper dinámico

No sólo trigger fijo 5%.

Investigar:

- severidad de shock;
- capital pre-settlement;
- trader;
- loss streak;
- recovery state;
- one-shot vs persistente.

Existe soporte:

`--ceiling-portfolio-shock-one-shot`

Investigar si un taper de un solo ATTACK posterior conserva más upside y controla tail.

## H2 — ATTACK live-DD taper

La infraestructura contiene:

- `ceiling_attack_drawdown_taper_trigger`;
- `ceiling_attack_drawdown_taper_fraction`.

Concepto:

- ATTACK sano = potencia completa;
- DD vivo = reducir sólo escalamiento incremental;
- recuperación = volver a liberar.

Debe exponerse/probarse sin rechazar entrada.

## H3 — riesgo ATTACK por estado

El 20% single-risk cap actualmente afecta decenas de ATTACK.

No convertir 20% en dogma.

Investigar una política causal donde:

- capital pequeño / estado frágil → menor risk fraction;
- capital sano / Portfolio fuerte → mayor risk fraction;
- después de shock → reducción;
- después de recuperación → restauración.

## H4 — trader-specific causal stress

En el DD actual R38_GBPJPY y R34_XAUUSD dominan el daño.

NO bloquear esos Traders.

Investigar si la intensidad incremental puede responder causalmente a:

- racha propia;
- shock propio;
- regime;
- volatility;
- correlation;
- recent realized loss.

## H5 — Portfolio reserve inteligente

Portfolio debe conservar capacidad de crecimiento y una reserva de supervivencia.

No hard wall global.

No one-shot depletion.

No liberar todo.

Probar reserve curves y recovery-aware release.

## H6 — DD por generaciones de capital

El peor DD ocurre temprano.

Después CIBO produce decenas de miles.

Investigar si la arquitectura necesita reglas diferentes por **estado causal de capital**, NO hard-coded por tiempo.

No usar “año 1/año 2”.

Usar:

- capital multiple;
- realized cushion;
- recovery;
- risk headroom;
- protected reserve.

---

# 15. REGLA DE NO DEGRADACIÓN DEL TECHO

Una vez cerrado el true ceiling, toda mejora de DD debe compararse contra ese techo.

No aceptar automáticamente:

- 25% DD con 50% menos capital;
- 30% DD con techo destruido;
- 40% DD con compounding apagado.

El objetivo del Owner es:

> **BAJAR DRAWDOWN LO MÁXIMO POSIBLE SIN DEGRADAR EL TECHO.**

Orden de evaluación:

1. preservar causalidad;
2. preservar 3.368/3.368;
3. preservar arquitectura económica;
4. preservar ceiling;
5. bajar DD;
6. si una defensa aumenta ceiling Y baja DD, promover;
7. si baja DD pero destruye ceiling, rechazar o usar sólo como evidencia diagnóstica.

---

# 16. SENSORES OBLIGATORIOS A MANTENER

## Sizing

- requested multiplier;
- authorized multiplier;
- final multiplier;
- reason counts;
- intensity cap counts;
- risk/margin/provider geometry.

## CIBO Compound

- positive net;
- negative net;
- recovery;
- profit reinvestment;
- capital recycled.

## Compound Portfolio

- cushion;
- available credit;
- recycled total;
- withheld capital;
- shock state;
- shock bind count;
- gross profit/loss;
- profit factor;
- loss by Trader;
- loss by multiplier.

## Adaptive Leverage

- provider cap;
- distributed cap;
- single-risk cap;
- DD budget cap;
- cushion funding cap;
- risk cap;
- margin cap;
- binding reason counts.

## Lifecycle

- entry count;
- data available count;
- applied trade count;
- changed outcome count;
- stop protection count;
- gap stop count;
- fallback count;
- blocked-by-trigger counts.

## Global

- total final capital;
- profit%;
- peak;
- trough;
- max DD;
- top DD episodes;
- Sovereign;
- cushion;
- all entries preserved;
- 3.368/3.368;
- no rejected;
- no deferred;
- no upstream filtered.

---

# 17. QUÉ FALTA PARA CERTIFICAR CIBO

**CIBO NO ESTÁ CERTIFICADO.**

Ceiling research y certificación son cosas distintas.

## 17.1 Cerrar ceiling discovery

Pendiente.

USD 34k es récord, no ceiling.

Debe cerrarse ridge físico/económico.

## 17.2 Comprimir DD

Pendiente crítico.

El corridor soberano de ceiling/capital management sigue siendo:

- ideal ~20–25%;
- 25% máximo para esta línea.

Actualmente ~51%.

No pasa.

## 17.3 Resolver Sovereign negativo

En varias variantes de alto ceiling el Sovereign termina negativo aunque total capital sea enorme y ATTACK sovereign breach sea cero.

Debe entenderse y reconciliarse.

No ocultar con cushion.

## 17.4 Estabilidad paramétrica

El ganador no puede depender de un punto mágico.

Necesita vecindad:

- ATTACK cap;
- risk fraction;
- slope;
- shock trigger;
- shock taper;
- MEDIUM cap;
- lifecycle thresholds.

## 17.5 Ablations

Con una arquitectura candidata final:

- Full;
- sin Sizing;
- sin CIBO Compound;
- sin Compound Portfolio;
- sin Adaptive Leverage;
- sin Native cognition;
- sin lifecycle;
- sin shock taper;
- sin loss-streak taper;
- sin profit recycling.

Medir quién crea valor.

## 17.6 Scientific battery

Requerido:

- chronological folds;
- walk-forward;
- Monte Carlo;
- path reorder;
- loss clustering;
- p05 PnL;
- p95 DD;
- probability positive;
- tail loss;
- ruin/survival;
- cost x2;
- slippage stress;
- spread stress;
- margin compression;
- remove best 1/2/3 trades;
- concentration stress;
- regime stability;
- temporal replication.

## 17.7 Forward qualification

El protocolo final exige sin reducción:

- decision epochs >= 80;
- candidate outcomes >= 200;
- selected outcomes >= 60;
- span >= 28 días;
- trading days >= 20;
- lineages >= 7;
- outcomes/lineage >= 8;
- 4 contiguous folds;
- candidate coverage >= 95%;
- selected coverage = 100%;
- baseline-selected coverage = 100%;
- pre-freeze decisions = 0.

## 17.8 Policy/calibration freeze

Antes de fresh holdout:

- política congelada;
- parámetros congelados;
- hashes;
- comparison identities;
- causal gates;
- no retoque después de ver holdout.

## 17.9 CE2I / GEN-C closure

Aplicables deben cerrar:

- causal comparison;
- economic non-compensation;
- OOS;
- stress;
- temporal replication.

## 17.10 Compound closure

Debe probar:

- accounting conservation;
- provenance;
- no double counting;
- capital generations;
- protected floor semantics;
- profit graduation;
- Internal Capital Market;
- reservation/release/recycling;
- path-dependent Monte Carlo;
- adversarial stress;
- temporal replication.

## 17.11 Failure engineering

Obligatorio:

- restart;
- duplicate event;
- duplicate reservation;
- partial settlement;
- ledger crash;
- unknown mutation outcome;
- reconciliation mismatch;
- stale snapshot;
- provider unavailable;
- capital-source mismatch;
- release-before-reconciliation;
- concurrent allocation.

Hard invariants:

- ZERO DOUBLE-SPEND;
- ZERO DUPLICATE AUTHORITY;
- ZERO SILENT SOURCE CREATION;
- ZERO RELEASE BEFORE RECONCILIATION.

## 17.12 Fresh OOS / sealed holdout

Protected identity:

`CIBO_USD60_6M_HOLDOUT_2017H1_V1`

Window:

`2017-01-01 inclusive → 2017-07-01 exclusive`

NO abrir hasta cumplir prerequisites.

Después de abrir:

- no retune;
- no relajar gates;
- no recalibrar con ese resultado;
- fail = resultado científico.

## 17.13 Worst-Trader Rescue Exam

Contrato:

`docs/research/CIBO-WORST-TRADER-RESCUE-EXAM-CONTRACT-V1.md`

Pendiente de activación después de efficiency/ceiling engineering.

Debe medir capacidad de rescatar o minimizar daño en Traders débiles sin modificar sus metodologías.

## 17.14 Final Integrated Exam

Protocolo:

`docs/research/CIBO-FINAL-INTEGRATED-CERTIFICATION-EXAM-PROTOCOL-V1.md`

Debe pasar:

P1–P8:

- source-of-truth;
- zero open;
- no unexplained red CI;
- provider/Risk/CMA/forward truth;
- forward qualification;
- policy freeze;
- scientific closure;
- Compound closure.

Y E1–E10:

- authority;
- capital conservation;
- realized-capital law;
- provider truth;
- Risk precedence;
- chronology/no leakage;
- economic non-compensation;
- stress integrity;
- temporal replication;
- deterministic replay.

## 17.15 World Cup Maximum Capability Exam

Según:

`docs/research/CIBO-INTEGRATED-CERTIFICATION-SEQUENCE-AMENDMENT-V1.md`

ambos exámenes se mantienen mandatory/certification-blocking.

Orden vigente de continuidad:

`PRE_EXAM → FINAL INTEGRATED EXAM → WORLD CUP MAXIMUM CAPABILITY EXAM → STRICT ZERO-OPEN → FINAL CERTIFICATION CANDIDATE`

No confundir un ceiling replay espectacular con certificación.

---

# 18. ARCHIVOS CLAVE

## Core

- `src/qore/infrastructure/trader_lab/cibo_three_mode_capital_lab.py`
- `src/qore/infrastructure/cibo_position_lifecycle.py`
- `scripts/cibo_trader_lab_three_mode_ceiling.py`

## Current ceiling / DD workflows

- `.github/workflows/cibo-trader-lab-portfolio-shock-taper-frontier.yml`
- `.github/workflows/cibo-trader-lab-portfolio-shock-fast.yml`
- `.github/workflows/cibo-trader-lab-attack-single-risk-frontier.yml`
- `.github/workflows/cibo-trader-lab-medium-dd-compression-ridge.yml`
- `.github/workflows/cibo-trader-lab-selective-medium-dd-frontier.yml`
- `.github/workflows/cibo-trader-lab-portfolio-dd-budget-frontier.yml`
- `.github/workflows/cibo-trader-lab-growth-staged-edge-ridge.yml`
- `.github/workflows/cibo-trader-lab-exact-ceiling-m14-ridge.yml`

## Certification governance

- `docs/research/CIBO-FINAL-INTEGRATED-CERTIFICATION-EXAM-PROTOCOL-V1.md`
- `docs/research/CIBO-INTEGRATED-CERTIFICATION-SEQUENCE-AMENDMENT-V1.md`
- `docs/research/CIBO-USD60-6M-MAXIMUM-REAL-CAPABILITY-CERTIFICATION-V1.md`
- `docs/research/CIBO-WORST-TRADER-RESCUE-EXAM-CONTRACT-V1.md`

---

# 19. TRABAJOS QUE NO DEBEN REPETIRSE

Ya está probado que NO funciona como solución final:

- volver a filtrar entradas;
- DEFER financiero;
- reducir densidad para maquillar DD;
- global loss cuts fuertes;
- broad defensive stop para todo;
- extender defensa MEDIUM ≤2x sin selectividad;
- Portfolio hard DD budget como única defensa;
- bajar ATTACK indiscriminadamente;
- capar todo a 1x;
- usar future outcome;
- apagar Compound;
- apagar Portfolio;
- tratar 8.000% como techo;
- tratar USD 34k como techo.

---

# 20. PRIMER PLAN DEL SIGUIENTE ARQUITECTO

## P0 — cerrar el run actual

Leer:

`37644740113`

Si aparece un ganador >USD 34.019 con DD similar:

- promoverlo como NUEVO RÉCORD;
- seguir ceiling discovery.

## P1 — continuar ridge superior

Si 350x todavía mejora:

- extender;
- no asumir 500x como cap;
- detener sólo por evidencia.

Si risk 22/24% sube ceiling pero empeora DD temprano:

- no descartar todo;
- separar risk scaling por estado causal.

## P2 — confirmar true ceiling

No congelar hasta tener cliff.

## P3 — freeze de referencia económica

Una vez cerrado true ceiling:

registrar:

- exact capital;
- exact profit%;
- exact DD;
- config;
- artifacts;
- hashes;
- sensors.

## P4 — DD forensics profundo

Construir atlas top-10 drawdowns.

No tuning antes de attribution.

## P5 — atacar causas, no síntomas

Diseñar defensa por:

- mode;
- Trader;
- shock;
- loss streak;
- capital state;
- regime;
- correlation;
- leverage generation.

## P6 — repetir replay

Toda reparación vuelve al banco.

## P7 — aceptar sólo Pareto real

Mejor:

- mismo/mayor ceiling;
- menor DD.

No sacrificar ceiling para pintar DD bonito.

---

# 21. FRASE DE CONTINUIDAD PARA NUEVO CHAT

> Repositorio `mezas3238-hue/qore-core`, branch `agent/cibo-causal-expectation-leakage-fix-001`. Leer íntegramente `docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_POST_34K_CEILING_AND_DD_COMPRESSION.md`. USD 34.019 desde USD 60 (+56.598% profit total aprox.) es sólo el récord observado, NO el techo. Primero terminar true ceiling discovery; después hacer DD forensics profundo y reducir DD hacia 20–25% sin degradar el techo. Mantener 3.368/3.368 entradas y los cuatro motores económicos trabajando juntos. Ciclo obligatorio: mejorar → replay → sensores → reparar → replay.

---

# 22. RESUMEN EJECUTIVO

CIBO pasó de una arquitectura moderna de ~USD 1.8k a:

- ~USD 28k con growth-staged raw ceiling;
- >USD 32k con protección selectiva;
- **USD 34.019** con Portfolio shock taper.

El ceiling actual observado equivale aproximadamente a:

**+56.598,66% de ganancia total sobre USD 60.**

Pero NO hay evidencia de que sea el ceiling definitivo.

De hecho:

- cientos de ATTACK siguen chocando contra caps;
- el max DD ocurre temprano con multiplicadores bajos;
- el cap alto actúa principalmente tarde;
- por lo tanto existe espacio lógico para aumentar terminal capital sin necesariamente empeorar el peor DD temprano.

La misión inmediata es seguir subiendo hasta demostrar el true ceiling.

Luego:

**TECHO CONGELADO → ESTUDIO PROFUNDO DEL DD → REDUCCIÓN MÁXIMA DEL DD SIN DEGRADAR TECHO → ROBUSTEZ → FRESH OOS → EXÁMENES → ZERO-OPEN → CERTIFICACIÓN.**
