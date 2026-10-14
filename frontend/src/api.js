const request = async (path, payload) => {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.message || data.error || 'Something went wrong')
  }
  return data
}

export const register = (payload) => request('/auth/register', payload)
export const login = (payload) => request('/auth/login', payload)
