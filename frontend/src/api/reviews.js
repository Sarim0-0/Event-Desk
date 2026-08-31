import { authenticatedRequest } from './authenticated.js'

export function listEventReviews({ tokens }) {
  return authenticatedRequest('/reviews', { tokens })
}

export function createReview({ tokens, bookingId, rating, comment }) {
  return authenticatedRequest('/reviews', {
    tokens,
    method: 'POST',
    body: { booking_id: bookingId, rating, comment },
  })
}

export function updateReview({ tokens, reviewId, rating, comment }) {
  return authenticatedRequest(`/reviews/${reviewId}`, {
    tokens,
    method: 'PATCH',
    body: { rating, comment },
  })
}

export function deleteReview({ tokens, reviewId }) {
  return authenticatedRequest(`/reviews/${reviewId}`, {
    tokens,
    method: 'DELETE',
  })
}

export function createReviewReply({ tokens, reviewId, body }) {
  return authenticatedRequest(`/reviews/${reviewId}/replies`, {
    tokens,
    method: 'POST',
    body: { body },
  })
}
