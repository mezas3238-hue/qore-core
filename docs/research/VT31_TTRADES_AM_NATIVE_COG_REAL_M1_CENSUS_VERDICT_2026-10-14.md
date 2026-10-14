# QORE CORE — VT31 TTrades NY AM · CENSO REAL M1 DE COGNITIVA (14-OCT-2026)

## Estado / trazabilidad
- **PR [#934](https://github.com/mezas3238-hue/qore-core/pull/934) (DRAFT)**, stacked sobre productor per-profile PR #933, encima de M2 #932 y testigo #929. PR #930 (ICT GENERAL) continúa **rama hermana**, no fusionado.
- **Pre-reg antes de código/datos de esta ronda**: commit `41b97b356de031bd19b7fa0ef9144841d7683254`; contrato del emisor congelado sobre PR #933 commit `1556766c1831190b5459bf93404081412200ba7d`.
- **Fuente NAS100 CFD original de GitHub Actions**: artifact `11459859004`, 1.059.784 M1 (2023-10-01→2026-10-01); hash SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa` verificado antes de uso. Fuente **DESARROLLO YA OBSERVADO**, no Fresh Holdout/OOS. No otro dataset, ninguna compra.
- **EJECUCIÓN VERIFICADA**: [GitHub Actions #38622553350](https://github.com/mezas3238-hue/qore-core/actions/runs/38622553350), código `8992224ea8bdb34984a55be8476af0fcf994df2e`. **159/159 pytest PASS**, Ruff y compile PASS, 3 blobs G3 congelados coinciden, lectura data SHA PASS y QA de cierre/hash PASS.
- [Artifact auditado #11921659492](https://github.com/mezas3238-hue/qore-core/actions/runs/38622553350/artifacts/11921659492), ZIP digest SHA256 `968b2a2db4b67cce8e0505928a73d4e07c1b662167a2cdd34aca2e8d3f3e6adf`. Archivos `VT31_TTRADES_AM_M1_METHOD_CENSUS.json`, resumen JSON, JUnit, hashes, SHA y scope.

## Resultado exacto: censo de 775 días NY de las 09h/10h
| Resultado mutuamente excluyente | Días |
|---|---:|
| `MSS_ATTESTED_CONTEXT_ONLY` (primer retorno con MSS QORE, DOL TTrades y V2 corroborados) | **128** |
| `FIRST_RETURN_NO_QORE_MSS` | **483** |
| `SWEEP_NO_RETURN` | **92** |
| `NO_SWEEP` | **65** |
| `REJECTED_SOURCE` | **1** |
| `INCOMPLETE_M1_HOURS` | **6** |
| **TOTAL** | **775** |

**Horas completas**: 769 días. **128/769 = 16,64%** de días completos con un único contexto metodológico M2–M3 atestiguado. **483/769 = 62,81%** detectaron primer regreso direccional, pero no MSS proxy en ESA misma vela; estos NO son 483 trades perdidos, ni prueba de que el criterio sea autoral ICT/TTrades. **NO ajustar umbral luego de ver este resultado.**

Los 128 son **DTO cognitivos de prueba**, NO órdenes, NO CE limit ACK, NO fills, NO TP/SL, NO resultados netos, NO rentabilidad. Para TTrades 2025 sigue sin verificarse autoralmente el requisito exacto del desplazamiento y OB/Breaker M4. El módulo puede cumplir su proxy QORE sin ser la estrategia entera del autor.

## Por qué este resultado importa
- El error doctrinal del COG G3 genérico descrito en #927/#928 (elegir high prior cash 150 vs opuesto H1 high 110) se aborda mediante un nuevo **productor específico de perfil** en #933 sin tocar G3 original. El censo #934 efectivamente lo ejercitó en históricos reales 3Y, aunque el COG fuente general sigue sin corregirse / reemplazarse.
- En 775 días, el principal punto de pérdida de oportunidad **bajo esta especificación conservadora** es el requisito QORE MSS en el **primer regreso** (483 clasificados). No significa que la metodología autoral imponga el requisito o que al retirarlo se gane dinero.
- La data original fue verificada por SHA antes del censo. Se evitó el sesgo de esperar un segundo regreso "mejor" en días fallidos, se preservó el primer sweep, y sólo se usaron prefijos M1 cerrados al as_of.
- La categoría `REJECTED_SOURCE` contiene un solo día, disponible para inspección individual en el JSON de artifact; investigar su reason code antes de atribuirlo a un patrón real específico. No inventar cuál fue.

## Matriz M0–M7 después del censo
| Gate | Estado |
|---|---|
| M0 | Identidad de perfiles separada en investigación; G3 original intacto |
| M1 | Datos M1 originales SHA PASS; causalidad de prefijo por día |
| M2 | Testigos H1 TTrades #929 y DOL ICT #932/#930; fuente context corroborada parcial |
| M3 | 128 contextos con pivote3/cruce/desplazamiento QORE proxy corroborados; fidelidad autoral **PENDIENTE** |
| M4 | displacement directo/FVG/OB/Breaker no implementados bajo contrato autoral completo |
| M5 | swing stop vs C2 QORE, expiración y rutas de salida sin certificar |
| M6 | `G3_PENDING_DUAL_SIGNATURE` — issue #897 |
| M7 | `EDGE_NOT_DEMONSTRATED` — broker BID/ASK NAS100 exacto/fills/órdenes #900, OOS independiente pendiente |

## Próxima acción concreta
1. Auditar el único REJECTED_SOURCE y la distribución de motivos de 483 primeros regresos sin MSS, **sin elegir parámetros por retornos ni tocar Fresh Holdout**.
2. Mapear casos de la fuente TTrades de displacement, FVG, OB y Breaker con definiciones versionadas. Lo no demostrado por texto autoral continúa marcado `QORE_PROXY`.
3. Formalizar M5 swing que causa desplazamiento / invalidación / DOL / vencimiento y pruebas intrabar UNKNOWN sin estimar fills.
4. Confrontar PR #930 y #932: ambos source witnesses para ICT general, semántica distinta para huecos. Decidir contrato único mediante revisión sin merge automático.
5. M6 firmas verdaderas y M7 economía/broker por separado; no confundir 128 eventos con ~150 fills anuales.

**PROHIBIDO:** MERGE a main sin Owner, LIVE, VPS, FundedNext real, OMS/order API, sizing trader, datos comprados, Fresh Holdout para calibración, extrapolación de PF/DD inexistentes.
