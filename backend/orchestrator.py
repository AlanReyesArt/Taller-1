"""
orchestrator.py — Clasificador de rúbricas M1-M5, T1-T9, L1
"""

import re
import json
import os
import httpx
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

LANGFLOW_URL = os.getenv("LANGFLOW_URL", "http://localhost:7860")
LANGFLOW_API_KEY = os.getenv("LANGFLOW_API_KEY", "")
LANGFLOW_TIMEOUT = int(os.getenv("LANGFLOW_TIMEOUT", "600"))

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
USE_LLM_ORCHESTRATOR = os.getenv("USE_LLM_ORCHESTRATOR", "false").lower() == "true"


METODOLOGICAS = {
    "M1": {
        "enfoque": "Cuantitativo",
        "diseno_mcp": "Experimental Puro",
    },
    "M2": {
        "enfoque": "Cuantitativo",
        "diseno_mcp": "Cuasiexperimental",
    },
    "M3": {
        "enfoque": "Cuantitativo",
        "diseno_mcp": "Descriptivo Transversal",
    },
    "M4": {
        "enfoque": "Cuantitativo",
        "diseno_mcp": "Descriptivo Longitudinal",
    },
    "M5": {
        "enfoque": "Cualitativo",
        "diseno_mcp": "Cualitativo",
    },
}


TECNICAS = {
    "T1": {
        "linea": "Robótica, Automatización Avanzada y Sistemas Inteligentes",
        "sublinea": "Sistemas Inteligentes",
        "keywords": [
            "sistema inteligente", "sistemas inteligentes", "agente inteligente", "agentes inteligentes",
            "sistema experto", "sistemas expertos", "lógica difusa", "logica difusa", "inferencia",
            "razonamiento", "base de conocimiento", "bases de conocimiento", "ontología", "ontologia",
            "multiagente", "multi-agente", "agente", "deliberación", "deliberacion",
            "recomendador", "sistema de recomendación", "sistema de recomendacion"
        ],
    },
    "T2": {
        "linea": "Robótica, Automatización Avanzada y Sistemas Inteligentes",
        "sublinea": "Gestión de Datos e Información",
        "keywords": [
            "gestión de datos", "gestion de datos", "información", "informacion", "calidad de datos",
            "gobierno de datos", "data governance", "business intelligence", "inteligencia de negocios",
            "bi", "power bi", "dashboard", "cuadro de mando", "kpi", "indicadores",
            "data warehouse", "almacén de datos", "almacen de datos", "etl", "elt", "olap",
            "big data", "spark", "hadoop", "kafka", "data lake", "lakehouse", "pipeline de datos"
        ],
    },
    "T3": {
        "linea": "Robótica, Automatización Avanzada y Sistemas Inteligentes",
        "sublinea": "Inteligencia Artificial",
        "keywords": [
            "inteligencia artificial", "ia", "machine learning", "aprendizaje automático", "aprendizaje automatico",
            "deep learning", "red neuronal", "redes neuronales", "modelo predictivo", "clasificación", "clasificacion",
            "regresión", "regresion", "random forest", "svm", "xgboost", "cnn", "yolo", "opencv",
            "visión computacional", "vision computacional", "computer vision", "ia generativa", "llm", "gpt", "rag"
        ],
    },
    "T4": {
        "linea": "Robótica, Automatización Avanzada y Sistemas Inteligentes",
        "sublinea": "Sistemas de Información",
        "keywords": [
            "sistema de información", "sistemas de información", "sistema de informacion", "sistemas de informacion",
            "erp", "crm", "sistema web", "aplicación web", "aplicacion web", "sistema empresarial",
            "sistema integrado", "sistema hospitalario", "sig", "sigac", "auditoría", "auditoria",
            "auditoría de sistemas", "seguridad de la información", "seguridad de la informacion", "iso 27001",
            "iso 27002", "iso/iec 27002", "cumplimiento", "checklist", "lista de verificación", "lista de verificacion"
        ],
    },
    "T5": {
        "linea": "Robótica, Automatización Avanzada y Sistemas Inteligentes",
        "sublinea": "Comunicación, Tecnología de la Información e Innovación",
        "keywords": [
            "comunicación", "comunicacion", "tecnología de la información", "tecnologia de la informacion",
            "innovación", "innovacion", "redes", "redes de datos", "iot", "internet de las cosas",
            "cloud", "nube", "telecomunicaciones", "ciberseguridad", "infraestructura ti",
            "servicios ti", "itil", "cobit", "transformación digital", "transformacion digital"
        ],
    },
    "T6": {
        "linea": "Robótica, Automatización Avanzada y Sistemas Inteligentes",
        "sublinea": "Ingeniería de Software",
        "keywords": [
            "ingeniería de software", "ingenieria de software", "arquitectura de software", "arquitectura de sistemas",
            "desarrollo de software", "software", "backend", "frontend", "api rest", "microservicios",
            "clean architecture", "arquitectura limpia", "scrum", "kanban", "uml", "casos de uso",
            "diagrama de clases", "requerimientos funcionales", "requerimientos no funcionales", "devops", "ci/cd"
        ],
    },
    "T7": {
        "linea": "Robótica, Automatización Avanzada y Sistemas Inteligentes",
        "sublinea": "Sistemas Cognitivos",
        "keywords": [
            "sistemas cognitivos", "sistema cognitivo", "cognitivo", "procesamiento de lenguaje natural",
            "lenguaje natural", "nlp", "bert", "transformer", "chatbot", "asistente virtual",
            "análisis de sentimientos", "analisis de sentimientos", "clasificación de texto", "clasificacion de texto",
            "minería de texto", "mineria de texto", "embeddings", "word2vec", "tf-idf", "corpus"
        ],
    },
    "T8": {
        "linea": "Robótica, Automatización Avanzada y Sistemas Inteligentes",
        "sublinea": "Robótica y Automatización Avanzada",
        "keywords": [
            "robótica", "robotica", "robot", "automatización avanzada", "automatizacion avanzada",
            "automatización", "automatizacion", "rpa", "control automático", "control automatico",
            "sensores", "actuadores", "arduino", "raspberry", "ros", "plc", "mqtt",
            "telemetría", "telemetria", "dron", "vehículo autónomo", "vehiculo autonomo"
        ],
    },
    "T9": {
        "linea": "Robótica, Automatización Avanzada y Sistemas Inteligentes",
        "sublinea": "Nanomateriales Funcionales",
        "keywords": [
            "nanomaterial", "nanomateriales", "nanotecnología", "nanotecnologia", "material funcional",
            "materiales funcionales", "grafeno", "nanotubos", "nanopartículas", "nanoparticulas",
            "nanoestructura", "material inteligente", "sensores nano", "nanocompuesto"
        ],
    },
}

def _normalizar(texto: str) -> str:
    texto = texto.lower()
    texto = texto.replace("á", "a").replace("é", "e").replace("í", "i")
    texto = texto.replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    return texto


def _score_keywords(t: str, keywords: list[str]) -> int:
    score = 0
    for kw in keywords:
        kw_norm = _normalizar(kw)
        if kw_norm in t:
            score += 3 if len(kw_norm.split()) >= 2 else 1
    return score


async def identificar_diseno(texto_tesis: str) -> dict:
    """
    Clasifica la tesis y devuelve los campos que necesita mcp_client.resolver_rubricas().
    """
    if USE_LLM_ORCHESTRATOR and DEEPSEEK_API_KEY:
        try:
            resultado = await _clasificar_con_deepseek(texto_tesis)
            if resultado:
                return resultado
        except Exception as e:
            print(f"⚠️ Orquestador LLM falló: {e}. Usando clasificador local.")

    return _clasificar_local(texto_tesis)


async def _clasificar_con_deepseek(texto_tesis: str) -> Optional[dict]:
    fragmento = " ".join(texto_tesis.split()[:4500])

    prompt = f"""
Eres el Orquestador de un sistema multiagente de evaluación de tesis de Ingeniería de Computación y Sistemas.

Debes seleccionar exactamente:
- Una rúbrica metodológica: M1, M2, M3, M4 o M5
- Una rúbrica técnica: T1 a T9
- La rúbrica lingüística siempre es L1

RÚBRICAS METODOLÓGICAS:
M1 = Cuantitativo / Experimental Puro
M2 = Cuantitativo / Cuasiexperimental
M3 = Cuantitativo / Descriptivo Transversal
M4 = Cuantitativo / Descriptivo Longitudinal
M5 = Cualitativo / Cualitativo, estudio de caso, fenomenológico, teoría fundamentada

RÚBRICAS TÉCNICAS:
T1 = Sistemas Inteligentes
T2 = Gestión de Datos e Información
T3 = Inteligencia Artificial
T4 = Sistemas de Información
T5 = Comunicación, Tecnología de la Información e Innovación
T6 = Ingeniería de Software
T7 = Sistemas Cognitivos
T8 = Robótica y Automatización Avanzada
T9 = Nanomateriales Funcionales

REGLAS:
- Si la tesis es auditoría, seguridad, ISO 27001/27002, NTS 139, checklist, cumplimiento o sistemas clínicos/empresariales: T4.
- Si la tesis es BI, Power BI, dashboard, ETL, data warehouse, Big Data o indicadores: T2.
- Si la tesis es IA, Machine Learning, Deep Learning, Visión Computacional o IA Generativa: T3.
- Si la tesis es Ingeniería de Software, arquitectura, desarrollo web, APIs, UML o DevOps: T6.
- Si el documento declara enfoque cualitativo o estudio de caso cualitativo: M5.
- Si es descriptivo y mide una sola vez: M3.
- Solo usa M4 si hay seguimiento temporal real, varios periodos comparados o análisis evolutivo.
- No confundas “periodo 2024” con longitudinal.

Devuelve SOLO JSON válido:
{{
  "rubrica_metodologica_id": "M3",
  "rubrica_tecnica_id": "T4",
  "rubrica_linguistica_id": "L1",
  "enfoque": "Cuantitativo",
  "diseno_mcp": "Descriptivo Transversal",
  "linea": "Robótica, Automatización Avanzada y Sistemas Inteligentes",
  "sublinea": "Sistemas de Información",
  "confianza": "alta",
  "justificacion": "..."
}}

TEXTO:
{fragmento}
"""

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "Responde únicamente JSON válido."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
    }

    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(
            "https://api.deepseek.com/chat/completions",
            headers=headers,
            json=payload,
        )
        r.raise_for_status()

    content = r.json()["choices"][0]["message"]["content"].strip()
    content = content.replace("```json", "").replace("```", "").strip()
    data = json.loads(content)

    return _normalizar_salida(data, metodo="llm_deepseek")


def _clasificar_local(texto_tesis: str) -> dict:
    t = _normalizar(texto_tesis)

    # ─────────────────────────────────────────────
    # 1. Tipo metodológico
    # ─────────────────────────────────────────────

    enfoque = "Cuantitativo"
    rubrica_met = "M3"

    es_cualitativo = any(k in t for k in [
        "enfoque cualitativo",
        "metodo de estudio de caso",
        "estudio de caso",
        "fenomenologico",
        "fenomenologia",
        "teoria fundamentada",
        "hermeneutico",
        "entrevista en profundidad",
        "analisis del discurso"
    ])

    es_mixto = any(k in t for k in [
        "enfoque mixto",
        "metodologia mixta",
        "metodo mixto",
        "triangulacion"
    ])

    es_experimental = any(k in t for k in [
        "experimental puro",
        "experimento verdadero",
        "asignacion aleatoria",
        "grupo experimental y grupo control",
        "grupo de control y grupo experimental"
    ])

    es_cuasi = any(k in t for k in [
        "cuasiexperimental",
        "cuasi experimental",
        "pre experimental",
        "preexperimental",
        "pretest",
        "postest",
        "pre test",
        "post test"
    ])

    evidencia_longitudinal = any(k in t for k in [
        "diseno longitudinal",
        "estudio longitudinal",
        "seguimiento longitudinal",
        "a lo largo del tiempo",
        "mediciones sucesivas",
        "varios momentos de medicion",
        "serie temporal",
        "datos de panel",
        "evolucion durante",
        "comparacion anual",
        "comparacion mensual"
    ])

    if es_cualitativo:
        enfoque = "Cualitativo"
        rubrica_met = "M5"
    elif es_experimental:
        enfoque = "Cuantitativo"
        rubrica_met = "M1"
    elif es_cuasi:
        enfoque = "Cuantitativo"
        rubrica_met = "M2"
    elif evidencia_longitudinal:
        enfoque = "Cuantitativo"
        rubrica_met = "M4"
    else:
        enfoque = "Cuantitativo" if not es_mixto else "Mixto"
        rubrica_met = "M3"

    # ─────────────────────────────────────────────
    # 2. Técnica: scoring T1-T9
    # ─────────────────────────────────────────────

    scores = {}
    for tid, info in TECNICAS.items():
        scores[tid] = _score_keywords(t, info["keywords"])

    # Prioridades fuertes para evitar clasificaciones absurdas.
    if any(k in t for k in [
        "auditoria", "auditoria de seguridad", "auditoria de sistemas",
        "iso 27001", "iso/iec 27001", "iso 27002", "iso/iec 27002",
        "nts 139", "minsa-2018", "checklist", "lista de verificacion",
        "controles de seguridad", "seguridad de la informacion",
        "confidencialidad", "integridad", "disponibilidad", "trazabilidad"
    ]):
        scores["T4"] += 100

    if any(k in t for k in [
        "business intelligence", "inteligencia de negocios", "power bi",
        "dashboard", "data warehouse", "etl", "olap", "modelo dimensional",
        "esquema estrella", "tablero de mando"
    ]):
        scores["T2"] += 80

    if any(k in t for k in [
        "machine learning", "deep learning", "red neuronal", "modelo predictivo",
        "random forest", "svm", "xgboost"
    ]):
        scores["T3"] += 80

    if any(k in t for k in [
        "procesamiento de lenguaje natural", "nlp", "bert", "transformer",
        "analisis de sentimientos", "clasificacion de texto", "chatbot"
    ]):
        scores["T7"] += 90

    if any(k in t for k in [
        "vision computacional", "computer vision", "yolo", "opencv",
        "deteccion de objetos", "cnn", "ia generativa", "llm", "gpt"
    ]):
        scores["T3"] += 90

    rubrica_tec = max(scores, key=scores.get)

    # Si ningún score es fuerte, usar T1 como general de sistemas/software.
    if scores[rubrica_tec] <= 2:
        rubrica_tec = "T1"

    return _normalizar_salida({
        "rubrica_metodologica_id": rubrica_met,
        "rubrica_tecnica_id": rubrica_tec,
        "rubrica_linguistica_id": "L1",
        "confianza": "alta" if scores.get(rubrica_tec, 0) >= 5 else "media",
        "justificacion": f"Clasificación local: {rubrica_met}/{rubrica_tec}/L1 con score técnico {scores.get(rubrica_tec, 0)}",
    }, metodo="local_keywords")


def _normalizar_salida(data: dict, metodo: str = "local") -> dict:
    rubrica_met = data.get("rubrica_metodologica_id", "M3")
    rubrica_tec = data.get("rubrica_tecnica_id", "T1")

    if rubrica_met not in METODOLOGICAS:
        rubrica_met = "M3"

    if rubrica_tec not in TECNICAS:
        rubrica_tec = "T1"

    m = METODOLOGICAS[rubrica_met]
    t = TECNICAS[rubrica_tec]

    enfoque = data.get("enfoque") or m["enfoque"]
    diseno_mcp = data.get("diseno_mcp") or m["diseno_mcp"]
    linea = data.get("linea") or t["linea"]
    sublinea = data.get("sublinea") or t["sublinea"]

    return {
        "enfoque": enfoque,
        "diseno": diseno_mcp,
        "alcance": "longitudinal" if diseno_mcp == "Descriptivo Longitudinal" else "transversal",
        "rama": rubrica_tec,
        "nivel_confianza": data.get("confianza", data.get("nivel_confianza", "media")),
        "justificacion": data.get("justificacion", f"Clasificación {rubrica_met}/{rubrica_tec}/L1"),
        "metodo": metodo,

        # Campos usados por mcp_client.resolver_rubricas()
        "linea": linea,
        "sublinea": sublinea,
        "diseno_mcp": diseno_mcp,

        # Campos útiles para debug/frontend
        "rubrica_metodologica_id": rubrica_met,
        "rubrica_tecnica_id": rubrica_tec,
        "rubrica_linguistica_id": "L1",
    }