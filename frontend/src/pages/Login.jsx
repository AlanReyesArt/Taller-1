// src/pages/Login.jsx — HU-01 (alumno) + HU-02 (maestro)
// Redirige automáticamente según el rol retornado por el backend

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../api'
import { useAuth } from '../AuthContext'

const styles = {
  page: { minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #1F3864 0%, #2E5FAB 100%)' },
  card: { background: '#fff', borderRadius: 16, padding: '48px 40px', width: '100%', maxWidth: 420, boxShadow: '0 20px 60px rgba(0,0,0,0.3)' },
  logo: { textAlign: 'center', marginBottom: 8 },
  logoTitle: { color: '#1F3864', fontSize: 22, fontWeight: 800, margin: 0 },
  logoSub: { color: '#666', fontSize: 12, margin: '4px 0 24px' },
  title: { fontSize: 20, fontWeight: 700, color: '#1F3864', marginBottom: 24, textAlign: 'center' },
  label: { display: 'block', fontSize: 13, fontWeight: 600, color: '#444', marginBottom: 6 },
  input: { width: '100%', padding: '10px 14px', border: '1.5px solid #ddd', borderRadius: 8, fontSize: 14, outline: 'none', transition: 'border 0.2s', marginBottom: 16 },
  btn: { width: '100%', padding: '12px', background: '#1F3864', color: '#fff', border: 'none', borderRadius: 8, fontSize: 15, fontWeight: 700, cursor: 'pointer', marginTop: 8 },
  error: { background: '#FEE2E2', color: '#B91C1C', padding: '10px 14px', borderRadius: 8, fontSize: 13, marginBottom: 16 },
  hint: { textAlign: 'center', fontSize: 12, color: '#999', marginTop: 16 },
  hintCode: { background: '#f5f5f5', padding: '2px 6px', borderRadius: 4, fontFamily: 'monospace' }
}

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { loginUser } = useAuth()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email || !password) { setError('Completa todos los campos'); return }
    setLoading(true); setError('')

    try {
      const data = await login(email, password)
      loginUser(data)
      // HU-01: alumno → dashboard | HU-02: maestro → panel docente
      navigate(data.rol === 'maestro' ? '/maestro' : '/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al iniciar sesión')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <div style={styles.logo}>
          <p style={styles.logoTitle}>UPAO</p>
          <p style={styles.logoSub}>Sistema de Deliberación Multiagente</p>
        </div>
        <p style={styles.title}>Iniciar Sesión</p>
        {error && <div style={styles.error}>{error}</div>}
        <form onSubmit={handleSubmit}>
          <label style={styles.label}>Correo institucional</label>
          <input
            style={styles.input} type="email" placeholder="correo@upao.edu.pe"
            value={email} onChange={e => setEmail(e.target.value)}
          />
          <label style={styles.label}>Contraseña</label>
          <input
            style={styles.input} type="password" placeholder="••••••••"
            value={password} onChange={e => setPassword(e.target.value)}
          />
          <button style={styles.btn} disabled={loading}>
            {loading ? 'Ingresando...' : 'Ingresar'}
          </button>
        </form>
        <div style={styles.hint}>
          <p>Cuentas de prueba:</p>
          <p><span style={styles.hintCode}>alumno@upao.edu.pe</span> / alumno123</p>
          <p><span style={styles.hintCode}>maestro@upao.edu.pe</span> / maestro123</p>
        </div>
      </div>
    </div>
  )
}
