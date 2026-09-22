La conexión entre los modelos de IA entrenados y el gemelo digital 3D tipo LiDAR es indirecta pero muy concreta : los modelos ML no generan la geometría LiDAR directamente, sino que predicen métricas ecosistémicas que luego se usan para escalar, colorear y modificar visualmente la nube de puntos 3D.

Aquí te explico el pipeline completo paso a paso:

## 🧠 Paso 1: Los Modelos de IA Predicen Métricas Globales
Primero, los 3 modelos entrenados predicen las métricas del escenario completo (por hectárea). Esto ocurre en _resumen() del backend:

Modelo IA Archivo entrenado Predicción (por ha) AGB_GEDI (Random Forest) AGB_GEDI.joblib + scaler Biomasa aérea total en Mg/ha INCENDIO (Random Forest) INCENDIO.joblib + scaler Probabilidad de incendio (0–1) 3PG_LSTM (Keras) 3PG_LSTM.h5 NEE (balance neto de C, no se usa en 3D)

La llamada está en _resumen() :

## 🌲 Paso 2: Se Disagregan las Métricas Globales a Cada Árbol Individual
Aquí es donde los resultados de la IA "bajan" al nivel de árbol individual. La función _trees() en api.py:230-267 recibe risk y biomass GLOBALES (del paso 1) y los distribuye entre ~700 árboles:

Dos cosas importantes aquí:

- Si existe parcela_tapajos.json → usa posiciones (x,y), alturas y elevaciones reales medidas en campo de BR-Sa1 Tapajós
- Si NO existe el archivo → genera 700 árboles proceduralmente con patrones de onda senoidal que simulan la estructura de dosel amazónico (columna 35×fila 20)
## 🎨 Paso 3: El Frontend 3D Transforma Cada Atributo en Propiedad Visual
Llega el array trees[] al componente ForestScene.tsx . La función buildPointCloud() ( líneas 26-107 ) convierte cada árbol en 188 retornos LiDAR distribuidos en 3 estructuras biofísicas:

Parte del árbol Retornos LiDAR Atributos visuales usados Tronco (fuste) 28 puntos height del árbol → define altura del tronco (55% altura total) Ramas primarias 20 puntos (4 ramas × 5 pts) crown (radio copa derivado de IA-biomasa) → largo de ramas Copa / dosel 140 puntos (domo semiesférico) risk del árbol (INCENDIO IA) → color del dosel

### 🎨 Mapeo Color ← Predicción INCENDIO (IA)
ForestScene.tsx:15-17 define la escala:

Y en línea 33 se aplica por árbol:

Además hay un gradiente lumínico vertical en la copa (copas superiores más vivas) simulando cómo el LiDAR GEDI impacta primero en la parte externa del dosel.

### 📏 Mapeo Escala ← Predicción AGB_GEDI (IA)
Líneas 30-31 :

El modo comparación (switch "Antes / después" en MapsView) renderiza dos grupos lado a lado:

- Izquierda (Antes / Baseline) : escala 0.82, riesgo fijo 0.28 (línea base sin gestión)
- Derecha (Después / Escenario) : escala 1.0, colores según la predicción de INCENDIO
Esto permite ver visualmente el impacto del escenario what-if: si el usuario aplicó clareo fuerte, verás muchos árboles rojos y más pequeños; si aplicó restauración, verás más verde y árboles más grandes.

## 🏔️ Terreno 3D también se Alimenta de Datos Reales
El componente TerrainMesh ( líneas 136-190 ) usa el campo terreno.elevations[][] que viene del backend (de parcela_tapajos.json ). Esto es DEM Copernicus interpolado bilinealmente sobre una malla de 32×32 segmentos, por lo que el relieve 3D no es plano sino que coincide con la topografía real de BR-Sa1.

## 🔁 Resumen del Flujo Completo IA → LiDAR 3D
## 💡 Nota clave
Los modelos de IA no predicen la posición de los árboles ni su estructura individual (tronco/ramas/copa). La estructura geométrica de la nube LiDAR se deriva de:

1. Datos reales si existe parcela_tapajos.json (mediciones de campo/LiDAR reales de Tapajós)
2. Proceduralización con proporciones biofísicas amazónicas (55% fuste / 45% copa)
Lo que SÍ viene directamente de los modelos IA entrenados son dos atributos visuales fundamentales que cambian con cada escenario what-if:

- El color de cada copa (verde/amarillo/rojo) según la predicción de riesgo de incendio del modelo INCENDIO
- La escala/magnitud global de la biomasa que afecta el tamaño relativo de los árboles, según AGB_GEDI
Y esto es lo que hace que el gemelo sea "digital e inteligente": al mover los sliders de gestión (clareo, restauración, etc.), el pipeline IA → visualización se actualiza en segundos y puedes ver el impacto espacialmente en el bosque 3D.