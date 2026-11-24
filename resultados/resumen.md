# Resumen de resultados

Generado con `python scripts/tabla_resultados.py`.

## Conversaciones de prueba (62 conversaciones, 153 turnos)

| Versión | Intención acc. | Intención macro-F1 | Datos F1 | Resp. inventadas | Reconoce que no sabe | Menciona lo esperado | s/turno |
|---|---|---|---|---|---|---|---|
| v0 cruda | 0.065 | 0.011 | 0.000 | 0.000 | 0.00 | 0.000 | 0.00 |
| v0 corregida | 0.771 | 0.773 | 0.873 | 0.000 | 0.00 | 0.015 | 95.72 |
| Reglas + regex + plantillas | 0.922 | 0.914 | 1.000 | 0.000 | 0.93 | 0.924 | 0.00 |
| TF-IDF sin contexto | 0.634 | 0.664 | 1.000 | 0.000 | 0.71 | 0.667 | 0.00 |
| TF-IDF + regex + plantillas (liviana) | 0.876 | 0.861 | 1.000 | 0.000 | 0.71 | 0.879 | 0.00 |
| qwen3:4b intención + regex + plantillas (final) | 0.935 | 0.919 | 1.000 | 0.000 | 0.79 | 0.970 | 1.69 |
| qwen3:4b intención y datos | 0.935 | 0.919 | 0.867 | 0.007 | 0.79 | 0.727 | 4.90 |
| TF-IDF + gemma3:4b redacta | 0.876 | 0.861 | 1.000 | 0.131 | 1.00 | 0.348 | 8.28 |

## Conversaciones de validación (20 conversaciones, 47 turnos)

| Versión | Intención acc. | Intención macro-F1 | Datos F1 | Resp. inventadas | Reconoce que no sabe | Menciona lo esperado | s/turno |
|---|---|---|---|---|---|---|---|
| v0 cruda | 0.043 | 0.007 | 0.000 | 0.000 | 0.00 | 0.000 | 0.00 |
| Reglas + regex + plantillas | 0.766 | 0.683 | 0.953 | 0.000 | 0.67 | 0.679 | 0.00 |
| TF-IDF sin contexto | 0.638 | 0.668 | 0.953 | 0.000 | 0.67 | 0.607 | 0.00 |
| TF-IDF + regex + plantillas (liviana) | 0.894 | 0.886 | 0.953 | 0.000 | 0.67 | 0.714 | 0.00 |
| qwen3:4b intención + regex + plantillas (final) | 0.915 | 0.844 | 0.953 | 0.000 | 0.67 | 0.750 | 4.78 |
| qwen3:4b intención y datos | 0.915 | 0.844 | 0.824 | 0.000 | 0.67 | 0.643 | 8.07 |
| TF-IDF + gemma3:4b redacta | 0.894 | 0.886 | 0.953 | 0.213 | 1.00 | 0.250 | 9.19 |
