"""
mcp_client.py — Cliente del Servidor MCP de Rúbricas
=====================================================
El backend llama a este módulo para obtener las rúbricas
que necesita inyectar como tweaks en Langflow.
"""

import httpx
import os
from dotenv import load_dotenv

load_dotenv()

MCP_URL = os.getenv("MCP_RUBRICAS_URL", "http://localhost:8001")
MCP_TIMEOUT = int(os.getenv("MCP_TIMEOUT", "15"))


async def resolver_rubricas(enfoque: str, diseno: str, linea: str, sublinea: str) -> dict | None:
    """
    Llama al MCP de rúbricas y retorna:
    {
      "rubrica_metodologica_id": "M3",
      "rubrica_tecnica_id": "T2",
      "rubrica_linguistica_id": "L1",
      "rubrica_metodologica": "...contenido md...",
      "rubrica_tecnica": "...contenido md...",
      "rubrica_linguistica": "...contenido md..."
    }
    Retorna None si el MCP no está disponible (graceful fallback).
    """
    payload = {
        "enfoque":  enfoque,
        "diseno":   diseno,
        "linea":    linea,
        "sublinea": sublinea,
    }
    try:
        async with httpx.AsyncClient(timeout=MCP_TIMEOUT) as client:
            r = await client.post(f"{MCP_URL}/resolver", json=payload)
            r.raise_for_status()
            data = r.json()
            print(f"✅ MCP rúbricas → {data['rubrica_metodologica_id']} / "
                  f"{data['rubrica_tecnica_id']} / {data['rubrica_linguistica_id']}")
            return data
    except httpx.ConnectError:
        print(f"⚠️  MCP Rúbricas no disponible en {MCP_URL} — se usará rúbrica vacía")
        return None
    except Exception as e:
        print(f"⚠️  Error llamando MCP Rúbricas: {e}")
        return None


async def verificar_mcp() -> tuple[bool, str]:
    """Verifica si el MCP de rúbricas está vivo."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{MCP_URL}/health")
            return (True, "ok") if r.status_code == 200 else (False, f"HTTP {r.status_code}")
    except Exception as e:
        return False, str(e)
