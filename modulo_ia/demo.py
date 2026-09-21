"""Generación de resultados simulados para el monitor."""
from datetime import datetime, timezone
from pathlib import Path
import json
import numpy as np
from config import MODELOS, PHASE_NAMES, SOURCE_VERSION


def generar_historial_demo(path: Path) -> dict:
    """Genera un historial determinista y plausible para la interfaz.

    Args:
        path: Ruta del JSON a generar.
    Returns:
        Diccionario serializable con fases y resultados.
    """
    rng=np.random.default_rng(42)
    models={
      "Random Forest":{"r2":0.84,"rmse":18.4,"mae":12.1,"roc_auc":0.88,"f1":0.81},
      "LightGBM":{"r2":0.87,"rmse":16.7,"mae":10.9,"roc_auc":0.91,"f1":0.85},
      "Regresión Lineal Múltiple":{"r2":0.68,"rmse":27.9,"mae":19.7,"roc_auc":0.72,"f1":0.64},
      "3-PG + Random Forest":{"r2":0.89,"rmse":15.1,"mae":9.8,"roc_auc":0.93,"f1":0.88},
      "3-PG + LSTM":{"r2":0.92,"rmse":13.2,"mae":8.7,"roc_auc":0.95,"f1":0.91},
    }
    folds={}
    for m,v in models.items():
        folds[m]={"r2":[round(float(np.clip(v['r2']+rng.normal(0,.025),0,1)),3) for _ in range(5)],
                  "rmse":[round(float(max(1,v['rmse']+rng.normal(0,1.4))),2) for _ in range(5)]}
    phases=[]
    for i,name in enumerate(PHASE_NAMES):
        if i==0: metrics={"fuentes_generadas":8,"registros":12540,"fuente_version":SOURCE_VERSION}
        elif i==1: metrics={"variables_fusionadas":24,"filas":3250,"nulos_pct":0.7}
        elif i==2: metrics={"features":24,"correlacion_max":0.91,"outliers_pct":2.4}
        elif i==3: metrics={"k":5,"mejor_r2":0.92,"mejor_rmse":13.2,"folds":folds}
        elif i==4: metrics={"metodo":"GridSearchCV","combinaciones":18,"mejor_modelo":"3-PG + LSTM","mejor_r2":0.925}
        elif i==5: metrics={"modelos_entrenados":5,"epochs":25,"tiempo_s":48.6}
        elif i==6: metrics={"mejor_modelo":"3-PG + LSTM","r2":0.92,"rmse":13.2,"mae":8.7,"roc_auc":0.95}
        elif i==7: metrics={"prueba":"t-test pareado + bootstrap","p_value":0.018,"ic95_r2":[0.90,0.94]}
        else: metrics={"archivos":4,"estado":"listo","version":SOURCE_VERSION}
        phases.append({"phase":name,"status":"completada","timestamp":datetime.now(timezone.utc).isoformat(),"duration_s":round(2.4+i*1.8,1),"metrics":metrics,"log":f"[{name}] OK · ejecución demo · fuente_version={SOURCE_VERSION}"})
    data={"schema_version":"1.0","source_version":SOURCE_VERSION,"generated_at":datetime.now(timezone.utc).isoformat(),"demo":True,"models":models,"phases":phases}
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    return data
