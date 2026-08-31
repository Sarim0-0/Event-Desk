import { ApiError, refreshAccessToken, request } from './auth.js'
import { updateAccessToken } from '../auth/tokenStorage.js'

export class SessionExpiredError extends Error {
  constructor(message = 'Your session has expired. Please log in again.') {
    super(message)
    this.name = 'SessionExpiredError'
  }
}

export async function authenticatedRequest(
  path,
  { tokens, method = 'GET', body } = {},
) {
  try {
    const data = await request(path, {
      method,
      body,
      accessToken: tokens.access_token,
    })
    return { data, tokens }
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error
  }

  let refreshed
  try {
    refreshed = await refreshAccessToken(tokens.refresh_token)
  } catch (error) {
    if (error instanceof ApiError && [401, 403].includes(error.status)) {
      throw new SessionExpiredError(
        typeof error.payload?.detail === 'string'
          ? error.payload.detail
          : undefined,
      )
    }
    throw error
  }

  const nextTokens = updateAccessToken(refreshed.access_token)
  if (!nextTokens) throw new SessionExpiredError()

  try {
    const data = await request(path, {
      method,
      body,
      accessToken: nextTokens.access_token,
    })
    return { data, tokens: nextTokens }
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      throw new SessionExpiredError()
    }
    throw error
  }
}
