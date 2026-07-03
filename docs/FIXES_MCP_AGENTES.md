# Fixes Aplicados — MCP + Agentes

## Problema 1: MCP no conectaba
**Causa:** Los Node IDs en el código eran incorrectos (IDs de una versión anterior).
**Fix:** `langflow_service.py` — Node IDs actualizados a los reales del flujo JSON:
- `NODE_PROMPT_METODOLOGICO` = `Prompt Template-AW4sI`
- `NODE_PROMPT_TECNICO`      = `Prompt Template-2bxBm`
- `NODE_PROMPT_LINGUISTICO`  = `Prompt Template-c4phv`
- `NODE_AGENT_METODOLOGICO`  = `Agent-Cobkg`
- etc.

**Cómo activar el MCP:** Solo necesitas que Docker Compose esté corriendo.
El contenedor `tesis_mcp_rubricas` ya se define en `docker-compose.yml`.
Al hacer `docker compose up`, el MCP sube automáticamente en `http://mcp-rubricas:8001`.

## Problema 2: Los 3 agentes mostraban el mismo JSON (el del Consenso)
**Causa:** El flujo Secuencial devuelve solo el último output (Consenso). El frontend
mostraba ese mismo texto en las 3 tarjetas.
**Fix:** 
- `langflow_service.py` → función `_extraer_todos_los_outputs()` que parsea todos
  los outputs del flujo y los clasifica por `agente` field del JSON.
- `main.py` → guarda `agentes: {metodologico, tecnico, linguistico, consenso}` en BD.
- `Dashboard.jsx` → lee `r.agentes.metodologico`, `r.agentes.tecnico`, etc.

## Problema 3: Los agentes no devolvían JSON estructurado
**Causa:** Los system prompts no pedían formato JSON explícito.
**Fix:** Prompts actualizados en `Arq_Secuencial_updated.json` — cada agente ahora:
1. Tiene instrucciones claras de formato JSON
2. Sabe que debe responder SOLO JSON sin backticks
3. Conoce los campos exactos requeridos (id, estado, puntos_max, puntos_obtenidos, evidencia)

## Para aplicar:
1. En Langflow: elimina el flujo Secuencial actual e importa `langflow-flows/Arq_Secuencial_updated.json`
2. Haz `docker compose down && docker compose up --build`
3. Verifica en logs: `✅ MCP rúbricas → M4 / T10 / L1`
