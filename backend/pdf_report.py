"""
pdf_report.py — v3
FIX: parser de secciones más robusto — tolera texto antes de ===CLAVE===
FIX: la sección "Conciliación Final" solo muestra ===DICTAMEN===, no el texto crudo completo
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
import os, re, json
from datetime import datetime


def _limpiar(texto: str) -> str:
    texto = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', texto)
    texto = re.sub(r'#{1,6}\s*', '', texto)
    texto = re.sub(r'===\s*\w+\s*===', '', texto)
    return texto.strip()


def _parsear_secciones(texto_completo: str) -> dict:
    """
    Parser robusto: busca ===CLAVE=== aunque haya texto antes o después.
    También soporta respuestas nativas en formato JSON.
    """
    secciones = {"metodologico": "", "tecnico": "", "linguistico": "", "dictamen": ""}
    if not texto_completo:
        return secciones

    # Intentar JSON
    try:
        texto_limpio = texto_completo
        if "```json" in texto_limpio:
            texto_limpio = texto_limpio.split("```json")[1].split("```")[0]
        elif texto_limpio.strip().startswith("{"):
            primer = texto_limpio.find("{")
            ultimo = texto_limpio.rfind("}")
            if primer != -1 and ultimo != -1 and ultimo > primer:
                texto_limpio = texto_limpio[primer:ultimo+1]
                
        data = json.loads(texto_limpio.strip())
        
        if isinstance(data, dict) and ("resumen_ejecutivo" in data or "niveles_por_dimension" in data):
            dictamen = f"<b>RESUMEN EJECUTIVO:</b>\n{data.get('resumen_ejecutivo', '')}\n\n"
            
            fortalezas = data.get("fortalezas_principales", [])
            if fortalezas:
                dictamen += "<b>FORTALEZAS PRINCIPALES:</b>\n" + "\n".join([f"• {f}" for f in fortalezas]) + "\n\n"
                
            debilidades = data.get("debilidades_principales", [])
            if debilidades:
                dictamen += "<b>DEBILIDADES PRINCIPALES:</b>\n" + "\n".join([f"• {d}" for d in debilidades]) + "\n\n"
                
            niveles = data.get("niveles_por_dimension", {})
            if niveles:
                secciones['metodologico'] = f"Estado del análisis: {str(niveles.get('metodologico', 'No evaluado')).replace('_', ' ').upper()}"
                secciones['tecnico'] = f"Estado del análisis: {str(niveles.get('tecnico', 'No evaluado')).replace('_', ' ').upper()}"
                
                ling_text = f"Estado del análisis: {str(niveles.get('linguistico', 'No evaluado')).replace('_', ' ').upper()}"
                if debilidades:
                    ling_text += "\n\nObservaciones detectadas (Globales):\n" + "\n".join([f"• {d}" for d in debilidades])
                secciones['linguistico'] = ling_text
            
            estado_global = data.get("estado_diagnostico", "").replace('_', ' ').upper()
            if estado_global:
                secciones['dictamen'] = f"<b>VEREDICTO GLOBAL:</b> {estado_global}\n\n" + dictamen
            else:
                secciones['dictamen'] = dictamen
                
            # If there's text after the JSON (e.g. Auditoría), append it (but strip backend metrics)
            if "ultimo" in locals() and ultimo != -1 and ultimo < len(texto_completo) - 1:
                appended_text = texto_completo[ultimo+1:].strip()
                if appended_text:
                    appended_text = re.sub(r'===RESULTADO_OFICIAL_BACKEND===[\s\S]*$', '', appended_text).strip()
                    if appended_text:
                        secciones['dictamen'] += "\n\n" + appended_text

            return secciones
    except Exception:
        pass

    # Fallback: Normalizar buscar el patrón ===CLAVE=== con variaciones
    patron = re.compile(
        r'={2,3}\s*(?:METODOL[OÓ]GICO|METODOLOGICO)\s*={2,3}|'
        r'={2,3}\s*TECNICO\s*={2,3}|'
        r'={2,3}\s*LING[UÜ][IÍ]STICO\s*={2,3}|'
        r'={2,3}\s*DICTAMEN\s*={2,3}',
        re.IGNORECASE
    )

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
    current_error = ""
    
    for linea in texto_linguistico.split('\n'):
        linea = linea.strip()
        if not linea:
            continue
            
        es_nuevo = re.match(r'^[\d\.\-\*•]+\s+', linea)
        tiene_kw = any(kw in linea.lower() for kw in ['error', 'falta', 'sin doi', 'sin año', 'sin autor', 'apa', 'cita', 'referencia', 'incorrecta', 'incompleta', 'ausente'])
        es_meta = any(kw in linea.lower() for kw in ['dictamen', 'extracto experimental', 'agente', 'conciliador', 'metodológico', 'técnico', 'lingüístico', 'análisis consolidado', 'estado del análisis'])
        
        if es_meta:
            continue
            
        if es_nuevo:
            if current_error:
                errores.append(current_error)
            current_error = linea
        else:
            if current_error:
                current_error += " " + linea
            elif tiene_kw:
                current_error = linea

    if current_error:
        errores.append(current_error)
        
    errores_limpios = []
    for e in errores:
        limpia = re.sub(r'^[\d\.\-\*•]+\s*', '', _limpiar(e)).strip()
        if limpia and 'sin errores' not in limpia.lower() and len(limpia) > 10:
            errores_limpios.append(limpia)
            
    return errores_limpios[:12]


def _detectar_veredicto(texto: str) -> tuple:
    upper = texto.upper() if texto else ""
    if "DESAPROBADO" in upper or "RECHAZ" in upper:
        return "DESAPROBADO", colors.HexColor("#FEE2E2"), "❌"
    elif "ATENCION PRIORITARIA" in upper or "ATENCIÓN PRIORITARIA" in upper:
        return "ATENCIÓN PRIORITARIA", colors.HexColor("#FEE2E2"), "❌"
    elif "APROBADO CON OBSERVACIONES" in upper or ("APROBADO" in upper and "OBSERV" in upper):
        return "APROBADO CON OBSERVACIONES", colors.HexColor("#FEF9C3"), "⚠️"
    elif "REQUIERE REVISION" in upper or "REQUIERE REVISIÓN" in upper:
        return "REQUIERE REVISIÓN", colors.HexColor("#FEF9C3"), "⚠️"
    elif "APROBADO" in upper:
        return "APROBADO", colors.HexColor("#D1FAE5"), "✅"
    return "EN REVISIÓN", colors.HexColor("#F3F4F6"), "⏳"


def _card_agente(story, titulo, contenido, bg_hex, styles):
    story.append(Paragraph(titulo, styles["h3"]))
    if contenido and len(contenido.strip()) > 10:
        contenido_br = contenido.replace('\n', '<br/>')
        t = Table([[Paragraph(contenido_br, styles["body"])]], colWidths=[16.5*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor(bg_hex)),
            ("TOPPADDING",    (0,0),(-1,-1), 12),
            ("BOTTOMPADDING", (0,0),(-1,-1), 12),
            ("LEFTPADDING",   (0,0),(-1,-1), 16),
            ("RIGHTPADDING",  (0,0),(-1,-1), 16),
            ("ROUNDEDCORNERS",[8,8,8,8]),
            ("BOX",           (0,0),(-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("Sin análisis disponible para esta sección.", styles["body"]))
    story.append(Spacer(1, 0.4*cm))




def _tabla_rubrica_detalle(story, titulo: str, detalle: dict, styles):
    """Agrega al PDF la rúbrica completa con estado por ítem."""
    if not detalle or not detalle.get("items"):
        return
    rubrica_id = detalle.get("rubrica_id", "—")
    items = detalle.get("items", [])
    
    # Filtrar items válidos para no imprimir tablas gigantes de 'NO EVALUADO' en flujo Jerárquico
    items_validos = [it for it in items if str(it.get("estado")).lower() not in ["error_evaluacion", "no evaluado"]]
    if not items_validos:
        # En vez de imprimir 60 items vacíos, informamos que no hay evaluación ítem por ítem
        story.append(Paragraph(f"{titulo} — Rúbrica {rubrica_id} (Evaluación ítem por ítem no disponible en este flujo)", styles["body"]))
        story.append(Spacer(1, 0.35*cm))
        return

    story.append(Paragraph(f"{titulo} — Rúbrica {rubrica_id} ({len(items)} ítems)", styles["h3"]))

    filas = [["ID", "Estado", "Criterio", "Pts"]]
    for it in items:
        estado_raw = (it.get("estado") or "observado").replace("_", " ").upper()
        if estado_raw == "ERROR EVALUACION":
            estado_raw = "NO EVALUADO"
        
        criterio_texto = _limpiar(it.get("descripcion", ""))
        criterio_p = Paragraph(criterio_texto, styles["body"])
        
        pts = f"{float(it.get('puntos_obtenidos') or 0):.2f}/{float(it.get('puntos_max') or 0):.2f}"
        filas.append([it.get("id", "—"), estado_raw, criterio_p, pts])

    tabla = Table(filas, colWidths=[1.5*cm, 2.5*cm, 10.5*cm, 2.0*cm], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND",     (0,0),(-1,0),  colors.HexColor("#F1F5F9")),
        ("TEXTCOLOR",      (0,0),(-1,0),  colors.HexColor("#0F172A")),
        ("FONTNAME",       (0,0),(-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",       (0,0),(-1,-1), 8),
        ("ROWBACKGROUNDS", (0,1),(-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("GRID",           (0,0),(-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ("VALIGN",         (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",     (0,0),(-1,-1), 6),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 6),
    ]))
    story.append(tabla)
    story.append(Spacer(1, 0.35*cm))


def _draw_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor("#94A3B8"))
    canvas.drawString(2*cm, 1.5*cm, "Sistema de Deliberación Multiagente - UPAO")
    canvas.drawRightString(19*cm, 1.5*cm, f"Página {doc.page}")
    if doc.page > 1:
        canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
        canvas.setLineWidth(0.5)
        canvas.line(2*cm, 28*cm, 19*cm, 28*cm)
        canvas.drawString(2*cm, 28.2*cm, "Reporte de Análisis de Tesis")
    canvas.restoreState()


def generar_reporte_estructural(
    thesis_id, nombre_alumno, titulo_tesis,
    resultado_analisis, output_dir="./uploads/reportes"
) -> str:
    os.makedirs(output_dir, exist_ok=True)
    filename  = f"reporte_tesis_{thesis_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    filepath  = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm, topMargin=2.5*cm, bottomMargin=2.5*cm)

    gs = getSampleStyleSheet()
    ST = {
        "cover_university": ParagraphStyle("cover_univ", parent=gs["Title"],
            fontName="Helvetica-Bold", fontSize=18, textColor=colors.HexColor("#0F172A"), alignment=TA_CENTER),
        "cover_system": ParagraphStyle("cover_sys", parent=gs["Normal"],
            fontName="Helvetica", fontSize=12, textColor=colors.HexColor("#64748B"), alignment=TA_CENTER),
        "cover_title": ParagraphStyle("cover_title", parent=gs["Title"],
            fontName="Helvetica-Bold", fontSize=26, textColor=colors.HexColor("#2563EB"), alignment=TA_CENTER, spaceBefore=20, spaceAfter=20, leading=30),
        "titulo": ParagraphStyle("titulo", parent=gs["Title"],
            fontName="Helvetica-Bold", fontSize=16, spaceAfter=10, textColor=colors.HexColor("#0F172A"), alignment=TA_CENTER),
        "sub": ParagraphStyle("sub", parent=gs["Normal"],
            fontName="Helvetica", fontSize=11, spaceAfter=5, textColor=colors.HexColor("#64748B"), alignment=TA_CENTER),
        "h2": ParagraphStyle("h2", parent=gs["Heading2"],
            fontName="Helvetica-Bold", fontSize=14, spaceBefore=20, spaceAfter=10, textColor=colors.HexColor("#1E293B")),
        "h3": ParagraphStyle("h3", parent=gs["Heading3"],
            fontName="Helvetica-Bold", fontSize=11, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#334155")),
        "body": ParagraphStyle("body", parent=gs["Normal"],
            fontName="Helvetica", fontSize=10, spaceAfter=6, leading=16, alignment=TA_JUSTIFY, textColor=colors.HexColor("#334155")),
        "pie":  ParagraphStyle("pie",  parent=gs["Normal"],
            fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#94A3B8"), alignment=TA_CENTER),
    }

    story = []
    tipo      = resultado_analisis.get("tipo", "analisis_completo")
    fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")

    tipo_label = {
        "analisis_completo": "REPORTE DE ANÁLISIS<br/>COMPLETO",
        "veredicto":         "DICTAMEN TÉCNICO<br/>FINAL",
        "debate_red":        "REPORTE DE DEBATE<br/>ENTRE AGENTES",
    }.get(tipo, "REPORTE DE<br/>ANÁLISIS")

    # ── Portada ──────────────────────────────────────────────────
    story += [
        Spacer(1, 4*cm),
        Paragraph("UNIVERSIDAD PRIVADA ANTENOR ORREGO", ST["cover_university"]),
        Spacer(1, 0.3*cm),
        Paragraph("Sistema de Deliberación Multiagente", ST["cover_system"]),
        Spacer(1, 3*cm),
        Paragraph(tipo_label, ST["cover_title"]),
        Spacer(1, 3*cm),
    ]
    t_portada = Table([
        ["Estudiante:",          nombre_alumno],
        ["Título de Tesis:",     Paragraph(titulo_tesis, ST["body"])],
        ["Fecha de Emisión:",    fecha_hoy],
    ], colWidths=[4.5*cm, 10.5*cm])
    t_portada.setStyle(TableStyle([
        ("FONTNAME",      (0,0),(0,-1), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 11),
        ("TEXTCOLOR",     (0,0),(-1,-1), colors.HexColor("#1E293B")),
        ("ALIGN",         (0,0),(0,-1), "RIGHT"),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("LINEBELOW",     (0,0),(-1,-2), 0.5, colors.HexColor("#E2E8F0")),
    ]))
    story += [t_portada, PageBreak()]

    meta = resultado_analisis.get("metadata_pdf", {})
    if meta:
        story.append(Paragraph("Datos del documento original", ST["h2"]))
        t_meta = Table([
            ["Páginas:",  str(meta.get("total_paginas","—"))],
            ["Palabras:", str(meta.get("total_palabras","—"))],
            ["Latencia de IA:", f"{resultado_analisis.get('latencia_total_ms',0)/1000:.1f} segundos"],
        ], colWidths=[4.5*cm, 12*cm])
        t_meta.setStyle(TableStyle([
            ("FONTNAME",      (0,0),(0,-1), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1), 10),
            ("TEXTCOLOR",     (0,0),(-1,-1), colors.HexColor("#334155")),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#F8FAFC")),
            ("ROUNDEDCORNERS",[6,6,6,6]),
        ]))
        story += [t_meta, Spacer(1,0.5*cm)]

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
            filas = [["#", "Observación"]] + [[str(i), Paragraph(e, ST["body"])] for i, e in enumerate(errores, 1)]
            t_apa = Table(filas, colWidths=[0.8*cm, 15.7*cm])
            t_apa.setStyle(TableStyle([
                ("BACKGROUND",     (0,0),(-1,0),  colors.HexColor("#F1F5F9")),
                ("TEXTCOLOR",      (0,0),(-1,0),  colors.HexColor("#0F172A")),
                ("FONTNAME",       (0,0),(-1,0),  "Helvetica-Bold"),
                ("FONTSIZE",       (0,0),(-1,-1), 9),
                ("ROWBACKGROUNDS", (0,1),(-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("GRID",           (0,0),(-1,-1), 0.5, colors.HexColor("#E2E8F0")),
                ("VALIGN",         (0,0),(-1,-1), "TOP"),
                ("TOPPADDING",     (0,0),(-1,-1), 8),
                ("BOTTOMPADDING",  (0,0),(-1,-1), 8),
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

        t_verd = Table([[f"{veredicto_icon}  DICTAMEN FINAL: {veredicto_label}"]], colWidths=[16.5*cm])
        t_verd.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), veredicto_bg),
            ("TEXTCOLOR",     (0,0),(-1,-1), colors.HexColor("#0F172A")),
            ("FONTNAME",      (0,0),(-1,-1), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1), 14),
            ("ALIGN",         (0,0),(-1,-1), "CENTER"),
            ("TOPPADDING",    (0,0),(-1,-1), 16),
            ("BOTTOMPADDING", (0,0),(-1,-1), 16),
            ("ROUNDEDCORNERS",[8,8,8,8]),
            ("BOX",           (0,0),(-1,-1), 1, colors.HexColor("#CBD5E1")),
        ]))
        story += [t_verd, Spacer(1,0.5*cm)]

        # Rigor Score breakdown si está disponible en el texto
        rigor_match = re.search(
            r'RIGOR SCORE FINAL[:\s]+([0-9.]+)',
            dictamen or "", re.IGNORECASE
        )
        if rigor_match:
            score_val = float(rigor_match.group(1))
            score_pct = round(score_val * 100, 1)
            t_score = Table([[
                Paragraph(f"RIGOR SCORE FINAL: {score_val:.3f} ({score_pct}%)", ParagraphStyle("score", parent=ST["h3"], alignment=TA_CENTER, fontSize=12))
            ]], colWidths=[16.5*cm])
            t_score.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#F1F5F9")),
                ("TOPPADDING",    (0,0),(-1,-1), 12),
                ("BOTTOMPADDING", (0,0),(-1,-1), 12),
                ("ROUNDEDCORNERS",[8,8,8,8]),
                ("BOX",           (0,0),(-1,-1), 1, colors.HexColor("#CBD5E1")),
            ]))
            story += [t_score, Spacer(1, 0.4*cm)]

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
                ("BACKGROUND",     (0,0),(-1,0),  colors.HexColor("#F1F5F9")),
                ("TEXTCOLOR",      (0,0),(-1,0),  colors.HexColor("#0F172A")),
                ("FONTNAME",       (0,0),(-1,0),  "Helvetica-Bold"),
                ("FONTSIZE",       (0,0),(-1,-1), 9),
                ("ROWBACKGROUNDS", (0,1),(-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("GRID",           (0,0),(-1,-1), 0.5, colors.HexColor("#E2E8F0")),
                ("ALIGN",          (1,0),(-1,-1), "CENTER"),
                ("TOPPADDING",     (0,0),(-1,-1), 8),
                ("BOTTOMPADDING",  (0,0),(-1,-1), 8),
            ]))
            story += [t_puntajes, Spacer(1,0.5*cm)]

        if dictamen:
            dictamen_br = dictamen.replace('\n', '<br/>')
            story.append(Paragraph(dictamen_br, ST["body"]))
            story.append(Spacer(1, 0.4*cm))
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
        t_verd = Table([[f"{veredicto_icon}  DICTAMEN FINAL: {veredicto_label}"]], colWidths=[16.5*cm])
        t_verd.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), veredicto_bg),
            ("TEXTCOLOR",     (0,0),(-1,-1), colors.HexColor("#0F172A")),
            ("FONTNAME",      (0,0),(-1,-1), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1), 14),
            ("ALIGN",         (0,0),(-1,-1), "CENTER"),
            ("TOPPADDING",    (0,0),(-1,-1), 16),
            ("BOTTOMPADDING", (0,0),(-1,-1), 16),
            ("ROUNDEDCORNERS",[8,8,8,8]),
            ("BOX",           (0,0),(-1,-1), 1, colors.HexColor("#CBD5E1")),
        ]))
        story += [t_verd, Spacer(1,0.5*cm)]

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
            
            # Simple Markdown to ReportLab HTML converter
            texto_md = dictamen
            texto_md = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', texto_md) # Bold
            texto_md = re.sub(r'\*(.*?)\*', r'<i>\1</i>', texto_md) # Italic
            texto_md = re.sub(r'(?m)^### (.*?)$', r'<br/><b><font size="11">\1</font></b>', texto_md) # H3
            texto_md = re.sub(r'(?m)^## (.*?)$', r'<br/><b><font size="12">\1</font></b>', texto_md) # H2
            texto_md = re.sub(r'(?m)^# (.*?)$', r'<br/><b><font size="14">\1</font></b>', texto_md) # H1
            texto_md = re.sub(r'(?m)^---+$', r'<br/>', texto_md) # HR
            
            dictamen_br = texto_md.replace('\n', '<br/>')
            story.append(Paragraph(dictamen_br, ST["body"]))

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
    # Footer and header are managed by _draw_header_footer

    doc.build(story, onFirstPage=_draw_header_footer, onLaterPages=_draw_header_footer)
    return filepath
