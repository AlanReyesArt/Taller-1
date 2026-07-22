import axios from 'axios'

const DIRECT_API_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({ baseURL: DIRECT_API_URL || '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.clear()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// Auth
export const login = async (email, password) => {
  const form = new URLSearchParams()
  form.append('username', email)
  form.append('password', password)
  const { data } = await api.post('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  })
  return data
}

export const getMe = async () => {
  const { data } = await api.get('/auth/me')
  return data
}

// Tesis
export const uploadThesis = async (titulo, file, onUploadProgress) => {
  const form = new FormData()
  form.append('titulo', titulo)
  form.append('file', file)
  const { data } = await api.post('/thesis/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  })
  return data
}

// 2 botones distintos → 2 endpoints distintos
export const analizarCompleto = async (thesisId) => {
  const { data } = await api.post(`/thesis/${thesisId}/analisis-completo`)
  return data
}

export const obtenerVeredicto = async (thesisId) => {
  const { data } = await api.post(`/thesis/${thesisId}/veredicto`)
  return data
}

// Sprint 2 — EP-02: debate circular Agente Metodológico ↔ Agente Técnico (ARQ_RED)
export const debateRed = async (thesisId) => {
  const { data } = await api.post(`/thesis/${thesisId}/debate-red`)
  return data
}

export const getAnalysisResult = async (thesisId) => {
  const { data } = await api.get(`/thesis/${thesisId}/result`)
  return data
}

export const getMyThesis = async () => {
  const { data } = await api.get('/thesis/')
  return data
}

export const downloadReport = (thesisId) => {
  const token = localStorage.getItem('token')
  const baseUrl = DIRECT_API_URL || '/api'
  window.open(`${baseUrl}/thesis/${thesisId}/report?token=${token}`, '_blank')
}

// Maestro
export const getAllThesisMaestro = async () => {
  const { data } = await api.get('/maestro/tesis')
  return data
}

export const getResultMaestro = async (thesisId) => {
  const { data } = await api.get(`/maestro/tesis/${thesisId}/result`)
  return data
}

export const validarTesis = async (thesisId, decision, comentario) => {
  const { data } = await api.post(`/maestro/tesis/${thesisId}/validar`, {
    decision,
    comentario,
  })
  return data
}
