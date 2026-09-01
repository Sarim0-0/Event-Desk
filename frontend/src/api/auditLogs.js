import { authenticatedRequest } from './authenticated.js'

export function listAuditLogs({ tokens }) {
  return authenticatedRequest('/audit-logs', { tokens })
}
