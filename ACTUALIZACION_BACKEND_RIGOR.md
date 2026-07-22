# Actualización aplicada

## Cambios principales

1. El flujo Secuencial ahora recibe un input reducido para diagnóstico preliminar.
2. El Jerárquico conserva el input segmentado completo.
3. Los estados se normalizan a `cumple`, `parcial` y `no_cumple`.
4. Los criterios parciales obtienen 50 % de su puntaje máximo.
5. El Rigor Score se calcula exclusivamente en FastAPI con pesos 40 % / 35 % / 25 %.
6. El veredicto oficial se determina en backend: APROBADO, APROBADO CON OBSERVACIONES o RECHAZADO.
7. El frontend prioriza `metricas_oficiales` y `veredicto_oficial`, no el número generado por DeepSeek.
8. Se corrigió el formato de ID-45 en T4; ahora se reconocen 60 criterios y un máximo aproximado de 7 puntos.

## Importante

- Mantén en Langflow los prompts actualizados que ya colocaste.
- Reinicia MCP, Langflow, backend y frontend después de reemplazar el proyecto.
- Ejecuta una tesis nueva o elimina el análisis anterior; los resultados antiguos conservan el score previo.
- Los archivos `.bak` contienen las versiones previas de los archivos modificados.
