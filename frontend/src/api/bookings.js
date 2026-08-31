import { authenticatedRequest } from './authenticated.js'

export function listBookings({ tokens, page = 1 }) {
  const query = new URLSearchParams({ page: String(page) })

  return authenticatedRequest(`/bookings?${query}`, { tokens })
}

export function createBooking({ tokens, eventId, quantity }) {
  return authenticatedRequest('/bookings', {
    tokens,
    method: 'POST',
    body: { event_id: eventId, quantity },
  })
}
