import { request } from './auth.js'

export function listEvents({ accessToken, page = 1 }) {
  const query = new URLSearchParams({ page: String(page) })

  return request(`/events?${query}`, { accessToken })
}
