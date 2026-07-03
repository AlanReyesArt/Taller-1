# DO-02 — Matriz de Roles y Prompts de Agentes

**Proyecto:** Sistema de Deliberación Multiagente para Análisis de Tesis UPAO  
**Épica:** EP-02 — Módulo de Crítica y Rigor Científico  
**Sprint:** 2 | **Fecha:** 06/06/2026

---

## 1. Tabla de Roles de Agentes

| Agente | Rol en el Sistema | Criterio de Evaluación Principal | Archivo de Prompt |
|---|---|---|---|
| **Metodológico** | Primer evaluador en la cadena. Analiza la coherencia estructural de la tesis: problema, objetivos, hipótesis y diseño de investigación. | Criterios de Kerlinger (1979): coherencia interna, validez lógica entre componentes metodológicos | TA-01_agente_metodologico.md |
| **Técnico** | Evaluador escéptico. Cuestiona la alineación entre el problema de investigación y la solución tecnológica propuesta. Genera contra-argumentaciones. | Viabilidad técnica, alineación problema-solución, justificación de la arquitectura tecnológica | TA-02_agente_tecnico.md |
| **Lingüístico** | Auditor formal. Detecta errores de citación APA 7, redacción académica y cumplimiento de la Guía UPAO. | Normas APA 7 (Capítulos 8-9), Guía de Productos Acreditables UPAO, redacción en voz pasiva académica | TA-04_agente_linguistico.md |
| **Consenso** | Juez final. Recibe los informes de los 3 agentes, calcula el Rigor Score ponderado y emite el dictamen oficial. | Rigor Score = Met×0.40 + Téc×0.35 + Ling×0.25. Umbral aprobación: ≥0.80 | TA-05_agente_consenso_rigor_score.md |

---

## 2. Esquemas JSON de Salida por Agente

### Agente Metodológico
```json
{
  "agente": "Metodológico",
  "secciones": [
    {
      "seccion": "Planteamiento del Problema",
      "estado": "cumple|observado|falta",
      "observacion": "descripción del hallazgo",
      "criterio_kerlinger": "criterio aplicado"
    }
  ],
  "score_metodologico": 0.85,
  "fortalezas": ["..."],
  "observaciones_criticas": ["..."]
}
```

### Agente Técnico
```json
{
  "agente": "Técnico",
  "argumentos": [
    {
      "argumento": "contra-argumentación concreta",
      "criterio_kerlinger": "criterio de Kerlinger referenciado",
      "severidad": "alta|media|baja",
      "seccion_afectada": "nombre de la sección"
    }
  ],
  "score_tecnico": 0.75,
  "decision": "aprobado|observado|rechazado"
}
```

### Agente Lingüístico
```json
{
  "agente": "Lingüístico",
  "errores_detectados": [
    {
      "tipo_error": "tipo según las 10 reglas APA",
      "ubicacion_aprox": "sección o párrafo",
      "fragmento": "texto con error (máx. 100 chars)",
      "sugerencia_correccion": "cómo corregirlo",
      "severidad": "alta|media|baja"
    }
  ],
  "total_errores": 0,
  "score_linguistico": 0.90,
  "cumple_minimo_apa": true
}
```

### Agente de Consenso
```json
{
  "agente": "Consenso",
  "scores": {
    "metodologico": 0.85,
    "tecnico": 0.75,
    "linguistico": 0.90,
    "rigor_score": 0.84
  },
  "decision": "aprobado|observado|rechazado",
  "resumen_debate": "síntesis ≤200 palabras",
  "observaciones_criticas": ["..."],
  "fortalezas": ["..."],
  "consenso_agentes": {
    "metodologico": "aprobado",
    "tecnico": "observado",
    "linguistico": "aprobado",
    "acuerdo_mayoritario": true
  }
}
```

---

## 3. Errores Tipificados por Agente

### Agente Metodológico — Errores que detecta
| Código | Error | Severidad |
|---|---|---|
| M-01 | Hipótesis no derivada del problema central | Alta |
| M-02 | Objetivos específicos no alineados con el objetivo general | Alta |
| M-03 | Variables no operacionalizadas | Alta |
| M-04 | Diseño de investigación no justificado | Media |
| M-05 | Marco teórico sin relación con el problema | Media |
| M-06 | Falta de antecedentes de investigación | Media |
| M-07 | Justificación insuficiente | Baja |
| M-08 | Limitaciones no declaradas | Baja |

### Agente Técnico — Errores que detecta
| Código | Error | Severidad |
|---|---|---|
| T-01 | Solución tecnológica no resuelve el problema planteado | Alta |
| T-02 | Arquitectura tecnológica sin justificación técnica | Alta |
| T-03 | No se compara con soluciones existentes | Media |
| T-04 | Métricas de evaluación no definidas | Media |
| T-05 | Tecnologías propuestas desactualizadas | Media |
| T-06 | Prototipo no validado con usuarios reales | Baja |

### Agente Lingüístico — Errores que detecta
| Código | Error | Regla APA 7 | Severidad |
|---|---|---|---|
| L-01 | Cita sin año | §8.11 | Alta |
| L-02 | Año sin autor | §8.11 | Alta |
| L-03 | Referencia sin DOI | §9.34 | Alta |
| L-04 | Sangría incorrecta | §9.43 | Media |
| L-05 | Orden no alfabético | §9.44 | Media |
| L-06 | Cita directa sin página | §8.25 | Alta |
| L-07 | Et al. incorrecto | §8.17 | Media |
| L-08 | Abreviatura no definida | §6.25 | Baja |
| L-09 | Redacción en primera persona | §4.16 | Media |
| L-10 | Tabla/figura sin formato | §7.4 | Baja |

---

## 4. Orden de Activación por Arquitectura

| Arquitectura | Orden de Agentes | Propósito |
|---|---|---|
| **Secuencial (Arq. 1)** | Met → Téc → Ling → Consenso | Revisión rápida en cadena |
| **Red / Debate (Arq. 3)** | Met ↔ Téc (3 rondas) → Consenso | Debate circular con contra-argumentación |
| **Jerárquica (Arq. 4)** | Met + Téc + Ling en paralelo → Consenso | Veredicto jerárquico eficiente |
| **Human-in-the-Loop (Arq. 2)** | Secuencial → Pausa → Docente → Consenso | Validación con intervención humana |
