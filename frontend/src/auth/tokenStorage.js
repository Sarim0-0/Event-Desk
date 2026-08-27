const STORAGE_KEY = 'eventdesk.auth'

function isTokenResponse(value) {
  return (
    value &&
    typeof value.access_token === 'string' &&
    value.access_token.length > 0 &&
    typeof value.refresh_token === 'string' &&
    value.refresh_token.length > 0 &&
    value.token_type === 'bearer'
  )
}

export function saveTokens(tokens) {
  if (!isTokenResponse(tokens)) {
    throw new TypeError('The API returned an invalid authentication response.')
  }

  localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens))
  return tokens
}

export function getStoredTokens() {
  try {
    const storedValue = localStorage.getItem(STORAGE_KEY)
    if (!storedValue) return null

    const tokens = JSON.parse(storedValue)
    if (!isTokenResponse(tokens)) {
      clearTokens()
      return null
    }

    return tokens
  } catch {
    clearTokens()
    return null
  }
}

export function updateAccessToken(accessToken) {
  const tokens = getStoredTokens()
  if (!tokens || typeof accessToken !== 'string' || !accessToken) {
    clearTokens()
    return null
  }

  return saveTokens({ ...tokens, access_token: accessToken })
}

export function clearTokens() {
  localStorage.removeItem(STORAGE_KEY)
}

export function getAccessTokenClaims(accessToken) {
  try {
    const encodedPayload = accessToken.split('.')[1]
    if (!encodedPayload) return null

    const base64 = encodedPayload.replace(/-/g, '+').replace(/_/g, '/')
    const paddedBase64 = base64.padEnd(Math.ceil(base64.length / 4) * 4, '=')
    return JSON.parse(atob(paddedBase64))
  } catch {
    return null
  }
}

export function isAccessTokenExpired(accessToken, clockSkewSeconds = 30) {
  const claims = getAccessTokenClaims(accessToken)
  if (typeof claims?.exp !== 'number') return true

  return claims.exp <= Math.floor(Date.now() / 1000) + clockSkewSeconds
}
