"""Exporta predicciones_modelos.csv a partir de los artefactos reales y el dataset fusionado local.

Reproduce el y_true/y_pred de entrenamiento (los modelos se reutilizan tal cual, sin re-entrenar):
se reconstruye la misma matriz_finita (dropna de predictoras + objetivo) del Colab y se transforma
con el escalador guardado de cada modelo. Ejecutar:

    python -m modulo_ia.exportar_predicciones

Requisitos: recursos/datos_procesados/dataset_fusionado.parquet (o .csv) descargado de Drive.
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MODELOS_DIR = ROOT / "modelos_entrenados"
DS_PARQUET = ROOT / "recursos" / "datos_procesados" / "dataset_fusionado.parquet"
DS_CSV = ROOT / "recursos" / "datos_procesados" / "dataset_fusionado.csv"
SALIDA = MODELOS_DIR / "predicciones_modelos.csv"

MODELOS_AGB = ["AGB_GEDI", "MLR_baseline", "3PG_RF", "LightGBM"]
MODELOS_EXTRA = ["LAI_MODEL", "FMC_MODEL"]
MODELO_CLF = "INCENDIO"


def cargar_dataset():
    if DS_PARQUET.exists():
        return pd.read_parquet(DS_PARQUET)
    if DS_CSV.exists():
        return pd.read_csv(DS_CSV)
    raise FileNotFoundError(
        "No se encontró el dataset fusionado. Descárgalo de Drive a "
        "recursos/datos_procesados/dataset_fusionado.parquet (o .csv)."
    )


def matriz_finita(df, columnas, objetivo, minimo=10):
    cols = [c for c in columnas + [objetivo] if c in df.columns]
    datos = df[cols].replace([np.inf, -np.inf], np.nan).dropna()
    if len(datos) < minimo:
        raise ValueError(f"Muestras insuficientes para {objetivo} ({len(datos)}).")
    return datos


def predecir_sklearn(nombre, datos, columnas, objetivo):
    """Predice con un modelo sklearn/joblib (RF, MLR, LightGBM)."""
    sc = joblib.load(MODELOS_DIR / f"{nombre}_scaler.joblib")
    X = sc.transform(datos[columnas].values)
    modelo = joblib.load(MODELOS_DIR / f"{nombre}.joblib")
    return np.asarray(modelo.predict(X), dtype=float)


def main():
    ds = cargar_dataset()
    filas = []

    for nombre in MODELOS_AGB + MODELOS_EXTRA:
        meta_file = MODELOS_DIR / f"{nombre}_metadata.json"
        model_file = MODELOS_DIR / f"{nombre}.joblib"
        if not (meta_file.exists() and model_file.exists()):
            print(f"[skip] {nombre}: falta artefacto local")
            continue
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        objetivo, columnas = meta["objetivo"], meta["predictoras"]
        datos = matriz_finita(ds, columnas, objetivo)
        yp = predecir_sklearn(nombre, datos, columnas, objetivo)
        yt = datos[objetivo].values.astype(float)
        for i in range(len(yt)):
            filas.append({"modelo": nombre, "objetivo": objetivo,
                          "idx": int(i), "y_true": float(yt[i]), "y_pred": float(yp[i])})
        print(f"[ok] {nombre}: objetivo={objetivo} ({len(yt)} muestras)")

    if (MODELOS_DIR / f"{MODELO_CLF}.joblib").exists():
        meta = json.loads((MODELOS_DIR / f"{MODELO_CLF}_metadata.json").read_text(encoding="utf-8"))
        objetivo, columnas = meta["objetivo"], meta["predictoras"]
        faltantes = [c for c in columnas if c not in ds.columns]
        if faltantes:
            print(f"[skip] {MODELO_CLF}: faltan características en el dataset {faltantes}")
        else:
            datos = matriz_finita(ds, columnas, objetivo, minimo=5)
            sc = joblib.load(MODELOS_DIR / f"{MODELO_CLF}_scaler.joblib")
            modelo = joblib.load(MODELOS_DIR / f"{MODELO_CLF}.joblib")
            try:
                proba = modelo.predict_proba(sc.transform(datos[columnas].values))
                yp = proba[:, 1]
            except Exception:
                yp = np.asarray(modelo.predict(sc.transform(datos[columnas].values)), dtype=float)
            yt = datos[objetivo].values.astype(float)
            for i in range(len(yt)):
                filas.append({"modelo": MODELO_CLF, "objetivo": objetivo,
                              "idx": int(i), "y_true": float(yt[i]), "y_pred": float(yp[i])})
            print(f"[ok] {MODELO_CLF}: objetivo={objetivo} ({len(yt)} muestras, proba)")
    else:
        print(f"[skip] {MODELO_CLF}: falta artefacto local")

    print("[skip] 3PG_LSTM: objetivo NEE con ventana temporal; no entra en el t-test de AGB.")

    df_out = pd.DataFrame(filas)
    df_out.to_csv(SALIDA, index=False)
    print(f"Guardado: {SALIDA} ({len(df_out)} filas, {df_out['modelo'].nunique()} modelos)")


if __name__ == "__main__":
    main()