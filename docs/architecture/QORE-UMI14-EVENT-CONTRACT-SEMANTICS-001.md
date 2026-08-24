# QORE-UMI14-EVENT-CONTRACT-SEMANTICS-001

## Estado

**PROGRAM D / UMI-14 — UMI13-UNR-014 R1 CANDIDATA DE FULL CLOSURE — NO CERTIFICADA**

Tracker: #396  
Parent audit: #363  
PR: #397  
Target: `UMI13-UNR-014` — `event-contracts`  
Baseline de recertificación: `76eda1ce4c324c3e97b70001ea4cac37a6d4a6a9`  
Baseline tree: `ca9722d11059f13a3c74c6820a15e15232c92171`  
Rama: `agent/qore-umi14-event-contract-semantics-014`

El candidato histórico fue preparado sobre una base anterior. Después del cierre e
integración de UNR-013, la rama se sincronizó con el `main` certificado sin alterar los
tres blobs preparatorios y se inició una nueva falsificación interna antes de cualquier
congelado R1.

La revisión interna encontró que el candidato preparatorio todavía usaba límites
`isinstance`, no revalidaba suficientemente estado anidado/fabricado, permitía que
`logical_values()` confiara en estado ya construido y usaba una canonicalización Decimal
no adecuada para Full Closure. R1 corrige esas debilidades antes del gate externo.

Este responsable conserva únicamente semántica contractual estática D04. No observa un
evento, no decide su resultado, no calcula probabilidad/precio, no ejecuta órdenes, no
liquida cash, no determina legalidad, no habilita Production y no autoriza capital real.

---

## 1. Gap material

UMI-13 conserva:

`UMI13-UNR-014 — event-resolution / outcome authority — binary payoff shape != authoritative resolution`

Un payoff binario por sí solo no preserva:

- qué criterio define el evento;
- qué outcomes contractuales existen;
- qué autoridad contractual resuelve;
- qué fuentes primarias/fallback controlan y en qué prioridad;
- qué regla de resolución se aplica;
- cómo se tratan correcciones de fuente;
- cómo se tratan conflictos entre fuentes;
- qué payout contractual corresponde a cada outcome.

Por tanto:

`BINARY PAYOFF SHAPE != AUTHORITATIVE RESOLUTION TERMS`

`RESOLUTION TERMS != RESOLVED OUTCOME`

---

## 2. Superficie autorizada

La corrección permanece limitada a exactamente tres archivos aditivos respecto del
baseline certificado:

1. `src/qore/infrastructure/event_contract_semantics.py`
2. `tests/infrastructure/test_event_contract_semantics.py`
3. `docs/architecture/QORE-UMI14-EVENT-CONTRACT-SEMANTICS-001.md`

No se modifica ningún owner certificado previo.

---

## 3. Valores estáticos

El owner define valores locales inmutables para:

- `EventContractTermsId`;
- `EventEvidenceRef`;
- `EventSubjectReferenceId`;
- `EventResolutionAuthorityRef`;
- `EventCriterionCode`;
- `EventOutcomeStructureCode`;
- `EventOutcomeCode`;
- `EventResolutionSourceCode`;
- `EventResolutionRuleCode`;
- `EventCorrectionPolicyCode`;
- `EventSourceConflictPolicyCode`;
- `EventCashPayout`;
- `EventOutcomeTerms`;
- `EventResolutionTerms`;
- `EventContractTerms`.

UMI-02 `EconomicIdentityId` se reutiliza para el instrumento y la moneda de payout. Este
owner no crea una segunda autoridad de identidad económica.

IDs UUID locales y `EconomicIdentityId` se validan con tipo exacto y el estado UUID
anidado también se revalida. Los códigos exigen `str` exacto, no vacío, sintaxis
canonical lowercase y máximo 96 caracteres.

---

## 4. Payout contractual y Decimal

`EventCashPayout` conserva:

- Decimal exacto, finito y no negativo;
- `EconomicIdentityId` exacto de moneda.

Zero payout es válido. No se impone una ley universal `$1/$0`, complementariedad ni
misma moneda para todos los outcomes.

La representación Decimal lógica:

- es independiente del contexto Decimal;
- colapsa signed zero a `0`;
- colapsa formas numéricamente equivalentes;
- no expande exponentes extremos proporcionalmente a su magnitud;
- usa forma compacta cuando la forma fija sería materialmente mayor.

`CONTRACTUAL PAYOUT != SETTLEMENT MUTATION`

---

## 5. Outcomes y orden no económico

Cada `EventOutcomeTerms` conserva un `EventOutcomeCode` exacto y su payout exacto.

`EventContractTerms` exige:

- tuple exacta;
- al menos dos outcomes;
- outcome codes únicos.

El orden de entrada de los outcomes **no es autoridad contractual por sí solo**. R1
canonicaliza el conjunto por outcome code/currency/amount para evitar que una simple
permutación del caller cree otra identidad económica.

Si un producto futuro necesita precedencia entre outcomes, esa precedencia debe quedar
representada mediante material contractual explícito, por ejemplo ordinal/rule code, y
no mediante el orden accidental de una colección de entrada.

Por contraste, el orden de las fuentes de resolución sí es material contractual y se
preserva exactamente.

`OUTCOME COLLECTION ORDER != RESOLUTION SOURCE PRIORITY`

---

## 6. Resolution authority y fuentes

`EventResolutionTerms` conserva:

- `EventResolutionAuthorityRef` opaco;
- sources primarias exactas, ordenadas y no vacías;
- sources fallback exactas, ordenadas y opcionales;
- `EventResolutionRuleCode`;
- `EventCorrectionPolicyCode`;
- `EventSourceConflictPolicyCode`;
- `scheduled_resolution_date` opcional.

Primary y fallback:

- deben ser tuples exactas;
- no admiten códigos duplicados;
- deben ser disjuntas entre sí;
- mantienen orden porque la prioridad de fuentes puede cambiar el contrato.

La referencia de authority no prueba identidad legal, credencial, API, provider support
ni capacidad de adjudicación.

`SOURCE REFERENCE != DATA FETCH`

`SOURCE PRIORITY != CALLER-ORDER NOISE`

---

## 7. Fechas estáticas sin ley cronológica inventada

El contrato puede conservar de forma independiente:

- `expiration_date: date | None`;
- `scheduled_resolution_date: date | None`.

Ambas, cuando existen, deben ser `date` exactas y no `datetime`.

R1 **no impone** que scheduled resolution deba ser anterior, igual o posterior a
expiration. La autoridad de #396 sólo exige conservar material contractual estático; no
prueba una relación cronológica universal aplicable a todos los event contracts.

Esto evita convertir una convención frecuente en una ley D04 universal no demostrada.
D06 conserva evaluación de reloj, deadline y calendario; D05 conserva la observación del
resultado real y su timestamp cuando exista.

`SCHEDULED RESOLUTION DATE != ACTUAL RESOLUTION TIME`

`STATIC DATE PAIR != UNIVERSAL DATE-ORDER LAW`

---

## 8. Exact types y revalidación fail-closed

R1 usa límites de tipo exacto en lugar de composición permisiva por subclases.

Los padres revalidan:

- wrappers UUID locales;
- `EconomicIdentityId` y su UUID interno;
- códigos locales;
- payout/moneda;
- outcomes;
- resolution terms;
- sources y policies;
- fechas exactas.

Cada `logical_values()` vuelve a ejecutar su validación. Por ello un objeto fabricado con
`object.__new__` o corrompido después de construcción con `object.__setattr__` no recibe
confianza sólo porque pertenece a la clase correcta.

`TYPE NAME EXISTS != VALID INTERNAL STATE`

`FROZEN DATACLASS != TRUSTED FOREVER`

---

## 9. Identidad lógica y no-colapso

La identidad lógica conserva por separado:

- tag `event-contract`;
- terms ID;
- instrument identity;
- subject reference;
- criterion code;
- outcome-structure code;
- outcomes canonicalizados;
- expiration date;
- resolution authority/sources/rules/policies/scheduled date;
- evidence ref.

Las pruebas R1 deben demostrar al menos:

- misma payout shape + distinto criterion != misma identidad;
- distinta outcome taxonomy != misma identidad;
- distinto payout amount/currency != misma identidad;
- distinta resolution authority != misma identidad;
- distinto primary/fallback source material != misma identidad;
- distinta source priority != misma identidad;
- distinta correction/conflict/resolution rule != misma identidad;
- distinta fecha estática representada != misma identidad;
- permutar outcomes sin cambiar material económico = misma identidad;
- permutar sources prioritarias = identidad distinta.

---

## 10. Separación de autoridad

| Material | Autoridad |
|---|---|
| Economic instrument / currency identity | UMI-02 / D04 |
| Static event criterion/outcome/payout/resolution terms | UNR-014 / D04 |
| Observed external event/source evidence / resolved observation | D05 |
| Current clock/deadline/calendar evaluation | D06 |
| Probability, market price, valuation methodology/results | D07 |
| Current positions / exposure / risk | D08 / D09 |
| Order / execution | D10 |
| Settlement / cash / position mutation | D11 |
| Legal / regulatory / eligibility determination | D22 |

El owner no ejecuta los policies de resolución. Sólo preserva el contrato estático que
otros departamentos podrán consumir bajo su propia autoridad.

---

## 11. Espacio negativo

R1 no contiene autoridad para:

- event scraping o feeds;
- provider/exchange API;
- current/resolved outcome;
- actual resolution timestamp;
- vote/score/weather/election parsing;
- current probability;
- market price;
- valuation;
- adjudication engine;
- correction/conflict execution;
- retry/polling/scheduler;
- order submission;
- settlement/cash/position mutation;
- portfolio/risk calculation;
- legal/regulatory eligibility;
- implicit wall clock;
- implicit/random UUID;
- secrets/productive credentials;
- Production;
- capital real.

`STATIC RESOLUTION TERMS != RESOLUTION ENGINE`

`CONTRACTUAL PAYOUT != CASH MOVEMENT`

---

## 12. R1 pre-freeze hardening

El candidato preparatorio anterior es evidencia histórica solamente.

Antes de establecer cualquier congelado R1 se corrigieron explícitamente:

1. exact-type boundaries;
2. nested UUID/EconomicIdentity revalidation;
3. local child-state revalidation;
4. reflective malformed-object resistance;
5. revalidación en cada `logical_values()`;
6. Decimal canonicalization context-independent y compacta;
7. outcome order no económico;
8. eliminación de la regla no demostrada `scheduled_resolution >= expiration`;
9. pruebas de negative space y autoridad D04.

Ninguna de estas correcciones habilita D05/D06/D07/D08/D09/D10/D11/D22.

---

## 13. Estado de gate

Al guardar este documento:

- baseline de recertificación = `76eda1ce4c324c3e97b70001ea4cac37a6d4a6a9`;
- R1 candidate = presente;
- Full Closure hardening = implementado, pendiente de Quality Gate;
- R1 freeze = NO ESTABLECIDO;
- exact post-freeze synthetic CI = NO ESTABLECIDO;
- DeepSeek Expert R1 = EN ESPERA;
- DeepSeek Coder R1 = EN ESPERA;
- Claude Code R1 = EN ESPERA;
- IA Final R1 = EN ESPERA;
- Ready = NO;
- #396 = OPEN;
- UMI-14 / PROGRAM D = NO CERRADOS;
- Production = CERRADO;
- capital real = NO AUTORIZADO.

Secuencia:

`FULL CI -> DIFF AUDIT -> CONGELADO R1 -> EXACT POST-FREEZE SYNTHETIC CI -> DEEPSEEK EXPERT -> IA -> DEEPSEEK CODER -> IA -> CLAUDE CODE -> IA -> IA FINAL -> READY -> MERGE(expected_head) -> POST-MERGE VERIFY -> CERRAR #396`

Cualquier cambio del HEAD después del CONGELADO invalida la ronda y exige nueva
vinculación, nuevo congelado, nuevo synthetic CI y reinicio serial desde DeepSeek Expert.
