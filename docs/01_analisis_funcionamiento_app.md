# Análisis del Funcionamiento de la Aplicación — Gemelo Digital Forestal

---

## 🏗️ Arquitectura General

La aplicación tiene una arquitectura de **frontend + backend desacoplados**:

- **Frontend**: React + TypeScript + Vite en `laboratorio_react/`
- **Backend**: FastAPI (Python) en `modulo_servidor/`
- **3D**: Three.js vía `@react-three/fiber` y `@react-three/drei`
- **IA generativa**: Integración con Google Gemini (opcional, mediante API key)

---

## 📌 Sitio Geográfico de Referencia

Todo el modelo está anclado al sitio **BR-Sa1** — **Floresta Nacional do Tapajós** (Amazonia brasileña), una parcela de investigación forestal real. La referencia geográfica aparece en el footer de la UI y en los datos de la parcela.

Se trabaja con dos escalas espaciales:
- **Área macro**: 500 × 500 m (25 hectáreas) → para el mapa 2D
- **Subparcela 3D**: 100 × 100 m (1 hectárea central) → para la visualización LiDAR 3D

---

## 🎛️ Flujo Principal de la Aplicación

El flujo se orquesta desde `src/App.tsx`:

### 1. Inicialización (al cargar la app)
- Carga los metadatos del **mejor modelo entrenado** llamando a `GET /modelo/mejor` del backend
- Inicializa un **escenario por defecto** (2026-09): clareo 10%, quema 5%, restauración 80 pl/ha, manejo combustibles 20%, FMC 55%, LAI 4, NDVI 0.72, precipitación 180mm, temp 27°C
- Inicializa los dos hooks personalizados:
  - `useSimulacion` → gestiona la llamada de inferencia
  - `useExplicacionIA` → gestiona la explicación por Gemini
- Verifica si el servidor tiene configurada la API key de Gemini

### 2. El Usuario Define un Escenario "What-If"
En la pestaña **Escenario**, el usuario ajusta sliders en `components/ScenarioControls.tsx`:

| Variable | Rango | Descripción |
|---|---|---|
| `clareo_pct` | 0-60% | Área basal removida |
| `quema_pct` | 0-50% | Biomasa removida por quema |
| `restauracion_plantas_ha` | 0-500 pl/ha | Nuevas plantas |
| `manejo_combustibles` | 0-100% | Reducción de combustible fino |
| `fmc` | 20-100% | Humedad del combustible |
| `lai` | 0.5-8 | Índice de área foliar |
| `ndvi` | 0-1 | Índice de vegetación |
| `precipitacion_mm` | 0-500mm | Acumulado mensual |
| `temperatura_c` | 15-35°C | Temp media |
| `year` / `month` | — | Estrato temporal |

### 3. Ejecución de la Simulación → Flujo Backend
Al presionar **"Ejecutar simulación"**, el frontend llama a `POST /simular` de `modulo_servidor/api.py`. El backend ejecuta esta cadena:

**Paso A — Gestión (`_gestion`)**: Transforma los sliders en vegetación efectiva. Por ejemplo:
- Clareo y quema **reducen** NDVI/LAI efectivos
- Restauración y manejo de combustibles **aumentan** NDVI/LAI
- Luego se **normalizan** al rango de entrenamiento de los modelos (NDVI 0.20–0.75, LAI 0.3–2.5, FMC 25–80%)

**Paso B — Inferencia de modelos ML reales** (`_resumen`):

Se calculan dos versiones del escenario:
- **Baseline / Línea base**: mismo clima pero sin gestión (clareo/quema/restauración = 0)
- **Escenario**: con las acciones del usuario

Para cada uno, se invocan hasta 3 modelos (se cargan de `modelos_entrenados/` — si no existen, degrada a fórmulas analíticas):

| Modelo | Archivo | Tipo | Predictores | Salida |
|---|---|---|---|---|
| **AGB_GEDI** | `AGB_GEDI.joblib` + scaler | Random Forest (regresión) | S1_VV, S1_VH (Sentinel-1 radar), NDVI, LAI, FMC, Temp, Precip, VPD | **Biomasa aérea (Mg/ha)** |
| **INCENDIO** | `INCENDIO.joblib` + scaler | Random Forest (clasificación) | NDVI, LAI, Temp, Precip, SW_in, VPD, NPP_3PG | **Probabilidad de incendio** |
| **3PG_LSTM** | `3PG_LSTM.h5` + scaler (carga perezosa) | Híbrido fisiológico + LSTM Keras | NPP_3PG, Temp, Precip, SW_in, VPD, LAI (ventana de 4 meses) | **NEE (Balance neto de ecosistema de C)** |

> 💡 El modelo LSTM se carga **perezosamente** solo cuando se necesita NEE, porque importar Keras tarda ~25s.

**Paso C — Serie temporal mensual**: Itera meses 1–12 aplicando estacionalidad (seno) para generar la curva anual.

**Paso D — Generación de árboles (`_trees`)**:
- Si existe `parcela_tapajos.json` → usa posiciones/alturas reales de árboles
- Si no → genera 700 árboles proceduralmente con patrones de onda (simulando dosel amazónico)
- A cada árbol le asigna un riesgo individual con jitter aleatorio

**Paso E — Traza de trazabilidad (`_insumos`)**: Registra exactamente qué valores recibió cada modelo, qué devolvió, y notas interpretativas.

El backend devuelve todo un objeto `Simulation` (tipado en `src/types.ts`): baseline, scenario, delta, temporal, trees, insumos, terreno, metadata_parcela.

---

## 🖥️ 4 Vistas / Pestañas

### 1️⃣ Escenario (`views/Scenario.tsx`)
- **Panel izquierdo**: sliders de control (ScenarioControls)
- **KPIs superiores**: 4 tarjetas con Biomasa, NPP, Riesgo incendio %, NEE — cada una con delta vs línea base
- **Comparación**: línea base vs escenario (biomasa)
- **Traza del modelo** (`components/ModelTrace.tsx`): muestra cada predictor con valor/unidad, resultado y notas interpretativas
- **Panel IA (Gemini)**: botón "Explicar con IA" que envía todo el escenario + resultados a LLM para obtener una explicación en lenguaje natural de ~150-200 palabras

### 2️⃣ Mapas 2D/3D (`views/Maps.tsx`)

**Mapa 2D** (`components/ForestMap2D.tsx`):
- Grilla 10×10 sobre el área macro 500×500m
- Agrupa árboles por celda promediando riesgo/biomasa/pérdida
- 3 capas toggleables: Biomasa, Riesgo incendio (rojo/amarillo/verde), GFW loss
- Recuadro punteado marca la subparcela 3D central

**Gemelo 3D** (`three/ForestScene.tsx`):
- **Nube de puntos LiDAR simulada** para cada árbol (188 retornos por árbol = tronco 28pts + ramas 20pts + copa 140pts)
- Proporciones biofísicas realistas de bosque amazónico (fuste = 55% altura, copa = 45%)
- Relieve topográfico real vía Copernicus DEM (interpolación bilineal en la malla)
- Color por nivel de riesgo: verde sano → amarillo medio → rojo alto
- Switch "Antes/después" que muestra lado a lado baseline vs escenario
- Cámara orbital (OrbitControls) y control flotante de tamaño de puntos LiDAR

### 3️⃣ Serie Temporal (`views/Timeline.tsx`)
- Gráfico (`components/TimeSeries.tsx`) de 12 meses con estacionalidad aplicada
- 4 líneas: biomasa base, biomasa escenario, riesgo base, riesgo escenario
- Tabla detallada con valores mensuales

### 4️⃣ Exportar Reporte (`views/Export.tsx`)
Tres formatos de descarga:
- **JSON completo**: escenario + KPIs + deltas + modelos + trazas + explicación IA + serie temporal
- **CSV**: resumen por variable, modelos usados, explicación IA (1 línea), serie temporal
- **Vista imprimible / PDF**: `window.print()` con el reporte formateado

---

## 🤖 Integración con Gemini (Explicación IA)

Endpoint `POST /explicar`:
1. Compone un **prompt estructurado** (`_prompt_explicacion`) en español con:
   - Escenario simulado (todas las variables)
   - Resultados (línea base → escenario → delta)
   - Traza detallada de cada modelo (predictoras + resultados)
   - Interpretaciones previas del laboratorio
2. Llama a la API REST de Google Gemini (`generativelanguage.googleapis.com`)
3. Devuelve el texto explicativo al frontend

El prompt instruye a Gemini a: lenguaje sencillo, ~150-200 palabras, introducción + 2-4 viñetas por modelo + conclusión práctica.

---

## 🔄 Mecanismo de Fallback / Degradación Elegante

El frontend **nunca se rompe** si el backend no está disponible:

- En `src/services/api.ts`, cada llamada `fetch` tiene un `catch` que:
  - `getModel()` → devuelve un modelo demo sintético
  - `simulate()` → ejecuta `demoSimulation()` en el navegador con fórmulas analíticas idénticas a las del backend
  - `explicarEstado()` → asume que está configurado (para que el UI no se rompa)

Del lado del backend también hay degradación por componente: si falta un `.joblib` o el `.h5`, ese modelo concreto se reemplaza por la fórmula analítica, pero los demás modelos entrenados siguen funcionando.

---

## 📊 Tipos Centrales (`src/types.ts`)

- **`Scenario`**: 12 variables de entrada del escenario what-if
- **`Simulation`**: respuesta completa del backend (baseline, scenario, delta, temporal[], trees[], insumos con trazabilidad, terreno, metadata_parcela)
- **`Tree`**: cada árbol individual (x, y, height, crown, biomass, risk, loss, elevation, en_subparcela_3d)
- **`Insumos` / `TrazaModelo`**: trazabilidad auditoriada de lo que hicieron los modelos

---

## ⚙️ Configuración

- El frontend lee la URL del backend desde `VITE_API_URL` (por defecto `http://localhost:8000`)
- El backend lee `GEMINI_API_KEY` y `GEMINI_MODEL` desde un archivo `config.py` (o variables de entorno)
- Los artefactos ML se buscan en `../modelos_entrenados/` desde el servidor:
  - `mejor_modelo.json` (metadatos)
  - `AGB_GEDI.joblib` + `_scaler.joblib`
  - `INCENDIO.joblib` + `_scaler.joblib`
  - `3PG_LSTM.h5` + `_scaler.joblib`
- Datos reales opcionales en `../recursos/datos_reales/parcela_tapajos.json` (árboles y terreno reales de Tapajós)

---

## 🎯 Resumen del Propósito

Es un **laboratorio de inferencia what-if** (no entrena modelos, solo los usa) para evaluar el impacto de decisiones de gestión forestal sobre métricas ecosistémicas clave: biomasa, productividad primaria neta (NPP), riesgo de incendio y balance neto de carbono (NEE). Lo hace combinando modelos de ML entrenados previamente con visualización 2D geoespacial y 3D estilo LiDAR, con trazabilidad total de cada inferencia y una capa de IA generativa para explicar los resultados en lenguaje sencillo.
