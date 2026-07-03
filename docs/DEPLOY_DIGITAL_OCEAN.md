# Guía de Despliegue — Digital Ocean
## Sistema de Deliberación Multiagente UPAO

> **Requisito del profesor:** El sistema debe estar desplegado y funcional para la Semana 11.

---

## 1. Obtener créditos de GitHub Student ($200 en Digital Ocean)

1. Ve a **https://education.github.com/pack** (GitHub Student Developer Pack)
2. Haz clic en **"Get your Student offers"**
3. Inicia sesión con tu cuenta GitHub y verifica con tu **carnet universitario UPAO** (foto)
4. Busca **"DigitalOcean"** en el pack → clic en **"Get access"**
5. Te redirige a Digital Ocean → crea tu cuenta con el email UPAO
6. **$200 de crédito por 1 año** se aplica automáticamente

---

## 2. Crear el Droplet (servidor virtual)

En Digital Ocean → **Create → Droplets**:

| Campo | Valor recomendado |
|-------|------------------|
| Imagen | Ubuntu 24.04 LTS |
| Tamaño | **Basic / Regular · 2 GB RAM · 1 vCPU · 50 GB SSD** (~$12/mes) |
| Región | San Francisco (más cercano a Perú con latencia OK) |
| Autenticación | SSH Key (recomendado) o contraseña |
| Nombre | `tesis-upao-multiagente` |

> Con los $200 de crédito tienes **~16 meses** con este droplet. Más que suficiente para la sustentación.

---

## 3. Conectarte al servidor

```bash
# Desde tu terminal (Windows: usa PowerShell o PuTTY)
ssh root@TU_IP_DEL_DROPLET

# Ejemplo:
ssh root@143.198.45.12
```

---

## 4. Instalar Docker y Docker Compose

```bash
# Actualizar paquetes
apt update && apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# Instalar Docker Compose plugin
apt install docker-compose-plugin -y

# Verificar
docker --version
docker compose version
```

---

## 5. Subir tu proyecto al servidor

**Opción A — desde GitHub (recomendado):**
```bash
# En el servidor
apt install git -y
git clone https://github.com/TU_USUARIO/tesis-system.git
cd tesis-system
```

**Opción B — con SCP (subir el ZIP directamente):**
```bash
# Desde tu computadora local
scp tesis-v7.zip root@TU_IP:/root/
ssh root@TU_IP
unzip tesis-v7.zip
cd tesis-v7
```

---

## 6. Configurar variables de entorno

```bash
# En el servidor, dentro de la carpeta del proyecto
cp .env.example .env
nano .env
```

Edita el `.env` con tus valores reales:

```env
# Langflow
LANGFLOW_URL=http://langflow:7860
LANGFLOW_FLOW_ID_SECUENCIAL=90305752-6095-472a-af6c-d3914a57d5f8
LANGFLOW_FLOW_ID_RED=b75aaa45-5343-4aad-87e6-1fcedcc2a048
LANGFLOW_FLOW_ID_HUMAN_LOOP=033ab925-fc74-49e9-aa17-f328ed7026c9

# API Key de Gemini (o la que uses)
GOOGLE_API_KEY=tu_api_key_real_aqui

# JWT
SECRET_KEY=una_clave_muy_segura_para_produccion_2026
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# RAG
CHROMA_DB_PATH=./database/chroma_db
```

---

## 7. Configurar el docker-compose para producción

Edita `docker-compose.yml` — cambia el frontend para escuchar en el puerto 80:

```yaml
  frontend:
    ports:
      - "80:5173"    # Cambiar de 5173:5173 → 80:5173
```

Y el backend en el puerto 8000 (ya debería estar así):
```yaml
  backend:
    ports:
      - "8000:8000"
```

---

## 8. Levantar el sistema

```bash
docker compose up -d --build
```

> La primera vez tarda ~5-10 minutos (descarga imágenes, instala dependencias del modelo de embeddings).

Verificar que todo esté corriendo:
```bash
docker compose ps
docker compose logs backend --tail=20
```

---

## 9. Abrir los puertos en el firewall de Digital Ocean

En Digital Ocean → tu Droplet → **Networking → Firewall**:

Crear una nueva regla para abrir:
- Puerto **80** (HTTP — Frontend)
- Puerto **8000** (API Backend)
- Puerto **7860** (Langflow — opcional, solo si quieres acceso externo)

---

## 10. Acceder al sistema

Después de levantar, tu sistema estará disponible en:

| Servicio | URL |
|---------|-----|
| **Frontend** | `http://TU_IP` |
| **API Docs (Swagger)** | `http://TU_IP:8000/docs` |
| **Langflow** | `http://TU_IP:7860` |

### Importar los flujos en Langflow (producción)
1. Abre `http://TU_IP:7860`
2. My Flows → Import
3. Sube los 3 JSON: `Arquitectura_Secuencial.json`, `Arquitectura_de_Red.json`, `Arquitectura_HumanLoop.json`
4. En cada flujo, configura tu `GOOGLE_API_KEY`

---

## 11. Dominio propio (opcional pero recomendado para sustentación)

Con el GitHub Student Pack también tienes acceso a un dominio `.me` gratis por 1 año en Namecheap:

1. Ve al pack → busca **Namecheap** → registra `tesis-upao.me` o similar
2. En Namecheap → DNS → agrega un registro A:
   ```
   Type: A
   Host: @
   Value: TU_IP_DROPLET
   ```
3. Espera 10-30 min → tu sistema estará en `http://tesis-upao.me`

---

## 12. Comandos útiles en producción

```bash
# Ver logs en tiempo real
docker compose logs -f backend

# Reiniciar solo el backend (sin bajar todo)
docker compose restart backend

# Actualizar el código
git pull
docker compose up -d --build backend

# Ver uso de recursos
docker stats

# Hacer backup de la base de datos
cp database/tesis.db database/tesis_backup_$(date +%Y%m%d).db
```

---

## Checklist final para la Semana 11

- [ ] Droplet creado y corriendo en Digital Ocean
- [ ] `docker compose ps` muestra todos los contenedores UP
- [ ] `http://TU_IP` abre el login del sistema
- [ ] Puedes iniciar sesión como alumno y como maestro
- [ ] Los 3 flujos Langflow están importados en producción
- [ ] Puedes subir una tesis y ver el análisis completo
- [ ] El maestro puede validar el dictamen
- [ ] RAG indexa automáticamente al terminar el análisis (`/api/rag/stats` retorna datos)
