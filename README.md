# Gemelo Digital Forestal

Prototipo funcional centrado en la **pantalla Monitor de Entrenamiento**. Toda la demo funciona sin internet ni credenciales externas y usa resultados sintéticos etiquetados `synthetic_test`.

## Ejecutar

```bash
pip install -r requirements.txt
streamlit run app.py
```

El monitor genera automáticamente `modelos_entrenados/historial_entrenamiento.json` si todavía no existe. Cuando Colab produzca los artefactos reales, se pueden cargar desde la barra lateral del monitor sin rediseñar la pantalla.

## Pantallas
1. **Monitor de Entrenamiento:** nueve fases, estados, progreso, duración, métricas, CV k=5, GridSearch, EDA, logs, comparación de modelos, carga de artefactos y re-ejecución demo.
2. **Probador de Modelos:** inferencia demostrativa y zona de carga del modelo real.
3. **Laboratorio React:** esqueleto preparado para escenario, mapas, serie temporal y 3D.

## Importante
Los resultados de la demo son ilustrativos y no representan estimaciones reales para BR-Sa1.

## Laboratorio React v2

La aplicación React incluye el Laboratorio del Mejor Modelo completo: simulación what-if, mapa 2D analítico con capas, bosque 3D procedural con GPU instancing, comparación antes/después, series temporales y exportación JSON/CSV. Puede funcionar en modo demostración sin FastAPI y cambia a inferencia del backend cuando `VITE_API_URL` está disponible.
