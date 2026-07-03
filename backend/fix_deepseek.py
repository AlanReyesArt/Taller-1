"""
fix_deepseek.py — Script de diagnóstico y fix del error DeepSeek

Ejecutar desde la carpeta backend:
    python fix_deepseek.py

Lo que hace:
1. Verifica conexión con Langflow
2. Lista los flujos activos y sus modelos
3. Detecta si hay nodos DeepSeek sin API key
4. Sugiere el fix correcto
"""

import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv()

LANGFLOW_URL = os.getenv("LANGFLOW_URL", "http://localhost:7860")
LANGFLOW_API_KEY = os.getenv("LANGFLOW_API_KEY", "")

headers = {}
if LANGFLOW_API_KEY:
    headers["x-api-key"] = LANGFLOW_API_KEY

def check():
    print("=" * 60)
    print("DIAGNÓSTICO DEL ERROR DEEPSEEK")
    print("=" * 60)

    # 1. Verificar Langflow
    try:
        r = httpx.get(f"{LANGFLOW_URL}/api/v1/flows/", headers=headers, timeout=10)
        flows = r.json()
        print(f"\n✅ Langflow conectado — {len(flows)} flujos encontrados\n")
    except Exception as e:
        print(f"\n❌ Langflow no responde: {e}")
        return

    # 2. Buscar flujos con DeepSeek
    flow_id_secuencial = os.getenv("LANGFLOW_FLOW_ID_SECUENCIAL", "")
    
    for flow in flows:
        fid   = flow.get("id", "")
        fname = flow.get("name", "")
        
        # Check nodes for DeepSeek
        try:
            r2 = httpx.get(f"{LANGFLOW_URL}/api/v1/flows/{fid}", headers=headers, timeout=10)
            fdata = r2.json()
            nodes = fdata.get("data", {}).get("nodes", [])
            
            for n in nodes:
                ntype = n["data"]["type"]
                tmpl  = n["data"]["node"].get("template", {})
                
                if "deepseek" in ntype.lower():
                    api_val = tmpl.get("api_key", {}).get("value", "")
                    print(f"⚠️  Flujo '{fname}' ({fid[:8]}...) — nodo DeepSeek encontrado")
                    print(f"   Nodo ID: {n['id']}")
                    print(f"   API key configurada: {'SÍ' if api_val else 'NO ← ESTE ES EL PROBLEMA'}")
                    print()
                
                # Check for deepseek in model selection
                model_opts = tmpl.get("model_name", {})
                if isinstance(model_opts, dict):
                    selected = model_opts.get("value", "")
                    if "deepseek" in str(selected).lower():
                        print(f"⚠️  Flujo '{fname}' — nodo {n['id']} usa modelo DeepSeek: {selected}")
        except:
            pass

    print("\n" + "=" * 60)
    print("SOLUCIONES:")
    print("=" * 60)
    print("""
OPCIÓN A — Volver a Gemini (más fácil, ya tienes la key):
  1. Abre Langflow → flujo Secuencial
  2. Click en cada nodo Agent
  3. Cambia el modelo de DeepSeek → gemini-2.5-flash
  4. En el campo "api_key" pon tu GOOGLE_API_KEY
  5. Guarda y vuelve a intentar

OPCIÓN B — Usar DeepSeek (para tesis más largas, como pidió el profr.):
  1. Crea cuenta en https://platform.deepseek.com
  2. Ve a API Keys → Create API Key
  3. Copia la key (empieza con sk-...)
  4. En el .env agrega: DEEPSEEK_API_KEY=sk-tu_key_aqui
  5. En Langflow → cada nodo DeepSeek → campo "api_key" → pega la key
  6. Guarda y vuelve a intentar

RECOMENDACIÓN: DeepSeek V3 es más barato que Gemini y tiene 64k context
(Gemini 2.5 Flash tiene 128k pero es más caro para tesis largas).
DeepSeek cuesta ~$0.27/M tokens de input vs Gemini ~$0.15/M.
Para una tesis de 16k chars ≈ 4k tokens → ~$0.001 por análisis.
""")

if __name__ == "__main__":
    check()
