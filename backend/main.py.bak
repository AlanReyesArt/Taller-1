"""
main.py — FastAPI
═══════════════════════════════════════════════════════════════════
Endpoints según el flujo de la UI:

  ALUMNO:
    POST /thesis/upload                  → sube PDF
    POST /thesis/{id}/analisis-completo  → corre flujo Secuencial
    POST /thesis/{id}/veredicto          → corre flujo Jerárquico
    GET  /thesis/{id}/result             → polling de estado + resultado
    GET  /thesis/                        → historial del alumno
    GET  /thesis/{id}/report             → descarga PDF del reporte

  DOCENTE:
    GET  /maestro/tesis                  → lista todas las tesis
    GET  /maestro/tesis/{id}/result      → ve el análisis completo
    POST /maestro/tesis/{id}/validar     → corre Human-Loop con su instrucción
                                           y guarda su decisión (aprobado/rechazado)
"""

import os
import json
from datetime import datetime
from typing import Optional

from fastapi import (
    FastAPI, Depends, HTTPException, status,
    UploadFile, File, Form, BackgroundTasks, Header
)
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import User, Thesis, AnalysisResult, init_db, engine
from auth import verify_password, create_access_token, get_current_user, require_rol, get_db
from pdf_extractor import extraer_texto_pdf, validar_pdf, extraer_capitulos, construir_input_langflow
from langflow_service import (
    ejecutar_analisis_completo,
    ejecutar_veredicto,
    ejecutar_debate_red,
    ejecutar_human_loop,
    verificar_langflow,
    LANGFLOW_URL,
    FLOW_ID_SECUENCIAL,
    FLOW_ID_JERARQUICO,
    FLOW_ID_HUMAN_LOOP,
    FLOW_ID_RED,
)
from pdf_report import generar_reporte_estructural

UPLOAD_DIR = "./uploads/tesis"
MAX_FILE_SIZE_MB = 20
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="Sistema Multiagente UPAO",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    init_db()
    print("🚀 Sistema iniciado")


# ── Schemas ───────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: str
    nombre: str
    user_id: int

class UserResponse(BaseModel):
    id: int
    email: str
    nombre: str
    rol: str
    class Config:
        from_attributes = True

class ThesisResponse(BaseModel):
    id: int
    titulo: str
    filename: str
    estado: str
    created_at: datetime
    class Config:
        from_attributes = True

class AnalysisResponse(BaseModel):
    thesis_id: int
    estado: str
    resultado: Optional[dict] = None
    latencia_ms: Optional[int] = None
    tokens_enviados: Optional[int] = None

class ValidarRequest(BaseModel):
    decision: str               # "aprobado" | "aprobado_con_cambios" | "rechazado"
    comentario: Optional[str] = None


# ── Health / Diagnóstico ──────────────────────────────────────────

@app.get("/health", tags=["Sistema"])
async def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/diagnostico", tags=["Sistema"])
async def diagnostico():
    from mcp_client import verificar_mcp
    lf_ok, lf_msg = await verificar_langflow()
    mcp_ok, mcp_msg = await verificar_mcp()
    return {
        "langflow_url": LANGFLOW_URL,
        "langflow_reachable": lf_ok,
        "langflow_status": lf_msg,
        "mcp_rubricas_url": os.getenv("MCP_RUBRICAS_URL", "http://localhost:8001"),
        "mcp_rubricas_reachable": mcp_ok,
        "mcp_rubricas_status": mcp_msg,
        "flows": {
            "secuencial":  FLOW_ID_SECUENCIAL,
            "jerarquico":  FLOW_ID_JERARQUICO,
            "human_loop":  FLOW_ID_HUMAN_LOOP,
            "red":         FLOW_ID_RED or "⚠️ No configurado — agrega LANGFLOW_FLOW_ID_RED en .env",
        },
        "google_api_key_set": bool(os.getenv("GOOGLE_API_KEY")),
        "langflow_api_key_set": bool(os.getenv("LANGFLOW_API_KEY")),
    }


# ── Auth ──────────────────────────────────────────────────────────

@app.post("/auth/login", response_model=TokenResponse, tags=["Auth"])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Cuenta desactivada")
    token = create_access_token(data={"sub": user.email, "rol": user.rol})
    return TokenResponse(access_token=token, rol=user.rol, nombre=user.nombre, user_id=user.id)


@app.get("/auth/me", response_model=UserResponse, tags=["Auth"])
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ── Upload ────────────────────────────────────────────────────────

@app.post("/thesis/upload", response_model=ThesisResponse, tags=["Tesis"])
async def upload_thesis(
    titulo: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_rol("alumno")),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    contenido = await file.read()
    if len(contenido) / (1024 * 1024) > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"El archivo supera los {MAX_FILE_SIZE_MB}MB")

    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    filename_seguro = f"{current_user.id}_{ts}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename_seguro)

    with open(filepath, "wb") as f:
        f.write(contenido)

    es_valido, error_msg = validar_pdf(filepath)
    if not es_valido:
        os.remove(filepath)
        raise HTTPException(status_code=400, detail=error_msg)

    tesis = Thesis(
        titulo=titulo,
        filename=file.filename,
        filepath=filepath,
        alumno_id=current_user.id,
        estado="subido",
    )
    db.add(tesis)
    db.commit()
    db.refresh(tesis)
    return tesis


# ── Análisis completo (Flujo Secuencial) ─────────────────────────

@app.post("/thesis/{thesis_id}/analisis-completo", response_model=AnalysisResponse, tags=["Tesis"])
async def analisis_completo(
    thesis_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_rol("alumno")),
    db: Session = Depends(get_db),
):
    """Botón 'Análisis completo' — corre el flujo Secuencial."""
    tesis = _get_tesis_alumno(thesis_id, current_user.id, db)
    if tesis.estado == "en_analisis":
        raise HTTPException(status_code=400, detail="Ya está siendo analizada")

    _limpiar_analisis_previo(thesis_id, db)
    tesis.estado = "en_analisis"
    db.commit()

    background_tasks.add_task(
        _bg_analisis_completo, thesis_id=thesis_id, filepath=tesis.filepath
    )
    return AnalysisResponse(thesis_id=thesis_id, estado="en_analisis")


async def _bg_analisis_completo(thesis_id: int, filepath: str):
    with Session(engine) as db:
        tesis = db.query(Thesis).filter(Thesis.id == thesis_id).first()
        if not tesis:
            return
        try:
            metadata_pdf = _metadata_pdf(filepath)
            flujos = await ejecutar_analisis_completo(filepath)

            resultado = {
                "tipo": "analisis_completo",
                "metadata_pdf": metadata_pdf,
                "hash_archivo": flujos.get("hash_archivo", ""),
                "latencia_total_ms": flujos.get("latencia_total_ms", 0),
                "secuencial": flujos["secuencial"],
                "agentes": flujos.get("agentes", {}),   # outputs parseados por agente
                "exito_general": flujos.get("exito_general", False),
                # Nuevos campos: diseño detectado y rúbricas usadas
                "diseno_info":  flujos.get("diseno_info"),
                "rubricas_ids": flujos.get("rubricas_ids"),
            }

            _guardar_analisis(db, tesis, resultado, metadata_pdf, flujos.get("latencia_total_ms", 0))
            tesis.estado = "pendiente_validacion" if flujos["exito_general"] else "error"
            db.commit()
            print(f"✅ Análisis completo tesis {thesis_id} — {'OK' if flujos['exito_general'] else 'ERROR'}")
            # Auto-indexar en ChromaDB (RAG)
            try:
                from rag_service import indexar_tesis as _indexar
                alumno_obj = db.query(User).filter(User.id == tesis.alumno_id).first()
                texto_rag = _extraer_texto_tesis(tesis.filepath)
                if texto_rag:
                    _indexar(thesis_id, tesis.titulo, alumno_obj.nombre if alumno_obj else "—", texto_rag, resultado)
                    print(f"✅ RAG: Tesis {thesis_id} indexada automáticamente")
            except Exception as rag_err:
                print(f"⚠️ RAG indexing falló (no crítico): {rag_err}")
        except Exception as e:
            tesis.estado = "error"
            db.commit()
            print(f"❌ Error análisis completo tesis {thesis_id}: {e}")


# ── Veredicto (Flujo Jerárquico) ─────────────────────────────────

@app.post("/thesis/{thesis_id}/veredicto", response_model=AnalysisResponse, tags=["Tesis"])
async def obtener_veredicto(
    thesis_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_rol("alumno")),
    db: Session = Depends(get_db),
):
    """Botón 'Obtener veredicto' — corre el flujo Jerárquico."""
    tesis = _get_tesis_alumno(thesis_id, current_user.id, db)
    if tesis.estado == "en_analisis":
        raise HTTPException(status_code=400, detail="Ya está siendo analizada")

    _limpiar_analisis_previo(thesis_id, db)
    tesis.estado = "en_analisis"
    db.commit()

    background_tasks.add_task(
        _bg_veredicto, thesis_id=thesis_id, filepath=tesis.filepath
    )
    return AnalysisResponse(thesis_id=thesis_id, estado="en_analisis")


async def _bg_veredicto(thesis_id: int, filepath: str):
    with Session(engine) as db:
        tesis = db.query(Thesis).filter(Thesis.id == thesis_id).first()
        if not tesis:
            return
        try:
            metadata_pdf = _metadata_pdf(filepath)
            flujos = await ejecutar_veredicto(filepath)

            resultado = {
                "tipo": "veredicto",
                "metadata_pdf": metadata_pdf,
                "hash_archivo": flujos.get("hash_archivo", ""),
                "latencia_total_ms": flujos.get("latencia_total_ms", 0),
                "jerarquico": flujos["jerarquico"],
                "diseno_info": flujos.get("diseno_info"),
                "rubricas_ids": flujos.get("rubricas_ids", {}),
                "rubricas_detalle": flujos.get("rubricas_detalle", {}),
                "exito_general": flujos.get("exito_general", False),
            }

            _guardar_analisis(db, tesis, resultado, metadata_pdf, flujos.get("latencia_total_ms", 0))
            tesis.estado = "pendiente_validacion" if flujos["exito_general"] else "error"
            db.commit()
            print(f"✅ Veredicto tesis {thesis_id} — {'OK' if flujos['exito_general'] else 'ERROR'}")
        except Exception as e:
            tesis.estado = "error"
            db.commit()
            print(f"❌ Error veredicto tesis {thesis_id}: {e}")


# ── Debate entre Agentes (Flujo Red) — Sprint 2 / EP-02 ──────────

@app.post("/thesis/{thesis_id}/debate-red", response_model=AnalysisResponse, tags=["Tesis"])
async def debate_red(
    thesis_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_rol("alumno")),
    db: Session = Depends(get_db),
):
    """
    Sprint 2 — EP-02: Debate circular entre Agente Metodológico y Agente Técnico.
    Usa el flujo ARQ_RED de Langflow (máx. 3 rondas, contador de iteraciones).
    Requiere LANGFLOW_FLOW_ID_RED en el .env.
    """
    if not FLOW_ID_RED:
        raise HTTPException(
            status_code=503,
            detail="Flujo ARQ_RED no configurado. Agrega LANGFLOW_FLOW_ID_RED en backend/.env tras importar el flujo en Langflow."
        )

    tesis = _get_tesis_alumno(thesis_id, current_user.id, db)
    if tesis.estado == "en_analisis":
        raise HTTPException(status_code=400, detail="Ya está siendo analizada")

    _limpiar_analisis_previo(thesis_id, db)
    tesis.estado = "en_analisis"
    db.commit()

    background_tasks.add_task(
        _bg_debate_red, thesis_id=thesis_id, filepath=tesis.filepath
    )
    return AnalysisResponse(thesis_id=thesis_id, estado="en_analisis")


async def _bg_debate_red(thesis_id: int, filepath: str):
    with Session(engine) as db:
        tesis = db.query(Thesis).filter(Thesis.id == thesis_id).first()
        if not tesis:
            return
        try:
            metadata_pdf = _metadata_pdf(filepath)
            flujos = await ejecutar_debate_red(filepath)

            resultado = {
                "tipo": "debate_red",
                "metadata_pdf": metadata_pdf,
                "hash_archivo": flujos.get("hash_archivo", ""),
                "latencia_total_ms": flujos.get("latencia_total_ms", 0),
                "red": flujos["red"],
                "exito_general": flujos.get("exito_general", False),
            }

            _guardar_analisis(db, tesis, resultado, metadata_pdf, flujos.get("latencia_total_ms", 0))
            tesis.estado = "pendiente_validacion" if flujos["exito_general"] else "error"
            db.commit()
            print(f"✅ Debate Red tesis {thesis_id} — {'OK' if flujos['exito_general'] else 'ERROR'}")
        except Exception as e:
            tesis.estado = "error"
            db.commit()
            print(f"❌ Error debate red tesis {thesis_id}: {e}")


# ── Resultado (polling) ───────────────────────────────────────────

@app.get("/thesis/{thesis_id}/result", response_model=AnalysisResponse, tags=["Tesis"])
async def get_result(
    thesis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tesis = db.query(Thesis).filter(Thesis.id == thesis_id).first()
    if not tesis:
        raise HTTPException(status_code=404, detail="Tesis no encontrada")
    if current_user.rol == "alumno" and tesis.alumno_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sin acceso")

    analisis = db.query(AnalysisResult).filter(AnalysisResult.thesis_id == thesis_id).first()
    return AnalysisResponse(
        thesis_id=thesis_id,
        estado=tesis.estado,
        resultado=json.loads(analisis.resultado_json) if analisis else None,
        latencia_ms=analisis.latencia_ms if analisis else None,
        tokens_enviados=analisis.tokens_enviados if analisis else None,
    )


@app.get("/thesis/", tags=["Tesis"])
async def get_my_thesis(
    current_user: User = Depends(require_rol("alumno")),
    db: Session = Depends(get_db),
):
    lista = db.query(Thesis).filter(Thesis.alumno_id == current_user.id).order_by(Thesis.created_at.desc()).all()
    return [
        {
            "id": t.id, "titulo": t.titulo, "filename": t.filename,
            "estado": t.estado, "created_at": t.created_at.isoformat(),
            "latencia_ms": (db.query(AnalysisResult).filter(AnalysisResult.thesis_id == t.id).first() or type('', (), {'latencia_ms': None})()).latencia_ms,
        }
        for t in lista
    ]


@app.get("/thesis/{thesis_id}/report", tags=["Tesis"])
async def download_report(
    thesis_id: int,
    token: Optional[str] = None,
    authorization: Optional[str] = Header(None),   # acepta Bearer token en header
    db: Session = Depends(get_db),
):
    # Acepta token via ?token= (window.open) O via Authorization: Bearer (fetch)
    raw_token = token
    if not raw_token and authorization:
        # Authorization: Bearer xxxxx
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            raw_token = parts[1]
    if not raw_token:
        raise HTTPException(status_code=401, detail="Token requerido")
    from auth import decode_token
    from models import User
    try:
        payload = decode_token(raw_token)
        email = payload.get("sub")
        current_user = db.query(User).filter(User.email == email).first()
        if not current_user:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")

    tesis = _get_tesis_alumno(thesis_id, current_user.id, db)
    analisis = db.query(AnalysisResult).filter(AnalysisResult.thesis_id == thesis_id).first()
    if not analisis:
        raise HTTPException(status_code=400, detail="Sin resultado de análisis")
    pdf_path = generar_reporte_estructural(
        thesis_id=thesis_id,
        nombre_alumno=current_user.nombre,
        titulo_tesis=tesis.titulo,
        resultado_analisis=json.loads(analisis.resultado_json),
    )
    return FileResponse(path=pdf_path, filename=f"reporte_{thesis_id}.pdf", media_type="application/pdf")


# ── Panel Docente ─────────────────────────────────────────────────

@app.get("/maestro/tesis", tags=["Maestro"])
async def get_all_tesis(
    current_user: User = Depends(require_rol("maestro")),
    db: Session = Depends(get_db),
):
    lista = db.query(Thesis).order_by(Thesis.created_at.desc()).all()
    return [
        {
            "id": t.id, "titulo": t.titulo,
            "alumno": (db.query(User).filter(User.id == t.alumno_id).first() or type('', (), {'nombre': '—'})()).nombre,
            "estado": t.estado,
            "created_at": t.created_at.isoformat(),
        }
        for t in lista
    ]


@app.get("/maestro/tesis/{thesis_id}/result", tags=["Maestro"])
async def get_result_maestro(
    thesis_id: int,
    current_user: User = Depends(require_rol("maestro")),
    db: Session = Depends(get_db),
):
    tesis = db.query(Thesis).filter(Thesis.id == thesis_id).first()
    if not tesis:
        raise HTTPException(status_code=404, detail="Tesis no encontrada")
    analisis = db.query(AnalysisResult).filter(AnalysisResult.thesis_id == thesis_id).first()
    alumno = db.query(User).filter(User.id == tesis.alumno_id).first()
    return {
        "tesis": {"id": tesis.id, "titulo": tesis.titulo, "estado": tesis.estado,
                  "alumno": alumno.nombre if alumno else "—"},
        "resultado": json.loads(analisis.resultado_json) if analisis else None,
        "latencia_ms": analisis.latencia_ms if analisis else None,
    }


@app.post("/maestro/tesis/{thesis_id}/validar", tags=["Maestro"])
async def validar_tesis(
    thesis_id: int,
    body: ValidarRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_rol("maestro")),
    db: Session = Depends(get_db),
):
    """
    El docente emite su decisión y observación.
    1. Guarda la decisión en la BD.
    2. Corre el flujo Human-Loop en background:
         TextInput ← texto del PDF (contexto para los agentes)
         ChatInput ← comentario del docente (intervención humana)
    3. El resultado del Human-Loop se adjunta al análisis existente.
    """
    if body.decision not in ("aprobado", "aprobado_con_cambios", "rechazado"):
        raise HTTPException(status_code=400, detail="decision debe ser: aprobado | aprobado_con_cambios | rechazado")

    tesis = db.query(Thesis).filter(Thesis.id == thesis_id).first()
    if not tesis:
        raise HTTPException(status_code=404, detail="Tesis no encontrada")

    tesis.estado = body.decision
    db.commit()

    # Correr Human-Loop en background para enriquecer el resultado
    background_tasks.add_task(
        _bg_human_loop,
        thesis_id=thesis_id,
        filepath=tesis.filepath,
        instruccion_docente=body.comentario or "Sin observaciones adicionales.",
        decision=body.decision,
    )

    return {"ok": True, "thesis_id": thesis_id, "estado": body.decision}


async def _bg_human_loop(thesis_id: int, filepath: str, instruccion_docente: str, decision: str):
    """
    Corre el flujo Human-Loop y adjunta su resultado al análisis existente.
    NO re-evalúa la tesis — recibe el análisis previo ya guardado + decisión docente.
    ChatInput ← payload con análisis previo + decisión + instrucción docente.
    """
    with Session(engine) as db:
        try:
            analisis = db.query(AnalysisResult).filter(AnalysisResult.thesis_id == thesis_id).first()
            resultado_previo = json.loads(analisis.resultado_json) if analisis else {}

            resultado_hl = await ejecutar_human_loop(resultado_previo, instruccion_docente, decision)

            if analisis:
                resultado_actual = json.loads(analisis.resultado_json)
                resultado_actual["human_loop"] = {
                    **resultado_hl,
                    "decision_docente": decision,
                    "comentario_docente": instruccion_docente,
                }
                analisis.resultado_json = json.dumps(resultado_actual, ensure_ascii=False)
                db.commit()
                print(f"✅ Human-Loop tesis {thesis_id} completado")
        except Exception as e:
            print(f"❌ Error Human-Loop tesis {thesis_id}: {e}")


# ── Helpers internos ──────────────────────────────────────────────

def _get_tesis_alumno(thesis_id: int, alumno_id: int, db) -> Thesis:
    tesis = db.query(Thesis).filter(Thesis.id == thesis_id, Thesis.alumno_id == alumno_id).first()
    if not tesis:
        raise HTTPException(status_code=404, detail="Tesis no encontrada")
    return tesis


def _limpiar_analisis_previo(thesis_id: int, db):
    previo = db.query(AnalysisResult).filter(AnalysisResult.thesis_id == thesis_id).first()
    if previo:
        db.delete(previo)
        db.commit()


def _metadata_pdf(filepath: str) -> dict:
    try:
        datos = extraer_texto_pdf(filepath)
        capitulos = extraer_capitulos(datos)

        return {
            "total_paginas": datos.get("total_paginas", 0),
            "total_palabras": datos.get("total_palabras", 0),
            "total_caracteres": datos.get("total_caracteres", 0),
            "capitulos_detectados": {
                key: bool(value.strip())
                for key, value in capitulos.items()
            },
            "chars_enviados_langflow": len(construir_input_langflow(datos)),
        }
    except Exception as e:
        print(f"⚠️ Error obteniendo metadata PDF: {e}")
        return {}


def _extraer_texto_tesis(filepath: str) -> str:
    try:
        datos = extraer_texto_pdf(filepath)
        return datos.get("texto_completo", "")
    except Exception:
        return ""


def _guardar_analisis(db, tesis: Thesis, resultado: dict, metadata_pdf: dict, latencia_ms: int):
    analisis = AnalysisResult(
        thesis_id=tesis.id,
        resultado_json=json.dumps(resultado, ensure_ascii=False),
        tokens_enviados=metadata_pdf.get("total_palabras", 0),
        tokens_recibidos=0,
        latencia_ms=latencia_ms,
    )
    db.add(analisis)


# ═══════════════════════════════════════════════════════════════════
# RAG — Endpoints (lo que pidió el profesor: almacenar en embeddings)
# ═══════════════════════════════════════════════════════════════════

from rag_service import (
    buscar_en_corpus, encontrar_tesis_similares, get_stats, indexar_tesis
)


class RagSearchRequest(BaseModel):
    consulta: str
    n_resultados: int = 5
    thesis_id: Optional[int] = None


@app.post("/thesis/{thesis_id}/indexar", tags=["RAG"])
async def indexar_tesis_rag(
    thesis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Indexa una tesis en ChromaDB para búsqueda semántica.
    Se llama automáticamente al terminar el análisis,
    pero también se puede llamar manualmente.
    """
    tesis = db.query(Thesis).filter(Thesis.id == thesis_id).first()
    if not tesis:
        raise HTTPException(status_code=404, detail="Tesis no encontrada")

    alumno = db.query(User).filter(User.id == tesis.alumno_id).first()
    texto = _extraer_texto_tesis(tesis.filepath)
    if not texto:
        raise HTTPException(status_code=400, detail="No se pudo extraer texto del PDF")

    analisis = db.query(AnalysisResult).filter(AnalysisResult.thesis_id == thesis_id).first()
    resultado = json.loads(analisis.resultado_json) if analisis else None

    stats = indexar_tesis(
        thesis_id=thesis_id,
        titulo=tesis.titulo,
        alumno=alumno.nombre if alumno else "—",
        texto_completo=texto,
        resultado_analisis=resultado,
    )
    return {"ok": True, **stats}


@app.post("/rag/buscar", tags=["RAG"])
async def rag_buscar(
    body: RagSearchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Búsqueda semántica en el corpus de tesis indexadas.
    Ejemplo: "metodología cuantitativa con muestra probabilística"
    """
    if not body.consulta.strip():
        raise HTTPException(status_code=400, detail="La consulta no puede estar vacía")

    resultados = buscar_en_corpus(
        consulta=body.consulta,
        n_resultados=body.n_resultados,
        filtro_thesis_id=body.thesis_id,
    )
    return {"consulta": body.consulta, "resultados": resultados, "total": len(resultados)}


@app.get("/rag/similares/{thesis_id}", tags=["RAG"])
async def rag_similares(
    thesis_id: int,
    n: int = 3,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna las n tesis más similares a la dada, basándose en embeddings.
    """
    similares = encontrar_tesis_similares(thesis_id, n=n)
    return {"thesis_id": thesis_id, "similares": similares}


@app.get("/rag/stats", tags=["RAG"])
async def rag_stats(current_user: User = Depends(get_current_user)):
    """Estadísticas del corpus RAG: total de chunks, tesis indexadas y modelo."""
    return get_stats()
