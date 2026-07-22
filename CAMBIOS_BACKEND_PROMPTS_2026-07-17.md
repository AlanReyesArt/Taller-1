# Actualización de integración Prompt–Backend

Fecha: 17 de julio de 2026

## Cambios principales

- El backend ya no sobrescribe los **System Messages** configurados manualmente en Langflow.
- El flujo Secuencial conserva únicamente la inyección de las rúbricas en los Prompt Templates.
- El parser reconoce el nuevo JSON de diagnóstico preliminar (`tipo_resultado: diagnostico_preliminar`).
- El flujo Secuencial deja de depender de palabras como APROBADO o RECHAZADO en el frontend.
- El frontend muestra los estados:
  - `sin_alertas_relevantes`
  - `requiere_revision`
  - `atencion_prioritaria`
- El parser jerárquico acepta `criterios` y mantiene compatibilidad temporal con `evaluaciones`.
- Los estados se normalizan a:
  - `cumple`
  - `observado`
  - `no_cumple`
  - `no_evaluable`
- Un criterio omitido por un agente ya no recibe 50 % automáticamente. Se registra como `error_evaluacion`.
- El backend valida IDs duplicados, desconocidos y criterios ausentes.
- `no_evaluable` se excluye del denominador aplicable, manteniendo la escala institucional 10/7/3.
- El backend continúa siendo la única fuente oficial para puntajes, Rigor Score y veredicto.
- Los reportes individuales de los agentes jerárquicos se guardan en el resultado para el frontend.

## Validaciones realizadas

- Compilación de los módulos Python modificados: correcta.
- Prueba unitaria básica del cálculo determinista: correcta.
- Compilación de producción del frontend con Vite: correcta.

## Puesta en marcha

En `frontend` ejecutar:

```bash
npm install
npm run dev
```

En `backend` activar el entorno virtual e instalar las dependencias si fuera necesario:

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Los Prompt Templates y System Messages deben permanecer configurados en Langflow tal como fueron actualizados manualmente.
