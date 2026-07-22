import pytest
import os
from fastapi.testclient import TestClient
from jose import jwt, JWTError
from fastapi import HTTPException

from main import app
from auth import (
    hash_password, verify_password, 
    create_access_token, decode_token,
    SECRET_KEY, ALGORITHM
)
from pdf_extractor import validar_pdf, _normalizar

@pytest.fixture(scope="module")
def client():
    # Instanciar el TestClient dentro del contexto asegura que los eventos
    # de startup (como inicializar la DB SQLite) se resuelvan correctamente.
    with TestClient(app) as c:
        yield c


# =====================================================================
# SECCIÓN 1: PRUEBAS DE RED Y ENDPOINTS (3 Tests)
# =====================================================================

def test_health_endpoint(client):
    """CP-U01: Verifica que el servidor levanta y el Event Loop responde al ping básico."""
    print("\n[TEST] Ejecutando CP-U01: Ping de Red al servidor FastAPI...")
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    print("       -> Servidor vivo y respondiendo HTTP 200 OK.")

def test_diagnostico_endpoint(client):
    """CP-U02: Verifica el endpoint de estado de conexión a Langflow y MCP."""
    print("\n[TEST] Ejecutando CP-U02: Verificando integraciones de IA (Langflow/MCP)...")
    response = client.get("/diagnostico")
    assert response.status_code == 200
    data = response.json()
    assert "langflow_reachable" in data
    print(f"       -> Conexión a Langflow verificada. Estado: {data['langflow_reachable']}")

def test_login_credenciales_invalidas(client):
    """CP-U03: Verifica que el endpoint de autenticación rechace usuarios no existentes."""
    print("\n[TEST] Ejecutando CP-U03: Intentando login con cuenta falsa...")
    response = client.post("/auth/login", data={"username": "hacker@upao.edu.pe", "password": "123"})
    assert response.status_code == 401
    assert "Credenciales incorrectas" in response.json()["detail"]
    print("       -> El sistema bloqueó correctamente el acceso (HTTP 401).")


# =====================================================================
# SECCIÓN 2: PRUEBAS DE SEGURIDAD Y CRIPTOGRAFÍA (4 Tests)
# =====================================================================

def test_password_hashing_match():
    """CP-U04: Valida que bcrypt encripte correctamente y reconozca la misma contraseña."""
    print("\n[TEST] Ejecutando CP-U04: Encriptando contraseña con Bcrypt...")
    password = "tesis_upao_2026"
    hash_pass = hash_password(password)
    assert hash_pass != password
    assert verify_password(password, hash_pass) is True
    print("       -> Contraseña encriptada y validada matemáticamente con éxito.")

def test_password_hashing_mismatch():
    """CP-U05: Valida que bcrypt rechace contraseñas que no coinciden con el hash."""
    print("\n[TEST] Ejecutando CP-U05: Forzando fallo matemático en Bcrypt...")
    password = "tesis_upao_2026"
    hash_pass = hash_password(password)
    assert verify_password("clave_equivocada", hash_pass) is False
    print("       -> Bcrypt rechazó la contraseña incorrecta, manteniendo la seguridad.")

def test_create_and_decode_jwt():
    """CP-U06: Prueba el flujo completo de emisión y apertura de tokens JWT."""
    print("\n[TEST] Ejecutando CP-U06: Firmando y decodificando token JWT...")
    payload_original = {"sub": "alumno@upao.edu.pe", "rol": "alumno"}
    token = create_access_token(data=payload_original)
    
    payload_decodificado = decode_token(token)
    assert payload_decodificado["sub"] == "alumno@upao.edu.pe"
    assert payload_decodificado["rol"] == "alumno"
    print("       -> JWT firmado, decodificado y la data interna está intacta.")

def test_decode_invalid_jwt():
    """CP-U07: Valida que el sistema rechace un token JWT manipulado o falso."""
    print("\n[TEST] Ejecutando CP-U07: Intentando inyectar un Token falso...")
    token_falso = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.falso.firma"
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token_falso)
    assert exc_info.value.status_code == 401
    print("       -> Excepción HTTP 401 capturada. El sistema no permite firmas falsas.")


# =====================================================================
# SECCIÓN 3: PRUEBAS DE UTILIDADES Y PROCESAMIENTO (3 Tests)
# =====================================================================

def test_validar_pdf_invalido(tmp_path):
    """CP-U08: Valida que PyMuPDF rechace archivos que no cumplen la firma hexadecimal PDF."""
    print("\n[TEST] Ejecutando CP-U08: Inyectando archivo de texto camuflado como PDF...")
    dummy_file = tmp_path / "falso.pdf"
    dummy_file.write_text("Esto es texto plano puro, no un PDF real.")
    
    es_valido, error = validar_pdf(str(dummy_file))
    assert es_valido is False
    assert "error" in error.lower() or "inválido" in error.lower() or "cannot" in error.lower()
    print("       -> PyMuPDF detectó el fraude y bloqueó el archivo corrupto.")

def test_normalizacion_texto():
    """CP-U09: Valida que el motor de limpieza quite saltos de línea y espacios extra."""
    print("\n[TEST] Ejecutando CP-U09: Limpiando ruido del extractor de texto...")
    texto_sucio = "   Hola \n\n mundo  \t\t esto   es   una   tesis.   "
    texto_limpio = _normalizar(texto_sucio)
    assert texto_limpio == "Hola mundo esto es una tesis."
    print("       -> El texto quedó pulido y estandarizado para enviar a Langflow.")

def test_validar_ruta_inexistente():
    """CP-U10: Valida el manejo de excepciones cuando el sistema no encuentra el archivo."""
    print("\n[TEST] Ejecutando CP-U10: Intentando procesar un archivo fantasma...")
    ruta_fantasma = "C:/ruta/inventada/tesis_que_no_existe.pdf"
    es_valido, error = validar_pdf(ruta_fantasma)
    assert es_valido is False
    assert error is not None
    print("       -> El sistema capturó el error I/O de disco limpiamente.")
