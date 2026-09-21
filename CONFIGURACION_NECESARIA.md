# Configuración necesaria del sistema

Este documento describe qué se debe **crear o restaurar** para que el Gemelo Digital Forestal funcione correctamente. Esos elementos **no se ven en git** porque el `.gitignore` los excluye: son secretos, entornos, dependencias, el frontend instalado y los modelos entrenados.

> Lo que sí se versiona: código fuente, documentación, `requirements.txt`, `.env.example` (ambas), JS públicas (`laboratorio_react/public/*.json`) y los datos de ejemplo (`recursos/datos_ejemplo/`).

---

## 1. `.env` (raíz del repositorio)

Copiar `.env.example` y ajustar los valores:

```bash
copy .env.example .env
```

| Variable           | Obligatoria | Descripción |
| ------------------ | ----------- | ----------- |
| `USE_REAL_DATA`    | No          | `False` para demo sintética. |
| `API_URL`          | No          | `http://localhost:8000` (FastAPI). |
| `GEMINI_API_KEY`   | No          | Solo necesaria para `/explicar` (explicación con IA). Si está vacía, esa funcionalidad devuelve error claro. |
| `GEMINI_MODEL`     | No          | `gemini-3.6-flash` por defecto. |

El sistema arranca sin `.env` (usa valores por defecto de `config.py`), pero se recomienda crearlo.

---

## 2. `.env` del frontend (`laboratorio_react/.env`)

```bash
copy .env.example .env
```

| Variable        | Obligatoria | Descripción |
| --------------- | ----------- | ----------- |
| `VITE_API_URL`  | No          | URL de FastAPI (`http://localhost:8000`). Sin esto, el front usa esa URL por defecto y, si el backend no responde, cae al simulador sintético en el navegador. |

---

## 3. Entorno de Python

1. Crear y activar un entorno virtual (el .gitignore excluye `venv312/`):

   ```bash
   py -m venv venv312
   venv312\Scripts\activate
   ```

2. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```

   > **Aviso:** `requirements.txt` **no** incluye `tensorflow`/`keras`. La API los importa de forma perezosa (`modulo_servidor/api.py`) y solo hacen falta si se quiere cargar el modelo `3PG_LSTM.h5`. Sin ellos, la parte NEE degrada sin romper la UI.

---

## 4. Frontend React (`laboratorio_react/`)

`node_modules/` está ignorado; hay que instalarlo:

```bash
cd laboratorio_react
npm install
```

---

## 5. Modelos entrenados (`modelos_entrenados/`)

La carpeta existe en git solo con `.gitkeep`. Los artefactos se regeneran con `entrenamiento_colab.ipynb` o se restauran desde `modelos_entrenados-*.zip`.

| Archivo                        | Generación | Necesario para |
| ------------------------------ | ---------- | -------------- |
| `historial_entrenamiento.json` | Se genera **automáticamente** al abrir el Monitor (`app.py`). | Monitor de Entrenamiento |
| `mejor_modelo.json`            | Colab / carpeta de artefactos | `GET /modelo/mejor`, cabecera del lab |
| `AGB_GEDI.joblib` + `AGB_GEDI_scaler.joblib` | Colab | Inferencia de biomasa |
| `INCENDIO.joblib` + `INCENDIO_scaler.joblib` | Colab | Riesgo de incendio |
| `3PG_LSTM.h5` + `3PG_LSTM_scaler.joblib` | Colab | NEE (requiere keras) |

Si faltan, la API **degrada a modo sintético** por componente (`modulo_servidor/api.py`), de modo que la interfaz nunca se rompe; solo aparecen resultados de demostración con `source_version: synthetic_test`.

---

## 6. Ejecución

```bash
# 1) Streamlit (Monitor + Probador)
streamlit run app.py

# 2) API FastAPI (para el Laboratorio React)
uvicorn modulo_servidor.api:app --reload --port 8000

# 3) Laboratorio React (Vite)
cd laboratorio_react
npm run dev
```

---

## Resumen: qué se crea tras un `git clone`

1. `copy .env.example .env` (raíz) y `laboratorio_react\.env.example -> laboratorio_react\.env`.
2. `py -m venv venv312` + `pip install -r requirements.txt`.
3. `cd laboratorio_react && npm install`.
4. Regenerar o restaurar `modelos_entrenados/*` (opcional: la demo funciona sin ellos).
5. Levantar los tres servicios de la sección 6.