import os

code_to_add = '''
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
        return f"{{\\"error\\": \\"{str(e)}\\"}}"

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
        
    user_consenso = f"Dictamen Metodologico:\\n{res_m}\\n\\nDictamen Tecnico:\\n{res_t}\\n\\nDictamen Linguistico:\\n{res_l}"
    
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
'''

with open('backend/langflow_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

if '_simular_agente_deepseek' not in content:
    with open('backend/langflow_service.py', 'a', encoding='utf-8') as f:
        f.write('\n\n' + code_to_add)
    print('Added simulation functions')
else:
    print('Simulation functions already exist')
