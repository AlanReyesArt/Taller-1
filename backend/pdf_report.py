"""
pdf_report.py — v3
FIX: parser de secciones más robusto — tolera texto antes de ===CLAVE===
FIX: la sección "Conciliación Final" solo muestra ===DICTAMEN===, no el texto crudo completo
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
import os, re
from datetime import datetime


def _limpiar(texto: str) -> str:
    texto = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', texto)
    texto = re.sub(r'#{1,6}\s*', '', texto)
    texto = re.sub(r'===\s*\w+\s*===', '', texto)
    return texto.strip()


def _parsear_secciones(texto_completo: str) -> dict:
    """
    Parser robusto: busca ===CLAVE=== aunque haya texto antes o después.
    Gemini a veces escribe 'METODOL===OGICO===' o texto previo antes del separador.
    """
    secciones = {"metodologico": "", "tecnico": "", "linguistico": "", "dictamen": ""}
    if not texto_completo:
        return secciones

    # Normalizar: buscar el patrón ===CLAVE=== con variaciones
    # Cubre: ===METODOLOGICO===, ===METODOLÓGICO===, METODOL===OGICO=== etc.
    patron = re.compile(
        r'={2,3}\s*(?:METODOL[OÓ]GICO|METODOLOGICO)\s*={2,3}|'
        r'={2,3}\s*TECNICO\s*={2,3}|'
        r'={2,3}\s*LING[UÜ][IÍ]STICO\s*={2,3}|'
        r'={2,3}\s*DICTAMEN\s*={2,3}',
        re.IGNORECASE
    )

    # Mapear a clave interna
    def _clave(match_text: str) -> str:
        t = match_text.upper()
        if 'METOD' in t:   return 'metodologico'
        if 'TECNI' in t:   return 'tecnico'
        if 'LING'  in t:   return 'linguistico'
        if 'DICTA' in t:   return 'dictamen'
        return ''

    matches = list(patron.finditer(texto_completo))
    if not matches:
        # Sin separadores — todo al dictamen como fallback
        secciones['dictamen'] = _limpiar(texto_completo)
        return secciones

    for i, m in enumerate(matches):
        clave = _clave(m.group())
        if not clave:
            continue
        inicio = m.end()
        fin = matches[i + 1].start() if i + 1 < len(matches) else len(texto_completo)
        contenido = texto_completo[inicio:fin].strip()
        secciones[clave] = _limpiar(contenido)

    return secciones


def _extraer_errores_apa(texto_linguistico: str) -> list:
    if not texto_linguistico:
        return []
    errores = []
    for linea in texto_linguistico.split('\n'):
        linea = linea.strip()
        if not linea or len(linea) < 15:
            continue
        es_error = re.match(r'^[\d\-\*•]', linea) or any(
            kw in linea.lower() for kw in ['error', 'falta', 'sin doi', 'sin año',
                                            'sin autor', 'apa', 'cita', 'referencia',
                                            'incorrecta', 'incompleta', 'ausente'])
        es_meta = any(kw in linea.lower() for kw in [
            'dictamen', 'extracto experimental', 'agente', 'conciliador',
            'metodológico', 'técnico', 'lingüístico', 'análisis consolidado'])
        if es_error and not es_meta:
            limpia = re.sub(r'^[\d\.\-\*•]+\s*', '', _limpiar(linea)).strip()
            if limpia and 'sin errores' not in limpia.lower() and len(limpia) > 10:
                errores.append(limpia[:150])
    return errores[:12]


def _detectar_veredicto(texto: str) -> tuple:
    upper = texto.upper() if texto else ""
    if "DESAPROBADO" in upper or "RECHAZ" in upper:
        return "DESAPROBADO", colors.HexColor("#FEE2E2"), "❌"
    elif "APROBADO CON OBSERVACIONES" in upper or ("APROBADO" in upper and "OBSERV" in upper):
        return "APROBADO CON OBSERVACIONES", colors.HexColor("#FEF9C3"), "⚠️"
    elif "APROBADO" in upper:
        return "APROBADO", colors.HexColor("#D1FAE5"), "✅"
    return "EN REVISIÓN", colors.HexColor("#F3F4F6"), "⏳"


def _card_agente(story, titulo, contenido, bg_hex, styles):
    story.append(Paragraph(titulo, styles["h3"]))
    if contenido and len(contenido.strip()) > 10:
        parrafos = [contenido[i:i+700] for i in range(0, min(len(contenido), 2100), 700)]
        t = Table([[Paragraph(p, styles["body"])] for p in parrafos], colWidths=[16.5*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor(bg_hex)),
            ("TOPPADDING",    (0,0),(-1,-1), 10),
            ("BOTTOMPADDING", (0,0),(-1,-1), 10),
            ("LEFTPADDING",   (0,0),(-1,-1), 12),
            ("RIGHTPADDING",  (0,0),(-1,-1), 12),
            ("ROUNDEDCORNERS",[6,6,6,6]),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("Sin análisis disponible para esta sección.", styles["body"]))
    story.append(Spacer(1, 0.3*cm))




def _tabla_rubrica_detalle(story, titulo: str, detalle: dict, styles):
    """Agrega al PDF la rúbrica completa con estado por ítem."""
    if not detalle or not detalle.get("items"):
        return
    rubrica_id = detalle.get("rubrica_id", "—")
    items = detalle.get("items", [])
    story.append(Paragraph(f"{titulo} — Rúbrica {rubrica_id} ({len(items)} ítems)", styles["h3"]))

    filas = [["ID", "Estado", "Criterio", "Pts"]]
    for it in items:
        estado = (it.get("estado") or "observado").replace("_", " ").upper()
        criterio = _limpiar(it.get("descripcion", ""))[:180]
        pts = f"{float(it.get('puntos_obtenidos') or 0):.2f}/{float(it.get('puntos_max') or 0):.2f}"
        filas.append([it.get("id", "—"), estado, criterio, pts])

    tabla = Table(filas, colWidths=[1.5*cm, 2.5*cm, 10.5*cm, 2.0*cm], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND",     (0,0),(-1,0),  colors.HexColor("#1F3864")),
        ("TEXTCOLOR",      (0,0),(-1,0),  colors.white),
        ("FONTNAME",       (0,0),(-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",       (0,0),(-1,-1), 7),
        ("ROWBACKGROUNDS", (0,1),(-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("GRID",           (0,0),(-1,-1), 0.35, colors.HexColor("#E5E7EB")),
        ("VALIGN",         (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",     (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 4),
    ]))
    story.append(tabla)
    story.append(Spacer(1, 0.35*cm))


def generar_reporte_estructural(
    thesis_id, nombre_alumno, titulo_tesis,
    resultado_analisis, output_dir="./uploads/reportes"
) -> str:
    os.makedirs(output_dir, exist_ok=True)
    filename  = f"reporte_tesis_{thesis_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    filepath  = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    gs = getSampleStyleSheet()
    ST = {
        "titulo": ParagraphStyle("titulo", parent=gs["Title"],
            fontSize=15, spaceAfter=4, textColor=colors.HexColor("#1F3864"), alignment=TA_CENTER),
        "sub": ParagraphStyle("sub", parent=gs["Normal"],
            fontSize=10, spaceAfter=3, textColor=colors.HexColor("#555555"), alignment=TA_CENTER),
        "h2": ParagraphStyle("h2", parent=gs["Heading2"],
            fontSize=12, spaceBefore=16, spaceAfter=8, textColor=colors.HexColor("#1F3864")),
        "h3": ParagraphStyle("h3", parent=gs["Heading3"],
            fontSize=10, spaceBefore=10, spaceAfter=5, textColor=colors.HexColor("#2E5797")),
        "body": ParagraphStyle("body", parent=gs["Normal"],
            fontSize=9, spaceAfter=4, leading=14, alignment=TA_JUSTIFY),
        "pie":  ParagraphStyle("pie",  parent=gs["Normal"],
            fontSize=7, textColor=colors.grey, alignment=TA_CENTER),
    }

    story = []
    tipo      = resultado_analisis.get("tipo", "analisis_completo")
    fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")

    tipo_label = {
        "analisis_completo": "REPORTE DE ANÁLISIS COMPLETO",
        "veredicto":         "DICTAMEN TÉCNICO FINAL",
        "debate_red":        "REPORTE DE DEBATE ENTRE AGENTES",
    }.get(tipo, "REPORTE DE ANÁLISIS")

    # ── Portada ──────────────────────────────────────────────────
    story += [
        Paragraph("UNIVERSIDAD PRIVADA ANTENOR ORREGO", ST["titulo"]),
        Paragraph("Sistema de Deliberación Multiagente — Análisis de Tesis", ST["sub"]),
        Spacer(1, 0.4*cm),
        Paragraph(tipo_label, ST["titulo"]),
        Spacer(1, 0.3*cm),
    ]
    t_portada = Table([
        ["Alumno:",          nombre_alumno],
        ["Tesis:",           titulo_tesis[:80]],
        ["Fecha:",           fecha_hoy],
        ["Tipo de análisis:", tipo_label],
    ], colWidths=[3.5*cm, 13*cm])
    t_portada.setStyle(TableStyle([
        ("FONTNAME",      (0,0),(0,-1), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 9),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("TEXTCOLOR",     (0,0),(0,-1), colors.HexColor("#1F3864")),
    ]))
    story += [t_portada, Spacer(1,0.4*cm),
              HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1F3864")),
              Spacer(1,0.3*cm)]

    meta = resultado_analisis.get("metadata_pdf", {})
    if meta:
        story.append(Paragraph("Datos del documento", ST["h2"]))
        t_meta = Table([
            ["Páginas:",  str(meta.get("total_paginas","—"))],
            ["Palabras:", str(meta.get("total_palabras","—"))],
            ["Latencia:", f"{resultado_analisis.get('latencia_total_ms',0)/1000:.1f}s"],
        ], colWidths=[4*cm, 12.5*cm])
        t_meta.setStyle(TableStyle([
            ("FONTNAME",      (0,0),(0,-1), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1), 9),
            ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ]))
        story += [t_meta, Spacer(1,0.3*cm)]

    # ══════════════════════════════════════════════════════════════
    # ANÁLISIS COMPLETO
    # ══════════════════════════════════════════════════════════════
    if tipo == "analisis_completo":
        texto_completo = resultado_analisis.get("secuencial",{}).get("texto_crudo","")
        secciones = _parsear_secciones(texto_completo)

        story.append(Paragraph("1. Análisis por Agente Especialista", ST["h2"]))
        _card_agente(story, "📐 Agente Metodológico", secciones["metodologico"], "#EDE9FE", ST)
        _card_agente(story, "⚙️ Agente Técnico",      secciones["tecnico"],       "#E0F2FE", ST)
        _card_agente(story, "📝 Agente Lingüístico",  secciones["linguistico"],   "#DCFCE7", ST)

        # Errores APA — solo de la sección lingüística
        story.append(Paragraph("2. Errores de Citación APA 7 Detectados", ST["h2"]))
        errores = _extraer_errores_apa(secciones["linguistico"])
        if errores:
            story.append(Paragraph(f"Se detectaron {len(errores)} observaciones:", ST["body"]))
            story.append(Spacer(1, 0.2*cm))
            filas = [["#", "Observación"]] + [[str(i), e] for i, e in enumerate(errores, 1)]
            t_apa = Table(filas, colWidths=[0.8*cm, 15.7*cm])
            t_apa.setStyle(TableStyle([
                ("BACKGROUND",     (0,0),(-1,0),  colors.HexColor("#1F3864")),
                ("TEXTCOLOR",      (0,0),(-1,0),  colors.white),
                ("FONTNAME",       (0,0),(-1,0),  "Helvetica-Bold"),
                ("FONTSIZE",       (0,0),(-1,-1), 8),
                ("ROWBACKGROUNDS", (0,1),(-1,-1), [colors.white, colors.HexColor("#FEF9C3")]),
                ("GRID",           (0,0),(-1,-1), 0.5, colors.HexColor("#E5E7EB")),
                ("VALIGN",         (0,0),(-1,-1), "TOP"),
                ("TOPPADDING",     (0,0),(-1,-1), 5),
                ("BOTTOMPADDING",  (0,0),(-1,-1), 5),
            ]))
            story.append(t_apa)
        else:
            story.append(Paragraph(
                "No se detectaron errores APA específicos en el documento." if secciones["linguistico"]
                else "El Agente Lingüístico no retornó análisis en esta ejecución.",
                ST["body"]))

        # Dictamen final — SOLO la sección ===DICTAMEN===
        story += [Spacer(1,0.3*cm), Paragraph("3. Dictamen Final del Conciliador", ST["h2"])]
        dictamen = secciones["dictamen"]
        veredicto_label, veredicto_bg, veredicto_icon = _detectar_veredicto(dictamen)

        t_verd = Table([[f"{veredicto_icon}  VEREDICTO: {veredicto_label}"]], colWidths=[16.5*cm])
        t_verd.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), veredicto_bg),
            ("FONTNAME",      (0,0),(-1,-1), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1), 12),
            ("ALIGN",         (0,0),(-1,-1), "CENTER"),
            ("TOPPADDING",    (0,0),(-1,-1), 12),
            ("BOTTOMPADDING", (0,0),(-1,-1), 12),
        ]))
        story += [t_verd, Spacer(1,0.3*cm)]

        # Rigor Score breakdown si está disponible en el texto
        rigor_match = re.search(
            r'RIGOR SCORE FINAL[:\s]+([0-9.]+)',
            dictamen or "", re.IGNORECASE
        )
        if rigor_match:
            score_val = float(rigor_match.group(1))
            score_pct = round(score_val * 100, 1)
            # Barra visual del Rigor Score
            bar_filled = int(score_pct / 100 * 155)
            bar_empty  = 155 - bar_filled
            bar_color  = colors.HexColor("#10B981") if score_val >= 0.80 else (
                         colors.HexColor("#F59E0B") if score_val >= 0.60 else
                         colors.HexColor("#EF4444"))
            t_score = Table([[
                Paragraph(f"RIGOR SCORE: {score_val:.3f} ({score_pct}%)", ST["h3"])
            ]], colWidths=[16.5*cm])
            t_score.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#F8FAFC")),
                ("TOPPADDING",    (0,0),(-1,-1), 8),
                ("BOTTOMPADDING", (0,0),(-1,-1), 8),
                ("LEFTPADDING",   (0,0),(-1,-1), 12),
            ]))
            story += [t_score, Spacer(1, 0.2*cm)]

        # Tabla de puntajes por agente si están en el dictamen
        met_match = re.search(r'Metodol[oó]gico[:\s]+([0-9.]+)\s*/\s*([0-9.]+)\s*=\s*([0-9.]+)%', dictamen or "", re.IGNORECASE)
        tec_match = re.search(r'T[eé]cnico[:\s]+([0-9.]+)\s*/\s*([0-9.]+)\s*=\s*([0-9.]+)%', dictamen or "", re.IGNORECASE)
        lin_match = re.search(r'Ling[üu][ií]stico[:\s]+([0-9.]+)\s*/\s*([0-9.]+)\s*=\s*([0-9.]+)%', dictamen or "", re.IGNORECASE)

        if met_match and tec_match and lin_match:
            filas_score = [
                ["Agente", "Pts Obtenidos", "Pts Máximo", "Cumplimiento", "Peso", "Aporte"],
                ["Metodológico", met_match.group(1), met_match.group(2), f"{met_match.group(3)}%", "40%", f"{float(met_match.group(3))*0.4:.1f}%"],
                ["Técnico",      tec_match.group(1), tec_match.group(2), f"{tec_match.group(3)}%", "40%", f"{float(tec_match.group(3))*0.4:.1f}%"],
                ["Lingüístico",  lin_match.group(1), lin_match.group(2), f"{lin_match.group(3)}%", "20%", f"{float(lin_match.group(3))*0.2:.1f}%"],
            ]
            t_puntajes = Table(filas_score, colWidths=[3*cm, 2.5*cm, 2.5*cm, 3*cm, 2*cm, 3.5*cm])
            t_puntajes.setStyle(TableStyle([
                ("BACKGROUND",     (0,0),(-1,0),  colors.HexColor("#1F3864")),
                ("TEXTCOLOR",      (0,0),(-1,0),  colors.white),
                ("FONTNAME",       (0,0),(-1,0),  "Helvetica-Bold"),
                ("FONTSIZE",       (0,0),(-1,-1), 8),
                ("ROWBACKGROUNDS", (0,1),(-1,-1), [colors.white, colors.HexColor("#F0F4FA")]),
                ("GRID",           (0,0),(-1,-1), 0.5, colors.HexColor("#E5E7EB")),
                ("ALIGN",          (1,0),(-1,-1), "CENTER"),
                ("TOPPADDING",     (0,0),(-1,-1), 5),
                ("BOTTOMPADDING",  (0,0),(-1,-1), 5),
            ]))
            story += [t_puntajes, Spacer(1,0.3*cm)]

        if dictamen:
            for i in range(0, min(len(dictamen), 3500), 700):
                story.append(Paragraph(dictamen[i:i+700], ST["body"]))
        else:
            story.append(Paragraph(
                "El Conciliador no emitió dictamen estructurado. "
                "Verifica que el prompt del Conciliador incluya los separadores ===DICTAMEN===.",
                ST["body"]))

    # ══════════════════════════════════════════════════════════════
    # VEREDICTO (Jerárquico)
    # ══════════════════════════════════════════════════════════════
    elif tipo == "veredicto":
        texto_completo = resultado_analisis.get("jerarquico",{}).get("texto_crudo","")
        secciones = _parsear_secciones(texto_completo)
        dictamen  = secciones["dictamen"] or texto_completo

        story.append(Paragraph("Dictamen del Comité Evaluador", ST["h2"]))
        veredicto_label, veredicto_bg, veredicto_icon = _detectar_veredicto(dictamen)
        t_verd = Table([[f"{veredicto_icon}  VEREDICTO: {veredicto_label}"]], colWidths=[16.5*cm])
        t_verd.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), veredicto_bg),
            ("FONTNAME",      (0,0),(-1,-1), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1), 13),
            ("ALIGN",         (0,0),(-1,-1), "CENTER"),
            ("TOPPADDING",    (0,0),(-1,-1), 14),
            ("BOTTOMPADDING", (0,0),(-1,-1), 14),
        ]))
        story += [t_verd, Spacer(1,0.4*cm)]

        rubricas_detalle = resultado_analisis.get("rubricas_detalle", {}) or {}
        if rubricas_detalle:
            story.append(Paragraph("Rúbrica completa evaluada ítem por ítem", ST["h2"]))
            _tabla_rubrica_detalle(story, "📐 Metodológica", rubricas_detalle.get("metodologica"), ST)
            _tabla_rubrica_detalle(story, "⚙️ Técnica", rubricas_detalle.get("tecnica"), ST)
            _tabla_rubrica_detalle(story, "📝 Lingüística", rubricas_detalle.get("linguistica"), ST)

        if any([secciones["metodologico"], secciones["tecnico"], secciones["linguistico"]]):
            _card_agente(story, "📐 Metodológico", secciones["metodologico"], "#EDE9FE", ST)
            _card_agente(story, "⚙️ Técnico",      secciones["tecnico"],       "#E0F2FE", ST)
            _card_agente(story, "📝 Lingüístico",  secciones["linguistico"],   "#DCFCE7", ST)
        if dictamen:
            story.append(Paragraph("Justificación del Comité:", ST["h3"]))
            for i in range(0, min(len(dictamen), 3500), 700):
                story.append(Paragraph(dictamen[i:i+700], ST["body"]))

    # ══════════════════════════════════════════════════════════════
    # DEBATE RED
    # ══════════════════════════════════════════════════════════════
    elif tipo == "debate_red":
        texto_completo = resultado_analisis.get("red",{}).get("texto_crudo","")
        story.append(Paragraph("Debate entre Agentes — Arquitectura de Red", ST["h2"]))
        story.append(Paragraph(
            "Los agentes debatieron sobre la tesis en rondas circulares. "
            "El Agente de Consenso emitió el veredicto final.", ST["body"]))
        story.append(Spacer(1,0.3*cm))
        if texto_completo:
            limpio = _limpiar(texto_completo)
            for i in range(0, min(len(limpio), 4000), 700):
                story.append(Paragraph(limpio[i:i+700], ST["body"]))
        else:
            story.append(Paragraph("Resultado del debate no disponible.", ST["body"]))

    # ── Pie ───────────────────────────────────────────────────────
    story += [
        Spacer(1,1*cm),
        HRFlowable(width="100%", thickness=0.5, color=colors.grey),
        Spacer(1,0.2*cm),
        Paragraph(
            f"Generado automáticamente por el Sistema de Deliberación Multiagente "
            f"— UPAO {datetime.now().year}", ST["pie"])
    ]

    doc.build(story)
    return filepath
