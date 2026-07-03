"""
human_loop_recalculo.py
═══════════════════════════════════════════════════════════════════════
Reemplaza la versión anterior del Human-Loop que volvía a llamar a
Langflow + MCP + Orquestador (una segunda evaluación completa e innecesaria).

Nueva filosofía:
  Los puntajes del análisis original (rigor_score, puntajes por agente,
  hallazgos cumple/observado/falta) son la BASE INMUTABLE.

  El docente solo puede:
    1. Marcar un hallazgo específico como "corregido" (el alumno ya lo arregló)
    2. Marcar un hallazgo como "descartado" (el agente se equivocó / alucinó)
    3. Ajustar manualmente el puntaje de un ítem específico (override puntual)
    4. Dejar todo igual y solo aprobar/rechazar con un comentario

  El Rigor Score SOLO se recalcula si el docente tocó algo medible
  (corrigió, descartó o ajustó puntaje de al menos 1 ítem).
  Si el docente solo escribió un comentario sin tocar ítems → se mantiene
  el rigor_score original sin recalcular nada.

No requiere Langflow. No requiere MCP. Es una función determinística
en Python — 100% reproducible y sin costo de tokens.
"""

import re
from typing import Optional


# ══════════════════════════════════════════════════════════════════════
# PARSEO DEL RESULTADO ORIGINAL (lo que ya generó el flujo Secuencial/Jerárquico)
# ══════════════════════════════════════════════════════════════════════

def parsear_resultado_original(texto_dictamen: str) -> dict:
    """
    Extrae del texto del Conciliador (===DICTAMEN=== etc.) los puntajes
    base inmutables y la lista de hallazgos por agente.

    Retorna:
    {
        "rigor_score_original": 0.48,
        "puntajes": {
            "metodologico": {"obtenido": 5.0, "maximo": 12.0, "porcentaje": 41.67},
            "tecnico":      {"obtenido": 8.4, "maximo": 12.0, "porcentaje": 70.0},
            "linguistico":  {"obtenido": 1.0, "maximo": 5.5,  "porcentaje": 18.18},
        },
        "hallazgos": {
            "metodologico": [{"id": "h1", "texto": "...", "estado": "falta"}, ...],
            "tecnico": [...],
            "linguistico": [...],
        }
    }
    """
    if not texto_dictamen:
        return {"rigor_score_original": None, "puntajes": {}, "hallazgos": {}}

    # Separar por bloques ===CLAVE===
    secciones = {"metodologico": "", "tecnico": "", "linguistico": "", "dictamen": ""}
    patron = re.compile(r'={2,3}\s*(METODOL[OÓ]GICO|TECNICO|LING[UÜ][IÍ]STICO|DICTAMEN)\s*={2,3}', re.IGNORECASE)
    matches = list(patron.finditer(texto_dictamen))

    if matches:
        for i, m in enumerate(matches):
            clave = m.group(1).upper()
            inicio = m.end()
            fin = matches[i + 1].start() if i + 1 < len(matches) else len(texto_dictamen)
            contenido = texto_dictamen[inicio:fin].strip()
            if 'METODOL' in clave:
                secciones['metodologico'] = contenido
            elif 'TECNI' in clave:
                secciones['tecnico'] = contenido
            elif 'LING' in clave:
                secciones['linguistico'] = contenido
            elif 'DICTA' in clave:
                secciones['dictamen'] = contenido
    else:
        secciones['dictamen'] = texto_dictamen

    bloque_dictamen = secciones['dictamen']

    # Rigor Score original
    rigor_match = re.search(r'RIGOR SCORE FINAL[:\s]*([0-9.]+)', bloque_dictamen, re.IGNORECASE)
    rigor_score_original = float(rigor_match.group(1)) if rigor_match else None

    # Puntajes por agente (formato: "Metodológico: X.XX / Y.YY = ZZ.Z%")
    def extraer_puntaje(nombre_regex):
        m = re.search(rf'{nombre_regex}[:\s]*([0-9.]+)\s*/\s*([0-9.]+)\s*=?\s*([0-9.]+)\s*%', bloque_dictamen, re.IGNORECASE)
        if not m:
            return None
        return {"obtenido": float(m.group(1)), "maximo": float(m.group(2)), "porcentaje": float(m.group(3))}

    puntajes = {
        "metodologico": extraer_puntaje(r'Metodol[oó]gico'),
        "tecnico":      extraer_puntaje(r'T[eé]cnico'),
        "linguistico":  extraer_puntaje(r'Ling[üu][ií]stico'),
    }

    # Hallazgos numerados con estado (CUMPLE / OBSERVADO / FALTA)
    def extraer_hallazgos(texto_seccion, prefijo):
        if not texto_seccion:
            return []
        hallazgos = []
        for linea in texto_seccion.split('\n'):
            linea = linea.strip()
            m = re.match(r'^\d+\.\s*(.+)', linea)
            if not m:
                continue
            contenido = m.group(1)
            estado = (
                'falta' if re.search(r'\(FALTA\)|FALTA\b', contenido, re.IGNORECASE) else
                'observado' if re.search(r'\(OBSERVADO\)|OBSERVADO\b', contenido, re.IGNORECASE) else
                'cumple' if re.search(r'\(CUMPLE\)|CUMPLE\b', contenido, re.IGNORECASE) else
                'neutro'
            )
            idx = len(hallazgos) + 1
            hallazgos.append({
                "id": f"{prefijo}-{idx}",
                "texto": contenido,
                "estado": estado,
            })
        return hallazgos

    hallazgos = {
        "metodologico": extraer_hallazgos(secciones['metodologico'], "met"),
        "tecnico":      extraer_hallazgos(secciones['tecnico'], "tec"),
        "linguistico":  extraer_hallazgos(secciones['linguistico'], "lin"),
    }

    return {
        "rigor_score_original": rigor_score_original,
        "puntajes": puntajes,
        "hallazgos": hallazgos,
        "secciones_texto": secciones,
    }


# ══════════════════════════════════════════════════════════════════════
# APLICAR OBSERVACIONES DEL DOCENTE
# ══════════════════════════════════════════════════════════════════════

PESOS_AGENTE = {"metodologico": 0.40, "tecnico": 0.40, "linguistico": 0.20}

# Valor que se asigna a un ítem cuando el docente lo marca "corregido"
# (se asume que ahora cumple al 100% de su peso individual)
PUNTOS_POR_ITEM_CORREGIDO_DEFAULT = None  # se calcula proporcional al total de ítems


def aplicar_observaciones_docente(
    resultado_original: dict,
    observaciones: list,
    comentario_libre: Optional[str] = None,
) -> dict:
    """
    Aplica las observaciones puntuales del docente sobre los puntajes base.

    observaciones: lista de dicts con esta forma:
        {
            "hallazgo_id": "met-1",       # ID del hallazgo (de parsear_resultado_original)
            "accion": "corregir" | "descartar" | "ajustar_puntaje" | "mantener",
            "puntaje_nuevo": 1.5,          # solo si accion == "ajustar_puntaje"
            "comentario": "El alumno ya agregó la hipótesis en la versión final"
        }

    Si `observaciones` está vacío (el docente solo dejó un comentario_libre
    sin tocar ningún ítem), el rigor_score se mantiene IGUAL al original.

    Retorna:
    {
        "rigor_score_original": 0.48,
        "rigor_score_final": 0.55,         # solo cambia si hubo observaciones
        "recalculado": True/False,
        "puntajes_originales": {...},
        "puntajes_ajustados": {...},
        "cambios_aplicados": [
            {"hallazgo_id": "met-1", "accion": "corregir", "delta_puntos": 1.0, "agente": "metodologico"}
        ],
        "comentario_docente": "..."
    }
    """
    rigor_original = resultado_original.get("rigor_score_original")
    puntajes_orig  = resultado_original.get("puntajes", {})
    hallazgos      = resultado_original.get("hallazgos", {})

    # Sin observaciones puntuales → NO se recalcula nada
    if not observaciones:
        return {
            "rigor_score_original": rigor_original,
            "rigor_score_final": rigor_original,
            "recalculado": False,
            "puntajes_originales": puntajes_orig,
            "puntajes_ajustados": puntajes_orig,
            "cambios_aplicados": [],
            "comentario_docente": comentario_libre or "",
            "motivo": "El docente no modificó ningún ítem específico — se mantiene el Rigor Score original.",
        }

    # Mapear cada hallazgo_id a su agente (met-1 → metodologico, etc.)
    def agente_de_id(hallazgo_id: str) -> Optional[str]:
        if hallazgo_id.startswith("met"):
            return "metodologico"
        if hallazgo_id.startswith("tec"):
            return "tecnico"
        if hallazgo_id.startswith("lin"):
            return "linguistico"
        return None

    # Construir lookup de hallazgos por ID para validar existencia
    lookup_hallazgos = {}
    for agente, lista in hallazgos.items():
        for h in lista:
            lookup_hallazgos[h["id"]] = h

    # Copia mutable de los puntajes
    puntajes_ajustados = {
        ag: dict(p) if p else {"obtenido": 0.0, "maximo": 0.0, "porcentaje": 0.0}
        for ag, p in puntajes_orig.items()
    }

    cambios_aplicados = []

    for obs in observaciones:
        hallazgo_id = obs.get("hallazgo_id")
        accion      = obs.get("accion", "mantener")

        if accion == "mantener" or hallazgo_id not in lookup_hallazgos:
            continue

        agente = agente_de_id(hallazgo_id)
        if not agente or agente not in puntajes_ajustados:
            continue

        hallazgo = lookup_hallazgos[hallazgo_id]
        puntaje_agente = puntajes_ajustados[agente]
        maximo = puntaje_agente.get("maximo", 0.0)

        # Estimar el "peso individual" del ítem: maximo_agente / num_hallazgos_de_ese_agente
        num_hallazgos_agente = max(1, len(hallazgos.get(agente, [])))
        peso_item_estimado = maximo / num_hallazgos_agente if maximo > 0 else 0.0

        delta = 0.0

        if accion == "corregir":
            # El hallazgo estaba en FALTA/OBSERVADO y el docente confirma que ya se corrigió
            if hallazgo["estado"] in ("falta", "observado"):
                delta = peso_item_estimado  # sube el puntaje en el peso estimado del ítem
                hallazgo["estado"] = "cumple"

        elif accion == "descartar":
            # El docente determina que el agente se equivocó (falsa alarma / alucinación)
            # Se otorga el puntaje completo del ítem como si siempre hubiera cumplido
            if hallazgo["estado"] in ("falta", "observado"):
                delta = peso_item_estimado
                hallazgo["estado"] = "cumple"

        elif accion == "ajustar_puntaje":
            puntaje_nuevo = obs.get("puntaje_nuevo")
            if puntaje_nuevo is not None:
                delta = float(puntaje_nuevo) - 0.0  # se asume el ítem partía de 0 (estaba en falta/observado)

        if delta != 0.0:
            puntaje_agente["obtenido"] = round(min(maximo, puntaje_agente["obtenido"] + delta), 4)
            puntaje_agente["porcentaje"] = round(
                (puntaje_agente["obtenido"] / maximo * 100) if maximo > 0 else 0.0, 2
            )
            cambios_aplicados.append({
                "hallazgo_id": hallazgo_id,
                "agente": agente,
                "accion": accion,
                "delta_puntos": round(delta, 4),
                "comentario": obs.get("comentario", ""),
                "texto_hallazgo": hallazgo["texto"][:120],
            })

    # Recalcular Rigor Score solo si hubo cambios reales
    if cambios_aplicados:
        rigor_final = sum(
            (puntajes_ajustados.get(ag, {}).get("porcentaje", 0) / 100) * peso
            for ag, peso in PESOS_AGENTE.items()
        )
        rigor_final = round(rigor_final, 3)
        recalculado = True
    else:
        rigor_final = rigor_original
        recalculado = False

    return {
        "rigor_score_original": rigor_original,
        "rigor_score_final": rigor_final,
        "recalculado": recalculado,
        "puntajes_originales": puntajes_orig,
        "puntajes_ajustados": puntajes_ajustados,
        "cambios_aplicados": cambios_aplicados,
        "comentario_docente": comentario_libre or "",
        "hallazgos_actualizados": hallazgos,
    }


def determinar_dictamen(rigor_score: Optional[float]) -> str:
    """Misma lógica de corte que usa el Conciliador en Langflow."""
    if rigor_score is None:
        return "EN REVISIÓN"
    if rigor_score >= 0.80:
        return "APROBADO"
    if rigor_score >= 0.60:
        return "APROBADO CON OBSERVACIONES"
    return "RECHAZADO"


def generar_dictamen_human_loop(
    resultado_original: dict,
    observaciones: list,
    comentario_libre: Optional[str],
    decision_docente: str,
    nombre_docente: str = "Docente Asesor",
) -> dict:
    """
    Función principal — reemplaza la llamada completa a Langflow + MCP.

    Combina el recálculo de puntajes con la decisión administrativa final
    del docente (aprobado / aprobado_con_cambios / rechazado), que SIEMPRE
    tiene la última palabra independientemente del Rigor Score.
    """
    calculo = aplicar_observaciones_docente(resultado_original, observaciones, comentario_libre)

    dictamen_sugerido = determinar_dictamen(calculo["rigor_score_final"])

    return {
        **calculo,
        "dictamen_sugerido_por_score": dictamen_sugerido,
        "decision_final_docente": decision_docente,
        "nombre_docente": nombre_docente,
        "nota": (
            "El docente tiene la autoridad final. Si su decisión difiere del "
            "dictamen sugerido por el Rigor Score, esa discrepancia queda "
            "registrada para trazabilidad académica."
        ) if dictamen_sugerido.upper().replace(" ", "_") != decision_docente.upper().replace(" ", "_") else "",
    }
