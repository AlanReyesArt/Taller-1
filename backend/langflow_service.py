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


def _extraer_texto_pdf(filepath: str) -> str:
    """
    Extrae el PDF y construye el input compacto para Langflow.

    El flujo de Langflow sigue usando Chat Input.
    No se envía la tesis completa en bruto.
    Se envía un JSON segmentado.
    """
    from pdf_extractor import extraer_texto_pdf, construir_input_langflow

    datos = extraer_texto_pdf(filepath)
    texto_langflow = construir_input_langflow(datos)
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


def _extraer_todos_los_outputs(data: dict) -> dict:
    """
    Extrae los outputs de TODOS los agentes del flujo secuencial.
    Retorna un dict con claves: metodologico, tecnico, linguistico, consenso
    intentando parsear el JSON de cada uno.
    """
    import json as _json

    outputs_raw = []
    try:
        for salida in data.get("outputs", []):
            for r in salida.get("outputs", []):
                msg = r.get("results", {}).get("message", {})
                txt = ""
                if isinstance(msg, dict):
                    txt = msg.get("text", "") or msg.get("data", {}).get("text", "")
                if not txt:
                    txt = r.get("results", {}).get("text", "")
                if txt:
                    outputs_raw.append(str(txt))
    except Exception:
        pass

    resultado = {"metodologico": None, "tecnico": None, "linguistico": None, "consenso": None, "raw": outputs_raw}

    for txt in outputs_raw:
        # Intentar parsear JSON
        limpio = txt.strip()
        if limpio.startswith("```"):
            match = __import__('re').search(r'```(?:json)?\s*([\s\S]*?)```', limpio)
            if match:
                limpio = match.group(1).strip()
        ini = limpio.find('{')
        fin = limpio.rfind('}')
        if ini != -1 and fin != -1:
            try:
                parsed = _json.loads(limpio[ini:fin+1])
                agente = parsed.get("agente", "")
                if agente == "metodologico":
                    resultado["metodologico"] = parsed
                elif agente == "tecnico":
                    resultado["tecnico"] = parsed
                elif agente == "linguistico":
                    resultado["linguistico"] = parsed
                elif agente in ("consenso", "") and "rigor_score" in parsed:
                    resultado["consenso"] = parsed
                elif agente == "consenso":
                    resultado["consenso"] = parsed
            except Exception:
                pass

    # Si solo hay 1 output y tiene rigor_score → es el Consenso con todo anidado
    if resultado["consenso"] is None and len(outputs_raw) == 1:
        try:
            parsed = _json.loads(outputs_raw[0][outputs_raw[0].find('{'):outputs_raw[0].rfind('}')+1])
            if "rigor_score" in parsed or "puntaje_final" in parsed:
                resultado["consenso"] = parsed
        except Exception:
            pass

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


def _construir_rubrica_evaluada(rubrica_id: str, rubrica_md: str, bloque_evaluacion: str) -> dict:
    """
    Devuelve la rúbrica completa con estado por ítem.
    Si el juez no mencionó un ID, queda como OBSERVADO para que igual aparezca en el veredicto.
    """
    items_base = _parsear_items_rubrica_md(rubrica_md)
    cumplidos = _ids_en_estado(bloque_evaluacion, ["Cumplidos", "Cumple"])
    no_cumplidos = _ids_en_estado(bloque_evaluacion, ["No cumplidos", "No cumple", "Incumplidos"])
    observados = _ids_en_estado(bloque_evaluacion, ["Observados", "Observado", "Parciales", "Parcial"])

    evaluaciones = []
    for item in items_base:
        iid = item["id"].upper()
        pts = item.get("puntos_max", 0.0)
        # Precedencia: si un ID aparece en "No cumplidos" y también en otra parte,
        # gana NO CUMPLE. Esto evita falsos positivos por menciones repetidas del juez.
        if iid in no_cumplidos:
            estado = "no_cumple"
            puntos_obtenidos = 0.0
            observacion = "Criterio marcado como no cumplido por el comité jerárquico."
        elif iid in cumplidos:
            estado = "cumple"
            puntos_obtenidos = pts
            observacion = "Criterio marcado como cumplido por el comité jerárquico."
        elif iid in observados:
            estado = "observado"
            puntos_obtenidos = 0.0
            observacion = "Criterio observado por el comité jerárquico. Requiere revisión o evidencia adicional."
        else:
            estado = "observado"
            puntos_obtenidos = 0.0
            observacion = "No fue mencionado explícitamente en el dictamen; se conserva como observado para revisión."
        evaluaciones.append({
            "id": item["id"],
            "descripcion": item["descripcion"],
            "estado": estado,
            "puntos_max": pts,
            "puntos_obtenidos": puntos_obtenidos,
            "evidencia": "Ver dictamen jerárquico" if iid in cumplidos or iid in no_cumplidos or iid in observados else "No especificada en el dictamen",
            "observacion": observacion,
        })

    return {
        "rubrica_id": rubrica_id,
        "total_items": len(evaluaciones),
        "puntaje_maximo": round(sum(i.get("puntos_max", 0.0) for i in evaluaciones), 4),
        "puntaje_obtenido_estimado": round(sum(i.get("puntos_obtenidos", 0.0) for i in evaluaciones), 4),
        "items": evaluaciones,
    }


def _construir_rubricas_detalle(datos_mcp: dict | None, texto_veredicto: str) -> dict:
    """Construye M/T/L completas para el frontend y el PDF descargable."""
    if not datos_mcp:
        return {}
    return {
        "metodologica": _construir_rubrica_evaluada(
            datos_mcp.get("rubrica_metodologica_id", "M?"),
            datos_mcp.get("rubrica_metodologica", ""),
            _extraer_bloque(texto_veredicto, "metodologica"),
        ),
        "tecnica": _construir_rubrica_evaluada(
            datos_mcp.get("rubrica_tecnica_id", "T?"),
            datos_mcp.get("rubrica_tecnica", ""),
            _extraer_bloque(texto_veredicto, "tecnica"),
        ),
        "linguistica": _construir_rubrica_evaluada(
            datos_mcp.get("rubrica_linguistica_id", "L1"),
            datos_mcp.get("rubrica_linguistica", ""),
            _extraer_bloque(texto_veredicto, "linguistica"),
        ),
    }


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
        texto = _extraer_texto_pdf(filepath)
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
                # NODE_PROMPT_CONSENSO no tiene variables {rubrica_*}
                # Sus variables son: {texto_tesis}, {reporte_metodologico}, {reporte_tecnico}, {reporte_linguistico}
                # La rúbrica llega al consenso via system_prompt del DeepSeek
                # Inyectar también en system_prompt de los agentes para refuerzo
                NODE_AGENT_METODOLOGICO: {
                    "system_prompt": _build_agent_system_prompt("metodologico", datos_mcp["rubrica_metodologica"], diseno_info)
                },
                NODE_AGENT_TECNICO: {
                    "system_prompt": _build_agent_system_prompt("tecnico", datos_mcp["rubrica_tecnica"], diseno_info)
                },
                NODE_AGENT_LINGUISTICO: {
                    "system_prompt": _build_agent_system_prompt("linguistico", datos_mcp["rubrica_linguistica"], diseno_info)
                },
                NODE_AGENT_CONSENSO: {
                    "system_prompt": _build_consenso_system_prompt(diseno_info)
                },
            }
            print(f"  ✅ Rúbricas inyectadas: {rubricas_ids}")
        else:
            print("  ⚠️ MCP retornó vacío — los agentes usarán su criterio propio")
    else:
        print("  ⚠️ MCP Rúbricas no disponible — ejecutando sin rúbricas específicas")

    # ── Paso 3: Ejecutar flujo Secuencial con tweaks ──────────────────
    print("🔄 [3/3] Flujo Secuencial en Langflow (con rúbricas inyectadas)...")
    resultado_secuencial = await _ejecutar_flujo(
        "Secuencial",
        FLOW_ID_SECUENCIAL,
        texto,
        tweaks if tweaks else None,
    )

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
                # Inyectar system_prompt con rúbricas en los DeepSeek del flujo Jerárquico
                NODE_JER_AGENT_METODOLOGICO: {
                    "system_prompt": _build_agent_system_prompt("metodologico", datos_mcp["rubrica_metodologica"], diseno_info)
                },
                NODE_JER_AGENT_TECNICO: {
                    "system_prompt": _build_agent_system_prompt("tecnico", datos_mcp["rubrica_tecnica"], diseno_info)
                },
                NODE_JER_AGENT_LINGUISTICO: {
                    "system_prompt": _build_agent_system_prompt("linguistico", datos_mcp["rubrica_linguistica"], diseno_info)
                },
                NODE_JER_AGENT_CONSENSO: {
                    "system_prompt": _build_consenso_system_prompt(diseno_info)
                },
            }
            print(f"✅ MCP rúbricas → {rubricas_ids['metodologica']} / {rubricas_ids['tecnica']} / {rubricas_ids['linguistica']}")
            print(f"  ✅ Rúbricas inyectadas en flujo Jerárquico: {rubricas_ids}")
        else:
            print("  ⚠️ MCP retornó vacío — los agentes usarán su criterio propio")
    else:
        print("  ⚠️ MCP Rúbricas no disponible — ejecutando sin rúbricas específicas")

    # ── Paso 3: Ejecutar flujo Jerárquico ────────────────────────────
    print("🔄 [3/3] Flujo Jerárquico en Langflow (con rúbricas inyectadas)...")
    resultado_jerarquico = await _ejecutar_flujo(
        "Jerarquico",
        FLOW_ID_JERARQUICO,
        texto,
        tweaks if tweaks else None,
    )

    rubricas_detalle = _construir_rubricas_detalle(
        datos_mcp,
        resultado_jerarquico.get("texto_crudo", ""),
    )

    return {
        "jerarquico":      resultado_jerarquico,
        "diseno_info":     diseno_info,
        "rubricas_ids":    rubricas_ids,
        "rubricas_detalle": rubricas_detalle,
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

    return await _ejecutar_flujo(
        "HumanLoop",
        FLOW_ID_HUMAN_LOOP,
        payload,
        tweaks,
    )
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


def _build_consenso_system_prompt(diseno_info: dict) -> str:
    """System prompt del Agente Consenso con separadores para el frontend."""
    enfoque  = diseno_info.get("enfoque",  "Cuantitativo")
    diseno   = diseno_info.get("diseno",   "Descriptivo")
    sublinea = diseno_info.get("sublinea", "Ingeniería de Software")

    return f"""Eres el Presidente del Comité Evaluador de Tesis UPAO (Agente Consenso / Supervisor).

Recibirás los 3 reportes JSON de los agentes especializados.
IMPORTANTE: Los agentes evaluaron ítem por ítem usando rúbricas oficiales del MCP.

## CONTEXTO
- Enfoque: {enfoque} | Diseño: {diseno} | Sublínea: {sublinea}

## PASO 1: EXTRAER PUNTAJES DE CADA AGENTE
Del JSON de cada agente extrae:
  - puntaje_total y puntaje_maximo
  - Calcular porcentaje = puntaje_total / puntaje_maximo

## PASO 2: CALCULAR RIGOR SCORE PONDERADO
Los puntajes máximos de las rúbricas UPAO son: Metodológico=10pts, Técnico=7pts, Lingüístico=3pts (Total=20pts)
Por eso las ponderaciones son: Metodológico=50%, Técnico=35%, Lingüístico=15%

rigor_score = (pct_met * 0.50) + (pct_tec * 0.35) + (pct_lin * 0.15)
Donde pct_X = puntaje_total_agente / puntaje_maximo_agente (valor entre 0 y 1)

## PASO 3: CRITERIO DE DICTAMEN
- rigor_score >= 0.80 → APROBADO
- rigor_score >= 0.60 → APROBADO CON OBSERVACIONES
- rigor_score < 0.60  → RECHAZADO

## PASO 4: AUDITORÍA ANTI-ALUCINACIONES
Verifica que cada debilidad_critica de los agentes tenga evidencia real en el texto.
Si un agente marcó cumple sin evidencia textual → reduce su puntaje.

## PASO 5: RESPUESTA CON SEPARADORES (OBLIGATORIO usar estos separadores exactos)

===METODOLOGICO===
[Resumen de 3-5 hallazgos críticos del Agente Metodológico con puntaje: X.XX / Y.YY pts]

===TECNICO===
[Resumen de 3-5 hallazgos críticos del Agente Técnico con puntaje: X.XX / Y.YY pts]

===LINGUISTICO===
[Lista numerada de errores APA y redacción del Agente Lingüístico con puntaje: X.XX / Y.YY pts]

===DICTAMEN===
RESUMEN EJECUTIVO: [3-4 líneas sobre la tesis]

RIGOR SCORE CALCULADO:
- Metodológico: [obtenido] / [maximo] = [porcentaje]% × 50% = [aporte]
- Técnico:      [obtenido] / [maximo] = [porcentaje]% × 35% = [aporte]
- Lingüístico:  [obtenido] / [maximo] = [porcentaje]% × 15% = [aporte]
- RIGOR SCORE FINAL: [valor entre 0.0 y 1.0]

AUDITORÍA DE CONSISTENCIA: [¿Hay contradicciones entre agentes? ¿Algún cumple sin evidencia?]

VEREDICTO FINAL: APROBADO / APROBADO CON OBSERVACIONES / RECHAZADO
JUSTIFICACIÓN: [3-4 líneas basadas en los puntajes calculados]

PLAN DE MEJORA:
1. [Alta prioridad] [Acción concreta] — Responsable: Agente Metodológico/Técnico/Lingüístico
2. [Media prioridad] [Acción concreta]
3. [Baja prioridad] [Acción concreta]"""
