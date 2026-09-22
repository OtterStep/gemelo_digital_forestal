"""Entrada principal de la aplicación Streamlit."""
import json
import streamlit as st
from config import MODELOS_DIR, SOURCE_VERSION

st.set_page_config(page_title="Gemelo Digital Forestal", page_icon="🌳", layout="wide")

HIST = MODELOS_DIR / "historial_entrenamiento.json"
BEST = MODELOS_DIR / "mejor_modelo.json"


def _fuente():
    for p in (BEST, HIST):
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                return data.get("fuente_version") or data.get("source_version") or SOURCE_VERSION
            except Exception:
                continue
    return SOURCE_VERSION


n_modelos = sum(1 for f in MODELOS_DIR.glob("*.joblib") if "scaler" not in f.name and "artefactos" not in f.name)
hay_h5 = any(MODELOS_DIR.glob("*.h5"))
n_modelos += int(hay_h5)
hay_artefactos = BEST.exists() or n_modelos > 0
fuente = _fuente()

st.title("🌳 Gemelo Digital Forestal")
st.caption("Prototipo reproducible · BR-Sa1 (Floresta Nacional do Tapajós) como referencia geográfica")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Estado", "Operativa")
c2.metric("Fuente", fuente)
c3.metric("Modelos reales", n_modelos)
c4.metric("Entrenamiento real", "Sí (Colab)" if hay_artefactos else "Solo demo")

if hay_artefactos:
    st.success("Artefactos reales detectados: el Monitor muestra el flujo de entrenamiento completo y el Probador usa los modelos exportados.")
else:
    st.info("Aún no hay modelos exportados. La demo usa resultados simulados y está preparada para cargar los artefactos reales cuando estén disponibles.")

st.subheader("Arquitectura")
st.markdown("""
```text
Datos (Drive/FLUXNET+GEE) → Fusión → EDA → CV k=5 → GridSearch → Entrenamiento → Selección → Estadística → Artefactos
                                                                  ↓
                      historial_entrenamiento.json + mejor_modelo.json + modelos (*.joblib/*.h5)
                                                                  ↓
                     Streamlit (monitor/probador) → FastAPI → React (laboratorio + 3D)
```
""")