# VT08 A — SOURCE SWING REAL M15 FVG EVIDENCE CENSUS V1 PREREG

10-oct-2026, Architect A, PR #765. **Este preregistro es anterior a las salidas y estadísticas del nuevo censo real**. Se usará exactamente el artefacto 1095d consumido GitHub run #35934924907, software SHA b2d33e1b4829d8b4afc76983decca8a99131403c, cinco mercados EURJPY/USDCHF/NZDUSD/CADJPY/USDCAD, Owner NY 01/05/09. 7Y sealed intacto.

Se medirán tres ramas SIN FILLS/PnL:
1. `C2_CLOSURE_TO_C3`: C2 H4 cerrada con sweep único C1 y regreso dentro + POI FVG preexistente verificado desde C1 M15 + touch y PS/CISD durante C2; `swing_confirmed_at` >= H4 C2.closed_at. No llamar "trade C2".
2. `C3_CONTINUATION_INTRAC3`: C2 H4 cerrada + sweep único y reversed + FVG preexistente en C2 M15 y todavía no invalidado al abrir C3 + primer touch/PS M15 durante C3. Detectar **en prefijos crecientes**, sin mirar cierre final C3 H4 en decisión intra-C3.
3. `C3_CLOSURE_TO_C4`: C2 barrió C1 un solo extremo pero falló reversal closure, C3 close-confirmed más allá del cuerpo de C2 sin sweep C2 H/L, C4 en Owner, FVG preexistente de C3 M15, touch/PS confirmado en prefijos M15 de C4. C2 dual sweep/0 sweep distinguidos y rechazados. Aún no prueba source swing POI high-low u OB (D), y FVG solo es una modalidad.

POI FVG author priority verificable solo cuando **un único FVG M15** sigue activo. Si aparecen varios, `MULTIPLE_FVG_PRIORITY_UNRESOLVED` y no elegir el ganador por rendimiento o cronología arbitraria. Los FVG C1 y C2/C3 son source THREE CLOSED M15 `left.high<right.low` (bull) / `right.high<left.low` (bear). Invalidación hasta final source-candle con precio más allá del borde distal: QORE proxy C, NO source universal.

El contrato de swing M15 recomputa su serie de velas opuestas **solo dentro de la H4 actual**; source H4 completada debe ser derivada de 16 M15 consecutivas. Fecha as-of `C2 H4 end` o `C3 H4 end` para HTF closure, LTF CISD timestamp en el candle containing signal; nunca futuro. Registrar identities estables, timestamps y hashes. Mantener salidas por mercado/año, contextos, motivos, y comparar proporciones sin thresholds esperados; auditor puede inspeccionar cualquier regla C. No extrapolar ni optimizar 1514 OHLC falsificados ni 488 B01.

El reporte completo será **SHAPE_ONLY_RESEARCH**, 0 SOURCE_COMPLETE, 0 cognitive approved, 0 orders, 0 fills, 0 PnL. Los 105 dual-sweep del censo anterior no se adjudican. 
