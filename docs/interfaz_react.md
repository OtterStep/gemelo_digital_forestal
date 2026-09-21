# Interfaz React — Laboratorio del Mejor Modelo

## Escenario
Controles con rango y tooltip: clareo, quema prescrita, restauración, manejo de combustibles, FMC, LAI, NDVI, precipitación, temperatura, año y mes. `Ejecutar simulación` invoca `POST /simular` o el fallback sintético local.

## Mapas 2D/3D
El mapa 2D presenta una grilla analítica sintética. La escena 3D presenta tronco y copa procedural, terreno, iluminación y controles orbitales. El color de la copa codifica el riesgo de incendio.

## Serie temporal
Muestra 12 meses con línea base y escenario y una tabla trazable.

## Exportación
JSON y CSV contienen `source_version=synthetic_test`. La opción de impresión permite generar PDF desde el navegador.

## Contrato
- `GET /modelo/mejor`
- `GET /diccionario`
- `POST /simular`
- `POST /reporte`
