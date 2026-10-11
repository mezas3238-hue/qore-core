# QORE Native RESET G2 — cTrader DEMO EURUSD M1 ejecutado / DEV_M1_GROSS_NO_SUPPORT

**Fecha 2026-10-11. Estado final: STOP para el diseño específico de RESET presión-alta + reversión corta.** Esta es una sensibilidad **exploratoria POST G1**, no una confirmación independiente ni la refutación del mecanismo universal del benchmark WMR. No se testean variantes adicionales de horario/umbral/mercado.

## Cadena de causalidad de investigación

1. G1 negativo preservado en [PR #802](https://github.com/mezas3238-hue/qore-core/pull/802), cTrader DEMO EURUSD M5, `DEV_GROSS_NO_SUPPORT`, D `−0.691910 bps`; no modificado.
2. **G2 único preregistrado ANTES de observar resultados M1**: `docs/research/QORE_NATIVE_RESET_FIX_G2_M1_SINGLE_EXPLORATORY_PREREG_2026-10-11.md`, commit **`3d96c55b06d376b26fc9e501be9fe9d2539f59b4`**. Como G1 ya era conocido, etiquetado `EXPLORATORY_POST_G1`.
3. Implementación y test en [PR #804](https://github.com/mezas3238-hue/qore-core/pull/804), `src/qore/infrastructure/trader_lab/qore_native_reset_fix_g2_m1_exploratory_v1.py` y `tests/infrastructure/trader_lab/test_qore_native_reset_fix_g2_m1_exploratory_v1.py`.
4. Ejecución [GitHub Actions #38184186416](https://github.com/mezas3238-hue/qore-core/actions/runs/38184186416), **2/2 SUCCESS**, commit **`82eb33eedf23baef0cb37a112439be76b9bce416`**, 8 pruebas causales G2 y pruebas heredadas G1 PASS; Ruff PASS. Evidencia exacta [artifact #11719355680](https://github.com/mezas3238-hue/qore-core/actions/runs/38184186416/artifacts/11719355680). Reporte `g2-m1-results/g2-m1-report.json`, testigo de días `g2-m1-results/g2-m1-joint-days.jsonl`, checksums y código SHA.
5. Validación independiente del ZIP descargado: **report SHA256 `27ec96c2b8361d1bc1fbcc3e449db1dd3f6d03840a90e34d483914fe48d40dbe` = PASS; 2446 observaciones, JSONL SHA256 `405e95248b2d1c461980886d3fac7eeb40d1582034682d83ba0f53bd22feed7c` = PASS**. Las medias de las cuatro celdas y D se reconstruyeron de forma independiente desde JSONL exactamente (`D=-0.5205344107663744` vs report `-0.5205344107663743`; redondeo numérico <1e-12).

## Procedencia exacta (solo cTrader, ningún token requerido)

| Uso | Fuente existente GitHub Actions | Resolución |
|---|---|---|
| Reutilizar categorías de presión/p75 de G1 | [CIBO Atlas run #35166210458, artifact EURUSD #10475354631](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458) | M5 nativo, 745.458 velas |
| Aperturas M1 para G2 | [Capitalizer run #35548099334, artifact EURUSD **#10618547852**](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334) | **3.693.521** M1 nativas |
| Fuente sellada 2014-2016 (NO ABIERTA) | [CIBO pre-2016 run #36367221571, EURUSD artifact #10948342218](https://github.com/mezas3238-hue/qore-core/actions/runs/36367221571) | reservado; solo se conocen metadatos |

M1 original `QORE_CAPITALIZER_CIBO_10Y_NATIVE_M1_CLONE_V1`, commit productor `18c338aedd5013ce65a6cb6408ffbc2e904a6217`, manifest SHA256 **`ca8b27db9a7c0454ad6094f54a18b522e31992ec52aa0d2d2f58c8803cffcca6`**. Se verificó el **SHA256 de 11 `RAW_M1_LEDGER` anuales**, pertenencia al símbolo, OHLC y monotonicidad UTC, cuenta total y ventanas de fuente **2016-09-17..2026-09-17 UTC excl.**. Sin cTrader OAuth, sin descarga nueva, sin reconstruir M1 desde M5, sin Dukascopy, sin leer contenido sellado, sin VPS/MT5/LIVE.

## Identidad G2 única, frozen

- Presión FIX 15:30–15:55 Europe/London, PLACEBO 13:30–13:55; **idéntica fórmula y estratificación high/low G1**, percentil 75 de 120 formaciones válidas previas.
- Resultado **FIX `open M1 16:03 → open M1 16:15`**, placebo equivalente **`14:03→14:15`**, **12 minutos brutos** y `-sign(pressure) * 10000 * ln(exit/entry)`. Esta ventana **fue fijada después de G1, pero antes de outcomes M1**. No confundir con precio de ejecución broker ni con WMR print.
- El G1 aportó **2.450 días completos**, G2 exige las cuatro aperturas M1 reales, cohorte común **2.446 días**; cuatro excluidos por M1 incompleto, sin imputación. **498 bloques semanales ISO** y bootstrap conjunto 2.000 réplicas, seed **941102**.
- Gate predefinido: 300 días comunes y n>=50 para cada una de las cuatro celdas, `D>0`, límite inferior IC95 D>0 y reversión FIX-high>0. **Gate de muestra PASS**; **gate bruto exploratorio FAIL**.

## Evidencia económica descriptiva (retornos brutos, bps; no rentabilidad ejecutable)

| Grupo | Días | Reversión media bruta bps |
|---|---:|---:|
| FIX_HIGH | 596 | **+0.2582040350** |
| FIX_LOW | 1.850 | **+0.1643219012** |
| PLACEBO_HIGH | 624 | **+0.7110347199** |
| PLACEBO_LOW | 1.822 | **+0.0966181753** |

- FIX (high-low) **+0.0938821338 bps**, PLACEBO (high-low) **+0.6144165445 bps**; efecto diferencial **D = −0.5205344108 bps**.
- Bootstrap 2.000/2.000 réplicas válidas, **IC95 D = [−1.3823682665, +0.3759440977] bps**. Incluye cero. Ni amplitud ni dirección satisfacen la hipótesis prereg.
- Patrón relativo: G1 FIX high-low era negativo, aquí ligeramente positivo, pero **la reversión condicional sigue siendo mucho más intensa fuera de la ventana del fixing**. Esta observación es descriptiva, no evidencia de que el fixing cause inversión de un efecto; CI de la interacción incluye cero.
- M1 volumen de velas original por año verificado: 2016 105654, 2017 368133, 2018 368682, 2019 366324, 2020 370426, 2021 369088, 2022 370815, 2023 368838, 2024 372060, 2025 370481, 2026 263020.

## Dictamen y trabajo restante

1. **No son necesarios ticks ni BID/ASK para falsificar la existencia de una señal bruta condicional** en esta operacionalización. Después de G1 M5 negativo, **un G2 M1 predefinido también es negativo**, sin replantear el umbral para rescatarlo.
2. La prueba de M1 **no establece que el mecanismo de flujos de fixing WMR no exista**. No midió su print, las órdenes institucionales ni el verdadero coste de broker. No afirmar que cualquier sistema RESET imaginable sea imposible. Esta familia concreta queda `STOP/NO_PROMOTION`.
3. **No PF, Sharpe, Sortino, PnL, max drawdown de trader o beneficios capturables**: no hubo fills, stop, sizing, BID/ASK, comisiones ni control de latencia. Para una propuesta nueva con señal positiva bruta, esos costes sí serían indispensables antes de autorización transaccional, pero no tienen razón para bloquear el descarte bruto actual.
4. **NO** reabrir ventanas alternativas, mercados adicionales ni cambiar percentiles por este outcome; G2 post-G1 no da control del sesgo de exploración secuencial. Cualquier hipótesis distinta necesita mecanismo económico realmente independiente, evidencia causal y reservar OOS auténtico.
5. Investigación en GitHub solamente. No cambiar CIBO, Shared, traders existentes, VPS ni producción. **Cero traders promovidos**.

**Cierre: `G2_COMPLETED_EXPLORATORY_NEGATIVE`, `SOURCE_G0_NATIVE_M1_VERIFIED`, `TRADE_COST_UNMEASURED`, `NO_TRADER_CERTIFICATION`.**
