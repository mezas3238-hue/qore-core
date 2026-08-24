# QORE-UMI14-SECURITIES-FINANCING-SEMANTICS-001

## Estado

**PROGRAM D / UMI-14 — UNR-013 R8 CANDIDATA DE CIERRE — NO CERTIFICADA**

Tracker: #394  
Parent: #363  
PR: #437  
Target: `UMI13-UNR-013` — `securities-financing`  
Baseline certificado HASH: `db83b106f3a5e7f30a788567dfa970a38b7a379a`  
Tree inicial: `5b9c218a4fe3609b10e34b1cf8523cade0d10bbe`  
Rama: `agent/qore-umi14-securities-financing-full-closure-013`

R1–R7 son históricas. R8 corrige `CLAUDE-UNR013-R7-01`, aceptado por IA en review `5003563622`: `RepoTerms` conservaba rate, calculation y observation, pero no podía conservar de forma explícita la convención contractual de pago ni, para FLOATING, la convención de reset/re-fixing y colocación del fixing. Dos repos iguales en todo el material R7 podían por ello colapsar aun teniendo obligaciones temporales de financiación distintas.

Este responsable conserva únicamente semántica contractual estática D04. No observa índices, genera fechas, calcula tasas o intereses, calcula repurchase cash, valora collateral, ejecuta instrucciones, liquida operaciones, habilita Production ni autoriza capital real.

---

## 1. Alcance autorizado

La superficie respecto del baseline continúa limitada a exactamente tres archivos aditivos:

1. `src/qore/infrastructure/securities_financing_semantics.py`
2. `tests/infrastructure/test_securities_financing_semantics.py`
3. `docs/architecture/QORE-UMI14-SECURITIES-FINANCING-SEMANTICS-001.md`

Ningún archivo certificado previo se modifica.

Productos cubiertos:

- repo;
- securities lending;
- margin lending.

---

## 2. Valores comunes

Se reutilizan `EconomicIdentityId`, `DayCountConventionCode` y `FinancialTenor` con comprobación de tipo exacto y revalidación de estado interno.

Valores locales principales:

- `SftTermsId`;
- `SftEvidenceRef`;
- `SftPartyReferenceId`;
- `SftScheduleReferenceId`;
- `SftCollateralEligibilityCode`;
- `SftSecurityQuantityBasisCode`;
- `SftCompensationAccrualBasisCode`;
- `SftFinancingCalculationCode`.

Enums de convención de financiación reutilizados por repo y margin lending:

- `SftFinancingPaymentMode`;
- `SftFinancingResetMode`;
- `SftFinancingFixingTiming`;
- `SftFinancingObservationMode`.

Los códigos usan sintaxis canónica lowercase y máximo 64 caracteres.

`SftCashAmount` exige Decimal exacto, finito y positivo más currency identity.

`SftSecurityQuantity` exige security identity, cantidad Decimal exacta/positiva y `quantity_basis`. La base participa en identidad lógica; `units != nominal-amount`.

La canonicalización Decimal es independiente del contexto, conserva signed zero como `0` y mantiene exponentes extremos compactos.

---

## 3. Financing rate común

`SftRateTerms` conserva:

- `FIXED` o `FLOATING`;
- tasa contractual o spread;
- day count;
- referencia económica exacta cuando FLOATING.

FIXED prohíbe referencia flotante. FLOATING la exige.

`SftRateTerms` no pretende contener por sí solo todas las convenciones temporales o de cálculo de cada producto. Payment/reset/fixing/calculation/observation se conservan en el contrato que las necesita.

---

## 4. Duración, arrangement y margin/haircut

`SftDurationTerms` distingue `TERM`, `OPEN` y `CALLABLE`.

`SftArrangementTerms` distingue `BILATERAL` y `TRI_PARTY`; el segundo exige referencia exacta de agente.

`SftMarginTerms` conserva `initial_margin_ratio` y/o `haircut_ratio` como Decimal exacto, finito y no negativo. No representa current margin ni cálculo de riesgo.

---

## 5. Repo

`RepoTerms` conserva:

- instrumento;
- seller y buyer distintos;
- duración;
- near cash;
- basket no vacío de securities con quantity basis;
- financing rate;
- payment convention del financing return;
- reset/re-fixing convention cuando el financing rate es FLOATING;
- colocación contractual del fixing para reset periódico FLOATING;
- convención de calculation/observation cuando FLOATING;
- arrangement;
- referencia contractual técnica;
- far leg cuando corresponde;
- margin/haircut estático opcional.

TERM exige far leg compatible con la terminación contractual. OPEN no inventa far leg. CALLABLE sólo lo permite con terminación compatible.

Si se suministra far cash, su moneda debe coincidir con near cash. No se calcula repurchase cash.

El basket se canonicaliza por identidad/basis/cantidad y no acepta identidades duplicadas.

### 5.1 Payment de financiación

Todo repo conserva `financing_payment_mode` exacto:

- `PERIODIC`;
- `AT_TERMINATION`;
- `EXTERNAL_SCHEDULE`.

`PERIODIC` exige `financing_payment_tenor` exacto y prohíbe schedule reference.

`AT_TERMINATION` prohíbe tenor y schedule reference.

`EXTERNAL_SCHEDULE` exige `financing_payment_schedule_reference` exacta y prohíbe tenor.

La convención describe cuándo se debe pagar contractualmente el retorno de financiación. D04 no genera las fechas ni liquida el pago.

### 5.2 Reset / re-fixing FLOATING

Todo repo FLOATING conserva `financing_reset_mode` exacto:

- `PERIODIC`;
- `AT_PAYMENT`;
- `EXTERNAL_SCHEDULE`;
- `REFERENCE_CONVENTION`.

`PERIODIC` exige `financing_reset_tenor` exacto y `SftFinancingFixingTiming` exacto:

- `IN_ADVANCE`;
- `IN_ARREARS`;
- `REFERENCE_CONVENTION`.

`AT_PAYMENT` y `REFERENCE_CONVENTION` no aceptan tenor, schedule reference ni fixing timing adicional.

`EXTERNAL_SCHEDULE` exige `financing_reset_schedule_reference` exacta y no acepta tenor ni fixing timing adicional.

Repo FIXED prohíbe material de reset/fixing.

### 5.3 Calculation / observation FLOATING

Todo repo FLOATING exige:

- `financing_calculation: SftFinancingCalculationCode`;
- `financing_observation_mode: SftFinancingObservationMode`;
- `financing_observation_reference` sólo cuando observation mode es `EXTERNAL_TERMS`.

Modos de observación:

- `NONE`;
- `REFERENCE_CONVENTION`;
- `EXTERNAL_TERMS`.

La referencia externa de reset y la referencia externa de observation son material diferente y ocupan posiciones lógicas separadas. Un contrato puede delegar la frecuencia/calendario de reset a una referencia y, simultáneamente, identificar términos de observación adicionales mediante otra referencia.

Repo FIXED prohíbe calculation/observation material FLOATING.

### 5.4 Corrección R8

Para el mismo instrumento, parties, duración, cash, securities, benchmark/spread, day count, arrangement y demás material:

- `PERIODIC payment != AT_TERMINATION payment != EXTERNAL_SCHEDULE payment`;
- FLOATING `PERIODIC reset != AT_PAYMENT != EXTERNAL_SCHEDULE != REFERENCE_CONVENTION`;
- FLOATING `IN_ADVANCE != IN_ARREARS != REFERENCE_CONVENTION` cuando reset es periódico;
- diferentes reset schedule references producen identidad distinta;
- reset schedule reference y observation external reference no colapsan entre sí;
- calculation/observation continúan participando en identidad.

Esto cierra el witness de `CLAUDE-UNR013-R7-01` sin crear un motor temporal o de cálculo.

---

## 6. Securities lending

`SecuritiesLendingTerms` conserva lender/borrower, principal security, duración, compensation, collateralization, arrangement y margin terms opcionales.

`SecuritiesLendingCompensationTerms` mantiene separados lending fee y cash-collateral rebate.

Cada leg conserva:

- rate fijo/flotante;
- day count;
- referencia flotante cuando aplica;
- currency;
- accrual basis;
- payment mode;
- payment tenor o schedule reference;
- reset mode para FLOATING;
- reset tenor o schedule reference;
- colocación del fixing para reset periódico FLOATING;
- metodología contractual de cálculo FLOATING;
- modo de observación FLOATING;
- referencia externa de términos de observación cuando aplica.

### 6.1 Payment

Modos:

- `PERIODIC`;
- `AT_TERMINATION`;
- `EXTERNAL_SCHEDULE`.

`PERIODIC` exige tenor y prohíbe schedule reference. `AT_TERMINATION` prohíbe ambos. `EXTERNAL_SCHEDULE` exige referencia exacta y prohíbe tenor.

### 6.2 Reset FLOATING

Modos:

- `PERIODIC`;
- `AT_PAYMENT`;
- `EXTERNAL_SCHEDULE`;
- `REFERENCE_CONVENTION`.

`PERIODIC` exige reset tenor y `SftFinancingFixingTiming` exacto. Los otros modos aplican las mismas restricciones fail-closed establecidas en R7.

### 6.3 Calculation / observation FLOATING

Todo `SecuritiesLendingCompensationLegTerms` FLOATING exige:

- `floating_calculation: SftFinancingCalculationCode`;
- `floating_observation_mode: SftFinancingObservationMode`;
- `floating_observation_reference` sólo para `EXTERNAL_TERMS`.

Se mantiene cerrado `DS-EXPERT-UNR013-R6-01`:

- `daily-simple != daily-compounded`;
- `IN_ADVANCE != IN_ARREARS` cuando reset es periódico;
- `NONE != REFERENCE_CONVENTION != EXTERNAL_TERMS`;
- referencias externas distintas producen identidad distinta.

Un leg FIXED prohíbe reset/fixing/calculation/observation material flotante.

### 6.4 Collateralization

`SftCollateralizationMode` distingue:

- `UNCOLLATERALIZED`;
- `EXPLICIT`;
- `EXTERNAL_SCHEDULE`.

Los estados y referencias participan en identidad lógica.

---

## 7. Margin lending

`MarginLendingTerms` conserva credit limit contractual, financing rate, payment convention, reset convention, fixing timing, calculation/observation, eligibility estática, arrangement y margin terms opcionales.

Payment modes:

- `PERIODIC`;
- `AT_TERMINATION`;
- `EXTERNAL_SCHEDULE`.

Reset modes FLOATING:

- `PERIODIC`;
- `AT_PAYMENT`;
- `EXTERNAL_SCHEDULE`;
- `REFERENCE_CONVENTION`.

Para reset `PERIODIC` se exige `SftFinancingFixingTiming` exacto. Se mantienen los cierres R3–R6 correspondientes a margin lending.

Todo margin lending FLOATING exige además `SftFinancingCalculationCode`, `SftFinancingObservationMode` y referencia exacta sólo para `EXTERNAL_TERMS`.

FIXED prohíbe reset/fixing/calculation/observation material.

---

## 8. Identidad lógica y no-colapso

Las pruebas R8 deben demostrar al menos:

- repo != securities lending != margin lending;
- units != nominal-amount;
- securities-lending fee != cash-collateral rebate;
- uncollateralized != explicit != external-schedule collateralization;
- repo periodic payment != at-termination != external-schedule;
- repo periodic reset != at-payment != reference-convention != external-schedule;
- repo periodic + in-advance != periodic + in-arrears != reference-convention fixing;
- repo reset external reference y observation external reference permanecen separadas;
- repo FLOATING con distinta calculation/observation != misma identidad lógica;
- securities-lending compensation conserva todos los no-colapsos R7;
- margin lending conserva payment/reset/fixing/calculation/observation no-colapso;
- órdenes no económicos de baskets/sets se canonicalizan determinísticamente.

---

## 9. Bordes de composición

Los padres revalidan tipo exacto y estado interno relevante de hijos locales/importados. Objetos fabricados reflectivamente sin ejecutar constructor no reciben confianza sólo por pertenecer a la clase correcta.

Los tenores y referencias añadidos a repo se revalidan al construir y cada vez que `logical_values()` recompone el contrato. Mutación reflectiva posterior de hijos no evade la validación.

La superficie usa dataclasses `frozen=True, slots=True`, fechas explícitas, UUID explícitos y ausencia de estado global mutable.

---

## 10. Separación de responsabilidades

| Material | Responsable |
|---|---|
| Economic/security/currency/reference identity | UMI-02 / D04 |
| Day-count y tenor financiero estático | UMI-03 / D04 |
| SFT static terms y referencias estáticas | UNR-013 |
| Observaciones de mercado/collateral | D05 |
| Resolución de calendario/fechas | D06 |
| Devengo, fixing calculado, cashflow, pricing y valuation | D07 |
| Holdings y balances actuales | D08 |
| Margin/risk/exposure/capacity | D09 |
| Orders/execution/transfer instructions | D10 |
| Settlement/custody/collateral movement | D11 |
| Legal/regulatory/master-agreement determinations | D22 |

Payment mode, reset mode, fixing placement, calculation code y observation terms reference almacenados en D04 describen el contrato. No ejecutan esas convenciones.

---

## 11. Espacio negativo

R8 no contiene autoridad para:

- provider/network I/O;
- generación de payment/reset/fixing dates;
- observación de índices;
- cálculo de simple/compounded rate;
- cálculo de fixing, interés, accrual, repurchase price o cashflow;
- resolución operativa de lookback/lockout/observation shift;
- pricing/valuation;
- collateral valuation;
- posiciones, balances o utilization actuales;
- margin call/liquidation;
- locate/borrow availability;
- collateral movement/substitution/rehypothecation;
- recall/return;
- custody/settlement;
- execution/order submission;
- legal eligibility/KYC;
- wall clock implícito;
- UUID aleatorio/implícito;
- credenciales productivas;
- Production;
- capital real.

`STATIC PAYMENT CONVENTION != GENERATED PAYMENT DATE`

`STATIC RESET CONVENTION != OBSERVED RESET`

`STATIC FIXING PLACEMENT != OBSERVED FIXING`

`STATIC CALCULATION CODE != CALCULATED RATE`

`STATIC OBSERVATION TERMS REFERENCE != GENERATED OBSERVATION DATES`

---

## 12. Historial de rondas

R1 identificó compensación securities-lending incompleta y quantity basis ausente.

R2 cerró quantity basis y reforzó compensation; después se identificaron collateralization y timing incompletos.

R3 cerró collateralization/payment/reset de securities lending e identificó payment convention ausente en margin lending.

R4 añadió payment convention e identificó reset convention ausente en margin lending.

R5 añadió reset mode/tenor/reference; DeepSeek Expert identificó falta de `IN_ADVANCE`/`IN_ARREARS` en margin lending.

R6 corrigió ese punto y añadió calculation/observation para margin lending y repo FLOATING. DeepSeek Expert R6 identificó `DS-EXPERT-UNR013-R6-01` en fee/rebate FLOATING de securities lending.

R7 añadió fixing/calculation/observation al compensation leg de securities lending. DeepSeek Expert R7 y DeepSeek Coder R7 no encontraron defectos materiales. Claude Code R7 identificó `CLAUDE-UNR013-R7-01`: repo todavía carecía de payment/reset/fixing timing explícito. IA reprodujo y aceptó ese hallazgo como ALTA en review `5003563622`.

R8 reutiliza los tipos de financing timing ya presentes para cerrar esa colisión de repo. No cambia la autoridad del owner.

Toda conclusión R1–R7 queda histórica para sus hashes previos; R8 debe validarse desde cero.

---

## 13. Estado R8

Al guardar este documento:

- R1–R7 = históricas;
- R8 candidate = presente;
- `CLAUDE-UNR013-R7-01` = corrección implementada, pendiente de validación completa R8;
- PRUEBAS COMPLETAS del HEAD final = pendientes;
- CONGELADO R8 = no establecido;
- DeepSeek Expert R8 = EN ESPERA;
- DeepSeek Coder R8 = EN ESPERA;
- Claude Code R8 = EN ESPERA;
- IA Final R8 = EN ESPERA;
- Ready = no establecido;
- #394 = abierto;
- UNR-013 / UMI-14 / PROGRAM D = no cerrados;
- Production = cerrado;
- capital real = no autorizado.

Secuencia restante:

`PRUEBAS COMPLETAS -> REVISIÓN TÉCNICA -> CONGELAR R8 -> PRUEBAS COMPLETAS SOBRE SYNTHETIC EXACTO -> DEEPSEEK EXPERT R8 -> IA -> DEEPSEEK CODER R8 -> IA -> CLAUDE CODE R8 -> IA -> IA FINAL -> READY -> INTEGRAR CON HEAD ESPERADO -> VERIFICAR INTEGRACIÓN -> CERRAR #394 -> CONTINUAR UMI-14`

Cualquier cambio del HEAD después del CONGELADO obliga a una nueva ronda y reinicia la secuencia externa desde DeepSeek Expert.
