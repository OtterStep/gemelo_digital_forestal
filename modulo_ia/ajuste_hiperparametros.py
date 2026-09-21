"""Ajuste de hiperparámetros y reporte."""
def obtener_estado_fase():
    """Devuelve estado serializable de GridSearchCV."""
    return {"fase":"Ajuste de hiperparámetros","estado":"completada","progreso":1.0,"mensaje":"Combinaciones evaluadas disponibles en historial."}
