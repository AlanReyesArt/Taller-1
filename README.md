# Sistema de Deliberación Multiagente — UPAO

## Arquitectura

El sistema ejecuta **3 flujos Langflow** sobre cada tesis enviada:

| Flujo | Arquitectura | Qué hace | Flow ID |
|-------|-------------|----------|---------|
| Secuencial | Arq. 4 | PDF → Agente Metodológico → Técnico → Lingüístico → JSON | `90305752-6095-472a-af6c-d3914a57d5f8` |
| De Red | Arq. 3 | Los 3 agentes debaten y el Agente Consenso sintetiza | `b75aaa45-5343-4aad-87e6-1fcedcc2a048` |
| Human-Loop | Arq. 2 | Genera el dictamen y lo pausa para validación del docente | `033ab925-fc74-49e9-aa17-f328ed7026c9` |

## Setup

### 1. Variables de entorno
```bash
cp .env.example .env
# Edita .env y pon tu GOOGLE_API_KEY
```

### 2. Importar los flujos en Langflow
Abre Langflow (http://localhost:7860) → My Flows → Import y sube los 3 JSON:
- `Arquitectura_Secuencial.json`
- `Arquitectura_de_Red.json`
- `tesis-arquitectura_Human-in-the-loop.json`

⚠️ Los IDs de los flujos ya están hardcodeados en `langflow_service.py` y en `.env.example`.
Si Langflow les asigna IDs distintos al importar, actualiza el `.env`.

### 3. Configurar API Key en Langflow
En cada flujo dentro de Langflow, abre los nodos de Google Generative AI
y pon tu `GOOGLE_API_KEY` (o configúrala como variable global en Langflow Settings).

### 4. Levantar con Docker
```bash
docker-compose up --build
```

- Frontend: http://localhost:5173
- Backend:  http://localhost:8000
- Langflow: http://localhost:7860

### Usuarios de prueba
| Email | Password | Rol |
|-------|----------|-----|
| alumno@upao.edu.pe | alumno123 | alumno |
| maestro@upao.edu.pe | maestro123 | maestro |

## Por qué fallaba antes

El backend enviaba el texto del PDF como `input_value` en JSON, pero los 3 flujos
Langflow tienen nodos **File** como entrada — esperan un archivo, no texto plano.

**Solución implementada:**
1. El PDF se sube a Langflow vía `POST /api/v1/files/upload/{flow_id}`
2. Langflow devuelve un `file_path` interno
3. Se inyecta ese path en el nodo File del flujo vía `tweaks`
4. Se llama `POST /api/v1/run/{flow_id}` con esos tweaks
