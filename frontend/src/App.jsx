// src/App.jsx — Router principal con protección de rutas por rol

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './AuthContext'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import MaestroPanel from './pages/MaestroPanel'

function PrivateRoute({ children, rolRequerido }) {
  const { user, loading } = useAuth()
  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', color: '#1F3864', fontSize: 18 }}>Cargando...</div>
  if (!user) return <Navigate to="/login" replace />
  if (rolRequerido && user.rol !== rolRequerido) return <Navigate to={user.rol === 'maestro' ? '/maestro' : '/dashboard'} replace />
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/dashboard" element={
            <PrivateRoute rolRequerido="alumno">
              <Dashboard />
            </PrivateRoute>
          } />
          <Route path="/maestro" element={
            <PrivateRoute rolRequerido="maestro">
              <MaestroPanel />
            </PrivateRoute>
          } />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
