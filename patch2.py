import re

with open('backend/langflow_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Modificar ejecutar_analisis_completo (Secuencial)
# Buscar: resultado_secuencial = await _ejecutar_flujo(\n        "Secuencial",\n        FLOW_ID_SECUENCIAL,\n        texto,\n        tweaks if tweaks else None,\n    )
# Reemplazar con _simular_flujo_jerarquico_secuencial
sec_pattern = r'resultado_secuencial = await _ejecutar_flujo\(\s*"Secuencial",\s*FLOW_ID_SECUENCIAL,\s*texto,\s*tweaks if tweaks else None,?\s*\)'
sec_replacement = '''print("🔄 [3/3] Simulando Flujo Secuencial en Python puro...")
    resultado_secuencial = await _simular_flujo_jerarquico_secuencial(texto, datos_mcp or {}, diseno_info, False)'''
content = re.sub(sec_pattern, sec_replacement, content, count=1)

# 2. Modificar ejecutar_veredicto (Jerarquico)
jer_pattern = r'resultado_jerarquico = await _ejecutar_flujo\(\s*"Jerarquico",\s*FLOW_ID_JERARQUICO,\s*texto,\s*tweaks if tweaks else None,?\s*\)'
jer_replacement = '''print("🔄 [3/3] Simulando Flujo Jerárquico en Python puro...")
    resultado_jerarquico = await _simular_flujo_jerarquico_secuencial(texto, datos_mcp or {}, diseno_info, True)'''
content = re.sub(jer_pattern, jer_replacement, content, count=1)

# 3. Modificar ejecutar_human_loop
human_pattern = r'return await _ejecutar_flujo\(\s*"HumanLoop",\s*FLOW_ID_HUMAN_LOOP,\s*payload,\s*tweaks,?\s*\)'
human_replacement = '''print("🔄 Simulando Flujo Human-in-the-Loop en Python puro...")
    system_prompt = tweaks[NODE_HUMAN_AGENT_FINAL]["system_prompt"]
    return await _simular_flujo_human_loop(payload, system_prompt)'''
content = re.sub(human_pattern, human_replacement, content, count=1)

with open('backend/langflow_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied to replace _ejecutar_flujo calls.")
