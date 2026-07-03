# SP-02b — Spike: Mecanismo de Consenso entre Agentes

**Proyecto:** Sistema de Deliberación Multiagente para Análisis de Tesis  
**Épica:** EP-02 — Módulo de Crítica y Rigor Científico  
**Sprint:** 2 | **Fecha:** 06/06/2026  
**Dependencia:** SP-02

---

## 1. Problema Investigado

¿Cómo puede el Agente de Consenso detectar que los otros agentes están de acuerdo y terminar el debate antes de agotar las 3 rondas?

---

## 2. Solución Elegida: Comparación de Veredictos en el JSON de Estado

Al final de cada ronda, cada agente escribe su veredicto parcial en el JSON de estado:

```json
{
  "iteracion_actual": 2,
  "veredictos_ronda": {
    "metodologico": "observado",
    "tecnico": "observado"
  },
  "consenso_alcanzado": false
}
```

El nodo de control evalúa: **si `veredictos_ronda.metodologico == veredictos_ronda.tecnico`** → activa `consenso_alcanzado = true` y redirige el flujo al Agente de Consenso.

### Lógica de consenso

```
SI metodologico == tecnico:
    consenso_alcanzado = true
    → saltar a Agente de Consenso
SINO:
    iteracion_actual += 1
    → continuar debate (si iteracion_actual < max_iteraciones)
```

---

## 3. Escenarios de Prueba

| Escenario | Veredicto Metodológico | Veredicto Técnico | ¿Consenso? | Rondas |
|---|---|---|---|---|
| Ambos detectan problema grave | "rechazado" | "rechazado" | ✅ Sí | 1 |
| Divergen en ronda 1, coinciden en ronda 2 | "observado" → "rechazado" | "rechazado" → "rechazado" | ✅ Sí | 2 |
| Nunca coinciden (agotamiento) | "aprobado" | "rechazado" | ❌ No | 3 |

---

## 4. Decisión Técnica

La lógica de consenso se implementa como una condición en el nodo Router de Langflow que evalúa el JSON de estado después de cada ronda. No requiere un agente adicional — es una regla determinista basada en la comparación de strings del campo `veredictos_ronda`.

**Ventaja clave:** reduce el tiempo de ejecución en un 33-66% cuando hay consenso temprano, reduciendo también el consumo de tokens de la API.
