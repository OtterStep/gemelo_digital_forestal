"""Probador de modelos: inferencia con los artefactos reales de Colab.

Si el modelo ya existe se usa tal cual; si no se puede cargar en este entorno
(keras / lightgbm ausentes) degrada con un mensaje claro, sin re-entrenar.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from config import MODELOS_DIR, SOURCE_VERSION

st.set_page_config(page_title="Probador de Modelos", page_icon="🧪", layout="wide")

CATALOGO = {
    "AGB_GEDI":   {"archivo": "AGB_GEDI.joblib",   "escalador": "AGB_GEDI_scaler.joblib",   "requiere": None, "tipo": "RF · biomasa",       "clasificador": False, "lstm": False},
    "MLR_baseline": {"archivo": "MLR_baseline.joblib", "escalador": "MLR_baseline_scaler.joblib", "requiere": None, "tipo": "Regresión lineal · biomasa", "clasificador": False, "lstm": False},
    "LAI_MODEL":  {"archivo": "LAI_MODEL.joblib",  "escalador": "LAI_MODEL_scaler.joblib",  "requiere": None, "tipo": "RF · LAI",           "clasificador": False, "lstm": False},
    "FMC_MODEL":  {"archivo": "FMC_MODEL.joblib",  "escalador": "FMC_MODEL_scaler.joblib",  "requiere": None, "tipo": "RF · FMC",           "clasificador": False, "lstm": False},
    "3PG_RF":     {"archivo": "3PG_RF.joblib",     "escalador": "3PG_RF_scaler.joblib",     "requiere": None, "tipo": "Híbrido 3-PG + RF", "clasificador": False, "lstm": False},
    "INCENDIO":   {"archivo": "INCENDIO.joblib",   "escalador": "INCENDIO_scaler.joblib",   "requiere": None, "tipo": "RF · clasificador",  "clasificador": True,  "lstm": False},
    "3PG_LSTM":   {"archivo": "3PG_LSTM.h5",       "escalador": "3PG_LSTM_scaler.joblib",   "requiere": None, "tipo": "Híbrido 3-PG + LSTM (NEE)", "clasificador": False, "lstm": True},
    "LightGBM":   {"archivo": "LightGBM.joblib",   "escalador": "LightGBM_scaler.joblib",   "requiere": "lightgbm", "tipo": "Baseline boosting", "clasificador": False, "lstm": False},
}

PREVIOS_FALLBACK = {
    "S1_VV": (0.0, 1.0, 0.72), "S1_VH": (0.0, 1.0, 0.72), "NDVI": (0.0, 1.0, 0.72),
    "LAI": (0.0, 8.0, 4.0), "FMC": (10.0, 95.0, 55.0), "TA_ERA": (0.0, 35.0, 26.0),
    "P_ERA": (0.0, 15.0, 5.0), "SW_IN_ERA": (0.0, 400.0, 186.0), "VPD_ERA": (0.0, 12.0, 5.0),
    "NPP_3PG": (0.05, 0.2, 0.11),
}


def _cargar_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _metadata(nombre):
    return _cargar_json(MODELOS_DIR / f"{nombre}_metadata.json") or {}


@st.cache_resource(show_spinner="Cargando artefacto real… (primera vez puede tardar si implica keras/tensorflow)")
def _cargar_modelo(nombre):
    """Carga modelo + scaler reales. Devuelve (modelo, scaler, predictoras, error)."""
    info = CATALOGO[nombre]
    if info["requiere"]:
        return None, None, None, (
            f"`{nombre}` requiere **{info['requiere']}**, que no está instalado en este entorno. "
            f"El artefacto existe pero no se puede cargar aquí; entrénalo/sirvelo desde Colab."
        )
    archivo = MODELOS_DIR / info["archivo"]
    if not archivo.exists():
        return None, None, None, f"No existe `{archivo.name}`. Habría que entrenarlo en Colab; la app no re-entrena."
    try:
        import joblib
        if info.get("lstm"):
            from keras.models import load_model
            modelo = load_model(archivo, compile=False)
        else:
            modelo = joblib.load(archivo)
        scaler = joblib.load(MODELOS_DIR / info["escalador"])
        predictoras = _metadata(nombre).get("predictoras") or [c for c in PREVIOS_FALLBACK]
        return modelo, scaler, predictoras, None
    except ModuleNotFoundError as e:
        return None, None, None, f"Paquete faltante: `{getattr(e, 'name', e)}`. El artefacto existe pero no se puede usar aquí."
    except Exception as e:
        return None, None, None, f"Error al cargar artefactos: {type(e).__name__}: {e}"


def _rangos(scaler, predictoras):
    """Rangos por variable derivados de la escala de entrenamiento (mean ± 3·std)."""
    if scaler is None or not (hasattr(scaler, "mean_") and hasattr(scaler, "scale_")):
        return {}
    mean = np.asarray(scaler.mean_, dtype=float)
    scale = np.asarray(scaler.scale_, dtype=float)
    out = {}
    for i, col in enumerate(predictoras):
        if i < len(mean):
            lo, hi = float(mean[i] - 3 * scale[i]), float(mean[i] + 3 * scale[i])
            if lo > hi:
                lo, hi = hi, lo
            out[col] = (round(lo, 4), round(hi, 4), round(float(mean[i]), 4))
    return out


st.title("🧪 Probador de Modelos")
st.caption("Inferencia con los artefactos reales exportados desde Colab · sin re-entrenamiento")

nombre = st.selectbox("Modelo", list(CATALOGO.keys()))
info = CATALOGO[nombre]
met = _metadata(nombre)

estado_archivo = "✅ artefacto presente" if (MODELOS_DIR / info["archivo"]).exists() else "❌ artefacto ausente"
st.caption(f"`{info['archivo']}` · {estado_archivo} · objetivo: {met.get('objetivo', info['tipo'])}")

r2_meta = (met.get("metricas") or {}).get("r2")
if r2_meta is not None:
    try:
        if float(r2_meta) < 0.3:
            st.warning(
                f"⚠️ Este artefacto quedó **mal ajustado en Colab** (R² ≈ {float(r2_meta):.3f}). "
                "Es el resultado real del entrenamiento v1; sus predicciones pueden no ser fiables."
            )
    except (TypeError, ValueError):
        pass

modelo, scaler, predictoras, error = _cargar_modelo(nombre)

if error:
    st.warning(error)
    st.stop()

rangos = _rangos(scaler, predictoras or [])
st.caption(f"Variables predictoras ({len(predictoras or [])}): `" + "`, `".join(predictoras or []) + "`")
st.caption("Los rangos por defecto derivan de la escala de entrenamiento (mean ± 3·std).")

# ---------------------------------------------------------------- Entrada manual
st.subheader("Entrada manual (escala de entrenamiento del modelo)")
if info.get("lstm"):
    st.caption("El LSTM usa una ventana de **4 pasos temporales**; la fila ingresada se repite 4 veces como ventana.")
cols = st.columns(4)
vals = {}
for i, col in enumerate(predictoras or []):
    lo, hi, val = rangos.get(col, PREVIOS_FALLBACK.get(col, (0.0, 1.0, 0.5)))
    step = max((hi - lo) / 100.0, 1e-4)
    vals[col] = cols[i % 4].number_input(
        col, min_value=float(lo), max_value=float(hi), value=float(val), step=float(step), format="%.4f"
    )

if st.button("▶ Ejecutar inferencia", type="primary"):
    fila = np.array([[vals[c] for c in predictoras]])
    fila_sc = scaler.transform(fila)
    with st.expander("Fila normalizada (Scaler)"):
        st.dataframe(pd.DataFrame(fila_sc, columns=predictoras), width="stretch")
    if info["clasificador"]:
        proba = modelo.predict_proba(fila_sc)[0]
        pred = int(modelo.predict(fila_sc)[0])
        c1, c2 = st.columns(2)
        c1.metric("Clase predicha", "🔥 Incendio" if pred == 1 else "🌿 Sin incendio")
        c2.metric("Probabilidad de incendio", f"{proba[1]:.2%}" if len(proba) > 1 else "—")
    elif info.get("lstm"):
        x_lstm = fila_sc.astype(np.float32).repeat(4, axis=0).reshape(1, 4, len(predictoras))
        pred = float(np.asarray(modelo.predict(x_lstm, verbose=0)).ravel()[0])
        st.metric(f"Predicción NEE · {met.get('objetivo', nombre)}", f"{pred:.3f} g C/m²·día")
        st.caption("Valores bajos/negativos: ecosistema como sumidero de CO₂.")
    else:
        pred = float(modelo.predict(fila_sc)[0])
        st.metric(f"Predicción · {met.get('objetivo', nombre)}", f"{pred:.3f}")

# ---------------------------------------------------------------- Batch CSV
st.divider()
st.subheader("Predicción en lote (CSV)")
up_csv = st.file_uploader("Sube un CSV con las columnas predictoras", type="csv")
if up_csv:
    try:
        df = pd.read_csv(up_csv)
        faltan = [c for c in predictoras if c not in df.columns]
        if faltan:
            st.error(f"Faltan columnas: {faltan}")
        else:
            X = scaler.transform(df[predictoras].astype(float).to_numpy())
            if info["clasificador"]:
                proba = modelo.predict_proba(X)[:, 1]
                df_out = df.copy()
                df_out["prediccion"] = modelo.predict(X)
                df_out["prob_incendio"] = np.round(proba, 4)
            elif info.get("lstm"):
                X_lstm = X.astype(np.float32).repeat(4, axis=1).reshape(len(df), 4, len(predictoras))
                df_out = df.copy()
                df_out["prediccion"] = np.round(np.asarray(modelo.predict(X_lstm, verbose=0)).ravel(), 4)
            else:
                df_out = df.copy()
                df_out["prediccion"] = np.round(modelo.predict(X), 4)
            df_out["fuente_version"] = _cargar_json(MODELOS_DIR / "mejor_modelo.json") or {}
            fuente = (df_out.at[0, "fuente_version"].get("fuente_version") if isinstance(df_out.at[0, "fuente_version"], dict) else SOURCE_VERSION)
            df_out["fuente_version"] = fuente
            st.dataframe(df_out, width="stretch", hide_index=True)
            st.download_button(
                "⬇ Descargar predicciones",
                data=df_out.to_csv(index=False).encode("utf-8"),
                file_name=f"predicciones_{nombre}.csv",
                mime="text/csv",
            )
    except Exception as e:
        st.error(f"Error procesando el CSV: {type(e).__name__}: {e}")
else:
    st.info("Sube una tabla para predecir múltiples filas con el modelo real.")