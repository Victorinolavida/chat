const request = async (path, { method = 'POST', payload, token, signal } = {}) => {
  const headers = {}
  if (payload !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`

  const response = await fetch(path, {
    method,
    headers,
    body: payload !== undefined ? JSON.stringify(payload) : undefined,
    signal,
  })

  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(data.message || data.error || 'Something went wrong')
    error.status = response.status
    throw error
  }
  return data
}

export const register = (payload) => request('/auth/register', { payload })
export const login = (payload) => request('/auth/login', { payload })

export const authRequest = (path, options = {}) => request(path, options)
