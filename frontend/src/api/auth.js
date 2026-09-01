const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()
const API_BASE_URL = (configuredApiBaseUrl || '/api').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(response, payload) {
    super(`EventDesk API request failed with status ${response.status}.`)
    this.name = 'ApiError'
    this.status = response.status
    this.payload = payload
  }
}

export async function request(
  path,
  { method = 'GET', body, accessToken } = {},
) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    mode: 'cors',
    credentials: 'omit',
    headers: {
      Accept: 'application/json',
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })

  const contentType = response.headers.get('content-type') || ''
  const hasNoContent = [204, 205].includes(response.status)
  const payload = !hasNoContent && contentType.includes('application/json')
    ? await response.json()
    : null

  if (!response.ok) {
    throw new ApiError(response, payload)
  }

  return payload
}

export function signUp({ name, email, password, role }) {
  return request('/auth/signup', {
    method: 'POST',
    body: { name, email, password, role },
  })
}

export function logIn({ email, password }) {
  return request('/auth/login', {
    method: 'POST',
    body: { email, password },
  })
}

export function refreshAccessToken(refreshToken) {
  return request('/auth/refresh', {
    method: 'POST',
    body: { refresh_token: refreshToken },
  })
}

export function logOut(refreshToken) {
  return request('/auth/logout', {
    method: 'POST',
    body: { refresh_token: refreshToken },
  })
}
