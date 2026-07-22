"""
langflow_service.py — Integración Langflow

Pipeline completo:
  1. Extrae/segmenta PDF.
  2. Orquestador Python detecta diseño + sublínea de investigación.
  3. Llama al MCP de Rúbricas para obtener el contenido de M1-M5, T1-T11, L1.
  4. Inyecta las rúbricas como tweaks en los Prompt Templates del flujo.
  5. Ejecuta el flujo Langflow con el texto + rúbricas inyectadas.
"""

import httpx
import hashlib
import time
import os
import re
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

LANGFLOW_URL = os.getenv("LANGFLOW_URL", "http://localhost:7860")
LANGFLOW_API_KEY = os.getenv("LANGFLOW_API_KEY", "")
LANGFLOW_TIMEOUT = int(os.getenv("LANGFLOW_TIMEOUT", "600"))

FLOW_ID_SECUENCIAL = os.getenv("LANGFLOW_FLOW_ID_SECUENCIAL", "")
FLOW_ID_JERARQUICO = os.getenv("LANGFLOW_FLOW_ID_JERARQUICO", "")
FLOW_ID_HUMAN_LOOP = os.getenv("LANGFLOW_FLOW_ID_HUMAN_LOOP", "")
FLOW_ID_RED = os.getenv("LANGFLOW_FLOW_ID_RED", "")

HUMAN_LOOP_TEXT_INPUT_NODE = os.getenv("HUMAN_LOOP_TEXT_INPUT_NODE", "TextInput-uCrOd")

MAX_CHARS = int(os.getenv("LANGFLOW_MAX_CHARS", "80000"))


def calcular_hash(filepath: str) -> str:
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if LANGFLOW_API_KEY:
        headers["x-api-key"] = LANGFLOW_API_KEY
    else:
        print("⚠️ LANGFLOW_API_KEY no configurada en backend/.env")
    return headers


async def verificar_langflow() -> tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{LANGFLOW_URL}/health")
            if r.status_code == 200:
                return True, "ok"
            return False, f"HTTP {r.status_code}"
    except httpx.ConnectError:
        return False, f"No se puede conectar a Langflow en {LANGFLOW_URL}"
    except Exception as e:
        return False, str(e)


def _extraer_respuesta_langflow(data: dict) -> str:
    fragmentos = []

    try:
        for salida in data.get("outputs", []):
            for item in salida.get("outputs", []):
                results = item.get("results", {})

                msg = results.get("message", {})
                if isinstance(msg, dict):
                    txt = msg.get("text") or msg.get("data", {}).get("text")
                    if txt and str(txt).strip():
                        fragmentos.append(str(txt).strip())
                        continue

                txt = results.get("text", "")
                if txt and str(txt).strip():
                    fragmentos.append(str(txt).strip())
                    continue

                art = item.get("artifacts", {}).get("message", "")
                if art and str(art).strip():
                    fragmentos.append(str(art).strip())

    except Exception as e:
        print(f"⚠️ Error extrayendo respuesta de Langflow: {e}")

    if fragmentos:
        resultado = "\n\n".join(fragmentos)
        print(f"📤 Texto extraído de Langflow: {len(resultado)} chars ({len(fragmentos)} bloque(s))")
        return resultado

    print("⚠️ No se pudo extraer texto estructurado. Devolviendo JSON crudo.")
    return str(data)


async def _run_flow(flow_id: str, input_value: str, tweaks: Optional[dict] = None) -> dict:
    if not flow_id:
        raise ValueError("Flow ID vacío. Configura el ID del flujo en backend/.env")

    texto_enviado = input_value[:MAX_CHARS]

    if len(input_value) > MAX_CHARS:
        print(f"⚠️ Texto truncado: {len(input_value)} → {MAX_CHARS} chars")

    payload = {
        "input_value": texto_enviado,
        "input_type": "chat",
        "output_type": "chat",
    }

    if tweaks:
        payload["tweaks"] = tweaks

    print(f"🚀 Run flujo [{flow_id[:8]}...] — {len(texto_enviado)} chars en ChatInput")

    inicio = time.time()

    async with httpx.AsyncClient(timeout=LANGFLOW_TIMEOUT) as client:
        response = await client.post(
            f"{LANGFLOW_URL}/api/v1/run/{flow_id}",
            json=payload,
            headers=_headers(),
        )

        if response.status_code != 200:
            print(f"❌ Error Langflow {response.status_code}: {response.text[:500]}")

        response.raise_for_status()

    latencia_ms = int((time.time() - inicio) * 1000)
    texto_respuesta = _extraer_respuesta_langflow(response.json())

    print(f"✅ OK — {latencia_ms}ms — {len(texto_respuesta)} chars en respuesta")

    return {
        "texto": texto_respuesta,
        "latencia_ms": latencia_ms,
        "raw_data": response.json(),
    }


async def _ejecutar_flujo(nombre: str, flow_id: str, input_value: str, tweaks: Optional[dict] = None) -> dict:
    if not flow_id:
        return {
            "texto_crudo": "",
            "latencia_ms": 0,
            "exito": False,
            "error": f"Flow ID de '{nombre}' no configurado en backend/.env",
        }

    try:
        resultado = await _run_flow(flow_id, input_value, tweaks)

        return {
            "texto_crudo": resultado["texto"],
            "latencia_ms": resultado["latencia_ms"],
            "exito": True,
            "error": None,
            "raw_data": resultado.get("raw_data", {}),
        }

    except httpx.TimeoutException:
        msg = f"Timeout ({LANGFLOW_TIMEOUT}s) en flujo {nombre}"
        print(f"❌ {msg}")

        return {
            "texto_crudo": "",
            "latencia_ms": 0,
            "exito": False,
            "error": msg,
        }

    except Exception as e:
        print(f"❌ Error en flujo {nombre}: {e}")

        return {
            "texto_crudo": "",
            "latencia_ms": 0,
            "exito": False,
            "error": str(e),
        }


def _extraer_texto_pdf(filepath: str, rapido: bool = False) -> str:
    """
    Extrae el PDF y construye el input compacto para Langflow.

    El flujo de Langflow sigue usando Chat Input.
    No se envía la tesis completa en bruto.
    Se envía un JSON segmentado.
    """
    from pdf_extractor import extraer_texto_pdf, construir_input_langflow, construir_input_langflow_rapido

    datos = extraer_texto_pdf(filepath)
    texto_langflow = construir_input_langflow_rapido(datos) if rapido else construir_input_langflow(datos)
    print("\n" + "="*80)
    print("TEXTO ENVIADO A LANGFLOW")
    print("="*80)
    print(texto_langflow[:12000])
    print("="*80)

    if not texto_langflow.strip():
        raise ValueError("El PDF no contiene texto extraíble o no se pudo segmentar")

    print(
        f"📄 PDF segmentado para Langflow: "
        f"{datos.get('total_paginas', 0)} páginas, "
        f"{datos.get('total_palabras', 0)} palabras, "
        f"{len(texto_langflow)} chars enviados"
    )

    return texto_langflow


def _extraer_json_de_texto(texto: str) -> Optional[dict]:
    """Extrae de forma tolerante un objeto JSON contenido en la respuesta del LLM."""
    import json
    import re

    if not texto:
        return None
    limpio = str(texto).strip()
    if limpio.startswith("```"):
        m = re.search(r"```(?:json)?\s*([\s\S]*?)(?:```|$)", limpio, re.IGNORECASE)
        if m:
            limpio = m.group(1).strip()
    ini = limpio.find("{")
    fin = limpio.rfind("}")
    
    if ini < 0:
        return None
        
    if fin < ini:
        # Intento de cierre forzado para JSONs truncados
        limpio = limpio + "}"
        fin = limpio.rfind("}")

    try:
        dato = json.loads(limpio[ini:fin + 1])
        return dato if isinstance(dato, dict) else None
    except json.JSONDecodeError:
        # Intento básico de limpieza (comas extra, etc.)
        try:
            parcheado = re.sub(r',(\s*[}\]])', r'\1', limpio[ini:fin + 1])
            dato = json.loads(parcheado)
            return dato if isinstance(dato, dict) else None
        except Exception:
            pass
        return None
    except Exception:
        return None


def _normalizar_estado_criterio(valor: str) -> str:
    estado = str(valor or "").strip().lower().replace(" ", "_")
    equivalencias = {
        "parcial": "observado",
        "cumple_parcialmente": "observado",
        "observación": "observado",
        "observacion": "observado",
        "no_cumple": "no_cumple",
        "no-cumple": "no_cumple",
        "falta": "no_cumple",
        "incumple": "no_cumple",
        "no_evaluable": "no_evaluable",
        "no_aplica": "no_evaluable",
        "n/a": "no_evaluable",
    }
    estado = equivalencias.get(estado, estado)
    return estado if estado in {"cumple", "observado", "no_cumple", "no_evaluable"} else "error_evaluacion"


def _normalizar_reporte_agente(reporte: Optional[dict], agente: str) -> Optional[dict]:
    if not isinstance(reporte, dict):
        return None
    items = reporte.get("criterios")
    if not isinstance(items, list):
        items = reporte.get("evaluaciones")
    if isinstance(items, list):
        normalizados = []
        for item in items:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            normalizados.append({
                "id": str(item.get("id", "")).strip().upper(),
                "estado": _normalizar_estado_criterio(item.get("estado")),
                "evidencia": str(item.get("evidencia") or "").strip(),
                "ubicacion": str(item.get("ubicacion") or "").strip(),
                "justificacion": str(item.get("justificacion") or item.get("observacion") or "").strip(),
                "confianza": str(item.get("confianza") or "media").strip().lower(),
            })
        reporte = dict(reporte)
        reporte["criterios"] = normalizados
        # Alias temporal para componentes antiguos del frontend.
        reporte["evaluaciones"] = normalizados
    reporte.setdefault("agente", agente)
    return reporte


def _extraer_todos_los_outputs(data: dict) -> dict:
    """Extrae y clasifica las respuestas JSON de todos los agentes de un flujo."""
    outputs_raw = []
    try:
        for salida in data.get("outputs", []):
            for item in salida.get("outputs", []):
                results = item.get("results", {})
                msg = results.get("message", {})
                txt = ""
                if isinstance(msg, dict):
                    txt = msg.get("text", "") or msg.get("data", {}).get("text", "")
                txt = txt or results.get("text", "") or item.get("artifacts", {}).get("message", "")
                if txt and str(txt).strip():
                    outputs_raw.append(str(txt).strip())
    except Exception as exc:
        print(f"⚠️ No se pudieron recorrer todos los outputs: {exc}")

    resultado = {
        "metodologico": None,
        "tecnico": None,
        "linguistico": None,
        "consenso": None,
        "raw": outputs_raw,
        "errores_parseo": [],
    }

    for indice, texto in enumerate(outputs_raw):
        parsed = _extraer_json_de_texto(texto)
        if not parsed:
            resultado["errores_parseo"].append({"output": indice, "motivo": "json_invalido"})
            continue
        agente = str(parsed.get("agente") or "").strip().lower()
        tipo = str(parsed.get("tipo_resultado") or "").strip().lower()
        if agente in {"metodologico", "tecnico", "linguistico"}:
            resultado[agente] = _normalizar_reporte_agente(parsed, agente)
        elif agente in {"consenso", "juez"} or tipo in {"diagnostico_preliminar", "dictamen_jerarquico"}:
            resultado["consenso"] = parsed

    # Algunos flujos solo exponen el último output.
    if resultado["consenso"] is None and len(outputs_raw) == 1:
        parsed = _extraer_json_de_texto(outputs_raw[0])
        if parsed:
            resultado["consenso"] = parsed

    return resultado



# ══════════════════════════════════════════════════════════════════════
# Utilidades de rúbricas para mostrar ítem por ítem en el Veredicto
# ══════════════════════════════════════════════════════════════════════

def _parsear_items_rubrica_md(rubrica_md: str) -> list[dict]:
    """Convierte una rúbrica Markdown en lista de ítems ID-XX/Descripción/Puntaje."""
    if not rubrica_md:
        return []
    patron = re.compile(
        r'(ID-\d+)\s*\n\s*Descripci[oó]n:\s*(.*?)\s*\n\s*Puntaje:\s*([0-9.]+)',
        re.IGNORECASE | re.DOTALL,
    )
    items = []
    for item_id, desc, pts in patron.findall(rubrica_md):
        desc_limpia = re.sub(r'\s+', ' ', desc).strip()
        try:
            pts_float = float(pts)
        except Exception:
            pts_float = 0.0
        items.append({
            "id": item_id.strip(),
            "descripcion": desc_limpia,
            "puntos_max": pts_float,
        })
    return items


def _extraer_bloque(texto: str, titulo: str) -> str:
    """Extrae una sección ===TITULO=== del texto del juez jerárquico."""
    if not texto:
        return ""
    normal = {
        "metodologica": r"METODOL[OÓ]GIC[OA]|METODOLOGICO|METODOLOGICA",
        "tecnica": r"T[ÉE]CNIC[OA]|TECNICO|TECNICA",
        "linguistica": r"LING[UÜ][IÍ]STIC[OA]|LINGUISTICO|LINGUISTICA",
    }
    key = titulo.lower()
    pat = normal.get(key, titulo)
    re_sec = re.compile(
        rf'===\s*(?:{pat})\s*===([\s\S]*?)(?====\s*[A-ZÁÉÍÓÚÑ ]+\s*===|$)',
        re.IGNORECASE,
    )
    m = re_sec.search(texto)
    return m.group(1).strip() if m else ""


def _expandir_rangos_ids(texto: str) -> set[str]:
    """Extrae IDs sueltos y rangos tipo ID-01 a ID-60."""
    ids = {m.upper() for m in re.findall(r'ID-\d{1,3}', texto or '', flags=re.IGNORECASE)}

    for a, b in re.findall(r'ID-(\d{1,3})\s*(?:a|al|hasta|-)\s*ID-(\d{1,3})', texto or '', flags=re.IGNORECASE):
        ini, fin = int(a), int(b)
        if ini <= fin and fin - ini <= 300:
            ancho = max(len(a), len(b), 2)
            for n in range(ini, fin + 1):
                ids.add(f"ID-{n:0{ancho}d}")
    return ids


def _ids_en_estado(bloque: str, encabezados: list[str]) -> set[str]:
    """
    Obtiene IDs SOLO debajo de encabezados exactos como:
    Cumplidos:, No cumplidos:, Observados:.

    Importante: antes fallaba porque "Cumplidos" también matcheaba dentro de
    "No cumplidos" y marcaba como ✅ los criterios que estaban en ❌.
    """
    if not bloque:
        return set()

    # Encabezados posibles que delimitan subsecciones dentro del bloque del agente.
    delimitadores = [
        "Rúbrica utilizada", "Rubrica utilizada",
        "Puntaje metodológico", "Puntaje tecnico", "Puntaje técnico", "Puntaje lingüístico", "Puntaje linguistico",
        "Cumplidos", "Cumple",
        "No cumplidos", "No cumple", "Incumplidos", "Faltantes", "Falta",
        "Observados", "Observado", "Parciales", "Parcial",
        "Fortalezas", "Debilidades", "Recomendaciones",
        "VEREDICTO", "RIGOR SCORE", "===",
    ]

    ids = set()
    heads = "|".join(re.escape(h) for h in encabezados)
    stops = "|".join(re.escape(h) for h in delimitadores)

    # Debe aparecer al inicio de línea. Así "No cumplidos" ya no activa "Cumplidos".
    patron = re.compile(
        rf'(?im)^\s*(?:{heads})\s*:?\s*$([\s\S]*?)(?=^\s*(?:{stops})\s*:?\s*$|^\s*===|\Z)',
    )

    # Variante para encabezados y contenido en la misma línea:
    # Cumplidos: ID-01, ID-02
    patron_misma_linea = re.compile(
        rf'(?im)^\s*(?:{heads})\s*:\s*(.*?)(?=\n\s*(?:{stops})\s*:|\n\s*===|\Z)',
        re.DOTALL,
    )

    for pat in (patron, patron_misma_linea):
        for m in pat.finditer(bloque):
            contenido = m.group(1) or ""
            # "Ninguno" no debe aportar IDs aunque luego el texto tenga otros IDs en otra sección.
            if re.search(r'\bningun[oa]s?\b|\(\s*ningun[oa]\s*\)', contenido, re.IGNORECASE):
                continue
            ids.update(_expandir_rangos_ids(contenido))

    return ids


def _construir_rubrica_evaluada(
    rubrica_id: str,
    rubrica_md: str,
    reporte_agente: Optional[dict] = None,
    bloque_evaluacion: str = "",
) -> dict:
    """Combina la rúbrica MCP con la evaluación JSON del agente.

    Un criterio ausente nunca se convierte silenciosamente en ``observado``.
    Se marca como ``error_evaluacion`` para hacerlo visible y evitar un 50 % ficticio.
    """
    items_base = _parsear_items_rubrica_md(rubrica_md)
    reporte = _normalizar_reporte_agente(reporte_agente, str((reporte_agente or {}).get("agente") or ""))
    por_id = {
        str(i.get("id") or "").upper(): i
        for i in (reporte or {}).get("criterios", [])
        if isinstance(i, dict) and i.get("id")
    }

    # Compatibilidad limitada con respuestas planas antiguas.
    cumplidos = _ids_en_estado(bloque_evaluacion, ["Cumplidos", "Cumple"]) if not por_id else set()
    no_cumplidos = _ids_en_estado(bloque_evaluacion, ["No cumplidos", "No cumple", "Incumplidos"]) if not por_id else set()
    observados = _ids_en_estado(bloque_evaluacion, ["Observados", "Observado", "Parciales", "Parcial"]) if not por_id else set()

    evaluaciones = []
    ids_esperados = {item["id"].upper() for item in items_base}
    duplicados = []
    ids_vistos = []
    for item in (reporte or {}).get("criterios", []):
        iid = str(item.get("id") or "").upper()
        if iid in ids_vistos and iid not in duplicados:
            duplicados.append(iid)
        ids_vistos.append(iid)

    for item in items_base:
        iid = item["id"].upper()
        pts = float(item.get("puntos_max") or 0.0)
        evaluado = por_id.get(iid)
        if evaluado:
            estado = _normalizar_estado_criterio(evaluado.get("estado"))
            evidencia = evaluado.get("evidencia") or ""
            ubicacion = evaluado.get("ubicacion") or ""
            observacion = evaluado.get("justificacion") or ""
            confianza = evaluado.get("confianza") or "media"
        elif iid in no_cumplidos:
            estado, evidencia, ubicacion, observacion, confianza = "no_cumple", "", "", "Marcado como no cumplido en la respuesta del comité.", "baja"
        elif iid in cumplidos:
            estado, evidencia, ubicacion, observacion, confianza = "cumple", "", "", "Marcado como cumplido en la respuesta del comité.", "baja"
        elif iid in observados:
            estado, evidencia, ubicacion, observacion, confianza = "observado", "", "", "Marcado como observado en la respuesta del comité.", "baja"
        else:
            estado, evidencia, ubicacion = "error_evaluacion", "", ""
            observacion = "El agente no devolvió este criterio. Se requiere reintento o revisión humana."
            confianza = "baja"

        if estado == "cumple":
            puntos_obtenidos = pts
        elif estado == "observado":
            puntos_obtenidos = pts * 0.5
        else:
            puntos_obtenidos = 0.0

        evaluaciones.append({
            "id": item["id"],
            "descripcion": item["descripcion"],
            "estado": estado,
            "puntos_max": pts,
            "puntos_obtenidos": round(puntos_obtenidos, 4),
            "evidencia": evidencia,
            "ubicacion": ubicacion,
            "observacion": observacion,
            "confianza": confianza,
        })

    no_evaluables = [i for i in evaluaciones if i["estado"] == "no_evaluable"]
    errores = [i for i in evaluaciones if i["estado"] == "error_evaluacion"]
    max_total = sum(i["puntos_max"] for i in evaluaciones)
    max_aplicable = sum(i["puntos_max"] for i in evaluaciones if i["estado"] != "no_evaluable")
    obtenido = sum(i["puntos_obtenidos"] for i in evaluaciones)

    return {
        "rubrica_id": rubrica_id,
        "total_items": len(evaluaciones),
        "puntaje_maximo": round(max_total, 4),
        "puntaje_maximo_aplicable": round(max_aplicable, 4),
        "puntaje_obtenido_estimado": round(obtenido, 4),
        "items_no_evaluables": len(no_evaluables),
        "items_con_error": len(errores),
        "ids_duplicados": duplicados,
        "ids_desconocidos": sorted(set(por_id) - ids_esperados),
        "contrato_valido": not errores and not duplicados,
        "items": evaluaciones,
    }


def _construir_rubricas_detalle(datos_mcp: dict | None, agentes: Optional[dict] = None, texto_veredicto: str = "") -> dict:
    """Construye las tres rúbricas completas usando prioritariamente JSON estructurado."""
    if not datos_mcp:
        return {}
    agentes = agentes or {}
    return {
        "metodologica": _construir_rubrica_evaluada(
            datos_mcp.get("rubrica_metodologica_id", "M?"),
            datos_mcp.get("rubrica_metodologica", ""),
            agentes.get("metodologico"),
            _extraer_bloque(texto_veredicto, "metodologica"),
        ),
        "tecnica": _construir_rubrica_evaluada(
            datos_mcp.get("rubrica_tecnica_id", "T?"),
            datos_mcp.get("rubrica_tecnica", ""),
            agentes.get("tecnico"),
            _extraer_bloque(texto_veredicto, "tecnica"),
        ),
        "linguistica": _construir_rubrica_evaluada(
            datos_mcp.get("rubrica_linguistica_id", "L1"),
            datos_mcp.get("rubrica_linguistica", ""),
            agentes.get("linguistico"),
            _extraer_bloque(texto_veredicto, "linguistica"),
        ),
    }


def _calcular_metricas_oficiales(rubricas_detalle: dict) -> dict:
    """Calcula puntajes, Rigor Score y veredicto exclusivamente en backend."""
    pesos = {"metodologica": 0.40, "tecnica": 0.35, "linguistica": 0.25}
    dimensiones = {}
    rigor = 0.0
    contrato_valido = True

    for clave, peso in pesos.items():
        rubrica = (rubricas_detalle or {}).get(clave) or {}
        maximo_total = float(rubrica.get("puntaje_maximo") or 0.0)
        maximo_aplicable = float(rubrica.get("puntaje_maximo_aplicable") or maximo_total)
        obtenido_bruto = round(sum(float(i.get("puntos_obtenidos") or 0.0) for i in rubrica.get("items", [])), 4)
        porcentaje = (obtenido_bruto / maximo_aplicable) if maximo_aplicable > 0 else 0.0
        # Se mantiene la escala institucional original (10/7/3), aun cuando
        # existan criterios no evaluables excluidos del denominador.
        obtenido_escalado = round(porcentaje * maximo_total, 4)
        valido_dimension = bool(rubrica.get("contrato_valido", False))
        contrato_valido = contrato_valido and valido_dimension
        dimensiones[clave] = {
            "puntaje_obtenido": obtenido_escalado,
            "puntaje_obtenido_bruto": obtenido_bruto,
            "puntaje_maximo": round(maximo_total, 4),
            "puntaje_maximo_aplicable": round(maximo_aplicable, 4),
            "porcentaje": round(porcentaje, 4),
            "peso": peso,
            "items_no_evaluables": int(rubrica.get("items_no_evaluables") or 0),
            "items_con_error": int(rubrica.get("items_con_error") or 0),
            "contrato_valido": valido_dimension,
        }
        rigor += porcentaje * peso

    rigor = round(max(0.0, min(1.0, rigor)), 4)
    if rigor >= 0.80:
        veredicto = "APROBADO"
    elif rigor >= 0.60:
        veredicto = "APROBADO CON OBSERVACIONES"
    else:
        veredicto = "RECHAZADO"

    return {
        "dimensiones": dimensiones,
        "rigor_score": rigor,
        "rigor_porcentaje": round(rigor * 100, 2),
        "rigor_sobre_10": round(rigor * 10, 2),
        "veredicto_oficial": veredicto,
        "pesos": pesos,
        "fuente": "backend_determinista",
        "contrato_valido": contrato_valido,
        "advertencia_contrato": None if contrato_valido else "Uno o más agentes omitieron criterios o devolvieron una estructura inválida.",
    }


def _anexar_resultado_oficial(texto: str, metricas: dict) -> str:
    """Elimina scores/veredictos ambiguos del LLM y agrega el resultado oficial."""
    texto = texto or ""
    texto = re.sub(r'(?im)^\s*RIGOR\s*SCORE(?:\s*FINAL)?\s*[:=]\s*[0-9.]+.*$', '', texto)
    texto = re.sub(r'(?im)^\s*VEREDICTO\s*FINAL\s*:\s*(?:APROBADO(?:\s+CON\s+OBSERVACIONES)?|RECHAZADO).*$','',texto)
    dims = metricas.get("dimensiones", {})
    met = dims.get("metodologica", {})
    tec = dims.get("tecnica", {})
    lin = dims.get("linguistica", {})
    bloque = f"""

===RESULTADO_OFICIAL_BACKEND===
Puntaje metodológico: {met.get('puntaje_obtenido', 0):.2f} / {met.get('puntaje_maximo', 0):.2f} pts
Puntaje técnico: {tec.get('puntaje_obtenido', 0):.2f} / {tec.get('puntaje_maximo', 0):.2f} pts
Puntaje lingüístico: {lin.get('puntaje_obtenido', 0):.2f} / {lin.get('puntaje_maximo', 0):.2f} pts
RIGOR SCORE FINAL: {metricas.get('rigor_score', 0):.4f}
RIGOR PORCENTAJE: {metricas.get('rigor_porcentaje', 0):.2f}%
VEREDICTO FINAL: {metricas.get('veredicto_oficial', 'RECHAZADO')}
FUENTE: backend_determinista
"""
    return texto.rstrip() + bloque


async def ejecutar_analisis_completo(filepath: str) -> dict:
    """
    Flujo Secuencial con inyección de rúbricas via MCP.

    Pipeline:
      1. Extrae y segmenta el PDF.
      2. El Orquestador Python detecta diseño + sublínea de la tesis.
      3. Llama al MCP de Rúbricas para obtener el contenido correcto (M3, T10, L1, etc).
      4. Inyecta las rúbricas como tweaks en los Prompt Templates del flujo.
      5. Ejecuta el flujo Langflow — los agentes reciben rúbricas reales, no strings vacíos.
    """
    from orchestrator import identificar_diseno
    from mcp_client import resolver_rubricas, verificar_mcp

    hash_archivo = calcular_hash(filepath)
    inicio_total = time.time()

    # ── Verificar Langflow ─────────────────────────────────────────────
    ok, msg = await verificar_langflow()
    if not ok:
        error = f"Langflow no disponible: {msg}"
        return {
            "secuencial": {"texto_crudo": "", "latencia_ms": 0, "exito": False, "error": error},
            "hash_archivo": hash_archivo, "latencia_total_ms": 0, "exito_general": False,
            "diseno_info": None, "rubricas_ids": None,
        }

    # ── Extraer PDF ────────────────────────────────────────────────────
    try:
        texto = _extraer_texto_pdf(filepath, rapido=True)
    except Exception as e:
        return {
            "secuencial": {"texto_crudo": "", "latencia_ms": 0, "exito": False, "error": str(e)},
            "hash_archivo": hash_archivo, "latencia_total_ms": 0, "exito_general": False,
            "diseno_info": None, "rubricas_ids": None,
        }

    # ── Paso 1: Orquestador Python — detecta diseño y sublínea ────────
    print("🔄 [1/3] Orquestador: detectando diseño de investigación...")
    diseno_info = await identificar_diseno(texto)
    enfoque  = diseno_info.get("enfoque", "Cuantitativo")
    diseno   = diseno_info.get("diseno_mcp",  diseno_info.get("diseno", "Descriptivo Transversal"))
    linea    = diseno_info.get("linea",   "Software y Tecnologías de Información")
    sublinea = diseno_info.get("sublinea","Ingeniería de Software y Arquitectura de Sistemas")
    print(f"  ✅ {enfoque} / {diseno} / {sublinea}")

    # ── Paso 2: MCP — obtener contenido de rúbricas ───────────────────
    print("🔄 [2/3] MCP Rúbricas: cargando contenido de rúbricas...")
    tweaks = {}
    rubricas_ids = {}
    datos_mcp = None

    mcp_ok, _ = await verificar_mcp()
    if mcp_ok:
        datos_mcp = await resolver_rubricas(enfoque, diseno, linea, sublinea)
        if datos_mcp:
            rubricas_ids = {
                "metodologica": datos_mcp["rubrica_metodologica_id"],
                "tecnica":      datos_mcp["rubrica_tecnica_id"],
                "linguistica":  datos_mcp["rubrica_linguistica_id"],
            }
            # Inyectar contenido de rúbricas en los Prompt Templates via tweaks
            # Los Prompt Templates usan la variable {rubrica_X} en su template
            # La inyectamos via tweaks con el nombre exacto de la variable del template
            tweaks = {
                NODE_PROMPT_METODOLOGICO: {
                    "rubrica_metodologica": datos_mcp["rubrica_metodologica"]
                },
                NODE_PROMPT_TECNICO: {
                    "rubrica_tecnica": datos_mcp["rubrica_tecnica"]
                },
                NODE_PROMPT_LINGUISTICO: {
                    "rubrica_linguistica": datos_mcp["rubrica_linguistica"]
                },
                NODE_AGENT_CONSENSO: {
                    "system_prompt": _build_consenso_system_prompt_secuencial(diseno_info)
                }
            }
            print(f"  ✅ Rúbricas inyectadas: {rubricas_ids}")
        else:
            print("  ⚠️ MCP retornó vacío — los agentes usarán su criterio propio")
    else:
        print("  ⚠️ MCP Rúbricas no disponible — ejecutando sin rúbricas específicas")

    # ── Paso 3: Ejecutar flujo Secuencial con tweaks ──────────────────
    print("🔄 [3/3] Flujo Secuencial en Langflow (con rúbricas inyectadas)...")
    print("🔄 [3/3] Simulando Flujo Secuencial en Python puro...")
    resultado_secuencial = await _simular_flujo_jerarquico_secuencial(texto, datos_mcp or {}, diseno_info, False)

    # Extraer outputs por agente del resultado
    todos_outputs = _extraer_todos_los_outputs(
        resultado_secuencial.get("raw_data", {})
    )

    return {
        "secuencial":      resultado_secuencial,
        "agentes":         todos_outputs,      # outputs individuales parseados
        "diseno_info":     diseno_info,
        "rubricas_ids":    rubricas_ids,
        "hash_archivo":    hash_archivo,
        "latencia_total_ms": int((time.time() - inicio_total) * 1000),
        "exito_general":   resultado_secuencial["exito"],
    }


async def _auditoria_exhaustiva_jerarquica(texto_tesis: str, dictamen_inicial: str, diseno_info: dict) -> dict:
    """Segunda pasada real para el veredicto jerárquico.

    Verifica evidencia, contradicciones y coherencia entre los tres comités. No
    recalcula el Rigor Score: los puntajes oficiales permanecen en el backend.
    La función es tolerante a fallos; si DeepSeek no está disponible, el
    veredicto inicial continúa siendo válido.
    """
    habilitada = os.getenv("JERARQUICO_AUDITORIA_EXHAUSTIVA", "true").lower() in {"1", "true", "si", "sí", "yes"}
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not habilitada or not api_key:
        return {"texto": "", "latencia_ms": 0, "exito": False, "omitida": True}

    modelo = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    url = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
    max_chars = int(os.getenv("JERARQUICO_AUDITORIA_MAX_CHARS", "42000"))

    prompt = f"""Eres el Auditor de Evidencia de un comité universitario. Realiza una segunda revisión exhaustiva del dictamen multiagente.

CONTEXTO DETECTADO:
{diseno_info}

TESIS SEGMENTADA (fuente primaria):
{texto_tesis[:max_chars]}

DICTAMEN INICIAL DEL COMITÉ:
{dictamen_inicial[:26000]}

TAREAS OBLIGATORIAS:
1. Verifica si las observaciones principales tienen evidencia rastreable en la tesis.
2. Detecta contradicciones entre los análisis metodológico, técnico y lingüístico.
3. Señala falsos positivos, afirmaciones no sustentadas o criterios que requieren revisión humana.
4. Prioriza entre 5 y 10 hallazgos críticos, indicando área, evidencia breve y acción correctiva.
5. Emite una conclusión de consistencia del dictamen: ALTA, MEDIA o BAJA.

REGLAS:
- No calcules ni modifiques puntajes, Rigor Score o veredicto oficial.
- No inventes citas ni páginas. Si no existe evidencia suficiente, indícalo expresamente.
- Responde en español, con estructura clara y concisa.
"""

    payload = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": "Auditas evidencia académica con rigor, trazabilidad y prudencia."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": int(os.getenv("JERARQUICO_AUDITORIA_MAX_TOKENS", "2600")),
        "stream": False,
    }
    inicio = time.time()
    try:
        async with httpx.AsyncClient(timeout=int(os.getenv("JERARQUICO_AUDITORIA_TIMEOUT", "180"))) as client:
            r = await client.post(url, json=payload, headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            })
            r.raise_for_status()
        data = r.json()
        texto = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        return {
            "texto": texto,
            "latencia_ms": int((time.time() - inicio) * 1000),
            "exito": bool(texto),
            "omitida": False,
        }
    except Exception as e:
        print(f"⚠️ Auditoría exhaustiva omitida por error no crítico: {e}")
        return {
            "texto": "",
            "latencia_ms": int((time.time() - inicio) * 1000),
            "exito": False,
            "omitida": False,
            "error": str(e),
        }


async def ejecutar_veredicto(filepath: str) -> dict:
    """
    Flujo Jerárquico — 3 agentes en paralelo → Consenso supervisor.

    Pipeline:
      1. Extrae y segmenta el PDF.
      2. Orquestador detecta diseño + sublínea.
      3. MCP carga rúbricas (M*, T*, L1).
      4. Inyecta rúbricas via tweaks en los Prompt Templates del flujo Jerárquico.
      5. Ejecuta el flujo en Langflow.
    """
    from orchestrator import identificar_diseno
    from mcp_client import resolver_rubricas, verificar_mcp

    hash_archivo = calcular_hash(filepath)
    inicio_total = time.time()

    ok, msg = await verificar_langflow()
    if not ok:
        error = f"Langflow no disponible: {msg}"
        return {
            "jerarquico": {"texto_crudo": "", "latencia_ms": 0, "exito": False, "error": error},
            "hash_archivo": hash_archivo, "latencia_total_ms": 0, "exito_general": False,
            "diseno_info": None, "rubricas_ids": None,
        }

    try:
        texto = _extraer_texto_pdf(filepath)
    except Exception as e:
        return {
            "jerarquico": {"texto_crudo": "", "latencia_ms": 0, "exito": False, "error": str(e)},
            "hash_archivo": hash_archivo, "latencia_total_ms": 0, "exito_general": False,
            "diseno_info": None, "rubricas_ids": None,
        }

    # ── Paso 1: Orquestador ───────────────────────────────────────────
    print("🔄 [1/3] Orquestador: detectando diseño de investigación...")
    diseno_info = await identificar_diseno(texto)
    enfoque  = diseno_info.get("enfoque", "Cuantitativo")
    diseno   = diseno_info.get("diseno_mcp", diseno_info.get("diseno", "Descriptivo Transversal"))
    linea    = diseno_info.get("linea", "Software y Tecnologías de Información")
    sublinea = diseno_info.get("sublinea", "Ingeniería de Software y Arquitectura de Sistemas")
    print(f"  ✅ {enfoque} / {diseno} / {sublinea}")

    # ── Paso 2: MCP ───────────────────────────────────────────────────
    print("🔄 [2/3] MCP Rúbricas: cargando contenido de rúbricas...")
    tweaks = {}
    rubricas_ids = {}
    datos_mcp = None

    mcp_ok, _ = await verificar_mcp()
    if mcp_ok:
        datos_mcp = await resolver_rubricas(enfoque, diseno, linea, sublinea)
        if datos_mcp:
            rubricas_ids = {
                "metodologica": datos_mcp["rubrica_metodologica_id"],
                "tecnica":      datos_mcp["rubrica_tecnica_id"],
                "linguistica":  datos_mcp["rubrica_linguistica_id"],
            }
            # Inyectar en Prompt Templates del flujo Jerárquico
            tweaks = {
                NODE_JER_PROMPT_METODOLOGICO: {
                    "rubrica_metodologica": datos_mcp["rubrica_metodologica"]
                },
                NODE_JER_PROMPT_TECNICO: {
                    "rubrica_tecnica": datos_mcp["rubrica_tecnica"]
                },
                NODE_JER_PROMPT_LINGUISTICO: {
                    "rubrica_linguistica": datos_mcp["rubrica_linguistica"]
                },
                NODE_JER_AGENT_CONSENSO: {
                    "system_prompt": _build_consenso_system_prompt_jerarquico(diseno_info)
                }
            }
            print(f"✅ MCP rúbricas → {rubricas_ids['metodologica']} / {rubricas_ids['tecnica']} / {rubricas_ids['linguistica']}")
            print(f"  ✅ Rúbricas inyectadas en flujo Jerárquico: {rubricas_ids}")
        else:
            print("  ⚠️ MCP retornó vacío — los agentes usarán su criterio propio")
    else:
        print("  ⚠️ MCP Rúbricas no disponible — ejecutando sin rúbricas específicas")

    # ── Paso 3: Ejecutar flujo Jerárquico ────────────────────────────
    print("🔄 [3/3] Flujo Jerárquico en Langflow (con rúbricas inyectadas)...")
    print("🔄 [3/3] Simulando Flujo Jerárquico en Python puro...")
    resultado_jerarquico = await _simular_flujo_jerarquico_secuencial(texto, datos_mcp or {}, diseno_info, True)

    # Segunda pasada real: audita evidencia y coherencia. Esto diferencia el
    # veredicto exhaustivo del diagnóstico preliminar sin introducir esperas
    # artificiales. Los puntajes siguen calculándose exclusivamente en backend.
    auditoria = await _auditoria_exhaustiva_jerarquica(
        texto,
        resultado_jerarquico.get("texto_crudo", ""),
        diseno_info,
    )
    if auditoria.get("exito"):
        resultado_jerarquico["texto_crudo"] = (
            resultado_jerarquico.get("texto_crudo", "").rstrip()
            + "\n\n# AUDITORÍA DE EVIDENCIA Y CONSISTENCIA\n"
            + auditoria["texto"]
        )

    agentes_jerarquicos = _extraer_todos_los_outputs(
        resultado_jerarquico.get("raw_data", {})
    )
    rubricas_detalle = _construir_rubricas_detalle(
        datos_mcp,
        agentes_jerarquicos,
        resultado_jerarquico.get("texto_crudo", ""),
    )
    metricas_oficiales = _calcular_metricas_oficiales(rubricas_detalle)
    resultado_jerarquico["texto_original_llm"] = resultado_jerarquico.get("texto_crudo", "")
    resultado_jerarquico["auditoria_exhaustiva"] = auditoria
    resultado_jerarquico["latencia_ms"] = resultado_jerarquico.get("latencia_ms", 0) + auditoria.get("latencia_ms", 0)
    resultado_jerarquico["texto_crudo"] = _anexar_resultado_oficial(
        resultado_jerarquico.get("texto_crudo", ""), metricas_oficiales
    )
    resultado_jerarquico["rigor_score"] = metricas_oficiales["rigor_score"]
    resultado_jerarquico["veredicto_oficial"] = metricas_oficiales["veredicto_oficial"]

    return {
        "jerarquico":      resultado_jerarquico,
        "diseno_info":     diseno_info,
        "rubricas_ids":    rubricas_ids,
        "agentes":          agentes_jerarquicos,
        "rubricas_detalle": rubricas_detalle,
        "metricas_oficiales": metricas_oficiales,
        "auditoria_exhaustiva": auditoria,
        "rigor_score": metricas_oficiales["rigor_score"],
        "veredicto_oficial": metricas_oficiales["veredicto_oficial"],
        "hash_archivo":    hash_archivo,
        "latencia_total_ms": int((time.time() - inicio_total) * 1000),
        "exito_general":   resultado_jerarquico["exito"],
    }


async def ejecutar_human_loop(resultado_previo: dict, instruccion_docente: str, decision: str) -> dict:
    """
    Flujo Human-in-the-Loop.

    NO re-evalúa la tesis. Recibe:
      - resultado_previo: el análisis completo ya guardado (Secuencial o Jerárquico)
      - instruccion_docente: observación/instrucción del docente
      - decision: aprobado | aprobado_con_cambios | rechazado

    Construye un payload resumido y lo envía al flujo HumanLoop en Langflow.
    El único agente activo (DeepSeek iad8q) genera feedback accionable para el alumno.
    """
    print(f"🔄 Human-Loop — decisión: {decision} | instrucción: {instruccion_docente[:80]}...")

    # ── Construir resumen del análisis previo ────────────────────
    tipo = resultado_previo.get("tipo", "analisis_completo")

    # Extraer texto del Conciliador según el tipo de análisis previo
    if tipo == "veredicto":
        texto_conciliador = resultado_previo.get("jerarquico", {}).get("texto_crudo", "")
    elif tipo == "analisis_completo":
        texto_conciliador = resultado_previo.get("secuencial", {}).get("texto_crudo", "")
    else:
        texto_conciliador = ""

    # Extraer diseno_info si existe
    diseno_info = resultado_previo.get("diseno_info", {})
    enfoque  = diseno_info.get("enfoque", "No detectado")
    diseno   = diseno_info.get("diseno", "No detectado")
    sublinea = diseno_info.get("sublinea", "No detectada")

    # Etiqueta legible de la decisión
    decision_label = {
        "aprobado": "✅ APROBADO",
        "aprobado_con_cambios": "✏️ APROBADO CON CAMBIOS",
        "rechazado": "❌ RECHAZADO",
    }.get(decision, decision.upper())

    # Payload que recibe el ChatInput del flujo
    payload = f"""DECISIÓN DEL DOCENTE: {decision_label}

INSTRUCCIÓN DEL DOCENTE:
{instruccion_docente or "Sin observaciones adicionales."}

---
ANÁLISIS PREVIO DEL SISTEMA MULTIAGENTE:
Tipo de análisis: {tipo.upper().replace("_", " ")}
Diseño detectado: {enfoque} / {diseno} / {sublinea}

{texto_conciliador[:6000] if texto_conciliador else "Sin análisis previo disponible."}
"""

    tweaks = {
        NODE_HUMAN_AGENT_FINAL: {
            "system_prompt": """Eres el filtro final Human-in-the-Loop del sistema multiagente de evaluación de tesis UPAO.

Recibes:
1. La decisión oficial del docente.
2. La observación del docente.
3. El análisis previo del sistema multiagente.

Reglas obligatorias:
- La decisión del docente prevalece sobre el dictamen preliminar de la IA.
- No ocultes ni contradigas la decisión del docente.
- No generes un bloque plano sin estructura.
- Integra las observaciones humanas como correcciones oficiales.
- Mantén redacción formal, académica y clara.

Devuelve usando exactamente esta estructura:

===DICTAMEN===

Título de la tesis:
[Extrae o resume el título si aparece en el análisis previo]

Evaluación metodológica:
[Resume el estado metodológico e integra la observación del docente si aplica]

Evaluación técnica:
[Resume el estado técnico del trabajo]

Evaluación lingüística:
[Resume errores APA, redacción y formato]

Correcciones aplicadas por el supervisor humano:
- [Corrección 1]
- [Corrección 2]
- [Corrección 3]

Rigor Score final:
[X.X / 5.0] [Aprobado / Observado / Insuficiente]

Veredicto final:
[APROBADO / APROBADO CON CAMBIOS / RECHAZADO]

Justificación final:
[Explica por qué se mantiene o modifica el dictamen de la IA según la decisión del docente]

Recomendaciones finales:
1. [Acción concreta prioritaria]
2. [Acción concreta prioritaria]
3. [Acción concreta prioritaria]
"""
        }
    }

    print("🔄 Simulando Flujo Human-in-the-Loop en Python puro...")
    system_prompt = tweaks[NODE_HUMAN_AGENT_FINAL]["system_prompt"]
    return await _simular_flujo_human_loop(payload, system_prompt)
async def ejecutar_debate_red(filepath: str) -> dict:
    """
    Flujo de Red.
    """
    hash_archivo = calcular_hash(filepath)
    inicio_total = time.time()

    ok, msg = await verificar_langflow()

    if not ok:
        error = f"Langflow no disponible: {msg}"
        return {
            "red": {
                "texto_crudo": "",
                "latencia_ms": 0,
                "exito": False,
                "error": error,
            },
            "hash_archivo": hash_archivo,
            "latencia_total_ms": 0,
            "exito_general": False,
        }

    try:
        texto = _extraer_texto_pdf(filepath)
    except Exception as e:
        return {
            "red": {
                "texto_crudo": "",
                "latencia_ms": 0,
                "exito": False,
                "error": str(e),
            },
            "hash_archivo": hash_archivo,
            "latencia_total_ms": 0,
            "exito_general": False,
        }

    print("🔄 [1/1] Ejecutando flujo Red en Langflow...")
    resultado_red = await _ejecutar_flujo(
        "Red",
        FLOW_ID_RED,
        texto,
    )

    return {
        "red": resultado_red,
        "hash_archivo": hash_archivo,
        "latencia_total_ms": int((time.time() - inicio_total) * 1000),
        "exito_general": resultado_red["exito"],
    }
# ══════════════════════════════════════════════════════════════════════
# IDs de nodos — Flujo SECUENCIAL
# ══════════════════════════════════════════════════════════════════════
NODE_PROMPT_METODOLOGICO = os.getenv("NODE_PROMPT_METODOLOGICO", "Prompt Template-lExmE")
NODE_PROMPT_TECNICO      = os.getenv("NODE_PROMPT_TECNICO",      "Prompt Template-fvDGh")
NODE_PROMPT_LINGUISTICO  = os.getenv("NODE_PROMPT_LINGUISTICO",  "Prompt Template-SYefO")
NODE_PROMPT_CONSENSO     = os.getenv("NODE_PROMPT_CONSENSO",     "Prompt Template-9xUyA")
NODE_AGENT_METODOLOGICO  = os.getenv("NODE_AGENT_METODOLOGICO",  "DeepSeekModelComponent-XsFWz")
NODE_AGENT_TECNICO       = os.getenv("NODE_AGENT_TECNICO",       "DeepSeekModelComponent-YTa3k")
NODE_AGENT_LINGUISTICO   = os.getenv("NODE_AGENT_LINGUISTICO",   "DeepSeekModelComponent-cKWsF")
NODE_AGENT_CONSENSO      = os.getenv("NODE_AGENT_CONSENSO",      "DeepSeekModelComponent-Iqo9x")

# ══════════════════════════════════════════════════════════════════════
# IDs de nodos — Flujo JERÁRQUICO (Arq__Jerarquica.json)
# ══════════════════════════════════════════════════════════════════════
NODE_JER_PROMPT_METODOLOGICO = os.getenv("NODE_JER_PROMPT_METODOLOGICO", "Prompt Template-JH4ra")
NODE_JER_PROMPT_TECNICO      = os.getenv("NODE_JER_PROMPT_TECNICO",      "Prompt Template-IhagR")
NODE_JER_PROMPT_LINGUISTICO  = os.getenv("NODE_JER_PROMPT_LINGUISTICO",  "Prompt Template-0zCAQ")
NODE_JER_PROMPT_CONSENSO     = os.getenv("NODE_JER_PROMPT_CONSENSO",     "Prompt Template-zPNx3")
NODE_JER_AGENT_METODOLOGICO  = os.getenv("NODE_JER_AGENT_METODOLOGICO",  "DeepSeekModelComponent-5jV3E")
NODE_JER_AGENT_TECNICO       = os.getenv("NODE_JER_AGENT_TECNICO",       "DeepSeekModelComponent-K3rdz")
NODE_JER_AGENT_LINGUISTICO   = os.getenv("NODE_JER_AGENT_LINGUISTICO",   "DeepSeekModelComponent-Ql16C")
NODE_JER_AGENT_CONSENSO      = os.getenv("NODE_JER_AGENT_CONSENSO",      "DeepSeekModelComponent-Szpng")

# ══════════════════════════════════════════════════════════════════════
# IDs de nodos — Flujo HUMAN-IN-THE-LOOP (Arq__Human.json)
# ══════════════════════════════════════════════════════════════════════
NODE_HUMAN_PROMPT_METODOLOGICO = os.getenv("NODE_HUMAN_PROMPT_METODOLOGICO", "Prompt Template-3pYPo")
NODE_HUMAN_PROMPT_TECNICO      = os.getenv("NODE_HUMAN_PROMPT_TECNICO",      "Prompt Template-tEskb")
NODE_HUMAN_PROMPT_LINGUISTICO  = os.getenv("NODE_HUMAN_PROMPT_LINGUISTICO",  "Prompt Template-S3zpO")
NODE_HUMAN_PROMPT_CONSENSO     = os.getenv("NODE_HUMAN_PROMPT_CONSENSO",     "Prompt Template-32RL2")
NODE_HUMAN_PROMPT_FINAL        = os.getenv("NODE_HUMAN_PROMPT_FINAL",        "Prompt Template-Fnj3Z")
NODE_HUMAN_AGENT_METODOLOGICO  = os.getenv("NODE_HUMAN_AGENT_METODOLOGICO",  "DeepSeekModelComponent-ynTPe")
NODE_HUMAN_AGENT_TECNICO       = os.getenv("NODE_HUMAN_AGENT_TECNICO",       "DeepSeekModelComponent-3XknQ")
NODE_HUMAN_AGENT_LINGUISTICO   = os.getenv("NODE_HUMAN_AGENT_LINGUISTICO",   "DeepSeekModelComponent-9KSaA")
NODE_HUMAN_AGENT_CONSENSO      = os.getenv("NODE_HUMAN_AGENT_CONSENSO",      "DeepSeekModelComponent-FdVAt")
NODE_HUMAN_AGENT_FINAL         = os.getenv("NODE_HUMAN_AGENT_FINAL",         "DeepSeekModelComponent-iad8q")


# ══════════════════════════════════════════════════════════════════════
# Constructores de System Prompts con rúbricas (para inyectar via tweaks)
# ══════════════════════════════════════════════════════════════════════

def _build_agent_system_prompt(agente: str, rubrica_md: str, diseno_info: dict) -> str:
    """
    Construye el system_prompt enriquecido para cada agente.
    Fuerza al LLM a evaluar ÍTEM POR ÍTEM usando los IDs de la rúbrica del MCP.
    """
    import re as _re

    enfoque  = diseno_info.get("enfoque",  "Cuantitativo")
    diseno   = diseno_info.get("diseno",   "Descriptivo")
    sublinea = diseno_info.get("sublinea", "Ingeniería de Software")

    roles = {
        "metodologico": (
            "Agente Metodológico del Comité Evaluador de Tesis UPAO",
            "Evalúas EXCLUSIVAMENTE el rigor metodológico de la tesis.",
            "metodologico"
        ),
        "tecnico": (
            "Agente Técnico del Comité Evaluador de Tesis UPAO",
            "Evalúas EXCLUSIVAMENTE los aspectos técnicos según la sublínea de investigación.",
            "tecnico"
        ),
        "linguistico": (
            "Agente Lingüístico del Comité Evaluador de Tesis UPAO",
            "Evalúas EXCLUSIVAMENTE la calidad de redacción, formato APA 7 y referencias.",
            "linguistico"
        ),
    }
    nombre, tarea, clave = roles.get(agente, roles["metodologico"])

    # Extraer IDs y puntajes de la rúbrica MD para construir lista explícita
    # Formato esperado en el MD: "ID-XX\nDescripción: ...\nPuntaje: X.XXXX"
    items_extraidos = _re.findall(
        r'(ID-\d+)\s*\nDescripci[oó]n:\s*(.+?)\nPuntaje:\s*([0-9.]+)',
        rubrica_md, _re.DOTALL
    )

    if items_extraidos:
        # Construir lista de IDs explícita para el LLM
        lista_ids = ""
        puntaje_maximo = 0.0
        for item_id, desc, pts in items_extraidos:
            pts_float = float(pts)
            puntaje_maximo += pts_float
            desc_corta = desc.strip().replace("\n", " ")[:120]
            lista_ids += f"\n- **{item_id}** ({pts_float:.4f} pts): {desc_corta}"

        instruccion_items = f"""\n## LISTA DE ÍTEMS A EVALUAR (OBLIGATORIO evaluar TODOS)
Puntaje máximo total: **{puntaje_maximo:.4f} pts**
{lista_ids}

## INSTRUCCIÓN CRÍTICA
- Evalúa CADA ítem de la lista anterior.
- Para cada ID-XX pregúntate: ¿Está esto EXPLÍCITAMENTE en el texto de la tesis?
- Si no está escrito: puntos_obtenidos = 0, evidencia = "No encontrado en el documento"
- NO seas complaciente. NO inventes evidencia. Solo lo que está en el texto.
- Tu JSON debe tener exactamente {len(items_extraidos)} evaluaciones, una por cada ID.
"""
        ejemplo_evaluacion = f'{{"id": "{items_extraidos[0][0]}", "descripcion": "...", "estado": "cumple|parcial|no_cumple", "puntos_max": {float(items_extraidos[0][2]):.4f}, "puntos_obtenidos": 0.0, "evidencia": "cita literal o No encontrado", "observacion": "..."}}'
    else:
        # Fallback si el MD no tiene el formato esperado
        lista_ids = rubrica_md[:3000]
        puntaje_maximo = 10.0
        instruccion_items = "Evalúa todos los criterios de la rúbrica recibida ítem por ítem."
        ejemplo_evaluacion = '{"id": "ID-01", "descripcion": "...", "estado": "cumple", "puntos_max": 0.1667, "puntos_obtenidos": 0.0, "evidencia": "...", "observacion": "..."}'

    return f"""Eres el {nombre}.
{tarea}

## CONTEXTO DE ESTA TESIS
- Enfoque: {enfoque}
- Diseño: {diseno}
- Sublínea técnica: {sublinea}

## RÚBRICA OFICIAL DEL MCP (NO inventes criterios adicionales)
{rubrica_md[:4000]}
{instruccion_items}

## FORMATO DE RESPUESTA OBLIGATORIO (JSON puro, sin markdown, sin texto antes ni después):
{{
  "agente": "{clave}",
  "enfoque": "{enfoque}",
  "diseno": "{diseno}",
  "evaluaciones": [
    {ejemplo_evaluacion}
  ],
  "puntaje_total": 0.0,
  "puntaje_maximo": {puntaje_maximo:.4f},
  "porcentaje_cumplimiento": 0.0,
  "fortalezas": ["fortaleza 1", "fortaleza 2"],
  "debilidades_criticas": ["debilidad que impide aprobación 1"],
  "recomendaciones": ["acción concreta 1"]
}}"""


def _build_consenso_system_prompt_secuencial(diseno_info: dict) -> str:
    enfoque  = diseno_info.get("enfoque",  "Cuantitativo")
    diseno   = diseno_info.get("diseno",   "Descriptivo")
    sublinea = diseno_info.get("sublinea", "Ingeniería de Software")

    return f"""Eres el Agente Orquestador para un Diagnóstico Rápido de Tesis UPAO.

CONTEXTO: Enfoque: {enfoque} | Diseño: {diseno} | Sublínea: {sublinea}

Realiza un diagnóstico rápido cualitativo destacando las principales fortalezas y debilidades basándote en los reportes de los otros agentes.
NO CALCULES NINGÚN PUNTAJE NI RIGOR SCORE. Esto se hará en el backend.

FORMATO DE RESPUESTA OBLIGATORIO (JSON puro):
{{
  "tipo_resultado": "diagnostico_preliminar",
  "agente": "consenso",
  "resumen_ejecutivo": "[Breve resumen cualitativo en 2-3 lineas]",
  "fortalezas_rapidas": ["Fortaleza 1", "Fortaleza 2"],
  "debilidades_principales": ["Debilidad 1", "Debilidad 2", "Debilidad 3"],
  "recomendaciones_inmediatas": ["Recomendación 1", "Recomendación 2"]
}}"""

def _build_consenso_system_prompt_jerarquico(diseno_info: dict) -> str:
    enfoque  = diseno_info.get("enfoque",  "Cuantitativo")
    diseno   = diseno_info.get("diseno",   "Descriptivo")
    sublinea = diseno_info.get("sublinea", "Ingeniería de Software")

    return f"""Eres el Presidente del Comité Evaluador de Tesis UPAO (Agente Consenso / Supervisor).

Recibirás reportes de 3 agentes.
CONTEXTO: Enfoque: {enfoque} | Diseño: {diseno} | Sublínea: {sublinea}

TU TAREA EXCLUSIVA ES EL ANÁLISIS CUALITATIVO.
NO REALICES NINGÚN CÁLCULO MATEMÁTICO NI ASIGNES PUNTAJES. 
Los puntajes oficiales los calculará el sistema en el backend para evitar errores y alucinaciones.

FORMATO DE RESPUESTA OBLIGATORIO (JSON puro):
{{
  "tipo_resultado": "dictamen_jerarquico",
  "agente": "consenso",
  "resumen_ejecutivo": "[Resumen cualitativo general de la tesis y los hallazgos en 3-5 líneas]",
  "contradicciones_detectadas": ["Contradicción entre agentes 1", "Contradicción entre agentes 2"],
  "hallazgos_prioritarios": ["Hallazgo metodológico crítico", "Hallazgo técnico crítico", "Hallazgo lingüístico crítico"],
  "justificacion": "[Justificación cualitativa de por qué el trabajo presenta fallas o fortalezas a nivel global]",
  "plan_mejora_priorizado": ["Mejora 1", "Mejora 2", "Mejora 3"]
}}"""



async def _simular_agente_deepseek(system_prompt: str, user_prompt: str, agente: str = "") -> str:
    import json
    import httpx
    import asyncio
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    modelo = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    url = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
    
    payload = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt[:80000]},
        ],
        "temperature": 0.1,
    }
    
    print(f"  -> Iniciando Agente {agente}...")
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(url, json=payload, headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            })
            r.raise_for_status()
            
        print(f"  OK Agente {agente} completado")
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  Error en Agente {agente}: {e}")
        return f"{{\"error\": \"{str(e)}\"}}"

async def _simular_flujo_jerarquico_secuencial(texto: str, datos_mcp: dict, diseno_info: dict, es_jerarquico: bool) -> dict:
    import time
    import asyncio
    t0 = time.time()
    
    pm = _build_agent_system_prompt("metodologico", datos_mcp.get("rubrica_metodologica", ""), diseno_info)
    pt = _build_agent_system_prompt("tecnico", datos_mcp.get("rubrica_tecnica", ""), diseno_info)
    pl = _build_agent_system_prompt("linguistico", datos_mcp.get("rubrica_linguistica", ""), diseno_info)
    
    res_m, res_t, res_l = await asyncio.gather(
        _simular_agente_deepseek(pm, texto, "Metodologico"),
        _simular_agente_deepseek(pt, texto, "Tecnico"),
        _simular_agente_deepseek(pl, texto, "Linguistico")
    )
    
    if es_jerarquico:
        p_consenso = _build_consenso_system_prompt_jerarquico(diseno_info)
    else:
        p_consenso = _build_consenso_system_prompt_secuencial(diseno_info)
        
    user_consenso = f"Dictamen Metodologico:\n{res_m}\n\nDictamen Tecnico:\n{res_t}\n\nDictamen Linguistico:\n{res_l}"
    
    res_consenso = await _simular_agente_deepseek(p_consenso, user_consenso, "Consenso")
    latencia = int((time.time() - t0) * 1000)
    
    return {
        "texto_crudo": res_consenso,
        "latencia_ms": latencia,
        "exito": True,
        "error": None,
        "raw_data": {
            "outputs": [
                {
                    "outputs": [
                        {"results": {"message": {"text": res_m}}},
                        {"results": {"message": {"text": res_t}}},
                        {"results": {"message": {"text": res_l}}},
                        {"results": {"message": {"text": res_consenso}}}
                    ]
                }
            ]
        }
    }

async def _simular_flujo_human_loop(payload: str, system_prompt: str) -> dict:
    import time
    t0 = time.time()
    res = await _simular_agente_deepseek(system_prompt, payload, "HumanLoop")
    latencia = int((time.time() - t0) * 1000)
    
    return {
        "texto_crudo": res,
        "latencia_ms": latencia,
        "exito": True,
        "error": None,
        "raw_data": {
            "outputs": [
                {
                    "outputs": [
                        {"results": {"message": {"text": res}}}
                    ]
                }
            ]
        }
    }
