# VT31 MC-P2 — Dictamen ejecutado, adaptador de evidencia cognitiva M1 H1 NY AM (14 octubre 2026)

## Estado científico

**`M2_TTRADES_NATIVE_CONTEXT_SOURCE_WITNESS_PASS`**, **`M3_RETURN_INSIDE_SOURCE_OBSERVED_NOT_FULL_DISPLACEMENT_CERTIFIED`**, **`COG_EVIDENCE_V2_CONTRACT_INTEGRATION_PASS`**, **`METHOD_CERTIFICATION_PENDING`**, **`COGNITIVE_CERTIFICATION_PENDING`**, **`VT31_TRADER_NOT_CERTIFIED`**.

Prerregistro fuente fijo **antes de codificar**: `docs/research/VT31_MC_P2_TTRADES_NATIVE_H1_SOURCE_PREREG_2026-10-14.md` en commit **`910426029b4a3098327cbc8b7f334a307fed2bc1`**. Fuente primaria oficial [TTrades: AM Silver Bullet Strategy on NQ (19 junio 2025)](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/): H1 09–10 Nueva York, sesión 10–11, sweep high→SHORT hacia H1 low o low→LONG hacia H1 high, confirmación de displacement y familia de entrada. Esta exigencia de 09am **NO es regla universal** del ICT Silver Bullet original Londres/NY PM.

## Evidencia de CI reproducible

- **[GitHub Actions run #38607626630 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38607626630)**. Código exacto `d356e5fcd0d4fc364239ed4cfb1f4a71a0c94447`; **101/101 tests PASS** en 1.31 s, Ruff PASS y Python py_compile PASS. Se reejecutaron tests del comprobador nativo MC-P2, **COG_EVIDENCE_V2**, testigo #926, y regresiones cleanroom COG/OPS/M1/G3 con hashes G3 originales verificados.
- [Artefacto CI #11916311533](https://github.com/mezas3238-hue/qore-core/actions/runs/38607626630/artifacts/11916311533): ZIP SHA256 `b963b003f91a39ad017632408fba13cf8ca17ae28b1f55b409def031006cfd76` (metadato del GitHub artifact). Incluye JUnit, log de pytest, SHA256SUMS, commit probatorio y alcance. Expiración prevista 2027-01-12.
- Rama investigación separada `agent/vt31-mc-p2-ttrades-native-context-20261014`, hija de [PR #928](https://github.com/mezas3238-hue/qore-core/pull/928). Originales `cognition.py`, `operations.py`, y acta G3 permanecen con Git blob SHAs `d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9`, `0ce9707314aecb71155de8b57044b6ec028847b2`, `e99c70b4e018d626fb620d9a21b9314a51abc36d`.

## Qué quedó implementado

**Código `scripts/vt31_mc_p2_ttrades_native_h1_evidence_20261014.py`**:
1. `native_ttrades_am_context` recibe SOLO hechos observables: 60 M1 previos del H1 09 NY, prefijo cerrado M1 10 NY y `as_of` externo. Rechaza la sesión equivocada, vela futura y as-of desfasado; `UNKNOWN` para H1/prefijo incompleto. Usa `America/New_York` real verano e invierno.
2. Registra PRIMER barrido high/low y hora de la M1 de cierre que lo hizo observable. No permite elegir segundo lado por observar una futura oportunidad favorable. Si high y low se barren en misma vela, `UNKNOWN:BOTH_H1_SIDES_SWEPT_UNKNOWN_INTRABAR_ORDER`; si barrido contrario ocurre luego, `REJECTED:OPPOSITE_H1_RAID_AFTER_FIRST_SWEEP`.
3. Una M1 posterior debe CERRAR direccionalmente dentro del rango 09 para `RETURN_INSIDE_OBSERVED`; **NO permite certificar vuelta/displacement en la misma M1 del sweep** por falta de secuencia intrabar. No atribuye cuerpo 1,25× a TTrades (es proxy QORE ajeno al texto primario).
4. Deriva LONG+target H1 high tras LOW raid y SHORT+target H1 low tras HIGH raid. Emite `NativeAmContext` inmutable serializable; `method_certified=false`, `cognition_certified=false`, `execution_authorized=false`.
5. `compare_native_with_existing_cog` empareja este testigo con un **DTO de COG independiente preexistente** y `COG_EVIDENCE_V2`: reconstruye H1 y prefijo de la serie COG original, rechaza mutación de OHLC, side/target contrario y MSS anterior al barrido. Un contexto con COG/MSS concordante produce estado máximo **`CONTEXT_ATTESTED_NOT_CERTIFIED`**. Nunca fabrica un `CognitiveDecision`.
6. Los testigos CONFORMANTES de la integración son DTO **SINTÉTICOS** usados para probar el contrato, no órdenes de trading ni señales históricas del COG actual. La regresión real-producer anterior #927 y la adversarial de #928 permanecen vigentes: **el COG actual NO implementa nativamente el barrido/DOL TTrades**, por lo tanto esta integración no hace que pase TTrades automáticamente.

## Matriz de prueba efectivamente superada

- LONG y SHORT válidos con 09:00 H1 completo, verano **EDT UTC−4** e invierno **EST UTC−5**.
- Barrido aún ausente `AWAIT_SWEEP`, tras barrido sin M1 posterior de retorno `AWAIT_RETURN`.
- M1 con sweep simultáneo ambos extremos `UNKNOWN`, sweep contrario posterior `REJECTED`, repetición mismo lado mantiene primera marca.
- H1 con 59 M1, missing interval 09, gap 10, datos futuros, `as_of` retroactivo o stale, reloj horario no permitido y perfil Londres: no se aceptan falsos positivos.
- Dos DTO sintéticos (LONG/SHORT) satisfacen contexto y **COG_EVIDENCE_V2** sin adquirir trading authority; sin DTO `COG_NOT_PRESENT`; target/DOL adulterado `REJECTED`; side contradicho `REJECTED`; MSS anterior a sweep `REJECTED`; alteración de velas de origen `REJECTED`.
- 11:00 NY final se mantiene solo como cierre de evidencia de última M1; **no autoriza una orden posterior a ventana**.
- Regresiones originales COG/OPS/G3 y testigo V2 PASAN, código frozen conservado.

## Gates pendientes y siguiente trabajo

**M0 perfil** separado (`TTRADES_NY_AM_2025` vs `ICT_GENERAL_2023`) en módulos research, NO selector live. **M1 cronología** testada en fixtures; falta cronología extensa de mercados reales. **M2 source H1 raid/DOL** con atestador autónomo funcional, falta integrar en generador nuevo NY AM y evaluar cuántas veces el COG auténtico coincide sin retuning. **M3 MSS** comprobado por V2 independientemente; regreso direccional no equivale a demostrar todo displacement de fuente. **M4** FVG/OB/Breaker/displacement por fuente todavía no certificadas; **M5** stop swing TTrades vs stop C2 QORE, pendiente; **M6** doble revisión roles, issue #897 pendiente; **M7** economía independiente.

**Próxima prioridad técnica para VT31 principal (ICT general)**: construir el segundo atestador nativo **`ICT_DOL_SOURCE_V1`**, que reconstruya ex ante los niveles prior cash, Asia/London en los tres horarios y compruebe origen, tiempo de confirmación y consumo de liquidez a partir de M1 independiente. Esto elimina el `UNKNOWN:ICT_EXTERNAL_DOL_PROVENANCE_UNVERIFIED` del V2 cuando haya evidencia, pero **no transforma una regla QORE de escoger DOL cercano en doctrina ICT** ni prueba edge. Posteriormente debe auditarse MSS/FVG y causalidad por sesiones, nunca adoptar el H1 09 de TTrades como filtro universal.

**Par G3 intacto:** acta `a446afa17ed6e411b8f0b6fc182b103a78959a97`, código `78d4cdac0e09d1a6eef37b99c505ffc5098031fc`, todavía `G3_PENDING_DUAL_SIGNATURE`. Owner tiene una sola cuenta: autorización de investigar NO son firmas duales inventadas. No hay merge, main, VPS, órdenes, QDLE ni sizing propio, producción/LIVE, holdout, replay económico o certificación real.
