# QORE-UMI14-SECURITIES-FINANCING-SEMANTICS-001

## Estado

**PROGRAM D / UMI-14 — UNR-013 R6 CANDIDATA DE CIERRE — NO CERTIFICADA**

Tracker: #394  
Parent: #363  
PR: #437  
Target: `UMI13-UNR-013` — `securities-financing`  
Baseline certificado HASH: `db83b106f3a5e7f30a788567dfa970a38b7a379a`  
Tree inicial: `5b9c218a4fe3609b10e34b1cf8523cade0d10bbe`  
Rama: `agent/qore-umi14-securities-financing-full-closure-013`

R1–R5 son históricas. R6 incorpora la corrección aceptada para `DS-EXPERT-UNR013-R5-01` y dos comprobaciones IA adicionales realizadas antes del CONGELADO: convenciones flotantes materiales de margin lending y repo no pueden depender sólo de la identidad de la referencia económica.

Este responsable conserva únicamente semántica contractual estática D04. No observa índices, genera fechas, calcula tasas/intereses, valora collateral, ejecuta instrucciones, liquida operaciones, habilita Production ni autoriza capital real.

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
- `SftEvidenceRef` como identificador técnico histórico del código;
- `SftPartyReferenceId`;
- `SftScheduleReferenceId`;
- `SftCollateralEligibilityCode`;
- `SftSecurityQuantityBasisCode`;
- `SftCompensationAccrualBasisCode`;
- `SftFinancingCalculationCode`.

Los códigos usan sintaxis canónica lowercase y máximo 64 caracteres.

`SftCashAmount` exige Decimal exacto, finito y positivo más currency identity.

`SftSecurityQuantity` exige security identity, cantidad Decimal exacta/positiva y `quantity_basis`. La base participa en identidad lógica; por tanto `units != nominal-amount`.

La canonicalización Decimal es independiente del contexto, conserva signed zero como `0` y mantiene exponentes extremos compactos.

---

## 3. Financing rate común

`SftRateTerms` conserva:

- `FIXED` o `FLOATING`;
- tasa contractual o spread;
- day count;
- referencia económica exacta cuando FLOATING.

FIXED prohíbe referencia flotante. FLOATING la exige.

`SftRateTerms` no pretende contener por sí solo todas las convenciones temporales o de cálculo de cada producto. Las dimensiones adicionales se conservan en el contrato que las necesita.

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
- arrangement;
- referencia contractual técnica;
- far leg cuando corresponde;
- margin/haircut estático opcional;
- convención adicional de cálculo/observación cuando el financing rate es FLOATING.

TERM exige far leg compatible con la terminación contractual. OPEN no inventa far leg. CALLABLE sólo lo permite con terminación compatible.

Si se suministra far cash, su moneda debe coincidir con near cash. No se calcula repurchase cash.

El basket se canonicaliza por identidad/basis/cantidad y no acepta identidades duplicadas.

### Repo flotante R6

Un repo FLOATING exige:

- `financing_calculation: SftFinancingCalculationCode`;
- `financing_observation_mode: SftFinancingObservationMode`;
- `financing_observation_reference` sólo cuando el modo es `EXTERNAL_TERMS`.

Modos de observación:

- `NONE`;
- `REFERENCE_CONVENTION`;
- `EXTERNAL_TERMS`.

Esto evita que dos repos con el mismo benchmark/spread/day count pero distinta metodología contractual u otros términos de observación queden representados como el mismo material. La referencia externa identifica términos estáticos como lookback/observation mechanics sin generar fechas ni calcular la tasa.

Repo FIXED prohíbe esos campos flotantes.

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

`SftCollateralizationMode` distingue:

- `UNCOLLATERALIZED`;
- `EXPLICIT`;
- `EXTERNAL_SCHEDULE`.

Los tres estados y sus referencias participan en identidad lógica.

---

## 7. Margin lending

`MarginLendingTerms` conserva credit limit contractual, financing rate, payment convention, reset convention, eligibility estática, arrangement y margin terms opcionales.

Payment modes:

- `PERIODIC`;
- `AT_TERMINATION`;
- `EXTERNAL_SCHEDULE`.

Reset modes FLOATING:

- `PERIODIC`;
- `AT_PAYMENT`;
- `EXTERNAL_SCHEDULE`;
- `REFERENCE_CONVENTION`.

### Corrección R6 — fixing placement

Para reset `PERIODIC`, R6 exige `SftFinancingFixingTiming` exacto:

- `IN_ADVANCE`;
- `IN_ARREARS`;
- `REFERENCE_CONVENTION`.

Esto cierra `DS-EXPERT-UNR013-R5-01`: dos contratos con la misma referencia, spread, day count, payment y reset tenor pero distinto fixing placement ya no comparten identidad lógica.

`AT_PAYMENT`, `REFERENCE_CONVENTION` y `EXTERNAL_SCHEDULE` no aceptan un fixing timing adicional porque el propio modo define o delega la colocación temporal.

### Cálculo y observación FLOATING

Todo margin lending FLOATING exige además:

- `SftFinancingCalculationCode`;
- `SftFinancingObservationMode`;
- referencia exacta sólo para `EXTERNAL_TERMS`.

Ejemplos de códigos canónicos posibles incluyen `daily-simple`, `daily-compounded` y `reference-convention`.

Así, para el mismo benchmark y demás material, `daily-simple != daily-compounded`.

El modo `EXTERNAL_TERMS` permite identificar material estático adicional como lookback/lockout/observation-shift/calendario sin trasladar a D04 la generación de fechas ni el cálculo financiero.

FIXED prohíbe reset/fixing/calculation/observation material.

---

## 8. Identidad lógica y no-colapso

Las pruebas R6 deben demostrar al menos:

- repo != securities lending != margin lending;
- units != nominal-amount;
- securities-lending fee != cash-collateral rebate;
- uncollateralized != explicit != external-schedule collateralization;
- periodic payment != at-termination != external-schedule;
- periodic reset != at-payment != reference-convention != external-schedule;
- periodic + in-advance != periodic + in-arrears;
- daily-simple != daily-compounded;
- observation `NONE != REFERENCE_CONVENTION != EXTERNAL_TERMS`;
- distintas referencias externas != mismo material;
- repo FLOATING con distinta convención de cálculo/observación != misma identidad lógica.

Los órdenes no económicos de baskets/sets se canonicalizan determinísticamente.

---

## 9. Bordes de composición

Los padres revalidan tipo exacto y estado interno relevante de hijos locales/importados. Objetos fabricados reflectivamente sin ejecutar constructor no reciben confianza sólo por pertenecer a la clase correcta.

La superficie usa dataclasses `frozen=True, slots=True`, timestamps no implícitos, UUID explícitos y ausencia de estado global mutable.

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

---

## 11. Espacio negativo

R6 no contiene autoridad para:

- provider/network I/O;
- generación de payment/reset/fixing dates;
- observación de índices;
- cálculo de simple/compounded rate;
- cálculo de fixing, interés, accrual o cashflow;
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

`STATIC CALCULATION CODE != CALCULATED RATE`

`STATIC OBSERVATION TERMS REFERENCE != GENERATED OBSERVATION DATES`

`STATIC FIXING PLACEMENT != OBSERVED FIXING`

---

## 12. Historial de rondas

R1 cerró compensación securities-lending y quantity basis.

R2 cerró collateralization explícita/externa y ambigüedad de payment/reset en securities lending.

R3 identificó payment convention ausente en margin lending.

R4 añadió payment convention e identificó reset convention ausente.

R5 añadió reset mode/tenor/reference; DeepSeek Expert confirmó ese cierre e identificó `DS-EXPERT-UNR013-R5-01` por falta de `IN_ADVANCE`/`IN_ARREARS`.

R6 corrige ese hallazgo y, antes del CONGELADO, amplía preventivamente calculation/observation para margin lending y repo FLOATING donde IA demostró pares contractuales materiales adicionales.

Toda conclusión R1–R5 queda histórica para sus HASH anteriores; R6 debe validarse desde cero.

---

## 13. Estado R6

Al guardar este documento:

- R1–R5 = históricas;
- R6 candidate = presente;
- PRUEBAS COMPLETAS del HEAD final = pendientes;
- CONGELADO R6 = no establecido;
- DeepSeek Expert R6 = EN ESPERA;
- DeepSeek Coder R6 = EN ESPERA;
- Claude Code R6 = EN ESPERA;
- Ready = no establecido;
- #394 = abierto;
- UNR-013 / UMI-14 / PROGRAM D = no cerrados;
- Production = cerrado;
- capital real = no autorizado.

Secuencia restante:

`PRUEBAS COMPLETAS -> REVISIÓN TÉCNICA -> CONGELAR R6 -> PRUEBAS COMPLETAS SOBRE SYNTHETIC EXACTO -> DEEPSEEK EXPERT R6 -> IA -> DEEPSEEK CODER R6 -> IA -> CLAUDE CODE R6 -> IA -> IA FINAL -> READY -> INTEGRAR CON HEAD ESPERADO -> VERIFICAR INTEGRACIÓN -> CERRAR #394 -> CONTINUAR UMI-14`

Cualquier cambio del HEAD después del CONGELADO obliga a una nueva ronda y reinicia la secuencia externa desde DeepSeek Expert.
