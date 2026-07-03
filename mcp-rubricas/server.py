"""
mcp-rubricas/server.py — Servidor MCP de Rúbricas UPAO
========================================================
Sirve el contenido de las rúbricas (MD) según el diseño
metodológico y la sublínea técnica detectados por el Orquestador.

Endpoints:
  GET  /health
  GET  /catalogo
  GET  /rubrica/{id}
  POST /resolver
"""

import json
import unicodedata
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="MCP Rubricas UPAO", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent

LINEA_SISTEMAS = "Robótica, Automatización Avanzada y Sistemas Inteligentes"

CATALOGO_METODOLOGICO = {
    "Experimental Puro": "M1",
    "Cuasiexperimental": "M2",
    "Descriptivo Transversal": "M3",
    "Descriptivo Longitudinal": "M4",
    "Cualitativo": "M5",
}

CATALOGO_TECNICO = {
    "Sistemas Inteligentes": "T1",
    "Gestión de Datos e Información": "T2",
    "Inteligencia Artificial": "T3",
    "Sistemas de Información": "T4",
    "Comunicación, Tecnología de la Información e Innovación": "T5",
    "Comunicación TI e Innovación": "T5",
    "Ingeniería de Software": "T6",
    "Sistemas Cognitivos": "T7",
    "Robótica y Automatización Avanzada": "T8",
    "Nanomateriales Funcionales": "T9",
}

# Compatibilidad temporal con nombres antiguos. Esto evita que el backend falle
# si el orquestador todavía detecta una sublínea anterior.
ALIAS_TECNICO = {
    "ingenieria de software y arquitectura de sistemas": "T6",
    "transformacion digital y sistemas empresariales": "T4",
    "gestion de proyectos ti y gobierno de datos": "T5",
    "iot y redes de datos": "T5",
    "machine learning y deep learning": "T3",
    "procesamiento de lenguaje natural": "T7",
    "automatizacion inteligente de procesos": "T8",
    "ia generativa y percepcion computacional": "T3",
    "ingenieria de datos y big data": "T2",
    "business intelligence y aprendizaje estadistico": "T2",
    "auditoria de sistemas y analitica de seguridad": "T4",
}

RUBRICA_LINGUISTICA_ID = "L1"

DIRS = {
    "M": BASE_DIR / "metodologicas",
    "T": BASE_DIR / "tecnicas",
    "L": BASE_DIR / "linguisticas",
}


def _norm(texto: str) -> str:
    texto = (texto or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.replace("ñ", "n")
    return " ".join(texto.split())


def _leer_metadata(rubrica_id: str) -> dict:
    prefix = rubrica_id[0].upper()
    json_path = DIRS[prefix] / f"{rubrica_id}.json"
    if not json_path.exists():
        return {"id": rubrica_id}
    return json.loads(json_path.read_text(encoding="utf-8"))


def _leer_rubrica(rubrica_id: str) -> str:
    """Lee el contenido .md de una rúbrica por ID.

    Para técnicas acepta nombres como T1_sistemas_inteligentes.md.
    """
    rubrica_id = rubrica_id.upper().strip()
    prefix = rubrica_id[0]
    if prefix not in DIRS:
        raise FileNotFoundError(f"Prefijo desconocido: {prefix}")

    folder = DIRS[prefix]
    metadata = _leer_metadata(rubrica_id)

    # 1) Intentar ruta declarada en JSON.
    archivo_md = metadata.get("archivo_md")
    if archivo_md:
        md_path = BASE_DIR / archivo_md
        if md_path.exists():
            return md_path.read_text(encoding="utf-8")

    # 2) Intentar nombre directo T1.md / M1.md / L1.md.
    md_path = folder / f"{rubrica_id}.md"
    if md_path.exists():
        return md_path.read_text(encoding="utf-8")

    # 3) Intentar prefijo T1_*.md.
    matches = sorted(folder.glob(f"{rubrica_id}_*.md"))
    if matches:
        return matches[0].read_text(encoding="utf-8")

    raise FileNotFoundError(f"Rúbrica {rubrica_id} no encontrada en {folder}")


def _resolver_metodologica(diseno: str) -> str:
    if diseno in CATALOGO_METODOLOGICO:
        return CATALOGO_METODOLOGICO[diseno]

    d = _norm(diseno)
    for key, val in CATALOGO_METODOLOGICO.items():
        k = _norm(key)
        if d in k or k in d:
            return val
    if "cualit" in d:
        return "M5"
    if "cuasi" in d:
        return "M2"
    if "experimental" in d and "cuasi" not in d:
        return "M1"
    if "longitudinal" in d:
        return "M4"
    return "M3"


def _resolver_tecnica(sublinea: str) -> str:
    if sublinea in CATALOGO_TECNICO:
        return CATALOGO_TECNICO[sublinea]

    s = _norm(sublinea)
    if s in ALIAS_TECNICO:
        return ALIAS_TECNICO[s]

    for key, val in CATALOGO_TECNICO.items():
        k = _norm(key)
        if s in k or k in s:
            return val

    # Detección por palabras clave para mayor tolerancia.
    if any(x in s for x in ["business intelligence", "bi", "datos", "data", "big data", "warehouse", "etl", "power bi"]):
        return "T2"
    if any(x in s for x in ["inteligencia artificial", "machine learning", "deep learning", "ia", "modelo predictivo"]):
        return "T3"
    if any(x in s for x in ["sistema de informacion", "sistemas de informacion", "auditoria", "seguridad", "iso", "cumplimiento"]):
        return "T4"
    if any(x in s for x in ["comunicacion", "tecnologia de la informacion", "innovacion", "redes", "iot", "cloud"]):
        return "T5"
    if any(x in s for x in ["software", "arquitectura", "aplicacion", "web", "uml"]):
        return "T6"
    if any(x in s for x in ["cognitivo", "nlp", "lenguaje natural", "chatbot", "llm", "agente"]):
        return "T7"
    if any(x in s for x in ["robotica", "automatizacion", "rpa", "sensor", "control"]):
        return "T8"
    if any(x in s for x in ["nanomaterial", "material"]):
        return "T9"
    return "T1"


class ClasificacionRequest(BaseModel):
    enfoque: str
    diseno: str
    linea: str
    sublinea: str


class RubricaResponse(BaseModel):
    rubrica_metodologica_id: str
    rubrica_tecnica_id: str
    rubrica_linguistica_id: str
    rubrica_metodologica: str
    rubrica_tecnica: str
    rubrica_linguistica: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "MCP Rubricas UPAO v3", "linea": LINEA_SISTEMAS}


@app.get("/catalogo")
def catalogo():
    return {
        "linea_investigacion": LINEA_SISTEMAS,
        "metodologicas": CATALOGO_METODOLOGICO,
        "tecnicas": CATALOGO_TECNICO,
        "alias_tecnicos_compatibilidad": ALIAS_TECNICO,
        "linguistica": RUBRICA_LINGUISTICA_ID,
    }


@app.get("/rubrica/{rubrica_id}")
def get_rubrica(rubrica_id: str):
    try:
        rid = rubrica_id.upper()
        return {
            "id": rid,
            "contenido": _leer_rubrica(rid),
            "metadata": _leer_metadata(rid),
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/resolver", response_model=RubricaResponse)
def resolver_rubricas(data: ClasificacionRequest):
    met_id = _resolver_metodologica(data.diseno)
    tec_id = _resolver_tecnica(data.sublinea)
    ling_id = RUBRICA_LINGUISTICA_ID

    try:
        return RubricaResponse(
            rubrica_metodologica_id=met_id,
            rubrica_tecnica_id=tec_id,
            rubrica_linguistica_id=ling_id,
            rubrica_metodologica=_leer_rubrica(met_id),
            rubrica_tecnica=_leer_rubrica(tec_id),
            rubrica_linguistica=_leer_rubrica(ling_id),
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
