# VT31 TTrades AM — Auditoría de artefactos OB / Breaker: 3 controles ejecutados

**Corte 2026-10-13.** **No hay edge económico validado; NO GO a LIVE/OMS/G6/G7.** Investigación explicativa, no nuevo método operable. G3 antiguo sin firmar/no modificado.

## Protocolo y evidencia verificable

1. **Preregistro ex ante**: `docs/research/VT31_OB_BB_CONTROLS_PREREG_20261013.md`, commit **`2748d59daf1d32d42b6dd41d37c6def1ab314e41`**, en la rama de controles **antes del script de ejecución**; el CI verifica precedencia Git. Baseline fijo de cuatro familias en `9f85b83e1bfd23c02e5f642bd33defa65208f015`, PR #906. **Cero cambios** a detectores, datos, parámetros o rentabilidad previa.
2. **[CI #38412820476 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38412820476)**, SHA ejecutado `a2c32e833105ad42eee9aabd785348e9d275ea32`, **10/10** pruebas sintéticas adversariales; Ruff/py_compile, manifiesto de SHA256 y prueba de fuente M1 verificadas; artifact **`11821658524`** (JSON completo y resumen).
3. 775 jornadas NY, M1 desarrollo NAS100 CFD **1.059.784** velas 2023-10-01 a 2026-10-01, SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, artifact M1 `11459859004`. **No se abrió holdout**, ni tick BID/ASK, no broker ACK. Todos los retornos son movimiento direccional a +15 M1 desde apertura posterior a *cada marca de confirmación* (o desde desplazamiento para reloj común), **no PnL real**.

## 1. Solapamiento exacto: OB y Breaker no generan ninguna jornada autónoma

En 775 días de investigación: **563 sin candidato**, **212 con al menos una familia**. Diagonales: DIRECT 212, FVG 205, OB 116, BREAKER 84. Todas las fuentes OB y BB aparecen en días con DIRECT, por construcción de la metodología actual.

| Pares / diferenciales de día | Número |
|---|---:|
| OB y FVG | **111** |
| OB y DIRECT | **116 de 116** |
| BREAKER y FVG | **81** |
| BREAKER y DIRECT | **84 de 84** |
| OB y BREAKER | **66** |
| OB sin FVG ni DIRECT | **0** |
| BREAKER sin DIRECT, FVG ni OB | **0** |
| OB sin FVG (pero con DIRECT) | **5** |
| BREAKER sin FVG (pero con DIRECT) | **3** |
| Los cuatro detectores en una jornada | **64** |
| Ningún detector en una jornada | **563** |

Partición exacta de las **16** combinaciones, orden `DIRECT,FVG,OB,BREAKER` (no cifras de operaciones): `0000=563;1000=1;1001=1;1010=3;1011=2;1100=77;1101=17;1110=47;1111=64`; las otras siete combinaciones más `0001`, `0010`, `0011`, `0100`, `0101`, `0110`, `0111` valen cero. Estos 617 sumandos de familias no son 617 trades independientes. **No existe un conjunto OB exclusivo nuevo a nivel día; sí existen instantes de confirmación diferentes, cuya utilidad ejecutable no ha sido probada.**

## 2. Ancla común: la selección OB/Breaker se produce más tarde

La apertura M1 siguiente al cierre de la **primera confirmación de displacement** es el ancla idéntica por jornada. De esta forma, cualquier diferencia entre familias en la tabla proviene **exclusivamente del conjunto de días que desarrolló luego cada familia**, no del instante de su propia confirmación.

| Días que eventualmente tienen familia | N | Propio reloj +15m, pts | Reloj común displacement +15m, pts | IC95 semanal reloj común |
|---|---:|---:|---:|---|
| DIRECT | 212 | −1,464151 | **−1,464151** | [−7,976825; +5,431298] |
| FVG | 205 | −1,445951 | **−0,763805** | [−7,690032; +6,492402] |
| **OB** | **116** | **+1,865948** | **−25,301207** | **[−32,881468; −17,343887]** |
| **BREAKER** | **84** | **+1,661548** | **−22,692381** | **[−31,525416; −13,379280]** |

**Hallazgo crítico:** los días que más tarde activan un retesteo OB/Breaker son, en esta cohorte, días con enorme desplazamiento desfavorable en los 15 min tras el displacement inicial. Los números positivos a +15m desde sus confirmaciones propias son **posteriores** a la secuencia que llevó al retesteo. **Pertenecer a OB/BB en el reloj común es información futura**. No convertir los retornos del reloj común ni sus bandas en rendimiento tradable, causalidad o facultad de elegir previamente esos días. El ancla común NO reconcilia precios de entrada: solo sincroniza reloj.

## 3. Placebo de extremo genérico 3-M1, CAUSAL

Sobre el mismo universo con sweep/displacement, **primer mínimo estricto M1 de tres velas confirmado después de displacement para LONG**, análogo máximo para SHORT; el pivote solo existe **al cierre de la tercera vela**, no al extremo central. Máximo una muestra por día, sin condiciones OB/BB. En **201/212** días con displacement se encontró pivote con historia 15m completa; **11** no. Resultado placebo general: **−2,685522 puntos** medios (CI bootstrap semanal 95% **[−9,680726; +3,987190]**, 116 semanas). **Esto contradice la afirmación no demostrada de que todo extremo local debe tener retorno positivo**. La conclusión NO es que OB/Breaker sean superiores por ello: el placebo puede ocurrir a otra hora, con distinta selección de retest y distinta posición en el recorrido.

Controles por **mismo día y dirección**, cuando las dos series tienen 15m completos:

| Emparejamiento | N | Media familia | Media pivote genérico | Diferencia pareada familia − pivote | IC95 de diferencia por semanas |
|---|---:|---:|---:|---:|---|
| OB frente a primer pivote 3-M1 | **115/116** | +2,209391 | **−14,728783** | **+16,938174** | **[+9,882762; +24,500782]** |
| BREAKER frente a primer pivote 3-M1 | **83/84** | +1,211687 | **−15,254699** | **+16,466386** | **[+8,447143; +24,994751]** |

**Advertencia obligatoria:** **0 de 115** OB y **0 de 83** BREAKER coinciden exactamente en el minuto de confirmación con su pivote placebo. Desfase familia menos pivote, media OB **+3,4696 min**, mediana **−1 min**, rango **−8 a +44 min**; media BREAKER **+0,9036 min**, mediana **−2 min**, rango **−11 a +42 min**. Las diferencias pareadas grandes **NO identifican una ventaja causal** de OB/BB: un pivote causal anterior al retesteo puede sufrir primero una excursión de pérdida mientras el retesteo ocurre tras la reversión; la selección OB/BB tiene información posterior y el benchmark usa reloj diferente. Bootstrap que excluye cero para una métrica NO comparable en tiempos tampoco certifica la estrategia.

**Resultado metodológico:** el argumento «los retornos positivos de OB/BB son trivialmente idénticos a todos los extremos locales» **no quedó respaldado por este placebo**. **Sí quedó plenamente visible un artefacto potencial de reloj y selección posterior**, suficiente para no afirmar ventaja sin un control exactamente sincronizado y política de ejecución.

## 4. Dictamen / siguiente revisión obligatoria

- **Solapamiento:** 100% de OB y BB incrustado en DIRECT a nivel jornada. No hay nuevos días de operación por añadir estas etiquetas.
- **Tiempo:** el supuesto liderazgo de medias +1,87/+1,66 desaparece en comparación con el mismo reloj previo; es distinto tipo de pregunta, y las cohortes son post hoc. La diferencia pareada con placebo **no es identificable como edge** por la asimetría de confirmación.
- **Extremo genérico:** negativo en general; **no cumple** la hipótesis simplista de pivote genérico +1,5 a +2. No seleccionar OB/BB por el placebo negativo, porque su positivo puede seguir siendo efecto de filtrado de contexto/retest.
- **Veredicto económico:** `VT31_OB_BREAKER_NET_EDGE_NOT_IDENTIFIED`; **NO financiar OMS/G6/G7 ni producir órdenes** a partir de estos resultados. Hace falta un contraste de señales con **mismo as-of, hora, condiciones, riesgo y precio ejecutable**, preregistrado en datos nuevos (no después de ganar en desarrollo), con NQ/NAS100 equivalente, BID/ASK/ACK y holdout independiente. Si faltan, cerrar como insuficiencia de evidencia, no como falsación total de ICT/TTrades.
- **Gobernanza intacta:** acta G3 `a446afa17ed6e411b8f0b6fc182b103a78959a97`, código `78d4cdac0e09d1a6eef37b99c505ffc5098031fc`, PR #896 DRAFT sin firmas. Este análisis no altera contratos ni ejemplos fuente, precios reales, holdout, producción ni VPS.

**Fuente de números completa**: [CI #38412820476](https://github.com/mezas3238-hue/qore-core/actions/runs/38412820476), artifact `11821658524`, con `ob-breaker-three-controls.json`, `three-controls-summary.json`, commit de software y manifiesto SHA256.
