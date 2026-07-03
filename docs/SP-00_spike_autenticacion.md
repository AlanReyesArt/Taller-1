# SP-00: Spike — Autenticación JWT vs Cookie de Sesión
**Entregable obligatorio del Spike** · Sprint 1 · EP-00

---

## 1. Objetivo
Evaluar las dos estrategias de autenticación más comunes para una API REST con FastAPI y elegir la más adecuada para el sistema de análisis de tesis UPAO.

---

## 2. Opciones Evaluadas

### Opción A: JWT (JSON Web Token)
El servidor genera un token firmado que el cliente almacena y envía en cada request en el header `Authorization: Bearer <token>`.

| Criterio | Evaluación |
|---|---|
| Stateless (sin estado en servidor) | ✅ Sí — el servidor no almacena sesiones |
| Escalabilidad | ✅ Alta — funciona bien con múltiples instancias |
| Compatibilidad con React SPA | ✅ Nativa — axios interceptors |
| Compatibilidad con APIs REST | ✅ Estándar de facto |
| Revocación de tokens | ⚠️ Requiere blacklist en BD si se necesita |
| Implementación en FastAPI | ✅ python-jose + OAuth2PasswordBearer |
| Expiración configurable | ✅ Sí — campo `exp` en el payload |

### Opción B: Sesiones por Cookie (server-side sessions)
El servidor guarda la sesión en memoria o base de datos y envía una cookie al cliente.

| Criterio | Evaluación |
|---|---|
| Stateless | ❌ No — el servidor guarda el estado |
| Escalabilidad | ⚠️ Baja sin Redis o BD compartida |
| Compatibilidad con React SPA | ⚠️ Requiere configuración CORS especial |
| Compatibilidad con APIs REST | ⚠️ No es el estándar para APIs |
| Revocación | ✅ Inmediata — eliminar sesión del servidor |
| Implementación en FastAPI | ⚠️ Requiere librería adicional (starlette-sessions) |

---

## 3. Decisión

**✅ Estrategia elegida: JWT con FastAPI OAuth2**

**Justificación:**
1. El frontend es una SPA en React — los tokens JWT se manejan nativamente con axios interceptors
2. La API REST es stateless por diseño — JWT mantiene esa coherencia
3. Para una PoC académica, la revocación de tokens no es un requerimiento crítico
4. FastAPI tiene soporte nativo para OAuth2 con `OAuth2PasswordBearer` + `python-jose`
5. Expiración de 8 horas según el criterio de aceptación de HU-01

---

## 4. Implementación

**Librerías utilizadas:**
- `python-jose[cryptography]` — generación y verificación de JWT
- `passlib[bcrypt]` — hash seguro de contraseñas
- `python-multipart` — para recibir el form de login (OAuth2 estándar)

**Flujo de autenticación:**
```
POST /auth/login (email + password en form-data)
  → Verifica contraseña con bcrypt
  → Genera JWT con {sub: email, rol: alumno|maestro, exp: +8h}
  → Retorna {access_token, rol, nombre, user_id}

Requests protegidos:
  → Header: Authorization: Bearer <token>
  → FastAPI verifica firma del JWT
  → Extrae rol y verifica permisos
  → 401 si token inválido o expirado
  → 403 si rol no autorizado
```

**Criterios de aceptación verificados:**
- ✅ Endpoint POST /auth/login devuelve token válido
- ✅ Middleware protege rutas según rol (alumno vs maestro)
- ✅ Token expira en 8 horas
- ✅ Contraseñas almacenadas con bcrypt (no en texto plano)
- ✅ Acceso al panel docente denegado para alumnos (403)

---

*Elaborado por: Gastañuadi Lescano Raul Andrés | Sprint 1 | Mayo 2026*
