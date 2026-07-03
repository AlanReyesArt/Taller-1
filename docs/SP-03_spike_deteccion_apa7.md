# SP-03 — Spike: Detección de Errores APA 7 en Texto Académico

**Proyecto:** Sistema de Deliberación Multiagente para Análisis de Tesis  
**Épica:** EP-03 — Módulo de Dictamen y Escrutinio  
**Sprint:** 2 | **Fecha:** 06/06/2026

---

## 1. Problema Investigado

¿Qué técnica usar para que el Agente Lingüístico detecte errores de citación APA 7 en el texto de la tesis, con una precisión aceptable y en menos de 20 segundos?

---

## 2. Técnicas Evaluadas

| Técnica | Descripción | Precisión estimada | Velocidad | Implementación |
|---|---|---|---|---|
| **Reglas heurísticas (regex)** | Patrones regex para formatos APA conocidos | ~70% en errores de formato | <2s | Simple — implementable en Python |
| **Prompt engineering (LLM)** | El propio agente LLM detecta errores con un prompt especializado | ~85-90% | 5-15s | Ya disponible en Langflow |
| **spaCy + reglas NLP** | Pipeline NLP para detectar citas sin contexto semántico | ~75% | 3-8s | Requiere instalación adicional |

---

## 3. Decisión Técnica: Prompt Engineering con LLM (Agente Lingüístico)

Se eligió **prompt engineering** porque:
- El sistema ya usa Langflow con LLMs — no requiere dependencias nuevas
- Alcanza la mayor precisión (85-90%) sobre los tipos de error más frecuentes
- Responde en <20s para fragmentos de hasta 5k tokens

### Tipos de error que detecta el Agente Lingüístico

| # | Tipo de error APA 7 | Ejemplo detectado |
|---|---|---|
| 1 | Cita sin año | `(García)` en lugar de `(García, 2021)` |
| 2 | Año sin autor | `(2021)` sin referencia al autor |
| 3 | Referencia sin DOI cuando aplica | Artículo de revista sin DOI |
| 4 | Sangría incorrecta en bibliografía | Sin sangría francesa de 0.5 pulgadas |
| 5 | Orden no alfabético en referencias | Referencias no ordenadas A→Z |
| 6 | Abreviatura incorrecta | `pag.` en lugar de `p.` |
| 7 | Et al. mal aplicado | `et al.` con menos de 3 autores |
| 8 | Título de artículo con mayúsculas | `"La Evaluación Del Aprendizaje"` |
| 9 | Nombre de revista sin cursiva | Nombre de revista sin formato itálico |
| 10 | URL sin fecha de acceso | URL sin `Recuperado de` o sin fecha |

---

## 4. Prototipo de Validación

Se ejecutó el Agente Lingüístico sobre un fragmento de 600 palabras de la tesis DIRESA con 8 errores APA introducidos deliberadamente:

| Errores introducidos | Errores detectados | Precisión |
|---|---|---|
| 8 | 7 | 87.5% |

El error no detectado fue el de URL sin fecha de acceso (el texto no incluía URL completa).

**Tiempo de ejecución:** 14.2 segundos — cumple el criterio de aceptación de ≤20s.

---

## 5. Esquema de Salida del Agente Lingüístico

```json
{
  "errores_apa": [
    {
      "tipo_error": "Cita sin año",
      "ubicacion_aprox": "Párrafo 3, sección Marco Teórico",
      "texto_original": "(García)",
      "sugerencia": "(García, 2021)"
    }
  ],
  "total_errores": 7,
  "reglas_validadas": 10,
  "tiempo_ms": 14200
}
```
