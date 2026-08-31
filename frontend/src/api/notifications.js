import { authenticatedRequest } from './authenticated.js'

export function listNotifications({ tokens, context = 'all' }) {
  const query =
    context && context !== 'all'
      ? `?context=${encodeURIComponent(context)}`
      : ''

  return authenticatedRequest(`/notifications${query}`, { tokens })
}

export function markNotificationRead({ tokens, notificationId }) {
  return authenticatedRequest(
    `/notifications/${encodeURIComponent(notificationId)}/read`,
    {
      tokens,
      method: 'PATCH',
    },
  )
}

export function markAllNotificationsRead({ tokens }) {
  return authenticatedRequest('/notifications/read-all', {
    tokens,
    method: 'PATCH',
  })
}

export function getNotificationSocketUrl(accessToken) {
  const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()
  const apiBaseUrl = (configuredApiBaseUrl || '/api').replace(/\/$/, '')
  const baseUrl = new URL(apiBaseUrl, window.location.origin)
  baseUrl.protocol = baseUrl.protocol === 'https:' ? 'wss:' : 'ws:'
  baseUrl.pathname = `${baseUrl.pathname}/ws/notifications`.replace(/\/+/g, '/')
  baseUrl.search = new URLSearchParams({ token: accessToken }).toString()
  return baseUrl.toString()
}
