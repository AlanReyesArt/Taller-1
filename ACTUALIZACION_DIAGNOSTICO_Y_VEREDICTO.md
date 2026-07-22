# Actualización: diagnóstico preliminar y veredicto exhaustivo

## Cambios realizados

1. **Semáforo del diagnóstico corregido**
   - Las tarjetas ya no dependen únicamente de subtítulos internos.
   - También revisan las debilidades finales clasificadas por área.
   - Si existe una debilidad metodológica, técnica o lingüística explícita, el área se muestra como **Requiere revisión** o **Crítico**, en lugar de **Adecuado**.

2. **Diagnóstico secuencial más ligero**
   - Se redujo el contexto enviado al flujo secuencial.
   - Conserva solo fragmentos ejecutivos de resumen, problema, objetivos, metodología, arquitectura, resultados y conclusiones.
   - No utiliza la tesis completa ni pretende reemplazar el veredicto oficial.

3. **Veredicto jerárquico más profundo**
   - Después del comité multiagente se ejecuta una segunda auditoría real con DeepSeek.
   - La auditoría verifica evidencia, contradicciones, falsos positivos y prioridades de corrección.
   - No se agregó una demora artificial: el tiempo adicional corresponde a procesamiento real.
   - El Rigor Score y el veredicto oficial continúan calculándose de forma determinista en el backend.

## Configuración

En `backend/.env` puede activarse o desactivarse la segunda revisión:

```env
JERARQUICO_AUDITORIA_EXHAUSTIVA=true
JERARQUICO_AUDITORIA_MAX_CHARS=42000
JERARQUICO_AUDITORIA_MAX_TOKENS=2600
JERARQUICO_AUDITORIA_TIMEOUT=180
```

Para que la auditoría funcione debe existir `DEEPSEEK_API_KEY`.
