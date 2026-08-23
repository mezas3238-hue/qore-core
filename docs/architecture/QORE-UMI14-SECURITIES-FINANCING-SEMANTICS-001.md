# QORE-UMI14-SECURITIES-FINANCING-SEMANTICS-001

## Estado

**PROGRAM D / UMI-14 — UNR-013 R5 CORRECCIÓN FULL-CLOSURE CANDIDATA — NO CERTIFICADA**

Tracker: #394  
Parent final review: #363  
PR: #437  
Target: `UMI13-UNR-013` — `securities-financing`  
Baseline certificado: `db83b106f3a5e7f30a788567dfa970a38b7a379a`  
Tree inicial: `5b9c218a4fe3609b10e34b1cf8523cade0d10bbe`  
Rama: `agent/qore-umi14-securities-financing-full-closure-013`

R1, R2, R3 y R4 son rondas históricas. R5 incorpora la corrección aceptada por IA para
`DS-EXPERT-UNR013-R4-01`: la convención contractual de reset del financing rate flotante
de margin lending debe formar parte de D04 y de la identidad lógica.

La adjudicación IA del hallazgo R4 está registrada en la revisión `5003271066`.

Este responsable continúa limitado a semántica contractual estática D04. No observa,
calcula, ejecuta, liquida, valora, genera calendarios, opera custodias, habilita Production
ni autoriza capital real.

---

## 1. Alcance autorizado

UMI-13 retuvo:

`UMI13-UNR-013 — securities-financing — repo/securities lending/margin lending — distinct SFT forms; no dedicated owner`.

La corrección mantiene un responsable específico para tres formas estáticas distintas:

- repo;
- securities lending;
- margin lending.

Cash/money-market, derivados genéricos y facilidades genéricas no sustituyen por sí solos
esta estructura contractual.

La superficie continúa siendo exactamente tres archivos aditivos respecto del baseline:

1. `src/qore/infrastructure/securities_financing_semantics.py`
2. `tests/infrastructure/test_securities_financing_semantics.py`
3. `docs/architecture/QORE-UMI14-SECURITIES-FINANCING-SEMANTICS-001.md`

No se modifica ningún archivo previamente certificado.

---

## 2. Contratos reutilizados

Se reutilizan únicamente contratos cuya semántica coincide:

- `EconomicIdentityId` para referencias económicas canónicas;
- `DayCountConventionCode` para day-count contractual;
- `FinancialTenor` / `FinancialTenorUnit` para tenor financiero estático.

El consumidor vuelve a validar:

- tipo exacto;
- UUID interno exacto;
- código interno canónico;
- `FinancialTenor.value` exacto y positivo;
- `FinancialTenor.unit` exacto.

No se confía en subclases ni en objetos exactos con estado interno malformado.

---

## 3. Referencias locales

### `SftTermsId`

Identidad UUID explícita de términos SFT.

### `SftEvidenceRef`

Referencia UUID opaca a respaldo contractual retenido. No transporta contenido ni autoridad
operativa.

### `SftPartyReferenceId`

Referencia UUID opaca de parte contractual. No afirma identidad legal, KYC, cuenta ni LEI.

### `SftScheduleReferenceId`

Referencia UUID opaca a material contractual estático externo de calendario/términos.

`SftScheduleReferenceId` no genera fechas, no resuelve calendarios y no ejecuta pagos.

---

## 4. Códigos canónicos

Los siguientes valores usan código lowercase canónico, no vacío y con máximo 64 caracteres:

- `SftCollateralEligibilityCode`;
- `SftSecurityQuantityBasisCode`;
- `SftCompensationAccrualBasisCode`.

Sintaxis:

`[a-z0-9]+(?:[._-][a-z0-9]+)*`

El responsable conserva el código contractual suministrado; no inventa una taxonomía
universal que el baseline no haya certificado.

---

## 5. Dinero y cantidades de securities

### `SftCashAmount`

Conserva:

- `amount: Decimal` exacto, finito y positivo;
- `currency_identity_id: EconomicIdentityId` exacto.

### `SftSecurityQuantity`

Conserva:

- `security_identity_id`;
- `quantity: Decimal` exacto, finito y positivo;
- `quantity_basis: SftSecurityQuantityBasisCode`.

La base de cantidad forma parte de identidad lógica.

Por tanto, para la misma security y el mismo valor numérico:

`units != nominal-amount`

cuando el contrato suministra bases distintas.

Esto conserva el cierre material de `DS-EXPERT-UNR013-R1-02`.

---

## 6. Financing rate común

`SftRateTerms` conserva:

- `SftRateKind.FIXED` o `FLOATING`;
- tasa contractual o spread exacto;
- `DayCountConventionCode`;
- referencia económica exacta cuando el rate es FLOATING.

FIXED prohíbe una referencia flotante.

FLOATING exige una referencia flotante.

`SftRateTerms` no pretende por sí solo contener todas las convenciones temporales de cada
producto. Las convenciones estáticas adicionales se conservan en el contrato que las
necesita.

No se observa el índice, no se calcula el all-in rate y no se calcula devengo.

---

## 7. Duración

`SftDurationTerms` distingue:

### TERM

- fecha inicial exacta;
- fecha final exacta requerida;
- fecha final posterior a la inicial;
- sin notice period.

### OPEN

- fecha inicial exacta;
- sin fecha final inventada;
- notice days positivo opcional.

### CALLABLE

- notice days positivo requerido;
- fecha final contractual opcional;
- cuando existe debe ser posterior a la inicial.

No representa estado actual de ejercicio o terminación.

---

## 8. Arrangement

`SftArrangementTerms` distingue:

- `BILATERAL`;
- `TRI_PARTY`.

BILATERAL prohíbe agente tri-party.

TRI_PARTY exige `SftPartyReferenceId` exacto para el agente.

La existencia de la referencia no otorga autoridad operacional al agente.

---

## 9. Margin/haircut estático

`SftMarginTerms` conserva:

- `initial_margin_ratio` opcional;
- `haircut_ratio` opcional.

Al menos uno debe existir.

Cada valor suministrado debe ser Decimal exacto, finito y no negativo.

No existe restricción universal `<= 1` porque esa ley no está demostrada para todas las
convenciones cubiertas.

Estos son términos contractuales, no current margin ni cálculo de riesgo.

---

## 10. Repo

`RepoTerms` conserva:

- términos e instrumento;
- seller y buyer distintos;
- duración;
- near cash;
- basket no vacío de securities con quantity basis;
- financing rate;
- arrangement;
- respaldo contractual;
- far leg cuando corresponde;
- margin/haircut estático opcional.

El basket se canonicaliza por material económico y el orden del caller no forma parte de
la economía declarada.

Se rechazan securities duplicadas por `EconomicIdentityId` dentro del basket.

La identidad del producto repo no puede ser la misma que una security transferida.

TERM exige far leg y su fecha debe coincidir con la terminación contractual.

OPEN prohíbe inventar far leg.

CALLABLE permite far leg únicamente cuando existe terminación contractual y las fechas
coinciden.

Si existe `repurchase_cash`, su currency debe coincidir con la del near cash.

No se calcula repurchase cash.

---

## 11. Securities lending — compensación

`SecuritiesLendingCompensationTerms` mantiene separados:

- `lending_fee`;
- `cash_collateral_rebate`.

Cada leg usa `SecuritiesLendingCompensationLegTerms`, que conserva:

- rate fijo/flotante;
- day count;
- referencia flotante cuando aplica;
- currency;
- accrual basis;
- payment mode;
- payment tenor o schedule reference según modo;
- reset mode para rate flotante;
- reset tenor o schedule reference según modo.

### Payment modes

`SftCompensationPaymentMode`:

- `PERIODIC`;
- `AT_TERMINATION`;
- `EXTERNAL_SCHEDULE`.

PERIODIC exige tenor financiero exacto y prohíbe schedule reference.

AT_TERMINATION prohíbe tenor y schedule reference.

EXTERNAL_SCHEDULE exige `SftScheduleReferenceId` exacto y prohíbe tenor.

### Reset modes flotantes

`SftCompensationResetMode`:

- `PERIODIC`;
- `AT_PAYMENT`;
- `EXTERNAL_SCHEDULE`;
- `REFERENCE_CONVENTION`.

Rate fijo prohíbe todo reset material.

Rate flotante exige un reset mode exacto.

Estas convenciones son estáticas. No se generan fechas ni se observan índices.

La superficie conserva el cierre de `DS-EXPERT-UNR013-R1-01` y
`DS-EXPERT-UNR013-R2-02` salvo demostración posterior de una colisión nueva.

---

## 12. Securities lending — collateralization

`SftCollateralizationMode` distingue:

- `UNCOLLATERALIZED`;
- `EXPLICIT`;
- `EXTERNAL_SCHEDULE`.

### UNCOLLATERALIZED

- collateral tuple vacío;
- sin external schedule reference.

### EXPLICIT

- collateral tuple no vacío;
- sin external schedule reference.

### EXTERNAL_SCHEDULE

- `SftScheduleReferenceId` exacto requerido;
- collateral tuple puede estar vacío o contener items estáticos explícitos adicionales.

El modo y la referencia externa forman parte de identidad lógica.

Así, un contrato uncollateralized no colapsa con otro cuya collateralization está gobernada
por material contractual externo.

Esto conserva el cierre de `DS-EXPERT-UNR013-R2-01`.

No se representa collateral actual, valoración, sustitución, custody ni settlement.

---

## 13. Margin lending — pago y reset de financiación

`MarginLendingTerms` conserva:

- términos e instrumento;
- lender y borrower distintos;
- duración;
- credit limit contractual positivo;
- financing rate;
- convención contractual de pago del financing rate;
- convención contractual de reset cuando el financing rate es flotante;
- collateral eligibility;
- conjunto canónico opcional de identidades elegibles;
- arrangement;
- respaldo contractual;
- margin/haircut estático opcional.

### Cierre del hallazgo R3 — payment

DeepSeek Expert R3 identificó `DS-EXPERT-UNR013-R3-01`: R3 podía representar dos
facilidades iguales en todo material retenido pero con interés periódico frente a interés
pagadero al terminar.

R4 añadió `SftFinancingPaymentMode`:

- `PERIODIC = "periodic"`;
- `AT_TERMINATION = "at-termination"`;
- `EXTERNAL_SCHEDULE = "external-schedule"`.

`MarginLendingTerms` conserva:

- `financing_payment_mode`;
- `financing_payment_tenor` cuando PERIODIC;
- `financing_payment_schedule_reference` cuando EXTERNAL_SCHEDULE.

No existe default semántico para `financing_payment_mode`.

PERIODIC exige tenor financiero exacto y positivo y prohíbe referencia externa.

AT_TERMINATION prohíbe tenor y referencia externa.

EXTERNAL_SCHEDULE exige `SftScheduleReferenceId` exacto y prohíbe tenor.

R4 cerró el par `monthly != at-termination` y R5 conserva ese cierre.

### Hallazgo R4 aceptado — floating reset

DeepSeek Expert R4, paquete `UNR013-ETAPAC-R4-DS-EXPERT-01`, identificó
`DS-EXPERT-UNR013-R4-01`.

El R4 podía representar dos facilidades flotantes iguales en todo material retenido, con la
misma referencia, spread, day count y convención de pago, pero con reset:

- PERIODIC 1 month;
- AT_PAYMENT.

Como R4 no retenía la convención de reset de margin lending, ambas podían compartir
identidad lógica.

IA aceptó el hallazgo en `5003271066`.

### Corrección R5 — floating reset

R5 añade `SftFinancingResetMode`:

- `PERIODIC = "periodic"`;
- `AT_PAYMENT = "at-payment"`;
- `EXTERNAL_SCHEDULE = "external-schedule"`;
- `REFERENCE_CONVENTION = "reference-convention"`.

`MarginLendingTerms` conserva adicionalmente:

- `financing_reset_mode`;
- `financing_reset_tenor`;
- `financing_reset_schedule_reference`.

Para financing rate FIXED:

- todo material de reset está prohibido.

Para financing rate FLOATING:

- un `financing_reset_mode` exacto es obligatorio.

#### PERIODIC

- tenor financiero exacto y positivo requerido;
- schedule reference prohibida.

#### AT_PAYMENT

- tenor prohibido;
- schedule reference prohibida.

#### REFERENCE_CONVENTION

- tenor prohibido;
- schedule reference prohibida.

#### EXTERNAL_SCHEDULE

- `SftScheduleReferenceId` exacto requerido;
- tenor prohibido.

La proyección lógica de margin lending incluye por separado:

`(payment_mode, payment_tenor | None, payment_schedule_reference | None)`

seguido de:

`(reset_mode, reset_tenor | None, reset_schedule_reference | None) | None`.

Por tanto, para tasa flotante:

`PERIODIC != AT_PAYMENT != EXTERNAL_SCHEDULE != REFERENCE_CONVENTION`

cuando todos los demás términos sean idénticos.

La corrección conserva solamente la convención estática. D05 puede aportar observaciones,
D06 puede resolver fechas concretas y D07 puede calcular fixing/devengo/interés; este
responsable no realiza ninguna de esas funciones.

---

## 14. Margin lending — collateral eligibility

`SftCollateralEligibilityCode` conserva calificación contractual canónica.

`eligible_collateral_identity_ids` es una tupla exacta opcional:

- puede estar vacía;
- cuando contiene referencias, cada una debe ser `EconomicIdentityId` exacta;
- no permite duplicados;
- el orden del caller se canonicaliza;
- el instrumento de la facility no puede ser su propio eligible collateral.

La tupla no representa collateral actual ni disponibilidad.

---

## 15. Identidad lógica

Cada producto comienza con un discriminante distinto:

- `repo`;
- `securities-lending`;
- `margin-lending`.

La identidad lógica conserva todo material estático de cada contrato dentro del alcance
demostrado.

Para margin lending R5 incluye específicamente:

1. discriminante;
2. terms ID;
3. instrument ID;
4. lender;
5. borrower;
6. duration;
7. credit limit;
8. financing rate;
9. financing payment convention;
10. financing reset convention o `None` para tasa fija;
11. collateral eligibility;
12. eligible collateral identities;
13. arrangement;
14. optional static margin terms;
15. contractual reference.

Casos de no-colapso requeridos por pruebas R5:

- monthly periodic payment != at termination;
- periodic payment != external payment schedule;
- periodic floating reset != at-payment reset;
- periodic reset != external reset schedule;
- external reset schedule A != external reset schedule B por referencia;
- units != nominal-amount;
- fee != rebate;
- uncollateralized != explicit != external-schedule collateralization;
- repo != securities lending != margin lending.

---

## 16. Determinismo Decimal

Todo material numérico utiliza Decimal exacto y finito.

Subclases Decimal se rechazan.

La representación lógica Decimal:

- usa `Decimal.as_tuple()`;
- canonicaliza signed zero a `"0"`;
- elimina ceros finales del coeficiente;
- no depende de `Decimal.normalize()`;
- no depende de precisión ambiental;
- conserva round-trip exacto;
- mantiene exponentes extremos en forma compacta cuando la forma fija crecería de manera
  desproporcionada.

Ejemplos:

`Decimal("1E+1000000") -> "1e+1000000"`

`Decimal("1E-1000000") -> "1e-1000000"`

---

## 17. Bordes de composición

Todo hijo local/importado se vuelve a validar en el padre.

La matriz incluye, entre otros:

- UUID wrappers;
- EconomicIdentityId;
- DayCountConventionCode;
- FinancialTenor y FinancialTenorUnit;
- quantity basis;
- compensation accrual basis;
- schedule references;
- compensation payment/reset modes;
- financing payment/reset modes;
- collateralization mode;
- cash/security children;
- compensation legs;
- top-level product terms.

Objetos exactos fabricados sin constructor no adquieren confianza únicamente por su clase.

---

## 18. Límites de autoridad

| Material | Responsable |
|---|---|
| Economic/security/currency/reference identity | UMI-02 / D04 |
| Day-count y tenor financiero estático | UMI-03 / D04 |
| SFT static terms y referencias de schedule | este UNR-013 |
| Observaciones de mercado/collateral | D05 |
| Resolución de calendario/fechas | D06 |
| Devengo, cashflow, pricing y valuation | D07 |
| Holdings y balances actuales | D08 |
| Margin/risk/exposure/capacity | D09 |
| Orders/execution/transfer instructions | D10 |
| Settlement/custody/collateral movement | D11 |
| Legal/regulatory/master-agreement determinations | D22 |

---

## 19. Espacio negativo

R5 no contiene autoridad para:

- provider/network I/O;
- generación de payment/reset dates;
- observación de índices;
- cálculo de fixing, interés, accrual o cashflow;
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

`STATIC PAYMENT CONVENTION != GENERATED PAYMENT DATES`

`STATIC RESET CONVENTION != OBSERVED OR CALCULATED RATE`

`STATIC COLLATERALIZATION != CURRENT COLLATERAL STATE`

`STATIC FINANCING RATE != CALCULATED INTEREST`

---

## 20. Historial de rondas

### R1

DeepSeek Expert identificó:

- `DS-EXPERT-UNR013-R1-01` — compensación securities-lending incompleta;
- `DS-EXPERT-UNR013-R1-02` — quantity basis ausente.

### R2

R2 cerró quantity basis, pero DeepSeek Expert identificó:

- `DS-EXPERT-UNR013-R2-01` — collateralization no distinguía external schedule;
- `DS-EXPERT-UNR013-R2-02` — payment/reset timing ambiguo.

### R3

R3 cerró los cuatro hallazgos anteriores. DeepSeek Expert R3 identificó:

- `DS-EXPERT-UNR013-R3-01` — MarginLendingTerms no retenía la convención contractual de
  pago del financing rate.

IA aceptó ese hallazgo en `5003219200`.

### R4

R4 incorporó `SftFinancingPaymentMode` y material de tenor/referencia de pago. DeepSeek
Expert R4 confirmó el cierre de R3-01 e identificó:

- `DS-EXPERT-UNR013-R4-01` — MarginLendingTerms no retenía la convención contractual de
  reset del financing rate flotante.

IA aceptó ese hallazgo en `5003271066`.

### R5

R5 incorpora `SftFinancingResetMode` y material de tenor/referencia de reset requerido por
modo, con prohibición explícita para tasa fija y exigencia explícita para tasa flotante.

R5 debe ser validado desde cero; ninguna conclusión anterior certifica este HEAD.

---

## 21. Estado de validación R5

Estado al guardar este documento:

- R1 = histórico;
- R2 = histórico;
- R3 = histórico;
- R4 = histórico tras el primer cambio R5;
- R5 candidate = presente;
- PRUEBAS COMPLETAS R5 = pendientes;
- CONGELADO R5 = no establecido;
- revisión externa R5 = en espera;
- Ready = no establecido;
- #394 = abierto;
- UNR-013 = no cerrado;
- UMI-14 = no cerrado;
- PROGRAM D = no cerrado;
- Production = cerrado;
- real capital = no autorizado.

Secuencia requerida después de fijar el HEAD final:

`PRUEBAS COMPLETAS -> REVISIÓN DEL DIFF -> CONGELAR R5 -> PRUEBAS COMPLETAS SOBRE SYNTHETIC EXACTO -> DEEPSEEK EXPERT R5 -> IA -> DEEPSEEK CODER R5 -> IA -> CLAUDE CODE R5 -> IA -> IA FINAL -> READY -> INTEGRAR CON HEAD ESPERADO -> VERIFICAR INTEGRACIÓN -> CERRAR #394 -> CONTINUAR UMI-14`

Cualquier cambio del HEAD después del CONGELADO R5 obliga a una nueva ronda desde DeepSeek
Expert.
