# Laboratorio React — Gemelo Digital Forestal

Laboratorio de inferencia y simulación del mejor modelo. No entrena modelos.

## Funcionalidades
- Header dinámico desde `mejor_modelo.json`/`GET /modelo/mejor`.
- Escenarios what-if con clareo, quema, restauración, combustible, FMC, LAI, NDVI, precipitación y temperatura.
- Mapa 2D analítico de datos sintéticos.
- Bosque 3D procedural con 700 árboles, tronco + copa, cámara orbital y color por riesgo.
- Serie temporal mensual base vs escenario.
- Exportación JSON/CSV y vista imprimible para PDF.
- Fallback local: si FastAPI no está disponible, la interfaz ejecuta el simulador sintético en el navegador.

## Ejecución
```bash
npm install
npm run dev
```

Para usar FastAPI:
```bash
cd ..
uvicorn modulo_servidor.api:app --reload --port 8000
```

El front usa `VITE_API_URL=http://localhost:8000` si se define; de lo contrario usa ese valor por defecto.

## Limitaciones
Todo resultado es `synthetic_test`. La escena 3D es procedural y no representa especies reales. La geometría se limita a 700 árboles para conservar fluidez en hardware modesto.
