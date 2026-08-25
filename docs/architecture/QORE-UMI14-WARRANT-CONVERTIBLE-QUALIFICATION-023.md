# QORE-UMI14-WARRANT-CONVERTIBLE-QUALIFICATION-023

## Estado

**PROGRAM D / UMI-14 — UNR-023 CANDIDATE**

Tracking: #451  
Parent: #363  
Base de construcción: `dab8524533a5cbb5605261b00d83a8d857a04d84`

## Objetivo

Cerrar `UMI13-UNR-023` con una calificación D04 acotada para estructuras warrant y
convertible que reutilice la economía ya representada por UMI-05 y UMI-09.

La entrega no crea una segunda semántica de opción, una segunda semántica de
conversión ni una nueva familia universal de equity-linked products.

```text
WARRANT QUALIFICATION
!= OPTION ECONOMICS

CONVERTIBLE QUALIFICATION
!= CONVERSION ENGINE

TARGET EQUITY QUALIFICATION
!= EQUITY TERMS DUPLICATION
```

## 1. Alcance retenido

UMI-13 conserva el pendiente:

`equities — warrant / convertible cross-family structural-payoff qualification`

UMI-06 deja warrant/structured payoff fuera de su contrato estático. UMI-05 y UMI-09
contienen piezas económicas reutilizables, pero no certifican por sí solas la unión
transversal entre el instrumento fuente y el equity objetivo.

La entrega representa exactamente dos categorías:

- `warrant`;
- `convertible`.

No constituye una taxonomía universal de warrants, convertibles ni equity-linked
securities.

## 2. Forma superior

`WarrantConvertibleQualification` conserva:

- `WarrantConvertibleQualificationId` suministrado por llamador;
- categoría exacta `WARRANT | CONVERTIBLE`;
- unión tipada exacta:
  - `EquityWarrantQualificationTerms`;
  - `ConvertibleQualificationTerms`;
- `WarrantConvertibleEvidenceRef` suministrado por llamador.

Categoría y variante deben coincidir exactamente.

No existe reloj implícito, UUID generado, estado global mutable ni fuente externa.

## 3. Warrant

`EquityWarrantQualificationTerms` conserva:

- identidad económica completa del warrant;
- identidad económica completa del equity objetivo;
- `OptionContractTerms` existente de UMI-05.

Leyes:

1. `option_terms.instrument_identity_id == warrant_identity.identity_id`;
2. `option_terms.underlying_identity_id == target_equity_identity.identity_id`;
3. warrant y target equity son identidades distintas;
4. target equity demuestra familia exacta `equities`;
5. no se impone una familia raíz al warrant por inferencia desde la fila UMI-13.

UMI-05 sigue siendo responsable de:

- right;
- strike;
- exercise style/dates;
- expiry;
- settlement identity/style;
- multiplier/notional;
- respaldo del contrato de opción.

UNR-023 no vuelve a definir esos significados.

## 4. Convertible

`ConvertibleQualificationTerms` conserva:

- identidad económica completa del instrumento convertible;
- identidad económica completa del equity objetivo;
- `StructuredConversionFeature` existente de UMI-09;
- `credit_leg_identity` opcional sólo cuando exista un tramo crediticio canónico
  material para la estructura.

Leyes:

1. `conversion_feature.target_identity_id == target_equity_identity.identity_id`;
2. convertible y target equity son identidades distintas;
3. target equity demuestra familia exacta `equities`;
4. si `credit_leg_identity` está presente, demuestra familia
   `fixed-income-credit` y no puede ser el equity objetivo;
5. no se impone una familia raíz única al convertible.

UMI-09 sigue siendo responsable de:

- `units_per_source_unit`;
- optional conversion level;
- target identity del feature;
- respaldo propio del feature;
- ausencia de ejecución de conversión.

UNR-023 no duplica ratio ni nivel de conversión.

## 5. Identidad económica

Toda `EconomicIdentity` almacenada se revalida por estado con tipos exactos:

- `EconomicIdentity`;
- `EconomicIdentityId` + UUID interno exacto;
- `EconomicIdentityKind`;
- `IdentityFamilyCode` + `str` exacto y código canónico;
- `IdentityConstructionKind`;
- `IdentityEvidenceRef` + UUID interno exacto.

También se reaplica exactamente la regla UMI-02:

```text
CONTINUOUS_REFERENCE -> REFERENCE_OBJECT
```

No se exige procedencia de construcción. Un objeto fabricado con estado enteramente
válido es indistinguible contractualmente de otro creado por el constructor normal;
lo material es el estado validable.

## 6. Revalidación de `OptionContractTerms`

La calificación no confía ciegamente en validaciones históricas permisivas de UMI-05.
Antes de emitir `logical_values()` vuelve a validar por estado:

- `DerivativeTermsId` + UUID;
- tres `EconomicIdentityId` + UUID interno;
- relaciones instrument/underlying/settlement retenidas por UMI-05;
- `OptionRight` exacto;
- `DerivativeStrike` y sus variantes estructurales;
- `OptionExerciseTerms`, estilos, fechas y orden Bermudan;
- expiry exacto;
- settlement style exacto;
- `DerivativeEvidenceRef` + UUID;
- multiplier/notional exactos, Decimals finitos positivos y unidades canónicas.

La economía sigue siendo de UMI-05; esta revalidación sólo evita que estado importado
corrompido o subclases sean promovidos por la nueva frontera.

## 7. Revalidación de `StructuredConversionFeature`

La calificación vuelve a validar:

- `StructuredFeatureId` + UUID;
- target `EconomicIdentityId` + UUID;
- `StructuredPositiveRatio` con Decimal exacto, finito y positivo;
- `StructuredEvidenceRef` + UUID;
- optional `StructuredContractLevel` con Decimal exacto, enum exacto, identidad de
  referencia exacta y unidad canónica exacta.

No ejecuta conversión ni observa niveles de mercado.

## 8. Decimal y determinismo

Los Decimals importados se serializan con representación determinista y compacta.
La decisión entre representación fija y científica se toma antes de materializar una
cadena fija extensa, evitando crecimiento innecesario para exponentes extremos.

Esto no altera el valor económico y no introduce aritmética de payoff o valoración.

`logical_values()` revalida recursivamente antes de emitir la representación.

## 9. Reutilización de UMI-06

UMI-06 mantiene autoridad sobre `EquitySecurityTerms`, incluido emisor, clase y otras
semánticas equity ya existentes. UNR-023 no copia issuer/share-class ni crea un segundo
contrato de equity.

La regla transversal que necesita UNR-023 es más estrecha: la identidad completa del
target debe demostrar familia `equities` y coincidir con el target del contrato
UMI-05/09 enlazado.

## 10. Casos de prueba retenidos

La suite demuestra al menos:

- conjunto exacto warrant/convertible;
- categoría/variante incompatible rechazada;
- warrant identity ↔ option instrument mismatch rechazado;
- target equity ↔ option underlying mismatch rechazado;
- target equity ↔ conversion target mismatch rechazado;
- target no-equity rechazado;
- optional credit leg con familia incorrecta rechazado;
- ninguna familia raíz warrant/convertible inventada desde UMI-13;
- regla UMI-02 continuous-reference reaplicada;
- corrupción posterior de UUID interno, strike Decimal, exercise enum y conversion
  ratio rechazada por `logical_values()`;
- UUID/str subclass laundering rechazado;
- Decimal de exponente extremo emitido de forma compacta;
- ausencia de reloj/UUID implícito y de autoridad operativa.

## 11. Límites explícitos

Esta entrega no:

- calcula precio o valor de conversión;
- calcula paridad, delta, Greeks o valoración;
- decide ejercicio;
- decide o ejecuta conversión;
- genera órdenes ni movimientos de valores/efectivo;
- consulta proveedor o venue;
- liquida instrumentos;
- modifica Risk o cuentas;
- habilita Production o capital real.

## 12. Criterio de cierre

UNR-023 puede cerrarse sólo si código, pruebas y este documento permanecen alineados,
las PRUEBAS COMPLETAS son OK, la revisión técnica serial no deja hallazgos materiales
y la integración se verifica sobre el HASH esperado.
