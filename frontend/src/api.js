const request = async (path, { method = 'POST', payload, token } = {}) => {
  const headers = {}
  if (payload !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`

  const response = await fetch(path, {
    method,
    headers,
    body: payload !== undefined ? JSON.stringify(payload) : undefined,
  })

  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.message || data.error || 'Something went wrong')
  }
  return data
}

export const register = (payload) => request('/auth/register', { payload })
export const login = (payload) => request('/auth/login', { payload })

export const authRequest = (path, options = {}) => request(path, options)
