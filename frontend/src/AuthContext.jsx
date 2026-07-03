// src/AuthContext.jsx — Estado global de autenticación

import { createContext, useContext, useState, useEffect } from 'react'
import { getMe } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      getMe()
        .then(setUser)
        .catch(() => localStorage.clear())
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const loginUser = (tokenData) => {
    localStorage.setItem('token', tokenData.access_token)
    localStorage.setItem('rol', tokenData.rol)
    localStorage.setItem('nombre', tokenData.nombre)
    setUser({ rol: tokenData.rol, nombre: tokenData.nombre, id: tokenData.user_id })
  }

  const logoutUser = () => {
    localStorage.clear()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loginUser, logoutUser, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
