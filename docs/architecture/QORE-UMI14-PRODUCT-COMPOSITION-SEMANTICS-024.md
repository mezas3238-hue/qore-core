# QORE-UMI14-PRODUCT-COMPOSITION-SEMANTICS-024

## Estado

**PROGRAM D / UMI-14 — UNR-024 CANDIDATE**

Tracking: #452  
Parent: #363  
Base de construcción: `5525e955307d3de715c0e22e2e51be1ad3283fa7`

## Objetivo

Cerrar `UMI13-UNR-024` con una semántica D04 acotada para composiciones
product-specific de tipo basket, spread y multi-leg cuando la estructura no puede
expresarse mediante UMI-05 o UMI-09 sin inventar material económico.

La entrega preserva estas fronteras:

```text
PRODUCT COMPOSITION
!= DERIVATIVE COMPOSITION BY IMPLICATION

UNORDERED PRODUCT
!= ORDERED PRODUCT WITH INVENTED ORDINALS

PRODUCT ROLE / MAGNITUDE
!= UNDERLYING FAMILY ECONOMICS

COMPOSITION TERMS
!= PAYOFF / VALUATION / REBALANCING / ROUTING
```

## 1. Reconstrucción de propietarios existentes

### UMI-05

`DerivativeCompositionTerms` ya representa una composición derivada con:

- `DerivativeLegId`;
- `DerivativeLegOrdinal` obligatorio;
- `EconomicIdentityId` de componente;
- LONG / SHORT;
- ratio Decimal positivo;
- evidencia.

La raíz exige component identities únicas, ordinales únicos y contiguos `1..N`, y
canoniza por ordinal.

Por tanto, si el producto es exactamente una composición derivada
LONG/SHORT/ratio con secuencia contractual, UMI-05 sigue siendo el propietario.

UNR-024 no copia ni reemplaza `DerivativeCompositionTerms`.

### UMI-09

`StructuredHybridSyntheticTerms` usa `StructuredComponentBinding` para relacionar la
identidad raíz con componentes mediante `IdentityRelationship`, y añade features
higher-order.

Los bindings se canonizan set-like por `relationship_id`; UMI-09 no convierte esos
bindings en una secuencia contractual global ni define pesos/cantidades product-specific.

UNR-024 no copia relaciones UMI-02 ni features UMI-09.

## 2. Superficie nueva

La entrega añade exactamente:

- `ProductCompositionTerms`;
- `ProductCompositionLeg`;
- `ProductCompositionMagnitude`;
- wrappers/enums locales mínimos para IDs, evidencia, rol, ordinal, clase, modo,
  dirección y clase de magnitud.

No modifica propietarios certificados anteriores.

## 3. Versión y clase

`ProductCompositionTerms.logical_values()` comienza con:

`product-composition.v1`

Ese tag versiona el esquema lógico de esta superficie.

La clase económica es exactamente:

- `BASKET`;
- `SPREAD`;
- `MULTI_LEG`.

La clase no decide por sí sola si la composición es ordenada o no ordenada.

## 4. Identidad

La raíz y cada componente reutilizan `EconomicIdentityId` de UMI-02.

No se almacena `EconomicIdentity` completo porque UNR-024 no necesita demostrar una
familia económica concreta. Las economías de equity, futures, FX, commodity, rates u
otras familias permanecen bajo sus propietarios.

Toda `EconomicIdentityId` almacenada es revalidada por:

- tipo exacto;
- UUID interno exacto.

La raíz no puede aparecer como componente de sí misma.

## 5. Modo de orden

`ProductCompositionMode` distingue exactamente:

### `ORDERED_CONTRACTUAL`

El orden forma parte de los términos.

Reglas:

- todo leg debe llevar `ProductCompositionLegOrdinal`;
- ordinal exacto `int`, no `bool`;
- ordinal positivo;
- ordinales únicos;
- secuencia contigua `1..N`;
- caller-order se sustituye por ordinal contractual.

### `UNORDERED_CANONICAL`

El caller-order no tiene significado económico.

Reglas:

- ningún leg puede llevar ordinal;
- no se inventa ordinal para reutilizar UMI-05;
- la colección se canoniza por material semántico del leg.

La clave canónica usa:

- component identity;
- role;
- optional direction;
- magnitude kind;
- magnitude Decimal canónico;
- optional quantity unit.

No usa `leg_id` ni evidence para decidir orden económico.

## 6. Leg

`ProductCompositionLeg` conserva:

- `ProductCompositionLegId` local;
- `EconomicIdentityId` del componente;
- `ProductCompositionRoleCode` extensible;
- `ProductCompositionMagnitude`;
- `ProductCompositionEvidenceRef`;
- optional `ProductCompositionDirection` LONG / SHORT;
- optional ordinal, permitido sólo por el modo de la raíz.

El role code es material product-specific. No pretende reemplazar relaciones UMI-02
ni crear una taxonomía universal de roles.

Direction es opcional porque no toda composición product-specific expresa una
posición LONG/SHORT.

## 7. Magnitud

`ProductCompositionMagnitudeKind` distingue:

- `RATIO`;
- `WEIGHT`;
- `QUANTITY`.

Todo valor debe ser un `Decimal` exacto, finito y positivo.

El signo económico no se codifica usando un Decimal negativo. Cuando sea material,
LONG/SHORT lo expresa `direction`.

### RATIO / WEIGHT

No aceptan unidad económica. Una unidad inventada para un ratio o peso sería
distorsión semántica.

### QUANTITY

Puede llevar `unit_identity_id: EconomicIdentityId`.

`unit_identity_id is None` significa que la cantidad contractual es adimensional.
Cuando la cantidad tiene unidad económica, la identidad de unidad debe conservarse
explícitamente.

UNR-024 no interpreta ni convierte unidades.

## 8. Duplicado semántico

`leg_id` y evidence son trazabilidad local, no una justificación para representar dos
veces la misma pierna económica.

Se rechazan dos legs con el mismo:

- component identity;
- role;
- direction;
- magnitude kind/value/unit.

Por tanto, cambiar sólo `leg_id`, evidence u ordinal no evita el rechazo.

La misma component identity sí puede aparecer más de una vez cuando cambia material
semántico real, por ejemplo:

- rol distinto;
- dirección distinta;
- magnitud distinta.

Esto evita importar la regla más estrecha de UMI-05 que exige component identities
globalmente únicas.

## 9. Determinismo y Decimal

Los Decimals se serializan de forma determinista y compacta.

La decisión entre forma fija y científica se toma antes de materializar una cadena
fija potencialmente gigantesca. Valores como:

- `1E+100000000`;
- `1E-100000000`;

permanecen compactos.

`logical_values()` vuelve a ejecutar validación exacta/recursiva antes de emitir
material, de modo que corrupción post-construcción no se promueve a identidad lógica.

## 10. Casos adversariales obligatorios

La suite cubre al menos:

- clase y modo exactos;
- independencia clase ↔ modo;
- ordered caller-order reemplazado por ordinal;
- unordered caller-order canonizado determinísticamente;
- ordinal ausente en ordered;
- ordinal presente en unordered;
- ordinal duplicado/no contiguo;
- `bool` rechazado como ordinal;
- tuple exacto y mínimo de dos legs;
- root self-reference;
- leg IDs duplicados;
- duplicado semántico con IDs/evidence distintos;
- misma identidad permitida cuando rol/dirección cambia;
- RATIO/WEIGHT con unidad rechazado;
- QUANTITY adimensional y unitful;
- Decimal no positivo/no finito/primitive incorrecto;
- UUID/str subclass laundering;
- corrupción post-construcción de UUID, role, magnitude, enum, ordinal y unidad;
- exponentes Decimal extremos;
- ausencia de reloj, UUID implícito y autoridad operativa.

## 11. Límites explícitos

Esta entrega no:

- calcula precio;
- calcula payoff;
- calcula NAV;
- calcula spread actual;
- produce valoración;
- decide pesos dinámicos;
- rebalancea;
- crea señales;
- enruta legs;
- ejecuta órdenes;
- liquida;
- consulta proveedor;
- modifica Risk;
- modifica cuentas;
- habilita Production;
- usa capital real.

## 12. Criterio de cierre

UNR-024 puede cerrarse sólo cuando:

1. código, pruebas y este documento coinciden;
2. superficie permanece acotada;
3. PRUEBAS COMPLETAS están OK sobre el HASH exacto;
4. revisión serial independiente no deja hallazgo material;
5. integración usa el HASH esperado;
6. `main` y CI post-merge quedan verificados.

Después de UNR-024 corresponde la reconstrucción final UMI-14; no se infiere
automáticamente `PROGRAM-D FINAL PASS` por cerrar este issue.
