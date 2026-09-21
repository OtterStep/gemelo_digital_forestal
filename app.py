"""Entrada principal de la aplicación Streamlit."""
import streamlit as st
from pathlib import Path
from config import MODELOS_DIR, SOURCE_VERSION

st.set_page_config(page_title="Gemelo Digital Forestal", page_icon="🌳", layout="wide")
st.title("🌳 Gemelo Digital Forestal")
st.caption("Prototipo reproducible · datos sintéticos · BR-Sa1 como referencia geográfica")

c1,c2,c3,c4=st.columns(4)
c1.metric("Estado", "Demo operativa")
c2.metric("Fuente", SOURCE_VERSION)
c3.metric("Modelos", "5")
c4.metric("Entrenamiento real", "Solo Colab")

st.info("Usa **Monitor de Entrenamiento** en el menú lateral para ver los resultados simulados de cada fase. Los artefactos reales de Colab se pueden cargar después desde la barra lateral del monitor.")

st.subheader("Arquitectura")
st.markdown("""
```text
Datos sintéticos → Fusión → EDA → CV k=5 → GridSearch → Entrenamiento → Selección → Estadística → Artefactos
                                                                  ↓
                                      historial_entrenamiento.json + mejor_modelo.json + modelos (*.pkl/*.joblib/*.h5)
                                                                  ↓
                              Streamlit (monitor/probador) → FastAPI → React (laboratorio + 3D)
```
""")
if not MODELOS_DIR.exists() or not any(MODELOS_DIR.iterdir()):
    st.warning("Aún no hay modelos exportados. La demo usa resultados simulados y está preparada para cargar los artefactos reales cuando estén disponibles.")
