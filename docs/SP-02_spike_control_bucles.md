# SP-02 — Spike: Control de Bucles en Debate Multiagente

**Proyecto:** Sistema de Deliberación Multiagente para Análisis de Tesis  
**Épica:** EP-02 — Módulo de Crítica y Rigor Científico  
**Sprint:** 2 | **Fecha:** 06/06/2026  
**Equipo:** Reyes Arteaga Alan David · Gastañuadi Lescano Raul Andrés

---

## 1. Problema Investigado

¿Cómo evitar que el debate circular entre el Agente Metodológico y el Agente Técnico en la Arquitectura de Red genere ciclos infinitos?

---

## 2. Solución Elegida: Contador de Iteraciones en JSON de Estado

Se implementa un **JSON de estado maestro** que viaja entre los nodos de Langflow. Este JSON incluye los campos de control:

```json
{
  "iteracion_actual": 1,
  "max_iteraciones": 3,
  "historial_debate": [],
  "consenso_alcanzado": false
}
```

### Lógica de parada (dos condiciones, la primera que se cumpla gana):

| Condición | Descripción |
|---|---|
| **Agotamiento** | `iteracion_actual >= max_iteraciones` (3 rondas) → el flujo pasa al Agente de Consenso automáticamente |
| **Consenso anticipado** | ≥2 agentes emiten el mismo veredicto en la misma ronda → el flujo salta al Agente de Consenso sin esperar la ronda 3 |

### Implementación en Langflow

En el nodo del Agente de Consenso se configura una condición de entrada:

```
SI consenso_alcanzado == true  →  emitir veredicto inmediato
SI iteracion_actual >= 3       →  emitir veredicto por agotamiento
SINO                           →  continuar al siguiente ciclo
```

---

## 3. Alternativas Descartadas

| Alternativa | Razón del descarte |
|---|---|
| Timeout por tiempo (ej. 40s) | No predecible: depende de la latencia de la API del LLM, no del contenido |
| Detención por longitud de respuesta | Artificialmente corta el debate, no evalúa calidad del consenso |
| Intervención manual por ronda | Rompe el principio de automatización del sistema |

---

## 4. Decisión Técnica

**Se implementa el contador de iteraciones en el JSON de estado** porque:
- Es determinista: siempre termina en máximo 3 rondas (≤120s total estimado)
- Permite el consenso anticipado si los agentes coinciden antes
- El historial completo queda persistido en `analysis_results` de SQLite para métricas posteriores

---

## 5. Prototipo de Prueba

Se ejecutó el flujo ARQ_RED con la tesis de prueba DIRESA en 3 escenarios:

| Escenario | Resultado | Rondas ejecutadas |
|---|---|---|
| Agentes coinciden desde ronda 1 | Consenso anticipado activado | 1 |
| Agentes coinciden en ronda 2 | Consenso anticipado activado | 2 |
| Agentes nunca coinciden | Agotamiento — Consenso emite veredicto | 3 |

**Entregable verificado:** el flujo se detuvo correctamente en los 3 escenarios sin ciclos infinitos.
