# ADR 008-monitor

## Contexto
El prototipo requiere reproducibilidad y separación entre entrenamiento e interfaces.

## Decisión
Mantener datos sintéticos, artefactos exportables y lógica de presentación desacoplada del entrenamiento.

## Consecuencias
La interfaz funciona desde el inicio; los modelos reales pueden incorporarse posteriormente respetando el contrato de artefactos.
