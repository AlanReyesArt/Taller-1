import { useState, useEffect, useRef } from 'react'
import { getAllThesisMaestro, getResultMaestro, validarTesis } from '../api'
import { useAuth } from '../AuthContext'
import { useNavigate } from 'react-router-dom'

const C = { primary: '#1F3864', success: '#065F46', warning: '#92400E', danger: '#7F1D1D', accent: '#4F46E5' }

const badge = (estado) => {
  const map = {
    subido:               { bg: '#DBEAFE', color: '#1E40AF', label: '📄 Subido' },
    en_analisis:          { bg: '#FEF3C7', color: '#92400E', label: '⏳ En análisis' },
    pendiente_validacion: { bg: '#FEF9C3', color: '#854D0E', label: '🔔 Pendiente revisión' },
    aprobado:             { bg: '#D1FAE5', color: '#065F46', label: '✅ Aprobado' },
    aprobado_con_cambios: { bg: '#FEF9C3', color: '#854D0E', label: '✏️ Aprobado con cambios' },
    rechazado:            { bg: '#FEE2E2', color: '#7F1D1D', label: '❌ Rechazado' },
    error:                { bg: '#FEE2E2', color: '#7F1D1D', label: '⚠️ Error' },
  }
  const s = map[estado] || { bg: '#F3F4F6', color: '#374151', label: estado }
  return <span style={{ background: s.bg, color: s.color, padding: '3px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600 }}>{s.label}</span>
}

// Extrae secciones del texto consolidado usando etiquetas ===METODOLOGICO===, ===TECNICO===, etc.
function extraerSeccion(texto, keyword) {
  if (!texto) return null

  const tagMap = {
    metodol: 'METODOLOGICO',
    tecni: 'TECNICO',
    tecnic: 'TECNICO',
    lingu: 'LINGUISTICO',
    lingui: 'LINGUISTICO',
    redac: 'LINGUISTICO',
    dictam: 'DICTAMEN',
  }

  const key = keyword.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z]/g, '')
  const tag = Object.entries(tagMap).find(([k]) => key.includes(k))?.[1]

  if (tag) {
    const tags = []
    const reTags = /={2,}\s*(METODOLOGICO|TECNICO|LINGUISTICO|DICTAMEN)\s*={2,}/gi
    let m
    while ((m = reTags.exec(texto)) !== null) {
      tags.push({ tag: m[1].toUpperCase(), start: m.index, end: m.index + m[0].length })
    }

    const current = tags.find(t => t.tag === tag)
    if (current) {
      const next = tags.find(t => t.start > current.start)
      return texto.slice(current.end, next ? next.start : texto.length).trim()
    }
  }

  // Fallback por palabras clave, pero cortando si aparece otra etiqueta interna.
  const lower = texto.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
  const idx = lower.indexOf(key)
  if (idx === -1) return null
  const rest = texto.slice(idx)
  const next = rest.search(/={2,}\s*(METODOLOGICO|TECNICO|LINGUISTICO|DICTAMEN)\s*={2,}/i)
  return rest.slice(0, next > 0 ? next : Math.min(1200, rest.length)).trim()
}

function limpiarTextoAgente(texto) {
  if (!texto) return ''
  return texto
    .replace(/={2,}\s*(METODOLOGICO|TECNICO|LINGUISTICO|DICTAMEN)\s*={2,}/gi, '')
    .replace(/^\s*(METODOLOGICO|TECNICO|LINGUISTICO|DICTAMEN)\s*={2,}\s*/gi, '')
    .replace(/^\s*=+\s*$/gm, '')
    .replace(/\*\*/g, '')
    .replace(/---+/g, '')
    .trim()
}

function extraerLineasBloque(texto, titulo) {
  if (!texto) return []
  const re = new RegExp(String.raw`(^|\n)\s*${titulo}\s*:?\s*([\s\S]*?)(?=\n\s*(Cumplidos|No cumplidos|Fortalezas|Debilidades|Recomendaciones|Puntaje|Rigor|Veredicto|Resumen|Auditoría|Justificación|Plan de mejora)\s*:?|$)`, 'i')
  const m = texto.match(re)
  if (!m) return []
  return m[2]
    .split('\n')
    .map(x => x.replace(/^\s*[-•]\s*/, '').replace(/^\s*\d+\.\s*/, '').trim())
    .filter(Boolean)
    .filter(x => !/^(ninguno|ninguna|no reportado)$/i.test(x))
    .slice(0, 8)
}


function extraerHallazgos(texto) {
  const clean = limpiarTextoAgente(texto)
  const bloque = clean.match(/Hallazgos[^:]*:\s*([\s\S]*?)(?=\n\s*Puntaje|\n\s*Cumplidos|\n\s*No cumplidos|$)/i)
  const base = bloque ? bloque[1] : clean
  const numbered = [...base.matchAll(/^\s*\d+\.\s*(.+)$/gm)].map(m => m[1].trim())
  if (numbered.length) return numbered.slice(0, 8)
  return base
    .split('\n')
    .map(x => x.replace(/^\s*[-•]\s*/, '').trim())
    .filter(x => x.length > 20)
    .slice(0, 6)
}

function DetalleEvaluacion({ texto, color }) {
  const clean = limpiarTextoAgente(texto)
  const puntaje = extraerPuntaje(clean)
  const hallazgos = extraerHallazgos(clean)
  const cumplidos = extraerLineasBloque(clean, 'Cumplidos')
  const noCumplidos = extraerLineasBloque(clean, 'No cumplidos')

  const box = (title, items, bg, col, icon) => items.length > 0 && (
    <div style={{ background: bg, border: `1px solid ${col}22`, borderRadius: 10, padding: '10px 12px' }}>
      <div style={{ fontWeight: 800, color: col, fontSize: 12, marginBottom: 8 }}>{icon} {title}</div>
      <ul style={{ margin: 0, paddingLeft: 18, color: '#374151', lineHeight: 1.55 }}>
        {items.map((it, i) => <li key={i} style={{ marginBottom: 5 }}>{it}</li>)}
      </ul>
    </div>
  )

  return (
    <div style={{ marginTop: 10, background: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: 12, padding: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <strong style={{ color: C.primary, fontSize: 13 }}>Evaluación completa</strong>
        <span style={{ background: '#F8FAFC', color, border: `1px solid ${color}40`, borderRadius: 999, padding: '4px 10px', fontSize: 11, fontWeight: 800 }}>
          Puntaje: {puntaje}
        </span>
      </div>
      <div style={{ display: 'grid', gap: 10, fontSize: 12 }}>
        {box('Hallazgos principales', hallazgos, '#F8FAFC', color, '🔎')}
        {box('Criterios cumplidos', cumplidos, '#ECFDF5', '#047857', '✅')}
        {box('Criterios no cumplidos', noCumplidos, '#FEF2F2', '#B91C1C', '❌')}
        {!hallazgos.length && !cumplidos.length && !noCumplidos.length && (
          <div style={{ color: '#374151', lineHeight: 1.65, maxHeight: 220, overflowY: 'auto', whiteSpace: 'pre-wrap' }}>
            {clean}
          </div>
        )}
      </div>
    </div>
  )
}

// Tarjeta de reporte de un agente
function ReporteAgente({ titulo, icono, texto, color }) {
  const [expandido, setExpandido] = useState(false)
  if (!texto) return null
  const preview = texto.slice(0, 200) + (texto.length > 200 ? '...' : '')
  return (
    <div style={{ border: `1.5px solid ${color}30`, borderRadius: 10, overflow: 'hidden', marginBottom: 10 }}>
      <div style={{ background: `${color}15`, padding: '10px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 700, color: C.primary, fontSize: 13 }}>{icono} {titulo}</span>
        <button onClick={() => setExpandido(e => !e)}
          style={{ background: 'none', border: 'none', color: color, cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
          {expandido ? '▲ ver menos' : '▼ ver más'}
        </button>
      </div>
      <div style={{ padding: '12px 16px', background: '#fff', fontSize: 13, color: '#374151', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
        {expandido ? texto : preview}
      </div>
    </div>
  )
}


function contarCoincidencias(texto, patron) {
  if (!texto) return 0
  const m = texto.match(patron)
  return m ? m.length : 0
}

function extraerPuntaje(texto) {
  if (!texto) return 'No reportado'
  const m = texto.match(/puntaje[^:\n]*:\s*([0-9.]+)\s*\/\s*([0-9.]+)/i)
  return m ? `${m[1]} / ${m[2]}` : 'No reportado'
}

function estadoAgente(texto) {
  const t = (texto || '').toLowerCase()
  const faltas = contarCoincidencias(texto || '', /\(FALTA\)|no cumplidos?|ausencia|no se presenta|no se incluye|no detalla|no define/gi)
  if (t.includes('puntaje') && (t.includes('0.0 /') || t.includes('0.00 /'))) {
    return { icon: '🔴', label: 'Crítico', bg: '#FEE2E2', color: '#7F1D1D' }
  }
  if (faltas >= 5) return { icon: '🔴', label: 'Crítico', bg: '#FEE2E2', color: '#7F1D1D' }
  if (faltas >= 2 || t.includes('observado')) return { icon: '🟡', label: 'Requiere revisión', bg: '#FEF3C7', color: '#92400E' }
  return { icon: '🟢', label: 'Adecuado', bg: '#D1FAE5', color: '#065F46' }
}

function AgentSummaryCard({ titulo, icono, texto, color }) {
  const estado = estadoAgente(texto)
  const ids = new Set((texto || '').match(/ID-\d{2}/g) || [])
  const faltas = contarCoincidencias(texto || '', /\(FALTA\)|No cumplidos?:|no se presenta|no se incluye|ausencia/gi)
  const puntaje = extraerPuntaje(texto)
  return (
    <div style={{ border: '1px solid #E5E7EB', borderRadius: 14, padding: 14, background: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 20 }}>{icono}</span>
          <div>
            <div style={{ fontWeight: 800, color: C.primary, fontSize: 13 }}>{titulo}</div>
            <div style={{ fontSize: 11, color: '#6B7280' }}>Puntaje IA: {puntaje}</div>
          </div>
        </div>
        <span style={{ background: estado.bg, color: estado.color, padding: '5px 10px', borderRadius: 999, fontSize: 11, fontWeight: 800 }}>
          {estado.icon} {estado.label}
        </span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
        <div style={{ background: '#F8FAFC', borderRadius: 8, padding: '8px 10px' }}>
          <div style={{ fontSize: 16, fontWeight: 800, color }}>{ids.size || '—'}</div>
          <div style={{ fontSize: 10, color: '#6B7280' }}>criterios citados</div>
        </div>
        <div style={{ background: '#F8FAFC', borderRadius: 8, padding: '8px 10px' }}>
          <div style={{ fontSize: 16, fontWeight: 800, color: estado.color }}>{faltas}</div>
          <div style={{ fontSize: 10, color: '#6B7280' }}>alertas detectadas</div>
        </div>
      </div>
      <details>
        <summary style={{ cursor: 'pointer', color, fontSize: 12, fontWeight: 800, listStyle: 'none' }}>
          🔍 Ver evaluación completa
        </summary>
        <DetalleEvaluacion texto={texto} color={color} />
      </details>
    </div>
  )
}

function decisionMeta(decision) {
  const map = {
    aprobado: { icon: '✅', label: 'Aprobado', color: '#065F46', bg: '#D1FAE5' },
    aprobado_con_cambios: { icon: '✏️', label: 'Aprobado con cambios', color: '#92400E', bg: '#FEF3C7' },
    rechazado: { icon: '❌', label: 'Rechazado', color: '#7F1D1D', bg: '#FEE2E2' },
  }
  return map[decision] || { icon: '📌', label: 'Sin decisión', color: '#374151', bg: '#F3F4F6' }
}

// Modal principal de validación
function ModalValidacion({ tesis, onClose, onValidado }) {
  const [resultado, setResultado]       = useState(null)
  const [loading, setLoading]           = useState(true)
  const [step, setStep]                 = useState('ver')  // 'ver' | 'intervenir' | 'confirmado'
  const [decision, setDecision]         = useState('')
  const [comentario, setComentario]     = useState('')
  const [enviando, setEnviando]         = useState(false)
  const [sugerencias, setSugerencias]   = useState([])
  const [resultadoHL, setResultadoHL]   = useState(null)
  const [pollingHL, setPollingHL]       = useState(false)

  useEffect(() => {
    getResultMaestro(tesis.id)
      .then(d => {
        setResultado(d)
        // Generar sugerencias de intervención basadas en el texto del análisis
        const texto = d?.resultado?.secuencial?.texto_crudo || d?.resultado?.jerarquico?.texto_crudo || ''
        const sugs = []
        if (texto.toLowerCase().includes('metodol')) sugs.push('Reforzar análisis metodológico: la matriz de consistencia necesita mayor coherencia entre variables.')
        if (texto.toLowerCase().includes('apa') || texto.toLowerCase().includes('cit')) sugs.push('Corregir citaciones APA en el capítulo de referencias bibliográficas.')
        if (texto.toLowerCase().includes('muestr') || texto.toLowerCase().includes('muestra')) sugs.push('Justificar estadísticamente el tamaño muestral en el Capítulo III.')
        if (texto.toLowerCase().includes('técni') || texto.toLowerCase().includes('arquit')) sugs.push('Agregar diagrama de arquitectura de despliegue en la sección técnica.')
        setSugerencias(sugs.slice(0, 3))
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [tesis.id])

  const confirmarDecision = async () => {
    if (!decision) return
    setEnviando(true)
    try {
      await validarTesis(tesis.id, decision, comentario)
      setStep('confirmado')
      onValidado(tesis.id, decision)
      // Polling: esperar resultado Human-Loop del backend (corre en background ~60-120s)
      setPollingHL(true)
      let intentos = 0
      const intervalo = setInterval(async () => {
        intentos++
        try {
          const res = await getResultMaestro(tesis.id)
          const hl = res?.resultado?.human_loop
          if (hl?.texto_crudo) {
            setResultadoHL(hl)
            setPollingHL(false)
            clearInterval(intervalo)
          }
        } catch {}
        if (intentos >= 30) { setPollingHL(false); clearInterval(intervalo) }
      }, 5000)
    } catch (e) {
      alert('Error al validar: ' + (e.response?.data?.detail || e.message))
    } finally {
      setEnviando(false)
    }
  }

  const r            = resultado?.resultado || {}
  const tipoAnalisis = r.tipo
  const textoIA      = tipoAnalisis === 'veredicto' ? r.jerarquico?.texto_crudo : r.secuencial?.texto_crudo

  // Extraer secciones de los 3 agentes del texto del Conciliador
  const secMet = extraerSeccion(textoIA, 'metodol')
  const secTec = extraerSeccion(textoIA, 'técni') || extraerSeccion(textoIA, 'tecni')
  const secLin = extraerSeccion(textoIA, 'lingü') || extraerSeccion(textoIA, 'lingu') || extraerSeccion(textoIA, 'redac')

  // Detectar veredicto del sistema
  const textoUpper = (textoIA || '').toUpperCase()
  const veredictoSistema = textoUpper.includes('RECHAZ') || textoUpper.includes('NO APROBADO')
    ? { icon: '❌', label: 'RECHAZADO', color: '#7F1D1D', bg: '#FEE2E2' }
    : textoUpper.includes('OBSERV') || textoUpper.includes('CAMBIO')
    ? { icon: '⚠️', label: 'APROBADO CON OBSERVACIONES', color: '#92400E', bg: '#FEF3C7' }
    : textoIA
    ? { icon: '✅', label: 'APROBADO', color: '#065F46', bg: '#D1FAE5' }
    : null

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
      <div style={{ background: '#fff', borderRadius: 16, width: '100%', maxWidth: 760, maxHeight: '92vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>

        {/* Header */}
        <div style={{ background: C.primary, color: '#fff', padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15 }}>📋 {tesis.titulo}</div>
            <div style={{ fontSize: 12, opacity: 0.75, marginTop: 2 }}>👤 {tesis.alumno}</div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#fff', fontSize: 22, cursor: 'pointer', lineHeight: 1 }}>✕</button>
        </div>

        {/* Stepper */}
        <div style={{ display: 'flex', borderBottom: '1px solid #E5E7EB', flexShrink: 0 }}>
          {[['ver', '1', 'Ver análisis IA'], ['intervenir', '2', 'Tu intervención'], ['confirmado', '3', 'Confirmado']].map(([key, num, label]) => (
            <div key={key} style={{
              flex: 1, padding: '10px 0', textAlign: 'center', fontSize: 12, fontWeight: 600,
              borderBottom: step === key ? `2px solid ${C.primary}` : '2px solid transparent',
              color: step === key ? C.primary : '#9CA3AF',
              cursor: step !== 'confirmado' && key !== 'confirmado' ? 'pointer' : 'default',
            }}
              onClick={() => step !== 'confirmado' && key !== 'confirmado' && setStep(key)}>
              <span style={{ background: step === key ? C.primary : '#E5E7EB', color: step === key ? '#fff' : '#9CA3AF', borderRadius: '50%', width: 20, height: 20, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, marginRight: 6 }}>{num}</span>
              {label}
            </div>
          ))}
        </div>

        <div style={{ overflowY: 'auto', flex: 1, padding: 24 }}>

          {/* ── STEP 1: Ver análisis ── */}
          {step === 'ver' && (
            <>
              {loading ? (
                <div style={{ textAlign: 'center', padding: 48, color: '#9CA3AF' }}>
                  <div style={{ fontSize: 32, marginBottom: 8 }}>🤖</div>
                  Cargando análisis de los agentes...
                </div>
              ) : !textoIA ? (
                <div style={{ background: '#FEF3C7', borderRadius: 8, padding: 16, color: '#92400E', fontSize: 13 }}>
                  ⚠️ Esta tesis aún no tiene un análisis disponible. El alumno debe correr el análisis primero.
                </div>
              ) : (
                <>
                  {/* Veredicto del sistema */}
                  {veredictoSistema && (
                    <div style={{ background: veredictoSistema.bg, borderRadius: 10, padding: '14px 20px', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 12 }}>
                      <span style={{ fontSize: 24 }}>{veredictoSistema.icon}</span>
                      <div>
                        <div style={{ fontWeight: 800, color: veredictoSistema.color, fontSize: 14 }}>
                          PROPUESTA DE LOS AGENTES: {veredictoSistema.label}
                        </div>
                        <div style={{ fontSize: 11, color: veredictoSistema.color, opacity: 0.8, marginTop: 2 }}>
                          Esta es una propuesta preliminar. Tu intervención en el paso 2 puede modificar el dictamen final.
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Tipo de análisis */}
                  <div style={{ background: '#EFF6FF', borderRadius: 8, padding: '8px 14px', marginBottom: 16, fontSize: 12, color: '#1E40AF' }}>
                    Tipo: <strong>{tipoAnalisis === 'veredicto' ? '🏛️ Veredicto jerárquico' : '🔍 Análisis secuencial'}</strong>
                    {resultado?.latencia_ms && <span style={{ marginLeft: 10, color: '#6B7280' }}>⚡ {(resultado.latencia_ms / 1000).toFixed(1)}s</span>}
                  </div>

                  {/* Resumen ejecutivo por agente */}
                  <h4 style={{ color: C.primary, fontSize: 13, marginBottom: 10 }}>📊 Evaluación preliminar de la IA</h4>
                  <div style={{ background: '#F8FAFC', border: '1px solid #E5E7EB', borderRadius: 10, padding: '10px 14px', marginBottom: 14, fontSize: 12, color: '#475569', lineHeight: 1.55 }}>
                    Revisión generada por los agentes como propuesta inicial. El docente puede validar, corregir o modificar este resultado en el siguiente paso.
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 10, marginBottom: 14 }}>
                    <AgentSummaryCard titulo="Agente Metodológico" icono="📐" texto={secMet || textoIA} color="#3B82F6" />
                    {secTec && <AgentSummaryCard titulo="Agente Técnico" icono="⚙️" texto={secTec} color="#8B5CF6" />}
                    {secLin && <AgentSummaryCard titulo="Agente Lingüístico" icono="📝" texto={secLin} color="#10B981" />}
                  </div>

                  {/* Propuesta completa del conciliador */}
                  <div style={{ marginTop: 8 }}>
                    <button onClick={() => document.getElementById('dictamen-completo').style.display =
                      document.getElementById('dictamen-completo').style.display === 'none' ? 'block' : 'none'}
                      style={{ background: 'none', border: '1px solid #E5E7EB', borderRadius: 6, padding: '6px 14px', fontSize: 12, cursor: 'pointer', color: '#6B7280', marginBottom: 8 }}>
                      📄 Ver dictamen completo del Conciliador
                    </button>
                    <div id="dictamen-completo" style={{ display: 'none', background: '#F8FAFC', border: '1px solid #E5E7EB', borderRadius: 8, padding: 16, fontSize: 12, color: '#374151', whiteSpace: 'pre-wrap', lineHeight: 1.7, maxHeight: 250, overflowY: 'auto' }}>
                      {textoIA}
                    </div>
                  </div>

                  {/* Nota sobre Human-Loop */}
                  <div style={{ background: '#EEF2FF', borderRadius: 8, padding: '12px 16px', marginTop: 16, fontSize: 12, color: '#4F46E5', lineHeight: 1.6 }}>
                    <strong>ℹ️ ¿Cómo funciona tu intervención?</strong><br />
                    En el paso 2, puedes escribir tus observaciones como docente. Los agentes IA usarán tus instrucciones para <strong>regenerar el dictamen final</strong>. Tu criterio prevalece sobre cualquier hallazgo de la IA.
                  </div>
                </>
              )}

              {textoIA && (
                <button onClick={() => setStep('intervenir')}
                  style={{ width: '100%', marginTop: 20, background: C.primary, color: '#fff', border: 'none', padding: '12px 0', borderRadius: 8, fontWeight: 700, fontSize: 14, cursor: 'pointer' }}>
                  Continuar → Tu intervención como docente
                </button>
              )}
            </>
          )}

          {/* ── STEP 2: Intervención del docente ── */}
          {step === 'intervenir' && (
            <>
              <div style={{ background: 'linear-gradient(135deg, #EEF2FF 0%, #F8FAFC 100%)', border: '1px solid #C7D2FE', borderRadius: 14, padding: '16px 18px', marginBottom: 18, fontSize: 13, color: C.accent, lineHeight: 1.6 }}>
                <strong>👨‍🏫 Intervención docente</strong><br />
                Revisa la propuesta de los agentes, añade tus observaciones y define la decisión oficial. Tu criterio prevalece sobre el análisis preliminar.
              </div>

              {/* Sugerencias rápidas */}
              {sugerencias.length > 0 && (
                <div style={{ marginBottom: 18 }}>
                  <div style={{ fontSize: 12, color: '#475569', marginBottom: 8, fontWeight: 800 }}>
                    💡 Observaciones sugeridas
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    {sugerencias.map((s, i) => {
                      const lower = s.toLowerCase()
                      const tag = lower.includes('apa') || lower.includes('cita') ? 'APA' : lower.includes('muestr') ? 'Muestra' : lower.includes('arquitect') || lower.includes('técn') ? 'Técnico' : 'Metodología'
                      const color = tag === 'APA' ? '#B45309' : tag === 'Técnico' ? '#1D4ED8' : tag === 'Muestra' ? '#7C3AED' : '#047857'
                      return (
                        <button key={i} onClick={() => setComentario(prev => prev ? prev + '\n' + s : s)}
                          style={{ background: '#fff', border: `1.5px solid ${color}55`, borderRadius: 999, padding: '8px 12px', fontSize: 12, color, cursor: 'pointer', fontWeight: 700 }}>
                          + {tag}: {s.length > 54 ? s.slice(0, 54) + '…' : s}
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Textarea de observación */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <label style={{ fontWeight: 800, fontSize: 13, color: '#374151' }}>
                  📝 Observación del docente
                </label>
                <span style={{ fontSize: 11, color: comentario.length > 1500 ? '#B91C1C' : '#9CA3AF' }}>{comentario.length} / 1500</span>
              </div>
              <textarea
                value={comentario}
                onChange={e => setComentario(e.target.value.slice(0, 1800))}
                placeholder={"Escribe tu instrucción final. Ejemplo: 'Confirmo el análisis de los agentes, pero agregar como observación crítica la falta de validación de instrumentos con juicio de expertos.'"}
                rows={6}
                style={{ width: '100%', padding: '13px 14px', border: '1.5px solid #CBD5E1', borderRadius: 10, fontSize: 13, resize: 'vertical', boxSizing: 'border-box', lineHeight: 1.6, marginBottom: 8 }}
              />

              <details style={{ marginBottom: 18 }}>
                <summary style={{ cursor: 'pointer', color: '#6B7280', fontSize: 12, fontWeight: 700 }}>💡 Ver ejemplos de intervención</summary>
                <div style={{ background: '#F8FAFC', border: '1px solid #E5E7EB', borderRadius: 10, padding: 12, marginTop: 8, fontSize: 12, color: '#475569', lineHeight: 1.65 }}>
                  <div>• El agente metodológico está equivocado en el punto 2; la muestra sí es representativa porque la población es finita.</div>
                  <div>• Ignorar las observaciones de redacción. Enfocarse solo en la validez metodológica.</div>
                  <div>• Agregar como observación crítica que falta validación de instrumentos con juicio de expertos.</div>
                </div>
              </details>

              {/* Selección de decisión */}
              <label style={{ display: 'block', fontWeight: 800, fontSize: 13, color: '#374151', marginBottom: 10 }}>
                🏛️ Decisión oficial del docente
              </label>
              <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
                {[
                  { key: 'aprobado', label: '✅ Aprobar', bg: '#10B981', desc: 'La tesis cumple todos los requisitos' },
                  { key: 'aprobado_con_cambios', label: '✏️ Aprobar con cambios', bg: '#F59E0B', desc: 'Requiere correcciones menores' },
                  { key: 'rechazado', label: '❌ Rechazar', bg: '#EF4444', desc: 'No cumple requisitos mínimos' },
                ].map(opt => (
                  <button key={opt.key} onClick={() => setDecision(opt.key)}
                    style={{
                      flex: 1, minWidth: 150, padding: '14px 12px', borderRadius: 14, border: `2px solid ${decision === opt.key ? opt.bg : '#E5E7EB'}`,
                      background: decision === opt.key ? opt.bg : '#fff',
                      color: decision === opt.key ? '#fff' : '#374151',
                      cursor: 'pointer', fontWeight: 800, fontSize: 13, transition: 'all 0.15s', boxShadow: decision === opt.key ? `0 8px 18px ${opt.bg}35` : '0 1px 3px rgba(0,0,0,0.04)'
                    }}>
                    <div>{opt.label}</div>
                    <div style={{ fontSize: 10, opacity: 0.8, marginTop: 3 }}>{opt.desc}</div>
                  </button>
                ))}
              </div>

              {!decision && (
                <div style={{ background: '#FEF3C7', borderRadius: 6, padding: '8px 12px', marginBottom: 12, fontSize: 12, color: '#92400E' }}>
                  ⚠️ Selecciona una decisión antes de confirmar.
                </div>
              )}

              <button
                onClick={confirmarDecision}
                disabled={!decision || enviando}
                style={{ width: '100%', background: decision ? C.primary : '#9CA3AF', color: '#fff', border: 'none', padding: '13px 0', borderRadius: 8, fontWeight: 700, fontSize: 14, cursor: decision ? 'pointer' : 'not-allowed', opacity: enviando ? 0.7 : 1 }}>
                {enviando ? '⏳ Generando dictamen oficial...' : '🏛️ Generar dictamen oficial'}
              </button>
              {enviando && (
                <p style={{ textAlign: 'center', color: '#6B7280', fontSize: 12, marginTop: 8 }}>
                  Los agentes están integrando tu intervención. El dictamen oficial se generará en background.
                </p>
              )}
            </>
          )}

          {/* ── STEP 3: Confirmado + resultado Human-Loop ── */}
          {step === 'confirmado' && (
            <div style={{ padding: '24px 16px' }}>
              {/* Cabecera decisión */}
              {(() => {
                const dm = decisionMeta(decision)
                const aiLabel = veredictoSistema?.label || 'No determinado'
                return (
                  <div style={{ marginBottom: 20 }}>
                    <div style={{ textAlign: 'center', marginBottom: 16 }}>
                      <div style={{ fontSize: 38, marginBottom: 6 }}>🏛️</div>
                      <h3 style={{ color: C.primary, margin: 0 }}>Dictamen oficial del docente</h3>
                      <p style={{ color: '#6B7280', fontSize: 12, margin: '6px 0 0' }}>La decisión humana prevalece sobre la propuesta inicial de los agentes.</p>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 12 }}>
                      <div style={{ background: '#F8FAFC', border: '1px solid #E5E7EB', borderRadius: 12, padding: 14, textAlign: 'center' }}>
                        <div style={{ fontSize: 11, color: '#6B7280', fontWeight: 700 }}>PROPUESTA IA</div>
                        <div style={{ fontSize: 14, fontWeight: 900, color: veredictoSistema?.color || '#374151', marginTop: 4 }}>{aiLabel}</div>
                      </div>
                      <div style={{ background: dm.bg, border: `1px solid ${dm.color}44`, borderRadius: 12, padding: 14, textAlign: 'center' }}>
                        <div style={{ fontSize: 11, color: dm.color, fontWeight: 700 }}>DECISIÓN DOCENTE</div>
                        <div style={{ fontSize: 14, fontWeight: 900, color: dm.color, marginTop: 4 }}>{dm.icon} {dm.label.toUpperCase()}</div>
                      </div>
                    </div>

                    <div style={{ background: '#ECFDF5', border: '1px solid #A7F3D0', borderRadius: 12, padding: '12px 14px', marginBottom: 12, fontSize: 12, color: '#065F46', lineHeight: 1.65 }}>
                      <strong>🔁 Cambios aplicados por intervención humana</strong>
                      <div>✓ Se registró una decisión docente oficial.</div>
                      <div>✓ Se incorporaron observaciones humanas al dictamen final.</div>
                      <div>✓ La decisión humana prevalece sobre la propuesta inicial de los agentes.</div>
                    </div>

                    {comentario && (
                      <div style={{ background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: 12, padding: '12px 14px', color: '#92400E', fontSize: 12, lineHeight: 1.65 }}>
                        <strong>📝 Observación del docente:</strong><br />{comentario}
                      </div>
                    )}
                  </div>
                )
              })()}

              {/* Spinner mientras llega el resultado */}
              {pollingHL && !resultadoHL && (
                <div style={{ textAlign: 'center', padding: '20px 0', color: '#6B7280', fontSize: 13 }}>
                  <div style={{ fontSize: 28, marginBottom: 8 }}>⏳</div>
                  Los agentes están procesando tu instrucción...<br />
                  <span style={{ fontSize: 11, color: '#9CA3AF' }}>Esto puede tardar entre 30s y 2 minutos</span>
                </div>
              )}

              {/* Resultado del Human-Loop cuando llega */}
              {resultadoHL?.texto_crudo && (() => {
                const texto = resultadoHL.texto_crudo
                // Parsear secciones del dictamen
                const getSeccion = (t, key) => {
                  const r = t.match(new RegExp(`===${key}===([\s\S]*?)(?====|$)`, 'i'))
                  return r ? r[1].trim() : null
                }
                const secMet  = getSeccion(texto, 'METODOLOGICO')
                const secTec  = getSeccion(texto, 'TECNICO')
                const secLin  = getSeccion(texto, 'LINGUISTICO')
                const secDict = getSeccion(texto, 'DICTAMEN')
                const rigorM  = texto.match(/RIGOR SCORE FINAL[:\s]+([0-9.]+)/i)
                const rigor   = rigorM ? parseFloat(rigorM[1]) : null
                const rigorColor = rigor >= 0.80 ? '#065F46' : rigor >= 0.60 ? '#92400E' : '#7F1D1D'
                const rigorBg    = rigor >= 0.80 ? '#D1FAE5' : rigor >= 0.60 ? '#FEF3C7' : '#FEE2E2'
                const vUpper = texto.toUpperCase()
                const vLabel = vUpper.includes('RECHAZ') ? '❌ RECHAZADO' : vUpper.includes('OBSERV') ? '⚠️ APROBADO CON OBSERVACIONES' : '✅ APROBADO'

                return (
                  <div>
                    {/* Veredicto + Rigor Score */}
                    <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap', marginBottom: 16 }}>
                      <span style={{ fontWeight: 800, fontSize: 15, background: rigorBg, color: rigorColor, borderRadius: 8, padding: '8px 18px' }}>
                        {vLabel}
                      </span>
                      {rigor !== null && (
                        <span style={{ background: rigorBg, color: rigorColor, borderRadius: 8, padding: '8px 18px', fontWeight: 700, fontSize: 13 }}>
                          📊 Rigor Score: {rigor.toFixed(2)} ({(rigor * 100).toFixed(1)}%)
                        </span>
                      )}
                    </div>

                    {/* Tarjetas por agente */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 16 }}>
                      {secMet && (
                        <div style={{ border: '1.5px solid #3B82F6', borderRadius: 10, overflow: 'hidden' }}>
                          <div style={{ background: '#EFF6FF', padding: '8px 14px', fontWeight: 700, fontSize: 13, color: '#1D4ED8' }}>📐 Agente Metodológico</div>
                          <div style={{ padding: '10px 14px', fontSize: 12, color: '#374151', lineHeight: 1.7, maxHeight: 160, overflowY: 'auto', whiteSpace: 'pre-wrap' }}>
                            {secMet.slice(0, 600)}
                          </div>
                        </div>
                      )}
                      {secTec && (
                        <div style={{ border: '1.5px solid #8B5CF6', borderRadius: 10, overflow: 'hidden' }}>
                          <div style={{ background: '#F5F3FF', padding: '8px 14px', fontWeight: 700, fontSize: 13, color: '#6D28D9' }}>⚙️ Agente Técnico</div>
                          <div style={{ padding: '10px 14px', fontSize: 12, color: '#374151', lineHeight: 1.7, maxHeight: 160, overflowY: 'auto', whiteSpace: 'pre-wrap' }}>
                            {secTec.slice(0, 600)}
                          </div>
                        </div>
                      )}
                      {secLin && (
                        <div style={{ border: '1.5px solid #F59E0B', borderRadius: 10, overflow: 'hidden' }}>
                          <div style={{ background: '#FFFBEB', padding: '8px 14px', fontWeight: 700, fontSize: 13, color: '#92400E' }}>📝 Agente Lingüístico</div>
                          <div style={{ padding: '10px 14px', fontSize: 12, color: '#374151', lineHeight: 1.7, maxHeight: 160, overflowY: 'auto', whiteSpace: 'pre-wrap' }}>
                            {secLin.slice(0, 600)}
                          </div>
                        </div>
                      )}
                      {secDict && (
                        <div style={{ border: '2px solid #10B981', borderRadius: 10, overflow: 'hidden' }}>
                          <div style={{ background: '#D1FAE5', padding: '8px 14px', fontWeight: 700, fontSize: 13, color: '#065F46' }}>⚖️ Dictamen Final</div>
                          <div style={{ padding: '10px 14px', fontSize: 12, color: '#374151', lineHeight: 1.7, maxHeight: 200, overflowY: 'auto', whiteSpace: 'pre-wrap' }}>
                            {secDict.slice(0, 800)}
                          </div>
                        </div>
                      )}
                      {!secMet && !secDict && (
                        <div style={{ border: '1px solid #E5E7EB', borderRadius: 10, padding: 14, fontSize: 12, color: '#374151', lineHeight: 1.7, whiteSpace: 'pre-wrap', maxHeight: 300, overflowY: 'auto' }}>
                          {texto}
                        </div>
                      )}
                    </div>

                    <details style={{ border: '1px solid #E5E7EB', borderRadius: 8, marginBottom: 12 }}>
                      <summary style={{ padding: '8px 14px', fontSize: 11, cursor: 'pointer', color: '#6B7280', fontWeight: 600 }}>
                        📄 Ver respuesta completa del flujo
                      </summary>
                      <div style={{ padding: '10px 14px', fontSize: 11, color: '#374151', lineHeight: 1.7, whiteSpace: 'pre-wrap', maxHeight: 300, overflowY: 'auto' }}>
                        {texto}
                      </div>
                    </details>
                  </div>
                )
              })()}

              <button onClick={onClose}
                style={{ width: '100%', background: C.primary, color: '#fff', border: 'none', padding: '11px 0', borderRadius: 8, fontWeight: 600, fontSize: 13, cursor: 'pointer', marginTop: 8 }}>
                Cerrar
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}


// ── HU-17: Panel de estadísticas (Chart.js via CDN) ──────────────
function EstadisticasPanel({ tesisList }) {
  const canvasRef = useRef(null)
  const chartRef  = useRef(null)

  const aprobadas  = tesisList.filter(t => t.estado === 'aprobado').length
  const observadas = tesisList.filter(t => t.estado === 'aprobado_con_cambios').length
  const rechazadas = tesisList.filter(t => t.estado === 'rechazado').length
  const pendientes = tesisList.filter(t => t.estado === 'pendiente_validacion').length
  const total      = tesisList.length
  const conScore   = tesisList.filter(t => t.rigor_score > 0)
  const promScore  = conScore.length > 0
    ? (conScore.reduce((s, t) => s + t.rigor_score, 0) / conScore.length).toFixed(2)
    : '—'

  useEffect(() => {
    if (!canvasRef.current || aprobadas + observadas + rechazadas + pendientes === 0) return

    // Cargar Chart.js dinámicamente si no está cargado
    const loadChart = () => {
      if (chartRef.current) { chartRef.current.destroy(); chartRef.current = null }
      const ctx = canvasRef.current.getContext('2d')
      chartRef.current = new window.Chart(ctx, {
        type: 'bar',
        data: {
          labels: ['Aprobadas', 'Aprobadas c/cambios', 'Rechazadas', 'Pendientes'],
          datasets: [{
            label: 'Tesis',
            data: [aprobadas, observadas, rechazadas, pendientes],
            backgroundColor: ['#10B981', '#F59E0B', '#EF4444', '#6366F1'],
            borderRadius: 6,
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
        }
      })
    }

    if (window.Chart) {
      loadChart()
    } else {
      const script = document.createElement('script')
      script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js'
      script.onload = loadChart
      document.head.appendChild(script)
    }
    return () => { if (chartRef.current) { chartRef.current.destroy(); chartRef.current = null } }
  }, [aprobadas, observadas, rechazadas, pendientes])

  if (total === 0) return null

  return (
    <div style={{ background: '#fff', borderRadius: 16, padding: 28, boxShadow: '0 2px 8px rgba(0,0,0,0.08)', marginBottom: 24 }}>
      <h3 style={{ color: C.primary, marginBottom: 20, fontSize: 15 }}>📊 HU-17 — Estadísticas del Ciclo</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 24 }}>
        {[
          ['📚', 'Total analizadas', total, '#1F3864'],
          ['✅', 'Aprobadas', aprobadas, '#065F46'],
          ['✏️', 'Aprobadas c/cambios', observadas, '#92400E'],
          ['📊', 'Promedio Rigor Score', promScore, '#4338CA'],
        ].map(([icon, label, val, color]) => (
          <div key={label} style={{ background: '#F8FAFC', borderRadius: 10, padding: '14px 16px', textAlign: 'center' }}>
            <div style={{ fontSize: 20 }}>{icon}</div>
            <div style={{ fontSize: 22, fontWeight: 800, color }}>{val}</div>
            <div style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>{label}</div>
          </div>
        ))}
      </div>
      <div style={{ height: 180 }}>
        <canvas ref={canvasRef} />
      </div>
    </div>
  )
}

export default function MaestroPanel() {
  const { user, logoutUser } = useAuth()
  const navigate = useNavigate()
  const [tesisList, setTesisList] = useState([])
  const [loading, setLoading]     = useState(true)
  const [modalTesis, setModalTesis] = useState(null)

  useEffect(() => {
    getAllThesisMaestro()
      .then(setTesisList)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleValidado = (thesisId, decision) => {
    setTesisList(prev => prev.map(t => t.id === thesisId ? { ...t, estado: decision } : t))
    setTimeout(() => setModalTesis(null), 3000)
  }

  const pendientes = tesisList.filter(t => t.estado === 'pendiente_validacion')

  return (
    <div style={{ minHeight: '100vh', background: '#F0F4F8' }}>

      {/* Navbar */}
      <nav style={{ background: C.primary, color: '#fff', padding: '12px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <span style={{ fontWeight: 800, fontSize: 16 }}>UPAO — Panel del Docente</span>
          <span style={{ marginLeft: 12, fontSize: 12, opacity: 0.7 }}>Sistema de Deliberación Multiagente</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <span style={{ fontSize: 13 }}>👨‍🏫 {user?.nombre}</span>
          <button onClick={() => { logoutUser(); navigate('/login') }}
            style={{ background: 'rgba(255,255,255,0.2)', border: 'none', color: '#fff', padding: '6px 14px', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>
            Cerrar sesión
          </button>
        </div>
      </nav>

      <div style={{ maxWidth: 960, margin: '0 auto', padding: '32px 24px' }}>

        {/* Métricas */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 28 }}>
          {[
            ['📚', 'Total tesis', tesisList.length],
            ['🔔', 'Pendientes de revisión', pendientes.length],
            ['✅', 'Procesadas', tesisList.length - pendientes.length],
          ].map(([icon, label, val]) => (
            <div key={label} style={{ background: '#fff', borderRadius: 12, padding: '20px 24px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)', textAlign: 'center' }}>
              <div style={{ fontSize: 28 }}>{icon}</div>
              <div style={{ fontSize: 28, fontWeight: 800, color: C.primary }}>{val}</div>
              <div style={{ fontSize: 12, color: '#6B7280' }}>{label}</div>
            </div>
          ))}
        </div>

        {/* HU-17 Estadísticas */}
        <EstadisticasPanel tesisList={tesisList} />

        {/* Lista */}
        <div style={{ background: '#fff', borderRadius: 16, padding: 32, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h2 style={{ color: C.primary, margin: 0 }}>📋 Tesis para revisión</h2>
            {pendientes.length > 0 && (
              <span style={{ background: '#FEF3C7', color: '#92400E', padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600 }}>
                {pendientes.length} pendiente{pendientes.length > 1 ? 's' : ''}
              </span>
            )}
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#9CA3AF' }}>Cargando tesis...</div>
          ) : tesisList.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 48, color: '#9CA3AF' }}>
              <div style={{ fontSize: 40, marginBottom: 8 }}>📭</div>
              No hay tesis registradas aún.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {tesisList.map(t => (
                <div key={t.id} style={{
                  border: `1.5px solid ${t.estado === 'pendiente_validacion' ? '#F59E0B' : '#E5E7EB'}`,
                  borderRadius: 10, padding: '16px 20px',
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
                  background: t.estado === 'pendiente_validacion' ? '#FFFBEB' : '#fff',
                }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, color: '#1F2937', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.titulo}</div>
                    <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 4 }}>
                      👤 {t.alumno} · {new Date(t.created_at).toLocaleDateString('es-PE')}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
                    {badge(t.estado)}
                    {['pendiente_validacion', 'aprobado', 'aprobado_con_cambios', 'rechazado'].includes(t.estado) && (
                      <button onClick={() => setModalTesis(t)}
                        style={{ background: C.primary, color: '#fff', border: 'none', padding: '7px 14px', borderRadius: 6, cursor: 'pointer', fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap' }}>
                        {t.estado === 'pendiente_validacion' ? '👁️ Revisar' : '📄 Ver detalle'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {modalTesis && (
        <ModalValidacion
          tesis={modalTesis}
          onClose={() => setModalTesis(null)}
          onValidado={handleValidado}
        />
      )}
    </div>
  )
}
