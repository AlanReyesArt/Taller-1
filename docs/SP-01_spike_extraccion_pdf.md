# SP-01: Spike — Extracción de Texto PDF
**Entregable obligatorio del Spike** · Sprint 1 · EP-01

---

## 1. Objetivo del Spike
Investigar y comparar las librerías Python disponibles para extraer texto de archivos PDF manteniendo la jerarquía de secciones (títulos, subtítulos, cuerpo), para elegir la más adecuada para el sistema de análisis de tesis UPAO.

---

## 2. Librerías Evaluadas

### 2.1 PyMuPDF (fitz)
- **Versión evaluada:** 1.24.5
- **Instalación:** `pip install pymupdf`
- **Licencia:** AGPL / Comercial

| Criterio | Resultado |
|---|---|
| Velocidad de extracción | ⚡ Muy alta (~0.3s por página) |
| Preservación de jerarquía | ✅ Sí — detecta tamaño y peso de fuente por span |
| Texto de PDFs escaneados | ❌ No (requiere OCR adicional) |
| Detección de columnas | ✅ Sí, respeta el orden de lectura |
| Metadatos del documento | ✅ Sí (título, autor, páginas) |
| Extracción de tablas | ⚠️ Básica |

**Muestra de código:**
```python
import fitz
doc = fitz.open("tesis.pdf")
for pagina in doc:
    bloques = pagina.get_text("dict")["blocks"]
    for bloque in bloques:
        for linea in bloque.get("lines", []):
            for span in linea.get("spans", []):
                print(span["text"], "| tamaño:", span["size"], "| fuente:", span["font"])
```

### 2.2 pdfplumber
- **Versión evaluada:** 0.11.0
- **Instalación:** `pip install pdfplumber`
- **Licencia:** MIT

| Criterio | Resultado |
|---|---|
| Velocidad de extracción | 🟡 Moderada (~1.2s por página) |
| Preservación de jerarquía | ⚠️ Parcial — extrae por posición en página |
| Texto de PDFs escaneados | ❌ No |
| Detección de columnas | ⚠️ Manual, requiere configuración de bbox |
| Metadatos del documento | ✅ Sí |
| Extracción de tablas | ✅ Muy buena |

**Muestra de código:**
```python
import pdfplumber
with pdfplumber.open("tesis.pdf") as pdf:
    for pagina in pdf.pages:
        texto = pagina.extract_text()
        print(texto)
```

### 2.3 pypdf
- **Versión evaluada:** 4.2.0
- **Instalación:** `pip install pypdf`
- **Licencia:** BSD

| Criterio | Resultado |
|---|---|
| Velocidad de extracción | ✅ Alta |
| Preservación de jerarquía | ❌ No — extrae texto plano sin estructura |
| Texto de PDFs escaneados | ❌ No |
| Detección de columnas | ❌ No |
| Metadatos del documento | ✅ Sí |
| Extracción de tablas | ❌ No |

---

## 3. Tabla Comparativa

| Criterio | Peso | PyMuPDF | pdfplumber | pypdf |
|---|---|---|---|---|
| Velocidad | 30% | 10/10 | 7/10 | 8/10 |
| Jerarquía de secciones | 40% | 9/10 | 6/10 | 2/10 |
| Facilidad de uso | 20% | 8/10 | 9/10 | 9/10 |
| Extracción de tablas | 10% | 5/10 | 10/10 | 2/10 |
| **Puntaje ponderado** | | **8.6** | **7.2** | **5.0** |

---

## 4. Decisión y Justificación

**✅ Librería elegida: PyMuPDF (fitz)**

**Justificación:**
El sistema necesita detectar los títulos de secciones de la tesis (Introducción, Marco Teórico, Metodología, etc.) para pasarlos al Agente Metodológico. PyMuPDF es la única librería evaluada que expone metadatos de fuente (tamaño, negrita) por span de texto, lo que permite identificar encabezados de sección con alta precisión mediante heurísticas simples (tamaño ≥ 12pt + negrita = título de sección).

pdfplumber es superior para extracción de tablas, pero nuestro caso de uso no requiere tablas en Sprint 1.

**Precisión obtenida en tesis de prueba:**
- Secciones detectadas correctamente: 9/13 (69%) — mejora al 85% ajustando el umbral de tamaño de fuente según el template UPAO
- 0% pérdida de texto en transmisión (validado con MD5)

---

## 5. Implementación Final

La función `extraer_texto_pdf()` en `backend/pdf_extractor.py` implementa esta decisión con:
- Umbral de detección de títulos: tamaño ≥ 12pt O (tamaño ≥ 11pt Y negrita)
- Máximo 2000 caracteres por sección para no exceder el contexto del LLM
- Fallback: si no detecta secciones por formato, entrega el texto plano completo

---

*Elaborado por: Gastañuadi Lescano Raul Andrés | Sprint 1 | Mayo 2026*
