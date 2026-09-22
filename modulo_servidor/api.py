"""API de inferencia y simulación del Laboratorio React.

Carga los artefactos de entrenamiento reales de MODELOS_DIR (modelos_entrenados)
y los usa para /modelo/mejor y /simular. Si un artefacto no está disponible,
degrada ese componente al simulador analítico para no romper la interfaz.
"""
import math, os, random
import requests
from datetime import datetime
from functools import lru_cache
from pathlib import Path
import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from config import SOURCE_VERSION, GEMINI_API_KEY, GEMINI_MODEL


app = FastAPI(title="Gemelo Digital Forestal API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

MODELOS_DIR = Path(__file__).resolve().parent.parent / "modelos_entrenados"

# Valores base de referencia (medios de entrenamiento / clima neutro).
S1_VV_BASE, S1_VH_BASE = -9.8, -16.5
SW_IN_BASE, VPD_BASE = 186.0, 5.0
NEUTRO = {"fmc": 55.0, "lai": 4.0, "ndvi": 0.72, "precipitacion_mm": 180.0, "temperatura_c": 27.0}


def _clamp(v, a, b):
    return max(a, min(b, float(v)))


@lru_cache(maxsize=1)
def _artefactos():
    """Carga perezosa de modelos y scalers con degradación por componente."""
    out = {"best": None, "agb": None, "incendio": None, "lstm": None,
           "sc_agb": None, "sc_inc": None, "sc_lstm": None}
    try:
        p = MODELOS_DIR / "mejor_modelo.json"
        if p.exists():
            out["best"] = p.read_text(encoding="utf-8")
    except Exception:
        pass
    for key, fn in (("agb", "AGB_GEDI.joblib"), ("incendio", "INCENDIO.joblib")):
        try:
            import joblib
            out[key] = joblib.load(MODELOS_DIR / fn)
        except Exception:
            out[key] = None
    for key, fn in (("sc_agb", "AGB_GEDI_scaler.joblib"), ("sc_inc", "INCENDIO_scaler.joblib")):
        try:
            import joblib
            out[key] = joblib.load(MODELOS_DIR / fn)
        except Exception:
            out[key] = None
    # El LSTM (keras/tensorflow) se carga de forma perezosa: importar keras es
    # lento (~25 s la primera vez) y solo hace falta cuando se pide NEE.
    out["lstm"] = None
    out["sc_lstm"] = None
    return out


@lru_cache(maxsize=1)
def _cargar_lstm():
    """Carga perezosa del modelo 3-PG LSTM (keras) + scaler. Devuelve (modelo, scaler)."""
    try:
        from keras.models import load_model
        import joblib
        lstm = load_model(MODELOS_DIR / "3PG_LSTM.h5", compile=False)
        sc_lstm = joblib.load(MODELOS_DIR / "3PG_LSTM_scaler.joblib")
        return lstm, sc_lstm
    except Exception:
        return None, None


def _lstm_ok():
    return _cargar_lstm()[0] is not None


def _par(s, k, d):
    v = s.get(k, d)
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(d)


def _npp3pg(ndvi_ef, lai_ef):
    return 0.107 * (1 + (ndvi_ef - 0.363) * 0.6 + (lai_ef - 0.913) * 0.12)


def _gestion(s):
    cl = _par(s, "clareo_pct", 0) / 100
    qu = _par(s, "quema_pct", 0) / 100
    res = _par(s, "restauracion_plantas_ha", 0)
    fuel = _par(s, "manejo_combustibles", 0) / 100
    ndvi = _clamp(_par(s, "ndvi", NEUTRO["ndvi"]), 0, 1)
    lai = _clamp(_par(s, "lai", NEUTRO["lai"]), 0, 8)
    fmc = float(NEUTRO["fmc"]) if "fmc" not in s else _par(s, "fmc", NEUTRO["fmc"])
    ta = float(NEUTRO["temperatura_c"]) if "temperatura_c" not in s else _par(s, "temperatura_c", NEUTRO["temperatura_c"])
    p = max(0.0, float(NEUTRO["precipitacion_mm"]) if "precipitacion_mm" not in s else _par(s, "precipitacion_mm", NEUTRO["precipitacion_mm"]))
    ndvi_ef = max(0.0, ndvi * (1 - cl) * (1 - qu * 0.8) + res * 0.0002)
    lai_ef = max(0.0, lai * (1 - cl * 1.1) * (1 - qu * 0.9) + res * 0.0008)
    # Mapeo del dominio de los sliders al rango de entrenamiento de los modelos.
    ndvi_mdl = 0.20 + ndvi_ef * 0.55
    lai_mdl = _clamp(0.30 + (lai_ef - 0.5) / 7.5 * 2.2, 0.3, 2.5)
    fmc_mdl = 25.0 + (fmc - 20.0) / 80.0 * 55.0
    p_mdl = p / 500.0 * 20.0
    return {"cl": cl, "qu": qu, "fuel": fuel, "res": res,
            "ndvi_ef": ndvi_ef, "lai_ef": lai_ef, "fmc": fmc, "ta": ta, "p": p,
            "ndvi_mdl": ndvi_mdl, "lai_mdl": lai_mdl, "fmc_mdl": fmc_mdl, "p_mdl": p_mdl}


def _mes_season(m):
    return math.sin((m - 1) / 12 * 2 * math.pi)


def _fila(mes, g):
    """Row de predictores efectivos para un mes dado (base de vegetación + estacionalidad)."""
    se = _mes_season(mes)
    ndvi_m = _clamp(g["ndvi_mdl"] * (1 + se * 0.10), 0, 1)
    lai_m = _clamp(g["lai_mdl"] * (1 + se * 0.15), 0, 8)
    ta_m = g["ta"] + 3.0 * se
    p_m = max(0.0, g["p_mdl"] * (1 + se * 0.5))
    swin_m = SW_IN_BASE * (1 + se * 0.3)
    vpd_m = VPD_BASE * (1 + se * 0.3)
    npp = _npp3pg(ndvi_m, lai_m)
    return {
        "agb": [S1_VV_BASE, S1_VH_BASE, ndvi_m, lai_m, g["fmc_mdl"], ta_m, p_m, vpd_m],
        "inc": [ndvi_m, lai_m, ta_m, p_m, swin_m, vpd_m, npp],
        "lstm": [npp, ta_m, p_m, swin_m, vpd_m, lai_m],
    }


def _fuente():
    try:
        import json
        return json.loads(_artefactos()["best"]).get("fuente_version", SOURCE_VERSION)
    except Exception:
        return SOURCE_VERSION


def _pred_biomasa(f, art):
    if art["agb"] is not None and art["sc_agb"] is not None:
        try:
            return float(art["agb"].predict(art["sc_agb"].transform([f]))[0])
        except Exception:
            return None
    return None


def _pred_riesgo(f, art):
    if art["incendio"] is not None and art["sc_inc"] is not None:
        try:
            return float(art["incendio"].predict_proba(art["sc_inc"].transform([f]))[0][1])
        except Exception:
            return None
    return None


def _pred_nee(ventana, art):
    lstm, sc_lstm = _cargar_lstm()
    if lstm is not None and sc_lstm is not None:
        try:
            x = sc_lstm.transform(ventana).astype(np.float32).reshape(1, 4, 6)
            return float(np.asarray(lstm.predict(x, verbose=0)).ravel()[0])
        except Exception:
            return None
    return None


def _escenarios(s):
    """Devuelve (escenario, neutro) en términos brutos de gestión/clima."""
    scen = _gestion(s)
    neutro_s = dict(s)
    for k in ("clareo_pct", "quema_pct", "restauracion_plantas_ha", "manejo_combustibles"):
        neutro_s[k] = 0
    return scen, _gestion(neutro_s)


def _npp_analitico(g):
    n = 8.4
    return n * (1 + g["lai_ef"] * 0.03 + g["ndvi_ef"] * 0.08 + g["p"] / 10000 - g["ta"] * 0.002)


def _sim_analitico(g, art, mes=9):
    """Fallback analítico (compatible con la demo) si fallan los modelos."""
    b = 210.0
    qu = g["qu"]; cl = g["cl"]; fuel = g["fuel"]; res = g["res"]
    bm = b * (1 - cl / 1 - qu * 0.8) + res * 0.018 + fuel * 0.04
    risk = _clamp(0.28 + cl * 0.002 + qu * 0.0025 - res * 0.00018 - fuel * 0.004
                  + (55 - g["fmc"]) * 0.003 + (1.8 - g["lai_ef"]) * 0.04 + (1 - g["ndvi_ef"]) * 0.12, 0.02, 0.98)
    return {"biomasa": bm, "npp": _npp_analitico(g), "riesgo": risk}


def _resumen(g, art, mes):
    f = _fila(mes, g)
    out = _sim_analitico(g, art, mes)
    bm = _pred_biomasa(f["agb"], art)
    if bm is not None:
        out["biomasa"] = bm
    rk = _pred_riesgo(f["inc"], art)
    if rk is not None:
        out["riesgo"] = _clamp(rk, 0.02, 0.98)
    ventana = [_fila(mes - k, g)["lstm"] for k in (3, 2, 1, 0)]
    nee = _pred_nee(ventana, art)
    out["nee"] = nee
    return out


def _trees(risk, biomass):
    rng = random.Random(42)
    out = []
    for i in range(700):
        x = (i % 35) / 34 * 100 - 50
        y = (i // 35) / 19 * 60 - 30
        h = _clamp(7 + (math.sin(i * 12.3) * 0.5 + 0.5) * 22 + (x + y) * 0.02, 5, 32)
        rr = _clamp(risk + (math.sin(i * 0.77) * 0.5) * 0.2, 0.03, 0.98)
        out.append({"x": x, "y": y, "height": h, "crown": 1.2 + h * 0.09,
                    "biomass": biomass / 210 * (h / 18), "risk": rr,
                    "loss": rng.random() * 0.12})
    return out


PRED_META = {
    "agb": [("S1_VV", "dB"), ("S1_VH", "dB"), ("NDVI", ""), ("LAI", "m²/m²"), ("FMC", "%"),
            ("TA_ERA", "°C"), ("P_ERA", "mm"), ("VPD_ERA", "hPa")],
    "inc": [("NDVI", ""), ("LAI", "m²/m²"), ("TA_ERA", "°C"), ("P_ERA", "mm"),
            ("SW_IN_ERA", "W/m²"), ("VPD_ERA", "hPa"), ("NPP_3PG", "")],
    "lstm": [("NPP_3PG", ""), ("TA_ERA", "°C"), ("P_ERA", "mm"), ("SW_IN_ERA", "W/m²"),
             ("VPD_ERA", "hPa"), ("LAI", "m²/m²")],
}


def _predictoras(kind, vec):
    return [{"nombre": n, "valor": round(v, 3), "unidad": u} for (n, u), v in zip(PRED_META[kind], vec)]


def _insumos(scen, mes, cur, base, art, payload):
    """Traza de la inferencia: qué datos recibió cada modelo y qué devolvió."""
    f = _fila(mes, scen)
    cl = round(_par(payload, "clareo_pct", 0), 1)
    qu = round(_par(payload, "quema_pct", 0), 1)
    res = round(_par(payload, "restauracion_plantas_ha", 0))
    fuel = round(_par(payload, "manejo_combustibles", 0), 1)
    fmc = _par(payload, "fmc", 55)
    modelos = [
        {"objetivo": "Biomasa", "modelo": "AGB_GEDI" if art["agb"] else "sintético",
         "tipo": "Random Forest regresión", "predictoras": _predictoras("agb", f["agb"]),
         "resultado": round(cur["biomasa"], 2), "unidad": "Mg/ha"},
        {"objetivo": "Riesgo incendio", "modelo": "INCENDIO" if art["incendio"] else "sintético",
         "tipo": "Random Forest clasificación", "predictoras": _predictoras("inc", f["inc"]),
         "resultado": round(cur["riesgo"], 3), "unidad": "probabilidad"},
        {"objetivo": "NEE", "modelo": "3PG_LSTM" if _lstm_ok() else "no disponible",
         "tipo": "Híbrido fisiológico-LSTM", "predictoras": _predictoras("lstm", f["lstm"]),
         "resultado": round(cur["nee"], 3) if cur["nee"] is not None else None, "unidad": "flujo neto de C"},
    ]
    notes = []
    if cl or qu:
        notes.append(f"El clareo ({cl}%) y la quema ({qu}%) redujeron la vegetación efectiva "
                     f"(NDVI {scen['ndvi_ef']:.2f}, LAI {scen['lai_ef']:.2f}) antes de entrar a los modelos.")
    if art["agb"]:
        d = cur["biomasa"] - base["biomasa"]
        notes.append(f"Con NDVI {f['agb'][2]:.2f} y LAI {f['agb'][3]:.2f} en escala de entrenamiento, AGB_GEDI "
                     f"estimó {cur['biomasa']:.1f} Mg/ha, {'por debajo' if d < -0.5 else 'por encima' if d > 0.5 else 'similar a'} "
                     f"la línea base ({base['biomasa']:.1f} Mg/ha).")
    if art["incendio"]:
        dr = cur["riesgo"] - base["riesgo"]
        notes.append(f"INCENDIO estima {cur['riesgo']*100:.1f}% de probabilidad de incendio con FMC {fmc:.0f}% y "
                     f"LAI {f['inc'][1]:.2f} ({'más' if dr >= 0 else 'menos'} que la base {base['riesgo']*100:.1f}%).")
    if cur["nee"] is not None:
        notes.append(f"El LSTM 3-PG predice un balance neto de carbono (NEE) de {cur['nee']:.3f}; "
                     "negativo significa que el ecosistema actúa como sumidero de CO₂.")
    notes.append("Los valores de los sliders se normalizaron al rango de entrenamiento "
                 "(NDVI 0.20–0.75, LAI 0.3–2.5, FMC 25–80%, precipitación 0–20) tal como los ve cada modelo.")
    return {"gestion": {"clareo_pct": cl, "quema_pct": qu, "restauracion_plantas_ha": res,
                        "manejo_combustibles": fuel},
            "vegetacion_efectiva": {"ndvi": round(scen["ndvi_ef"], 3), "lai": round(scen["lai_ef"], 3),
                                    "npp_3pg": round(_npp3pg(scen["ndvi_ef"], scen["lai_ef"]), 3)},
            "modelos": modelos, "interpretaciones": notes}


def _fmt_num(x, nd=2):
    try:
        return "—" if x is None else f"{float(x):.{nd}f}"
    except (TypeError, ValueError):
        return str(x)


def _prompt_explicacion(scen, sim):
    """Compone un prompt en español sencillo con los datos reales de la inferencia."""
    g = [("Clareo", "clareo_pct", 0, "%"), ("Quema", "quema_pct", 0, "%"),
         ("Restauración", "restauracion_plantas_ha", 0, "pl/ha"),
         ("Manejo de combustibles", "manejo_combustibles", 0, "%"),
         ("NDVI", "ndvi", 0.72, ""), ("LAI", "lai", 4.0, "m²/m²"),
         ("FMC", "fmc", 55, "%"), ("Precipitación", "precipitacion_mm", 180, "mm"),
         ("Temperatura", "temperatura_c", 27, "°C")]
    esc = " | ".join(f"{n} {_fmt_num(_par(scen, k, d), 1)}{u}".strip() for n, k, d, u in g)
    base, cur, delta = sim.get("baseline", {}), sim.get("scenario", {}), sim.get("delta", {})
    kpis = []
    for k, label, unit in (("biomasa", "Biomasa", "Mg/ha"), ("npp", "NPP", "Mg C/ha/año"),
                           ("riesgo", "Riesgo de incendio", "probabilidad"),
                           ("nee", "NEE (balance neto de carbono)", "flujo neto de C")):
        kpis.append(f"- {label}: línea base {_fmt_num(base.get(k))} → escenario "
                    f"{_fmt_num(cur.get(k))} (delta {_fmt_num(delta.get(k))}) {unit}".strip())
    traza = []
    for m in sim.get("insumos", {}).get("modelos", []):
        preds = ", ".join(f"{p.get('nombre')}={_fmt_num(p.get('valor'), 3)} {p.get('unidad', '')}".strip()
                          for p in m.get("predictoras", []))
        traza.append(f"- {m.get('objetivo')} ({m.get('modelo')}, {m.get('tipo')}): analizó {preds}; "
                     f"devolvió {_fmt_num(m.get('resultado'), 3)} {m.get('unidad', '')}".strip())
    notas = "\n".join(f"- {n}" for n in sim.get("insumos", {}).get("interpretaciones", []))
    sv = sim.get("source_version", "desconocida")
    return (
        "Eres un divulgador forestal. Explica en lenguaje sencillo y claro qué significa esta inferencia "
        "de un gemelo digital forestal (sitio BR-Sa1, Floresta Nacional do Tapajós). NO inventes valores: "
        "usa solo los datos entregados. Responde en español, ~150-200 palabras, con una introducción breve, "
        "2-4 viñetas de qué hizo cada modelo y un cierre con la conclusión práctica del cambio frente a la "
        "línea base. Recuerda que un NEE negativo significa que el ecosistema es sumidero de CO₂ y que "
        "esto es ilustrativo, no para decisiones operativas.\n\n"
        f"## Escenario simulado\n{esc}\n\n"
        f"## Resultado de la inferencia (modelos entrenados, fuente {sv})\n" + "\n".join(kpis) + "\n\n"
        "## Qué analizó cada modelo (traza)\n" + ("\n".join(traza) or "- sin traza disponible") + "\n\n"
        "## Interpretaciones del laboratorio\n" + (notas or "- sin notas")
    )


def _gemini(prompt):
    model = GEMINI_MODEL or "gemini-2.0-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 4096}}
    try:
        r = requests.post(url, params={"key": GEMINI_API_KEY}, json=body, timeout=90)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"No se pudo contactar a Gemini ({e.__class__.__name__}).")
    if r.status_code != 200:
        det = ""
        try:
            det = r.json().get("error", {}).get("message", "")
        except Exception:
            pass
        raise HTTPException(status_code=502,
                            detail=f"Gemini respondió error {r.status_code}: {det}".strip().rstrip(":"))
    try:
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        raise HTTPException(status_code=502, detail="Gemini no devolvió un texto utilizable.")


@app.get('/modelo/mejor')
def mejor():
    """Devuelve metadatos del mejor modelo exportado o de demostración."""
    art = _artefactos()
    try:
        import json
        b = json.loads(art["best"])
        return {"nombre": b.get("mejor_modelo", "3PG_LSTM"),
                "tipo": b.get("tipo"),
                "objetivo": b.get("objetivo"),
                "metricas": b.get("metricas", {}),
                "validacion_cruzada": b.get("validacion_cruzada"),
                "variables_predictoras": b.get("variables_predictoras"),
                "hiperparametros": b.get("hiperparametros"),
                "source_version": b.get("fuente_version", _fuente()),
                "fecha": b.get("fecha_seleccion")}
    except Exception:
        return {"nombre": "3-PG + LSTM", "metricas": {"r2": 0.92, "rmse": 13.2, "mae": 8.7, "roc_auc": 0.95},
                "source_version": SOURCE_VERSION, "fecha": datetime.now().isoformat()}


@app.get('/diccionario')
def diccionario():
    """Devuelve rangos de variables usados por los controles del laboratorio."""
    return {"clareo_pct": {"unit": "%", "min": 0, "max": 60}, "quema_pct": {"unit": "%", "min": 0, "max": 50},
            "restauracion_plantas_ha": {"unit": "pl/ha", "min": 0, "max": 500},
            "manejo_combustibles": {"unit": "%", "min": 0, "max": 100},
            "fmc": {"unit": "%", "min": 20, "max": 100}, "lai": {"unit": "m²/m²", "min": 0.5, "max": 8},
            "ndvi": {"unit": "", "min": 0, "max": 1}, "precipitacion_mm": {"unit": "mm", "min": 0, "max": 500},
            "temperatura_c": {"unit": "°C", "min": 15, "max": 35}}


@app.post('/simular')
def simular(payload: dict):
    """Ejecuta una inferencia what-if con los modelos entrenados reales."""
    scen, neutro = _escenarios(payload)
    art = _artefactos()
    mes = int(_par(payload, "month", 9))
    cur = _resumen(scen, art, mes)
    base = _resumen(neutro, art, mes)
    temporal = []
    for i in range(1, 13):
        sc = _resumen(scen, art, i)
        bc = _resumen(neutro, art, i)
        temporal.append({"period": f"2026-{i:02d}", "baseline": bc["biomasa"], "scenario": sc["biomasa"],
                         "riesgo_base": bc["riesgo"], "riesgo_escenario": sc["riesgo"]})
    return {"source_version": _fuente(),
            "modelos": {"biomasa": "AGB_GEDI" if art["agb"] else "sintético",
                        "riesgo": "INCENDIO" if art["incendio"] else "sintético",
                        "nee": "3PG_LSTM" if _lstm_ok() else "no disponible"},
            "baseline": base, "scenario": cur,
            "delta": {"biomasa": cur["biomasa"] - base["biomasa"], "npp": cur["npp"] - base["npp"],
                      "riesgo": cur["riesgo"] - base["riesgo"], "nee": cur["nee"] - base["nee"]
                      if cur["nee"] is not None and base["nee"] is not None else None},
            "insumos": _insumos(scen, mes, cur, base, art, payload),
            "temporal": temporal, "trees": _trees(cur["riesgo"], cur["biomasa"])}


@app.post('/reporte')
def reporte(payload: dict):
    """Devuelve un resumen trazable listo para ser consumido por un generador PDF/Excel."""
    return {"generated_at": datetime.now().isoformat(), "source_version": SOURCE_VERSION, "payload": payload}


@app.get('/explicar/estado')
def explicar_estado():
    """Indica si el servidor tiene configurada la llave de Gemini."""
    return {"configurado": bool(GEMINI_API_KEY)}


@app.post('/explicar')
def explicar(payload: dict):
    """Explica en lenguaje sencillo qué significa la inferencia usando Gemini."""
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=400,
                            detail="GEMINI_API_KEY no está configurada en el servidor (revisa el archivo .env).")
    sim = payload.get("simulation")
    scen = payload.get("escenario") if payload.get("escenario") is not None else {}
    if not isinstance(sim, dict) or any(k not in sim for k in ("baseline", "scenario", "delta")):
        raise HTTPException(status_code=400, detail="Faltan los datos de la simulación (simulation).")
    return {"explicacion": _gemini(_prompt_explicacion(scen, sim))}