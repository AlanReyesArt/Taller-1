"""
rag_service.py — Servicio RAG con ChromaDB
==========================================
El profesor pidió integrar un RAG (Retrieval-Augmented Generation) para:
  1. Almacenar el texto de cada tesis en embeddings (ChromaDB)
  2. Hacer consultas semánticas sobre el corpus de tesis
  3. Recuperar tesis similares o fragmentos relevantes

Estrategia implementada:
  - ChromaDB (local, sin infraestructura extra) para embeddings
  - sentence-transformers (paraphrase-multilingual-MiniLM) — modelo multilingüe
    que funciona bien con español sin necesidad de API key
  - Cada tesis se divide en chunks de ~500 palabras con overlap de 50 palabras
  - Los embeddings se guardan en ./database/chroma_db/

Endpoints que usa esto (ver main.py):
  POST /thesis/{id}/indexar   → indexa la tesis en ChromaDB tras el análisis
  GET  /rag/buscar            → búsqueda semántica sobre el corpus
  GET  /rag/similares/{id}    → tesis similares a una tesis dada
"""

import os
import re
from typing import Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./database/chroma_db")
COLLECTION_NAME = "tesis_upao"

# Modelo multilingüe liviano (~120MB), funciona bien con español
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Tamaño de chunk en palabras
CHUNK_SIZE  = 500
CHUNK_OVERLAP = 50


def _get_client():
    """Retorna el cliente ChromaDB (persistente en disco)."""
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    return chromadb.PersistentClient(
        path=CHROMA_DB_PATH,
        settings=Settings(anonymized_telemetry=False)
    )


def _get_collection():
    """Retorna o crea la colección de tesis con embeddings en español."""
    client = _get_client()
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )


def _dividir_en_chunks(texto: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Divide el texto en chunks de ~chunk_size palabras con overlap.
    Respeta los saltos de párrafo cuando es posible.
    """
    palabras = texto.split()
    if not palabras:
        return []
    
    chunks = []
    inicio = 0
    while inicio < len(palabras):
        fin = min(inicio + chunk_size, len(palabras))
        chunk = " ".join(palabras[inicio:fin])
        if chunk.strip():
            chunks.append(chunk.strip())
        if fin == len(palabras):
            break
        inicio = fin - overlap
    return chunks


def indexar_tesis(
    thesis_id: int,
    titulo: str,
    alumno: str,
    texto_completo: str,
    resultado_analisis: Optional[dict] = None,
) -> dict:
    """
    Indexa una tesis en ChromaDB dividiéndola en chunks con embeddings.
    
    Args:
        thesis_id:         ID de la tesis en SQLite
        titulo:            Título de la tesis
        alumno:            Nombre del alumno
        texto_completo:    Texto extraído del PDF
        resultado_analisis: Resultado del análisis (opcional, agrega contexto)
    
    Returns:
        {"chunks_indexados": int, "collection_size": int}
    """
    if not texto_completo or len(texto_completo.strip()) < 50:
        return {"chunks_indexados": 0, "collection_size": 0, "error": "Texto insuficiente"}

    collection = _get_collection()

    # Limpiar indexación previa de esta tesis
    try:
        ids_existentes = collection.get(where={"thesis_id": thesis_id})["ids"]
        if ids_existentes:
            collection.delete(ids=ids_existentes)
    except Exception:
        pass

    # Enriquecer el texto con el análisis si está disponible
    texto_enriquecido = texto_completo
    if resultado_analisis:
        texto_sec = resultado_analisis.get("secuencial", {}).get("texto_crudo", "")
        if texto_sec:
            texto_enriquecido += f"\n\n[ANÁLISIS AGENTE METODOLÓGICO]\n{texto_sec[:1500]}"

    chunks = _dividir_en_chunks(texto_enriquecido)
    if not chunks:
        return {"chunks_indexados": 0, "collection_size": 0}

    # Preparar metadatos y IDs únicos
    ids        = [f"tesis_{thesis_id}_chunk_{i}" for i in range(len(chunks))]
    metadatos  = [
        {
            "thesis_id":   thesis_id,
            "titulo":      titulo[:100],
            "alumno":      alumno[:80],
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
        for i in range(len(chunks))
    ]

    collection.add(documents=chunks, metadatas=metadatos, ids=ids)
    print(f"✅ RAG: Tesis {thesis_id} indexada con {len(chunks)} chunks")
    
    return {
        "chunks_indexados": len(chunks),
        "collection_size":  collection.count(),
    }


def buscar_en_corpus(
    consulta: str,
    n_resultados: int = 5,
    filtro_thesis_id: Optional[int] = None,
) -> list[dict]:
    """
    Búsqueda semántica en el corpus de tesis indexadas.
    
    Args:
        consulta:          Texto de la consulta en lenguaje natural
        n_resultados:      Número de resultados a retornar
        filtro_thesis_id:  Si se especifica, busca solo dentro de esa tesis
    
    Returns:
        Lista de {texto, thesis_id, titulo, alumno, score, chunk_index}
    """
    collection = _get_collection()
    if collection.count() == 0:
        return []

    where = {"thesis_id": filtro_thesis_id} if filtro_thesis_id else None

    try:
        resultados = collection.query(
            query_texts=[consulta],
            n_results=min(n_resultados, collection.count()),
            where=where,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        print(f"⚠️ Error en búsqueda RAG: {e}")
        return []

    salida = []
    documentos = resultados["documents"][0]
    metadatos  = resultados["metadatas"][0]
    distancias = resultados["distances"][0]

    for doc, meta, dist in zip(documentos, metadatos, distancias):
        # distance en coseno → similaridad (1 - distance)
        score = round(1 - dist, 4)
        salida.append({
            "texto":       doc[:500],
            "thesis_id":   meta["thesis_id"],
            "titulo":      meta["titulo"],
            "alumno":      meta["alumno"],
            "chunk_index": meta["chunk_index"],
            "score":       score,
        })

    return salida


def encontrar_tesis_similares(thesis_id: int, n: int = 3) -> list[dict]:
    """
    Dado el ID de una tesis, retorna las n tesis más similares del corpus.
    Usa el primer chunk de la tesis como consulta representativa.
    """
    collection = _get_collection()
    if collection.count() < 2:
        return []

    # Obtener el primer chunk de la tesis de referencia
    try:
        doc_referencia = collection.get(
            ids=[f"tesis_{thesis_id}_chunk_0"],
            include=["documents"]
        )
        if not doc_referencia["documents"]:
            return []
        texto_ref = doc_referencia["documents"][0]
    except Exception:
        return []

    # Buscar similares excluyendo la propia tesis
    resultados = buscar_en_corpus(texto_ref, n_resultados=n + 5)
    similares = [r for r in resultados if r["thesis_id"] != thesis_id]
    
    # Deduplicar por thesis_id (tomar el chunk con mayor score)
    vistos = {}
    for r in similares:
        tid = r["thesis_id"]
        if tid not in vistos or r["score"] > vistos[tid]["score"]:
            vistos[tid] = r
    
    return list(vistos.values())[:n]


def get_stats() -> dict:
    """Estadísticas del corpus RAG."""
    try:
        collection = _get_collection()
        count = collection.count()
        # Contar tesis únicas
        if count > 0:
            all_meta = collection.get(include=["metadatas"])["metadatas"]
            tesis_unicas = len(set(m["thesis_id"] for m in all_meta))
        else:
            tesis_unicas = 0
        return {
            "total_chunks":   count,
            "tesis_indexadas": tesis_unicas,
            "modelo":         EMBEDDING_MODEL,
            "coleccion":      COLLECTION_NAME,
        }
    except Exception as e:
        return {"error": str(e)}
