# TraderCoach 4 — bot de simulación

Replica, en papel, las dos estrategias operables de TraderCoach 4 VIP/Platinum (Invierta Para Ganar):

- **Smart Picks** para armar la lista: filtro de largos y filtro de cortos, con el sector líder del Sector Tracker.
- **Factor X7** para la entrada, en largo y en corto.
- **Puntos pivote** diarios y semanales para el stop y el objetivo.
- **GAP de SPY**, con las fórmulas de la hoja Power Pack.
- **Opciones** como compra de un call o de un put. La lección 34 también explica la venta; el papel no la hace, porque ahí la pérdida no queda limitada a la prima.

No envía órdenes a Interactive Brokers ni a ningún otro bróker. Escribe un plan y un diario para que tú coloques la orden, si quieres, en una cuenta demo.

Operar con estas reglas puede perder dinero. El curso no promete un resultado y este programa tampoco.

## Qué hace cada regla

**Largo (Factor X7).** Exige las dos partes:

- EPS del trimestre contra el mismo trimestre del año anterior, mayor a 15%.
- EPS anual mayor a 25%.
- Propiedad institucional mayor a 50% y menor a 90%.
- Acciones en circulación dividido el volumen promedio de 3 meses. El curso pide que ese número sea lo más pequeño posible y no deja un tope. El bot lo muestra y, si pones `max_supply_demand_days` en el config, lo usa como filtro.
- S&P 500 y la acción en tendencia alcista de unos 3 meses (precio sobre la media de 63 sesiones y media al alza).
- La media de 5 sesiones cruza por encima de la de 10, el mismo día o como máximo 2 días después, con volumen por encima de la media de 50 barras. Esa media es el estudio de volumen de la plantilla `factor X7` de Interactive Brokers. El ATR de 14 va en el gráfico y el bot lo informa. StochRSI y RVI están en el archivo y quedan ocultos.
- RSI de 14 sesiones menor a 70. Por debajo de 30 es el caso ideal, no un requisito.
- Stop en el soporte pivote más cercano por debajo del precio. Objetivo en la resistencia que deje al menos 2 a 1. Si ningún pivote llega a esa relación, el objetivo se alarga hasta ella. Si no hay un nivel del lado del stop, se usa el extremo de las últimas 5 velas.
- Además, el filtro Smart Picks de largos: volumen promedio de más de 200.000, beta mayor a 0.5, institucional mayor a 50%, EPS trimestral mayor a 15%, EPS de este año mayor a 25%, y SMA 20 sobre SMA 50 sobre SMA 200. El sector no va fijo. El ejemplo del video era Technology; el sector del día se mira en el Sector Tracker.
- Tamaño: como máximo el 30% del portafolio y como máximo el 2% de pérdida si toca el stop.
- Cierre también si la media de 10 cruza por encima de la de 5.

El punto “líderes, productos y servicios” es cualitativo. El bot no lo inventa: lo deja pendiente salvo que corras el escaneo con `--leader`.

**Corto.** El Factor X7 dice que en la venta en corto no se usa el análisis fundamental de EPS. Pide tendencia bajista de 3 meses en el S&P 500 y en la acción, cruce de la media de 10 sobre la de 5, volumen alto y RSI mayor a 30 (ideal, mayor a 70). El filtro Smart Picks de cortos, que es otro video, sí pide volumen promedio de más de 200.000, beta mayor a 0.5, institucional mayor a 50% y la pila SMA 20 bajo SMA 50 bajo SMA 200. No pide EPS ni sector.

**Pivotes.** La lección 18 calcula P, R1, R2, S1 y S2 con el high, low y close del día anterior, y otra vez con los de la semana anterior. El nivel que queda debajo del precio se usa como soporte y el que queda arriba, como resistencia. El pivote es el nivel más importante. El ejercicio pide un gráfico de 30 días con velas diarias.

**GAP de SPY.** Si hoy abre por encima del cierre de ayer, el lado es corto. Si abre por debajo, el lado es largo. El objetivo es el cierre de ayer. El stop es el 30% del rango de ayer: la hoja lo rotula como 35% del ATR, pero la fórmula usa el 30% de high menos low de ayer. Hace falta, además, probabilidad ponderada mayor a 70% y que el hueco mida entre 20% y 40% de ese rango. La probabilidad mezcla la zona del hueco (70%), el día de la semana (15%), el mes (5%) y el día del mes (10%), con las tablas de la hoja.

## Cómo correrlo

```powershell
cd tradercoach-bot
py -3 -m tradercoach.cli demo
py -3 -m tradercoach.cli gap
py -3 -m tradercoach.cli scan --symbols AAPL MSFT NVDA
py -3 -m tradercoach.cli scan --instrument options --symbols AAPL
py -3 -m tradercoach.cli paper
py -3 -m tradercoach.cli analisis
py -3 -m tradercoach.cli plantilla
py -3 -m tradercoach.cli fuentes AAPL --abrir
```

`fuentes` lista la página del curso para cada chequeo, incluidos los dos filtros de Finviz, el Sector Tracker, los pivotes, la lección 27 y las lecciones 34 a 36. Con `--abrir` escribe `data/accesos-AAPL.html` y la abre. El mapa completo está en `FUENTES.md`.

`analisis` resume el diario simulado de los últimos 30 días y escribe el estado mental de la lección 27 y los 10 mandamientos de la lección 36. `scan` empieza por la brújula de SPY a 3 y a 12 meses.

En opciones, el bot compra el call o el put fuera del dinero más cercano al precio, en el vencimiento que Yahoo abre primero. Los ejemplos de la lección 35 usaron strikes más alejados, 525 a 600 y 354 a 400, en un vencimiento de junio. Eso queda citado en la nota del contrato. No es un porcentaje fijo ni un plazo de 30 a 45 días.

No hace falta instalar librerías: corre con Python 3. `demo` no usa internet y reproduce el ejemplo numérico de la hoja del GAP. El curso pide Nasdaq para el EPS, Yahoo para estadísticas y holders, e Interactive Brokers para el gráfico. `gap` y `scan` leen esas cifras en Yahoo para calcular sin abrir la plataforma.

Copia `config.example.yaml` a `config.yaml` para cambiar el capital o la lista de acciones. El diario simulado queda en `data/journal.csv`.

Los precios del GAP usan la apertura de la última sesión ya cerrada que devuelve Yahoo. Para decidir antes de la apertura del día tendrías que pasar la apertura en premarket; el programa, tal como está, evalúa la sesión diaria ya publicada.
