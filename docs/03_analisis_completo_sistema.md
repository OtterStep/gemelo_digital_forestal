# Análisis Completo del Sistema — Gemelo Digital Forestal

## 🎯 Propósito General del Proyecto

El **Gemelo Digital Forestal** es un prototipo reproducible de laboratorio científico para la **gestión forestal inteligente** centrado en el sitio de investigación **BR-Sa1 / Floresta Nacional do Tapajós** (Amazonia brasileña, ~100.000 hectáreas).

Es un **sistema de inferencia what-if** (no entrena modelos en tiempo real, solo reutiliza artefactos previamente entrenados) que permite evaluar el impacto de decisiones de gestión forestal sobre 4 métricas ecosistémicas clave:

| Métrica | Unidad | Significado |
|---|---|---|
| **Biomasa aérea (AGB)** | Mg/ha | Cantidad de carbono almacenado en árboles vivos |
| **NPP** (Productividad Primaria Neta) | Mg C/ha/año | Crecimiento neto del bosque |
| **Riesgo de incendio** | Probabilidad 0-1 | Probabilidad de evento de fuego |
| **NEE** (Balance neto de ecosistema) | flujo neto de C | Si es < 0: el bosque absorbe CO₂ (sumidero) |

El proyecto está diseñado para funcionar en **modo demo 100% offline** (sin internet, sin credenciales) con datos sintéticos etiquetados `synthetic_test`, y **degradar elegantemente** a artefactos reales de entrenamiento cuando estén disponibles (entrenados externamente en Google Colab).

---

## 🏗️ Arquitectura General del Sistema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GOOGLE COLAB (ENTRENAMIENTO)                         │
│  aentrenamiento_colab.ipynb  →  descarga datos (GEE/GEDI/FLUXNET/Drive)     │
│                                → fusiona → EDA → CV → GridSearch            │
│                                → entrena 8 modelos                           │
│                                → valida estadísticamente                     │
│                                → EXPORTAR ARTEFACTOS (Drive)                 │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ copiar manualmente a:
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DIRECTORIO: modelos_entrenados/                      │
│  mejor_modelo.json  ·  historial_entrenamiento.json  ·  resultados_metricas │
│  AGB_GEDI.joblib (+scaler)   ·   INCENDIO.joblib (+scaler)                  │
│  3PG_LSTM.h5    (+scaler)    ·   MLR_baseline / LAI / FMC / 3PG_RF / LGBM   │
└───────────────────────────┬──────────────────────┬───────────────────────────┘
                            │                      │
                            ▼                      ▼
┌──────────────────────────────┐   ┌────────────────────────────────────────┐
│     STREAMLIT (3 pantallas)  │   │   FASTAPI (backend inferencia)         │
│  app.py              (Home)  │   │   modulo_servidor/api.py                │
│  pages/1_Monitor...py        │   │   GET  /modelo/mejor  /diccionario      │
│  pages/2_Probador....py      │   │   POST /simular  /reporte  /explicar    │
│                              │   │   GET  /explicar/estado                 │
└──────────────────────────────┘   └───────────────┬────────────────────────┘
                                                   │ REST JSON
                                                   ▼
                                   ┌───────────────────────────────────┐
                                   │   REACT + THREE.JS (FRONTEND)     │
                                   │   laboratorio_react/               │
                                   │   4 pestañas: Escenario · Mapas   │
                                   │   2D/3D · Serie temporal · Export │
                                   └───────────────────────────────────┘
```

---

## 📁 Estructura Completa de Carpetas y Archivos (Inventario Exhaustivo)

### 🔹 Raíz del Proyecto (`gemelo_digital_forestal/`)

| Archivo / Carpeta | Propósito |
|---|---|
| **`README.md`** | Documentación de entrada: propósito, ejecutar Streamlit, descripción de las 3 pantallas. |
| **`config.py`** | Configuración central del sistema: rutas (ROOT_DIR, MODELOS_DIR), SEED, SOURCE_VERSION, GEMINI_API_KEY, AREA_ESTUDIO (bbox, hectáreas), YEARS (2019-2023), lista MODELOS, PHASE_NAMES (9 fases del pipeline). |
| **`app.py`** | Entrada principal de **Streamlit Home**: 4 métricas en tarjetas (Estado/Fuente/Nº modelos/Entrenamiento real), detección de artefactos locales, diagrama del pipeline ASCII. |
| **`requirements.txt`** | 15 dependencias: `streamlit 1.50`, `pandas 2.2`, `numpy 2.1`, `scikit-learn 1.6`, `plotly 5.24`, `joblib 1.4`, `fastapi 0.115`, `uvicorn 0.34`, `python-dotenv`, `matplotlib`, `openpyxl`, `reportlab`, `mkdocs-material`. |
| **`.env.example`** | Plantilla para variables de entorno (GEMINI_API_KEY, etc.). |
| **`.gitignore` · `.gitattributes`** | Configuración Git. |
| **`CONFIGURACION_NECESARIA.md`** | (Supuesto) guía de setup. |
| **`mkdocs.yml`** | Configuración de la documentación estática MkDocs Material. |
| **`aentrenamiento_colab.ipynb`** | Notebook Jupyter pensado para ejecutar en **Google Colab**: es el único lugar donde se descargan datos y se entrena modelos pesados. Genera artefactos exportables. |
| **`pages/`** | Páginas secundarias de Streamlit (menú lateral). |
| **`docs/`** | Documentación MkDocs: 11 ADRs, tutoriales, API ref, guía usuario, metodología, limitaciones, etc. |
| **`laboratorio_react/`** | Frontend React V2 del Laboratorio del Mejor Modelo (app de usuario final). |
| **`modulo_servidor/`** | Backend FastAPI de inferencia (sirve al frontend React). |
| **`modulo_ia/`** | Módulo Python con toda la lógica de ML: demo, entrenamiento, CV, selección, pruebas estadísticas, exportación. |
| **`modulo_datos/`** | (Skeleton `__init__.py` + README) Módulo de ingesta/carga de datos. |
| **`modulo_fusion/`** | (Skeleton) Módulo de fusión de fuentes de datos. |
| **`modulo_carbono/`** | (Skeleton) Módulo dedicado a modelos de ciclo de carbono. |
| **`modulo_riesgo_incendio/`** | (Skeleton) Módulo dedicado a modelos de riesgo de fuego. |
| **`modulo_escenarios/`** | (Skeleton) Módulo de definición/ejecución de escenarios what-if. |
| **`modulo_visualizacion/`** | (Skeleton) Módulo de gráficos y visualización. |
| **`modulo_reportes/`** | (Skeleton) Módulo de generación de reportes PDF/Excel. |
| **`utilidades/`** | (Skeleton) Utilidades compartidas. |
| **`modelos_entrenados/`** | **CARPETA CLAVE**: almacén de artefactos exportados (`.joblib`, `.h5`, `.json`). Tiene `.gitkeep`; se popula al copiar resultados de Colab. |
| **`recursos/`** | Datos de ejemplo y datos reales de parcela. |
| **`scripts/`** | Scripts auxiliares (ej: extracción GEE). |

---

### 🔹 `pages/` — Streamlit Multi-Page

| Archivo | Propósito |
|---|---|
| **`1_Monitor_Entrenamiento.py`** (680 líneas) | **Pantalla principal del pipeline de ML**: 9 pestañas (una por fase) con progreso, métricas, previews de datos reales (FLUXNET, ERA5), gráficos Plotly (CV, bootstrap IC95, violines de errores, histogramas delta), sidebar para subir artefactos manualmente, botón regenerar demo. Incluye ejecución en vivo de pruebas estadísticas (t-test pareado + bootstrap 1000 remuestreos) sobre `predicciones_modelos.csv` con cache. |
| **`2_Probador_Modelos.py`** (194 líneas) | **Playground de inferencia unitaria/lote**: selector de 8 modelos catalogados (AGB_GEDI, MLR_baseline, LAI_MODEL, FMC_MODEL, 3PG_RF, INCENDIO, 3PG_LSTM, LightGBM), cada uno con archivo+scaler definidos. Genera sliders automáticamente derivados del `StandardScaler` (mean ± 3·std). Soporta inferencia manual y CSV batch. Detecta modelos mal ajustados (R²<0.3) y avisa. |

---

### 🔹 `docs/` — Documentación MkDocs Material

| Subcarpeta / Archivo | Contenido |
|---|---|
| **`index.md`** | Diagrama mermaid del pipeline arquitectura (Datos→Fusión→Colab→modelos_entrenados→Streamlit/FastAPI→React). |
| **`instalacion.md`** | Guía de setup. |
| **`guia_usuario.md`** | Manual de uso. |
| **`metodologia.md`** | Descripción de métodos científicos. |
| **`modelos.md`** | Catálogo de modelos. |
| **`metricas_evaluacion.md`** | R², RMSE, MAE, ROC-AUC. |
| **`limitaciones.md`** | Advertencias y alcances. |
| **`interfaz_react.md`** | Guía interfaz React. |
| **`interfaz_streamlit.md`** | Guía interfaz Streamlit. |
| **`diccionario_datos.md` · `.json`** | Definición de variables. |
| **`adr/` (11 ADRs)** | Architecture Decision Records: 001 área estudio, 002 tiempo, 003 biomasa, 004 fluxnet, 005 soil, 006 IFN, 007 interfaces colab, 008 monitor, 009 React, 010 API, 011 3D. |
| **`api/referencia.md`** | Documentación endpoints FastAPI. |
| **`tutoriales/` (3 tutoriales)** | 01 descarga datos, 02 fusión, 03 predicción Streamlit. |

---

### 🔹 `laboratorio_react/` — Frontend React (Vite + TypeScript)

| Subcarpeta / Archivo | Propósito |
|---|---|
| **`package.json`** | React 18, Three 0.169, `@react-three/fiber` 8.17, `@react-three/drei` 9.122, Vite 6, Vitest 3, TypeScript 5.7. Scripts: `dev`, `build`, `preview`, `test`. |
| **`vite.config.ts`** | Config bundler Vite. |
| **`tsconfig.json`** | Config TypeScript. |
| **`.env.example`** | `VITE_API_URL`. |
| **`index.html`** | HTML entry. |
| **`README.md`** | Ejecución: `npm install && npm run dev` + `uvicorn modulo_servidor.api:app --port 8000`. |
| **`public/diccionario_datos.json`** | Diccionario de variables estático fallback. |
| **`public/mejor_modelo.json`** | Metadatos del mejor modelo fallback estático. |
| **`src/main.tsx`** | Punto de entrada React: `<React.StrictMode><App />`. |
| **`src/App.tsx`** (50 líneas) | Orquestador: carga modelo, gestiona 4 tabs, pasa props entre hooks y vistas, estado `Scenario` inicial. |
| **`src/types.ts`** (99 líneas) | **Tipos centrales**: `Scenario` (12 campos), `Metricas` (biomasa/npp/riesgo/nee), `Predictora`, `TrazaModelo`, `Insumos`, `Tree` (9 campos x/y/height/crown/biomass/risk/loss/elevation/en_subparcela_3d), `Terreno` (grid/elevation), `ParcelaMetadata`, `Simulation`, `Model`. |
| **`src/style.css`** | Hojas de estilo globales. |
| **`src/services/api.ts`** | Cliente REST: `getModel()`, `simulate()`, `getDictionary()`, `explicarEstado()`, `explicarIA()`. **Cada función tiene fallback demo local** (`demoSimulation`) con fórmulas analíticas idénticas al backend, en caso de que FastAPI no responda. |
| **`src/services/api.test.ts`** | Tests Vitest del API client. |
| **`src/hooks/useSimulacion.ts`** | Custom hook React: estado `{loading, result, run()}` que llama a `simulate()`. |
| **`src/hooks/useExplicacionIA.ts`** | Custom hook React: estado `{configurado, explicacion, cargando, error, run()}` que llama a `explicarIA()`. |
| **`src/views/Scenario.tsx`** | Vista 1: panel sliders izq + 4 KPI cards + comparación base/escenario + `ModelTrace` + panel Gemini con botón "Explicar con IA". |
| **`src/views/Maps.tsx`** | Vista 2: `ForestMap2D` + `ForestScene` 3D con switch comparación antes/después. |
| **`src/views/Timeline.tsx`** | Vista 3: `TimeSeries` SVG + tabla 12 meses. |
| **`src/views/Export.tsx`** | Vista 4: 3 botones (↓JSON, ↓CSV, imprimir PDF) + reporte formateado. |
| **`src/components/ScenarioControls.tsx`** | 11 sliders range input (clareo, quema, restauración, combustible, FMC, LAI, NDVI, precip, temp, año, mes) + tooltips. |
| **`src/components/KpiCard.tsx`** | Tarjeta KPI reutilizable: label + valor + delta (↑verde / ↓rojo). |
| **`src/components/ModelTrace.tsx`** | Traza de trazabilidad: gestión + vegetación_efectiva + 3 tarjetas por modelo (objetivo, predictoras, resultado) + lista interpretaciones. |
| **`src/components/ForestMap2D.tsx`** | Grilla 10×10 (área macro 500×500m) con toggle 3 capas (biomasa/riesgo/loss), celdas coloreadas por riesgo, recuadro punteado verde para la parcela 3D central. |
| **`src/components/TimeSeries.tsx`** | Gráfico SVG polilínea (baseline vs scenario) sin librerías. |
| **`src/components/Tooltip.tsx`** | Tooltip informativo. |
| **`src/components/Glossary.tsx` · `Glossary.css`** | Glosario drawer lateral con términos (biomasa, NPP, riesgo, NEE, etc.). |
| **`src/three/ForestScene.tsx`** (313 líneas) | **Componente 3D principal**: Canvas Three.js, `buildPointCloud()` que genera 188 retornos LiDAR por árbol (28 tronco cónico + 20 ramas × 4 + 140 copa domo semiesférico con distribución no uniforme hacia cáscara superior), colores por riesgo, `TerrainMesh` con elevación DEM Copernicus bilineal, `OrbitControls`, overlay slider tamaño punto, switch modo comparación lado-a-lado (baseline escala 0.82 vs escenario escala 1.0). |

---

### 🔹 `modulo_servidor/` — Backend FastAPI

| Archivo | Propósito |
|---|---|
| **`api.py`** (481 líneas) | **Motor de inferencia completo**: FastAPI con CORS *. 8 endpoints. Cadena de funciones: `_artefactos()` carga modelos/scalers con degradación por componente (si falta un `.joblib`, ese modelo cae a sintético pero los demás funcionan); `_cargar_lstm()` carga perezosa de Keras (para evitar ~25s de import si no se pide NEE); `_gestion()` normaliza sliders a rango entrenamiento y calcula vegetación efectiva (clareo/quema reducen, restauración aumenta); `_fila()` construye vectores de predictores con estacionalidad seno mensual; `_pred_biomasa/_riesgo/_nee` invocan los `.joblib/.h5` reales; `_resumen()` compone baseline vs escenario; `_trees()` distribuye risk/biomass globales a árboles individuales con jitter (datos reales si existe `parcela_tapajos.json`); `_insumos()` compone traza auditable; `_prompt_explicacion()` arma prompt español estructurado de ~500 tokens para Gemini; `_gemini()` llama REST a `generativelanguage.googleapis.com`. |
| **`README.md`** | Descripción corta. |
| **`__init__.py`** | Package marker. |

Endpoints disponibles:
```
GET  /modelo/mejor      → metadatos mejor modelo (R², RMSE, MAE, hiperparámetros, source_version)
GET  /diccionario       → rangos y unidades de todas las variables de control
POST /simular           → endpoint principal: recibe Scenario, devuelve Simulation completa
POST /reporte           → stub para generador PDF/Excel
GET  /explicar/estado   → indica si GEMINI_API_KEY está configurada
POST /explicar          → envía escenario + simulación a Gemini, devuelve explicación texto
```

---

### 🔹 `modulo_ia/` — Lógica de Machine Learning

| Archivo | Propósito |
|---|---|
| **`demo.py`** (43 líneas) | Genera `historial_entrenamiento.json` demo **determinista** (seed 42): 5 modelos con métricas plausibles (Random Forest R²=0.84 → 3-PG+LSTM R²=0.92), 5 folds CV con ruido normal, 9 fases con duraciones crecientes, métricas por etapa. Se llama cuando no hay historial real. |
| **`entrenamiento.py`** | Skeleton `obtener_estado_fase()` para la fase 6 del pipeline. |
| **`validacion_cruzada.py`** | Skeleton CV k=5. |
| **`ajuste_hiperparametros.py`** | Skeleton GridSearchCV. |
| **`seleccion_modelo.py`** | Skeleton selección mejor modelo. |
| **`analisis_exploratorio.py`** | Skeleton EDA. |
| **`pruebas_estadisticas.py`** (172 líneas) | **Motor estadístico serio**: `bootstrap_ic95()` 1000 remuestreos R² percentiles 2.5/97.5; `test_t_pareado_errores()` t-student `ttest_rel` sobre errores absolutos pareados (modelo vs referencia AGB_GEDI); `ejecutar_pruebas_en_vivo()` lee `predicciones_modelos.csv`, ejecuta ambos contrastes sobre todos los modelos de AGB y además calcula AUC para INCENDIO. Retorna estructura JSON-safe lista para Plotly. |
| **`exportar_predicciones.py`** | Script CLI: `python -m modulo_ia.exportar_predicciones` para regenerar `predicciones_modelos.csv` re-leyendo los modelos y dataset procesados sin reentrenar. |
| **`__init__.py`** | Package marker. |

---

### 🔹 `modelos_entrenados/` — Almacén de Artefactos

Contiene `.gitkeep` inicialmente. Cuando se copian resultados de Colab aquí se encuentra:

| Artefacto Tipo | Nombre esperado | Consumido por |
|---|---|---|
| Metadatos JSON | `mejor_modelo.json` | FastAPI `/modelo/mejor`, Streamlit Home, Monitor pestaña 8 |
| Historial JSON | `historial_entrenamiento.json` | Streamlit Monitor 9 pestañas |
| Métricas JSON | `resultados_metricas.json` | Monitor pestañas 4 (CV) y 7 (estadística) |
| Modelo + Scaler | `AGB_GEDI.joblib` + `AGB_GEDI_scaler.joblib` | FastAPI, Probador Streamlit |
| Modelo + Scaler | `INCENDIO.joblib` + `INCENDIO_scaler.joblib` | FastAPI, Probador |
| Modelo + Scaler | `3PG_LSTM.h5` + `3PG_LSTM_scaler.joblib` | FastAPI, Probador (carga perezosa keras) |
| Modelo + Scaler | `MLR_baseline`, `LAI_MODEL`, `FMC_MODEL`, `3PG_RF`, `LightGBM` (`.joblib` + scaler) | Probador |
| Metadata JSON | `<NOMBRE>_metadata.json` (x cada modelo) | Probador (objetivo, métricas, predictoras), Monitor |
| Columnas JSON | `columnas_predictoras.json` | Monitor pestaña 6 |
| Predicciones CSV | `predicciones_modelos.csv` | Monitor pestaña 7 (pruebas estadísticas en vivo) |

---

### 🔹 `recursos/` — Datos de Entrada

| Subcarpeta / Archivo | Contenido |
|---|---|
| **`datos_ejemplo/predicciones_synthetic_test.csv`** | CSV ejemplo que el Probador y el Monitor usan para previsualizar estructura de entrada. |
| **`datos_reales/parcela_tapajos.json`** | Datos reales de BR-Sa1: `arboles[]` con x/y/height/crown/elevation/en_subparcela_3d; `terreno` con grid DEM; `metadata` con sitio, lat/lon, área, total árboles macro y subparcela 3D, fuente. Consumido por FastAPI `_trees()` y `_datos_parcela()`. |
| **`datos_crudos/`** (no aparece en LS pero sí en Monitor) | Espera `fluxnet/AMF_*FLUXMET_MM_*.csv` y `AMF_*ERA5_MM_*.csv` (FLUXNET AmeriFlux BR-Sa1 mensual + ERA5 forcings). Monitor lee columnas núcleo: TIMESTAMP, TA_ERA (temperatura), SW_IN_ERA (radiación onda corta), VPD_ERA (déficit presión vapor), P_ERA (precipitación), WS_ERA (viento), NEE_CUT_REF, GPP_DT_VUT_REF, RECO_DT_VUT_REF. |
| **`datos_procesados/`** | Espera `dataset_fusionado.csv` (264×25 fusionado FLUXNET × satélite). |

---

### 🔹 Módulos Skeleton (Preparados para Ampliación Futura)

| Módulo | Objetivo esperado |
|---|---|
| `modulo_datos/` | Clases `CargadorGEDI`, `CargadorFLUXNET`, `CargadorSentinel`, `CargadorLandsat`, `CargadorMODIS` — descarga/locura de fuentes heterogéneas. |
| `modulo_fusion/` | Alineación temporal espacial: join FLUXNET × GEDI huellas × Sentinel píxeles × MODIS MCD64A1 fecha fuego. Relleno NaN. |
| `modulo_carbono/` | Implementación del modelo fisiológico **3-PG** (Physiological Principles Predicting Growth) como clase Python pura para generar NPP_3PG sin depender de ML. |
| `modulo_riesgo_incendio/` | Índices de riesgo (FWI McArthur, NFDRS), integración con MODIS MCD64A1 áreas quemadas. |
| `modulo_escenarios/` | Factory de escenarios predefinidos: `BusinessAsUsual`, `RestauracionIntensiva`, `CambioClimaticoRCP85`, etc. |
| `modulo_visualizacion/` | Funciones Plotly altamente parametrizables para EDA. |
| `modulo_reportes/` | Clases `GeneradorPDF` (reportlab) y `GeneradorExcel` (openpyxl) consumiendo el endpoint `/reporte`. |
| `utilidades/` | Logger, lectura/escritura JSON, geometrías geográficas. |
| `scripts/extraer_gee.py` | Google Earth Engine Python API: extracción Sentinel-1/2, Landsat, MODIS para el bbox BR-Sa1. |

---

### 🔹 Dependencias Clave y su Rol

| Librería | Uso en el sistema |
|---|---|
| **scikit-learn 1.6** | Random Forest (AGB_GEDI, INCENDIO), StandardScaler, GridSearchCV, métricas r2_score/roc_auc_score. |
| **Keras/TensorFlow** (implícito vía `.h5`) | Modelo 3PG_LSTM híbrido (solo cuando existe el archivo y se llama a NEE). |
| **joblib 1.4** | Serialización/deserialización `.joblib` de modelos y scalers. |
| **scipy** | `stats.ttest_rel` para t-test pareado en pruebas estadísticas. |
| **pandas/numpy** | DataFrames, arrays, operaciones numéricas en toda la cadena. |
| **streamlit 1.50** | Home + Monitor 9 pestañas + Probador: estado sesión, caché `@st.cache_data` y `@st.cache_resource`, métricas, tabs, file_uploader. |
| **plotly 5.24** | Gráficos interactivos: violin errores AGB, barras R² bootstrap con IC, histogramas delta, heatmap correlaciones, barras CV k=5. |
| **fastapi 0.115 + uvicorn 0.34** | API REST JSON async con `@lru_cache` para cargas perezosas y middlewares CORS. |
| **Three.js + react-three/fiber + drei** | Renderizado WebGL 3D de la nube LiDAR (700 árboles × 188 pts = ~131.600 puntos) con controles orbitales y niebla. |
| **Vite 6 + TypeScript 5.7 + Vitest 3** | Bundler dev, tipado fuerte, tests unitarios. |
| **python-dotenv** | Carga `GEMINI_API_KEY` desde `.env`. |
| **requests** | Cliente HTTP para llamar a Gemini API REST. |
| **reportlab / openpyxl** | Preparados para generadores de reportes futuros. |
| **mkdocs-material + mkdocstrings** | Sitio de documentación estática. |

---

## 🛠️ El Pipeline de 9 Fases de Entrenamiento (Monitoreado por Streamlit)

Definido en `config.py` → `PHASE_NAMES`. Cada fase tiene estado (completada/en curso/pendiente/error), timestamps, duración, log y métricas específicas.

| Fase | Nombre | Qué produce | Métricas registradas |
|---|---|---|---|
| 1 | Descarga / generación de datos | Carpeta `recursos/datos_crudos/` con FLUXNET + ERA5 + GEDI + Satélite | fuentes_generadas (8), registros (~12.540) |
| 2 | Fusión de datos | `dataset_fusionado.csv` (264×25): join temporal por TIMESTAMP/mes/pixel | variables_fusionadas (24), filas (3.250), nulos_pct (0.7%) |
| 3 | Análisis exploratorio (EDA) | Describe + matriz correlación + detección outliers | features (24), correlacion_max (0.91), outliers_pct (2.4%) |
| 4 | Validación cruzada k=5 | R²/RMSE por fold por cada uno de 5 modelos | k=5, mejor_r², folds[modelo][r2[], rmse[]] |
| 5 | Ajuste de hiperparámetros | Mejor combinación GridSearch por modelo | método="GridSearchCV", combinaciones=18, mejor_r² |
| 6 | Entrenamiento final | Artefactos `.joblib/.h5` + scalers + metadata JSON | modelos_entrenados=5, epochs=25, tiempo_s |
| 7 | Pruebas estadísticas | Bootstrap IC 95% + t-test pareado | prueba="t-test pareado + bootstrap", p_value, ic95_r2[] |
| 8 | Selección de modelo | `mejor_modelo.json` con R²/RMSE/MAE/ROC-AUC | mejor_modelo="3-PG + LSTM", métricas, CV, variables predictoras |
| 9 | Exportación de artefactos | Carpeta `modelos_entrenados/` lista para producción | archivos=4, version=SOURCE_VERSION |

---

## 🧩 3 Interfaces de Usuario y su Público Objetivo

| Interfaz | Tecnología | URL/Puerto | Usuario tipo | Caso de uso |
|---|---|---|---|---|
| **Home Streamlit** | Streamlit multipage | `streamlit run app.py` / puerto por defecto | Investigador jefe, gestor de proyecto | Resumen ejecutivo: estado artefactos, arquitectura, conteo modelos. |
| **Monitor Entrenamiento** | Streamlit page 1 | Mismo | Científico de datos | Revisar cada una de las 9 fases del pipeline: logs, previews datos, gráficos CV, violines, descargar historial JSON, subir artefactos manualmente, ejecutar pruebas estadísticas en vivo. |
| **Probador Modelos** | Streamlit page 2 | Mismo | Ingeniero de ML + QA | Inferencia unitaria (sliders auto-derivados de scaler) y lote CSV con cualquiera de los 8 modelos; validar que el artefacto `.joblib` produce resultados coherentes. |
| **Laboratorio React** | React Vite dev server + FastAPI | `npm run dev` (5173) → `VITE_API_URL` (8000) | Usuario final: gestor forestal, tomador de decisiones, divulgador | Simular escenarios what-if con sliders sencillos, ver impacto en 2D/3D/LiDAR, pedir explicación sencilla IA, exportar reporte para reunión. |
| **Docs MkDocs** | MkDocs Material | `mkdocs serve` | Todo el equipo / usuarios nuevos | Documentación: ADRs, tutoriales, metodología, guías, API ref. |

---

## ⚡ Flujo End-to-End Completo (Desde Datos Hasta Visualización 3D)

```
1) Colab ejecuta aentrenamiento_colab.ipynb
   ├─► extrae GEDI L4A, Sentinel-1/2, Landsat, MODIS MCD64A1, FLUXNET BR-Sa1, ERA5
   ├─► fusiona → dataset 264×25
   ├─► EDA → CV k=5 → GridSearch → entrena 8 modelos (incluyendo 3PG_LSTM)
   ├─► t-test pareado + bootstrap IC95%
   └─► exporta todo a modelos_entrenados/ (copiar a carpeta local)

2) Usuario abre Streamlit:
   ├─► app.py detecta artefactos reales ✅
   ├─► Monitor muestra historial con métricas reales (no demo)
   └─► Probador permite inferir con AGB_GEDI e INCENDIO con sliders reales

3) Usuario abre Laboratorio React:
   ├─► npm run dev → carga App.tsx → getModel() → muestra nombre y R²/RMSE/MAE
   ├─► Usuario ajusta clareo=30% + quema=10% + restauracion=200 pl/ha
   ├─► Click "Ejecutar simulación" → useSimulacion.run() → POST /simular
   │      ├─► Backend: _gestion() → NDVI_efectivo = 0.72*(1-0.3)*(1-0.1*0.8) + 200*0.0002 = 0.47
   │      ├─► _fila(mes=9) → construye vector predictores normalizados
   │      ├─► AGB_GEDI.predict(scaler.transform([vec])) → biomasa = 156 Mg/ha
   │      ├─► INCENDIO.predict_proba(...) → riesgo = 41%
   │      ├─► (opcional) 3PG_LSTM.predict(ventana4meses) → NEE = -1.8 (sumidero)
   │      ├─► _trees(riesgo=0.41, biomasa=156) → 700 árboles con riesgo individual color amarillo-verdoso
   │      ├─► _insumos() → traza con todas las predictoras y valores exactos
   │      └─► devuelve Simulation JSON completo
   ├─► React renderiza 4 KPIs con deltas rojos/verdes
   ├─► User va a "Mapas 2D/3D"
   │      ├─► ForestMap2D: grilla 10×10 con celdas amarillas riesgo medio
   │      └─► ForestScene 3D: 131.600 puntos LiDAR, copas mayormente verdes→amarillas, cámara orbital
   ├─► User activa "Antes/después" → izquierda baseline verde escala 0.82, derecha escenario amarillo escala 1.0
   ├─► User click "Explicar con IA" → POST /explicar → Gemini devuelve 180 palabras explicando que la restauración compensó parte del clareo
   └─► User va a "Exportar reporte" → Descarga JSON + CSV + imprime PDF con todo el resumen
```

---

## 🔐 Estrategias de Robustez y Degradación Elegante

1. **Nunca descarga datos automáticamente**. Si no hay CSV locales, muestra aviso sin intentar bajar nada (evita costos GEE/credenciales).
2. **Nunca re-entrena modelos**. Streamlit Monitor y Probador solo leen artefactos; si faltan usa demo sintético seed=42.
3. **Degradación por componente** en FastAPI: si AGB_GEDI.joblib falta pero INCENDIO.joblib existe, INCENDIO funciona real y AGB cae a fórmula analítica; no se rompe nada.
4. **Fallback frontend 100% offline**: `services/api.ts` caché demo local `demoSimulation()` produce resultados idénticos al backend sin necesidad de FastAPI ni internet.
5. **LSTM carga perezosa**: importar `keras.models.load_model` tarda ~25s → solo se importa cuando la primera petición pide NEE. Mientras tanto los demás endpoints responden normal.
6. **Datos reales opcionales de parcela**: si `parcela_tapajos.json` no existe, `_trees()` genera 700 árboles procedurales sin error.
7. **Cachés múltiples**: `@lru_cache` Python, `@st.cache_data`/`@st.cache_resource` Streamlit, React `useMemo`.
8. **Seed determinista 42** en todos los generadores pseudoaleatorios (numpy, random, Python) → demo reproducible siempre.
9. **CORS `*` en FastAPI**: evita bloqueos al servir React desde distinto puerto.
10. **Validación de NEE**: `if cur["nee"] is not None` en todo el front. Si Keras falló, no pinta nada en vez de NaN.

---

## 🎓 Alcance Científico y Limitaciones Éticas

- **Referencia geográfica BR-Sa1**: ~lat -2.5 a -3.17, lon -55.33 a -54.5; ~100.000 ha; bosque tropical húmedo amazónico primario.
- **32 muestras GEDI reales** (huellas L4A AGB) usadas para entrenar AGB_GEDI.
- **NEE negativo = sumidero**: el bosque amazónico maduro absorbe CO₂; un NEE positivo (raro) implica que el ecosistema emite más de lo que captura.
- **FMC 25–80%**: contenido de humedad del combustible fino (hojarasca, ramitas); valores bajos (<35%) son condición de alto fuego.
- **Footers y captions en TODAS las interfaces**: "no usar para decisiones operativas reales" — disclaimer ético claro.
- **Todas las predicciones son ilustrativas**: el prototipo demuestra la cadena tecnológica; los pesos reales del entrenamiento Colab pueden ser v1 iniciales.

---

## 🚀 Cómo Ejecutar Todo el Sistema (3 puertos simultáneos)

```powershell
# Terminal 1 — Backend FastAPI (puerto 8000):
cd modulo_servidor
uvicorn modulo_servidor.api:app --reload --port 8000

# Terminal 2 — Streamlit (puerto ~8501):
streamlit run app.py

# Terminal 3 — Frontend React (puerto 5173):
cd laboratorio_react
npm install
npm run dev

# (Opcional) Terminal 4 — Documentación MkDocs (puerto 8000 o 8080):
mkdocs serve
```

Una vez arriba:
- Visita `http://localhost:8501` → Home Streamlit (artefactos reales o demo)
- Ve a Monitor de Entrenamiento → explora las 9 pestañas
- Ve a Probador Modelos → selecciona AGB_GEDI y ejecuta inferencia
- Visita `http://localhost:5173` → Laboratorio React → ajusta sliders → Ejecutar simulación → explora Mapas 3D → Exporta reporte
