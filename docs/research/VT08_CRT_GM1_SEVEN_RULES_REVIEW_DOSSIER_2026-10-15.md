# VT08 CRT — G-M1: dossier operativo de siete reglas para revisión independiente
**Fecha:** 2026-10-15. **Estado:** DRAFT / no adjudicado / no G-M1 PASS. Este es un contrato *propuesto*, no un backtest ni un certificado.

## Autoridad y muestra
El Owner permite tres fuentes: RomeoTPT, SpeculatorFL y TraderFlameseN; NO exige fidelidad exclusiva a Romeo. Sus conceptos inspiran CRT pero las definiciones exactas siguientes son **QORE ENGINEERING PROPUESTA**; ni los autores ni el Owner han aprobado los siete umbrales por separado. Fuentes primarias/de corroboración: [Romeo Model 1](https://www.youtube.com/watch?v=UUq_wKQ61Wo), [SpeculatorFL CRT](https://threadreaderapp.com/thread/1784493604473618604.html), [SpeculatorFL conformational](https://threadreaderapp.com/scrolly/1794311615535518154), [TraderFlameseN](https://threadreaderapp.com/thread/1790141530461622525.html); semejanza entre las últimas dos impide tratarlas como pruebas independientes de edge.

**Datos de desarrollo ya vistos:** 2024–2026 Atlas M5 AUDUSD/USDJPY; V1 54 candidatos, V2 745 (115 DOL primero, 538 invalidación primero), V3 139 (23 DOL primero, 69 invalidación primero, 42 expiración, 5 UNKNOWN). V3 tiene evidencia de trayectoria adversa. *Ninguno equivale a fills, PF neto ni OOS virgen*. Este dossier sirve para auditar semántica y no rescata económicamente V3 ni pre-registra V4.

## Siete artículos revisables

| Contrato | Regla causal QORE propuesta | Prueba negativa obligatoria |
|---|---|---|
| **G1 reference_eligibility** | H4 C1 y C2 completas, contiguas y cerradas; C2 cruza estrictamente un solo extremo de C1 y vuelve a cerrar dentro. Identidad con sello de reloj y hash. | Barrido doble, cierre fuera, M5 ausente -> ABSTAIN/UNKNOWN, nunca referencia válida. |
| **G2 multiple_reference_priority** | No seleccionar retrospectivamente el extremo antiguo que mejor habría funcionado; en el comparador V3 la referencia candidata es C1 adyacente a C2. Si múltiples referencias contemporáneas tienen conflicto sin prioridad causal homologada: ABSTAIN. | Dos niveles old-CRTH contradictorios: no elegir el más rentable. |
| **G3 parent_child_timeframe** | H4 padre cerrado establece dirección; sólo M15 derivadas de M5 completos, con cierre real y prefijo causal dentro de C3; hijo opuesto no autoriza reversal ni fallback. | Cambiar vela M15 futura jamás altera la tesis emitida previamente. |
| **G4 entry_confirmation** | **Solo comparador V3:** primera triple cronológica M15_REF / M15_SOURCE / M15_CONFIRM con sweep unilateral y reclaim en SOURCE, cuerpo SOURCE opuesto, y cierre de CONFIRM cruzando SOURCE.open en dirección H4. Es proxy QORE, no CSD universal de autores. | Un wick sin cierre cruzando SOURCE.open o confirmación aún abierta no confirma. |
| **G5 invalidation_expiry** | Extremo wick M15_SOURCE congelado como invalidación estructural; si invalidado antes de decisión, ABSTAIN; después, KILLED. Confirmación en cierre final de C3 = EXPIRED. Missing/ambigüedad = UNKNOWN. | Toque de ambas barreras en misma M5 no se convierte automáticamente en ganador. |
| **G6 destination_lifecycle** | Midpoint H4 C1, congelado antes de observación futura, debe quedar al frente y sin wick-touch previo durante el prefijo C3. Primer toque consume destino conceptual, NO equivale a fill. | Midpoint ya tocado no se recicla como nuevo destino. |
| **G7 conflict_and_rearm** | Una primera hipótesis por padre H4; contradicción suspende/veta. Rearm exige nueva identidad de evento, generación posterior y autorización causal por contrato propio, nunca rearm del mismo padre por resultado adverso. | Segunda triple posterior no reemplaza una primera fallida. |

### Discrepancias técnicas que no deben ocultarse
- G2 introduce conflicto de referencias **no plenamente detectado por el generador V3**; requiere una política observable PIT y revisión real antes de usarlo como selector.
- G7 requiere formalizar generación de eventos y memoria; "primera triple" por sí solo no certifica rearm cognitivo.
- H4 anclada UTC 00/04/08/12/16/20 es ingeniería de investigación, no horario universal de Romeo; calendarios, NY-DST, BTCUSD y fuente ejecutable requieren adjudicación propia.
- **No se debe buscar un nuevo parámetro ganador en Atlas ya consumido**. Una futura familia/identidad económica requiere preregistro antes de un conjunto OOS genuinamente no consultado.

## Condiciones de aceptación para G-M1 y G-M5

1. Cada regla debe recibir semántica exacta, versión/hash, prueba positiva, negativa, caso de conflicto y decisión individual (aceptar, modificar o rechazar).
2. Source-supported requiere fuente y localizador exacto respaldados en registry; lo no respaldado se etiqueta ingeniería QORE, no cita atribuida.
3. Dos identidades realmente independientes (Owner y auditor metodológico) deben autorizar la versión exacta. **Verificación externa de identidad en GitHub**, estado de review, SHA/digest, independencia del implementador y protección anti-replay. Un texto, una URL, un booleano o un CI verde no son aprobación.
4. La revisión G-M2 sobre 48 FIRST-LOOK y controles adicionales ocurre **antes** de abrir el futuro; documentar custodia de imágenes y sellado real. G-M3 exige discrepancias y contratesis, no 139/139 reconocimientos autorreferenciales. G-M4 requiere resolución formal de 5 UNKNOWN sin inventar terminal.
5. Hasta que exista un verificador confiable, el evaluador separa `proposal_complete` de `methodology_closed` y bloquea todo PASS autodeclarado mediante `METHODOLOGY_INDEPENDENT_APPROVAL_UNVERIFIED` y `G-Mx_PASS_ATTESTATION_UNVERIFIED`.
6. DD patrimonial, lotes y capital son **exclusividad de CIBO/QORE Risk**. En VT08 está prohibido sizing (incluyendo 1 lote o 1R fingidos). No merge, no demo/live/VPS/órdenes.

## Prioridad siguiente
Implementar autenticación verificable del reviewer y Owner sin flags inyectables; formalizar G2/G7 y el resto de las siete reglas con test adversarial; obtener revisión ciega de casos; después G-M3/G-M4 y G-M5. En paralelo custodiar datos Atlas12 antes de expiración real y definir fuente BID/ASK PIT, nueva OOS y Gates económicos externos. Estado exacto: **G-M1..G-M4 PARTIAL; G-M5 NOT ISSUED; GLOBAL NOT CERTIFIED**.
