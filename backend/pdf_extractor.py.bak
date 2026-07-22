"""
SP-01: Extracción de texto de PDF con PyMuPDF
Mejora: extracción completa + resumen estructurado por secciones para tesis grandes.
"""

import fitz
import re
from typing import Optional


SECCIONES_UPAO = [
    "resumen", "abstract", "introduccion", "introducción",
    "planteamiento", "problema", "objetivos", "objetivo",
    "hipotesis", "hipótesis", "justificacion", "justificación",
    "marco teorico", "marco teórico", "antecedentes",
    "metodologia", "metodología", "diseño",
    "resultados", "discusion", "discusión",
    "conclusiones", "recomendaciones", "referencias", "bibliografía",
    "arquitectura", "propuesta", "implementación", "desarrollo"
]


def _normalizar(texto: str) -> str:
    texto = texto.replace("\n", " ")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def extraer_texto_pdf(filepath: str) -> dict:
    doc = fitz.open(filepath)
    texto_completo = []
    secciones_detectadas = []
    seccion_actual = None
    contenido_seccion = []

    for num_pagina, pagina in enumerate(doc, start=1):
        bloques = pagina.get_text("dict")["blocks"]

        for bloque in bloques:
            if bloque.get("type") != 0:
                continue

            for linea in bloque.get("lines", []):
                linea_texto = " ".join(
                    span["text"].strip()
                    for span in linea.get("spans", [])
                    if span["text"].strip()
                )

                if not linea_texto:
                    continue

                span_ref = linea.get("spans", [{}])[0]
                tamaño_fuente = span_ref.get("size", 0)
                es_negrita = "bold" in span_ref.get("font", "").lower()

                texto_lower = linea_texto.lower()
                es_titulo = (
                    tamaño_fuente >= 12
                    and (es_negrita or tamaño_fuente >= 14)
                    and any(sec in texto_lower for sec in SECCIONES_UPAO)
                )

                if es_titulo:
                    if seccion_actual:
                        secciones_detectadas.append({
                            "nombre": seccion_actual["nombre"],
                            "pagina": seccion_actual["pagina"],
                            "contenido": _normalizar(" ".join(contenido_seccion))[:4000]
                        })

                    seccion_actual = {
                        "nombre": linea_texto,
                        "pagina": num_pagina
                    }
                    contenido_seccion = []
                else:
                    contenido_seccion.append(linea_texto)

                texto_completo.append(linea_texto)

    if seccion_actual:
        secciones_detectadas.append({
            "nombre": seccion_actual["nombre"],
            "pagina": seccion_actual["pagina"],
            "contenido": _normalizar(" ".join(contenido_seccion))[:4000]
        })

    total_paginas = len(doc)
    doc.close()

    texto_unido = _normalizar(" ".join(texto_completo))

    return {
        "texto_completo": texto_unido,
        "secciones_detectadas": secciones_detectadas,
        "total_paginas": total_paginas,
        "total_palabras": len(texto_unido.split()),
        "total_caracteres": len(texto_unido)
    }


def _extraer_por_patrones(texto: str, patrones_inicio: list[str], max_chars: int = 8000) -> str:
    texto_lower = texto.lower()

    posiciones = []
    for patron in patrones_inicio:
        idx = texto_lower.find(patron.lower())
        if idx != -1:
            posiciones.append(idx)

    if not posiciones:
        return ""

    inicio = min(posiciones)

    posibles_cortes = [
        "capítulo", "capitulo", "marco teórico", "marco teorico",
        "metodología", "metodologia", "resultados", "discusión",
        "discusion", "conclusiones", "referencias", "bibliografía",
        "bibliografia", "anexos"
    ]

    fin = min(len(texto), inicio + max_chars)
    for corte in posibles_cortes:
        idx_corte = texto_lower.find(corte, inicio + 300)
        if idx_corte != -1 and idx_corte > inicio:
            fin = min(fin, idx_corte)

    return texto[inicio:fin].strip()


def extraer_capitulos(datos_pdf: dict) -> dict:
    texto = datos_pdf.get("texto_completo", "")
    secciones = datos_pdf.get("secciones_detectadas", [])

    capitulos = {
        "titulo": "",
        "resumen": "",
        "problema": "",
        "objetivos": "",
        "hipotesis": "",
        "metodologia": "",
        "arquitectura": "",
        "resultados": "",
        "conclusiones": ""
    }

    # Primero intenta usar secciones detectadas por formato.
    for sec in secciones:
        nombre = sec.get("nombre", "").lower()
        contenido = sec.get("contenido", "")

        if "resumen" in nombre or "abstract" in nombre:
            capitulos["resumen"] += " " + contenido

        elif "problema" in nombre or "planteamiento" in nombre:
            capitulos["problema"] += " " + contenido

        elif "objetivo" in nombre:
            capitulos["objetivos"] += " " + contenido

        elif "hipotesis" in nombre or "hipótesis" in nombre:
            capitulos["hipotesis"] += " " + contenido

        elif "metodologia" in nombre or "metodología" in nombre or "diseño" in nombre:
            capitulos["metodologia"] += " " + contenido

        elif "arquitectura" in nombre or "propuesta" in nombre or "implementación" in nombre or "desarrollo" in nombre:
            capitulos["arquitectura"] += " " + contenido

        elif "resultado" in nombre:
            capitulos["resultados"] += " " + contenido

        elif "conclusion" in nombre or "conclusión" in nombre:
            capitulos["conclusiones"] += " " + contenido

    # Si no detectó por formato, usa búsqueda por palabras clave.
    if not capitulos["resumen"]:
        capitulos["resumen"] = _extraer_por_patrones(texto, ["resumen", "abstract"], 5000)

    if not capitulos["problema"]:
        capitulos["problema"] = _extraer_por_patrones(texto, [
            "planteamiento del problema",
            "realidad problemática",
            "problema general",
            "formulación del problema"
        ], 8000)

    if not capitulos["objetivos"]:
        capitulos["objetivos"] = _extraer_por_patrones(texto, [
            "objetivo general",
            "objetivos específicos",
            "objetivos especificos"
        ], 5000)

    if not capitulos["hipotesis"]:
        capitulos["hipotesis"] = _extraer_por_patrones(texto, [
            "hipótesis",
            "hipotesis"
        ], 4000)

    if not capitulos["metodologia"]:
        capitulos["metodologia"] = _extraer_por_patrones(texto, [
            "metodología",
            "metodologia",
            "materiales y métodos",
            "materiales y metodos",
            "diseño metodológico",
            "diseño de investigación"
        ], 12000)

    if not capitulos["arquitectura"]:
        capitulos["arquitectura"] = _extraer_por_patrones(texto, [
            "arquitectura",
            "propuesta técnica",
            "propuesta tecnica",
            "implementación",
            "implementacion",
            "desarrollo de la solución",
            "desarrollo de la solucion"
        ], 12000)

    if not capitulos["resultados"]:
        capitulos["resultados"] = _extraer_por_patrones(texto, [
            "resultados",
            "análisis de resultados",
            "analisis de resultados"
        ], 10000)

    if not capitulos["conclusiones"]:
        capitulos["conclusiones"] = _extraer_por_patrones(texto, [
            "conclusiones"
        ], 6000)

    # Limpieza final y límite para no mandar textos gigantes a Langflow.
    for key in capitulos:
        capitulos[key] = _normalizar(capitulos[key])[:6000]

    return capitulos


def construir_input_langflow(datos_pdf: dict) -> str:
    capitulos = extraer_capitulos(datos_pdf)

    payload = {
        "metadata": {
            "total_paginas": datos_pdf.get("total_paginas", 0),
            "total_palabras": datos_pdf.get("total_palabras", 0),
            "total_caracteres": datos_pdf.get("total_caracteres", 0),
            "tipo_input": "tesis_segmentada_para_langflow"
        },
        "capitulos": capitulos
    }

    import json
    return json.dumps(payload, ensure_ascii=False, indent=2)


def validar_pdf(filepath: str) -> tuple[bool, Optional[str]]:
    try:
        doc = fitz.open(filepath)
        if doc.page_count == 0:
            return False, "El PDF no tiene páginas"
        doc.close()
        return True, None
    except Exception as e:
        return False, f"Archivo PDF inválido: {str(e)}"