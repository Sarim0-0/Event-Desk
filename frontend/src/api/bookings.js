import { authenticatedRequest } from './authenticated.js'

export function listBookings({ tokens, page = 1 }) {
  const query = new URLSearchParams({ page: String(page) })

  return authenticatedRequest(`/bookings?${query}`, { tokens })
}

export function listUserBookings({ tokens, userId, page = 1 }) {
  const query = new URLSearchParams({ page: String(page) })

  return authenticatedRequest(`/users/${userId}/bookings?${query}`, {
    tokens,
  })
}

export function createBooking({ tokens, eventId, quantity }) {
  return authenticatedRequest('/bookings', {
    tokens,
    method: 'POST',
    body: { event_id: eventId, quantity },
  })
}

export function cancelBooking({ tokens, bookingId }) {
  return authenticatedRequest(`/bookings/${bookingId}/cancel`, {
    tokens,
    method: 'POST',
  })
}
