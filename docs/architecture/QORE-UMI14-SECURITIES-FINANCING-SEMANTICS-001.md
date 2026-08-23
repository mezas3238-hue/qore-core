# QORE-UMI14-SECURITIES-FINANCING-SEMANTICS-001

## Estado

**PROGRAM D / UMI-14 — UNR-013 R6 CORRECCIÓN FULL-CLOSURE CANDIDATA — NO CERTIFICADA**

Tracker: #394  
Parent final review: #363  
PR: #437  
Target: `UMI13-UNR-013` — `securities-financing`  
Baseline certificado HASH: `db83b106f3a5e7f30a788567dfa970a38b7a379a`  
Tree inicial: `5b9c218a4fe3609b10e34b1cf8523cade0d10bbe`  
Rama: `agent/qore-umi14-securities-financing-full-closure-013`

R1–R5 son rondas históricas. R6 incorpora la corrección aceptada por IA para
`DS-EXPERT-UNR013-R5-01` y una falsificación IA adicional realizada antes del CONGELADO:
para margin lending flotante, la identidad contractual debe retener tanto la colocación del
fixing (`IN_ADVANCE` / `IN_ARREARS`) como el método de cálculo y la autoridad de las reglas
adicionales de observación.

Este responsable continúa limitado a semántica contractual estática D04. No observa,
calcula, ejecuta, liquida, valora, genera calendarios, opera custodias, habilita Production
ni autoriza capital real.

---

## 1. Alcance

UMI-13 retuvo:

`UMI13-UNR-013 — securities-financing — repo/securities lending/margin lending — distinct SFT forms; no dedicated owner`.

La superficie continúa siendo exactamente tres archivos aditivos respecto del baseline:

1. `src/qore/infrastructure/securities_financing_semantics.py`
2. `tests/infrastructure/test_securities_financing_semantics.py`
3. `docs/architecture/QORE-UMI14-SECURITIES-FINANCING-SEMANTICS-001.md`

Ningún archivo certificado previo se modifica.

---

## 2. Contratos reutilizados

Se reutilizan:

- `EconomicIdentityId` para referencias económicas canónicas;
- `DayCountConventionCode` para day-count contractual;
- `FinancialTenor` / `FinancialTenorUnit` para tenor financiero estático.

El consumidor revalida tipo exacto y estado interno relevante. No se confía en subclases
ni en objetos exactos fabricados con estado interno inválido.

El baseline contiene semántica de floating-rate en otros responsables, pero no existe un
contrato cross-product certificado que pueda reutilizarse aquí sin trasladar semántica
específica de derivatives. R6 conserva por ello únicamente valores locales mínimos y
provider-neutral.

---

## 3. Referencias y códigos locales

### `SftTermsId`
UUID explícito de términos SFT.

### `SftEvidenceRef`
Referencia UUID opaca a respaldo contractual retenido.

### `SftPartyReferenceId`
Referencia UUID opaca de parte contractual; no afirma identidad legal, KYC, cuenta ni LEI.

### `SftScheduleReferenceId`
Referencia UUID opaca a material contractual estático externo de calendario/términos. No
genera fechas ni resuelve calendarios.

### Códigos canónicos

Usan código lowercase canónico, no vacío y de máximo 64 caracteres:

- `SftCollateralEligibilityCode`;
- `SftSecurityQuantityBasisCode`;
- `SftCompensationAccrualBasisCode`;
- `SftFinancingCalculationCode`.

Sintaxis:

`[a-z0-9]+(?:[._-][a-z0-9]+)*`

`SftFinancingCalculationCode` permite distinguir material contractual como
`daily-simple`, `daily-compounded` o una convención contractual equivalente sin imponer una
taxonomía universal cerrada.

---

## 4. Dinero y cantidades de securities

`SftCashAmount` conserva monto Decimal exacto, finito y positivo más currency identity.

`SftSecurityQuantity` conserva security identity, cantidad Decimal exacta/positiva y
`quantity_basis`.

La base de cantidad forma parte de identidad lógica. Por tanto, para la misma security y
el mismo valor numérico:

`units != nominal-amount`.

Esto mantiene cerrado `DS-EXPERT-UNR013-R1-02` salvo una nueva demostración material.

---

## 5. Financing rate común

`SftRateTerms` conserva:

- FIXED o FLOATING;
- tasa contractual o spread;
- day count;
- referencia económica exacta cuando FLOATING.

FIXED prohíbe una referencia flotante. FLOATING la exige.

`SftRateTerms` no pretende contener por sí solo cada convención temporal o de cálculo de
cada producto. Las convenciones contractuales adicionales se conservan en el contrato que
las necesita.

No observa el índice, no calcula fixing, all-in rate, devengo ni interés.

---

## 6. Duración y arrangement

`SftDurationTerms` distingue TERM, OPEN y CALLABLE.

TERM exige fecha final y no notice period. OPEN no inventa una terminación. CALLABLE exige
notice days positivo y puede retener fecha final contractual opcional.

`SftArrangementTerms` distingue BILATERAL y TRI_PARTY. BILATERAL prohíbe agente tri-party;
TRI_PARTY exige una referencia exacta de agente.

---

## 7. Margin/haircut estático

`SftMarginTerms` conserva `initial_margin_ratio` y/o `haircut_ratio` como Decimal exacto,
finito y no negativo.

No se impone una ley universal `<= 1` no demostrada. Son términos contractuales, no current
margin ni cálculo de riesgo.

---

## 8. Repo

`RepoTerms` conserva:

- instrumento;
- seller/buyer distintos;
- duración;
- near cash;
- basket no vacío de securities con quantity basis;
- financing rate;
- arrangement;
- respaldo contractual;
- far leg cuando corresponde;
- margin/haircut estático opcional.

El basket se canonicaliza porque el orden del caller no es economía declarada. Se rechazan
identidades duplicadas dentro del basket.

TERM exige far leg y coincidencia con terminación contractual. OPEN lo prohíbe. CALLABLE
sólo lo permite con terminación contractual compatible.

Si se suministra far cash, su moneda debe coincidir con near cash. No se calcula repurchase
cash.

---

## 9. Securities lending — compensación

`SecuritiesLendingCompensationTerms` mantiene separados lending fee y cash-collateral
rebate.

Cada leg conserva:

- rate fijo/flotante;
- day count;
- referencia flotante cuando aplica;
- currency;
- accrual basis;
- payment mode;
- payment tenor o schedule reference;
- reset mode para flotante;
- reset tenor o schedule reference.

Payment modes:

- `PERIODIC`;
- `AT_TERMINATION`;
- `EXTERNAL_SCHEDULE`.

Reset modes:

- `PERIODIC`;
- `AT_PAYMENT`;
- `EXTERNAL_SCHEDULE`;
- `REFERENCE_CONVENTION`.

Fixed compensation prohíbe reset material. Floating compensation exige reset mode exacto.

Esto mantiene cerrados `DS-EXPERT-UNR013-R1-01` y `DS-EXPERT-UNR013-R2-02` salvo nueva
demostración material.

---

## 10. Securities lending — collateralization

`SftCollateralizationMode` distingue:

- `UNCOLLATERALIZED`;
- `EXPLICIT`;
- `EXTERNAL_SCHEDULE`.

UNCOLLATERALIZED exige tuple vacío y sin referencia externa. EXPLICIT exige tuple no vacío
y sin referencia externa. EXTERNAL_SCHEDULE exige referencia exacta y puede retener además
items estáticos explícitos.

El modo y la referencia forman parte de identidad lógica. Esto mantiene cerrado
`DS-EXPERT-UNR013-R2-01` salvo nueva demostración material.

---

## 11. Margin lending — payment

R4 introdujo `SftFinancingPaymentMode` para cerrar `DS-EXPERT-UNR013-R3-01`:

- `PERIODIC`;
- `AT_TERMINATION`;
- `EXTERNAL_SCHEDULE`.

PERIODIC exige tenor financiero exacto y prohíbe schedule reference. AT_TERMINATION prohíbe
ambos. EXTERNAL_SCHEDULE exige `SftScheduleReferenceId` y prohíbe tenor.

La convención de pago forma parte de identidad lógica.

---

## 12. Margin lending — reset

R5 introdujo `SftFinancingResetMode` para cerrar `DS-EXPERT-UNR013-R4-01`:

- `PERIODIC`;
- `AT_PAYMENT`;
- `EXTERNAL_SCHEDULE`;
- `REFERENCE_CONVENTION`.

FIXED prohíbe material de reset. FLOATING exige reset mode exacto.

PERIODIC exige tenor. AT_PAYMENT no acepta tenor ni referencia. EXTERNAL_SCHEDULE exige
referencia externa. REFERENCE_CONVENTION delega frecuencia/trigger al material contractual
de la referencia.

---

## 13. Hallazgo R5 — fixing in advance / in arrears

DeepSeek Expert R5 identificó `DS-EXPERT-UNR013-R5-01`.

R5 podía representar dos contratos con el mismo floating reference, spread, day count,
payment mensual, reset mensual y demás material, pero uno con fixing `IN_ADVANCE` y otro
`IN_ARREARS`.

La distinción es estática: define dónde se fija la tasa respecto del período de devengo.
D05 puede aportar observaciones, D06 resolver fechas y D07 calcular interés, pero esos
responsables no sustituyen la regla contractual.

### Corrección R6

R6 añade `SftFinancingFixingTiming`:

- `IN_ADVANCE`;
- `IN_ARREARS`;
- `REFERENCE_CONVENTION`.

Para FLOATING + PERIODIC reset:

- reset tenor exacto requerido;
- fixing timing exacto requerido;
- reset schedule reference prohibida.

Para AT_PAYMENT, REFERENCE_CONVENTION y EXTERNAL_SCHEDULE, un fixing timing adicional está
prohibido porque el propio reset mode ya determina o delega esa colocación temporal.

Para FIXED, todo material reset/fixing está prohibido.

---

## 14. Falsificación IA adicional antes del CONGELADO R6

Antes de fijar R6, IA revisó las convenciones públicas de business loans basadas en SOFR y
el precedente interno de QORE para floating-rate conventions.

Se confirmó otro par material que R5 y la primera forma de R6 todavía podían colapsar:

- mismo SOFR/reference;
- mismo spread;
- mismo day count;
- mismo payment;
- mismo reset periódico;
- mismo fixing `IN_ARREARS`;
- contrato A: Daily Simple;
- contrato B: Daily Compounded.

También se confirmó que contratos de loans pueden distinguir lookback, lockout y
observation shift sin cambiar necesariamente la referencia económica base.

Esas son reglas contractuales estáticas. No son observaciones ni resultados de cálculo.

R6 se amplió **antes del CONGELADO** para retenerlas sin crear un motor de rates.

---

## 15. R6 — cálculo flotante

R6 añade:

`SftFinancingCalculationCode`.

Todo margin lending FLOATING exige un código exacto/canónico de cálculo. Ejemplos
provider-neutral de material que puede conservarse:

- `daily-simple`;
- `daily-compounded`;
- `reference-convention`;
- otra convención contractual canónica cuando corresponda.

El código forma parte de identidad lógica.

Por tanto, para el mismo benchmark y demás material:

`daily-simple != daily-compounded`.

R6 no ejecuta ese cálculo; sólo conserva la calificación contractual.

FIXED prohíbe `financing_calculation`.

---

## 16. R6 — autoridad de observación flotante

Lookback, lockout, observation shift, calendarios de fixing y reglas similares pueden ser
material contractual, pero modelar todos sus algoritmos dentro de este responsable
absorbería autoridad de D06/D07.

R6 añade `SftFinancingObservationMode`:

- `NONE`;
- `REFERENCE_CONVENTION`;
- `EXTERNAL_TERMS`.

Y un campo opcional:

`financing_observation_reference: SftScheduleReferenceId | None`.

### NONE

Declara que no existe material adicional de observación que deba distinguirse más allá de
la convención flotante ya retenida. Una referencia externa está prohibida.

### REFERENCE_CONVENTION

Declara explícitamente que las reglas adicionales de observación son las definidas por el
material contractual de la referencia económica. Una referencia externa adicional está
prohibida.

### EXTERNAL_TERMS

Declara que existe material contractual adicional —por ejemplo lookback/lockout/observation
shift/calendario— y exige una `SftScheduleReferenceId` exacta que lo identifica.

La referencia externa forma parte de identidad lógica. Dos conjuntos distintos de términos
externos no deben compartir la misma identidad de referencia.

Esto permite conservar la existencia y la identidad del material estático sin calcular
fechas ni tasas dentro de D04.

Todo margin lending FLOATING exige un `SftFinancingObservationMode` exacto. FIXED prohíbe
observation mode/reference.

---

## 17. Proyección lógica de margin lending flotante

La porción flotante de `MarginLendingTerms.logical_values()` conserva:

`(`
`  reset_mode,`
`  reset_tenor | None,`
`  reset_schedule_reference | None,`
`  fixing_timing | None,`
`  calculation_code,`
`  (observation_mode, observation_reference | None)`
`)`

El material de payment permanece separado.

Casos de no-colapso requeridos por pruebas R6 incluyen:

- periodic payment != at termination != external schedule;
- periodic reset != at-payment != external reset schedule != reference convention;
- periodic 1 month + in-advance != periodic 1 month + in-arrears;
- daily-simple != daily-compounded;
- observation NONE != REFERENCE_CONVENTION != EXTERNAL_TERMS;
- external observation terms A != external observation terms B por referencia;
- units != nominal-amount;
- uncollateralized != explicit != external-schedule collateralization;
- repo != securities lending != margin lending.

---

## 18. Margin lending — collateral eligibility

`SftCollateralEligibilityCode` conserva calificación contractual canónica.

`eligible_collateral_identity_ids` puede estar vacío o contener identidades exactas,
únicas y canonicalizadas. No representa collateral actual ni disponibilidad.

---

## 19. Determinismo Decimal

Todo material numérico usa Decimal exacto y finito. Subclases se rechazan.

La representación lógica:

- usa `Decimal.as_tuple()`;
- canonicaliza signed zero a `"0"`;
- elimina ceros finales del coeficiente;
- no depende de `Decimal.normalize()`;
- no depende de precisión ambiental;
- conserva exponentes extremos en forma compacta cuando corresponde.

---

## 20. Bordes de composición

Los padres revalidan hijos locales/importados y estado interno relevante. La matriz incluye:

- UUID wrappers;
- EconomicIdentityId;
- DayCountConventionCode;
- FinancialTenor / FinancialTenorUnit;
- quantity basis;
- compensation accrual basis;
- financing calculation code;
- schedule references;
- payment/reset modes;
- financing fixing timing;
- financing observation mode/reference;
- collateralization mode;
- cash/security children;
- top-level product terms.

Un objeto exacto fabricado sin constructor no recibe confianza sólo por su clase.

---

## 21. Límites de autoridad

| Material | Responsable |
|---|---|
| Economic/security/currency/reference identity | UMI-02 / D04 |
| Day-count y tenor financiero estático | UMI-03 / D04 |
| SFT static terms y referencias de términos | este UNR-013 |
| Observaciones de mercado/collateral | D05 |
| Resolución de calendario/fechas | D06 |
| Devengo, fixing calculado, cashflow, pricing y valuation | D07 |
| Holdings y balances actuales | D08 |
| Margin/risk/exposure/capacity | D09 |
| Orders/execution/transfer instructions | D10 |
| Settlement/custody/collateral movement | D11 |
| Legal/regulatory/master-agreement determinations | D22 |

---

## 22. Espacio negativo

R6 no contiene autoridad para:

- provider/network I/O;
- generación de payment/reset/fixing dates;
- observación de índices;
- cálculo de simple/compounded rate;
- cálculo de fixing, interés, accrual o cashflow;
- resolución de lookback/lockout/observation shift;
- pricing/valuation;
- collateral valuation;
- posiciones o balances actuales;
- utilization/available credit actuales;
- margin call o liquidation;
- locate/borrow availability;
- collateral substitution/rehypothecation operation;
- recall/return operation;
- custody/settlement operation;
- execution/order submission;
- legal eligibility/KYC;
- wall clock implícito;
- UUID aleatorio/implícito;
- productive credentials;
- Production;
- real-capital authority.

`STATIC CALCULATION CODE != CALCULATED RATE`

`STATIC OBSERVATION TERMS REFERENCE != GENERATED OBSERVATION DATES`

`STATIC FIXING PLACEMENT != OBSERVED FIXING`

---

## 23. Historial de rondas

### R1

DeepSeek Expert identificó:

- `DS-EXPERT-UNR013-R1-01` — compensación securities-lending incompleta;
- `DS-EXPERT-UNR013-R1-02` — quantity basis ausente.

### R2

R2 cerró quantity basis y se identificaron:

- `DS-EXPERT-UNR013-R2-01` — collateralization sin external schedule distinction;
- `DS-EXPERT-UNR013-R2-02` — payment/reset timing ambiguo.

### R3

R3 cerró los cuatro anteriores y se identificó:

- `DS-EXPERT-UNR013-R3-01` — margin lending sin convención de pago del financing rate.

### R4

R4 añadió payment convention y se identificó:

- `DS-EXPERT-UNR013-R4-01` — margin lending flotante sin reset convention.

### R5

R5 añadió reset mode/tenor/reference. DeepSeek confirmó el cierre de R4-01 e identificó:

- `DS-EXPERT-UNR013-R5-01` — reset periódico sin distinción fixing in-advance/in-arrears.

### R6

R6 añade:

- `SftFinancingFixingTiming`;
- `SftFinancingCalculationCode`;
- `SftFinancingObservationMode`;
- `financing_observation_reference`.

La ampliación de calculation/observation fue una corrección IA preventiva antes del
CONGELADO R6, basada en un par material reproducible de business loans y no en una
preferencia de riqueza de esquema.

R6 debe validarse desde cero; ninguna conclusión anterior certifica este HEAD.

---

## 24. Estado de validación R6

Estado al guardar este documento:

- R1–R5 = históricos;
- R6 candidate = presente;
- PRUEBAS COMPLETAS R6 = pendientes sobre HEAD final;
- CONGELADO R6 = no establecido;
- revisión externa R6 = en espera;
- Ready = no establecido;
- #394 = abierto;
- UNR-013 = no cerrado;
- UMI-14 = no cerrado;
- PROGRAM D = no cerrado;
- Production = cerrado;
- real capital = no autorizado.

Secuencia requerida tras fijar el HEAD final:

`PRUEBAS COMPLETAS -> REVISIÓN DEL DIFF -> CONGELAR R6 -> PRUEBAS COMPLETAS SOBRE SYNTHETIC EXACTO -> DEEPSEEK EXPERT R6 -> IA -> DEEPSEEK CODER R6 -> IA -> CLAUDE CODE R6 -> IA -> IA FINAL -> READY -> INTEGRAR CON HEAD ESPERADO -> VERIFICAR INTEGRACIÓN -> CERRAR #394 -> CONTINUAR UMI-14`

Cualquier cambio del HEAD después del CONGELADO R6 obliga a una nueva ronda desde DeepSeek
Expert.
