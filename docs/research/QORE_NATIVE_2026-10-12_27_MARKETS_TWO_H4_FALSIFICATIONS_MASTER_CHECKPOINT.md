# QORE Native — CHECKPOINT MAESTRO de investigación ejecutada, 2026-10-12

**Resumen científico con fuentes**. La visión sigue siendo hasta tres traders nativos diferenciados, únicamente con edge económico causal, robusto y descontando fricciones reales antes de certificación. Hasta hoy **0/3 traders certificados**. No abrir posiciones, ni VPS/MT5/Shared/CIBO/QDLE/LIVE; workstreams en ramas DRAFT sin fusionar producción.

## I. Históricos M5 — de 12 a 27 sin sustituir fuentes

| Corte cronológico | GitHub | Activos G0 SHA | M5 originales |
|---|---|---:|---:|
| Primera cohorte | [PR #816](https://github.com/mezas3238-hue/qore-core/pull/816), [run #38196127168](https://github.com/mezas3238-hue/qore-core/actions/runs/38196127168) | 12 | 8,726,985 |
| Unión primeros 11 nuevos | [PR #821](https://github.com/mezas3238-hue/qore-core/pull/821), [run #38202227551](https://github.com/mezas3238-hue/qore-core/actions/runs/38202227551) | 23 | 16,924,567 |
| +GBPNZD/AUDCAD/AUDCHF | [PR #823](https://github.com/mezas3238-hue/qore-core/pull/823), [run #38203866777](https://github.com/mezas3238-hue/qore-core/actions/runs/38203866777) | 26 | 19,160,586 |
| +AUDNZD | [PR #824](https://github.com/mezas3238-hue/qore-core/pull/824), [run #38204152494](https://github.com/mezas3238-hue/qore-core/actions/runs/38204152494) | **27** | **19,905,871** |

**Manifiesto final del último corte:** [artifact 27 #11726921285](https://github.com/mezas3238-hue/qore-core/actions/runs/38204152494/artifacts/11726921285), SHA256 `499219430212dd50ffcefe681e6372ac3d66a54c420d03c3924d1ec2dc9680d0`.

**Separar orígenes**: 12 originales cTrader DEMO CIBO sin prueba que sean misma cuenta bróker que 15 nuevos IC Markets DEMO. La unión es un índice lógico con RAW SHA por símbolo, no 27 precios pegados, no BID/ASK broker homologados, H4/D1 nativos no certificados. G0 = integridad, NO edge ni certificación net.

**Descarga restante #38193802541:** hubo 16/21 artifacts publicados (CADJPY ya descargado pero NO G0, CADCHF en progreso; CHFJPY, NZDJPY, NZDCHF, NZDCAD en cola en último chequeo). Los seis pendientes de G0 fijo son CADJPY, CADCHF, CHFJPY, NZDJPY, NZDCAD, NZDCHF. Reconfirmar estado real y fuente HASH **antes** de declarar 33. No reiniciar capturas paralelas ni reemplazar archivos de los 27.

## II. Dos intentos científicos económicos genuinos, ambos negativos

| Hipótesis congelada antes OHLC | Ronda exacta | Días dev / temporal | Delta bps vs control (dev / temporal) | Dictamen |
|---|---|---:|---:|---|
| H4-GROSS-01 EURUSD persistencia 12h vs momentum 4h | [PR #822](https://github.com/mezas3238-hue/qore-core/pull/822), [run #38203530559](https://github.com/mezas3238-hue/qore-core/actions/runs/38203530559) | 1,526 / 510 | +0.7434 / −0.2579, IC95 ambos incluyen 0 | NO_SUPPORT |
| H4-GROSS-02 XAUUSD reversión 12h vs reversión 4h | [PR #825](https://github.com/mezas3238-hue/qore-core/pull/825), [run #38204480486](https://github.com/mezas3238-hue/qore-core/actions/runs/38204480486) | 1,480 / 495 | −0.4361 / −0.1122, IC97.5 ambos incluyen 0 | NO_SUPPORT |

**Prereg fehaciente**: EURUSD `a4424ba3027018bab54f03aff668894f63f47da9`; XAUUSD `94bc58e89b5b2112e1c65df77a077bff2758b63c`; ambos anteriores al primer GitHub Actions que leyó outcomes. XAUUSD usó alfa .025 conservador por multiplicidad pero no corrige retroactivamente toda la investigación Core. Ambos períodos diagnostics NO OOS global virgen. **OHLC desde 2024-09-17 hasta 2026-09-17 no se leyó** en los motores de dichos experimentos. Resultados JSON firmados en artifact #11725134876 y #11726632551.

**Magnitud/coste:** EURUSD media gross +0.3553 dev / +0.7464 diag bps, con coste RT hipotético 1bps ambas negativas; XAUUSD media gross −0.2283/−1.6656 bps incluso a 0bps hipotético. Costes son escenarios, NO spreads BID/ASK medidos. No afirmar que se probó 'edge que desapareció al aplicar costes', pues no se probó ventaja gross robusta en ninguno. Política NO-NEWS para Native #814 sigue, estos gross fueron NEWS_UNFILTERED al faltar calendario as-of y por tanto NO son Traders implementables.

## III. Contrato de continuación sin buscar ganadores

1. **Fuente P0**: verificar uno a uno los seis símbolos pendientes del productor #38193802541 con 11 SHA originales/quality, sin confundir artifact published con AUDIT SHA PASS. Mantener 27 congelados. Producir manifiesto 33 sólo cuando seis/ seis pasen y sus timestamps/identidad se concilien.
2. **Scientific stop / multiplicidad**: marcar H4-GROSS-01 y 02 cerradas NO_SUPPORT. No testear misma señal con otras horas/símbolos 27×parámetros sin prereg independiente, registro de todas las hipótesis y ajuste de multiplicidad. No mirar retorno de activos para seleccionar el siguiente.
3. **Siguiente mecanismo**: justificar ventaja económica distinta por incentivos/flujo/estructura antes de ver PnL; elegir símbolo/mercado por fuentes e hipótesis, y rango histórico, control n/potencia, timeframes H4/D1 con causalidad. Considerar rango de coste ficticio y break-even gross, SIN presentar NET. Ponderar nuevos índices/metales solo si fuentes bróker realmente disponibles, no expandir sin manifiesto.
4. **Puertas operativas persistentes**: sesiones/rollover/DST broker, historia BID/ASK o PAPER live frictions futuras, calendario noticias known-asof y planes de salida pre-news, stops ejecutables, spread shocks, swaps y sizing; hasta entonces CERTIFICATION GATE BLOQUEADO. No usar CIBO/Shared para 'crear' edge ausente.
5. **DeepSeek** puede servir como auditor adversarial de hipótesis/bloqueos, pero solo fuente GitHub código/testigos/precios originales y metodología sellada tienen valor probatorio.

**Estado final reproducible:** 27/33 G0 fuente SHA; 2 modelos H4 falsados en sus versiones exactas; 0/3 sistemas económicos certificados; 0 operaciones ejecutadas; producción y VPS intactos.