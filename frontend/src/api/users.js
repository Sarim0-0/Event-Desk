import { authenticatedRequest } from './authenticated.js'

export function listUsers({ tokens }) {
  return authenticatedRequest('/users', { tokens })
}

export function updateOwnProfile({ tokens, profile }) {
  return authenticatedRequest('/users/me', {
    tokens,
    method: 'PATCH',
    body: profile,
  })
}

export function changeOwnPassword({ tokens, currentPassword, newPassword }) {
  return authenticatedRequest('/users/me/password', {
    tokens,
    method: 'PATCH',
    body: {
      current_password: currentPassword,
      new_password: newPassword,
    },
    shouldRefreshUnauthorized: (error) =>
      error.payload?.detail !== 'The current password is incorrect.',
  })
}

export function changeUserRole({ tokens, userId, role }) {
  return authenticatedRequest(`/users/${userId}/role`, {
    tokens,
    method: 'PATCH',
    body: { role },
  })
}

export function deactivateUser({ tokens, userId }) {
  return authenticatedRequest(`/users/${userId}/deactivate`, {
    tokens,
    method: 'POST',
  })
}
