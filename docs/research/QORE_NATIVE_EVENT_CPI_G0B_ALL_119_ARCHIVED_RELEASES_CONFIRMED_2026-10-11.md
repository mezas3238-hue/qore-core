# QORE Native CPI EVENT G0B — publicado y ejecutado: **119/119 comunicados CPI oficiales comprobados**

**Fecha 2026-10-11 (America/Asuncion); ejecutado en GitHub Actions 2026-10-12 UTC.**

## Dictamen documental

**`ARCHIVE_HEADER_ALL_MATCH` — PASS exclusivamente de existencia y encabezado archivado.** Las **119 fechas de calendario CPI histórico** en el intervalo 2016-09-17..2026-09-17 UTC fueron cotejadas una por una con el [índice BLS de comunicados archivados](https://www.bls.gov/bls/news-release/cpi.htm) y con **el propio encabezado HTML de cada comunicado**. Los **119/119** enlaces coinciden con la fecha en el nombre de archivo `cpi_MMDDYYYY.htm`, el mes/año de referencia declarado y embargo **08:30 hora del Este**. No se detectaron contradicciones de fecha, hora ni referencia.

La prueba es **corroboración retrospectiva del comunicado en archivo oficial**, no una prueba de cuándo supo cada participante la fecha antes del anuncio ni de la recepción a nivel milisegundos.

## Cadena de prueba

- Pre-registro anterior a código y lectura: `docs/research/QORE_NATIVE_EVENT_CPI_G0B_ARCHIVED_RELEASE_HEADER_PREREG_2026-10-11.md` congelado en commit **`c8092917ea27afbeee2d6b4cb4df1d2cbe245d1a`**.
- Fuente fijada: calendario G0 [run #38189483643](https://github.com/mezas3238-hue/qore-core/actions/runs/38189483643), artifact **#11720651765** con 119 eventos y SHA256 verificado. CERO cambios sobre fechas.
- Verificación ejecutada [Actions **#38191272828**](https://github.com/mezas3238-hue/qore-core/actions/runs/38191272828), jobs quality y archive_headers **SUCCESS**, código SHA `8ecf74eb4c0cd4f7b387bff7dafa3b3999fe15b7`; artifact **[#11721169357](https://github.com/mezas3238-hue/qore-core/actions/runs/38191272828/artifacts/11721169357)**.
- Verificación SHA independiente de ZIP descargado: `g0b-release-header-audit.json` SHA256 `3dd736810b99e039bb995802abe5f69ee9f8fca280f17aa68764358826e2de98` y `g0b-release-header-by-date.json` SHA256 `3d78e694b353afad2bafd1c061117f8c1633fcedd79e00eebd57b387589f51d3` coinciden con archivo `OUTPUT_SHA256SUMS.txt`. Recontadas **119 filas únicas**, 119 `archive_index_match=true`, 119 `archive_header_confirmed=true`, sin contradicciones ni faltantes.
- BLS archive index tuvo **223 enlaces CPI fechados** de muchos años anteriores, filtrados SOLO por las 119 fechas congeladas; el hash del índice consultado **`e522ffbbd037e18febae96b978ac1873617661e9e75a8f5f6ac6b4271ffd6c43`**. Se cotejaron encabezados usando solo un prefijo acotado de cada release; se registran URL/hashes del prefijo y clases de coincidencia, **no valores CPI ni series**.
- Ciclo de reparación puramente técnico: primera corrida #38190785427 falló por imports (quality), segunda #38190819714 vio solo enlaces porque rechazaba archivos HTML largos, siguiente #38191020776 confirmó 48 por longitud y formato, #38191145970 confirmó 52; los formatos archivados 2016–2021 tenían texto **Windows-1252**, incluso separador `EN DASH` no UTF-8; algunas cabeceras 2022 carecían del nombre del día de la semana. Se añadieron pruebas específicas y se verificó sin alterar un solo calendario. Las cifras anteriores no son ensayos económicos ni seleccionar datos por resultados.
- Última rama contiene pruebas adicionales del formato 2016 (CP1252) con code head `518a6c565f3ec5e1430aad835fecd15d359af69f`; la corrida previa exitosa que sí ejecutó el mismo código fuente funcional fue #38191272828. El resultado 119/119 ya tiene su artifact verificado.

## Reconciliación con G0 M1

La cohorte documental **119 comunicados reales archivados** es un concepto distinto de la subcohorte de **113 eventos con 71/71 timestamps M1 disponibles** en NAS100/USTEC de CIBO [G0 #38189483643, artifact #11720822239](https://github.com/mezas3238-hue/qore-core/actions/runs/38189483643/artifacts/11720822239). Los seis días con ventanas incompletas **no implican falta de comunicado CPI**: 2017-01-18, 2017-03-15, 2017-04-14, 2017-05-12, 2020-04-10, 2022-12-13. No imputar datos ni atribuir causalidad de huecos a vacaciones/feriados sin evidencia broker.

**2025:** BLS indexa como comunicado real el CPI de referencia **septiembre de 2025 publicado el 24 de octubre de 2025**. **Octubre 2025 de referencia nunca tuvo comunicado**; no añadir release ausente al estudio (fuente BLS shutdown FAQ). Los 11 registros del año de publicación 2025 son correctos.

## G0C, G0D y potencia siguen bloqueando economía G1

**G0C consenso previo.** La posibilidad técnica publicada por [Trading Economics Point-in-Time](https://docs.tradingeconomics.com/economic_calendar/point-in-time/) no acredita que el proveedor preserve vintages CPI de 2016 o snapshots exactos **T-24 h/T-5 min**. El esquema TE `Forecast`/ `TEForecast`/ `LastUpdate` puede reflejar un valor cambiado después del evento; no inferir que el forecast estuvo disponible antes por aparecer en el registro histórico. Segundo proveedor independiente (Reuters/Econoday/Bloomberg u otro licenciado) tampoco disponible en nuestras conexiones. **Se congeló previamente una lista exacta de 24 eventos diagnósticos sin mirar forecasts:** `docs/research/QORE_NATIVE_EVENT_CPI_G0C_TWO_SOURCE_24_EVENT_PIT_COMPARISON_PREREG_2026-10-11.md`. Requiere headline/core CPI MoM SA definición idéntica, timestamps previos, procedencia independiente, cobertura 24/24, diferencia máxima 0,05 puntos porcentuales y documentación de discrepancias. Acuerdo >95% en 24 fechas **no prueba fiabilidad poblacional al 95%**. `TWO_PROVIDER_COMPARISON_NOT_RUN`.

**G0D coste CPI.** Sin spreads históricos reales NAS100/USTEC, latencia, contrato, comisiones y slippage al minuto del anuncio, ningún efecto de decenas de bps bruto implica rentabilidad neta. `EVENT_SPREAD_COST_UNVERIFIED`. `BID/ASK` no fue necesario para fuente CPI G0B, pero **sí** para credibilidad económica transaccional.

**Potencia estadística fuente-only.** Máximo nominal **113 eventos con ventana M1 completa**, antes de censurar por ausencia de consenso, señal y costos. La cota teórica de efecto mínimo detectable en muestra independiente, alfa 5% bilateral y potencia 80%: `MDE≈2.802σ/sqrt(n)`. Sin inferir σ de los precios:
- n=113: para desviación estándar supuesta de resultado de 10/20/40/60bps => MDE aprox **2,64 / 5,27 / 10,54 / 15,82 bps**;
- n=56 si se parte muestra por signo: MDE aprox **3,74 / 7,49 / 14,97 / 22,47 bps**.
- Si se necesita `LCB95>+2bps`, la media verdadera debe superar 2bps **más** el margen de precisión exigido; costes y persistencia temporal aumentan la dificultad. Estas cifras **NO** son volatilidad medida ni expectativa del edge.

**Decisión:** `G0B_ARCHIVE_RELEASE_PASS`, `G1_BLOCKED_CONSENSUS_ASOF_AND_EVENT_COST_AND_POWER`. No abrir un backtest económico con resultado conocido CPI o costos supuestos. El posible drift post-publicación 08:35→09:05 NY queda solo como **familia candidata**, sin señal firmada ni riesgo predefinidos: se completarán reglas causal first-online/retención, proveedor/scope as-of y costes antes de cualquier PnL.

**Trabajo GitHub research únicamente, 0 operaciones, 0 traders certificados, producción/VPS/MT5/CIBO/Shared intactos.**
