"""
EN-00 + TA-01 (Sprint 1): Esquema de base de datos SQLite con SQLAlchemy
Tablas: users, thesis, analysis_results, reports, teacher_feedback
"""

from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime,
    ForeignKey, Boolean, create_engine
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database/tesis.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # necesario para SQLite
)

Base = declarative_base()


class User(Base):
    """
    Tabla: users
    Campos: id, email, password_hash, rol (alumno|maestro), nombre
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    rol = Column(String(20), nullable=False)          # "alumno" | "maestro"
    nombre = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Relaciones
    tesis = relationship("Thesis", back_populates="alumno")


class Thesis(Base):
    """
    Tabla: thesis
    Una tesis por subida. Un alumno puede tener historial de versiones.
    """
    __tablename__ = "thesis"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    alumno_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Estado del flujo: subido | en_analisis | pendiente_validacion | aprobado | rechazado | error
    estado = Column(String(50), default="subido")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    alumno = relationship("User", back_populates="tesis")
    analisis = relationship("AnalysisResult", back_populates="tesis", uselist=False)
    reporte = relationship("Report", back_populates="tesis", uselist=False)
    feedback_docente = relationship("TeacherFeedback", back_populates="tesis", uselist=False)


class AnalysisResult(Base):
    """
    Tabla: analysis_results
    Guarda la respuesta cruda del Agente Metodológico (EP-01 / Arq. Secuencial)
    """
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    thesis_id = Column(Integer, ForeignKey("thesis.id"), nullable=False, unique=True)
    # JSON con estructura: {"secciones": [...], "tokens_enviados": N, "tokens_recibidos": N}
    resultado_json = Column(Text, nullable=False)
    tokens_enviados = Column(Integer, default=0)
    tokens_recibidos = Column(Integer, default=0)
    latencia_ms = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tesis = relationship("Thesis", back_populates="analisis")


class Report(Base):
    """
    Tabla: reports
    Reporte final con Rigor Score y dictamen (EP-03)
    """
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    thesis_id = Column(Integer, ForeignKey("thesis.id"), nullable=False, unique=True)
    rigor_score = Column(Float, default=0.0)
    # "aprobado" | "observado" | "rechazado"
    decision = Column(String(20), nullable=True)
    resumen_debate = Column(Text, nullable=True)
    errores_apa_json = Column(Text, nullable=True)    # JSON lista de errores APA
    observaciones_json = Column(Text, nullable=True)  # JSON por sección
    pdf_path = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tesis = relationship("Thesis", back_populates="reporte")


class TeacherFeedback(Base):
    """
    Tabla: teacher_feedback
    Validación manual del maestro (EP-04 / Human-in-the-Loop)
    """
    __tablename__ = "teacher_feedback"

    id = Column(Integer, primary_key=True, index=True)
    thesis_id = Column(Integer, ForeignKey("thesis.id"), nullable=False, unique=True)
    maestro_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # "aprobado" | "rechazado"
    decision = Column(String(20), nullable=False)
    comentario = Column(Text, nullable=True)
    feedback_editado = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tesis = relationship("Thesis", back_populates="feedback_docente")


def init_db():
    """Crea todas las tablas y 2 usuarios de prueba (alumno + maestro)."""
    from passlib.context import CryptContext
    from sqlalchemy.orm import Session

    Base.metadata.create_all(bind=engine)

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    with Session(engine) as db:
        # Verificar que no existan ya
        if db.query(User).count() == 0:
            def _hash(p): return pwd_context.hash(p.encode("utf-8")[:72].decode("utf-8", errors="ignore"))
            usuarios_prueba = [
                User(
                    email="alumno@upao.edu.pe",
                    password_hash=_hash("alumno123"),
                    rol="alumno",
                    nombre="Raul Gastañuadi"
                ),
                User(
                    email="maestro@upao.edu.pe",
                    password_hash=_hash("maestro123"),
                    rol="maestro",
                    nombre="Walter Cueva"
                ),
            ]
            db.add_all(usuarios_prueba)
            db.commit()
            print("✅ DB inicializada con 2 usuarios de prueba")
        else:
            print("✅ DB ya inicializada")
