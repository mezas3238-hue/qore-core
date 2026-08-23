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
`DS-EXPERT-UNR013-R5-01`: un reset flotante periódico de margin lending necesita retener
si el fixing contractual ocurre `IN_ADVANCE`, `IN_ARREARS` o conforme a la convención de
la referencia.

Este responsable continúa limitado a semántica contractual estática D04. No observa,
calcula, ejecuta, liquida, valora, genera calendarios, opera custodias, habilita Production
ni autoriza capital real.

---

## 1. Alcance

UMI-13 retuvo:

`UMI13-UNR-013 — securities-financing — repo/securities lending/margin lending — distinct SFT forms; no dedicated owner`.

La superficie sigue siendo exactamente tres archivos aditivos respecto del baseline:

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

No existe en el baseline un contrato genérico cross-product de fixing que pueda importarse
sin trasladar semántica específica de otro responsable. Por eso R6 conserva un enum local
mínimo para la colocación temporal del fixing periódico.

---

## 3. Referencias locales

### `SftTermsId`

UUID explícito de términos SFT.

### `SftEvidenceRef`

Referencia UUID opaca a respaldo contractual retenido.

### `SftPartyReferenceId`

Referencia UUID opaca de parte contractual; no afirma identidad legal, KYC, cuenta ni LEI.

### `SftScheduleReferenceId`

Referencia UUID opaca a material contractual estático externo de calendario/términos. No
genera fechas ni resuelve calendarios.

---

## 4. Códigos canónicos

Usan código lowercase canónico, no vacío y de máximo 64 caracteres:

- `SftCollateralEligibilityCode`;
- `SftSecurityQuantityBasisCode`;
- `SftCompensationAccrualBasisCode`.

Sintaxis:

`[a-z0-9]+(?:[._-][a-z0-9]+)*`

---

## 5. Dinero y cantidades de securities

### `SftCashAmount`

Conserva monto Decimal exacto, finito y positivo más `currency_identity_id` exacto.

### `SftSecurityQuantity`

Conserva:

- `security_identity_id`;
- cantidad Decimal exacta, finita y positiva;
- `quantity_basis`.

La base de cantidad forma parte de identidad lógica. Por tanto `units` y
`nominal-amount` no colapsan para la misma security y el mismo número.

Esto mantiene cerrado `DS-EXPERT-UNR013-R1-02` salvo una nueva demostración material.

---

## 6. Financing rate común

`SftRateTerms` conserva:

- FIXED o FLOATING;
- tasa contractual o spread;
- day count;
- referencia económica exacta cuando FLOATING.

FIXED prohíbe referencia flotante. FLOATING la exige.

`SftRateTerms` no pretende contener por sí solo cada convención temporal de cada producto.
Las convenciones contractuales adicionales se conservan en el contrato que las necesita.

No observa el índice, no calcula fixing, all-in rate, devengo ni interés.

---

## 7. Duración

`SftDurationTerms` distingue TERM, OPEN y CALLABLE.

TERM exige fecha de terminación y no notice period. OPEN no inventa una terminación.
CALLABLE exige notice days positivo y puede retener una fecha final contractual opcional.

No representa estado actual de ejercicio o terminación.

---

## 8. Arrangement

`SftArrangementTerms` distingue BILATERAL y TRI_PARTY.

BILATERAL prohíbe agente tri-party. TRI_PARTY exige `SftPartyReferenceId` exacto para el
agente.

---

## 9. Margin/haircut estático

`SftMarginTerms` conserva `initial_margin_ratio` y/o `haircut_ratio` como Decimal exacto,
finito y no negativo.

No se impone una ley universal `<= 1` no demostrada. Son términos contractuales, no current
margin ni cálculo de riesgo.

---

## 10. Repo

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

TERM exige far leg y coincidencia con la terminación contractual. OPEN prohíbe inventarlo.
CALLABLE sólo lo permite con terminación contractual compatible.

Si se suministra far cash, su moneda debe coincidir con near cash. No se calcula repurchase
cash.

---

## 11. Securities lending — compensación

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

Esto mantiene cerrados `DS-EXPERT-UNR013-R1-01` y `DS-EXPERT-UNR013-R2-02` salvo una nueva
demostración material.

---

## 12. Securities lending — collateralization

`SftCollateralizationMode` distingue:

- `UNCOLLATERALIZED`;
- `EXPLICIT`;
- `EXTERNAL_SCHEDULE`.

UNCOLLATERALIZED exige tuple vacío y sin referencia externa. EXPLICIT exige tuple no vacío
y sin referencia externa. EXTERNAL_SCHEDULE exige referencia exacta y puede retener además
items estáticos explícitos.

El modo y la referencia forman parte de identidad lógica. Esto mantiene cerrado
`DS-EXPERT-UNR013-R2-01` salvo una nueva demostración material.

---

## 13. Margin lending — payment

R4 introdujo `SftFinancingPaymentMode` para cerrar `DS-EXPERT-UNR013-R3-01`:

- `PERIODIC`;
- `AT_TERMINATION`;
- `EXTERNAL_SCHEDULE`.

PERIODIC exige tenor financiero exacto y prohíbe schedule reference. AT_TERMINATION prohíbe
ambos. EXTERNAL_SCHEDULE exige `SftScheduleReferenceId` y prohíbe tenor.

La convención de pago forma parte de identidad lógica.

---

## 14. Margin lending — reset

R5 introdujo `SftFinancingResetMode` para cerrar `DS-EXPERT-UNR013-R4-01`:

- `PERIODIC`;
- `AT_PAYMENT`;
- `EXTERNAL_SCHEDULE`;
- `REFERENCE_CONVENTION`.

FIXED prohíbe material de reset. FLOATING exige reset mode exacto.

PERIODIC exige tenor. AT_PAYMENT no acepta tenor ni referencia. EXTERNAL_SCHEDULE exige
referencia externa. REFERENCE_CONVENTION delega la regla de reset al material contractual
de la referencia.

---

## 15. Margin lending — R6 fixing placement

### Hallazgo R5 aceptado

DeepSeek Expert R5 identificó `DS-EXPERT-UNR013-R5-01`.

R5 podía representar dos contratos con el mismo:

- floating reference;
- spread;
- day count;
- payment mensual;
- reset periódico mensual;
- resto del material;

pero uno con fixing `IN_ADVANCE` y otro `IN_ARREARS`.

Como R5 sólo retenía reset mode + tenor, ambos podían proyectar la misma identidad lógica.

La distinción es estática: define la colocación contractual del fixing respecto del período
de devengo. D05 puede aportar observaciones, D06 resolver fechas y D07 calcular intereses,
pero esos responsables no sustituyen la regla contractual.

### Corrección R6

R6 añade `SftFinancingFixingTiming`:

- `IN_ADVANCE = "in-advance"`;
- `IN_ARREARS = "in-arrears"`;
- `REFERENCE_CONVENTION = "reference-convention"`.

El campo nuevo es:

`financing_fixing_timing: SftFinancingFixingTiming | None`.

La regla es intencionalmente acotada:

### FLOATING + PERIODIC reset

- `financing_reset_tenor` exacto y positivo requerido;
- `financing_fixing_timing` exacto requerido;
- external reset schedule reference prohibida.

Esto permite distinguir, para el mismo tenor:

`IN_ADVANCE != IN_ARREARS != REFERENCE_CONVENTION`.

### FLOATING + AT_PAYMENT

- tenor prohibido;
- external schedule reference prohibida;
- `financing_fixing_timing` adicional prohibido.

El propio modo ya fija el trigger contractual y no necesita un segundo calificador.

### FLOATING + REFERENCE_CONVENTION

- tenor prohibido;
- external schedule reference prohibida;
- `financing_fixing_timing` adicional prohibido.

El propio modo delega la convención temporal completa al material contractual de la
referencia; duplicar un segundo valor podría crear contradicción.

### FLOATING + EXTERNAL_SCHEDULE

- `SftScheduleReferenceId` exacto requerido;
- tenor prohibido;
- `financing_fixing_timing` adicional prohibido.

La referencia externa identifica el material contractual que gobierna las fechas de reset;
no se introduce un segundo schedule reference de fixing que pueda divergir del primero.

### FIXED

Todo material de reset/fixing está prohibido.

La identidad lógica R6 del reset de margin lending es:

`(reset_mode, reset_tenor | None, reset_schedule_reference | None, fixing_timing | None)`.

Por tanto el par material que originó R6 ya no colapsa.

---

## 16. Alcance de `REFERENCE_CONVENTION`

`REFERENCE_CONVENTION` es una delegación estática explícita, no una observación implícita.

Cuando se usa como fixing timing de un reset periódico, indica que la colocación temporal
es la definida por el material contractual de la referencia. Cuando se usa como reset mode,
la propia frecuencia/trigger también queda gobernada por ese material.

R6 no afirma que este enum sea una metodología universal de tasas flotantes. Convenciones
como simple/compounded, lookback, lockout u observation shift sólo deben añadirse aquí si
una revisión futura demuestra un par contractual material que no puede distinguirse por la
referencia contractual o por una referencia externa ya retenida.

---

## 17. Margin lending — collateral eligibility

`SftCollateralEligibilityCode` conserva la calificación contractual canónica.

`eligible_collateral_identity_ids` puede estar vacío o contener identidades exactas,
únicas y canonicalizadas. No representa collateral actual ni disponibilidad.

---

## 18. Identidad lógica

Cada producto comienza con un discriminante distinto:

- `repo`;
- `securities-lending`;
- `margin-lending`.

Para margin lending R6, la proyección incluye:

1. discriminante;
2. terms ID;
3. instrument ID;
4. lender;
5. borrower;
6. duration;
7. credit limit;
8. financing rate;
9. financing payment convention;
10. financing reset + fixing convention o `None` para tasa fija;
11. collateral eligibility;
12. eligible collateral identities;
13. arrangement;
14. optional static margin terms;
15. respaldo contractual.

Casos de no-colapso requeridos por pruebas R6 incluyen:

- periodic payment != at termination != external schedule;
- periodic reset != at-payment != external schedule != reference convention;
- periodic 1 month + in-advance != periodic 1 month + in-arrears;
- periodic explicit timing != periodic reference convention;
- units != nominal-amount;
- fee != rebate;
- uncollateralized != explicit != external-schedule collateralization;
- repo != securities lending != margin lending.

---

## 19. Determinismo Decimal

Todo material numérico usa Decimal exacto y finito. Subclases se rechazan.

La representación lógica:

- usa `Decimal.as_tuple()`;
- canonicaliza signed zero a `"0"`;
- elimina ceros finales del coeficiente;
- no depende de `Decimal.normalize()`;
- no depende de precisión ambiental;
- conserva exponentes extremos en representación compacta cuando corresponde.

---

## 20. Bordes de composición

Los padres revalidan hijos locales/importados y su estado interno relevante. Entre otros:

- UUID wrappers;
- EconomicIdentityId;
- DayCountConventionCode;
- FinancialTenor y FinancialTenorUnit;
- quantity basis;
- compensation accrual basis;
- schedule references;
- compensation payment/reset modes;
- financing payment/reset modes;
- financing fixing timing;
- collateralization mode;
- cash/security children;
- compensation legs;
- top-level product terms.

Un objeto exacto fabricado sin su constructor no recibe confianza sólo por su clase.

---

## 21. Límites de autoridad

| Material | Responsable |
|---|---|
| Economic/security/currency/reference identity | UMI-02 / D04 |
| Day-count y tenor financiero estático | UMI-03 / D04 |
| SFT static terms y referencias de schedule | este UNR-013 |
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

`STATIC FIXING PLACEMENT != OBSERVED FIXING`

`STATIC RESET CONVENTION != GENERATED RESET DATES`

`STATIC COLLATERALIZATION != CURRENT COLLATERAL STATE`

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

R4 añadió la convención de pago y se identificó:

- `DS-EXPERT-UNR013-R4-01` — margin lending flotante sin convención de reset.

### R5

R5 añadió reset mode/tenor/reference. DeepSeek Expert confirmó el cierre de R4-01 e
identificó:

- `DS-EXPERT-UNR013-R5-01` — reset periódico sin distinción fixing in-advance/in-arrears.

### R6

R6 añade `SftFinancingFixingTiming` y lo exige únicamente para reset flotante PERIODIC.

R6 debe validarse desde cero; ninguna conclusión anterior certifica este HEAD.

---

## 24. Estado de validación R6

Estado al guardar este documento:

- R1–R5 = históricos;
- R6 candidate = presente;
- PRUEBAS COMPLETAS R6 = pendientes;
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
