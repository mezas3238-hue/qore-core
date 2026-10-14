# VT31 — Dictamen L3 preparatorio: paridad temporal 1× frente a 32× sobre 3Y M1 · 2026-10-14

**Estado fuente-only**: `SOURCE_PARITY_PASS / OFFICIAL_TRADER_LAB_L3_NOT_QUALIFIED` · PR [#937 DRAFT](https://github.com/mezas3238-hue/qore-core/pull/937).

## Hechos comprobados
- **Prereg antes de código**: SHA `51eb61d6982c67026bdca39dd301b380347d54bd`, archivo `docs/research/VT31_L3_M1_SOURCE_PARITY_PREREG_2026-10-14.md`.
- **CI ejecutada en código exacto** `dff44a0ab18b1aa6ef5ecc653d8330e4f771435e`: [run #38637604042 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38637604042), **186/186 pytest PASS**, Ruff PASS y compilación PASS, fuente y 3 blobs G3 COG/OPS/acta SHA PASS.
- **Artifact**: [#11928263151](https://github.com/mezas3238-hue/qore-core/actions/runs/38637604042/artifacts/11928263151), ZIP SHA256 `484f3d6b94ae65a743813d0a459b7a5076ef638fbc6bfadb20e132c03ba39a52`; contiene reporte de parity, JUnit, logs, commit SHA y checksums.
- **Dataset original y NO Fresh Holdout**: artifact fuente #11459859004 en [run #38018856150](https://github.com/mezas3238-hue/qore-core/actions/runs/38018856150), NAS100 CFD 3Y, 1.059.784 M1, SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`. El workflow comprobó SHA bytes antes del análisis.
- **Población idéntica**: 775 días NY con fuentes 9h/10h, 769 días con 120 velas cerradas completas, **92.280 eventos M1 por trayectoria**, 128 contextos COG #933, 119 primeras FVG investigables #935, 8 sin FVG y 1 cierre fuera de la hora. M5 **61 touch sin fill, 31 misma M1 ambiguos, 27 expiraciones sin órdenes**.
- **Tres trayectorias concordantes**: censo batch original PR #935, streaming M1 x1, streaming M1 con reloj virtual x32, igualdad exacta por día/case (SHA256 del ledger), cronología de cierres M1 idéntica y cuenta de instantes idéntica. El avance explícito de reloj manual fue 60 s/evento frente a 1,875 s/evento; **es cronómetro VIRTUAL, NO 32× rendimiento medido real del motor**.
- **Tests adversariales añadidos**: dos climas DST EST/EDT, duplicados y huecos fail-closed, tentativas futuras interceptadas vía spy en cada llamada COG, hashing/detección de precios alterados, factor no preregistrado 16× rechazado.

## Tabla de estatus de Gates tras el ensayo

| Gate oficial | Hecho de la ronda | Estatus de certificación |
|---|---|---|
| L1 `METHODOLOGY FREEZE` | Source-proxy congelada sólo para experimento, NO candidato íntegro certificado ni doble firma G3, falta TTrades OB/Breaker | **PENDIENTE** |
| L2 `REPLAY` | 3Y fuente reproducida en decisiones, sin limit OMS, fill ACK, SL/TP, costes y saldo | **PENDIENTE** |
| L3 `FAST_FORWARD` | Paridad 1×/32× de **M2–M5 SOURCE-ONLY**, no función canónica `qualify_trader_lab_fast_forward` ni `TraderLabCandidateBinding` | **PENDIENTE; ensayo preparatorio PASS** |
| L4 `OOS` | toda data 3Y ya vista, sin muestra fresca | **BLOQUEADO** |
| L5 `STRESS` | 186 tests de estructura/fuentes, falta estrés económico completo | **PARCIAL** |
| L6 `MONTE_CARLO` | sin trades cerrados netos | **BLOQUEADO** |
| L7 `ECONOMIC` | 0 órdenes / 0 fills, PF/Sharpe/Sortino/DD no medibles, NAS100↔USTEC aún no homologado | **BLOQUEADO** |
| L8 `RISK` / L9 `CIBO` / L10 `INDEPENDENT` | sin atestaciones externas del candidato exacto | **BLOQUEADO** |

Esta separación refleja [`QORE-TRADER-LAB-001.md`](https://github.com/mezas3238-hue/qore-core/blob/main/docs/architecture/QORE-TRADER-LAB-001.md), [Issue #473](https://github.com/mezas3238-hue/qore-core/issues/473), y el verdadero [`trader_lab/fast_forward.py`](https://github.com/mezas3238-hue/qore-core/blob/main/src/qore/infrastructure/trader_lab/fast_forward.py). `TraderLabFastForwardQualification` exige un `TraderLabCandidateBinding` con estrategia congelada y eventos del replay original, que este ensayo NO fabrica.

## Próximo trabajo concreto, sin bucles de tuning
1. **L1**: resolver ambigüedad ICT_GENERAL vs TTrades NY AM y documentación primaria de FVG/OB/Breaker/MSS, stop/exit y configuración exacta. Preregistrar versión íntegra, obtener independencia metodológica G3 Issue #897; no reescribir #935 según los 119 casos.
2. **L2/L3 real**: ligar Trader Lab candidato/estrategia/input exactos y construir replay integral con visibilidad `available_at`, cancel/ACK del broker y salida no inventada; entonces usar `qualify_trader_lab_fast_forward` con la evidencia auténtica y prueba de paridad, no reusar esta paridad como certificado.
3. **Fuente M7/L7**: validar contrato NAS100↔USTEC Issue #857, fuente real BID/ASK #901 solo 30h incompletas, datos hasta 15:55 NY, verdaderos stops/tick/fees, invalidaciones M1 en orden broker y OOS realmente intocado.
4. **L4–L10**: nuevo holdout después de freeze real, stress/MC predefinidos, evidencia de edge NET, aprobaciones auténticas Risk/CIBO/independiente. La normativa **no permite saltar estos Gates** aunque haya 186 tests verdes.

No se ha realizado: LIVE, producción, VPS, FundedNext LIVE, push a main, merge, lotaje de trader, ejecución de órdenes, OOS, PnL ni entrega de falsas firmas. Estado `VT31_NOT_CERTIFIED`.

**Nota SHA**: este informe documental se publicó DESPUÉS del CI exitoso; la afirmación CI PASS se refiere al commit de código `dff44a0a...` y sus fuentes exactas, NO a una nueva ejecución del HEAD que contiene este texto.
