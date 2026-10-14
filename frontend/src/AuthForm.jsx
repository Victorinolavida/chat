import { useState } from 'react'
import { login, register } from './api'

export default function AuthForm({ onAuthenticated }) {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ username: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const update = (event) =>
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const credentials = { email: form.email, password: form.password }
      if (mode === 'register') {
        await register(form)
      }
      const { access_token: token, user } = await login(credentials)
      onAuthenticated({ token, user })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card">
      <h1>{mode === 'register' ? 'Create account' : 'Sign in'}</h1>
      <form onSubmit={submit}>
        {mode === 'register' && (
          <label>
            Username
            <input
              name="username"
              value={form.username}
              onChange={update}
              autoComplete="username"
              required
            />
          </label>
        )}
        <label>
          Email
          <input
            name="email"
            type="email"
            value={form.email}
            onChange={update}
            autoComplete="email"
            required
          />
        </label>
        <label>
          Password
          <input
            name="password"
            type="password"
            value={form.password}
            onChange={update}
            autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
            required
          />
        </label>

        {error && <p className="error">{error}</p>}

        <button type="submit" disabled={busy}>
          {busy ? 'Please wait…' : mode === 'register' ? 'Register' : 'Login'}
        </button>
      </form>

      <button
        type="button"
        className="link"
        onClick={() => {
          setMode(mode === 'register' ? 'login' : 'register')
          setError('')
        }}
      >
        {mode === 'register'
          ? 'Already have an account? Sign in'
          : 'Need an account? Register'}
      </button>
    </div>
  )
}
