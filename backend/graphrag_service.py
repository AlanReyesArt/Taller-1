"""
graphrag_service.py — GraphRAG con NetworkX + ChromaDB
═══════════════════════════════════════════════════════
Sprint 2 / EN-05: Almacenamiento de secciones de tesis en embeddings.

Arquitectura:
  PDF → secciones → embeddings (ChromaDB) → grafo de relaciones (NetworkX)

Esto permite:
  - HU-10: filtrar debate por sección
  - HU-12: buscar errores APA en secciones específicas
  - HU-13: detectar gaps de conocimiento entre secciones relacionadas
  - Benchmarking: coherencia semántica entre secciones (LSA-like via cosine similarity)

NO requiere OpenAI ni API externa — usa sentence-transformers local.
"""

import os
import json
import hashlib
from typing import Optional
import chromadb
from chromadb.utils import embedding_functions
import networkx as nx

# ── Config ────────────────────────────────────────────────────────
CHROMA_PATH = os.getenv("CHROMA_PATH", "./database/chroma")
COLLECTION_NAME = "tesis_secciones"

# Embedding function local (no requiere API key)
_emb_fn = embedding_functions.DefaultEmbeddingFunction()


def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_emb_fn,
        metadata={"hnsw:space": "cosine"},
    )


def _seccion_id(thesis_id: int, nombre_seccion: str) -> str:
    raw = f"{thesis_id}_{nombre_seccion}"
    return hashlib.md5(raw.encode()).hexdigest()


# ── Ingestión ─────────────────────────────────────────────────────

def ingestar_tesis(thesis_id: int, secciones: list[dict]) -> dict:
    """
    Guarda las secciones de una tesis en ChromaDB para búsqueda semántica.

    Args:
        thesis_id: ID de la tesis en SQLite
        secciones: lista de {nombre, contenido, pagina} (de pdf_extractor)

    Returns:
        {"secciones_indexadas": N, "ids": [...]}
    """
    if not secciones:
        return {"secciones_indexadas": 0, "ids": []}

    col = _get_collection()
    ids, docs, metas = [], [], []

    for sec in secciones:
        contenido = sec.get("contenido", "").strip()
        nombre = sec.get("nombre", "Sin título").strip()
        if not contenido or len(contenido) < 30:
            continue
        sid = _seccion_id(thesis_id, nombre)
        ids.append(sid)
        docs.append(contenido[:2000])  # ChromaDB limit
        metas.append({
            "thesis_id": thesis_id,
            "nombre_seccion": nombre,
            "pagina": sec.get("pagina", 0),
        })

    if ids:
        # upsert = no duplicar si ya existe
        col.upsert(ids=ids, documents=docs, metadatas=metas)

    print(f"✅ GraphRAG: {len(ids)} secciones indexadas para tesis {thesis_id}")
    return {"secciones_indexadas": len(ids), "ids": ids}


# ── Consulta semántica ────────────────────────────────────────────

def buscar_secciones(thesis_id: int, query: str, n_results: int = 5) -> list[dict]:
    """
    Busca secciones relacionadas con un query en la tesis.
    Usado por HU-10 (filtrar debate por sección) y HU-13 (detectar gaps).

    Returns:
        [{"nombre_seccion": str, "contenido": str, "distancia": float, "pagina": int}]
    """
    col = _get_collection()
    try:
        results = col.query(
            query_texts=[query],
            n_results=min(n_results, 10),
            where={"thesis_id": thesis_id},
        )
        items = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            dist = results["distances"][0][i] if results.get("distances") else 0.0
            items.append({
                "nombre_seccion": meta.get("nombre_seccion", ""),
                "contenido": doc[:500],
                "distancia": round(dist, 4),
                "pagina": meta.get("pagina", 0),
                "relevancia": round(1 - dist, 4),
            })
        return sorted(items, key=lambda x: x["distancia"])
    except Exception as e:
        print(f"⚠️ Error en búsqueda GraphRAG: {e}")
        return []


# ── Grafo de relaciones entre secciones ──────────────────────────

def construir_grafo(thesis_id: int) -> dict:
    """
    Construye un grafo de relaciones semánticas entre secciones de la tesis.
    Conecta secciones con similitud cosine > 0.4.

    Returns:
        {"nodos": [...], "aristas": [...], "secciones_aisladas": [...]}
    """
    col = _get_collection()
    try:
        res = col.get(where={"thesis_id": thesis_id}, include=["documents", "metadatas"])
    except Exception as e:
        return {"nodos": [], "aristas": [], "secciones_aisladas": [], "error": str(e)}

    if not res["ids"]:
        return {"nodos": [], "aristas": [], "secciones_aisladas": []}

    G = nx.Graph()
    secciones = []

    for i, doc_id in enumerate(res["ids"]):
        meta = res["metadatas"][i]
        nombre = meta.get("nombre_seccion", f"Sección {i+1}")
        G.add_node(doc_id, nombre=nombre, pagina=meta.get("pagina", 0))
        secciones.append({"id": doc_id, "nombre": nombre})

    # Calcular similitudes entre pares de secciones
    docs = res["documents"]
    ids = res["ids"]
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            # Similitud Jaccard simple como proxy (sin GPU)
            words_i = set(docs[i].lower().split())
            words_j = set(docs[j].lower().split())
            if not words_i or not words_j:
                continue
            jaccard = len(words_i & words_j) / len(words_i | words_j)
            if jaccard > 0.08:  # umbral de relación
                G.add_edge(ids[i], ids[j], peso=round(jaccard, 3))

    # Detectar secciones aisladas (sin conexiones = posibles gaps)
    aisladas = [G.nodes[n]["nombre"] for n in G.nodes if G.degree(n) == 0]

    return {
        "nodos": [{"id": n, "nombre": G.nodes[n]["nombre"], "grado": G.degree(n)} for n in G.nodes],
        "aristas": [{"origen": u, "destino": v, "peso": d["peso"]} for u, v, d in G.edges(data=True)],
        "secciones_aisladas": aisladas,
        "densidad_grafo": round(nx.density(G), 4) if G.number_of_nodes() > 1 else 0.0,
    }


# ── Detectar gaps de conocimiento (HU-13) ────────────────────────

def detectar_gaps(thesis_id: int) -> list[dict]:
    """
    HU-13: Detecta vacíos de conocimiento comparando secciones presentes
    con las secciones esperadas para una tesis UPAO.

    Returns:
        [{"seccion_esperada": str, "tipo_gap": str, "sugerencia": str}]
    """
    SECCIONES_REQUERIDAS = {
        "resumen": "Sintetiza el problema, metodología y resultados en máx. 250 palabras.",
        "planteamiento del problema": "Define el problema de investigación con estadísticas de contexto.",
        "objetivos": "Lista objetivo general y específicos con verbos en infinitivo.",
        "hipótesis": "Formula una hipótesis principal falsificable empíricamente.",
        "marco teórico": "Desarrolla el sustento teórico con mínimo 15 referencias APA 7.",
        "metodología": "Describe diseño, población, muestra, instrumentos y procedimiento.",
        "resultados": "Presenta hallazgos con tablas y figuras numeradas.",
        "discusión": "Contrasta resultados con antecedentes del marco teórico.",
        "conclusiones": "Responde cada objetivo específico en un párrafo.",
        "referencias": "Lista todas las fuentes citadas en formato APA 7.",
    }

    col = _get_collection()
    try:
        res = col.get(where={"thesis_id": thesis_id}, include=["metadatas"])
        nombres_presentes = {m.get("nombre_seccion", "").lower() for m in res["metadatas"]}
    except Exception:
        nombres_presentes = set()

    gaps = []
    for seccion, sugerencia in SECCIONES_REQUERIDAS.items():
        presente = any(seccion in nombre for nombre in nombres_presentes)
        if not presente:
            gaps.append({
                "seccion_esperada": seccion.title(),
                "tipo_gap": "teórico" if seccion in ["marco teórico", "hipótesis"] else
                            "metodológico" if seccion in ["metodología", "resultados"] else
                            "estructural",
                "sugerencia": sugerencia,
            })

    return gaps


# ── Coherencia semántica para benchmarking ────────────────────────

def calcular_coherencia(thesis_id: int) -> dict:
    """
    Calcula la coherencia semántica global de la tesis.
    Métrica usada en el benchmarking de arquitecturas.

    Returns:
        {"score": float (0-1), "interpretacion": str, "secciones_evaluadas": int}
    """
    grafo = construir_grafo(thesis_id)
    if not grafo["nodos"]:
        return {"score": 0.0, "interpretacion": "Sin secciones indexadas", "secciones_evaluadas": 0}

    n_nodos = len(grafo["nodos"])
    n_aristas = len(grafo["aristas"])
    densidad = grafo["densidad_grafo"]
    n_aisladas = len(grafo["secciones_aisladas"])

    # Score compuesto: densidad de conexiones - penalización por secciones aisladas
    penalizacion = n_aisladas / n_nodos if n_nodos > 0 else 0
    score = max(0.0, min(1.0, densidad - penalizacion * 0.3))

    interpretacion = (
        "Alta coherencia semántica entre secciones" if score >= 0.7 else
        "Coherencia moderada — revisar transiciones entre secciones" if score >= 0.4 else
        "Baja coherencia — posibles vacíos entre secciones temáticas"
    )

    return {
        "score": round(score, 3),
        "interpretacion": interpretacion,
        "secciones_evaluadas": n_nodos,
        "secciones_aisladas": n_aisladas,
        "densidad_grafo": densidad,
    }
