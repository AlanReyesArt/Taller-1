import { useState, useEffect, useRef } from 'react'
import { uploadThesis, analizarCompleto, obtenerVeredicto, debateRed, getAnalysisResult, getMyThesis, downloadReport } from '../api'
import { useAuth } from '../AuthContext'
import { useNavigate } from 'react-router-dom'

const C = { primary: '#1F3864', success: '#065F46', warning: '#92400E', danger: '#7F1D1D', accent: '#2E5797' }

const badge = (estado) => {
  const map = {
    subido:               { bg: '#DBEAFE', color: '#1E40AF', label: '📄 Subido' },
    en_analisis:          { bg: '#FEF3C7', color: '#92400E', label: '⏳ Analizando...' },
    pendiente_validacion: { bg: '#D1FAE5', color: '#065F46', label: '✅ Listo para docente' },
    aprobado:             { bg: '#D1FAE5', color: '#065F46', label: '✅ Aprobado' },
    aprobado_con_cambios: { bg: '#FEF9C3', color: '#854D0E', label: '✏️ Aprobado con cambios' },
    rechazado:            { bg: '#FEE2E2', color: '#7F1D1D', label: '❌ Rechazado' },
    error:                { bg: '#FEE2E2', color: '#7F1D1D', label: '⚠️ Error' },
  }
  const s = map[estado] || { bg: '#F3F4F6', color: '#374151', label: estado }
  return <span style={{ background: s.bg, color: s.color, padding: '3px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600 }}>{s.label}</span>
}

// Tarjeta del agente con preview + expandible
function AgenteCard({ titulo, icono, respuesta, error, latencia_ms }) {
  const [expandido, setExpandido] = useState(false)
  const ok = !!respuesta && !error
  const preview = respuesta ? respuesta.slice(0, 160) + (respuesta.length > 160 ? '...' : '') : ''

  return (
    <div style={{ border: `2px solid ${ok ? '#10B981' : error ? '#EF4444' : '#E5E7EB'}`, borderRadius: 12, overflow: 'hidden', marginBottom: 12 }}>
      <div style={{ background: ok ? '#D1FAE5' : error ? '#FEE2E2' : '#F3F4F6', padding: '14px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 22 }}>{icono}</span>
          <div>
            <div style={{ fontWeight: 700, color: C.primary, fontSize: 14 }}>{titulo}</div>
            {latencia_ms > 0 && <div style={{ fontSize: 11, color: '#6B7280' }}>⚡ {latencia_ms.toLocaleString()} ms</div>}
          </div>
        </div>
        <span style={{ fontSize: 18 }}>{ok ? '✅' : error ? '❌' : '⏳'}</span>
      </div>

      {error && <div style={{ background: '#FEF2F2', padding: '10px 20px', fontSize: 12, color: '#B91C1C' }}>⚠️ {error}</div>}

      {respuesta && (
        <div style={{ padding: '12px 20px', background: '#F8FAFC' }}>
          <p style={{ fontSize: 13, color: '#374151', margin: 0, lineHeight: 1.6 }}>
            {expandido ? respuesta : preview}
          </p>
          {respuesta.length > 160 && (
            <button onClick={() => setExpandido(e => !e)}
              style={{ background: 'none', border: 'none', color: C.accent, cursor: 'pointer', fontSize: 12, marginTop: 6, padding: 0, fontWeight: 600 }}>
              {expandido ? '▲ ver menos' : '▼ ver más'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// ── Tabla de ítems de rúbrica por agente ─────────────────────────────
function TablaItems({ items = [], titulo, color, bg }) {
  const [expandida, setExpandida] = useState(true)
  
  const validos = items.filter(i => {
    const st = String(i.estado || '').toLowerCase();
    return st && st !== 'error_evaluacion' && st !== 'no evaluado';
  });
  
  if (!items || items.length === 0) {
    return (
      <div style={{ padding: '12px 16px', fontSize: 13, color: '#6B7280', fontStyle: 'italic', background: '#F8FAFC', borderRadius: 8, border: '1px solid #E5E7EB', marginTop: 8 }}>
        Evaluación ítem por ítem no disponible en este flujo.
      </div>
    );
  }

  const aprobados  = items.filter(i => i.estado === 'cumple')
  const parciales  = items.filter(i => i.estado === 'parcial' || i.estado === 'observado')
  const reprobados = items.filter(i => i.estado === 'no_cumple' || i.estado === 'falta')
  const ptsObt     = items.reduce((s, i) => s + (parseFloat(i.puntos_obtenidos) || 0), 0)
  const ptsMax     = items.reduce((s, i) => s + (parseFloat(i.puntos_max) || 0), 0)
  const pct        = ptsMax > 0 ? Math.round((ptsObt / ptsMax) * 100) : 0

  const visibles = expandida ? items : items.slice(0, 6)

  return (
    <div style={{ marginTop: 10, border: `1px solid ${color}33`, borderRadius: 10, overflow: 'hidden' }}>
      {/* Header con resumen */}
      <div style={{ background: bg, padding: '10px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
        <span style={{ fontWeight: 700, color, fontSize: 13 }}>📋 {titulo} — Ítems evaluados</span>
        <div style={{ display: 'flex', gap: 8, fontSize: 12, flexWrap: 'wrap' }}>
          <span style={{ background: '#D1FAE5', color: '#065F46', padding: '2px 8px', borderRadius: 12, fontWeight: 600 }}>✅ {aprobados.length} cumple</span>
          <span style={{ background: '#FEF3C7', color: '#92400E', padding: '2px 8px', borderRadius: 12, fontWeight: 600 }}>⚠️ {parciales.length} observado</span>
          <span style={{ background: '#FEE2E2', color: '#7F1D1D', padding: '2px 8px', borderRadius: 12, fontWeight: 600 }}>❌ {reprobados.length} falta</span>
          <span style={{ background: '#EDE9FE', color: '#5B21B6', padding: '2px 8px', borderRadius: 12, fontWeight: 700 }}>{ptsObt.toFixed(2)} / {ptsMax.toFixed(2)} pts ({pct}%)</span>
        </div>
      </div>
      {/* Barra de progreso */}
      <div style={{ height: 4, background: '#E5E7EB' }}>
        <div style={{ height: 4, background: pct >= 60 ? '#10B981' : pct >= 30 ? '#F59E0B' : '#EF4444', width: `${Math.min(pct, 100)}%`, transition: 'width 0.5s' }} />
      </div>
      {/* Tabla de ítems */}
      <div style={{ padding: '8px 0', maxHeight: expandida ? 650 : 200, overflowY: 'auto' }}>
        {visibles.map((item, idx) => {
          const esCumple = item.estado === 'cumple'
          const esObs = item.estado === 'parcial' || item.estado === 'observado'
          const estadoColor = esCumple ? '#065F46' : esObs ? '#92400E' : '#7F1D1D'
          const estadoBg    = esCumple ? '#D1FAE5' : esObs ? '#FEF3C7' : '#FEE2E2'
          const estadoIcon  = esCumple ? '✅' : esObs ? '⚠️' : '❌'
          return (
            <div key={idx} style={{ display: 'grid', gridTemplateColumns: '60px 1fr 80px', gap: 8, padding: '6px 16px', borderBottom: '1px solid #F3F4F6', alignItems: 'start', fontSize: 12 }}>
              <span style={{ background: estadoBg, color: estadoColor, borderRadius: 6, padding: '2px 6px', fontWeight: 700, textAlign: 'center', whiteSpace: 'nowrap' }}>{estadoIcon} {item.id || `#${idx+1}`}</span>
              <div>
                <div style={{ color: '#374151', lineHeight: 1.4 }}>{item.descripcion || '—'}</div>
                {item.evidencia && item.evidencia !== 'No encontrado en el documento' && (
                  <div style={{ color: '#6B7280', fontSize: 11, marginTop: 4, fontStyle: 'italic' }}>"{item.evidencia}"</div>
                )}
              </div>
              <span style={{ textAlign: 'right', fontWeight: 600, color: estadoColor }}>{(parseFloat(item.puntos_obtenidos)||0).toFixed(2)} / {(parseFloat(item.puntos_max)||0).toFixed(2)}</span>
            </div>
          )
        })}
      </div>
      {items.length > 6 && (
        <div style={{ padding: '8px 16px', textAlign: 'center', borderTop: '1px solid #F3F4F6' }}>
          <button onClick={() => setExpandida(e => !e)}
            style={{ background: 'none', border: `1px solid ${color}`, color, borderRadius: 6, padding: '4px 14px', fontSize: 12, cursor: 'pointer', fontWeight: 600 }}>
            {expandida ? '▲ Ver menos' : `▼ Ver todos los ${items.length} ítems`}
          </button>
        </div>
      )}
    </div>
  )
}

// ── Sección agente con ítems integrados ───────────────────────────────
function SeccionAgente({ titulo, icono, color, bg, texto, items }) {
  const [expandido, setExpandido] = useState(false)
  if (!texto && (!items || items.length === 0)) return null
  return (
    <div style={{ border: `2px solid ${color}`, borderRadius: 12, overflow: 'hidden', marginBottom: 12 }}>
      <div style={{ background: bg, padding: '12px 20px', display: 'flex', gap: 10, alignItems: 'center' }}>
        <span style={{ fontSize: 20 }}>{icono}</span>
        <span style={{ fontWeight: 700, color, fontSize: 14 }}>{titulo}</span>
      </div>
      {texto && (
        <div style={{ padding: '14px 20px', fontSize: 13, color: '#374151', lineHeight: 1.8, background: '#F8FAFC' }}>
          <div style={{ whiteSpace: 'pre-wrap' }}>{expandido ? texto : texto.slice(0, 350) + (texto.length > 350 ? '...' : '')}</div>
          {texto.length > 350 && (
            <button onClick={() => setExpandido(e => !e)}
              style={{ background: 'none', border: 'none', color, cursor: 'pointer', fontSize: 12, marginTop: 6, padding: 0, fontWeight: 600 }}>
              {expandido ? '▲ ver menos' : '▼ ver más'}
            </button>
          )}
        </div>
      )}
      {items && items.length > 0 && (
        <div style={{ padding: '0 12px 12px' }}>
          <TablaItems items={items} titulo={titulo} color={color} bg={bg} />
        </div>
      )}
    </div>
  )
}

// ── Extractor de secciones por separador ===X=== ─────────────────────
function _extraerSeccion(txt, clave) {
  if (!txt) return ''

  // Si es un JSON estructurado, no intentar extraer con regex de markdown
  try {
    let jsonStr = txt;
    if (txt.includes('```json')) {
      jsonStr = txt.split('```json')[1].split('```')[0];
    } else if (txt.trim().startsWith('{')) {
      const firstBrace = txt.indexOf('{');
      const lastBrace = txt.lastIndexOf('}');
      if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
        jsonStr = txt.substring(firstBrace, lastBrace + 1);
      }
    }
    const asJson = JSON.parse(jsonStr)
    if (asJson && typeof asJson === 'object' && asJson.tipo_resultado) {
      return ''
    }
  } catch (e) {
    // No es JSON puro, continuamos con la extracción basada en texto.
  }

  const normalizar = (v = '') => v
    .toString()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toUpperCase()

  const k = normalizar(clave)
  const aliases = {
    METODOLOGICO: ['METODOLOGICO', 'METODOLOGIA', 'ANALISIS METODOLOGICO', 'EVALUACION METODOLOGICA'],
    TECNICO: ['TECNICO', 'ANALISIS TECNICO', 'EVALUACION TECNICA'],
    LINGUISTICO: ['LINGUISTICO', 'LINGUISTA', 'ANALISIS LINGUISTICO', 'EVALUACION LINGUISTICA'],
    DICTAMEN: ['DICTAMEN', 'DICTAMEN FINAL', 'DICTAMEN JERARQUICO', 'DICTAMEN FINAL OFICIAL', 'VEREDICTO FINAL']
  }

  let objetivo = k
  if (k.includes('METODOL')) objetivo = 'METODOLOGICO'
  else if (k.includes('TECN')) objetivo = 'TECNICO'
  else if (k.includes('LING')) objetivo = 'LINGUISTICO'
  else if (k.includes('DICT') || k.includes('VERED')) objetivo = 'DICTAMEN'

  const tags = aliases[objetivo] || [objetivo]

  // Formato recomendado: ===METODOLOGICO=== ... ===TECNICO===
  for (const tag of tags) {
    const re = new RegExp(`===\\s*${tag}[^=]*===([\\s\\S]*?)(?===\\s*[A-ZÁÉÍÓÚÑ ]{4,}[^=]*===|$)`, 'i')
    const m = txt.match(re)
    if (m?.[1]?.trim()) return m[1].trim()
  }

  // Fallback para respuestas libres del juez jerárquico con Markdown: ### 1. REPORTE...
  const lineas = txt.split(/\r?\n/)
  const indices = []
  lineas.forEach((linea, i) => {
    const limpia = normalizar(linea).replace(/[*#:_-]/g, ' ').replace(/\s+/g, ' ').trim()
    for (const tag of tags) {
      if (limpia.includes(tag)) {
        indices.push(i)
        break
      }
    }
  })

  if (indices.length > 0) {
    const startLine = indices[0]
    let endLine = lineas.length
    for (let j = startLine + 1; j < lineas.length; j++) {
      const l = lineas[j].trim()
      if (/^(#{2,}|\*\*|---)/.test(l) && j > startLine + 2) {
        endLine = j
        break
      }
    }
    return lineas.slice(startLine, endLine).join('\n').trim()
  }

  return ''
}

function _extraerDictamen(txt) {
  if (!txt) return ''
  try {
    let jsonStr = txt;
    if (txt.includes('```json')) {
      jsonStr = txt.split('```json')[1].split('```')[0];
    } else if (txt.trim().startsWith('{')) {
      const firstBrace = txt.indexOf('{');
      const lastBrace = txt.lastIndexOf('}');
      if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
        jsonStr = txt.substring(firstBrace, lastBrace + 1);
      }
    }
    const json = JSON.parse(jsonStr)
    if (json && json.resumen_ejecutivo) {
      return json.resumen_ejecutivo
    }
  } catch (e) {
    // ignorar
  }
  return _extraerSeccion(txt, 'DICTAMEN') || _extraerSeccion(txt, 'VEREDICTO') || ''
}

// Normaliza los ítems enviados por backend para que el veredicto muestre la rúbrica completa.
function _itemsRubricaCompleta(rubricasDetalle, clave, fallback = []) {
  // Prioridad: usar SIEMPRE la rúbrica completa enviada por backend.
  // El fallback del texto de Langflow solo trae 3-5 ítems y por eso antes se veía incompleto.
  const bloque = rubricasDetalle?.[clave]
  const items = bloque?.items || []

  if (items.length > 0) {
    return items.map(i => ({
      ...i,
      estado: i.estado || 'error_evaluacion',
      puntos_max: Number(i.puntos_max || 0),
      puntos_obtenidos: Number(i.puntos_obtenidos || 0),
    }))
  }

  return (fallback || []).map(i => ({
    ...i,
    estado: i.estado || 'error_evaluacion',
    puntos_max: Number(i.puntos_max || 0),
    puntos_obtenidos: Number(i.puntos_obtenidos || 0),
  }))
}

function _puntajeDesdeRubricaDetalle(rubricasDetalle, clave) {
  const bloque = rubricasDetalle?.[clave]
  if (!bloque) return null
  const obtenido = Number(bloque.puntaje_obtenido_estimado)
  const maximo = Number(bloque.puntaje_maximo)
  if (!Number.isFinite(obtenido) || !Number.isFinite(maximo) || maximo <= 0) return null
  return { obtenido, maximo }
}

// ── Tarjeta del veredicto (Jerárquico) ───────────────────────────────
function VeredictoCard({ respuesta, error, latencia_ms, agentes, rubricaIds, rubricasDetalle, disenoInfo, metricasOficiales, veredictoOficial }) {
  if (error) return (
    <div style={{ background: '#FEE2E2', borderRadius: 12, padding: 24, color: '#7F1D1D' }}>
      <strong>❌ Error al obtener veredicto:</strong> {error}
    </div>
  )
  if (!respuesta) return null

  const textoUp = respuesta.toUpperCase()
  const veredictoBackend = (veredictoOficial || metricasOficiales?.veredicto_oficial || '').toUpperCase()
  const esRechazado = veredictoBackend
    ? veredictoBackend === 'RECHAZADO'
    : (textoUp.includes('RECHAZ') || textoUp.includes('NO APROBADO'))
  const esObservaciones = veredictoBackend
    ? veredictoBackend.includes('OBSERV')
    : (!esRechazado && textoUp.includes('OBSERV'))
  const veredictoColor = esRechazado ? '#7F1D1D' : esObservaciones ? '#92400E' : '#065F46'
  const veredictoIcon  = esRechazado ? '❌' : esObservaciones ? '⚠️' : '✅'
  const veredictoLabel = esRechazado ? 'RECHAZADO' : esObservaciones ? 'APROBADO CON OBSERVACIONES' : 'APROBADO'
  const veredictoGrad  = esRechazado ? ['#FEE2E2','#FCA5A5'] : esObservaciones ? ['#FEF3C7','#FDE68A'] : ['#D1FAE5','#6EE7B7']

  // Intentar leer ítems de los agentes si vienen parseados
  const itemsMet  = _itemsRubricaCompleta(rubricasDetalle, 'metodologica', agentes?.metodologico?.evaluaciones || [])
  const itemsTec  = _itemsRubricaCompleta(rubricasDetalle, 'tecnica', agentes?.tecnico?.evaluaciones || [])
  const itemsLin  = _itemsRubricaCompleta(rubricasDetalle, 'linguistica', agentes?.linguistico?.evaluaciones || [])

  // Extraer puntajes del texto si no vienen en JSON
  const puntajeRe = (txt, label) => {
    if (!txt) return null
    const patterns = [
      new RegExp(String.raw`Puntaje\s+${label}[^\n:]*:?\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*([0-9]+(?:\.[0-9]+)?)`, 'i'),
      new RegExp(String.raw`${label}[^\n]*?([0-9]+(?:\.[0-9]+)?)\s*/\s*([0-9]+(?:\.[0-9]+)?)`, 'i'),
    ]
    for (const re of patterns) {
      const m = txt.match(re)
      if (m) return { obtenido: parseFloat(m[1]), maximo: parseFloat(m[2]) }
    }
    return null
  }

  const normalizarPuntaje = (p) => {
    if (!p) return null
    const obtenido = Number(p.obtenido)
    const maximo = Number(p.maximo)
    if (!Number.isFinite(obtenido) || !Number.isFinite(maximo) || maximo <= 0) return null
    return { obtenido, maximo }
  }

  const pMet = normalizarPuntaje(
    _puntajeDesdeRubricaDetalle(rubricasDetalle, 'metodologica') ||
    (agentes?.metodologico
      ? { obtenido: agentes.metodologico.puntaje_total, maximo: agentes.metodologico.puntaje_maximo }
      : puntajeRe(respuesta, 'Metodológico|Metodologico'))
  )
  const pTec = normalizarPuntaje(
    _puntajeDesdeRubricaDetalle(rubricasDetalle, 'tecnica') ||
    (agentes?.tecnico
      ? { obtenido: agentes.tecnico.puntaje_total, maximo: agentes.tecnico.puntaje_maximo }
      : puntajeRe(respuesta, 'Técnico|Tecnico'))
  )
  const pLin = normalizarPuntaje(
    _puntajeDesdeRubricaDetalle(rubricasDetalle, 'linguistica') ||
    (agentes?.linguistico
      ? { obtenido: agentes.linguistico.puntaje_total, maximo: agentes.linguistico.puntaje_maximo }
      : puntajeRe(respuesta, 'Lingüístico|Linguistico'))
  )

  const rigorMatch = respuesta.match(/RIGOR SCORE FINAL[:\s]*([0-9.]+)/i)
  const rigorBackend = Number(metricasOficiales?.rigor_score)
  const rigorScore = Number.isFinite(rigorBackend)
    ? rigorBackend
    : (rigorMatch ? parseFloat(rigorMatch[1]) : null)

  const secMet  = _extraerSeccion(respuesta, 'METODOLOGICO')
  const secTec  = _extraerSeccion(respuesta, 'TECNICO')
  const secLin  = _extraerSeccion(respuesta, 'LINGUISTICO')
  const secDict = _extraerDictamen(respuesta)

  const tieneSecciones = !!(secMet || secTec || secLin || secDict)

  return (
    <div>
      {/* Banner veredicto */}
      <div style={{ background: `linear-gradient(135deg, ${veredictoGrad[0]}, ${veredictoGrad[1]})`, border: `2px solid ${veredictoColor}33`, borderRadius: 16, padding: '20px 24px', textAlign: 'center', marginBottom: 16 }}>
        <div style={{ fontSize: 40, marginBottom: 6 }}>{veredictoIcon}</div>
        <div style={{ fontWeight: 900, fontSize: 22, color: veredictoColor, letterSpacing: 1 }}>{veredictoLabel}</div>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginTop: 10, flexWrap: 'wrap' }}>
          {latencia_ms > 0 && <span style={{ background: '#fff8', borderRadius: 8, padding: '3px 10px', fontSize: 12, color: '#374151' }}>⚡ {(latencia_ms/1000).toFixed(1)}s</span>}
          {rigorScore !== null && (
            <span style={{ background: '#fff8', borderRadius: 8, padding: '3px 10px', fontSize: 13, fontWeight: 700, color: veredictoColor }}>
              📊 Rigor Score: {rigorScore.toFixed(2)}
            </span>
          )}
        </div>
        {/* Barras de puntaje por dimensión */}
        {(pMet || pTec || pLin) && (
          <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 14, flexWrap: 'wrap' }}>
            {[['📐 Met', pMet, '#3B82F6'], ['⚙️ Tec', pTec, '#8B5CF6'], ['📝 Lin', pLin, '#10B981']].map(([lbl, p, col]) => p && (
              <div key={lbl} style={{ background: '#fff8', borderRadius: 10, padding: '8px 14px', minWidth: 100 }}>
                <div style={{ fontSize: 11, color: '#374151', fontWeight: 600, marginBottom: 4 }}>{lbl}</div>
                <div style={{ height: 6, background: '#E5E7EB', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ height: 6, background: col, width: `${Number.isFinite(p?.obtenido) && Number.isFinite(p?.maximo) && p.maximo > 0 ? Math.min(100, (p.obtenido / p.maximo) * 100) : 0}%`, borderRadius: 3 }} />
                </div>
                <div style={{ fontSize: 12, fontWeight: 700, color: col, marginTop: 3 }}>
                  {Number.isFinite(p?.obtenido) && Number.isFinite(p?.maximo) ? `${p.obtenido.toFixed(2)} / ${p.maximo.toFixed(2)} pts` : 'Puntaje no reportado'}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Resumen de ítems por rúbrica (si hay agentes parseados) ── */}
      {(itemsMet.length > 0 || itemsTec.length > 0 || itemsLin.length > 0) && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
          {[
            { label: 'Metodológico', items: itemsMet, color: '#1D4ED8', bg: '#EFF6FF', icon: '📐', id: rubricaIds?.metodologica },
            { label: 'Técnico',      items: itemsTec, color: '#6D28D9', bg: '#F5F3FF', icon: '⚙️', id: rubricaIds?.tecnica },
            { label: 'Lingüístico',  items: itemsLin, color: '#065F46', bg: '#ECFDF5', icon: '📝', id: rubricaIds?.linguistica },
          ].filter(s => s.items.length > 0).map(sec => {
            const aprobados  = sec.items.filter(i => i.estado === 'cumple').length
            const parciales  = sec.items.filter(i => i.estado === 'parcial' || i.estado === 'observado').length
            const total      = sec.items.length
            const pct        = Math.round((aprobados / total) * 100)
            return (
              <div key={sec.label} style={{ flex: 1, minWidth: 160, background: sec.bg, border: `1.5px solid ${sec.color}22`, borderRadius: 12, padding: '10px 14px' }}>
                <div style={{ fontWeight: 700, color: sec.color, fontSize: 13, marginBottom: 6 }}>
                  {sec.icon} {sec.label} {sec.id && <span style={{ fontSize: 11, opacity: 0.7 }}>({sec.id})</span>}
                </div>
                <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
                  <span style={{ background: '#D1FAE5', color: '#065F46', fontSize: 11, padding: '2px 7px', borderRadius: 10, fontWeight: 700 }}>✅ {aprobados} cumple</span>
                  {parciales > 0 && <span style={{ background: '#FEF3C7', color: '#92400E', fontSize: 11, padding: '2px 7px', borderRadius: 10, fontWeight: 700 }}>⚠️ {parciales} observado</span>}
                  <span style={{ background: '#FEE2E2', color: '#7F1D1D', fontSize: 11, padding: '2px 7px', borderRadius: 10, fontWeight: 700 }}>❌ {total - aprobados - parciales} no cumple</span>
                </div>
                <div style={{ height: 6, background: '#E5E7EB', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ height: 6, background: sec.color, width: `${pct}%`, borderRadius: 3, transition: 'width 0.4s' }} />
                </div>
                <div style={{ fontSize: 11, color: sec.color, fontWeight: 700, marginTop: 3 }}>{pct}% de ítems aprobados ({aprobados}/{total})</div>
              </div>
            )
          })}
        </div>
      )}

      {/* Secciones por agente con ítems */}
      {tieneSecciones ? (
        <>
          <SeccionAgente titulo="Agente Metodológico" icono="📐" color="#1D4ED8" bg="#EFF6FF" texto={secMet} items={itemsMet} />
          <SeccionAgente titulo="Agente Técnico"       icono="⚙️" color="#6D28D9" bg="#F5F3FF" texto={secTec} items={itemsTec} />
          <SeccionAgente titulo="Agente Lingüístico"   icono="📝" color="#065F46" bg="#ECFDF5" texto={secLin} items={itemsLin} />
          {secDict && (
            <div style={{ border: '2px solid #F59E0B', borderRadius: 12, overflow: 'hidden', marginBottom: 12 }}>
              <div style={{ background: '#FFFBEB', padding: '12px 20px', display: 'flex', gap: 10, alignItems: 'center' }}>
                <span style={{ fontSize: 20 }}>⚖️</span>
                <span style={{ fontWeight: 700, color: '#92400E', fontSize: 14 }}>Dictamen Final — Presidente del Comité</span>
              </div>
              <div style={{ padding: '14px 20px', fontSize: 13, color: '#374151', lineHeight: 1.8, whiteSpace: 'pre-wrap', background: '#FFFDF0' }}>
                {secDict}
              </div>
            </div>
          )}
        </>
      ) : (
        /* Fallback: mostrar texto completo si no hay separadores */
        <>
          {itemsMet.length > 0 && <SeccionAgente titulo="Agente Metodológico" icono="📐" color="#1D4ED8" bg="#EFF6FF" texto={secMet} items={itemsMet} />}
          {itemsTec.length > 0 && <SeccionAgente titulo="Agente Técnico"       icono="⚙️" color="#6D28D9" bg="#F5F3FF" texto={secTec} items={itemsTec} />}
          {itemsLin.length > 0 && <SeccionAgente titulo="Agente Lingüístico"   icono="📝" color="#065F46" bg="#ECFDF5" texto={secLin} items={itemsLin} />}
          <div style={{ background: '#F8FAFC', border: '1px solid #E5E7EB', borderRadius: 10, padding: 16 }}>
            <div style={{ fontSize: 12, color: '#6B7280', fontWeight: 600, marginBottom: 8 }}>📄 Dictamen completo del Comité</div>
            <div style={{ fontSize: 13, color: '#374151', whiteSpace: 'pre-wrap', lineHeight: 1.7, maxHeight: 500, overflowY: 'auto' }}>
              {(() => {
                try {
                  const asJson = JSON.parse(respuesta);
                  return asJson.resumen_ejecutivo || respuesta;
                } catch(e) {
                  return respuesta;
                }
              })()}
            </div>
          </div>
        </>
      )}

      <details style={{ border: '1px solid #E5E7EB', borderRadius: 8, marginTop: 8 }}>
        <summary style={{ padding: '8px 14px', fontSize: 12, cursor: 'pointer', color: '#6B7280', fontWeight: 600 }}>📄 Ver respuesta raw completa</summary>
        <div style={{ padding: '12px 16px', fontSize: 12, color: '#374151', whiteSpace: 'pre-wrap', lineHeight: 1.7, maxHeight: 400, overflowY: 'auto', background: '#F8FAFC' }}>{respuesta}</div>
      </details>
    </div>
  )
}



// ── Tarjeta ejecutiva para Análisis Rápido / Secuencial ─────────────────────
function _extraerListaSimple(texto, titulo, limite = 3) {
  if (!texto) return []
  const re = new RegExp(`${titulo}[:\\s]*\\n([\\s\\S]*?)(?=\\n[A-ZÁÉÍÓÚÑ ]{4,}:|\\n===|$)`, 'i')
  const m = texto.match(re)
  const bloque = m ? m[1] : ''
  return bloque
    .split(/\n+/)
    .map(x => x.replace(/^[-•\d.)\s]+/, '').trim())
    .filter(x => x.length > 8)
    .slice(0, limite)
}

function _extraerPuntajeLinea(texto, etiqueta) {
  if (!texto) return null
  const re = new RegExp(`Puntaje\\s+${etiqueta}[^:]*:\\s*([0-9]+(?:\\.[0-9]+)?)\\s*\\/\\s*([0-9]+(?:\\.[0-9]+)?)`, 'i')
  const m = texto.match(re)
  if (!m) return null
  const obtenido = parseFloat(m[1])
  const maximo = parseFloat(m[2])
  if (!Number.isFinite(obtenido) || !Number.isFinite(maximo) || maximo <= 0) return null
  return { obtenido, maximo, pct: Math.round((obtenido / maximo) * 100) }
}

function _extraerVeredictoSimple(texto) {
  if (!texto) return 'OBSERVADO'
  const m = texto.match(/VEREDICTO\s*FINAL\s*:\s*(APROBADO(?:\s+CON\s+OBSERVACIONES)?|OBSERVADO|RECHAZADO)/i)
  if (m) return m[1].toUpperCase()
  if (/RECHAZAD/i.test(texto)) return 'RECHAZADO'
  if (/APROB/i.test(texto)) return 'APROBADO'
  return 'OBSERVADO'
}


function _obtenerEstadoDiagnostico(textoArea) {
  const t = (textoArea || '').toLowerCase()
  const faltas = (textoArea.match(/\bFALTA\b|no cumple|no se presenta|no se incluye|ausencia total|carece|errores graves/gi) || []).length
  const observado = (textoArea.match(/observado|requiere revisión|requiere revision|inconsistencia/gi) || []).length
  const m = textoArea.match(/(\d+(?:[.,]\d+)?)\s*\/\s*(\d+(?:[.,]\d+)?)/)
  const obtenido = m ? parseFloat(m[1].replace(',', '.')) : null
  const maximo = m ? parseFloat(m[2].replace(',', '.')) : null
  const pct = Number.isFinite(obtenido) && Number.isFinite(maximo) && maximo > 0 ? (obtenido / maximo) * 100 : null

  if (faltas >= 5 || (pct !== null && pct < 35) || /ausencia total|deficiencias críticas|rechazado/i.test(textoArea)) {
    return { icono: '🔴', texto: 'Crítico', color: '#B91C1C', border: '#FCA5A5', detalle: 'Requiere atención prioritaria.' }
  }
  if (faltas >= 2 || observado >= 1 || (pct !== null && pct < 75)) {
    return { icono: '🟡', texto: 'Requiere revisión', color: '#92400E', border: '#FCD34D', detalle: 'Presenta observaciones importantes.' }
  }
  return { icono: '🟢', texto: 'Adecuado', color: '#047857', border: '#86EFAC', detalle: 'No se detectan alertas críticas.' }
}

function QuickAnalysisCard({ texto, latencia_ms, disenoInfo, agentes }) {
  const txt = texto || ''
  const consenso = agentes?.consenso && agentes.consenso.tipo_resultado === 'diagnostico_preliminar'
    ? agentes.consenso
    : null
  const estadoGeneral = consenso?.estado_diagnostico || 'requiere_revision'
  const configuracionEstado = {
    sin_alertas_relevantes: { label: 'SIN ALERTAS RELEVANTES', color: '#047857', bg: '#D1FAE5', icono: '🟢' },
    requiere_revision: { label: 'REQUIERE REVISIÓN', color: '#92400E', bg: '#FEF3C7', icono: '🟡' },
    atencion_prioritaria: { label: 'ATENCIÓN PRIORITARIA', color: '#B91C1C', bg: '#FEE2E2', icono: '🔴' },
  }
  const estadoVisual = configuracionEstado[estadoGeneral] || configuracionEstado.requiere_revision
  const { label: veredicto, color, bg, icono } = estadoVisual

  // Si el texto completo es un JSON, ya _extraerSeccion devuelve ''. Así evitamos repetir el JSON crudo.
  let secMet = _extraerSeccion(txt, 'METODOLOGICO')
  let secTec = _extraerSeccion(txt, 'TECNICO')
  let secLin = _extraerSeccion(txt, 'LINGUISTICO')

  // Evitamos hacer `|| txt` si txt es JSON
  let esJson = false;
  try {
    JSON.parse(txt);
    esJson = true;
  } catch(e){}

  if (!esJson) {
    secMet = secMet || txt;
    secTec = secTec || txt;
    secLin = secLin || txt;
  }

  let fortalezas = consenso?.fortalezas_principales || _extraerListaSimple(txt, 'Fortalezas', 3)
  let debilidades = consenso?.debilidades_principales || _extraerListaSimple(txt, 'Debilidades', 6)
  let recomendaciones = consenso?.recomendaciones_inmediatas || _extraerListaSimple(txt, 'Recomendaciones', 3)
  if (debilidades.length === 0) debilidades = (txt.match(/\d+\.\s*[^\n]*(?:FALTA|No se|Ausencia|Errores|carece)[^\n]*/gi) || []).slice(0, 6).map(x => x.replace(/^\d+\.\s*/, ''))
  if (recomendaciones.length === 0) recomendaciones = (txt.match(/\[Alta\][^\n]+|\[Media\][^\n]+|\[Baja\][^\n]+/gi) || []).slice(0, 3)

  // Algunas respuestas concentran las observaciones en la lista final en vez
  // de repetirlas dentro de cada bloque. Se combinan ambas fuentes para evitar
  // mostrar "Adecuado" cuando sí existen debilidades explícitas del área.
  const debMet = debilidades.filter(x => /metodol[oó]g/i.test(x)).join('\n')
  const debTec = debilidades.filter(x => /t[eé]cnic/i.test(x)).join('\n')
  const debLin = debilidades.filter(x => /ling[uü][ií]st|redacci[oó]n|apa|citaci[oó]n|ortograf/i.test(x)).join('\n')
  const estadoDesdeCodigo = (codigo, fallbackTexto) => {
    const mapa = {
      sin_alertas_relevantes: { icono: '🟢', texto: 'Sin alertas relevantes', color: '#047857', border: '#86EFAC', detalle: 'No se detectan alertas críticas en la muestra.' },
      requiere_revision: { icono: '🟡', texto: 'Requiere revisión', color: '#92400E', border: '#FCD34D', detalle: 'Presenta observaciones importantes.' },
      atencion_prioritaria: { icono: '🔴', texto: 'Atención prioritaria', color: '#B91C1C', border: '#FCA5A5', detalle: 'Requiere correcciones prioritarias.' },
    }
    return mapa[codigo] || _obtenerEstadoDiagnostico(fallbackTexto)
  }
  const niveles = consenso?.niveles_por_dimension || {}
  const estadoMet = estadoDesdeCodigo(niveles.metodologico, `${secMet}\n${debMet}`)
  const estadoTec = estadoDesdeCodigo(niveles.tecnico, `${secTec}\n${debTec}`)
  const estadoLin = estadoDesdeCodigo(niveles.linguistico, `${secLin}\n${debLin}`)

  const EstadoMini = ({ label, estado }) => (
    <div style={{ background: '#fff', border: `1.5px solid ${estado.border}`, borderRadius: 12, padding: 12 }}>
      <div style={{ fontSize: 12, color: '#6B7280', fontWeight: 800, marginBottom: 8 }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 22 }}>{estado.icono}</span>
        <span style={{ fontSize: 14, color: estado.color, fontWeight: 900 }}>{estado.texto}</span>
      </div>
      <div style={{ fontSize: 11, color: '#6B7280', marginTop: 6, lineHeight: 1.35 }}>
        {estado.detalle}
      </div>
    </div>
  )

  return (
    <div>
      <div style={{ background: bg, border: `2px solid ${color}33`, borderRadius: 16, padding: 18, marginBottom: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 12, color, fontWeight: 900, marginBottom: 4 }}>⚡ DIAGNÓSTICO PRELIMINAR</div>
            <div style={{ fontSize: 24, fontWeight: 900, color }}>{icono} {veredicto}</div>
            <div style={{ marginTop: 6, fontSize: 13, color: '#374151', maxWidth: 680, lineHeight: 1.55 }}>
              Resultado referencial del flujo secuencial. Para la evaluación oficial con rúbrica completa, utiliza <strong>Obtener Veredicto</strong>.
            </div>
          </div>
          <div style={{ textAlign: 'right', fontSize: 12, color: '#6B7280' }}>
            {latencia_ms > 0 && <div>⚡ {(latencia_ms / 1000).toFixed(1)}s</div>}
            {disenoInfo && <div>📋 {disenoInfo.enfoque || ''} / {disenoInfo.rama || disenoInfo.diseno || ''}</div>}
          </div>
        </div>
      </div>

      <div style={{ background: '#F8FAFC', border: '1.5px solid #E5E7EB', borderRadius: 12, padding: 12, marginBottom: 12, fontSize: 13, color: '#374151', lineHeight: 1.55 }}>
        ⚠️ Este diagnóstico es preliminar y no representa la calificación oficial. Su finalidad es identificar rápidamente las áreas con mayores observaciones. Para ver puntajes, rúbrica completa y dictamen definitivo, usa <strong>Obtener Veredicto</strong>.
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 10, marginBottom: 14 }}>
        <EstadoMini label="📐 Metodología" estado={estadoMet} />
        <EstadoMini label="⚙️ Técnico" estado={estadoTec} />
        <EstadoMini label="📝 Lingüístico" estado={estadoLin} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12, marginBottom: 12 }}>
        <div style={{ background: '#F8FAFC', border: '1px solid #E5E7EB', borderRadius: 12, padding: 14 }}>
          <div style={{ fontWeight: 800, color: '#065F46', marginBottom: 8 }}>✅ Fortalezas rápidas</div>
          {(fortalezas.length ? fortalezas : ['Contexto de investigación identificado.']).map((x, i) => <div key={i} style={{ fontSize: 13, color: '#374151', marginBottom: 6 }}>• {x}</div>)}
        </div>
        <div style={{ background: '#FFF7ED', border: '1px solid #FED7AA', borderRadius: 12, padding: 14 }}>
          <div style={{ fontWeight: 800, color: '#9A3412', marginBottom: 8 }}>⚠️ Debilidades principales</div>
          {(debilidades.length ? debilidades : ['Requiere revisión metodológica, técnica y lingüística.']).map((x, i) => <div key={i} style={{ fontSize: 13, color: '#374151', marginBottom: 6 }}>• {x}</div>)}
        </div>
        <div style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: 12, padding: 14 }}>
          <div style={{ fontWeight: 800, color: '#1D4ED8', marginBottom: 8 }}>🚀 Recomendaciones inmediatas</div>
          {(recomendaciones.length ? recomendaciones : ['Solicitar el veredicto formal con rúbrica completa.']).map((x, i) => <div key={i} style={{ fontSize: 13, color: '#374151', marginBottom: 6 }}>{i + 1}. {x}</div>)}
        </div>
      </div>

      <details style={{ border: '1px solid #E5E7EB', borderRadius: 8 }}>
        <summary style={{ padding: '8px 14px', fontSize: 12, cursor: 'pointer', color: '#6B7280', fontWeight: 700 }}>📄 Ver análisis técnico completo generado por agentes</summary>
        <div style={{ padding: '12px 16px', fontSize: 12, color: '#374151', lineHeight: 1.7, whiteSpace: 'pre-wrap', maxHeight: 420, overflowY: 'auto', background: '#F8FAFC' }}>
          {txt}
        </div>
      </details>
    </div>
  )
}

// ── Tarjeta visual para Human-in-the-Loop ─────────────────────────────
function _extraerSeccionHumanLoop(texto, nombre) {
  if (!texto) return ''
  const escaped = nombre.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

  const patrones = [
    new RegExp(`###\\s*${escaped}\\s*\\n([\\s\\S]*?)(?=\\n###\\s|\\n---\\s*\\n|$)`, 'i'),
    new RegExp(`\\*\\*${escaped}\\*\\*\\s*\\n([\\s\\S]*?)(?=\\n\\*\\*|\\n###\\s|\\n---\\s*\\n|$)`, 'i'),
    new RegExp(`${escaped}\\s*:?\\s*\\n([\\s\\S]*?)(?=\\n(?:###|Evaluación|Correcciones|Rigor Score|Veredicto|Justificación|Recomendaciones)\\b|$)`, 'i')
  ]

  for (const re of patrones) {
    const m = texto.match(re)
    if (m && m[1]?.trim()) return m[1].trim()
  }
  return ''
}

function _extraerTituloHumanLoop(texto) {
  if (!texto) return ''
  const m = texto.match(/(?:Título de la tesis|Titulo de la tesis)\s*:?\s*\n?\s*[“"]?([^\n”"]+)/i)
  return m ? m[1].replace(/\*\*/g, '').trim() : ''
}

function _extraerScoreHumanLoop(texto) {
  if (!texto) return null
  const m = texto.match(/Rigor Score final[\s\S]{0,120}?([0-9]+(?:\.[0-9]+)?)\s*\/\s*([0-9]+(?:\.[0-9]+)?)/i)
  if (!m) return null
  return { obtenido: parseFloat(m[1]), maximo: parseFloat(m[2]) }
}

function _extraerVeredictoHumanLoop(texto, decisionDocente) {
  if (decisionDocente === 'aprobado') return 'APROBADO'
  if (decisionDocente === 'aprobado_con_cambios') return 'APROBADO CON CAMBIOS'
  if (decisionDocente === 'rechazado') return 'RECHAZADO'

  const m = texto?.match(/Veredicto final\s*:?\s*([\s\S]{0,80})/i)
  const raw = m ? m[1].toUpperCase() : ''
  if (raw.includes('RECHAZ')) return 'RECHAZADO'
  if (raw.includes('CAMBIO') || raw.includes('OBSERV')) return 'APROBADO CON CAMBIOS'
  if (raw.includes('APROB')) return 'APROBADO'
  return 'NO DEFINIDO'
}

function HumanLoopCard({ humanLoop, selectedThesis }) {
  if (!humanLoop?.texto_crudo) return null

  const texto = humanLoop.texto_crudo || ''
  const veredicto = _extraerVeredictoHumanLoop(texto, humanLoop.decision_docente)
  const rechazado = veredicto.includes('RECHAZ')
  const observado = !rechazado && (veredicto.includes('CAMBIOS') || veredicto.includes('OBSERV'))
  const color = rechazado ? '#7F1D1D' : observado ? '#92400E' : '#065F46'
  const bg = rechazado ? '#FEE2E2' : observado ? '#FEF3C7' : '#D1FAE5'
  const border = rechazado ? '#FCA5A5' : observado ? '#FDE68A' : '#6EE7B7'
  const icono = rechazado ? '❌' : observado ? '✏️' : '✅'

  const titulo = _extraerTituloHumanLoop(texto) || selectedThesis?.titulo || 'Tesis evaluada'
  const score = _extraerScoreHumanLoop(texto)
  const scorePct = score ? Math.round((score.obtenido / score.maximo) * 100) : null

  const met = _extraerSeccionHumanLoop(texto, 'Evaluación metodológica') || _extraerSeccionHumanLoop(texto, 'Evaluacion metodologica')
  const tec = _extraerSeccionHumanLoop(texto, 'Evaluación técnica') || _extraerSeccionHumanLoop(texto, 'Evaluacion tecnica')
  const lin = _extraerSeccionHumanLoop(texto, 'Evaluación lingüística') || _extraerSeccionHumanLoop(texto, 'Evaluacion linguistica')
  const correcciones = _extraerSeccionHumanLoop(texto, 'Correcciones aplicadas por el supervisor humano')
  const justificacion = _extraerSeccionHumanLoop(texto, 'Justificación final') || _extraerSeccionHumanLoop(texto, 'Justificacion final')
  const recomendaciones = _extraerSeccionHumanLoop(texto, 'Recomendaciones finales')

  return (
    <div style={{ marginTop: 24 }}>
      <div style={{ background: `linear-gradient(135deg, ${bg}, #fff)`, border: `2px solid ${border}`, borderRadius: 16, padding: 22, marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 260 }}>
            <div style={{ fontSize: 13, color, fontWeight: 800, marginBottom: 6 }}>👨‍🏫 HUMAN-IN-THE-LOOP — DICTAMEN OFICIAL</div>
            <div style={{ fontSize: 18, color: '#1F2937', fontWeight: 800, lineHeight: 1.35 }}>{titulo}</div>
            <div style={{ marginTop: 12, background: '#fff9', border: `1px solid ${border}`, borderRadius: 10, padding: '10px 12px', fontSize: 13, color: '#374151', lineHeight: 1.6 }}>
              <div><strong style={{ color }}>Decisión del docente:</strong> {humanLoop.decision_docente || veredicto}</div>
              {humanLoop.comentario_docente && <div style={{ marginTop: 6 }}><strong style={{ color }}>Observación del docente:</strong> {humanLoop.comentario_docente}</div>}
              <div style={{ marginTop: 6, color: '#6B7280', fontSize: 12 }}>El criterio del docente prevalece sobre el diagnóstico preliminar de la IA.</div>
            </div>
          </div>

          <div style={{ minWidth: 180, textAlign: 'center', background: '#fff9', borderRadius: 14, padding: '14px 18px', border: `1px solid ${border}` }}>
            <div style={{ fontSize: 36 }}>{icono}</div>
            <div style={{ fontSize: 18, fontWeight: 900, color, marginTop: 4 }}>{veredicto}</div>
            {score && (
              <>
                <div style={{ height: 8, background: '#E5E7EB', borderRadius: 4, overflow: 'hidden', marginTop: 10 }}>
                  <div style={{ height: 8, width: `${Math.min(scorePct, 100)}%`, background: color, borderRadius: 4 }} />
                </div>
                <div style={{ fontSize: 12, color, fontWeight: 800, marginTop: 5 }}>
                  Score final referencial: {score.obtenido.toFixed(1)} / {score.maximo.toFixed(1)}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12, marginBottom: 12 }}>
        {correcciones && (
          <div style={{ background: '#EFF6FF', border: '1.5px solid #93C5FD', borderRadius: 12, padding: 14 }}>
            <div style={{ color: '#1D4ED8', fontWeight: 800, fontSize: 13, marginBottom: 8 }}>🧑‍🏫 Correcciones del supervisor</div>
            <div style={{ fontSize: 13, color: '#374151', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>{correcciones}</div>
          </div>
        )}
        {justificacion && (
          <div style={{ background: '#FFFBEB', border: '1.5px solid #FDE68A', borderRadius: 12, padding: 14 }}>
            <div style={{ color: '#92400E', fontWeight: 800, fontSize: 13, marginBottom: 8 }}>⚖️ Justificación final</div>
            <div style={{ fontSize: 13, color: '#374151', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>{justificacion}</div>
          </div>
        )}
      </div>

      <SeccionAgente titulo="Evaluación metodológica" icono="📐" color="#1D4ED8" bg="#EFF6FF" texto={met} items={[]} />
      <SeccionAgente titulo="Evaluación técnica" icono="⚙️" color="#6D28D9" bg="#F5F3FF" texto={tec} items={[]} />
      <SeccionAgente titulo="Evaluación lingüística" icono="📝" color="#065F46" bg="#ECFDF5" texto={lin} items={[]} />

      {recomendaciones && (
        <div style={{ border: '2px solid #10B981', borderRadius: 12, overflow: 'hidden', marginBottom: 12 }}>
          <div style={{ background: '#ECFDF5', padding: '12px 20px', display: 'flex', gap: 10, alignItems: 'center' }}>
            <span style={{ fontSize: 20 }}>✅</span>
            <span style={{ fontWeight: 700, color: '#065F46', fontSize: 14 }}>Recomendaciones finales</span>
          </div>
          <div style={{ padding: '14px 20px', fontSize: 13, color: '#374151', lineHeight: 1.8, whiteSpace: 'pre-wrap', background: '#F8FAFC' }}>
            {recomendaciones}
          </div>
        </div>
      )}

      <details style={{ border: '1px solid #E5E7EB', borderRadius: 8 }}>
        <summary style={{ padding: '8px 14px', fontSize: 12, cursor: 'pointer', color: '#6B7280', fontWeight: 600 }}>
          📄 Ver dictamen Human-in-the-Loop completo
        </summary>
        <div style={{ padding: '12px 16px', fontSize: 12, color: '#374151', whiteSpace: 'pre-wrap', lineHeight: 1.7, maxHeight: 420, overflowY: 'auto', background: '#F8FAFC' }}>
          {texto}
        </div>
      </details>
    </div>
  )
}

export default function Dashboard() {
  const { user, logoutUser } = useAuth()
  const navigate = useNavigate()

  const [tesisList, setTesisList]       = useState([])
  const [selectedThesis, setSelectedThesis] = useState(null)
  const [analisis, setAnalisis]         = useState(null)
  const [uploading, setUploading]       = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [analyzing, setAnalyzing]       = useState(false)
  const [titulo, setTitulo]             = useState('')
  const [file, setFile]                 = useState(null)
  const [uploadError, setUploadError]   = useState('')
  const [tab, setTab]                   = useState('upload')
  const pollingRef = useRef(null)

  useEffect(() => { cargarTesis(); return () => clearInterval(pollingRef.current) }, [])

  const cargarTesis = async () => {
    try { setTesisList(await getMyThesis()) } catch (err) { if (err.response?.status === 404) { clearInterval(pollingRef.current); setAnalyzing(false); setUploadError('El servidor se reinició o la tesis fue eliminada. Por favor, vuelve a subir el documento.'); } }
  }

  const iniciarPolling = (thesisId) => {
    clearInterval(pollingRef.current)
    pollingRef.current = setInterval(async () => {
      try {
        const res = await getAnalysisResult(thesisId)
        if (res.estado !== 'en_analisis') {
          clearInterval(pollingRef.current)
          setAnalyzing(false)
          setAnalisis(res)
          setTab('resultado')
          cargarTesis()
        }
      } catch (err) { if (err.response?.status === 404) { clearInterval(pollingRef.current); setAnalyzing(false); setUploadError('El servidor se reinició o la tesis fue eliminada. Por favor, vuelve a subir el documento.'); } }
    }, 5000)
  }

  // Sube el PDF y decide qué flujo correr según el botón presionado
  const handleUploadYAnalizar = async (tipo) => {
    if (!file || !titulo.trim()) { setUploadError('Completa el título y selecciona un PDF'); return }
    if (!file.name.toLowerCase().endsWith('.pdf')) { setUploadError('Solo se aceptan PDFs'); return }
    if (file.size > 20 * 1024 * 1024) { setUploadError('El archivo supera los 20MB'); return }

    setUploading(true); setUploadError(''); setUploadProgress(0)
    try {
      const tesis = await uploadThesis(titulo, file, (evt) => {
        setUploadProgress(Math.round((evt.loaded / evt.total) * 100))
      })
      setTesisList(prev => [tesis, ...prev])
      setSelectedThesis(tesis)
      setAnalyzing(true)
      setTab('resultado')

      if (tipo === 'completo') {
        await analizarCompleto(tesis.id)
      } else if (tipo === 'debate') {
        await debateRed(tesis.id)
      } else {
        await obtenerVeredicto(tesis.id)
      }
      iniciarPolling(tesis.id)
      setTitulo(''); setFile(null)
    } catch (err) {
      setUploadError(err.response?.data?.detail || 'Error al procesar el archivo')
      setAnalyzing(false)
    } finally {
      setUploading(false)
    }
  }

  // Ver resultado de una tesis ya existente del historial
  const verResultado = async (tesis) => {
    setSelectedThesis(tesis)
    setTab('resultado')
    try {
      const res = await getAnalysisResult(tesis.id)
      setAnalisis(res)
      if (res.estado === 'en_analisis') { setAnalyzing(true); iniciarPolling(tesis.id) }
      else setAnalyzing(false)
    } catch (err) { if (err.response?.status === 404) { clearInterval(pollingRef.current); setAnalyzing(false); setUploadError('El servidor se reinició o la tesis fue eliminada. Por favor, vuelve a subir el documento.'); } }
  }

  const r = analisis?.resultado || {}
  const tipoAnalisis = r.tipo  // 'analisis_completo' | 'veredicto' | 'debate_red'
  const secuencial   = r.secuencial   || {}
  const jerarquico   = r.jerarquico   || {}
  const humanLoop    = r.human_loop   || {}
  const red          = r.red          || {}
  const disenoInfo   = r.diseno_info  || null
  const rubrica      = r.rubrica      || null
  // Outputs individuales por agente (nuevo: cada uno tiene su propio JSON)
  const agentes      = r.agentes      || {}
  const datosMet     = agentes.metodologico || null
  const datosTec     = agentes.tecnico      || null
  const datosLin     = agentes.linguistico  || null
  const datosConsenso = agentes.consenso    || null

  return (
    <div style={{ minHeight: '100vh', background: '#F0F4F8' }}>

      {/* Navbar */}
      <nav style={{ background: C.primary, color: '#fff', padding: '12px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <span style={{ fontWeight: 800, fontSize: 16 }}>UPAO — Sistema de Análisis de Tesis</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <span style={{ fontSize: 13 }}>👤 {user?.nombre}</span>
          <button onClick={() => { logoutUser(); navigate('/login') }}
            style={{ background: 'rgba(255,255,255,0.2)', border: 'none', color: '#fff', padding: '6px 14px', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>
            Cerrar sesión
          </button>
        </div>
      </nav>

      <div style={{ maxWidth: 860, margin: '0 auto', padding: '32px 24px' }}>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
          {[['upload', '📤 Subir Tesis'], ['resultado', '🔍 Ver Análisis'], ['historial', '📋 Historial']].map(([key, label]) => (
            <button key={key} onClick={() => setTab(key)} style={{
              padding: '8px 20px', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: 13,
              background: tab === key ? C.primary : '#fff',
              color: tab === key ? '#fff' : '#374151',
              boxShadow: tab === key ? '0 2px 8px rgba(31,56,100,0.3)' : '0 1px 3px rgba(0,0,0,0.1)',
            }}>{label}</button>
          ))}
        </div>

        {/* ── TAB UPLOAD ── */}
        {tab === 'upload' && (
          <div style={{ background: '#fff', borderRadius: 16, padding: 32, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
            <h2 style={{ color: C.primary, marginBottom: 4 }}>📤 Subir Tesis</h2>
            <p style={{ color: '#666', fontSize: 13, marginBottom: 24 }}>Elige el tipo de análisis que necesitas.</p>

            {uploadError && (
              <div style={{ background: '#FEE2E2', color: '#7F1D1D', padding: '10px 16px', borderRadius: 8, marginBottom: 16, fontSize: 13 }}>
                {uploadError}
              </div>
            )}

            {/* Título */}
            <label style={{ display: 'block', fontWeight: 600, fontSize: 13, color: '#444', marginBottom: 6 }}>Título de la tesis</label>
            <input value={titulo} onChange={e => setTitulo(e.target.value)}
              placeholder="Ej: Sistema Multiagente para análisis de tesis UPAO"
              style={{ width: '100%', padding: '10px 14px', border: '1.5px solid #ddd', borderRadius: 8, fontSize: 14, marginBottom: 20, boxSizing: 'border-box' }} />

            {/* Archivo */}
            <label style={{ display: 'block', fontWeight: 600, fontSize: 13, color: '#444', marginBottom: 6 }}>Archivo PDF</label>
            <div style={{ border: '2px dashed #CBD5E1', borderRadius: 8, padding: 24, textAlign: 'center', marginBottom: 24 }}>
              <input type="file" accept=".pdf" onChange={e => setFile(e.target.files[0])} style={{ display: 'none' }} id="pdf-input" />
              <label htmlFor="pdf-input" style={{ cursor: 'pointer' }}>
                <div style={{ fontSize: 32, marginBottom: 8 }}>📄</div>
                <div style={{ color: C.primary, fontWeight: 600 }}>
                  {file ? file.name : 'Haz clic para seleccionar un PDF'}
                </div>
                <div style={{ color: '#9CA3AF', fontSize: 12, marginTop: 4 }}>Máximo 20MB</div>
              </label>
            </div>

            {/* Progress bar */}
            {uploading && (
              <div style={{ marginBottom: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#666', marginBottom: 4 }}>
                  <span>Subiendo...</span><span>{uploadProgress}%</span>
                </div>
                <div style={{ background: '#E5E7EB', borderRadius: 8, height: 8 }}>
                  <div style={{ background: C.primary, width: `${uploadProgress}%`, height: 8, borderRadius: 8, transition: 'width 0.3s' }} />
                </div>
              </div>
            )}

            {/* Los 3 botones de acción */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
              {/* Botón 1: Análisis rápido → Flujo Secuencial */}
              <div style={{ border: '2px solid #3B82F6', borderRadius: 12, padding: 20 }}>
                <div style={{ fontSize: 24, marginBottom: 8 }}>🔍</div>
                <div style={{ fontWeight: 700, color: C.primary, marginBottom: 6 }}>Análisis rápido</div>
                <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 16, lineHeight: 1.5 }}>
                  Diagnóstico preliminar y ejecutivo. Muestra estado estimado, puntajes referenciales y recomendaciones rápidas.
                </div>
                <div style={{ fontSize: 11, color: '#6B7280', marginBottom: 12 }}>⚡ Resultado en ~30s</div>
                <button
                  onClick={() => handleUploadYAnalizar('completo')}
                  disabled={uploading || analyzing}
                  style={{ width: '100%', background: '#3B82F6', color: '#fff', border: 'none', padding: '10px 0', borderRadius: 8, fontWeight: 700, fontSize: 13, cursor: 'pointer', opacity: (uploading || analyzing) ? 0.6 : 1 }}>
                  {analyzing ? '⏳ Analizando...' : 'Generar diagnóstico rápido'}
                </button>
              </div>

              {/* Botón 2: Acciones de mejora → Flujo Red */}
              <div style={{ border: '2px solid #EF4444', borderRadius: 12, padding: 20 }}>
                <div style={{ fontSize: 24, marginBottom: 8 }}>⚔️</div>
                <div style={{ fontWeight: 700, color: C.primary, marginBottom: 6 }}>Acciones de mejora</div>
                <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 16, lineHeight: 1.5 }}>
                  Feedback accionable: qué corregir, en qué sección, con prioridad y recomendaciones puntuales para el alumno.
                </div>
                <div style={{ fontSize: 11, color: '#6B7280', marginBottom: 12 }}>🛠️ Plan accionable ~40s</div>
                <button
                  onClick={() => handleUploadYAnalizar('debate')}
                  disabled={uploading || analyzing}
                  style={{ width: '100%', background: '#EF4444', color: '#fff', border: 'none', padding: '10px 0', borderRadius: 8, fontWeight: 700, fontSize: 13, cursor: 'pointer', opacity: (uploading || analyzing) ? 0.6 : 1 }}>
                  {analyzing ? '⏳ Generando...' : 'Generar acciones'}
                </button>
              </div>

              {/* Botón 3: Veredicto → Flujo Jerárquico */}
              <div style={{ border: '2px solid #8B5CF6', borderRadius: 12, padding: 20 }}>
                <div style={{ fontSize: 24, marginBottom: 8 }}>🏛️</div>
                <div style={{ fontWeight: 700, color: C.primary, marginBottom: 6 }}>Obtener veredicto</div>
                <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 16, lineHeight: 1.5 }}>
                  Evaluación formal con rúbrica completa ítem por ítem, puntaje oficial, dictamen y reporte descargable.
                </div>
                <div style={{ fontSize: 11, color: '#6B7280', marginBottom: 12 }}>📊 Resultado en ~60s</div>
                <button
                  onClick={() => handleUploadYAnalizar('veredicto')}
                  disabled={uploading || analyzing}
                  style={{ width: '100%', background: '#8B5CF6', color: '#fff', border: 'none', padding: '10px 0', borderRadius: 8, fontWeight: 700, fontSize: 13, cursor: 'pointer', opacity: (uploading || analyzing) ? 0.6 : 1 }}>
                  {analyzing ? '⏳ Generando...' : 'Obtener veredicto'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── TAB RESULTADO ── */}
        {tab === 'resultado' && (
          <div style={{ background: '#fff', borderRadius: 16, padding: 32, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>

            {analyzing ? (
              <div style={{ textAlign: 'center', padding: 48 }}>
                <div style={{ fontSize: 52, marginBottom: 16 }}>🤖</div>
                <h3 style={{ color: C.primary, marginBottom: 8 }}>
                  {tipoAnalisis === 'veredicto' ? 'Generando dictamen del comité...' : tipoAnalisis === 'debate_red' ? 'Generando acciones de mejora...' : 'Generando diagnóstico preliminar...'}
                </h3>
                <p style={{ color: '#666', fontSize: 13 }}>
                  Los agentes están procesando tu documento. El diagnóstico rápido es referencial; el veredicto oficial se obtiene en el flujo jerárquico.
                </p>
                <div style={{ marginTop: 24, display: 'inline-block', background: '#FEF3C7', borderRadius: 8, padding: '10px 20px', color: '#92400E', fontSize: 13 }}>
                  ⏳ Verificando cada 5 segundos...
                </div>
              </div>

            ) : analisis ? (
              <>
                {/* Cabecera */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24, gap: 12, flexWrap: 'wrap' }}>
                  <div>
                    <h2 style={{ color: C.primary, marginBottom: 4 }}>
                      {tipoAnalisis === 'veredicto' ? '🏛️ Dictamen del Comité Evaluador' : tipoAnalisis === 'debate_red' ? '🛠️ Acciones de mejora' : '⚡ Diagnóstico preliminar'}
                    </h2>
                    <p style={{ color: '#666', fontSize: 13, margin: 0 }}>{selectedThesis?.titulo}</p>
                  </div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {['pendiente_validacion','aprobado','aprobado_con_cambios','rechazado'].includes(analisis.estado) && selectedThesis && (
                      <button onClick={async () => {
                        try {
                          const token = localStorage.getItem('token')
                          const res = await fetch(`/api/thesis/${selectedThesis.id}/report`, {
                            headers: { 'Authorization': `Bearer ${token}` }
                          })
                          if (!res.ok) { alert('Error al descargar: ' + res.status); return }
                          const blob = await res.blob()
                          const url = URL.createObjectURL(blob)
                          const a = document.createElement('a')
                          a.href = url
                          a.download = `reporte_tesis_${selectedThesis.id}.pdf`
                          document.body.appendChild(a)
                          a.click()
                          document.body.removeChild(a)
                          URL.revokeObjectURL(url)
                        } catch(e) { alert('Error al descargar: ' + e.message) }
                      }}
                        style={{ background: C.success, color: '#fff', border: 'none', padding: '9px 16px', borderRadius: 8, cursor: 'pointer', fontWeight: 600, fontSize: 12 }}>
                        ⬇️ Descargar reporte
                      </button>
                    )}
                  </div>
                </div>

                {/* Métricas */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 10, marginBottom: 28 }}>
                  {[
                    ['📄', 'Páginas', r.metadata_pdf?.total_paginas ?? '—'],
                    ['📝', 'Palabras', r.metadata_pdf?.total_palabras?.toLocaleString() ?? '—'],
                    ['⚡', 'Tiempo', r.latencia_total_ms ? `${(r.latencia_total_ms / 1000).toFixed(1)}s` : '—'],
                    ['🔒', 'Estado', analisis.estado],
                  ].map(([icon, label, val]) => (
                    <div key={label} style={{ background: '#F8FAFC', borderRadius: 10, padding: '12px 14px', textAlign: 'center' }}>
                      <div style={{ fontSize: 20 }}>{icon}</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: C.primary }}>{val}</div>
                      <div style={{ fontSize: 11, color: '#6B7280' }}>{label}</div>
                    </div>
                  ))}
                </div>

                {/* ── ANÁLISIS COMPLETO: muestra la respuesta del Secuencial ── */}
                {tipoAnalisis === 'analisis_completo' && (
                  <>
                    <h3 style={{ color: C.primary, fontSize: 15, marginBottom: 14 }}>Diagnóstico rápido</h3>

                    {/* El flujo Secuencial devuelve el resultado consolidado del Conciliador.
                        Lo mostramos como tarjeta única del conciliador con el texto completo. */}
                    {/* ── Agente Orquestador: diseño detectado + rúbrica ── */}
                {disenoInfo && (
                  <div style={{ border: '2px solid #7C3AED', borderRadius: 12, overflow: 'hidden', marginBottom: 16 }}>
                    <div style={{ background: '#F5F3FF', padding: '12px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span style={{ fontSize: 22 }}>🤖</span>
                        <div>
                          <div style={{ fontWeight: 700, color: '#5B21B6', fontSize: 14 }}>Agente Orquestador — Diseño de Investigación Detectado</div>
                          <div style={{ fontSize: 11, color: '#7C3AED' }}>Confianza: {disenoInfo.nivel_confianza} • {disenoInfo.metodo === 'keywords' ? 'Detección por palabras clave' : 'IA'}</div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        {[
                          [disenoInfo.enfoque, '#6D28D9', '#EDE9FE'],
                          [disenoInfo.diseno?.replace('_', '-'), '#1D4ED8', '#DBEAFE'],
                          [disenoInfo.rama, '#065F46', '#D1FAE5'],
                        ].map(([label, color, bg]) => label && (
                          <span key={label} style={{ background: bg, color, fontWeight: 700, fontSize: 12, padding: '3px 10px', borderRadius: 20 }}>{label.toUpperCase()}</span>
                        ))}
                      </div>
                    </div>
                    {disenoInfo.justificacion && (
                      <div style={{ padding: '10px 20px', background: '#FAFAFA', fontSize: 13, color: '#374151', fontStyle: 'italic' }}>
                        💡 {disenoInfo.justificacion}
                      </div>
                    )}
                    {rubrica && (
                      <div style={{ padding: '10px 20px', background: '#F5F3FF', borderTop: '1px solid #EDE9FE', display: 'flex', gap: 20 }}>
                        <span style={{ fontSize: 13, color: '#5B21B6' }}>📋 Rúbrica específica generada:</span>
                        <strong style={{ color: '#5B21B6' }}>{rubrica.total_items} ítems</strong>
                        <span style={{ color: '#7C3AED' }}>/ {rubrica.total_puntos} puntos máximos</span>
                        <span style={{ color: '#9CA3AF', fontSize: 12 }}>Los ítems granulares (0.25/0.5/1.0 pts) guían a cada agente</span>
                      </div>
                    )}
                  </div>
                )}

                                {secuencial.exito ? (() => {
                      const txt = secuencial.texto_crudo || ''
                      const secMet  = _extraerSeccion(txt, 'metodol')
                      const secTec  = _extraerSeccion(txt, 'tecni')
                      const secLin  = _extraerSeccion(txt, 'lingu')
                      const secDict = _extraerDictamen(txt)
                      return (
                        <>
                          <QuickAnalysisCard texto={txt} latencia_ms={secuencial.latencia_ms} disenoInfo={disenoInfo} agentes={agentes} />
                          {/* Detalle por agentes oculto por defecto para mantener el análisis rápido como diagnóstico ejecutivo */}
                          <div style={{ display: 'none' }}>
                          <div style={{ border: '2px solid #3B82F6', borderRadius: 12, overflow: 'hidden', marginBottom: 12 }}>
                            <div style={{ background: '#EFF6FF', padding: '12px 20px', display: 'flex', gap: 10, alignItems: 'center' }}>
                              <span style={{ fontSize: 20 }}>📐</span>
                              <span style={{ fontWeight: 700, color: '#1D4ED8', fontSize: 14 }}>Agente Metodológico</span>
                            </div>
                            <div style={{ padding: '14px 20px', fontSize: 13, color: '#374151', lineHeight: 1.8, whiteSpace: 'pre-wrap', background: '#F8FAFC' }}>
                              {secMet || '(Sin hallazgos metodológicos)'}
                            </div>
                          </div>
                          <div style={{ border: '2px solid #8B5CF6', borderRadius: 12, overflow: 'hidden', marginBottom: 12 }}>
                            <div style={{ background: '#F5F3FF', padding: '12px 20px', display: 'flex', gap: 10, alignItems: 'center' }}>
                              <span style={{ fontSize: 20 }}>⚙️</span>
                              <span style={{ fontWeight: 700, color: '#6D28D9', fontSize: 14 }}>Agente Técnico</span>
                            </div>
                            <div style={{ padding: '14px 20px', fontSize: 13, color: '#374151', lineHeight: 1.8, whiteSpace: 'pre-wrap', background: '#F8FAFC' }}>
                              {secTec || '(Sin hallazgos técnicos)'}
                            </div>
                          </div>
                          <div style={{ border: '2px solid #10B981', borderRadius: 12, overflow: 'hidden', marginBottom: 12 }}>
                            <div style={{ background: '#ECFDF5', padding: '12px 20px', display: 'flex', gap: 10, alignItems: 'center' }}>
                              <span style={{ fontSize: 20 }}>📝</span>
                              <span style={{ fontWeight: 700, color: '#065F46', fontSize: 14 }}>Agente Lingüístico</span>
                            </div>
                            <div style={{ padding: '14px 20px', fontSize: 13, color: '#374151', lineHeight: 1.8, whiteSpace: 'pre-wrap', background: '#F8FAFC' }}>
                              {secLin || '(Sin hallazgos lingüísticos)'}
                            </div>
                          </div>
                          {secDict && (
                            <div style={{ border: '2px solid #F59E0B', borderRadius: 12, overflow: 'hidden', marginBottom: 12 }}>
                              <div style={{ background: '#FFFBEB', padding: '12px 20px', display: 'flex', gap: 10, alignItems: 'center' }}>
                                <span style={{ fontSize: 20 }}>⚖️</span>
                                <span style={{ fontWeight: 700, color: '#92400E', fontSize: 14 }}>Dictamen Final Consolidado</span>
                              </div>
                              <div style={{ padding: '14px 20px', fontSize: 13, color: '#374151', lineHeight: 1.8, whiteSpace: 'pre-wrap', background: '#FFFDF0' }}>
                                {secDict}
                              </div>
                            </div>
                          )}
                          <details style={{ border: '1px solid #E5E7EB', borderRadius: 8 }}>
                            <summary style={{ padding: '8px 14px', fontSize: 12, cursor: 'pointer', color: '#6B7280', fontWeight: 600 }}>📄 Ver respuesta completa</summary>
                            <div style={{ padding: '12px 16px', fontSize: 12, color: '#374151', lineHeight: 1.7, whiteSpace: 'pre-wrap', maxHeight: 400, overflowY: 'auto', background: '#F8FAFC' }}>
                              {txt}
                            </div>
                          </details>
                          </div>
                        </>
                      )
                    })() : (
                      <div style={{ background: '#FEE2E2', borderRadius: 10, padding: 16, color: '#7F1D1D', fontSize: 13 }}>
                        ❌ {secuencial.error || 'Error en el análisis'}
                      </div>
                    )}

                    {/* Botón para ir a veredicto */}
                    {analisis.estado === 'pendiente_validacion' && (
                      <div style={{ marginTop: 20, display: 'flex', gap: 12 }}>
                        <button onClick={() => setTab('upload')}
                          style={{ background: '#8B5CF6', color: '#fff', border: 'none', padding: '10px 20px', borderRadius: 8, fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>
                          🏛️ Quiero el veredicto final
                        </button>
                      </div>
                    )}
                  </>
                )}

                {/* ── VEREDICTO: muestra resultado del Jerárquico ── */}
                {tipoAnalisis === 'veredicto' && (
                  <>
                    <h3 style={{ color: C.primary, fontSize: 15, marginBottom: 14 }}>Dictamen del comité</h3>
                    <VeredictoCard
                      respuesta={jerarquico.texto_crudo}
                      error={jerarquico.error}
                      latencia_ms={jerarquico.latencia_ms}
                      agentes={agentes}
                      rubricaIds={r.rubricas_ids}
                      rubricasDetalle={r.rubricas_detalle}
                      disenoInfo={r.diseno_info}
                      metricasOficiales={r.metricas_oficiales}
                      veredictoOficial={r.veredicto_oficial}
                    />
                  </>
                )}

                {/* ── DEBATE RED: HU-08 visualización por rondas (Sprint 2 / EP-02) ── */}
                {tipoAnalisis === 'debate_red' && (
                  <>
                    <h3 style={{ color: C.primary, fontSize: 15, marginBottom: 14 }}>🛠️ Acciones de mejora — Feedback accionable</h3>
                    {red.error ? (
                      <div style={{ background: '#FEE2E2', border: '1px solid #FCA5A5', borderRadius: 10, padding: 16, color: '#7F1D1D', fontSize: 13 }}>
                        <strong>Error en el debate:</strong> {red.error}
                        {red.error.includes('no configurado') && (
                          <div style={{ marginTop: 8, fontSize: 12, color: '#991B1B' }}>
                            👉 Agrega <code>LANGFLOW_FLOW_ID_RED=tu-uuid-aqui</code> en <code>backend/.env</code> y reinicia el backend.
                          </div>
                        )}
                      </div>
                    ) : red.texto_crudo ? (() => {
                      // Parsear rondas del debate del texto crudo
                      const texto = red.texto_crudo
                      const rondas = []
                      const patronRonda = /ronda\s*(\d+)|iteraci[oó]n\s*(\d+)|turno\s*(\d+)/gi
                      let partes = texto.split(patronRonda).filter(Boolean)

                      // Intentar extraer secciones por agente
                      const secMetod = texto.match(/metodol[oó]gic[oa][:\s]*([\s\S]*?)(?=t[eé]cnic|lingü|consenso|veredicto|$)/i)
                      const secTecni = texto.match(/t[eé]cnic[oa][:\s]*([\s\S]*?)(?=metodol|lingü|consenso|veredicto|$)/i)
                      const secConse = texto.match(/(?:consenso|veredicto)[:\s]*([\s\S]*?)$/i)

                      // Extraer Rigor Score si existe en el texto
                      const rigorMatch = texto.match(/rigor.?score[:\s]*([0-9.]+)/i)
                      const rigorScore = rigorMatch ? parseFloat(rigorMatch[1]) : null
                      const rigorColor = rigorScore >= 0.80 ? '#065F46' : rigorScore >= 0.60 ? '#92400E' : '#7F1D1D'
                      const rigorBg    = rigorScore >= 0.80 ? '#D1FAE5' : rigorScore >= 0.60 ? '#FEF3C7' : '#FEE2E2'

                      // Alertas HU-09 — detectar vacíos y contradicciones
                      const alertasAlta = (texto.match(/falta|ausencia|no presenta|no se evidencia|contradicción/gi) || []).length
                      const alertasMedia = (texto.match(/se recomienda|observaci[oó]n|inconsistencia|revisar/gi) || []).length

                      return (
                        <div>
                          {/* Métricas */}
                          <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
                            <span style={{ background: '#FEF3C7', borderRadius: 8, padding: '6px 14px', fontSize: 12, color: '#92400E' }}>
                              ⏱️ {red.latencia_ms ? `${(red.latencia_ms/1000).toFixed(1)}s` : '—'}
                            </span>
                            <span style={{ background: '#EDE9FE', borderRadius: 8, padding: '6px 14px', fontSize: 12, color: '#5B21B6' }}>
                              🔁 Máx. 3 rondas
                            </span>
                            {rigorScore !== null && (
                              <span style={{ background: rigorBg, borderRadius: 8, padding: '6px 14px', fontSize: 12, fontWeight: 700, color: rigorColor }}>
                                📊 Rigor Score: {rigorScore.toFixed(2)}
                              </span>
                            )}
                          </div>

                          {/* HU-09: Alertas visuales */}
                          {(alertasAlta > 0 || alertasMedia > 0) && (
                            <div style={{ marginBottom: 16 }}>
                              <div style={{ fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 6 }}>
                                🚨 Alertas detectadas
                              </div>
                              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                {alertasAlta > 0 && (
                                  <span style={{ background: '#FEE2E2', color: '#7F1D1D', borderRadius: 6, padding: '4px 10px', fontSize: 12, fontWeight: 600 }}>
                                    🔴 {alertasAlta} vacío{alertasAlta > 1 ? 's' : ''} crítico{alertasAlta > 1 ? 's' : ''}
                                  </span>
                                )}
                                {alertasMedia > 0 && (
                                  <span style={{ background: '#FEF3C7', color: '#92400E', borderRadius: 6, padding: '4px 10px', fontSize: 12, fontWeight: 600 }}>
                                    🟡 {alertasMedia} observaci{alertasMedia > 1 ? 'ones' : 'ón'}
                                  </span>
                                )}
                              </div>
                            </div>
                          )}

                          {/* Intervenciones de cada agente */}
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 16 }}>
                            {secMetod && (
                              <div style={{ border: '1.5px solid #3B82F6', borderRadius: 10, overflow: 'hidden' }}>
                                <div style={{ background: '#EFF6FF', padding: '8px 14px', fontWeight: 700, fontSize: 13, color: '#1D4ED8' }}>
                                  📐 Agente Metodológico
                                </div>
                                <div style={{ padding: '10px 14px', fontSize: 13, color: '#374151', lineHeight: 1.7, maxHeight: 180, overflowY: 'auto' }}>
                                  {secMetod[1]?.trim().slice(0, 600) || ''}
                                </div>
                              </div>
                            )}
                            {secTecni && (
                              <div style={{ border: '1.5px solid #8B5CF6', borderRadius: 10, overflow: 'hidden' }}>
                                <div style={{ background: '#F5F3FF', padding: '8px 14px', fontWeight: 700, fontSize: 13, color: '#6D28D9' }}>
                                  ⚙️ Agente Técnico
                                </div>
                                <div style={{ padding: '10px 14px', fontSize: 13, color: '#374151', lineHeight: 1.7, maxHeight: 180, overflowY: 'auto' }}>
                                  {secTecni[1]?.trim().slice(0, 600) || ''}
                                </div>
                              </div>
                            )}
                            {secConse && (
                              <div style={{ border: '2px solid #10B981', borderRadius: 10, overflow: 'hidden' }}>
                                <div style={{ background: '#D1FAE5', padding: '8px 14px', fontWeight: 700, fontSize: 13, color: '#065F46' }}>
                                  ⚖️ Agente de Consenso — Veredicto
                                </div>
                                <div style={{ padding: '10px 14px', fontSize: 13, color: '#374151', lineHeight: 1.7, maxHeight: 200, overflowY: 'auto' }}>
                                  {secConse[1]?.trim().slice(0, 800) || ''}
                                </div>
                              </div>
                            )}
                          </div>

                          {/* Texto completo colapsable */}
                          <details style={{ border: '1px solid #E5E7EB', borderRadius: 8 }}>
                            <summary style={{ padding: '8px 14px', fontSize: 12, cursor: 'pointer', color: '#6B7280', fontWeight: 600 }}>
                              📄 Ver debate completo
                            </summary>
                            <div style={{ padding: '10px 14px', fontSize: 12, color: '#374151', lineHeight: 1.7, whiteSpace: 'pre-wrap', maxHeight: 350, overflowY: 'auto' }}>
                              {texto}
                            </div>
                          </details>
                        </div>
                      )
                    })() : (
                      <div style={{ color: '#6B7280', fontSize: 13 }}>Sin resultado de debate disponible.</div>
                    )}
                  </>
                )}

                {/* ── HU-12: Lista de errores APA — visible en análisis completo ── */}
                {(tipoAnalisis === 'analisis_completo' || tipoAnalisis === 'flujo_jerarquico') && (() => {
                  const rawT = secuencial?.texto_crudo || jerarquico?.texto_crudo || ''; const textoLing = _extraerSeccion(rawT, 'lingu') || rawT
                  if (!textoLing) return null
                  // Solo extraer líneas numeradas del bloque LINGUISTICO
                  const erroresApa = []
                  const lineas = textoLing.split('\n')
                  lineas.forEach(l => {
                    const lt = l.trim()
                    const l2 = lt.toLowerCase()
                    const esLinea = /^\d+\./.test(lt) || lt.startsWith('-') || lt.startsWith('•')
                    const tieneKw = l2.includes('apa') || l2.includes('cit') || l2.includes('referencia') || l2.includes('doi') || l2.includes('falta') || l2.includes('error')
                    if ((esLinea || tieneKw) && lt.length > 15) erroresApa.push(lt)
                  })
                  if (erroresApa.length === 0) return null
                  return (
                    <div style={{ marginTop: 20, border: '1.5px solid #F59E0B', borderRadius: 10, overflow: 'hidden' }}>
                      <div style={{ background: '#FEF3C7', padding: '10px 16px', fontWeight: 700, fontSize: 13, color: '#92400E', display: 'flex', justifyContent: 'space-between' }}>
                        <span>📋 Errores de Citación APA 7 detectados</span>
                        <span style={{ fontWeight: 400, fontSize: 11 }}>{erroresApa.length} encontrados</span>
                      </div>
                      <div style={{ padding: 14 }}>
                        {erroresApa.slice(0, 8).map((e, i) => (
                          <div key={i} style={{ display: 'flex', gap: 10, padding: '6px 0', borderBottom: i < erroresApa.length - 1 ? '1px solid #FEF3C7' : 'none', fontSize: 13, color: '#374151' }}>
                            <span style={{ color: '#F59E0B', flexShrink: 0 }}>⚠</span>
                            <span>{e.slice(0, 150)}</span>
                          </div>
                        ))}
                        {erroresApa.length > 8 && (
                          <div style={{ fontSize: 11, color: '#9CA3AF', marginTop: 6 }}>
                            +{erroresApa.length - 8} más en el reporte completo
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })()}

                {/* ── HU-10: Filtro de debate por sección ── */}
                {tipoAnalisis === 'debate_red' && red.texto_crudo && (() => {
                  const secciones = ['Introducción','Marco Teórico','Metodología','Hipótesis','Conclusiones','Resultados']
                  const [seccionFiltro, setSeccionFiltro] = window._hu10State || [null, () => {}]
                  // usamos un pequeño hack inline para state sin hook extra
                  return (
                    <div style={{ marginTop: 20, border: '1.5px solid #6366F1', borderRadius: 10, overflow: 'hidden' }}>
                      <div style={{ background: '#EEF2FF', padding: '10px 16px', fontWeight: 700, fontSize: 13, color: '#4338CA' }}>
                        🔍 HU-10 — Filtrar debate por sección
                      </div>
                      <div style={{ padding: '12px 16px' }}>
                        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
                          {secciones.map(sec => {
                            const activa = red.texto_crudo.toLowerCase().includes(sec.toLowerCase())
                            return (
                              <button key={sec}
                                onClick={() => window._hu10FiltroActivo = window._hu10FiltroActivo === sec ? null : sec}
                                style={{ padding: '5px 12px', borderRadius: 20, fontSize: 12, border: '1px solid #6366F1',
                                  background: !activa ? '#F3F4F6' : (window._hu10FiltroActivo === sec ? '#6366F1' : '#EEF2FF'),
                                  color: !activa ? '#9CA3AF' : (window._hu10FiltroActivo === sec ? '#fff' : '#4338CA'),
                                  cursor: activa ? 'pointer' : 'not-allowed' }}>
                                {sec}
                              </button>
                            )
                          })}
                        </div>
                        {window._hu10FiltroActivo && (() => {
                          const re = new RegExp(`(${window._hu10FiltroActivo}[\s\S]{0,600})`, 'i')
                          const match = red.texto_crudo.match(re)
                          return match ? (
                            <div style={{ background: '#F8FAFC', border: '1px solid #E5E7EB', borderRadius: 8, padding: 12, fontSize: 13, color: '#374151', lineHeight: 1.7 }}>
                              <strong style={{ color: '#4338CA' }}>Argumentos sobre: {window._hu10FiltroActivo}</strong>
                              <p style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>{match[1].slice(0, 600)}</p>
                            </div>
                          ) : (
                            <div style={{ fontSize: 13, color: '#9CA3AF' }}>No se encontraron argumentos sobre "{window._hu10FiltroActivo}" en este debate.</div>
                          )
                        })()}
                      </div>
                    </div>
                  )
                })()}

                {/* ── HU-13: Gaps de conocimiento ── */}
                {(tipoAnalisis === 'debate_red' || tipoAnalisis === 'analisis_completo') && (() => {
                  const textoBase = red.texto_crudo || secuencial?.texto_crudo || ''
                  if (!textoBase) return null
                  const gapPatterns = [
                    { re: /no se evidencia|ausencia de|no presenta|carece de/gi, tipo: 'Gap metodológico', color: '#7F1D1D', bg: '#FEE2E2' },
                    { re: /falta de fundamento|sin sustento teórico|no cita|marco teórico insuficiente/gi, tipo: 'Gap teórico', color: '#92400E', bg: '#FEF3C7' },
                    { re: /no se valida|sin validación|falta validar|instrumento no validado/gi, tipo: 'Gap empírico', color: '#1E40AF', bg: '#DBEAFE' },
                  ]
                  const gaps = []
                  gapPatterns.forEach(({ re, tipo, color, bg }) => {
                    const matches = textoBase.match(re) || []
                    if (matches.length > 0) {
                      const idx = textoBase.search(re)
                      const fragmento = textoBase.slice(Math.max(0, idx - 30), idx + 150).replace(/\n/g, ' ').trim()
                      gaps.push({ tipo, color, bg, count: matches.length, fragmento })
                    }
                  })
                  if (gaps.length === 0) return null
                  return (
                    <div style={{ marginTop: 20, border: '1.5px solid #7C3AED', borderRadius: 10, overflow: 'hidden' }}>
                      <div style={{ background: '#F5F3FF', padding: '10px 16px', fontWeight: 700, fontSize: 13, color: '#5B21B6' }}>
                        🧩 HU-13 — Gaps de conocimiento detectados ({gaps.length} tipo{gaps.length > 1 ? 's' : ''})
                      </div>
                      <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {gaps.map((g, i) => (
                          <div key={i} style={{ background: g.bg, borderRadius: 8, padding: '10px 14px' }}>
                            <div style={{ fontWeight: 700, fontSize: 12, color: g.color, marginBottom: 4 }}>
                              {g.tipo} — {g.count} instancia{g.count > 1 ? 's' : ''}
                            </div>
                            <div style={{ fontSize: 12, color: '#374151', lineHeight: 1.6 }}>
                              "...{g.fragmento}..."
                            </div>
                            <div style={{ fontSize: 11, color: g.color, marginTop: 6, fontStyle: 'italic' }}>
                              💡 Sugerencia: Revisar y reforzar esta sección con fuentes académicas adicionales.
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                })()}

                {/* ── Human-Loop: dictamen final del docente ── */}
                <HumanLoopCard humanLoop={humanLoop} selectedThesis={selectedThesis} />

                {!r.exito_general && (
                  <div style={{ background: '#FEF3C7', borderRadius: 8, padding: '12px 16px', marginTop: 16, fontSize: 13, color: '#92400E' }}>
                    ⚠️ El análisis no pudo completarse. Verifica que Langflow esté corriendo y que la LANGFLOW_API_KEY esté configurada en backend/.env.
                  </div>
                )}
              </>

            ) : (
              <div style={{ textAlign: 'center', padding: 48, color: '#6B7280' }}>
                <div style={{ fontSize: 48 }}>📭</div>
                <p>Sube una tesis o selecciona una del historial para ver el resultado.</p>
              </div>
            )}
          </div>
        )}

        {/* ── TAB HISTORIAL ── */}
        {tab === 'historial' && (
          <div style={{ background: '#fff', borderRadius: 16, padding: 32, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
            <h2 style={{ color: C.primary, marginBottom: 20 }}>📋 Historial de Tesis</h2>
            {tesisList.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 48, color: '#9CA3AF' }}>Aún no has subido ninguna tesis.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {tesisList.map(t => (
                  <div key={t.id} style={{ border: '1px solid #E5E7EB', borderRadius: 10, padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                      <div style={{ fontWeight: 600, color: '#1F2937' }}>{t.titulo}</div>
                      <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 4 }}>
                        {t.filename} · {new Date(t.created_at).toLocaleDateString('es-PE')}
                        {t.latencia_ms && ` · ${(t.latencia_ms / 1000).toFixed(1)}s`}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      {badge(t.estado)}
                      <button onClick={() => verResultado(t)}
                        style={{ background: C.primary, color: '#fff', border: 'none', padding: '6px 14px', borderRadius: 6, cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
                        Ver resultado
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
