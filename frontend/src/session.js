const STORAGE_KEY = 'chat.session'

const decodeJwtPayload = (token) => {
  if (typeof token !== 'string') return null
  const segment = token.split('.')[1]
  if (!segment) return null
  try {
    const base64 = segment.replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
    const json = decodeURIComponent(
      atob(padded)
        .split('')
        .map((char) => `%${`00${char.charCodeAt(0).toString(16)}`.slice(-2)}`)
        .join(''),
    )
    return JSON.parse(json)
  } catch {
    return null
  }
}

export const getTokenExpiry = (token) => {
  const payload = decodeJwtPayload(token)
  if (!payload || typeof payload.exp !== 'number') return null
  return payload.exp * 1000
}

export const isTokenExpired = (token) => {
  const expiry = getTokenExpiry(token)
  if (expiry === null) return true
  return expiry <= Date.now()
}

export const saveSession = (session) => {
  if (!session) return
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
}

export const loadSession = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const session = JSON.parse(raw)
    if (!session?.token || !session?.user) return null
    return session
  } catch {
    return null
  }
}

export const clearSession = () => {
  localStorage.removeItem(STORAGE_KEY)
}
