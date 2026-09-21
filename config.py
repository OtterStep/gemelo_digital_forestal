"""Configuración central del prototipo forestal."""
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass
MODELOS_DIR = ROOT_DIR / "modelos_entrenados"
DATOS_DIR = ROOT_DIR / "recursos" / "datos_ejemplo"
SEED = 42
USE_REAL_DATA = False
SOURCE_VERSION = "synthetic_test"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash").strip()
AREA_ESTUDIO = {
    "sitio": "BR-Sa1 / Floresta Nacional do Tapajós",
    "crs": "EPSG:4326",
    "bbox": [-55.3333, -3.1667, -54.5, -2.5],
    "hectareas_aprox": 100_000,
}
YEARS = list(range(2019, 2024))
MODELOS = ["Random Forest", "LightGBM", "Regresión Lineal Múltiple", "3-PG + Random Forest", "3-PG + LSTM"]
PHASE_NAMES = [
    "Descarga / generación de datos", "Fusión de datos", "Análisis exploratorio",
    "Validación cruzada (k=5)", "Ajuste de hiperparámetros", "Entrenamiento final",
    "Selección de modelo", "Pruebas estadísticas", "Exportación de artefactos"
]
