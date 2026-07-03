# Despliegue en Digital Ocean — Guía completa

## Paso 0: Obtener créditos (una sola vez)
1. Ve a https://github.com/education y regístrate con tu correo UPAO (@upao.edu.pe)
2. Sube foto de tu carnet universitario
3. Una vez aprobado (24-48h): crédito de $200 en Digital Ocean por 1 año
4. Crea tu cuenta en https://digitalocean.com usando tu GitHub Student

## Paso 1: Crear el Droplet
```
Tamaño: Basic — $6/mes (1 vCPU, 1GB RAM) — suficiente para la demo
Sistema: Ubuntu 24.04 LTS
Región: San Francisco (más cercano a Perú)
Autenticación: SSH key (la creas en el paso 2)
```

## Paso 2: Conectarse al Droplet
```bash
ssh root@TU_IP_DROPLET
```

## Paso 3: Instalar Docker en el Droplet
```bash
apt update && apt upgrade -y
apt install -y docker.io docker-compose git
systemctl enable docker
systemctl start docker
```

## Paso 4: Subir el proyecto
```bash
# En tu PC local — comprimir sin node_modules
cd C:/Users/user/Pictures/TALLER/TALLER/tesis-v7
zip -r tesis-v7-deploy.zip . --exclude "*/node_modules/*" --exclude "*/__pycache__/*" --exclude "*.pyc"

# Copiar al droplet
scp tesis-v7-deploy.zip root@TU_IP_DROPLET:/root/

# En el droplet
cd /root && unzip tesis-v7-deploy.zip -d tesis-v7
cd tesis-v7
```

## Paso 5: Configurar el .env para producción
```bash
nano backend/.env
```
Cambiar estas líneas:
```
LANGFLOW_URL=http://langflow:7860   # ← dentro de Docker usa el nombre del servicio
DATABASE_URL=sqlite:///./database/tesis.db
CHROMA_PATH=./database/chroma
```

## Paso 6: Configurar vite.config.js para producción
```bash
nano frontend/vite.config.js
```
Cambiar el proxy target:
```js
target: 'http://backend:8000',   // ← nombre del servicio Docker, no localhost
```

## Paso 7: Levantar con Docker Compose
```bash
cd /root/tesis-v7
docker-compose up -d --build
```
Esperar ~5 minutos la primera vez (descarga imágenes).

## Paso 8: Verificar que funciona
```bash
# Ver logs
docker-compose logs -f backend

# Probar el backend
curl http://localhost:8000/health

# Ver todos los contenedores
docker-compose ps
```

## Paso 9: Acceder desde internet
```
Frontend: http://TU_IP_DROPLET:5173
Backend (API docs): http://TU_IP_DROPLET:8000/docs
Langflow: http://TU_IP_DROPLET:7860
```

## Paso 10: Configurar dominio (opcional, con GitHub Student)
GitHub Student te da un dominio .me gratis. Apúntalo a tu IP con un registro A.

## Paso 11: Importar los flujos en Langflow desplegado
1. Abre http://TU_IP_DROPLET:7860
2. My Flows → Import
3. Importa los 4 JSONs de /langflow-flows/
4. Copia los Flow IDs de la URL de cada flujo
5. Actualiza backend/.env con los nuevos IDs
6. `docker-compose restart backend`

---
