import { authenticatedRequest } from './authenticated.js'

export function listUsers({ tokens }) {
  return authenticatedRequest('/users', { tokens })
}
