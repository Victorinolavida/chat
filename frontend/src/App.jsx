import { useCallback, useEffect, useState } from 'react'
import AuthForm from './AuthForm'
import Chat from './Chat'
import {
  clearSession,
  getTokenExpiry,
  isTokenExpired,
  loadSession,
  saveSession,
} from './session'
import './App.css'

const MAX_TIMEOUT = 2 ** 31 - 1

function App() {
  const [session, setSession] = useState(() => {
    const stored = loadSession()
    if (!stored) return null
    if (isTokenExpired(stored.token)) {
      clearSession()
      return null
    }
    return stored
  })

  const logout = useCallback(() => {
    clearSession()
    setSession(null)
  }, [])

  const authenticate = useCallback((next) => {
    saveSession(next)
    setSession(next)
  }, [])

  useEffect(() => {
    if (!session) return undefined
    const expiry = getTokenExpiry(session.token)
    if (expiry === null) return undefined
    const delay = Math.max(0, Math.min(expiry - Date.now(), MAX_TIMEOUT))
    const timer = setTimeout(logout, delay)
    return () => clearTimeout(timer)
  }, [session, logout])

  return (
    <div className="app">
      {session ? (
        <Chat session={session} onLogout={logout} onAuthError={logout} />
      ) : (
        <AuthForm onAuthenticated={authenticate} />
      )}
    </div>
  )
}

export default App
