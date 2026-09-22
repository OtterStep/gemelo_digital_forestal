"""Monitor de entrenamiento: una pestaña por fase con descripción, muestra
de datos y resultados. Reutiliza los artefactos reales cuando existen y
degrada a demo sintética si no hay artefactos. Nunca descarga ni re-entrena.
"""
import json
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import ROOT_DIR, MODELOS_DIR, PHASE_NAMES, SOURCE_VERSION
from modulo_ia.demo import generar_historial_demo
from modulo_ia.pruebas_estadisticas import ejecutar_pruebas_en_vivo

st.set_page_config(page_title="Monitor de Entrenamiento", page_icon="📊", layout="wide")

HIST = MODELOS_DIR / "historial_entrenamiento.json"
BEST = MODELOS_DIR / "mejor_modelo.json"
METRICAS = MODELOS_DIR / "resultados_metricas.json"
DATOS_CRUDOS = ROOT_DIR / "recursos" / "datos_crudos"
DATOS_PROC = ROOT_DIR / "recursos" / "datos_procesados"
FLUXDIR = DATOS_CRUDOS / "fluxnet"
EJEMPLO = ROOT_DIR / "recursos" / "datos_ejemplo" / "predicciones_synthetic_test.csv"

FASE_NOMBRES = {
    "descarga_datos": "1 · Descarga de datos",
    "fusion": "2 · Fusión de datos",
    "analisis_exploratorio": "3 · Análisis exploratorio (EDA)",
    "validacion_cruzada": "4 · Validación cruzada (k=5)",
    "ajuste_hiperparametros": "5 · Ajuste de hiperparámetros",
    "entrenamiento_final": "6 · Entrenamiento final",
    "pruebas_estadisticas": "7 · Pruebas estadísticas",
    "seleccion_modelo": "8 · Selección de modelo",
    "exportacion_artefactos": "9 · Exportación de artefactos",
}
ESTADO_ICONO = {"completada": "✅", "en curso": "🟡", "pendiente": "⚪", "error": "🔴"}

CORE_MET = ["TIMESTAMP", "TA_ERA", "SW_IN_ERA", "VPD_ERA", "P_ERA", "WS_ERA",
            "NEE_CUT_REF", "GPP_DT_VUT_REF", "RECO_DT_VUT_REF"]
CORE_ERA = ["TIMESTAMP", "TA_ERA", "SW_IN_ERA", "VPD_ERA", "P_ERA", "WS_ERA"]
CORE_EDA = ["TA_ERA", "SW_IN_ERA", "VPD_ERA", "P_ERA", "NEE_CUT_REF", "GPP_DT_VUT_REF", "RECO_DT_VUT_REF"]

FLUXMET_MM = next((p for p in FLUXDIR.glob("AMF_*FLUXMET_MM_*.csv") if p.is_file()), None) if FLUXDIR.exists() else None
ERA5_MM = next((p for p in FLUXDIR.glob("AMF_*ERA5_MM_*.csv") if p.is_file()), None) if FLUXDIR.exists() else None


def _cargar_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _fmt_ts(ts):
    if not ts:
        return "—"
    if isinstance(ts, str):
        return ts.replace("T", " ")[:19]
    return str(ts)


def _fmt_duracion(s):
    if s is None:
        return "—"
    s = float(s)
    if s >= 60:
        return f"{s / 60:.1f} min"
    return f"{s:.1f} s"


def _normalizar_fases(data):
    if not data:
        return []
    fases = data.get("fases") or data.get("phases") or []
    out = []
    for f in fases:
        nombre = f.get("fase") or f.get("phase") or "?"
        mensajes = f.get("mensajes")
        if mensajes is None:
            log = f.get("log", "")
            mensajes = [log] if isinstance(log, str) and log else []
        out.append({
            "nombre": nombre,
            "nombre_ui": FASE_NOMBRES.get(nombre, nombre),
            "estado": (f.get("estado") or f.get("status") or "pendiente"),
            "inicio": f.get("timestamp_inicio") or f.get("timestamp"),
            "fin": f.get("timestamp_fin"),
            "duracion_s": f.get("duracion_s") or f.get("duration_s"),
            "mensajes": mensajes or [],
            "metricas": f.get("metricas") or f.get("metrics") or {},
        })
    return out


def _extraer_modelos(data):
    modelos = {}
    if not data:
        return modelos
    models_raw = data.get("models")
    if not models_raw:
        etapa = next((f for f in (data.get("fases") or []) if f.get("fase") == "entrenamiento_final"), None)
        models_raw = (etapa or {}).get("metricas", {}) if etapa else {}
    for nombre, m in models_raw.items():
        met = _cargar_json(MODELOS_DIR / f"{nombre}_metadata.json") or {}
        row = dict(met.get("metricas", {}))
        if isinstance(m, dict):
            for k, v in m.items():
                row.setdefault(k, v)
        row["objetivo"] = met.get("objetivo", "")
        row["tipo"] = met.get("tipo", "").replace("_", " ").capitalize()
        modelos[nombre] = row
    return modelos


def _es_demo(data):
    return bool(data and data.get("demo", False))


@st.cache_data(show_spinner=False)
def cargar_historial(mtime=None):
    data = _cargar_json(HIST)
    if data is not None:
        return data
    return generar_historial_demo(HIST)


@st.cache_data(show_spinner=False)
def _leer_fluxmet_mm(mtime):
    if FLUXMET_MM is None:
        return None
    try:
        return pd.read_csv(FLUXMET_MM, usecols=[c for c in CORE_MET if c in pd.read_csv(FLUXMET_MM, nrows=0).columns], na_values=-9999)
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def _leer_era5_mm(mtime):
    if ERA5_MM is None:
        return None
    try:
        return pd.read_csv(ERA5_MM, usecols=[c for c in CORE_ERA if c in pd.read_csv(ERA5_MM, nrows=0).columns], na_values=-9999)
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def _fusion_muestra(mtime_met, mtime_era, n=8):
    m = _leer_fluxmet_mm(mtime_met)
    e = _leer_era5_mm(mtime_era)
    if m is None or e is None or m.empty or e.empty:
        return None
    m2 = m.rename(columns={c: c + "_flux" for c in m.columns if c != "TIMESTAMP"})
    e2 = e.rename(columns={c: c + "_era" for c in e.columns if c != "TIMESTAMP"})
    df = m2.merge(e2, on="TIMESTAMP", how="outer")
    df["TIMESTAMP"] = df["TIMESTAMP"].astype(str)
    return df.dropna(how="all").head(n)


@st.cache_data(show_spinner=False)
def _eda_estadisticas(mtime_met):
    m = _leer_fluxmet_mm(mtime_met)
    if m is None or m.empty:
        return None, None
    cols = [c for c in CORE_EDA if c in m.columns]
    return m[cols].describe().T, m[cols].corr()


@st.cache_data(show_spinner=False)
def _muestra_ejemplo(mtime):
    if not EJEMPLO.exists():
        return None
    try:
        return pd.read_csv(EJEMPLO)
    except Exception:
        return None


@st.cache_data(show_spinner="Ejecutando las pruebas estadísticas con los modelos reales…")
def _ejecutar_pruebas(mtime_csv, n_iter=1000, seed=42):
    return ejecutar_pruebas_en_vivo(n_iter=n_iter, semilla=seed)


def _es_graficable(m):
    """Excluye de los gráficos modelos mal ajustados (predicciones fuera de rango físico) y clasificadores."""
    if m["objetivo"].lower() == "incendio":
        return False
    return m.get("r2") is not None and abs(m["r2"]) <= 1.5


def _render_pruebas(res):
    filas_res = []
    for n, m in res["modelos"].items():
        t = m.get("ttest")
        es_inc = m["objetivo"].lower() == "incendio"
        if es_inc:
            ic, tcol, pcol, dif, sign = "—", "—", "—", "—", "—"
        else:
            ic = f"[{m['ic95_bajo']:.2f}, {m['ic95_alto']:.2f}]" if m.get("ic95_bajo", float("nan")) == m.get("ic95_bajo", float("nan")) else "—"
            tcol = f"{t['t_stat']:.3f}" if t else "—"
            pcol = f"{t['p_valor']:.4f}" if t else "—"
            dif = f"{t['diferencia_media']:.3f}" if t else "—"
            sign = "✅ Sí" if (t and t["diferencia_significativa"]) else "❌ No"
        filas_res.append({
            "Modelo": n, "Objetivo": m["objetivo"], "n": m["n"],
            "R² medio (bootstrap)": m["r2_medio_boot"], "IC 95% R²": ic,
            "t (errores vs ref.)": tcol, "p-valor": pcol,
            "Dif. media errores": dif, "Significativa (α=0.05)": sign, "AUC": "—" if es_inc else m.get("auc"),
        })
    st.markdown("#### Resumen de resultados")
    st.dataframe(pd.DataFrame(filas_res), width="stretch", hide_index=True)
    st.caption(
        f"Referencia: **{res['referencia']}**. El t-test pareado compara los errores absolutos "
        "(|y_true − y_pred|) de cada modelo de AGB vs. los de la referencia (delta > 0 ⇒ el modelo "
        f"comete más error). Bootstrap: {res['n_iter']} remuestreos, semilla {res['semilla']}, IC 95% del R². "
        "Modelos marcados con R² fuera de rango (mal ajustados) se muestran en la tabla pero se excluyen de los gráficos."
    )

    grafs = {n: m for n, m in res["modelos"].items() if _es_graficable(m)}
    if not grafs:
        return

    st.divider()
    c_i1, c_g1 = st.columns([2, 3])
    with c_i1:
        st.markdown("##### 1 · Bootstrap IC95 del R² por modelo")
        st.caption("El R² es comparable entre objetivos (adimensional).")
        mejor = max(grafs, key=lambda k: grafs[k]["r2_medio_boot"])
        st.metric("Mejor R² medio (bootstrap)", f"{grafs[mejor]['r2_medio_boot']:.3f}", delta=mejor)
        st.metric("IC más estrecho (estable)", f"±{min((grafs[k]['ic95_alto'] - grafs[k]['ic95_bajo']) / 2 for k in grafs):.3f}")
    with c_g1:
        df1 = pd.DataFrame([
            {"Modelo": n, "R² medio": m["r2_medio_boot"], "IC bajo": m["ic95_bajo"], "IC alto": m["ic95_alto"],
             "Rol": "Referencia" if n == res["referencia"] else "Modelo"}
            for n, m in grafs.items()
        ]).sort_values("R² medio", ascending=False)
        fig1 = go.Figure(go.Bar(
            x=df1["Modelo"], y=df1["R² medio"],
            error_y=dict(type="data", visible=True,
                         array=(df1["IC alto"] - df1["R² medio"]).clip(lower=0).tolist(),
                         arrayminus=(df1["R² medio"] - df1["IC bajo"]).clip(lower=0).tolist()),
            marker_color=["#2e86ab" if r == "Referencia" else "#8e9eab" for r in df1["Rol"]],
        ))
        fig1.update_layout(title="R² medio por remuestreo bootstrap ± IC 95%",
                           yaxis_title="R²", xaxis_title="Modelo", showlegend=False)
        st.plotly_chart(fig1)
    st.markdown(
        "**Explicación:** para cada modelo se remuestrea con reposición las y_true/y_pred y se recalcula el R² "
        "en cada remuestreo; las barras muestran la media y el intervalo que captura el 95% de las veces el valor. "
        "El intervalo traduce la estabilidad del modelo: uno ancho indica que su R² depende mucho de qué muestras "
        "queden en cada remuestreo."
    )

    st.divider()
    agb_graf = {n: m for n, m in grafs.items() if m["objetivo"] == "AGBD_gedi"}
    c_i2, c_g2 = st.columns([2, 3])
    with c_i2:
        st.markdown("##### 2 · Errores absolutos por modelo (AGB, t·ha⁻¹)")
        st.caption("Misma unidad de objetivo (biomasa) ⇒ comparables entre modelos.")
        medios = {n: m["errores_medios"] for n, m in agb_graf.items()}
        st.metric("Error medio (referencia)", f"{medios.get(res['referencia'], float('nan')):.2f}")
        if len(medios) > 1:
            peor = min(medios, key=lambda k: -medios[k])
            st.metric("Peor error medio", f"{medios[peor]:.2f}", delta=peor)
    with c_g2:
        e_rows = [{"Modelo": n, "Error absoluto (t·ha⁻¹)": v} for n in agb_graf for v in res["graficos"]["errores"][n]]
        fig2 = px.violin(pd.DataFrame(e_rows), x="Modelo", y="Error absoluto (t·ha⁻¹)",
                         box=True, points="all", color="Modelo",
                         title="Distribución de errores absolutos por modelo (pareado)",
                         color_discrete_sequence=["#2e86ab", "#b0413e", "#8e8d55", "#6a4c93"])
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2)
    st.markdown(
        "**Explicación:** cada violín muestra la distribución del error absoluto de cada modelo sobre las 32 "
        "muestras GEDI reales. El t-test pareado (prueba 1 del resumen) compara estas distribuciones fila a fila, "
        "con la misma muestra en ambos modelos, en lugar de comparar promedios globales."
    )

    st.divider()
    no_ref = [n for n in agb_graf if n != res["referencia"]]
    if no_ref:
        c_i3, c_g3 = st.columns([2, 3])
        with c_i3:
            st.markdown("##### 3 · Diferencia de errores (modelo − referencia)")
            st.caption("Delta > 0 ⇒ el modelo comete más error que AGB_GEDI en esa muestra.")
            min_p = min((agb_graf.get(n, {}).get("ttest", {}) or {}).get("p_valor", 1.0) for n in no_ref)
            st.metric("p-valor mínimo (t-test)", f"{min_p:.4f}")
            if min_p < 0.05:
                st.success("Al menos un modelo difiere significativamente de la referencia (p < 0.05).")
            else:
                st.warning("Ningún modelo difiere significativamente de la referencia.")
        with c_g3:
            d_rows = [{"Modelo": n, "Δ error vs referencia": v}
                      for n in no_ref
                      for v in res["graficos"]["dif_errores"][n]]
        fig3 = px.histogram(pd.DataFrame(d_rows), x="Δ error vs referencia", nbins=32,
                            facet_col="Modelo", facet_col_wrap=2, facet_row_spacing=0.15,
                            title="Histograma de la diferencia pareada de errores vs. AGB_GEDI")
        fig3.add_vline(x=0, line_dash="dot", line_color="black")
        fig3.update_layout(showlegend=False)
        fig3.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1].strip()))
        st.plotly_chart(fig3)
    st.markdown(
        "**Explicación:** por cada muestra se resta el error de la referencia al error del modelo. La distribución "
        "centrada en 0 indica empate; desplazada a la derecha (valores positivos) que el modelo se equivoca más. "
        "El p-valor del t-test pareado decide si ese desplazamiento es estadísticamente significativo (α=0.05)."
    )


mtime_met = FLUXMET_MM.stat().st_mtime if FLUXMET_MM else 0
mtime_era = ERA5_MM.stat().st_mtime if ERA5_MM else 0
mtime_ej = EJEMPLO.stat().st_mtime if EJEMPLO.exists() else 0

hist = st.session_state.get("historial") or cargar_historial(HIST.stat().st_mtime if HIST.exists() else None)
fases = _normalizar_fases(hist)
fases_por_id = {f["nombre"]: f for f in fases}
modelos = _extraer_modelos(hist)
es_demo = _es_demo(hist)
fuente = hist.get("fuente_version") or hist.get("source_version") or SOURCE_VERSION
completadas = sum(1 for f in fases if f["estado"] == "completada")
total = max(len(fases), 1)
progreso = completadas / total
met = _cargar_json(METRICAS) or {}

st.title("📊 Monitor de Entrenamiento")
if es_demo:
    st.caption(f"Historial **demo sintético** · fuente `{fuente}` · sin artefactos reales")
else:
    st.caption(f"Artefactos **reales de Colab** · fuente `{fuente}` · datos y modelos reutilizados (sin re-descarga)")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Progreso del pipeline", f"{progreso:.0%}")
c2.metric("Fases", f"{completadas}/{len(fases)}")
c3.metric("Modelos", len(modelos))
c4.metric("Fuente", fuente)
st.progress(progreso)

st.subheader("0 · Datos locales (idempotente)")
cd1, cd2, cd3 = st.columns(3)
hay_datos = (DATOS_CRUDOS.exists() and any(DATOS_CRUDOS.rglob("*"))) or (DATOS_PROC.exists() and any(DATOS_PROC.rglob("*")))
cd1.metric("Datos descargados", "Sí" if hay_datos else "No", delta="Reutilizados · sin descarga")
cd2.metric("Crudos (FLUXNET/GEE)", "Sí" if DATOS_CRUDOS.exists() else "No")
cd3.metric("Procesados (fusionado)", "Sí" if (DATOS_PROC.exists() and any(DATOS_PROC.rglob("*"))) else "No")
with st.expander("¿Cómo se gestiona la descarga de datos?"):
    st.markdown(
        "La descarga de datos ocurre **solo en Colab** (`entrenamiento_colab.ipynb`) contra Drive. "
        "Esta app **nunca descarga**: si los datos ya existen en `recursos/datos_crudos` o "
        "`recursos/datos_procesados`, se usan directamente; si no, se indica que faltan sin intentar bajarlos."
    )


def _cabecera_fase(fid):
    f = fases_por_id.get(fid)
    if not f:
        st.caption(f"Fase `{fid}` sin registro en este historial.")
        return
    est = f["estado"]
    st.markdown(f"### {ESTADO_ICONO.get(est, '⚪')} {f['nombre_ui']} — *{est}*")
    st.caption(f"🕐 {_fmt_ts(f['inicio'])} → {_fmt_ts(f['fin'])} · ⏱ {_fmt_duracion(f['duracion_s'])}")
    if f["mensajes"]:
        with st.expander("Ver log"):
            st.code("\n".join(f["mensajes"]))


def _metricas_etapa(fid):
    f = fases_por_id.get(fid)
    if f and f["metricas"]:
        st.markdown("**Métricas registradas:**")
        st.json(f["metricas"], expanded=False)


def _muestra_df(df, titulo):
    if df is None or df.empty:
        st.info("Sin datos locales disponibles para mostrar una muestra.")
        return
    st.markdown(f"**{titulo}**")
    st.dataframe(df.head(8), width="stretch", hide_index=True)


t1, t2, t3, t4, t5, t6, t7, t8, t9 = st.tabs([
    "1 · Descarga", "2 · Fusión", "3 · EDA", "4 · CV k=5", "5 · Hiperparámetros",
    "6 · Entrenamiento", "7 · Estadística", "8 · Selección", "9 · Artefactos",
])

# =================================================================== 1 · Descarga
with t1:
    _cabecera_fase("descarga_datos")
    st.markdown(
        "**Mapeo:** se descargan los insumos del gemelo digital: huellas **GEDI L4A** (biomasa AGB), "
        "series **Sentinel-1/2** y **Landsat** (índices y humedad), **MODIS** (fuego MCD64A1 y vegetación "
        "MOD13Q1) y **FLUXNET BR-Sa1 + ERA5** (meteorología y flujos de carbono). El resultado se baja a "
        "Drive; en esta máquina los datos crudos ya descargados viven en `recursos/datos_crudos`."
    )
    st.markdown("#### Muestra de datos (crudos locales)")
    archivos = []
    if FLUXDIR.exists():
        for p in FLUXDIR.iterdir():
            if p.is_file():
                archivos.append({"Archivo": p.name, "Tamaño (KB)": round(p.stat().st_size / 1024, 1)})
    if archivos:
        st.dataframe(pd.DataFrame(archivos), width="stretch", hide_index=True)
    with st.expander("Preview FLUXMET mensual (FLUXMET_MM)"):
        _muestra_df(_leer_fluxmet_mm(mtime_met), "Primeras filas (columnas núcleo)")
    with st.expander("Preview ERA5 mensual (ERA5_MM)"):
        _muestra_df(_leer_era5_mm(mtime_era), "Primeras filas (columnas núcleo)")
    st.markdown("#### Resultados")
    _metricas_etapa("descarga_datos")

# =================================================================== 2 · Fusión
with t2:
    _cabecera_fase("fusion")
    st.markdown(
        "**Mapeo:** se fusionan las series satelitales con FLUXNET/ERA5 en una ventana mensual por píxel/date, "
        "se alinean columnas, se rellenan huecos (p. ej. meses sin imagen MODIS → fracción quemada 0) y se genera "
        "el dataset de entrenamiento. Este paso ocurre en Colab; el dataset oficial (`dataset_fusionado.csv`, "
        "264×25) está en Drive y **no se descarga aquí**."
    )
    st.markdown("#### Muestra de datos (preview calculada en vivo con FLUXMET × ERA5)")
    _muestra_df(_fusion_muestra(mtime_met, mtime_era), "Join FLUXMET × ERA5 por TIMESTAMP (cabecera)")
    st.markdown("#### Resultados")
    _metricas_etapa("fusion")

# =================================================================== 3 · EDA
with t3:
    _cabecera_fase("analisis_exploratorio")
    st.markdown(
        "**Mapeo:** análisis exploratorio de la biomasa (AGB GEDI) y sus predictores: distribución, valores "
        "atípicos y correlaciones entre variables. Las 32 muestras GEDI válidas y la matriz de correlación de "
        "entrenamiento se generan en Colab."
    )
    st.markdown("#### Muestra de datos (estadística de columnas climáticas/flujo locales)")
    eda_desc, eda_corr = _eda_estadisticas(mtime_met)
    if eda_desc is not None:
        st.dataframe(eda_desc, width="stretch")
    st.markdown("#### Resultados")
    if eda_corr is not None:
        st.plotly_chart(px.imshow(eda_corr, text_auto=True, title="Matriz de correlación (datos locales)"))
    _metricas_etapa("analisis_exploratorio")

# =================================================================== 4 · CV k=5
with t4:
    _cabecera_fase("validacion_cruzada")
    st.markdown(
        "**Mapeo:** validación cruzada con **k=5** sobre cada modelo: se estima el error real de generalización "
        "(R², RMSE, MAE) con la desviación entre folds. Los valores por fold se exportan desde Colab."
    )
    st.markdown("#### Muestra de datos (resultados agregados de los folds)")
    cv = met.get("cv_resultados")
    if cv:
        cv_rows = [{"Modelo": n, "R² medio": m.get("r2_medio"), "RMSE medio": m.get("rmse_medio"),
                    "MAE medio": m.get("mae_medio"), "R² std": m.get("r2_std"), "RMSE std": m.get("rmse_std")}
                   for n, m in cv.items()]
        st.dataframe(pd.DataFrame(cv_rows), width="stretch", hide_index=True)
        fig_cv = px.bar(
            pd.DataFrame(cv_rows).dropna(subset=["R² medio"]), x="Modelo", y="R² medio",
            error_y="R² std", title="R² medio por modelo (CV k=5) ± desviación",
        )
        st.plotly_chart(fig_cv)
        st.caption("Nota: INCENDIO es clasificación; su 'R²' guardado corresponde al ROC-AUC.")
    else:
        st.info("Sin resultados de CV en este historial.")
    st.markdown("#### Resultados")
    _metricas_etapa("validacion_cruzada")

# =================================================================== 5 · Hiperparámetros
with t5:
    _cabecera_fase("ajuste_hiperparametros")
    st.markdown(
        "**Mapeo:** búsqueda de hiperparámetros con **GridSearchCV**. Para Random Forest se optimizó número de "
        "árboles (`n_estimators`), profundidad (`max_depth`) y mínimo de muestras para dividir (`min_samples_split`); "
        "para LightGBM, `n_estimators`, `max_depth` y `learning_rate`."
    )
    hp = (fases_por_id.get("ajuste_hiperparametros") or {}).get("metricas") or {}
    if "RandomForest" in hp:
        st.markdown("#### Muestra de datos (mejores combinaciones)")
        st.dataframe(pd.DataFrame(hp).T, width="stretch")
        st.markdown("| Hiperparámetro | Significado |")
        st.markdown("| --- | --- |")
        st.markdown("| `n_estimators` | nº de árboles / rondas de boosting |")
        st.markdown("| `max_depth` | profundidad máxima de cada árbol (controla el sobreajuste) |")
        st.markdown("| `min_samples_split` | muestras mínimas para dividir un nodo |")
        st.markdown("| `learning_rate` | tasa de aprendizaje del gradiente (LightGBM) |")
    else:
        st.info("Sin hiperparámetros registrados en este historial.")
    st.markdown("#### Resultados")
    _metricas_etapa("ajuste_hiperparametros")

# =================================================================== 6 · Entrenamiento
with t6:
    _cabecera_fase("entrenamiento_final")
    st.markdown(
        "**Mapeo:** se entrenan los modelos finales con todos los folds: biomasa (**AGB_GEDI**, **MLR_baseline**, "
        "**3PG_RF**, LightGBM), variables de vegetación (**LAI_MODEL**, **FMC_MODEL**), flujo neto **NEE** "
        "(**3PG_LSTM**) y clasificación de **incendio** (**INCENDIO**)."
    )
    st.markdown("#### Muestra de datos (filas de entrada de ejemplo)")
    _muestra_df(_muestra_ejemplo(mtime_ej), "Ejemplo de entrada (recursos/datos_ejemplo)")
    cols_pred = _cargar_json(MODELOS_DIR / "columnas_predictoras.json")
    if cols_pred:
        st.markdown("**Columnas predictoras:** `" + "`, `".join(cols_pred) + "`")
    st.markdown("#### Resultados")
    if modelos:
        rows = []
        for nombre, m in modelos.items():
            fila = {"Modelo": nombre, "Objetivo": m.get("objetivo", ""), "Tipo": m.get("tipo", "")}
            for k in ["r2", "rmse", "mae", "accuracy", "roc_auc"]:
                v = m.get(k)
                fila[k] = None if v is None or v != v else v
            rows.append(fila)
        df_mod = pd.DataFrame(rows)
        st.dataframe(df_mod, width="stretch", hide_index=True)
        if not es_demo:
            disponible = [n for n in df_mod["Modelo"] if (MODELOS_DIR / f"{n}.joblib").exists() or (MODELOS_DIR / f"{n}.h5").exists()]
            faltantes = [n for n in df_mod["Modelo"] if n not in disponible]
            if faltantes:
                st.warning(f"Modelos sin artefacto local (habría que entrenar en Colab): {', '.join(faltantes)}")
            else:
                st.success("Todos los modelos tienen artefacto exportado y se reutilizan tal cual (sin re-entreno).")
        chart = df_mod[df_mod["r2"].notna()].copy()
        if not chart.empty:
            fig = px.bar(chart, x="Modelo", y="r2", text="r2", title="R² final por modelo")
            fig.update_yaxes(range=[0, 1])
            st.plotly_chart(fig)
    else:
        st.info("No hay métricas de modelos en el historial.")

# =================================================================== 7 · Estadística
with t7:
    _cabecera_fase("pruebas_estadisticas")
    st.markdown(
        "**Mapeo:** para decidir si el mejor modelo es significativamente superior se aplican **t-test pareado** y "
        "**bootstrap** sobre las métricas de CV, reportando p-valor e intervalo de confianza al 95% del R²."
    )
    est = met.get("pruebas_estadisticas")
    if est:
        st.markdown("#### Muestra de datos (resultados del contraste)")
        rows_est = [{
            "Modelo": n,
            "t-stat": m.get("t_stat"),
            "p-valor": m.get("p_valor"),
            "Significativa": "✅ Sí" if m.get("diferencia_significativa") else "❌ No",
            "IC95 bajo": m.get("ic95_bajo"),
            "IC95 alto": m.get("ic95_alto"),
            "R² medio (boot)": m.get("r2_medio_boot"),
        } for n, m in est.items()]
        st.dataframe(pd.DataFrame(rows_est), width="stretch", hide_index=True)
        st.caption("Prueba comparativa vs. mejor modelo. INCENDIO es clasificación (IC95 en NaN).")
    else:
        st.info("Sin resultados de pruebas estadísticas en este historial.")
    st.markdown("#### Resultados")
    _metricas_etapa("pruebas_estadisticas")

    st.markdown("#### Pruebas estadísticas ejecutadas localmente (modelos reales)")
    PRED_CSV = MODELOS_DIR / "predicciones_modelos.csv"
    if es_demo or not PRED_CSV.exists():
        st.info(
            "No hay `modelos_entrenados/predicciones_modelos.csv`.\n\n"
            "Ejecuta una vez  `python -m modulo_ia.exportar_predicciones`  para regenerar las predicciones "
            "de entrenamiento (reutiliza los modelos reales y el dataset fusionado de "
            "`recursos/datos_procesados/`) y vuelve a cargar esta página."
        )
    else:
        if st.button("Ejecutar pruebas estadísticas", icon=":material/play_arrow:"):
            _ejecutar_pruebas.clear(PRED_CSV.stat().st_mtime)
        try:
            res = _ejecutar_pruebas(PRED_CSV.stat().st_mtime)
        except Exception as exc:
            st.error(f"No se pudieron ejecutar las pruebas: {exc}")
        else:
            _render_pruebas(res)

# =============================================================== 8 · Selección
with t8:
    _cabecera_fase("seleccion_modelo")
    st.markdown(
        "**Mapeo:** se elige el mejor modelo equilibrando métrica (R²/RMSE), estabilidad en CV y parsimonia. "
        "En esta versión el seleccionado es el **híbrido fisiológico 3-PG + LSTM** para NEE."
    )
    best = st.session_state.get("best") or _cargar_json(BEST)
    if best:
        st.markdown("#### Muestra de datos (mejor modelo)")
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Mejor modelo", best.get("mejor_modelo", "—"))
        b2.metric("Tipo", best.get("tipo", "—").replace("_", " "))
        b3.metric("Objetivo", best.get("objetivo", "—"))
        b4.metric("Fecha", (best.get("fecha_seleccion", "—") or "—").replace("T", " ")[:16])
        if best.get("metricas"):
            st.markdown("**Métricas finales:**")
            st.json(best.get("metricas"), expanded=True)
        if best.get("validacion_cruzada"):
            st.markdown("**Validación cruzada:**")
            st.json(best.get("validacion_cruzada"), expanded=True)
        varsb = best.get("variables_predictoras", [])
        if varsb:
            st.markdown("**Variables predictoras:** `" + "`, `".join(varsb) + "`")
    else:
        st.info("Sin `mejor_modelo.json` disponible.")
    st.markdown("#### Resultados")
    _metricas_etapa("seleccion_modelo")

# =================================================================== 9 · Artefactos
with t9:
    _cabecera_fase("exportacion_artefactos")
    st.markdown(
        "**Mapeo:** se exportan los artefactos finales desde Colab a Drive (`.joblib`/`.h5`, scalers y metadatos) "
        "para que Streamlit/FastAPI los reutilicen sin re-entrenar."
    )
    archivos = []
    for p in sorted(MODELOS_DIR.glob("*")):
        if p.is_file() and p.suffix in (".joblib", ".h5") and "scaler" not in p.name:
            met_f = _cargar_json(MODELOS_DIR / f"{p.stem}_metadata.json") or {}
            obj = met_f.get("objetivo", "")
            r2 = None
            for k in ("r2", "roc_auc", "accuracy"):
                v = met_f.get("metricas", {}).get(k)
                if v is not None:
                    r2 = v
                    break
            archivos.append({"Artefacto": p.name, "Objetivo": obj, "Métrica clave": r2,
                             "Tamaño (KB)": round(p.stat().st_size / 1024, 1)})
    if archivos:
        st.markdown("#### Muestra de datos (artefactos exportados)")
        st.dataframe(pd.DataFrame(archivos), width="stretch", hide_index=True)
    else:
        st.info("No hay artefactos exportados todavía.")
    st.markdown("#### Resultados")
    _metricas_etapa("exportacion_artefactos")
    st.subheader("Exportar historial")
    st.download_button(
        "⬇ Descargar historial JSON",
        data=json.dumps(hist, ensure_ascii=False, indent=2),
        file_name="historial_entrenamiento.json",
        mime="application/json",
        width="stretch",
    )

# =================================================================== Sidebar
with st.sidebar:
    st.header("Artefactos")
    st.write("Los artefactos ya presentes se reutilizan automáticamente.")
    up_hist = st.file_uploader("historial_entrenamiento.json", type="json")
    up_best = st.file_uploader("mejor_modelo.json", type="json")
    up_model = st.file_uploader("Modelo entrenado (.pkl/.joblib/.h5)", type=["pkl", "joblib", "h5"])
    if up_hist:
        try:
            st.session_state["historial"] = json.loads(up_hist.getvalue().decode("utf-8"))
            st.success("Historial cargado en la sesión")
        except Exception as e:
            st.error(f"JSON inválido: {e}")
    if up_best:
        try:
            st.session_state["best"] = json.loads(up_best.getvalue().decode("utf-8"))
            st.success("Mejor modelo cargado")
        except Exception as e:
            st.error(f"JSON inválido: {e}")
    if up_model:
        st.info(f"Modelo listo para integración: {up_model.name}")

    st.divider()
    st.markdown("**Datos locales**")
    if hay_datos:
        st.success("Datos ya descargados → se reutilizan (0 descargas).")
    else:
        st.info("No hay datos locales. La app no descarga; solo entrena/lee desde Drive/Colab.")

    if es_demo:
        if st.button("Regenerar demo", width="stretch"):
            generar_historial_demo(HIST)
            st.cache_data.clear()
            st.rerun()
    else:
        st.warning("Hay artefactos **reales**. Regenerar demo sobrescribiría el historial real.")
        confirmar = st.checkbox("Sobrescribir artefactos reales con demo", key="confirmar_demo")
        if st.button("Regenerar demo", width="stretch", disabled=not confirmar):
            generar_historial_demo(HIST)
            st.cache_data.clear()
            st.rerun()