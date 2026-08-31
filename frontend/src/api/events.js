import { authenticatedRequest } from './authenticated.js'

export function listCategories({ tokens }) {
  return authenticatedRequest('/events/categories', { tokens })
}

export function listTags({ tokens }) {
  return authenticatedRequest('/events/tags', { tokens })
}

export function listEvents({
  tokens,
  page = 1,
  categoryId = '',
  tagIds = [],
}) {
  const query = new URLSearchParams({ page: String(page) })
  if (categoryId) query.set('category_id', categoryId)
  tagIds.forEach((tagId) => query.append('tag_ids', tagId))

  return authenticatedRequest(`/events?${query}`, { tokens })
}

export function createEvent({ tokens, event }) {
  return authenticatedRequest('/events', {
    tokens,
    method: 'POST',
    body: event,
  })
}

export function getEventAvailabilitySocketUrl(accessToken) {
  const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()
  const apiBaseUrl = (configuredApiBaseUrl || '/api').replace(/\/$/, '')
  const baseUrl = new URL(apiBaseUrl, window.location.origin)
  baseUrl.protocol = baseUrl.protocol === 'https:' ? 'wss:' : 'ws:'
  baseUrl.pathname = `${baseUrl.pathname}/ws/events`.replace(/\/+/g, '/')
  baseUrl.search = new URLSearchParams({ token: accessToken }).toString()
  return baseUrl.toString()
}
