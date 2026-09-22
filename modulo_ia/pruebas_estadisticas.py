"""Pruebas estadísticas para comparación de modelos (metodología idéntica al Colab).

Se ejecutan localmente sobre `modelos_entrenados/predicciones_modelos.csv`, que contiene
y_true/y_pred por muestra y por modelo (reproducidos del entrenamiento sin re-entrenar:

    python -m modulo_ia.exportar_predicciones

Contrastes:
  1) t-test pareado de errores absolutos de cada modelo de AGB vs. el de referencia AGB_GEDI.
  2) Bootstrap IC 95% del R² por remuestreo sobre cada modelo (seed fija).
  3) (Opcional) AUC para la clasificación INCENDIO si sus predicciones están exportadas.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import r2_score, roc_auc_score

from config import MODELOS_DIR

PREDICCIONES_CSV = MODELOS_DIR / "predicciones_modelos.csv"
REFERENCIA = "AGB_GEDI"
OBJETIVO_AGB = "AGBD_gedi"
N_ITER_BOOT = 1000
SEED = 42


def obtener_estado_fase():
    """Devuelve estado serializable de pruebas estadísticas."""
    return {"fase": "Pruebas estadísticas", "estado": "completada", "progreso": 1.0,
            "mensaje": "t-test pareado y bootstrap con IC 95% ejecutados sobre predicciones reales."}


def cargar_predicciones(ruta=None):
    """Lee el CSV de predicciones por muestra. Devuelve DataFrame modelo/objetivo/idx/y_true/y_pred."""
    ruta = Path(ruta) if ruta else PREDICCIONES_CSV
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe {ruta}. Ejecuta primero: python -m modulo_ia.exportar_predicciones"
        )
    return pd.read_csv(ruta)


def bootstrap_ic95(y_true, y_pred, n_iter=N_ITER_BOOT, semilla=SEED):
    """IC 95% del R² por remuestreo bootstrap (replica exacta del Colab)."""
    rng = np.random.default_rng(semilla)
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    n = len(y_true)
    r2_boot = []
    for _ in range(n_iter):
        idx = rng.integers(0, n, n)
        try:
            r2_boot.append(r2_score(y_true[idx], y_pred[idx]))
        except Exception:
            continue
    if not r2_boot:
        return {"ic95_bajo": float("nan"), "ic95_alto": float("nan"), "r2_medio_boot": float("nan")}
    return {
        "ic95_bajo": float(np.percentile(r2_boot, 2.5)),
        "ic95_alto": float(np.percentile(r2_boot, 97.5)),
        "r2_medio_boot": float(np.mean(r2_boot)),
    }


def test_t_pareado_errores(err_ref, err_mod):
    """t-test pareado sobre errores absolutos (err_mod vs. err_ref, delta = err_mod - err_ref).

    delta > 0 implica que el modelo comete más error que la referencia.
    """
    err_ref = np.asarray(err_ref, dtype=float)
    err_mod = np.asarray(err_mod, dtype=float)
    t, p = stats.ttest_rel(err_ref, err_mod)
    d = err_mod - err_ref
    n = len(d)
    se = d.std(ddof=1) / np.sqrt(n)
    t_crit = stats.t.ppf(1 - 0.05 / 2, df=n - 1)
    return {
        "t_stat": float(t),
        "p_valor": float(p),
        "diferencia_media": float(d.mean()),
        "se": float(se),
        "ic95_bajo": float(d.mean() - t_crit * se),
        "ic95_alto": float(d.mean() + t_crit * se),
        "diferencia_significativa": bool(p < 0.05),
        "n": int(n),
    }


def _alinear_por_idx(filas_a, filas_b):
    """Alinea dos DataFrames (modelo A vs referencia) por idx para un contraste pareado."""
    return filas_a[["idx", "y_true", "y_pred"]].merge(
        filas_b[["idx", "y_true", "y_pred"]], on="idx", suffixes=("_mod", "_ref")
    )


def ejecutar_pruebas_en_vivo(ruta=None, n_iter=N_ITER_BOOT, semilla=SEED):
    """Ejecuta las pruebas estadísticas sobre predicciones_modelos.csv.

    Returns:
        dict JSON-safe: resumen por modelo (t-test, bootstrap, R², AUC) + datos para gráficos.
    """
    pred = cargar_predicciones(ruta)
    resultado = {"referencia": REFERENCIA, "n_iter": int(n_iter), "semilla": int(semilla),
                 "modelos": {}, "graficos": {"errores": {}, "dif_errores": {}}, "orden_agb": []}

    agb = pred[pred["objetivo"] == OBJETIVO_AGB]
    ref = agb[agb["modelo"] == REFERENCIA].sort_values("idx")
    if ref.empty:
        raise ValueError(f"No hay predicciones de {REFERENCIA} en el archivo de predicciones.")
    err_ref = np.abs(ref["y_true"].values - ref["y_pred"].values)

    for nombre in sorted(agb["modelo"].unique()):
        filas = agb[agb["modelo"] == nombre].sort_values("idx")
        yt = filas["y_true"].values.astype(float)
        yp = filas["y_pred"].values.astype(float)
        err = np.abs(yt - yp)
        boot = bootstrap_ic95(yt, yp, n_iter=n_iter, semilla=semilla)
        r2 = float(r2_score(yt, yp)) if len(yt) > 1 else float("nan")
        if nombre == REFERENCIA:
            ttest = {
                "t_stat": 0.0, "p_valor": 1.0, "diferencia_media": 0.0, "se": 0.0,
                "ic95_bajo": 0.0, "ic95_alto": 0.0, "diferencia_significativa": False,
                "n": int(len(yt)),
            }
            dif = None
        else:
            pareadas = _alinear_por_idx(filas, ref)
            ttest = test_t_pareado_errores(
                np.abs(pareadas["y_true_ref"].values - pareadas["y_pred_ref"].values),
                np.abs(pareadas["y_true_mod"].values - pareadas["y_pred_mod"].values),
            )
            dif = (np.abs(pareadas["y_true_mod"] - pareadas["y_pred_mod"])
                   - np.abs(pareadas["y_true_ref"] - pareadas["y_pred_ref"])).tolist()
        resultado["modelos"][nombre] = {
            "objetivo": OBJETIVO_AGB,
            "n": int(len(filas)),
            "r2": r2,
            "errores_medios": float(err.mean()),
            **boot,
            "ttest": ttest,
        }
        resultado["graficos"]["errores"][nombre] = err.tolist()
        if dif is not None:
            resultado["graficos"]["dif_errores"][nombre] = dif
        resultado["orden_agb"].append(nombre)

    for nombre in sorted(pred[pred["modelo"] != REFERENCIA]["modelo"].unique()):
        if nombre in resultado["modelos"]:
            continue
        filas = pred[pred["modelo"] == nombre].drop_duplicates("idx").sort_values("idx")
        yt = filas["y_true"].values.astype(float)
        yp = filas["y_pred"].values.astype(float)
        objetivo = str(filas["objetivo"].iloc[0])
        boot = bootstrap_ic95(yt, yp, n_iter=n_iter, semilla=semilla)
        r2 = float(r2_score(yt, yp)) if len(yt) > 1 else float("nan")
        entrada = {"objetivo": objetivo, "n": int(len(filas)), "r2": r2,
                   "errores_medios": float(np.abs(yt - yp).mean()), **boot,
                   "ttest": None}
        if objetivo.lower() == "incendio":
            try:
                entrada["auc"] = float(roc_auc_score(yt, yp))
            except Exception:
                entrada["auc"] = float("nan")
            entrada["bootstrap"] = None
        else:
            entrada["auc"] = float("nan")
        resultado["modelos"][nombre] = entrada
        resultado["graficos"]["errores"][nombre] = np.abs(yt - yp).tolist()

    return resultado