import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ApiError,
  logIn,
  logOut,
  refreshAccessToken,
  signUp,
} from './api/auth.js'
import {
  cancelEvent,
  createEvent,
  getEventAvailabilitySocketUrl,
  listCategories,
  listDraftEvents,
  listEvents,
  listTags,
  updateEvent,
} from './api/events.js'
import { cancelBooking, createBooking, listBookings } from './api/bookings.js'
import {
  createReview,
  createReviewReply,
  deleteReview,
  listEventReviews,
  updateReview,
} from './api/reviews.js'
import {
  getNotificationSocketUrl,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from './api/notifications.js'
import {
  changeOwnPassword,
  changeUserRole,
  deactivateUser,
  listUsers,
  updateOwnProfile,
} from './api/users.js'
import { listAuditLogs } from './api/auditLogs.js'
import { SessionExpiredError } from './api/authenticated.js'
import {
  clearTokens,
  getAccessTokenClaims,
  getStoredTokens,
  isAccessTokenExpired,
  saveTokens,
  updateAccessToken,
} from './auth/tokenStorage.js'
import './App.css'

const REGISTERABLE_ROLES = [
  {
    value: 'attendee',
    label: 'Attendee',
    description: 'Discover events and reserve your place.',
  },
  {
    value: 'organizer',
    label: 'Organizer',
    description: 'Create events and welcome your audience.',
  },
]

const EMPTY_SIGNUP_FORM = {
  name: '',
  email: '',
  password: '',
  role: 'attendee',
}

function normalizeName(value) {
  return value.trim().split(/\s+/u).filter(Boolean).join(' ')
}

function normalizeEmail(value) {
  return value.trim().toLowerCase()
}

function characterLength(value) {
  return [...value].length
}

function isLowercaseCharacter(character) {
  return (
    character.toLowerCase() === character &&
    character.toUpperCase() !== character
  )
}

function isUppercaseCharacter(character) {
  return (
    character.toUpperCase() === character &&
    character.toLowerCase() !== character
  )
}

function isNumberCharacter(character) {
  return /\p{Number}/u.test(character)
}

function isSpecialCharacter(character) {
  return !/[\p{Letter}\p{Number}\s]/u.test(character)
}

function getPasswordChecks(password) {
  const characters = [...password]

  return [
    {
      key: 'length',
      label: '8–128 characters',
      met: characters.length >= 8 && characters.length <= 128,
    },
    {
      key: 'lowercase',
      label: 'One lowercase letter',
      met: characters.some(isLowercaseCharacter),
    },
    {
      key: 'uppercase',
      label: 'One uppercase letter',
      met: characters.some(isUppercaseCharacter),
    },
    {
      key: 'number',
      label: 'One number',
      met: characters.some(isNumberCharacter),
    },
    {
      key: 'special',
      label: 'One special character',
      met: characters.some(isSpecialCharacter),
    },
  ]
}

function getPasswordStrength(password, checks) {
  if (!password) {
    return { level: 0, label: 'Enter a password', tone: 'empty' }
  }

  const passedChecks = checks.filter((check) => check.met).length

  if (passedChecks <= 2) {
    return { level: 1, label: 'Weak password', tone: 'weak' }
  }

  if (passedChecks === 3) {
    return { level: 2, label: 'Fair password', tone: 'fair' }
  }

  if (passedChecks === 4) {
    return { level: 3, label: 'Almost there', tone: 'good' }
  }

  return { level: 4, label: 'Strong password', tone: 'strong' }
}

function getApiErrors(error, fallbackMessage) {
  if (!(error instanceof ApiError)) {
    return {
      fieldErrors: {},
      message:
        'Unable to reach EventDesk. Check that the API is running and try again.',
    }
  }

  const detail = error.payload?.detail

  if (Array.isArray(detail)) {
    const fieldErrors = {}
    const generalErrors = []

    detail.forEach((issue) => {
      const field = issue.loc?.at(-1)
      const message = String(issue.msg || 'This value is invalid.').replace(
        /^Value error,\s*/i,
        '',
      )

      if (['name', 'email', 'password', 'role'].includes(field)) {
        fieldErrors[field] ??= message
      } else {
        generalErrors.push(message)
      }
    })

    return {
      fieldErrors,
      message: generalErrors.join(' ') || null,
    }
  }

  return {
    fieldErrors: {},
    message: typeof detail === 'string' ? detail : fallbackMessage,
  }
}

function EyeIcon({ hidden }) {
  return hidden ? (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M3 3l18 18M10.6 10.7a2 2 0 002.7 2.7M9.9 4.2A10.7 10.7 0 0112 4c5.5 0 9 5.6 9 5.6a15.8 15.8 0 01-2.3 2.8M6.1 6.1A17.2 17.2 0 003 9.6S6.5 15.2 12 15.2c1 0 2-.2 2.9-.6" />
    </svg>
  ) : (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M3 12s3.5-5.6 9-5.6 9 5.6 9 5.6-3.5 5.6-9 5.6S3 12 3 12z" />
      <circle cx="12" cy="12" r="2.4" />
    </svg>
  )
}

function BrandMark() {
  return (
    <div className="brand" aria-label="EventDesk">
      <span className="brand-mark" aria-hidden="true">
        <span />
        <span />
      </span>
      <span>EventDesk</span>
    </div>
  )
}

function Alert({ children, type = 'error' }) {
  if (!children) return null

  return (
    <div
      className={`alert alert-${type}`}
      role={type === 'error' ? 'alert' : 'status'}
    >
      <span className="alert-icon" aria-hidden="true">
        {type === 'error' ? '!' : '✓'}
      </span>
      <span>{children}</span>
    </div>
  )
}

function FieldError({ id, children }) {
  if (!children) return null

  return (
    <p className="field-error" id={id} role="alert">
      {children}
    </p>
  )
}

function PasswordField({
  value,
  onChange,
  error,
  showStrength = false,
  autoComplete,
  id = 'password',
  name = 'password',
  label = 'Password',
  placeholder,
}) {
  const [passwordVisible, setPasswordVisible] = useState(false)
  const checks = useMemo(() => getPasswordChecks(value), [value])
  const strength = getPasswordStrength(value, checks)
  const errorId = `${id}-error`
  const strengthId = `${id}-strength`
  const describedBy = [
    error ? errorId : null,
    showStrength ? strengthId : null,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className="form-field">
      <label htmlFor={id}>{label}</label>
      <div className={`password-input ${error ? 'input-error' : ''}`}>
        <input
          id={id}
          name={name}
          type={passwordVisible ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          autoComplete={autoComplete}
          maxLength={128}
          aria-invalid={Boolean(error)}
          aria-describedby={describedBy || undefined}
          placeholder={placeholder || (
            showStrength ? 'Create a strong password' : 'Enter your password'
          )}
        />
        <button
          className="visibility-toggle"
          type="button"
          onClick={() => setPasswordVisible((visible) => !visible)}
          aria-label={passwordVisible ? 'Hide password' : 'Show password'}
          aria-pressed={passwordVisible}
        >
          <EyeIcon hidden={passwordVisible} />
        </button>
      </div>
      <FieldError id={errorId}>{error}</FieldError>

      {showStrength && (
        <div className="password-strength" id={strengthId}>
          <div className="strength-heading">
            <span>Password strength</span>
            <strong className={`strength-${strength.tone}`}>
              {strength.label}
            </strong>
          </div>
          <div className="strength-bars" aria-hidden="true">
            {[1, 2, 3, 4].map((level) => (
              <span
                className={
                  level <= strength.level ? `bar-${strength.tone}` : ''
                }
                key={level}
              />
            ))}
          </div>
          <ul className="password-requirements">
            {checks.map((check) => (
              <li
                className={check.met ? 'requirement-met' : ''}
                key={check.key}
              >
                <span aria-hidden="true">{check.met ? '✓' : '•'}</span>
                {check.label}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function SignupForm({ onRegistered, onSwitch }) {
  const [form, setForm] = useState(EMPTY_SIGNUP_FORM)
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  function updateField(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
    setFieldErrors((current) => ({ ...current, [name]: undefined }))
    setFormError(null)
  }

  function validateForm(payload) {
    const errors = {}
    const nameLength = characterLength(payload.name)
    const passwordLength = characterLength(payload.password)
    const passwordChecks = getPasswordChecks(payload.password)

    if (nameLength < 2) {
      errors.name = 'Name must contain at least 2 characters.'
    }
    if (nameLength > 120) {
      errors.name = 'Name must contain at most 120 characters.'
    }

    if (!payload.email) errors.email = 'Email is required.'
    if (characterLength(payload.email) > 320) {
      errors.email = 'Email must contain at most 320 characters.'
    }

    if (passwordLength < 8) {
      errors.password = 'Password must contain at least 8 characters.'
    } else if (passwordLength > 128) {
      errors.password = 'Password must contain at most 128 characters.'
    } else if (passwordChecks.some((check) => !check.met)) {
      const missingRequirements = passwordChecks
        .filter((check) => !check.met && check.key !== 'length')
        .map((check) => check.label.toLowerCase().replace(/^one /, ''))

      errors.password = `Password must contain at least one ${missingRequirements.join(', ')}.`
    }

    if (!REGISTERABLE_ROLES.some((role) => role.value === payload.role)) {
      errors.role = 'Choose either attendee or organizer.'
    }

    return errors
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const payload = {
      name: normalizeName(form.name),
      email: normalizeEmail(form.email),
      password: form.password,
      role: form.role,
    }
    const validationErrors = validateForm(payload)

    if (Object.keys(validationErrors).length > 0) {
      setFieldErrors(validationErrors)
      setFormError('Please correct the highlighted fields and try again.')
      return
    }

    setSubmitting(true)
    setFieldErrors({})
    setFormError(null)

    try {
      const user = await signUp(payload)
      onRegistered(user)
    } catch (error) {
      const apiErrors = getApiErrors(
        error,
        'We could not create your account. Please try again.',
      )
      setFieldErrors(apiErrors.fieldErrors)
      setFormError(apiErrors.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-form-panel">
      <div className="form-heading">
        <p className="eyebrow">Join EventDesk</p>
        <h1>Create your account</h1>
        <p>Start discovering—or creating—events people remember.</p>
      </div>

      <Alert>{formError}</Alert>

      <form onSubmit={handleSubmit} noValidate>
        <div className="form-field">
          <label htmlFor="name">Full name</label>
          <input
            className={fieldErrors.name ? 'input-error' : ''}
            id="name"
            name="name"
            type="text"
            value={form.name}
            onChange={updateField}
            autoComplete="name"
            maxLength={120}
            aria-invalid={Boolean(fieldErrors.name)}
            aria-describedby={fieldErrors.name ? 'name-error' : undefined}
            placeholder="Your full name"
          />
          <FieldError id="name-error">{fieldErrors.name}</FieldError>
        </div>

        <div className="form-field">
          <label htmlFor="email">Email address</label>
          <input
            className={fieldErrors.email ? 'input-error' : ''}
            id="email"
            name="email"
            type="email"
            value={form.email}
            onChange={updateField}
            autoComplete="email"
            maxLength={320}
            aria-invalid={Boolean(fieldErrors.email)}
            aria-describedby={fieldErrors.email ? 'email-error' : undefined}
            placeholder="you@example.com"
          />
          <FieldError id="email-error">{fieldErrors.email}</FieldError>
        </div>

        <PasswordField
          value={form.password}
          onChange={updateField}
          error={fieldErrors.password}
          showStrength
          autoComplete="new-password"
        />

        <fieldset
          className="role-fieldset"
          aria-describedby={fieldErrors.role ? 'role-error' : undefined}
        >
          <legend>I want to join as</legend>
          <div className="role-options">
            {REGISTERABLE_ROLES.map((role) => (
              <label className="role-option" key={role.value}>
                <input
                  type="radio"
                  name="role"
                  value={role.value}
                  checked={form.role === role.value}
                  onChange={updateField}
                />
                <span className="role-radio" aria-hidden="true" />
                <span>
                  <strong>{role.label}</strong>
                  <small>{role.description}</small>
                </span>
              </label>
            ))}
          </div>
          <FieldError id="role-error">{fieldErrors.role}</FieldError>
        </fieldset>

        <button className="primary-button" type="submit" disabled={submitting}>
          {submitting ? <span className="spinner" aria-hidden="true" /> : null}
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <p className="auth-switch">
        Already have an account?{' '}
        <a href="/login" onClick={onSwitch}>
          Log in
        </a>
      </p>
    </div>
  )
}

function LoginForm({
  initialEmail,
  notice,
  noticeType,
  onAuthenticated,
  onSwitch,
}) {
  const [form, setForm] = useState({ email: initialEmail, password: '' })
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  function updateField(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
    setFieldErrors((current) => ({ ...current, [name]: undefined }))
    setFormError(null)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const payload = {
      email: normalizeEmail(form.email),
      password: form.password,
    }
    const errors = {}

    if (!payload.email) errors.email = 'Email is required.'
    if (characterLength(payload.email) > 320) {
      errors.email = 'Email must contain at most 320 characters.'
    }
    if (!payload.password) errors.password = 'Password is required.'
    if (characterLength(payload.password) > 128) {
      errors.password = 'Password must contain at most 128 characters.'
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      setFormError('Please correct the highlighted fields and try again.')
      return
    }

    setSubmitting(true)
    setFieldErrors({})
    setFormError(null)

    try {
      const tokens = await logIn(payload)
      saveTokens(tokens)
      onAuthenticated(tokens, { email: payload.email })
    } catch (error) {
      const apiErrors = getApiErrors(
        error,
        'We could not log you in. Please try again.',
      )
      setFieldErrors(apiErrors.fieldErrors)
      setFormError(apiErrors.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-form-panel login-panel">
      <div className="form-heading">
        <p className="eyebrow">Welcome back</p>
        <h1>Log in to EventDesk</h1>
        <p>Pick up where you left off and make the next event happen.</p>
      </div>

      <Alert type={noticeType}>{notice}</Alert>
      <Alert>{formError}</Alert>

      <form onSubmit={handleSubmit} noValidate>
        <div className="form-field">
          <label htmlFor="email">Email address</label>
          <input
            className={fieldErrors.email ? 'input-error' : ''}
            id="email"
            name="email"
            type="email"
            value={form.email}
            onChange={updateField}
            autoComplete="email"
            maxLength={320}
            aria-invalid={Boolean(fieldErrors.email)}
            aria-describedby={fieldErrors.email ? 'email-error' : undefined}
            placeholder="you@example.com"
          />
          <FieldError id="email-error">{fieldErrors.email}</FieldError>
        </div>

        <PasswordField
          value={form.password}
          onChange={updateField}
          error={fieldErrors.password}
          autoComplete="current-password"
        />

        <button className="primary-button" type="submit" disabled={submitting}>
          {submitting ? <span className="spinner" aria-hidden="true" /> : null}
          {submitting ? 'Logging in…' : 'Log in'}
        </button>
      </form>

      <p className="auth-switch">
        New to EventDesk?{' '}
        <a href="/signup" onClick={onSwitch}>
          Create an account
        </a>
      </p>
    </div>
  )
}

const EVENT_CARD_THEME_COUNT = 6

class UnexpectedEventResponseError extends Error {}

function formatEventDate(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return { day: '--', month: 'TBD', full: 'Date to be announced' }
  }

  return {
    day: new Intl.DateTimeFormat(undefined, { day: '2-digit' }).format(date),
    month: new Intl.DateTimeFormat(undefined, { month: 'short' })
      .format(date)
      .toUpperCase(),
    full: new Intl.DateTimeFormat(undefined, {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(date),
  }
}

function formatEventTime(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Time to be announced'

  return new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)
}

function formatTicketPrice(value) {
  const price = Number(value)
  if (!Number.isFinite(price)) return 'Price unavailable'
  if (price === 0) return 'Free'

  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(price)
}

function validateEventPage(payload) {
  return (
    payload &&
    Array.isArray(payload.items) &&
    Number.isInteger(payload.page) &&
    payload.page >= 1 &&
    payload.page_size === 6 &&
    Number.isInteger(payload.total_items) &&
    payload.total_items >= 0 &&
    Number.isInteger(payload.total_pages) &&
    payload.total_pages >= 0
  )
}

function getEventErrorMessage(error) {
  if (error instanceof ApiError) {
    const detail = error.payload?.detail
    if (typeof detail === 'string') return detail
  }

  if (error instanceof UnexpectedEventResponseError) {
    return 'The event service returned an unexpected response. Please try again.'
  }

  return 'We could not load events. Check your connection and try again.'
}

function EventMetaIcon({ type }) {
  if (type === 'location') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1116 0z" />
        <circle cx="12" cy="10" r="2.5" />
      </svg>
    )
  }

  if (type === 'ticket') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M3 8a2 2 0 002-2h14a2 2 0 002 2v2a2 2 0 010 4v2a2 2 0 01-2 2H5a2 2 0 00-2-2v-2a2 2 0 010-4V8zM13 7v2M13 11v2M13 15v2" />
      </svg>
    )
  }

  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M16 3v4M8 3v4M3 10h18" />
    </svg>
  )
}

function EventCard({ event, onSelect, index, categoryName, isOwned }) {
  const date = formatEventDate(event.event_datetime)
  const ticketsAvailable = Number(event.tickets_available)
  const totalTickets = Number(event.total_tickets)
  const ticketLabel =
    ticketsAvailable === 0
      ? 'Sold out'
      : `${ticketsAvailable} of ${totalTickets} tickets remaining`

  return (
    <button
      className={`event-card ${isOwned ? 'event-card-owned' : ''}`}
      type="button"
      aria-label={`View ${event.title}`}
      title={`View details for ${event.title}`}
      onClick={() => onSelect(event)}
    >
      <div className={`event-card-cover event-theme-${index % EVENT_CARD_THEME_COUNT}`}>
        <span className="event-status">{event.status}</span>
        {isOwned && <span className="event-owner-label">Your event</span>}
        {categoryName && <span className="event-category">{categoryName}</span>}
        <div className="event-date-tile">
          <strong>{date.day}</strong>
          <span>{date.month}</span>
        </div>
        <span className="event-cover-shape event-cover-shape-one" />
        <span className="event-cover-shape event-cover-shape-two" />
      </div>

      <div className="event-card-body">
        <div className="event-card-heading">
          <h2>{event.title}</h2>
          <span className="event-price">{formatTicketPrice(event.ticket_price)}</span>
        </div>
        <p className="event-description">{event.description}</p>

        <div className="event-meta">
          <span>
            <EventMetaIcon type="calendar" />
            {date.full} at {formatEventTime(event.event_datetime)}
          </span>
          <span>
            <EventMetaIcon type="location" />
            {event.venue}
          </span>
        </div>

        <div className="event-card-footer">
          <span className={ticketsAvailable === 0 ? 'tickets-sold-out' : ''}>
            <EventMetaIcon type="ticket" />
            {ticketLabel}
          </span>
          <span className="event-arrow" aria-hidden="true">→</span>
        </div>
      </div>
    </button>
  )
}

function EventCardSkeleton() {
  return (
    <div className="event-card event-card-skeleton" aria-hidden="true">
      <div className="event-card-cover skeleton-block" />
      <div className="event-card-body">
        <span className="skeleton-line skeleton-title" />
        <span className="skeleton-line" />
        <span className="skeleton-line skeleton-short" />
        <div className="skeleton-meta">
          <span className="skeleton-line" />
          <span className="skeleton-line" />
        </div>
      </div>
    </div>
  )
}

function AppIcon({ type }) {
  const paths = {
    events: (
      <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M16 3v4M8 3v4M3 10h18" /></>
    ),
    bookings: (
      <><path d="M3 8a2 2 0 002-2h14a2 2 0 002 2v2a2 2 0 010 4v2a2 2 0 01-2 2H5a2 2 0 00-2-2v-2a2 2 0 010-4V8z" /><path d="M13 7v2M13 11v2M13 15v2" /></>
    ),
    users: (
      <><circle cx="9" cy="8" r="3" /><path d="M3.5 20v-2a5.5 5.5 0 0111 0v2M16 5.5a3 3 0 010 5.5M17 14a5 5 0 013.5 4.8V20" /></>
    ),
    logs: (
      <><path d="M6 3h9l4 4v14H6zM14 3v5h5M9 12h7M9 16h7" /></>
    ),
    bell: (
      <><path d="M18 8a6 6 0 00-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></>
    ),
    notifications: (
      <><path d="M18 8a6 6 0 00-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></>
    ),
    plus: <path d="M12 5v14M5 12h14" />,
    check: <polyline points="20 6 9 17 4 12" />,
    cancel: (
      <><circle cx="12" cy="12" r="9" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" /></>
    ),
    clock: (
      <><circle cx="12" cy="12" r="9" /><polyline points="12 6 12 12 16 14" /></>
    ),
    star: (
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    ),
    reviews: (
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    ),
    reply: (
      <><polyline points="9 17 4 12 9 7" /><path d="M20 18v-2a4 4 0 00-4-4H4" /></>
    ),
  }

  return <svg viewBox="0 0 24 24" aria-hidden="true">{paths[type] || paths.bell}</svg>
}

function NotificationIcon({ type }) {
  const iconMap = {
    booking_confirmed: 'check',
    booking_cancelled: 'cancel',
    event_cancelled: 'cancel',
    event_reminder: 'clock',
    event_reviewed: 'star',
    review_replied: 'reply',
  }
  return <AppIcon type={iconMap[type] || 'bell'} />
}

function ApplicationShell({
  role,
  profile,
  currentPage,
  onNavigate,
  onCreateEvent,
  onOpenProfile,
  onLogout,
  loggingOut,
  unreadNotificationsCount = 0,
  children,
}) {
  const profileInitial = (profile?.name || role).charAt(0).toUpperCase()
  const navigation = [
    { key: 'events', label: 'Events' },
    { key: 'bookings', label: 'Bookings' },
    ...(['organizer', 'admin'].includes(role)
      ? [{ key: 'reviews', label: 'Reviews' }]
      : []),
    ...(role === 'admin'
      ? [
          { key: 'users', label: 'Users' },
          { key: 'logs', label: 'Logs' },
        ]
      : []),
  ]

  return (
    <main className="app-page">
      <header className="app-header">
        <BrandMark />
        <nav className="app-nav" aria-label="Primary navigation">
          {navigation.map((item) => (
            <a
              className={currentPage === item.key ? 'app-nav-active' : ''}
              href={`/${item.key}`}
              onClick={(event) => onNavigate(item.key, event)}
              aria-current={currentPage === item.key ? 'page' : undefined}
              key={item.key}
            >
              <AppIcon type={item.key} />
              {item.label}
            </a>
          ))}
        </nav>
        <div className="app-header-actions">
          {['organizer', 'admin'].includes(role) && (
            <button
              className="create-event-button"
              type="button"
              onClick={onCreateEvent}
            >
              <AppIcon type="plus" />
              Create event
            </button>
          )}
          <button
            className={`header-icon-button ${currentPage === 'notifications' ? 'header-icon-button-active' : ''}`}
            type="button"
            onClick={(event) => onNavigate('notifications', event)}
            aria-label={
              unreadNotificationsCount > 0
                ? `Notifications (${unreadNotificationsCount} unread)`
                : 'Notifications'
            }
            title="Notifications"
            aria-current={currentPage === 'notifications' ? 'page' : undefined}
          >
            <AppIcon type="bell" />
            {unreadNotificationsCount > 0 && (
              <span className="notification-badge" aria-hidden="true">
                {unreadNotificationsCount > 99 ? '99+' : unreadNotificationsCount}
              </span>
            )}
          </button>
          <button
            className="logout-button"
            type="button"
            onClick={onLogout}
            disabled={loggingOut}
          >
            {loggingOut ? 'Logging out...' : 'Log out'}
          </button>
          <button
            className="profile-button"
            type="button"
            onClick={onOpenProfile}
            aria-label="Open profile settings"
            title="Profile settings"
          >
            {profileInitial}
          </button>
        </div>
      </header>
      {children}
    </main>
  )
}

function Pagination({ pageData, loading, onChange, label }) {
  const first = pageData.total_items
    ? (pageData.page - 1) * pageData.page_size + 1
    : 0
  const last = pageData.total_items
    ? Math.min(pageData.page * pageData.page_size, pageData.total_items)
    : 0

  return (
    <nav className="pagination" aria-label={`${label} pages`}>
      <p>Showing {first}-{last} of {pageData.total_items}</p>
      <div className="pagination-controls">
        <button
          type="button"
          onClick={() => onChange(pageData.page - 1)}
          disabled={loading || pageData.page <= 1}
          aria-label="Previous page"
        >
          ←
        </button>
        <span>Page <strong>{pageData.page}</strong> of {pageData.total_pages}</span>
        <button
          type="button"
          onClick={() => onChange(pageData.page + 1)}
          disabled={loading || pageData.page >= pageData.total_pages}
          aria-label="Next page"
        >
          →
        </button>
      </div>
    </nav>
  )
}

function ResourceError({ title, message, onRetry }) {
  return (
    <div className="events-state events-error" role="alert">
      <span className="state-icon" aria-hidden="true">!</span>
      <h2>{title}</h2>
      <p>{message}</p>
      <button type="button" onClick={onRetry}>Try again</button>
    </div>
  )
}

function getResourceErrorMessage(error, resource) {
  if (error instanceof ApiError && typeof error.payload?.detail === 'string') {
    return error.payload.detail
  }
  return `We could not load ${resource}. Check your connection and try again.`
}

function isMetadataList(value) {
  return (
    Array.isArray(value) &&
    value.every(
      (item) =>
        typeof item?.id === 'string' &&
        typeof item?.name === 'string' &&
        item.name.length > 0,
    )
  )
}

function useEventMetadata({
  enabled,
  tokens,
  onSessionExpired,
  onTokensChanged,
}) {
  const [categories, setCategories] = useState([])
  const [tags, setTags] = useState([])
  const [loading, setLoading] = useState(enabled)
  const [error, setError] = useState(null)
  const [retryCount, setRetryCount] = useState(0)
  const tokensRef = useRef(tokens)

  useEffect(() => {
    tokensRef.current = tokens
  }, [tokens])

  useEffect(() => {
    if (!enabled) return undefined

    let cancelled = false
    async function loadMetadata() {
      setLoading(true)
      setError(null)
      try {
        const categoryResult = await listCategories({
          tokens: tokensRef.current,
        })
        const tagResult = await listTags({ tokens: categoryResult.tokens })
        if (
          !isMetadataList(categoryResult.data) ||
          !isMetadataList(tagResult.data)
        ) {
          throw new Error('Invalid event metadata response.')
        }
        if (!cancelled) {
          setCategories(categoryResult.data)
          setTags(tagResult.data)
          setLoading(false)
          if (tagResult.tokens.access_token !== tokensRef.current.access_token) {
            tokensRef.current = tagResult.tokens
            onTokensChanged(tagResult.tokens)
          }
        }
      } catch (requestError) {
        if (cancelled) return
        if (requestError instanceof SessionExpiredError) {
          onSessionExpired(requestError.message)
          return
        }
        setError(getResourceErrorMessage(requestError, 'categories and tags'))
        setLoading(false)
      }
    }

    loadMetadata()
    return () => { cancelled = true }
  }, [enabled, onSessionExpired, onTokensChanged, retryCount])

  return {
    categories,
    tags,
    loading,
    error,
    retry: () => setRetryCount((count) => count + 1),
  }
}

function getFormApiErrors(error, fields, fallbackMessage) {
  if (!(error instanceof ApiError)) {
    return {
      fieldErrors: {},
      message: 'Unable to reach EventDesk. Check that the API is running and try again.',
    }
  }

  const detail = error.payload?.detail
  if (!Array.isArray(detail)) {
    return {
      fieldErrors: {},
      message: typeof detail === 'string' ? detail : fallbackMessage,
    }
  }

  const fieldErrors = {}
  const generalErrors = []
  detail.forEach((issue) => {
    const field = issue.loc?.at(-1)
    const message = String(issue.msg || 'This value is invalid.').replace(
      /^Value error,\s*/i,
      '',
    )
    if (fields.includes(field)) fieldErrors[field] ??= message
    else generalErrors.push(message)
  })

  return {
    fieldErrors,
    message: generalErrors.join(' ') || null,
  }
}

function Modal({ titleId, onClose, className = '', children }) {
  useEffect(() => {
    function closeOnEscape(event) {
      if (event.key === 'Escape') onClose()
    }
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', closeOnEscape)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', closeOnEscape)
    }
  }, [onClose])

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <section
        className={`modal-panel ${className}`.trim()}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <button
          className="modal-close"
          type="button"
          onClick={onClose}
          aria-label="Close dialog"
        >
          ×
        </button>
        {children}
      </section>
    </div>
  )
}

function ConfirmationModal({
  title,
  description,
  confirmLabel,
  cancelLabel = 'Cancel',
  onClose,
  onConfirm,
  submitting = false,
}) {
  const titleId = 'confirmation-modal-title'
  const closeWhenIdle = () => {
    if (!submitting) onClose()
  }

  return (
    <Modal titleId={titleId} onClose={closeWhenIdle} className="confirmation-modal">
      <div className="confirmation-modal-icon" aria-hidden="true">!</div>
      <div className="modal-heading confirmation-modal-heading">
        <p className="eyebrow">Please confirm</p>
        <h1 id={titleId}>{title}</h1>
        <p>{description}</p>
      </div>
      <div className="modal-actions confirmation-modal-actions">
        <button className="secondary-button" type="button" onClick={closeWhenIdle} disabled={submitting}>
          {cancelLabel}
        </button>
        <button className="destructive-button" type="button" onClick={onConfirm} disabled={submitting}>
          {submitting && <span className="spinner" aria-hidden="true" />}
          {submitting ? 'Cancelling…' : confirmLabel}
        </button>
      </div>
    </Modal>
  )
}

const EMPTY_EVENT_FORM = {
  title: '',
  description: '',
  venue: '',
  event_datetime: '',
  ticket_price: '',
  total_tickets: '',
  category_id: '',
  tag_ids: [],
}

function CreateEventModal({
  tokens,
  onClose,
  onCreated,
  onSessionExpired,
  onTokensChanged,
  metadata,
}) {
  const [form, setForm] = useState(EMPTY_EVENT_FORM)
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  function updateField(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
    setFieldErrors((current) => ({ ...current, [name]: undefined }))
    setFormError(null)
  }

  function toggleTag(tagId) {
    setForm((current) => ({
      ...current,
      tag_ids: current.tag_ids.includes(tagId)
        ? current.tag_ids.filter((id) => id !== tagId)
        : [...current.tag_ids, tagId],
    }))
    setFieldErrors((current) => ({ ...current, tag_ids: undefined }))
    setFormError(null)
  }

  function validate() {
    const errors = {}
    const eventDate = new Date(form.event_datetime)
    const ticketPrice = Number(form.ticket_price)
    const totalTickets = Number(form.total_tickets)

    if (!form.title.trim()) errors.title = 'Event name is required.'
    else if (characterLength(form.title.trim()) > 255) {
      errors.title = 'Event name must contain at most 255 characters.'
    }
    if (!form.description.trim()) errors.description = 'Description is required.'
    if (!form.venue.trim()) errors.venue = 'Venue is required.'
    else if (characterLength(form.venue.trim()) > 255) {
      errors.venue = 'Venue must contain at most 255 characters.'
    }
    if (!form.event_datetime || Number.isNaN(eventDate.getTime())) {
      errors.event_datetime = 'Choose a valid event date and time.'
    } else if (eventDate <= new Date()) {
      errors.event_datetime = 'Event date and time must be in the future.'
    }
    if (form.ticket_price === '' || !Number.isFinite(ticketPrice) || ticketPrice < 0) {
      errors.ticket_price = 'Enter a ticket price of 0 or more.'
    } else if (!/^\d+(?:\.\d{1,2})?$/.test(form.ticket_price)) {
      errors.ticket_price = 'Ticket price can have at most two decimal places.'
    }
    if (!Number.isInteger(totalTickets) || totalTickets < 1) {
      errors.total_tickets = 'Enter at least one ticket.'
    }
    return errors
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const errors = validate()
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      setFormError('Please correct the highlighted fields and try again.')
      return
    }

    setSubmitting(true)
    setFieldErrors({})
    setFormError(null)
    try {
      const result = await createEvent({
        tokens,
        event: {
          title: form.title.trim(),
          description: form.description.trim(),
          venue: form.venue.trim(),
          event_datetime: new Date(form.event_datetime).toISOString(),
          ticket_price: Number(form.ticket_price),
          total_tickets: Number(form.total_tickets),
          category_id: form.category_id || null,
          tag_ids: form.tag_ids,
          status: 'published',
        },
      })
      if (result.tokens.access_token !== tokens.access_token) {
        onTokensChanged(result.tokens)
      }
      onCreated(result.data)
    } catch (error) {
      if (error instanceof SessionExpiredError) {
        onSessionExpired(error.message)
        return
      }
      const apiErrors = getFormApiErrors(
        error,
        Object.keys(EMPTY_EVENT_FORM),
        'We could not create the event. Please try again.',
      )
      setFieldErrors(apiErrors.fieldErrors)
      setFormError(apiErrors.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal titleId="create-event-title" onClose={onClose} className="form-modal">
      <div className="modal-heading">
        <p className="eyebrow">New experience</p>
        <h1 id="create-event-title">Create an event</h1>
        <p>Your event will be published and shown in the events grid immediately.</p>
      </div>
      <Alert>{formError}</Alert>
      {metadata.error && (
        <div className="metadata-inline-error" role="alert">
          <span>{metadata.error}</span>
          <button type="button" onClick={metadata.retry}>Try again</button>
        </div>
      )}
      <form className="event-form" onSubmit={handleSubmit} noValidate>
        <div className="form-field event-form-wide">
          <label htmlFor="event-title">Event name</label>
          <input id="event-title" name="title" value={form.title} onChange={updateField} maxLength={255} className={fieldErrors.title ? 'input-error' : ''} placeholder="e.g. Product Design Meetup" />
          <FieldError id="event-title-error">{fieldErrors.title}</FieldError>
        </div>
        <div className="form-field event-form-wide">
          <label htmlFor="event-description">Description</label>
          <textarea id="event-description" name="description" value={form.description} onChange={updateField} className={fieldErrors.description ? 'input-error' : ''} rows="4" placeholder="What should attendees know?" />
          <FieldError id="event-description-error">{fieldErrors.description}</FieldError>
        </div>
        <div className="form-field event-form-wide">
          <label htmlFor="event-venue">Venue</label>
          <input id="event-venue" name="venue" value={form.venue} onChange={updateField} maxLength={255} className={fieldErrors.venue ? 'input-error' : ''} placeholder="Venue name and location" />
          <FieldError id="event-venue-error">{fieldErrors.venue}</FieldError>
        </div>
        <div className="form-field">
          <label htmlFor="event-category">Category <span className="optional-label">Optional</span></label>
          <select id="event-category" name="category_id" value={form.category_id} onChange={updateField} disabled={metadata.loading}>
            <option value="">No category</option>
            {metadata.categories.map((category) => (
              <option value={category.id} key={category.id}>{category.name}</option>
            ))}
          </select>
          <FieldError id="event-category-error">{fieldErrors.category_id}</FieldError>
        </div>
        <div className="form-field">
          <label htmlFor="event-datetime">Date and time</label>
          <input id="event-datetime" name="event_datetime" type="datetime-local" value={form.event_datetime} onChange={updateField} className={fieldErrors.event_datetime ? 'input-error' : ''} />
          <FieldError id="event-datetime-error">{fieldErrors.event_datetime}</FieldError>
        </div>
        <div className="form-field">
          <label htmlFor="event-tickets">Total tickets</label>
          <input id="event-tickets" name="total_tickets" type="number" min="1" step="1" value={form.total_tickets} onChange={updateField} className={fieldErrors.total_tickets ? 'input-error' : ''} placeholder="100" />
          <FieldError id="event-tickets-error">{fieldErrors.total_tickets}</FieldError>
        </div>
        <div className="form-field">
          <label htmlFor="event-price">Price per ticket</label>
          <input id="event-price" name="ticket_price" type="number" min="0" step="0.01" value={form.ticket_price} onChange={updateField} className={fieldErrors.ticket_price ? 'input-error' : ''} placeholder="0.00" />
          <FieldError id="event-price-error">{fieldErrors.ticket_price}</FieldError>
        </div>
        <fieldset className="event-tag-fieldset event-form-wide">
          <legend>Tags <span className="optional-label">Optional</span></legend>
          {metadata.loading ? (
            <p className="metadata-help">Loading tags…</p>
          ) : metadata.tags.length === 0 ? (
            <p className="metadata-help">No tags are available.</p>
          ) : (
            <div className="tag-options">
              {metadata.tags.map((tag) => (
                <button
                  className={form.tag_ids.includes(tag.id) ? 'tag-option-selected' : ''}
                  type="button"
                  onClick={() => toggleTag(tag.id)}
                  aria-pressed={form.tag_ids.includes(tag.id)}
                  key={tag.id}
                >
                  {tag.name}
                </button>
              ))}
            </div>
          )}
          <FieldError id="event-tags-error">{fieldErrors.tag_ids}</FieldError>
        </fieldset>
        <div className="event-publish-note event-form-wide">
          <strong>Published immediately</strong>
          <span>The event will be visible in the event grid and its selected filters.</span>
        </div>
        <div className="modal-actions event-form-wide">
          <button className="secondary-button" type="button" onClick={onClose} disabled={submitting}>Cancel</button>
          <button className="primary-button" type="submit" disabled={submitting}>
            {submitting && <span className="spinner" aria-hidden="true" />}
            {submitting ? 'Creating event…' : 'Create event'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

function toDateTimeLocalInput(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''

  const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
  return localDate.toISOString().slice(0, 16)
}

function EditEventModal({
  event,
  tokens,
  onClose,
  onUpdated,
  onCancelled,
  onSessionExpired,
  onTokensChanged,
  metadata,
}) {
  const [form, setForm] = useState(() => ({
    title: event.title,
    description: event.description,
    venue: event.venue,
    event_datetime: toDateTimeLocalInput(event.event_datetime),
    ticket_price: String(event.ticket_price),
    total_tickets: String(event.total_tickets),
    category_id: event.category_id || '',
    tag_ids: [...event.tag_ids],
    status: event.status,
  }))
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [action, setAction] = useState(null)

  function updateField(changeEvent) {
    const { name, value } = changeEvent.target
    setForm((current) => ({ ...current, [name]: value }))
    setFieldErrors((current) => ({ ...current, [name]: undefined }))
    setFormError(null)
  }

  function toggleTag(tagId) {
    setForm((current) => ({
      ...current,
      tag_ids: current.tag_ids.includes(tagId)
        ? current.tag_ids.filter((id) => id !== tagId)
        : [...current.tag_ids, tagId],
    }))
    setFieldErrors((current) => ({ ...current, tag_ids: undefined }))
    setFormError(null)
  }

  function validate() {
    const errors = {}
    const eventDate = new Date(form.event_datetime)
    const ticketPrice = Number(form.ticket_price)
    const totalTickets = Number(form.total_tickets)

    if (!form.title.trim()) errors.title = 'Event name is required.'
    else if (characterLength(form.title.trim()) > 255) {
      errors.title = 'Event name must contain at most 255 characters.'
    }
    if (!form.description.trim()) errors.description = 'Description is required.'
    if (!form.venue.trim()) errors.venue = 'Venue is required.'
    else if (characterLength(form.venue.trim()) > 255) {
      errors.venue = 'Venue must contain at most 255 characters.'
    }
    if (!form.event_datetime || Number.isNaN(eventDate.getTime())) {
      errors.event_datetime = 'Choose a valid event date and time.'
    } else if (eventDate <= new Date()) {
      errors.event_datetime = 'Event date and time must be in the future.'
    }
    if (form.ticket_price === '' || !Number.isFinite(ticketPrice) || ticketPrice < 0) {
      errors.ticket_price = 'Enter a ticket price of 0 or more.'
    } else if (!/^\d+(?:\.\d{1,2})?$/.test(form.ticket_price)) {
      errors.ticket_price = 'Ticket price can have at most two decimal places.'
    }
    if (!Number.isInteger(totalTickets) || totalTickets < 1) {
      errors.total_tickets = 'Enter at least one ticket.'
    }
    if (!['draft', 'published'].includes(form.status)) {
      errors.status = 'Choose either draft or published.'
    }
    return errors
  }

  async function handleSubmit(submitEvent) {
    submitEvent.preventDefault()
    const errors = validate()
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      setFormError('Please correct the highlighted fields and try again.')
      return
    }

    setAction('saving')
    setFieldErrors({})
    setFormError(null)
    try {
      const result = await updateEvent({
        tokens,
        eventId: event.id,
        event: {
          title: form.title.trim(),
          description: form.description.trim(),
          venue: form.venue.trim(),
          event_datetime: new Date(form.event_datetime).toISOString(),
          ticket_price: Number(form.ticket_price),
          total_tickets: Number(form.total_tickets),
          category_id: form.category_id || null,
          tag_ids: form.tag_ids,
          status: form.status,
        },
      })
      if (result.tokens.access_token !== tokens.access_token) {
        onTokensChanged(result.tokens)
      }
      onUpdated(result.data)
    } catch (error) {
      if (error instanceof SessionExpiredError) {
        onSessionExpired(error.message)
        return
      }
      const apiErrors = getFormApiErrors(
        error,
        [...Object.keys(EMPTY_EVENT_FORM), 'status'],
        'We could not update the event. Please try again.',
      )
      setFieldErrors(apiErrors.fieldErrors)
      setFormError(apiErrors.message)
    } finally {
      setAction(null)
    }
  }

  async function handleCancelEvent() {
    if (action) return

    setAction('cancelling')
    setFieldErrors({})
    setFormError(null)
    try {
      const result = await cancelEvent({ tokens, eventId: event.id })
      if (result.tokens.access_token !== tokens.access_token) {
        onTokensChanged(result.tokens)
      }
      onCancelled(result.data)
    } catch (error) {
      if (error instanceof SessionExpiredError) {
        onSessionExpired(error.message)
        return
      }
      setFormError(
        getResourceErrorMessage(error, 'the event cancellation'),
      )
    } finally {
      setAction(null)
    }
  }

  return (
    <Modal titleId="edit-event-title" onClose={onClose} className="form-modal">
      <div className="modal-heading">
        <p className="eyebrow">Your event</p>
        <h1 id="edit-event-title">Edit event</h1>
        <p>Update the details below, or cancel this event for all attendees.</p>
      </div>
      <Alert>{formError}</Alert>
      {metadata.error && (
        <div className="metadata-inline-error" role="alert">
          <span>{metadata.error}</span>
          <button type="button" onClick={metadata.retry}>Try again</button>
        </div>
      )}
      <form className="event-form" onSubmit={handleSubmit} noValidate>
        <div className="form-field event-form-wide">
          <label htmlFor="edit-event-title-input">Event name</label>
          <input id="edit-event-title-input" name="title" value={form.title} onChange={updateField} maxLength={255} className={fieldErrors.title ? 'input-error' : ''} />
          <FieldError id="edit-event-title-error">{fieldErrors.title}</FieldError>
        </div>
        <div className="form-field event-form-wide">
          <label htmlFor="edit-event-description">Description</label>
          <textarea id="edit-event-description" name="description" value={form.description} onChange={updateField} className={fieldErrors.description ? 'input-error' : ''} rows="4" />
          <FieldError id="edit-event-description-error">{fieldErrors.description}</FieldError>
        </div>
        <div className="form-field event-form-wide">
          <label htmlFor="edit-event-venue">Venue</label>
          <input id="edit-event-venue" name="venue" value={form.venue} onChange={updateField} maxLength={255} className={fieldErrors.venue ? 'input-error' : ''} />
          <FieldError id="edit-event-venue-error">{fieldErrors.venue}</FieldError>
        </div>
        <div className="form-field">
          <label htmlFor="edit-event-category">Category <span className="optional-label">Optional</span></label>
          <select id="edit-event-category" name="category_id" value={form.category_id} onChange={updateField} disabled={metadata.loading}>
            <option value="">No category</option>
            {metadata.categories.map((category) => (
              <option value={category.id} key={category.id}>{category.name}</option>
            ))}
          </select>
          <FieldError id="edit-event-category-error">{fieldErrors.category_id}</FieldError>
        </div>
        <div className="form-field">
          <label htmlFor="edit-event-datetime">Date and time</label>
          <input id="edit-event-datetime" name="event_datetime" type="datetime-local" value={form.event_datetime} onChange={updateField} className={fieldErrors.event_datetime ? 'input-error' : ''} />
          <FieldError id="edit-event-datetime-error">{fieldErrors.event_datetime}</FieldError>
        </div>
        <div className="form-field">
          <label htmlFor="edit-event-tickets">Total tickets</label>
          <input id="edit-event-tickets" name="total_tickets" type="number" min="1" step="1" value={form.total_tickets} onChange={updateField} className={fieldErrors.total_tickets ? 'input-error' : ''} />
          <FieldError id="edit-event-tickets-error">{fieldErrors.total_tickets}</FieldError>
        </div>
        <div className="form-field">
          <label htmlFor="edit-event-price">Price per ticket</label>
          <input id="edit-event-price" name="ticket_price" type="number" min="0" step="0.01" value={form.ticket_price} onChange={updateField} className={fieldErrors.ticket_price ? 'input-error' : ''} />
          <FieldError id="edit-event-price-error">{fieldErrors.ticket_price}</FieldError>
        </div>
        <div className="form-field">
          <label htmlFor="edit-event-status">Status</label>
          <select id="edit-event-status" name="status" value={form.status} onChange={updateField}>
            <option value="draft">Draft</option>
            <option value="published">Published</option>
          </select>
          <FieldError id="edit-event-status-error">{fieldErrors.status}</FieldError>
        </div>
        <fieldset className="event-tag-fieldset event-form-wide">
          <legend>Tags <span className="optional-label">Optional</span></legend>
          {metadata.loading ? (
            <p className="metadata-help">Loading tagsâ€¦</p>
          ) : metadata.tags.length === 0 ? (
            <p className="metadata-help">No tags are available.</p>
          ) : (
            <div className="tag-options">
              {metadata.tags.map((tag) => (
                <button
                  className={form.tag_ids.includes(tag.id) ? 'tag-option-selected' : ''}
                  type="button"
                  onClick={() => toggleTag(tag.id)}
                  aria-pressed={form.tag_ids.includes(tag.id)}
                  key={tag.id}
                >
                  {tag.name}
                </button>
              ))}
            </div>
          )}
          <FieldError id="edit-event-tags-error">{fieldErrors.tag_ids}</FieldError>
        </fieldset>
        <div className="modal-actions event-form-wide edit-event-actions">
          <button className="destructive-button" type="button" onClick={handleCancelEvent} disabled={Boolean(action)}>
            {action === 'cancelling' ? 'Cancelling event…' : 'Cancel event'}
          </button>
          <button className="secondary-button" type="button" onClick={onClose} disabled={Boolean(action)}>Discard changes</button>
          <button className="primary-button" type="submit" disabled={Boolean(action)}>
            {action === 'saving' && <span className="spinner" aria-hidden="true" />}
            {action === 'saving' ? 'Saving changes…' : 'Save changes'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

function EventDetailsModal({
  event,
  tokens,
  onClose,
  onBooked,
  onEdit,
  onCancelled,
  onSessionExpired,
  onTokensChanged,
  categoryName,
  tagNames,
  canEdit,
  canCancel,
}) {
  const [showBooking, setShowBooking] = useState(false)
  const [quantity, setQuantity] = useState('1')
  const [fieldError, setFieldError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [confirmation, setConfirmation] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const date = formatEventDate(event.event_datetime)
  const available = Number(event.tickets_available)
  const total = Number(event.total_tickets)
  const requestedQuantity = Number(quantity)
  const ticketPrice = Number(event.ticket_price)
  const bookingTotal = Number.isInteger(requestedQuantity)
    ? ticketPrice * requestedQuantity
    : 0
  const isUpcoming = new Date(event.event_datetime) > new Date()
  const isBookable = event.status === 'published' && isUpcoming

  async function handleBooking(eventSubmit) {
    eventSubmit.preventDefault()
    if (
      !Number.isInteger(requestedQuantity) ||
      requestedQuantity < 1 ||
      requestedQuantity > available
    ) {
      setFieldError(`Choose between 1 and ${available} ticket${available === 1 ? '' : 's'}.`)
      return
    }

    setSubmitting(true)
    setFieldError(null)
    setFormError(null)
    setConfirmation(null)
    try {
      const result = await createBooking({
        tokens,
        eventId: event.id,
        quantity: requestedQuantity,
      })
      if (result.tokens.access_token !== tokens.access_token) {
        onTokensChanged(result.tokens)
      }
      setConfirmation(
        `${result.data.quantity} ticket${result.data.quantity === 1 ? '' : 's'} booked successfully.`,
      )
      setShowBooking(false)
      onBooked(
        result.data,
        Math.max(0, available - Number(result.data.quantity)),
      )
    } catch (error) {
      if (error instanceof SessionExpiredError) {
        onSessionExpired(error.message)
        return
      }
      const apiErrors = getFormApiErrors(
        error,
        ['quantity'],
        'We could not complete your booking. Please try again.',
      )
      setFieldError(apiErrors.fieldErrors.quantity)
      setFormError(apiErrors.message)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleCancelEvent() {
    if (cancelling || submitting) return

    setCancelling(true)
    setFormError(null)
    try {
      const result = await cancelEvent({ tokens, eventId: event.id })
      if (result.tokens.access_token !== tokens.access_token) {
        onTokensChanged(result.tokens)
      }
      onCancelled(result.data)
    } catch (error) {
      if (error instanceof SessionExpiredError) {
        onSessionExpired(error.message)
        return
      }
      setFormError(getResourceErrorMessage(error, 'the event cancellation'))
    } finally {
      setCancelling(false)
    }
  }

  return (
    <Modal titleId="event-detail-title" onClose={onClose} className="event-detail-modal">
      <div className="event-detail-cover">
        <span className="event-status">{event.status}</span>
        <div className="event-date-tile">
          <strong>{date.day}</strong>
          <span>{date.month}</span>
        </div>
        <span className="event-cover-shape event-cover-shape-one" />
        <span className="event-cover-shape event-cover-shape-two" />
      </div>
      <div className="event-detail-content">
        <div className="event-detail-heading">
          <div>
            <p className="eyebrow">Event details</p>
            <h1 id="event-detail-title">{event.title}</h1>
          </div>
          <strong className="event-detail-price">
            {formatTicketPrice(event.ticket_price)}
            {ticketPrice > 0 && <small> per ticket</small>}
          </strong>
        </div>

        <div className="event-detail-facts">
          <span><EventMetaIcon type="calendar" /><strong>{date.full}</strong><small>{formatEventTime(event.event_datetime)}</small></span>
          <span><EventMetaIcon type="location" /><strong>{event.venue}</strong><small>Venue</small></span>
          <span><EventMetaIcon type="ticket" /><strong>{available} of {total}</strong><small>Tickets remaining</small></span>
        </div>

        <div className="event-detail-description">
          <h2>About this event</h2>
          <p>{event.description}</p>
          {(categoryName || tagNames.length > 0) && (
            <div className="event-detail-taxonomy">
              {categoryName && <span>{categoryName}</span>}
              {tagNames.map((tagName) => <span key={tagName}>#{tagName}</span>)}
            </div>
          )}
        </div>

        <Alert type="success">{confirmation}</Alert>
        <Alert>{formError}</Alert>

        {showBooking ? (
          <form className="booking-form" onSubmit={handleBooking} noValidate>
            <div>
              <label htmlFor="booking-quantity">Number of tickets</label>
              <div className={`quantity-control ${fieldError ? 'input-error' : ''}`}>
                <button type="button" onClick={() => setQuantity(String(Math.max(1, requestedQuantity - 1 || 1)))} aria-label="Decrease ticket quantity">−</button>
                <input id="booking-quantity" name="quantity" type="number" min="1" max={available} step="1" value={quantity} onChange={(changeEvent) => { setQuantity(changeEvent.target.value); setFieldError(null); setFormError(null) }} />
                <button type="button" onClick={() => setQuantity(String(Math.min(available, (requestedQuantity || 0) + 1)))} aria-label="Increase ticket quantity">+</button>
              </div>
              <FieldError id="booking-quantity-error">{fieldError}</FieldError>
            </div>
            <div className="booking-total">
              <span>Total</span>
              <strong>{formatTicketPrice(bookingTotal)}</strong>
            </div>
            <div className="booking-form-actions">
              <button className="secondary-button" type="button" onClick={() => setShowBooking(false)} disabled={submitting}>Back</button>
              <button className="primary-button" type="submit" disabled={submitting || available === 0 || !isBookable}>
                {submitting && <span className="spinner" aria-hidden="true" />}
                {submitting ? 'Booking…' : 'Confirm booking'}
              </button>
            </div>
          </form>
        ) : canEdit ? (
          <div className="event-detail-actions">
            <p>You created this event. Manage its details or cancel it from the editor.</p>
            <button className="primary-button" type="button" onClick={onEdit}>
              Edit event
            </button>
          </div>
        ) : (
          <div className="event-detail-actions">
            <p>
              {!isBookable
                ? 'This event is not currently available for booking.'
                : available === 0
                  ? 'This event is sold out.'
                  : `${available} ticket${available === 1 ? '' : 's'} currently available.`}
            </p>
            <div className="event-detail-buttons">
              <button className="primary-button" type="button" onClick={() => { setShowBooking(true); setConfirmation(null) }} disabled={!isBookable || available === 0 || Boolean(confirmation) || cancelling}>
                {confirmation ? 'Booking confirmed' : !isBookable ? 'Unavailable' : available === 0 ? 'Sold out' : 'Book event'}
              </button>
              {canCancel && (
                <button className="destructive-button" type="button" onClick={handleCancelEvent} disabled={cancelling || submitting}>
                  {cancelling ? 'Cancelling…' : 'Cancel event'}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </Modal>
  )
}

function useAuthenticatedWebSocket({
  enabled = true,
  tokens,
  getSocketUrl,
  onMessage,
  onSessionExpired,
  onTokensChanged,
}) {
  const tokensRef = useRef(tokens)
  const getSocketUrlRef = useRef(getSocketUrl)
  const onMessageRef = useRef(onMessage)
  const onSessionExpiredRef = useRef(onSessionExpired)
  const onTokensChangedRef = useRef(onTokensChanged)
  const handshakeRefreshAttemptedRef = useRef(false)
  const accessToken = tokens?.access_token
  const refreshToken = tokens?.refresh_token

  useEffect(() => {
    tokensRef.current = tokens
    getSocketUrlRef.current = getSocketUrl
    onMessageRef.current = onMessage
    onSessionExpiredRef.current = onSessionExpired
    onTokensChangedRef.current = onTokensChanged
  }, [tokens, getSocketUrl, onMessage, onSessionExpired, onTokensChanged])

  useEffect(() => {
    handshakeRefreshAttemptedRef.current = false
  }, [refreshToken])

  useEffect(() => {
    if (!enabled || !accessToken) return undefined

    let socket = null
    let reconnectTimer = null
    let heartbeatTimer = null
    let stopped = false
    let retryAttempt = 0

    function scheduleReconnect() {
      if (stopped || reconnectTimer) return
      retryAttempt += 1
      const delay = Math.min(
        2000 * 1.5 ** Math.min(retryAttempt, 5),
        15000,
      )
      reconnectTimer = window.setTimeout(() => {
        reconnectTimer = null
        connect()
      }, delay)
    }

    async function refreshSocketToken() {
      try {
        const refreshed = await refreshAccessToken(
          tokensRef.current.refresh_token,
        )
        const nextTokens = updateAccessToken(refreshed.access_token)
        if (!nextTokens) throw new SessionExpiredError()

        tokensRef.current = nextTokens
        onTokensChangedRef.current?.(nextTokens)
        return true
      } catch (error) {
        if (
          error instanceof SessionExpiredError ||
          (error instanceof ApiError && [401, 403].includes(error.status))
        ) {
          stopped = true
          onSessionExpiredRef.current?.(
            error instanceof ApiError && typeof error.payload?.detail === 'string'
              ? error.payload.detail
              : undefined,
          )
          return false
        }

        scheduleReconnect()
        return false
      }
    }

    async function connect() {
      if (stopped) return

      if (isAccessTokenExpired(tokensRef.current.access_token)) {
        await refreshSocketToken()
        return
      }

      let opened = false
      socket = new WebSocket(
        getSocketUrlRef.current(tokensRef.current.access_token),
      )

      socket.addEventListener('open', () => {
        opened = true
        retryAttempt = 0
        handshakeRefreshAttemptedRef.current = false
        heartbeatTimer = window.setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) socket.send('keepalive')
        }, 30000)
      })

      socket.addEventListener('message', (message) => {
        try {
          onMessageRef.current?.(JSON.parse(message.data))
        } catch {
          // Ignore messages that are not valid JSON.
        }
      })

      socket.addEventListener('close', async () => {
        if (heartbeatTimer) {
          window.clearInterval(heartbeatTimer)
          heartbeatTimer = null
        }
        if (stopped) return

        const needsTokenRefresh =
          isAccessTokenExpired(tokensRef.current.access_token) ||
          (!opened && !handshakeRefreshAttemptedRef.current)
        if (needsTokenRefresh) {
          handshakeRefreshAttemptedRef.current = true
          await refreshSocketToken()
          return
        }

        scheduleReconnect()
      })
    }

    connect()
    return () => {
      stopped = true
      if (reconnectTimer) window.clearTimeout(reconnectTimer)
      if (heartbeatTimer) window.clearInterval(heartbeatTimer)
      socket?.close()
    }
  }, [accessToken, enabled])
}

function useEventAvailability({
  tokens,
  onAvailabilityUpdate,
  onSessionExpired,
  onTokensChanged,
}) {
  const handleMessage = useCallback(
    (payload) => {
      const availability = payload?.data
      if (
        payload?.type === 'event_availability_updated' &&
        typeof availability?.event_id === 'string' &&
        Number.isInteger(availability.total_tickets) &&
        Number.isInteger(availability.tickets_available)
      ) {
        onAvailabilityUpdate(availability)
      }
    },
    [onAvailabilityUpdate],
  )

  useAuthenticatedWebSocket({
    tokens,
    getSocketUrl: getEventAvailabilitySocketUrl,
    onMessage: handleMessage,
    onSessionExpired,
    onTokensChanged,
  })
}

function useNotifications({
  enabled,
  tokens,
  onNotificationReceived,
  onSessionExpired,
  onTokensChanged,
}) {
  const handleMessage = useCallback(
    (payload) => {
      if (
        payload?.type === 'notification' &&
        payload?.data &&
        typeof payload.data.id === 'string' &&
        typeof payload.data.message === 'string'
      ) {
        onNotificationReceived(payload.data)
      }
    },
    [onNotificationReceived],
  )

  useAuthenticatedWebSocket({
    enabled,
    tokens,
    getSocketUrl: getNotificationSocketUrl,
    onMessage: handleMessage,
    onSessionExpired,
    onTokensChanged,
  })
}

function EventsPage({
  tokens,
  onSessionExpired,
  onTokensChanged,
  metadata,
  currentUserId,
  role,
}) {
  const [page, setPage] = useState(1)
  const [eventView, setEventView] = useState('published')
  const [eventPage, setEventPage] = useState(null)
  const [selectedEvent, setSelectedEvent] = useState(null)
  const [editingEvent, setEditingEvent] = useState(null)
  const [selectedCategoryId, setSelectedCategoryId] = useState('')
  const [selectedTagIds, setSelectedTagIds] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [retryCount, setRetryCount] = useState(0)
  const [actionNotice, setActionNotice] = useState('')
  const tokensRef = useRef(tokens)
  const canViewDrafts = ['organizer', 'admin'].includes(role)
  const selectedTagKey = selectedTagIds.join('|')
  const categoryNames = useMemo(
    () => new Map(metadata.categories.map((item) => [item.id, item.name])),
    [metadata.categories],
  )
  const tagNames = useMemo(
    () => new Map(metadata.tags.map((item) => [item.id, item.name])),
    [metadata.tags],
  )

  useEffect(() => {
    tokensRef.current = tokens
  }, [tokens])

  useEffect(() => {
    if (!actionNotice) return undefined
    const timer = window.setTimeout(() => setActionNotice(''), 4500)
    return () => window.clearTimeout(timer)
  }, [actionNotice])

  const handleAvailabilityUpdate = useCallback((availability) => {
    const applyAvailability = (event) =>
      event.id === availability.event_id
        ? {
            ...event,
            total_tickets: availability.total_tickets,
            tickets_available: availability.tickets_available,
          }
        : event

    setEventPage((current) =>
      current
        ? { ...current, items: current.items.map(applyAvailability) }
        : current,
    )
    setSelectedEvent((current) =>
      current ? applyAvailability(current) : current,
    )
  }, [])

  useEventAvailability({
    tokens,
    onAvailabilityUpdate: handleAvailabilityUpdate,
    onSessionExpired,
    onTokensChanged,
  })

  useEffect(() => {
    let cancelled = false

    async function loadPage() {
      setLoading(true)
      setError(null)

      try {
        const loadEvents = eventView === 'drafts' ? listDraftEvents : listEvents
        const result = await loadEvents({
          tokens: tokensRef.current,
          page,
          categoryId: selectedCategoryId,
          tagIds: selectedTagKey ? selectedTagKey.split('|') : [],
        })
        const response = result.data

        if (!validateEventPage(response)) {
          throw new UnexpectedEventResponseError(
            'Invalid paginated event response.',
          )
        }

        if (!cancelled) {
          if (result.tokens.access_token !== tokensRef.current.access_token) {
            tokensRef.current = result.tokens
            onTokensChanged(result.tokens)
          }
          setEventPage(response)
          setLoading(false)
        }
      } catch (requestError) {
        if (cancelled) return

        if (requestError instanceof SessionExpiredError) {
          onSessionExpired(requestError.message)
          return
        }
        setError(getEventErrorMessage(requestError))
        setLoading(false)
      }
    }

    loadPage()
    return () => {
      cancelled = true
    }
  }, [
    onSessionExpired,
    onTokensChanged,
    eventView,
    page,
    retryCount,
    selectedCategoryId,
    selectedTagKey,
  ])

  const firstVisibleItem = eventPage?.total_items
    ? (eventPage.page - 1) * eventPage.page_size + 1
    : 0
  const lastVisibleItem = eventPage?.total_items
    ? Math.min(eventPage.page * eventPage.page_size, eventPage.total_items)
    : 0

  function changePage(nextPage) {
    if (
      loading ||
      !eventPage ||
      nextPage < 1 ||
      nextPage > eventPage.total_pages ||
      nextPage === page
    ) {
      return
    }

    setPage(nextPage)
    setSelectedEvent(null)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleBooked = useCallback((booking, remainingTickets) => {
    setEventPage((current) => {
      if (!current) return current
      return {
        ...current,
        items: current.items.map((event) =>
          event.id === booking.event_id
            ? {
                ...event,
                tickets_available: Math.min(
                  Number(event.tickets_available),
                  remainingTickets,
                ),
              }
            : event,
        ),
      }
    })
    setSelectedEvent((current) =>
      current?.id === booking.event_id
        ? {
            ...current,
            tickets_available: Math.min(
              Number(current.tickets_available),
              remainingTickets,
            ),
          }
        : current,
    )
  }, [])

  const handleEventUpdated = useCallback((updatedEvent) => {
    setEventPage((current) =>
      current
        ? {
            ...current,
            items: current.items.map((item) =>
              item.id === updatedEvent.id ? updatedEvent : item,
            ),
          }
        : current,
    )
    setSelectedEvent(null)
    setEditingEvent(null)
    setActionNotice(`${updatedEvent.title} was updated.`)
    setRetryCount((count) => count + 1)
  }, [])

  const handleEventCancelled = useCallback((cancelledEvent) => {
    setSelectedEvent(null)
    setEditingEvent(null)
    setActionNotice(`${cancelledEvent.title} was cancelled.`)
    setRetryCount((count) => count + 1)
  }, [])

  function selectCategory(event) {
    setSelectedCategoryId(event.target.value)
    setPage(1)
    setSelectedEvent(null)
  }

  function toggleFilterTag(tagId) {
    setSelectedTagIds((current) =>
      current.includes(tagId)
        ? current.filter((id) => id !== tagId)
        : [...current, tagId],
    )
    setPage(1)
    setSelectedEvent(null)
  }

  function clearFilters() {
    setSelectedCategoryId('')
    setSelectedTagIds([])
    setPage(1)
    setSelectedEvent(null)
  }

  function changeEventView(nextView) {
    if (nextView === eventView || (nextView === 'drafts' && !canViewDrafts)) {
      return
    }
    setEventView(nextView)
    setPage(1)
    setSelectedEvent(null)
    setEditingEvent(null)
    setActionNotice('')
  }

  const filtersActive = Boolean(selectedCategoryId || selectedTagIds.length)

  return (
    <section className="events-content" aria-labelledby="events-title">
        <div className="events-intro">
          <div>
            <p className="eyebrow">
              {eventView === 'drafts' ? 'Event management' : 'Upcoming experiences'}
            </p>
            <h1 id="events-title">
              {eventView === 'drafts' ? 'Draft events' : 'Explore events'}
            </h1>
            <p>
              {eventView === 'drafts'
                ? role === 'admin'
                  ? 'Review unpublished events from every organizer.'
                  : 'Finish and publish the events you are preparing.'
                : 'Find something worth showing up for.'}
            </p>
          </div>
          {!loading && eventPage && (
            <p className="events-count">
              {eventPage.total_items}{' '}
              {eventView === 'drafts'
                ? eventPage.total_items === 1 ? 'draft event' : 'draft events'
                : `${eventPage.total_items === 1 ? 'event' : 'events'} available`}
            </p>
          )}
        </div>

        {canViewDrafts && (
          <div className="event-view-tabs" role="tablist" aria-label="Event views">
            <button
              className={eventView === 'published' ? 'event-view-tab-active' : ''}
              type="button"
              role="tab"
              aria-selected={eventView === 'published'}
              onClick={() => changeEventView('published')}
            >
              Published events
            </button>
            <button
              className={eventView === 'drafts' ? 'event-view-tab-active' : ''}
              type="button"
              role="tab"
              aria-selected={eventView === 'drafts'}
              onClick={() => changeEventView('drafts')}
            >
              Draft events
            </button>
          </div>
        )}

        <div className="event-filters" aria-label="Filter events">
          <div className="event-category-filter">
            <label htmlFor="event-filter-category">Category</label>
            <select
              id="event-filter-category"
              value={selectedCategoryId}
              onChange={selectCategory}
              disabled={metadata.loading}
            >
              <option value="">All categories</option>
              {metadata.categories.map((category) => (
                <option value={category.id} key={category.id}>{category.name}</option>
              ))}
            </select>
          </div>
          <fieldset className="event-tag-filters">
            <legend>Tags <small>Events must match every selected tag</small></legend>
            <div>
              {metadata.loading ? (
                <span className="filter-message">Loading filters…</span>
              ) : metadata.tags.length === 0 ? (
                <span className="filter-message">No tags available</span>
              ) : metadata.tags.map((tag) => (
                <button
                  className={selectedTagIds.includes(tag.id) ? 'filter-tag-selected' : ''}
                  type="button"
                  onClick={() => toggleFilterTag(tag.id)}
                  aria-pressed={selectedTagIds.includes(tag.id)}
                  key={tag.id}
                >
                  {tag.name}
                </button>
              ))}
            </div>
          </fieldset>
          {filtersActive && (
            <button className="clear-filters" type="button" onClick={clearFilters}>
              Clear filters
            </button>
          )}
        </div>
        {metadata.error && (
          <div className="metadata-filter-error" role="alert">
            <span>{metadata.error}</span>
            <button type="button" onClick={metadata.retry}>Try again</button>
          </div>
        )}
        {actionNotice && <Alert type="success">{actionNotice}</Alert>}

        {error ? (
          <div className="events-state events-error" role="alert">
            <span className="state-icon" aria-hidden="true">!</span>
            <h2>Events could not be loaded</h2>
            <p>{error}</p>
            <button type="button" onClick={() => setRetryCount((count) => count + 1)}>
              Try again
            </button>
          </div>
        ) : loading ? (
          <div className="events-grid" aria-label="Loading events" aria-busy="true">
            {Array.from({ length: 6 }, (_, index) => (
              <EventCardSkeleton key={index} />
            ))}
          </div>
        ) : eventPage.items.length === 0 ? (
          <div className="events-state">
            <span className="state-icon state-icon-empty" aria-hidden="true">◇</span>
            <h2>
              {filtersActive
                ? 'No events match these filters'
                : eventView === 'drafts'
                  ? 'No draft events'
                  : 'No upcoming events yet'}
            </h2>
            <p>
              {filtersActive
                ? 'Try removing a category or tag filter.'
                : eventView === 'drafts'
                  ? role === 'admin'
                    ? 'There are no unpublished events to review.'
                    : 'Events saved as drafts will appear here.'
                  : 'Published events will appear here as soon as they are available.'}
            </p>
          </div>
        ) : (
          <>
            <div className="events-grid">
              {eventPage.items.map((event, index) => (
                <EventCard
                  event={event}
                  index={index}
                  onSelect={setSelectedEvent}
                  categoryName={categoryNames.get(event.category_id)}
                  isOwned={
                    ['organizer', 'admin'].includes(role) &&
                    event.organizer_id === currentUserId
                  }
                  key={event.id}
                />
              ))}
            </div>

            <nav className="pagination" aria-label="Event pages">
              <p>
                Showing {firstVisibleItem}-{lastVisibleItem} of{' '}
                {eventPage.total_items}
              </p>
              <div className="pagination-controls">
                <button
                  type="button"
                  onClick={() => changePage(page - 1)}
                  disabled={page <= 1}
                  aria-label="Previous page"
                >
                  ←
                </button>
                <span>
                  Page <strong>{page}</strong> of {eventPage.total_pages}
                </span>
                <button
                  type="button"
                  onClick={() => changePage(page + 1)}
                  disabled={page >= eventPage.total_pages}
                  aria-label="Next page"
                >
                  →
                </button>
              </div>
            </nav>
          </>
        )}
        {selectedEvent && (
          <EventDetailsModal
            event={selectedEvent}
            tokens={tokens}
            onClose={() => setSelectedEvent(null)}
            onBooked={handleBooked}
            onEdit={() => {
              setEditingEvent(selectedEvent)
              setSelectedEvent(null)
            }}
            onCancelled={handleEventCancelled}
            onSessionExpired={onSessionExpired}
            onTokensChanged={onTokensChanged}
            categoryName={categoryNames.get(selectedEvent.category_id)}
            tagNames={selectedEvent.tag_ids
              .map((tagId) => tagNames.get(tagId))
              .filter(Boolean)}
            canEdit={
              ['organizer', 'admin'].includes(role) &&
              selectedEvent.organizer_id === currentUserId &&
              ['draft', 'published'].includes(selectedEvent.status)
            }
            canCancel={
              selectedEvent.status !== 'cancelled' &&
              selectedEvent.status !== 'completed' &&
              (role === 'admin' || (
                role === 'organizer' &&
                selectedEvent.organizer_id === currentUserId
              ))
            }
          />
        )}
        {editingEvent && (
          <EditEventModal
            event={editingEvent}
            tokens={tokens}
            onClose={() => setEditingEvent(null)}
            onUpdated={handleEventUpdated}
            onCancelled={handleEventCancelled}
            onSessionExpired={onSessionExpired}
            onTokensChanged={onTokensChanged}
            metadata={metadata}
          />
        )}
    </section>
  )
}

function formatDateTime(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Date unavailable'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function shortId(value) {
  return typeof value === 'string' ? value.slice(0, 8) : 'Unknown'
}

function RatingStars({ rating, onChange }) {
  const interactive = typeof onChange === 'function'

  return (
    <div
      className={`review-stars ${interactive ? 'review-stars-interactive' : ''}`}
      aria-label={interactive ? 'Choose a rating out of 5 stars' : `${rating} out of 5 stars`}
      role={interactive ? 'group' : 'img'}
    >
      {[1, 2, 3, 4, 5].map((value) =>
        interactive ? (
          <button
            className={value <= rating ? 'review-star-active' : ''}
            type="button"
            onClick={() => onChange(value)}
            aria-label={`${value} star${value === 1 ? '' : 's'}`}
            aria-pressed={rating === value}
            key={value}
          >
            ★
          </button>
        ) : (
          <span className={value <= rating ? 'review-star-active' : ''} key={value}>
            ★
          </span>
        ),
      )}
    </div>
  )
}

function ReviewModal({
  booking,
  tokens,
  onClose,
  onSaved,
  onDeleted,
  onSessionExpired,
  onTokensChanged,
}) {
  const existingReview = booking.review
  const [rating, setRating] = useState(existingReview?.rating || 0)
  const [comment, setComment] = useState(existingReview?.comment || '')
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const busy = submitting || deleting
  const closeWhenIdle = () => {
    if (!busy) onClose()
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const normalizedComment = comment.trim()
    const errors = {}

    if (!Number.isInteger(rating) || rating < 1 || rating > 5) {
      errors.rating = 'Choose a rating from 1 to 5 stars.'
    }
    if (!normalizedComment) {
      errors.comment = 'Write a review before submitting.'
    }
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      setFormError('Please correct the highlighted fields and try again.')
      return
    }

    setSubmitting(true)
    setFieldErrors({})
    setFormError(null)
    try {
      const result = existingReview
        ? await updateReview({
            tokens,
            reviewId: existingReview.id,
            rating,
            comment: normalizedComment,
          })
        : await createReview({
            tokens,
            bookingId: booking.id,
            rating,
            comment: normalizedComment,
          })
      if (result.tokens.access_token !== tokens.access_token) {
        onTokensChanged(result.tokens)
      }
      onSaved(result.data)
    } catch (error) {
      if (error instanceof SessionExpiredError) {
        onSessionExpired(error.message)
        return
      }
      const apiErrors = getFormApiErrors(
        error,
        ['rating', 'comment'],
        `We could not ${existingReview ? 'update' : 'publish'} your review. Please try again.`,
      )
      setFieldErrors(apiErrors.fieldErrors)
      setFormError(apiErrors.message)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete() {
    if (!existingReview || deleting) return

    setDeleting(true)
    setFormError(null)
    try {
      const result = await deleteReview({
        tokens,
        reviewId: existingReview.id,
      })
      if (result.tokens.access_token !== tokens.access_token) {
        onTokensChanged(result.tokens)
      }
      onDeleted()
    } catch (error) {
      if (error instanceof SessionExpiredError) {
        onSessionExpired(error.message)
        return
      }
      setConfirmDelete(false)
      setFormError(
        error instanceof ApiError && typeof error.payload?.detail === 'string'
          ? error.payload.detail
          : 'We could not delete your review. Please try again.',
      )
    } finally {
      setDeleting(false)
    }
  }

  return (
    <Modal
      titleId="review-modal-title"
      onClose={closeWhenIdle}
      className="form-modal review-modal"
    >
      <div className="modal-heading">
        <p className="eyebrow">{existingReview ? 'Your feedback' : 'Share your experience'}</p>
        <h1 id="review-modal-title">
          {existingReview ? 'Edit review' : 'Leave a review'}
        </h1>
        <p>{booking.event_title}</p>
      </div>
      <Alert>{formError}</Alert>
      {existingReview?.replies?.length > 0 && (
        <div className="review-modal-replies">
          <span>Replies to your review</span>
          {existingReview.replies.map((reply) => (
            <div className={`review-reply review-reply-${reply.replier_role}`} key={reply.id}>
              <div>
                <strong>{reply.replier_role === 'admin' ? 'Admin reply' : 'Organizer reply'}</strong>
                <time dateTime={reply.created_at}>{formatDateTime(reply.created_at)}</time>
              </div>
              <p>{reply.body}</p>
            </div>
          ))}
        </div>
      )}
      <form className="review-form" onSubmit={handleSubmit} noValidate>
        <fieldset className="review-rating-field">
          <legend>Rating</legend>
          <RatingStars
            rating={rating}
            onChange={(value) => {
              setRating(value)
              setFieldErrors((current) => ({ ...current, rating: undefined }))
              setFormError(null)
            }}
          />
          <FieldError id="review-rating-error">{fieldErrors.rating}</FieldError>
        </fieldset>
        <div className="form-field">
          <label htmlFor="review-comment">Review</label>
          <textarea
            id="review-comment"
            name="comment"
            value={comment}
            onChange={(event) => {
              setComment(event.target.value)
              setFieldErrors((current) => ({ ...current, comment: undefined }))
              setFormError(null)
            }}
            className={fieldErrors.comment ? 'input-error' : ''}
            placeholder="What did you think of the event?"
            rows={5}
          />
          <FieldError id="review-comment-error">{fieldErrors.comment}</FieldError>
        </div>

        {confirmDelete && (
          <div className="review-delete-confirmation" role="alert">
            <div>
              <strong>Delete this review?</strong>
              <p>Your rating, comment, and all replies will be permanently removed.</p>
            </div>
            <div>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setConfirmDelete(false)}
                disabled={deleting}
              >
                Keep review
              </button>
              <button
                className="destructive-button"
                type="button"
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? 'Deleting…' : 'Delete permanently'}
              </button>
            </div>
          </div>
        )}

        <div className="modal-actions review-form-actions">
          {existingReview && !confirmDelete && (
            <button
              className="destructive-button"
              type="button"
              onClick={() => setConfirmDelete(true)}
              disabled={busy}
            >
              Delete review
            </button>
          )}
          <button className="secondary-button" type="button" onClick={closeWhenIdle} disabled={busy}>
            Cancel
          </button>
          <button className="primary-button" type="submit" disabled={busy || confirmDelete}>
            {submitting && <span className="spinner" aria-hidden="true" />}
            {submitting ? 'Saving…' : existingReview ? 'Save changes' : 'Publish review'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

function validateBookingPage(payload) {
  return (
    payload &&
    Array.isArray(payload.items) &&
    payload.items.every(
      (booking) =>
        typeof booking?.event_title === 'string' &&
        ['draft', 'published', 'cancelled', 'completed'].includes(
          booking.event_status,
        ) &&
        (booking.review === null ||
          (typeof booking.review?.id === 'string' &&
            booking.review.booking_id === booking.id &&
            Number.isInteger(booking.review.rating) &&
            booking.review.rating >= 1 &&
            booking.review.rating <= 5 &&
            typeof booking.review.comment === 'string' &&
            Array.isArray(booking.review.replies) &&
            booking.review.replies.every(
              (reply) =>
                typeof reply?.id === 'string' &&
                ['organizer', 'admin'].includes(reply.replier_role) &&
                typeof reply.body === 'string',
            ))),
    ) &&
    payload.page_size === 5 &&
    Number.isInteger(payload.page) &&
    Number.isInteger(payload.total_items) &&
    Number.isInteger(payload.total_pages)
  )
}

function BookingsPage({ tokens, onSessionExpired, onTokensChanged }) {
  const [page, setPage] = useState(1)
  const [bookingPage, setBookingPage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [retryCount, setRetryCount] = useState(0)
  const [cancellingBookingId, setCancellingBookingId] = useState(null)
  const [bookingToCancel, setBookingToCancel] = useState(null)
  const [reviewBooking, setReviewBooking] = useState(null)
  const [actionError, setActionError] = useState(null)
  const tokensRef = useRef(tokens)

  useEffect(() => {
    tokensRef.current = tokens
  }, [tokens])

  useEffect(() => {
    let cancelled = false

    async function loadBookings() {
      setLoading(true)
      setError(null)
      try {
        const result = await listBookings({ tokens: tokensRef.current, page })
        if (!validateBookingPage(result.data)) {
          throw new Error('Invalid paginated booking response.')
        }
        if (!cancelled) {
          if (result.tokens.access_token !== tokensRef.current.access_token) {
            tokensRef.current = result.tokens
            onTokensChanged(result.tokens)
          }
          setBookingPage(result.data)
          setLoading(false)
        }
      } catch (requestError) {
        if (cancelled) return
        if (requestError instanceof SessionExpiredError) {
          onSessionExpired(requestError.message)
          return
        }
        setError(getResourceErrorMessage(requestError, 'your bookings'))
        setLoading(false)
      }
    }

    loadBookings()
    return () => { cancelled = true }
  }, [onSessionExpired, onTokensChanged, page, retryCount])

  function changePage(nextPage) {
    if (
      loading ||
      !bookingPage ||
      nextPage < 1 ||
      nextPage > bookingPage.total_pages
    ) return

    setPage(nextPage)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function requestBookingCancellation(booking) {
    if (booking.status === 'cancelled' || cancellingBookingId) return

    setActionError(null)
    setBookingToCancel(booking)
  }

  async function handleCancelBooking() {
    const booking = bookingToCancel
    if (!booking || booking.status === 'cancelled' || cancellingBookingId) return

    setCancellingBookingId(booking.id)
    setActionError(null)
    try {
      const result = await cancelBooking({
        tokens: tokensRef.current,
        bookingId: booking.id,
      })
      if (result.tokens.access_token !== tokensRef.current.access_token) {
        tokensRef.current = result.tokens
        onTokensChanged(result.tokens)
      }
      setBookingPage((current) =>
        current
          ? {
              ...current,
              items: current.items.map((item) =>
                item.id === booking.id ? result.data : item,
              ),
            }
          : current,
      )
      setBookingToCancel(null)
    } catch (requestError) {
      if (requestError instanceof SessionExpiredError) {
        onSessionExpired(requestError.message)
        return
      }
      setActionError(getResourceErrorMessage(requestError, 'the booking cancellation'))
    } finally {
      setCancellingBookingId(null)
    }
  }

  function updateBookingReview(bookingId, review) {
    setBookingPage((current) =>
      current
        ? {
            ...current,
            items: current.items.map((booking) =>
              booking.id === bookingId ? { ...booking, review } : booking,
            ),
          }
        : current,
    )
  }

  function handleReviewSaved(review) {
    if (!reviewBooking) return
    updateBookingReview(reviewBooking.id, {
      ...review,
      replies: reviewBooking.review?.replies || [],
    })
    setReviewBooking(null)
  }

  function handleReviewDeleted() {
    if (!reviewBooking) return
    updateBookingReview(reviewBooking.id, null)
    setReviewBooking(null)
  }

  return (
    <section className="events-content" aria-labelledby="bookings-title">
      <div className="events-intro">
        <div>
          <p className="eyebrow">Your reservations</p>
          <h1 id="bookings-title">My bookings</h1>
          <p>Keep track of every event you have booked.</p>
        </div>
        {!loading && bookingPage && (
          <p className="events-count">{bookingPage.total_items} total</p>
        )}
      </div>

      {error ? (
        <ResourceError
          title="Bookings could not be loaded"
          message={error}
          onRetry={() => setRetryCount((count) => count + 1)}
        />
      ) : loading ? (
        <div className="booking-list" aria-label="Loading bookings" aria-busy="true">
          {Array.from({ length: 5 }, (_, index) => (
            <div
              className="booking-card booking-card-skeleton skeleton-block"
              key={index}
            />
          ))}
        </div>
      ) : bookingPage.items.length === 0 ? (
        <div className="events-state">
          <span className="state-icon state-icon-empty" aria-hidden="true">◇</span>
          <h2>No bookings yet</h2>
          <p>Your event reservations will appear here.</p>
        </div>
      ) : (
        <>
          <Alert>{actionError}</Alert>
          <div className="booking-list">
            {bookingPage.items.map((booking) => (
              <article className="booking-card" key={booking.id}>
                <div className="booking-icon"><AppIcon type="bookings" /></div>
                <div className="booking-main">
                  <div className="booking-heading">
                    <h2 title={booking.event_id}>
                      {booking.event_title || `Event ${shortId(booking.event_id)}`}
                    </h2>
                    <span className={`status-badge status-${booking.status}`}>
                      {booking.status === 'confirmed'
                        ? 'Booking confirmed'
                        : 'Booking cancelled'}
                    </span>
                    {booking.event_status === 'draft' && (
                      <span className="event-state-badge event-state-draft">
                        Event is draft
                      </span>
                    )}
                  </div>
                  <p>Booked {formatDateTime(booking.booked_at)}</p>
                  {booking.event_status === 'draft' && (
                    <p className="booking-event-notice">
                      The organizer has moved this event back to draft.
                    </p>
                  )}
                  <small title={booking.id}>Booking #{shortId(booking.id)}</small>
                </div>
                <div className="booking-quantity">
                  <span>Tickets</span>
                  <strong>{booking.quantity}</strong>
                </div>
                <div className="booking-actions">
                  {booking.review ? (
                    <button
                      className="secondary-button review-booking-button"
                      type="button"
                      onClick={() => {
                        setActionError(null)
                        setReviewBooking(booking)
                      }}
                    >
                      Edit review
                    </button>
                  ) : booking.status === 'confirmed' && booking.event_status !== 'cancelled' ? (
                    <button
                      className="secondary-button review-booking-button"
                      type="button"
                      onClick={() => {
                        setActionError(null)
                        setReviewBooking(booking)
                      }}
                    >
                      Leave a review
                    </button>
                  ) : null}
                  {booking.status === 'cancelled' ? (
                    <span className="read-status-label">Cancelled</span>
                  ) : (
                    <button
                      className="destructive-button"
                      type="button"
                      onClick={() => requestBookingCancellation(booking)}
                      disabled={Boolean(cancellingBookingId)}
                    >
                      {cancellingBookingId === booking.id
                        ? 'Cancelling…'
                        : 'Cancel booking'}
                    </button>
                  )}
                </div>
                {booking.cancelled_at && (
                  <p className="booking-cancelled">
                    Cancelled {formatDateTime(booking.cancelled_at)}
                  </p>
                )}
              </article>
            ))}
          </div>
          <Pagination
            pageData={bookingPage}
            loading={loading}
            onChange={changePage}
            label="Booking"
          />
        </>
      )}
      {bookingToCancel && (
        <ConfirmationModal
          title="Cancel this booking?"
          description={`This will cancel your reservation for ${bookingToCancel.quantity} ticket${bookingToCancel.quantity === 1 ? '' : 's'}. The ticket${bookingToCancel.quantity === 1 ? '' : 's'} will be returned to the event.`}
          confirmLabel="Cancel booking"
          cancelLabel="Keep booking"
          onClose={() => setBookingToCancel(null)}
          onConfirm={handleCancelBooking}
          submitting={cancellingBookingId === bookingToCancel.id}
        />
      )}
      {reviewBooking && (
        <ReviewModal
          booking={reviewBooking}
          tokens={tokens}
          onClose={() => setReviewBooking(null)}
          onSaved={handleReviewSaved}
          onDeleted={handleReviewDeleted}
          onSessionExpired={onSessionExpired}
          onTokensChanged={onTokensChanged}
        />
      )}
    </section>
  )
}

function useProtectedList({
  tokens,
  load,
  resource,
  onSessionExpired,
  onTokensChanged,
}) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [retryCount, setRetryCount] = useState(0)
  const tokensRef = useRef(tokens)

  useEffect(() => {
    tokensRef.current = tokens
  }, [tokens])

  useEffect(() => {
    let cancelled = false

    async function loadData() {
      setLoading(true)
      setError(null)
      try {
        const result = await load({ tokens: tokensRef.current })
        if (!Array.isArray(result.data)) {
          throw new Error(`Invalid ${resource} response.`)
        }
        if (!cancelled) {
          if (result.tokens.access_token !== tokensRef.current.access_token) {
            tokensRef.current = result.tokens
            onTokensChanged(result.tokens)
          }
          setData(result.data)
          setLoading(false)
        }
      } catch (requestError) {
        if (cancelled) return
        if (requestError instanceof SessionExpiredError) {
          onSessionExpired(requestError.message)
          return
        }
        setError(getResourceErrorMessage(requestError, resource))
        setLoading(false)
      }
    }

    loadData()
    return () => { cancelled = true }
  }, [load, onSessionExpired, onTokensChanged, resource, retryCount])

  return {
    data,
    setData,
    loading,
    error,
    retry: () => setRetryCount((count) => count + 1),
  }
}

function validateReviewGroups(payload) {
  return (
    Array.isArray(payload) &&
    payload.every(
      (group) =>
        typeof group?.event_id === 'string' &&
        typeof group.event_title === 'string' &&
        ['draft', 'published', 'cancelled', 'completed'].includes(group.event_status) &&
        typeof group.organizer_id === 'string' &&
        typeof group.organizer_name === 'string' &&
        Array.isArray(group.reviews) &&
        group.reviews.every(
          (review) =>
            typeof review?.id === 'string' &&
            typeof review.booking_id === 'string' &&
            typeof review.reviewer_id === 'string' &&
            typeof review.reviewer_name === 'string' &&
            Number.isInteger(review.rating) &&
            review.rating >= 1 &&
            review.rating <= 5 &&
            typeof review.comment === 'string' &&
            Array.isArray(review.replies) &&
            review.replies.every(
              (reply) =>
                typeof reply?.id === 'string' &&
                reply.review_id === review.id &&
                ['organizer', 'admin'].includes(reply.replier_role) &&
                typeof reply.body === 'string',
            ),
        ),
    )
  )
}

function ReplyModal({
  review,
  eventTitle,
  tokens,
  onClose,
  onReplied,
  onSessionExpired,
  onTokensChanged,
}) {
  const [body, setBody] = useState('')
  const [fieldError, setFieldError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const closeWhenIdle = () => {
    if (!submitting) onClose()
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const normalizedBody = body.trim()
    if (!normalizedBody) {
      setFieldError('Write a reply before submitting.')
      setFormError('Please correct the highlighted field and try again.')
      return
    }

    setSubmitting(true)
    setFieldError(null)
    setFormError(null)
    try {
      const result = await createReviewReply({
        tokens,
        reviewId: review.id,
        body: normalizedBody,
      })
      if (result.tokens.access_token !== tokens.access_token) {
        onTokensChanged(result.tokens)
      }
      onReplied(result.data)
    } catch (error) {
      if (error instanceof SessionExpiredError) {
        onSessionExpired(error.message)
        return
      }
      const apiErrors = getFormApiErrors(
        error,
        ['body'],
        'We could not publish this reply. Please try again.',
      )
      setFieldError(apiErrors.fieldErrors.body)
      setFormError(apiErrors.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      titleId="reply-modal-title"
      onClose={closeWhenIdle}
      className="form-modal reply-modal"
    >
      <div className="modal-heading">
        <p className="eyebrow">Respond to feedback</p>
        <h1 id="reply-modal-title">Reply to review</h1>
        <p>{eventTitle} · Review by {review.reviewer_name}</p>
      </div>
      <div className="reply-review-preview">
        <RatingStars rating={review.rating} />
        <p>{review.comment}</p>
      </div>
      <Alert>{formError}</Alert>
      <form className="review-form" onSubmit={handleSubmit} noValidate>
        <div className="form-field">
          <label htmlFor="reply-body">Your reply</label>
          <textarea
            id="reply-body"
            name="body"
            value={body}
            onChange={(event) => {
              setBody(event.target.value)
              setFieldError(null)
              setFormError(null)
            }}
            className={fieldError ? 'input-error' : ''}
            placeholder="Thank the attendee or address their feedback"
            rows={5}
          />
          <FieldError id="reply-body-error">{fieldError}</FieldError>
        </div>
        <div className="modal-actions">
          <button className="secondary-button" type="button" onClick={closeWhenIdle} disabled={submitting}>
            Cancel
          </button>
          <button className="primary-button" type="submit" disabled={submitting}>
            {submitting && <span className="spinner" aria-hidden="true" />}
            {submitting ? 'Publishing…' : 'Publish reply'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

function ReviewsPage({
  tokens,
  role,
  onSessionExpired,
  onTokensChanged,
}) {
  const {
    data: reviewGroups,
    setData: setReviewGroups,
    loading,
    error,
    retry,
  } = useProtectedList({
    tokens,
    onSessionExpired,
    onTokensChanged,
    load: listEventReviews,
    resource: 'event reviews',
  })
  const [replyTarget, setReplyTarget] = useState(null)

  const validGroups = reviewGroups && validateReviewGroups(reviewGroups)
    ? reviewGroups
    : null
  const totalReviews = validGroups?.reduce(
    (total, group) => total + group.reviews.length,
    0,
  ) || 0

  function handleReplied(reply) {
    if (!replyTarget) return
    setReviewGroups((current) =>
      current?.map((group) =>
        group.event_id !== replyTarget.event.event_id
          ? group
          : {
              ...group,
              reviews: group.reviews.map((review) =>
                review.id === replyTarget.review.id
                  ? { ...review, replies: [...review.replies, reply] }
                  : review,
              ),
            },
      ),
    )
    setReplyTarget(null)
  }

  if (!loading && reviewGroups && !validGroups) {
    return (
      <section className="events-content" aria-labelledby="reviews-title">
        <ResourceError
          title="Reviews could not be loaded"
          message="The server returned an invalid review response."
          onRetry={retry}
        />
      </section>
    )
  }

  return (
    <section className="events-content reviews-content" aria-labelledby="reviews-title">
      <div className="events-intro reviews-intro">
        <div>
          <p className="eyebrow">Event feedback</p>
          <h1 id="reviews-title">Reviews</h1>
          <p>
            {role === 'admin'
              ? 'See attendee feedback across every event and respond as an admin.'
              : 'See attendee feedback grouped under each of your events.'}
          </p>
        </div>
        {!loading && validGroups && (
          <div className="reviews-summary">
            <span>{validGroups.length} event{validGroups.length === 1 ? '' : 's'}</span>
            <strong>{totalReviews} review{totalReviews === 1 ? '' : 's'}</strong>
            <button type="button" onClick={retry}>Refresh</button>
          </div>
        )}
      </div>

      {error ? (
        <ResourceError
          title="Reviews could not be loaded"
          message={error}
          onRetry={retry}
        />
      ) : loading ? (
        <div className="review-groups" aria-label="Loading reviews" aria-busy="true">
          {Array.from({ length: 3 }, (_, index) => (
            <div className="review-group review-group-skeleton skeleton-block" key={index} />
          ))}
        </div>
      ) : validGroups.length === 0 ? (
        <div className="events-state">
          <span className="state-icon state-icon-empty" aria-hidden="true">☆</span>
          <h2>No reviews yet</h2>
          <p>Reviews will appear here under the event they belong to.</p>
        </div>
      ) : (
        <div className="review-groups">
          {validGroups.map((group) => (
            <section className="review-group" aria-labelledby={`reviews-event-${group.event_id}`} key={group.event_id}>
              <header className="review-group-header">
                <div>
                  <div className="review-event-title-line">
                    <h2 id={`reviews-event-${group.event_id}`}>{group.event_title}</h2>
                    <span className={`review-event-status review-event-status-${group.event_status}`}>
                      {group.event_status}
                    </span>
                  </div>
                  {role === 'admin' && <p>Organized by {group.organizer_name}</p>}
                </div>
                <span>{group.reviews.length} review{group.reviews.length === 1 ? '' : 's'}</span>
              </header>
              <div className="review-list">
                {group.reviews.map((review) => {
                  const hasRoleReply = review.replies.some(
                    (reply) => reply.replier_role === role,
                  )
                  return (
                    <article className="review-card" key={review.id}>
                      <div className="review-author-avatar" aria-hidden="true">
                        {review.reviewer_name.charAt(0).toUpperCase()}
                      </div>
                      <div className="review-card-content">
                        <div className="review-card-heading">
                          <div>
                            <strong>{review.reviewer_name}</strong>
                            <RatingStars rating={review.rating} />
                          </div>
                          <time dateTime={review.created_at}>{formatDateTime(review.created_at)}</time>
                        </div>
                        <p className="review-comment">{review.comment}</p>
                        {review.updated_at !== review.created_at && (
                          <small className="review-edited">Edited {formatDateTime(review.updated_at)}</small>
                        )}
                        {review.replies.length > 0 && (
                          <div className="review-replies">
                            {review.replies.map((reply) => (
                              <div className={`review-reply review-reply-${reply.replier_role}`} key={reply.id}>
                                <div>
                                  <strong>{reply.replier_role === 'admin' ? 'Admin reply' : 'Organizer reply'}</strong>
                                  <time dateTime={reply.created_at}>{formatDateTime(reply.created_at)}</time>
                                </div>
                                <p>{reply.body}</p>
                              </div>
                            ))}
                          </div>
                        )}
                        <div className="review-card-actions">
                          {hasRoleReply ? (
                            <span className="read-status-label">You replied</span>
                          ) : (
                            <button
                              className="secondary-button"
                              type="button"
                              onClick={() => setReplyTarget({ event: group, review })}
                            >
                              <AppIcon type="reply" />
                              Reply
                            </button>
                          )}
                        </div>
                      </div>
                    </article>
                  )
                })}
              </div>
            </section>
          ))}
        </div>
      )}

      {replyTarget && (
        <ReplyModal
          review={replyTarget.review}
          eventTitle={replyTarget.event.event_title}
          tokens={tokens}
          onClose={() => setReplyTarget(null)}
          onReplied={handleReplied}
          onSessionExpired={onSessionExpired}
          onTokensChanged={onTokensChanged}
        />
      )}
    </section>
  )
}

function ProfileModal({
  tokens,
  profile,
  role,
  onClose,
  onUpdated,
  onPasswordChanged,
  onSessionExpired,
  onTokensChanged,
}) {
  const [form, setForm] = useState(() => ({
    name: profile?.name || '',
    email: profile?.email || '',
    role,
  }))
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  })
  const [passwordFieldErrors, setPasswordFieldErrors] = useState({})
  const [passwordFormError, setPasswordFormError] = useState(null)
  const [changingPassword, setChangingPassword] = useState(false)
  const isAdmin = role === 'admin'

  function updateField(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
    setFieldErrors((current) => ({ ...current, [name]: undefined }))
    setFormError(null)
  }

  function updatePasswordField(event) {
    const { name, value } = event.target
    setPasswordForm((current) => ({ ...current, [name]: value }))
    setPasswordFieldErrors((current) => ({
      ...current,
      [name]: undefined,
    }))
    setPasswordFormError(null)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const nextName = normalizeName(form.name)
    const nextEmail = normalizeEmail(form.email)
    const payload = {}
    const errors = {}

    if (nextName) {
      if (characterLength(nextName) < 2) {
        errors.name = 'Name must contain at least 2 characters.'
      } else if (characterLength(nextName) > 120) {
        errors.name = 'Name must contain at most 120 characters.'
      } else if (nextName !== profile?.name) {
        payload.name = nextName
      }
    }

    if (nextEmail) {
      if (characterLength(nextEmail) > 320) {
        errors.email = 'Email must contain at most 320 characters.'
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/u.test(nextEmail)) {
        errors.email = 'Enter a valid email address.'
      } else if (nextEmail !== profile?.email) {
        payload.email = nextEmail
      }
    }

    if (!isAdmin && form.role !== role) payload.role = form.role

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      setFormError('Please correct the highlighted fields and try again.')
      return
    }
    if (Object.keys(payload).length === 0) {
      setFormError('Make a change before saving your profile.')
      return
    }

    setSubmitting(true)
    setFieldErrors({})
    setFormError(null)
    try {
      const result = await updateOwnProfile({ tokens, profile: payload })
      if (result.tokens.access_token !== tokens.access_token) {
        onTokensChanged(result.tokens)
      }
      onUpdated(result.data)
      onClose()
    } catch (error) {
      if (error instanceof SessionExpiredError) {
        onSessionExpired(error.message)
        return
      }
      const apiErrors = getFormApiErrors(
        error,
        ['name', 'email', 'role'],
        'We could not update your profile. Please try again.',
      )
      setFieldErrors(apiErrors.fieldErrors)
      setFormError(apiErrors.message)
    } finally {
      setSubmitting(false)
    }
  }

  async function handlePasswordSubmit(event) {
    event.preventDefault()
    const errors = {}
    const newPasswordLength = characterLength(passwordForm.new_password)
    const passwordChecks = getPasswordChecks(passwordForm.new_password)

    if (!passwordForm.current_password) {
      errors.current_password = 'Enter your current password.'
    } else if (characterLength(passwordForm.current_password) > 128) {
      errors.current_password = 'Password must contain at most 128 characters.'
    }
    if (newPasswordLength < 8) {
      errors.new_password = 'New password must contain at least 8 characters.'
    } else if (newPasswordLength > 128) {
      errors.new_password = 'New password must contain at most 128 characters.'
    } else if (passwordChecks.some((check) => !check.met)) {
      const missingRequirements = passwordChecks
        .filter((check) => !check.met && check.key !== 'length')
        .map((check) => check.label.toLowerCase().replace(/^one /, ''))
      errors.new_password = `Password must contain at least one ${missingRequirements.join(', ')}.`
    } else if (passwordForm.new_password === passwordForm.current_password) {
      errors.new_password = 'The new password must differ from the current password.'
    }
    if (passwordForm.confirm_password !== passwordForm.new_password) {
      errors.confirm_password = 'Passwords do not match.'
    }

    if (Object.keys(errors).length > 0) {
      setPasswordFieldErrors(errors)
      setPasswordFormError('Please correct the highlighted fields and try again.')
      return
    }

    setChangingPassword(true)
    setPasswordFieldErrors({})
    setPasswordFormError(null)
    try {
      await changeOwnPassword({
        tokens,
        currentPassword: passwordForm.current_password,
        newPassword: passwordForm.new_password,
      })
      onPasswordChanged()
    } catch (error) {
      if (error instanceof SessionExpiredError) {
        onSessionExpired(error.message)
        return
      }
      const apiErrors = getFormApiErrors(
        error,
        ['current_password', 'new_password'],
        'We could not change your password. Please try again.',
      )
      setPasswordFieldErrors(apiErrors.fieldErrors)
      setPasswordFormError(apiErrors.message)
    } finally {
      setChangingPassword(false)
    }
  }

  return (
    <Modal titleId="profile-title" onClose={onClose} className="form-modal profile-modal">
      <div className="modal-heading">
        <p className="eyebrow">Account settings</p>
        <h1 id="profile-title">Your profile</h1>
        <p>Leave name or email blank to keep the existing value.</p>
      </div>
      <Alert>{formError}</Alert>
      <form className="profile-form" onSubmit={handleSubmit} noValidate>
        <div className="form-field">
          <label htmlFor="profile-name">Name</label>
          <input id="profile-name" name="name" value={form.name} onChange={updateField} maxLength={120} autoComplete="name" className={fieldErrors.name ? 'input-error' : ''} placeholder="Keep current name" />
          <FieldError id="profile-name-error">{fieldErrors.name}</FieldError>
        </div>
        <div className="form-field">
          <label htmlFor="profile-email">Email address</label>
          <input id="profile-email" name="email" type="email" value={form.email} onChange={updateField} maxLength={320} autoComplete="email" className={fieldErrors.email ? 'input-error' : ''} placeholder="Keep current email" />
          <FieldError id="profile-email-error">{fieldErrors.email}</FieldError>
        </div>
        {isAdmin ? (
          <div className="profile-role-locked">
            <span>Your role</span>
            <strong>Admin</strong>
            <p>Admin accounts cannot change their own role.</p>
          </div>
        ) : (
          <div className="form-field">
            <label htmlFor="profile-role">Role</label>
            <select id="profile-role" name="role" value={form.role} onChange={updateField}>
              {REGISTERABLE_ROLES.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
            <FieldError id="profile-role-error">{fieldErrors.role}</FieldError>
          </div>
        )}
        <div className="modal-actions profile-form-actions">
          <button className="secondary-button" type="button" onClick={onClose} disabled={submitting}>Cancel</button>
          <button className="primary-button" type="submit" disabled={submitting}>
            {submitting && <span className="spinner" aria-hidden="true" />}
            {submitting ? 'Saving…' : 'Save profile'}
          </button>
        </div>
      </form>
      <div className="profile-section-divider" />
      <div className="profile-password-heading">
        <h2>Change password</h2>
        <p>You will be asked to log in again after changing your password.</p>
      </div>
      <Alert>{passwordFormError}</Alert>
      <form className="profile-form profile-password-form" onSubmit={handlePasswordSubmit} noValidate>
        <PasswordField
          id="profile-current-password"
          name="current_password"
          label="Current password"
          value={passwordForm.current_password}
          onChange={updatePasswordField}
          error={passwordFieldErrors.current_password}
          autoComplete="current-password"
        />
        <PasswordField
          id="profile-new-password"
          name="new_password"
          label="New password"
          value={passwordForm.new_password}
          onChange={updatePasswordField}
          error={passwordFieldErrors.new_password}
          showStrength
          autoComplete="new-password"
        />
        <PasswordField
          id="profile-confirm-password"
          name="confirm_password"
          label="Confirm new password"
          value={passwordForm.confirm_password}
          onChange={updatePasswordField}
          error={passwordFieldErrors.confirm_password}
          autoComplete="new-password"
          placeholder="Enter the new password again"
        />
        <div className="modal-actions profile-form-actions">
          <button className="primary-button" type="submit" disabled={changingPassword || submitting}>
            {changingPassword && <span className="spinner" aria-hidden="true" />}
            {changingPassword ? 'Changing password…' : 'Change password'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

function UsersPage({ tokens, onSessionExpired, onTokensChanged }) {
  const {
    data: users,
    setData: setUsers,
    loading,
    error,
    retry,
  } = useProtectedList({
    tokens,
    onSessionExpired,
    onTokensChanged,
    load: listUsers,
    resource: 'users',
  })
  const [actionLoading, setActionLoading] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [userToDeactivate, setUserToDeactivate] = useState(null)
  const tokensRef = useRef(tokens)

  useEffect(() => {
    tokensRef.current = tokens
  }, [tokens])

  function applyUserUpdate(updatedUser) {
    setUsers((current) =>
      current
        ? current.map((user) =>
            user.id === updatedUser.id ? updatedUser : user,
          )
        : current,
    )
  }

  async function handleRoleChange(user, nextRole) {
    if (actionLoading || user.role === nextRole || user.role === 'admin' || !user.is_active) {
      return
    }

    setActionLoading(`role-${user.id}`)
    setActionError(null)
    try {
      const result = await changeUserRole({
        tokens: tokensRef.current,
        userId: user.id,
        role: nextRole,
      })
      if (result.tokens.access_token !== tokensRef.current.access_token) {
        tokensRef.current = result.tokens
        onTokensChanged(result.tokens)
      }
      applyUserUpdate(result.data)
    } catch (requestError) {
      if (requestError instanceof SessionExpiredError) {
        onSessionExpired(requestError.message)
        return
      }
      setActionError(getResourceErrorMessage(requestError, 'the user role'))
    } finally {
      setActionLoading(null)
    }
  }

  function requestDeactivation(user) {
    if (actionLoading || user.role === 'admin' || !user.is_active) return

    setActionError(null)
    setUserToDeactivate(user)
  }

  async function handleDeactivate() {
    const user = userToDeactivate
    if (!user || actionLoading || user.role === 'admin' || !user.is_active) return

    setActionLoading(`status-${user.id}`)
    setActionError(null)
    try {
      const result = await deactivateUser({
        tokens: tokensRef.current,
        userId: user.id,
      })
      if (result.tokens.access_token !== tokensRef.current.access_token) {
        tokensRef.current = result.tokens
        onTokensChanged(result.tokens)
      }
      applyUserUpdate(result.data)
      setUserToDeactivate(null)
    } catch (requestError) {
      if (requestError instanceof SessionExpiredError) {
        onSessionExpired(requestError.message)
        return
      }
      setActionError(getResourceErrorMessage(requestError, 'the account status'))
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <section className="events-content" aria-labelledby="users-title">
      <div className="events-intro">
        <div>
          <p className="eyebrow">Administration</p>
          <h1 id="users-title">Users</h1>
          <p>Review registered accounts and their access roles.</p>
        </div>
        {users && <p className="events-count">{users.length} users</p>}
      </div>
      <Alert>{actionError}</Alert>

      {error ? (
        <ResourceError title="Users could not be loaded" message={error} onRetry={retry} />
      ) : loading ? (
        <div
          className="data-panel skeleton-block data-loading"
          aria-label="Loading users"
          aria-busy="true"
        />
      ) : users.length === 0 ? (
        <div className="events-state">
          <span className="state-icon state-icon-empty" aria-hidden="true">◇</span>
          <h2>No users found</h2>
        </div>
      ) : (
        <div className="data-panel table-scroll">
          <table className="data-table">
            <thead><tr><th>User</th><th>Role</th><th>Status</th><th>Joined</th></tr></thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td><strong>{user.name}</strong><span>{user.email}</span></td>
                  <td>
                    {user.role === 'admin' ? (
                      <span className="role-badge" title="Admin roles cannot be changed">
                        admin
                      </span>
                    ) : (
                      <select
                        className="user-role-select"
                        value={user.role}
                        onChange={(event) => handleRoleChange(user, event.target.value)}
                        disabled={!user.is_active || Boolean(actionLoading)}
                        aria-label={`Change ${user.name}'s role`}
                      >
                        {REGISTERABLE_ROLES.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    )}
                  </td>
                  <td>
                    {user.role !== 'admin' && user.is_active ? (
                      <button
                        className="deactivate-user-button"
                        type="button"
                        onClick={() => requestDeactivation(user)}
                        disabled={Boolean(actionLoading)}
                      >
                        {actionLoading === `status-${user.id}`
                          ? 'Deactivating…'
                          : 'Deactivate'}
                      </button>
                    ) : (
                      <span className={`account-status ${user.is_active ? 'account-active' : ''}`}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    )}
                  </td>
                  <td>{formatDateTime(user.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {userToDeactivate && (
        <ConfirmationModal
          title={`Deactivate ${userToDeactivate.name}?`}
          description="This user will immediately lose access, and their active sessions will be revoked. The current backend does not provide a way to reactivate the account."
          confirmLabel="Deactivate user"
          cancelLabel="Keep active"
          onClose={() => setUserToDeactivate(null)}
          onConfirm={handleDeactivate}
          submitting={actionLoading === `status-${userToDeactivate.id}`}
        />
      )}
    </section>
  )
}

function formatAuditAction(action) {
  if (typeof action !== 'string') return 'Activity recorded'
  const [entity, verb] = action.split('.')
  const entityLabel = `${entity?.charAt(0).toUpperCase()}${entity?.slice(1)}`
  return `${entityLabel} ${verb?.replaceAll('_', ' ') || ''}`.trim()
}

function LogsPage(props) {
  const {
    data: logs,
    loading,
    error,
    retry,
  } = useProtectedList({ ...props, load: listAuditLogs, resource: 'audit logs' })

  return (
    <section className="events-content" aria-labelledby="logs-title">
      <div className="events-intro">
        <div>
          <p className="eyebrow">Administration</p>
          <h1 id="logs-title">Audit logs</h1>
          <p>See the latest important activity across EventDesk.</p>
        </div>
        {logs && <p className="events-count">{logs.length} entries</p>}
      </div>

      {error ? (
        <ResourceError
          title="Audit logs could not be loaded"
          message={error}
          onRetry={retry}
        />
      ) : loading ? (
        <div
          className="data-panel skeleton-block data-loading"
          aria-label="Loading audit logs"
          aria-busy="true"
        />
      ) : logs.length === 0 ? (
        <div className="events-state">
          <span className="state-icon state-icon-empty" aria-hidden="true">◇</span>
          <h2>No audit activity yet</h2>
        </div>
      ) : (
        <div className="log-list">
          {logs.map((log) => (
            <article className="log-item" key={log.id}>
              <span className="log-icon"><AppIcon type="logs" /></span>
              <div>
                <h2>{formatAuditAction(log.action)}</h2>
                <p>
                  <span>{log.entity_type}</span>{' '}
                  <code title={log.entity_id}>{shortId(log.entity_id)}</code>
                  {' · '}Actor{' '}
                  <code title={log.actor_id || ''}>
                    {log.actor_id ? shortId(log.actor_id) : 'System'}
                  </code>
                </p>
              </div>
              <time dateTime={log.created_at}>{formatDateTime(log.created_at)}</time>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

function formatNotificationType(type) {
  const labels = {
    booking_confirmed: 'Booking confirmed',
    booking_cancelled: 'Booking cancelled',
    event_cancelled: 'Event cancelled',
    event_reminder: 'Event reminder',
    event_reviewed: 'New review',
    review_replied: 'Review reply',
  }
  return labels[type] || 'Notification'
}

function validateNotificationList(payload) {
  return (
    Array.isArray(payload) &&
    payload.every(
      (item) =>
        item &&
        typeof item.id === 'string' &&
        typeof item.message === 'string' &&
        typeof item.type === 'string',
    )
  )
}

const NOTIFICATION_CONTEXTS = [
  { key: 'all', label: 'All' },
  { key: 'booking', label: 'Bookings' },
  { key: 'review', label: 'Reviews' },
]

function matchesNotificationContext(notification, context) {
  if (context === 'booking') return Boolean(notification.related_booking_id)
  if (context === 'review') return Boolean(notification.related_review_id)
  return true
}

function NotificationsPage({
  tokens,
  onSessionExpired,
  onTokensChanged,
  subscribeToNotifications,
  onNotificationRead,
  onAllNotificationsRead,
}) {
  const [context, setContext] = useState('all')
  const [notifications, setNotifications] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [retryCount, setRetryCount] = useState(0)
  const [actionLoading, setActionLoading] = useState(null)
  const [actionNotice, setActionNotice] = useState('')
  const [actionError, setActionError] = useState(null)
  const tokensRef = useRef(tokens)

  useEffect(() => {
    tokensRef.current = tokens
  }, [tokens])

  useEffect(() => {
    let cancelled = false

    async function loadNotifications() {
      setLoading(true)
      setError(null)
      try {
        const result = await listNotifications({
          tokens: tokensRef.current,
          context,
        })
        if (!validateNotificationList(result.data)) {
          throw new Error('Invalid notifications response.')
        }
        if (!cancelled) {
          if (result.tokens.access_token !== tokensRef.current.access_token) {
            tokensRef.current = result.tokens
            onTokensChanged(result.tokens)
          }
          setNotifications(result.data)
          setLoading(false)
        }
      } catch (requestError) {
        if (cancelled) return
        if (requestError instanceof SessionExpiredError) {
          onSessionExpired(requestError.message)
          return
        }
        setError(getResourceErrorMessage(requestError, 'notifications'))
        setLoading(false)
      }
    }

    loadNotifications()
    return () => {
      cancelled = true
    }
  }, [context, onSessionExpired, onTokensChanged, retryCount])

  useEffect(() => {
    return subscribeToNotifications((incomingNotification) => {
      if (!matchesNotificationContext(incomingNotification, context)) return

      setNotifications((current) => {
        if (!current) return current
        const existingIndex = current.findIndex(
          (item) => item.id === incomingNotification.id,
        )
        if (existingIndex === -1) return [incomingNotification, ...current]

        const next = [...current]
        next[existingIndex] = incomingNotification
        return next
      })
    })
  }, [context, subscribeToNotifications])

  useEffect(() => {
    if (!actionNotice) return undefined
    const timer = window.setTimeout(() => setActionNotice(''), 4000)
    return () => window.clearTimeout(timer)
  }, [actionNotice])

  async function handleMarkRead(notificationId) {
    if (actionLoading) return
    const currentNotification = notifications?.find(
      (item) => item.id === notificationId,
    )
    if (!currentNotification || currentNotification.read_at) return

    setActionLoading(notificationId)
    setActionError(null)

    try {
      const result = await markNotificationRead({
        tokens: tokensRef.current,
        notificationId,
      })
      if (result.tokens.access_token !== tokensRef.current.access_token) {
        tokensRef.current = result.tokens
        onTokensChanged(result.tokens)
      }
      setNotifications((current) =>
        current
          ? current.map((item) =>
              item.id === notificationId ? result.data : item,
            )
          : current,
      )
      onNotificationRead(result.data)
    } catch (requestError) {
      if (requestError instanceof SessionExpiredError) {
        onSessionExpired(requestError.message)
        return
      }
      setActionError(
        getResourceErrorMessage(requestError, 'the notification update'),
      )
    } finally {
      setActionLoading(null)
    }
  }

  async function handleMarkAllRead() {
    if (actionLoading || !notifications || unreadCount === 0) return
    setActionLoading('all')
    setActionError(null)

    try {
      const result = await markAllNotificationsRead({
        tokens: tokensRef.current,
      })
      if (result.tokens.access_token !== tokensRef.current.access_token) {
        tokensRef.current = result.tokens
        onTokensChanged(result.tokens)
      }
      const readAt = new Date().toISOString()
      setNotifications((current) =>
        current
          ? current.map((item) => ({
              ...item,
              read_at: item.read_at || readAt,
            }))
          : current,
      )
      onAllNotificationsRead()
      setActionNotice(
        result.data.updated_count > 0
          ? `Marked ${result.data.updated_count} notification${result.data.updated_count === 1 ? '' : 's'} as read.`
          : 'All notifications are read.',
      )
    } catch (requestError) {
      if (requestError instanceof SessionExpiredError) {
        onSessionExpired(requestError.message)
        return
      }
      setActionError(
        getResourceErrorMessage(requestError, 'the notification update'),
      )
    } finally {
      setActionLoading(null)
    }
  }

  const unreadCount = notifications
    ? notifications.filter((item) => !item.read_at).length
    : 0

  return (
    <section className="events-content notifications-content" aria-labelledby="notifications-title">
      <div className="events-intro notifications-intro">
        <div>
          <p className="eyebrow">Updates &amp; Alerts</p>
          <h1 id="notifications-title">Notifications</h1>
          <p>Stay informed about your bookings, reviews, and event changes.</p>
        </div>
        <div className="notifications-header-actions">
          {actionNotice && (
            <span className="action-notice" role="status">
              ✓ {actionNotice}
            </span>
          )}
          <button
            className="secondary-button mark-all-read-button"
            type="button"
            onClick={handleMarkAllRead}
            disabled={loading || unreadCount === 0 || actionLoading === 'all'}
          >
            {actionLoading === 'all' ? 'Marking all...' : 'Mark all as read'}
          </button>
        </div>
      </div>

      <div className="notification-context-tabs" role="tablist" aria-label="Notification categories">
        {NOTIFICATION_CONTEXTS.map((item) => (
          <button
            key={item.key}
            role="tab"
            aria-selected={context === item.key}
            className={`context-tab ${context === item.key ? 'context-tab-active' : ''}`}
            onClick={() => setContext(item.key)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </div>

      <Alert>{actionError}</Alert>

      {error ? (
        <ResourceError
          title="Notifications could not be loaded"
          message={error}
          onRetry={() => setRetryCount((count) => count + 1)}
        />
      ) : loading ? (
        <div className="notification-list" aria-label="Loading notifications" aria-busy="true">
          {Array.from({ length: 4 }, (_, index) => (
            <div
              className="notification-card notification-card-skeleton skeleton-block"
              key={index}
            />
          ))}
        </div>
      ) : notifications.length === 0 ? (
        <div className="events-state">
          <span className="state-icon state-icon-empty" aria-hidden="true">🔔</span>
          <h2>No {context !== 'all' ? `${context} ` : ''}notifications</h2>
          <p>
            {context === 'all'
              ? 'When events, bookings, or reviews have updates, they will appear here in real time.'
              : `You have no ${context}-related notifications right now.`}
          </p>
        </div>
      ) : (
        <div className="notification-list">
          {notifications.map((notification) => {
            const isUnread = !notification.read_at
            const isItemActionLoading = actionLoading === notification.id

            return (
              <article
                className={`notification-card ${isUnread ? 'notification-unread' : ''}`}
                key={notification.id}
              >
                <div className={`notification-icon-wrapper notification-type-${notification.type}`}>
                  <NotificationIcon type={notification.type} />
                </div>
                <div className="notification-main">
                  <div className="notification-top">
                    <div className="notification-type-wrap">
                      <span className={`notification-badge-pill pill-${notification.type}`}>
                        {formatNotificationType(notification.type)}
                      </span>
                      {isUnread && <span className="unread-dot" title="Unread" />}
                    </div>
                    <time dateTime={notification.created_at} className="notification-time">
                      {formatDateTime(notification.created_at)}
                    </time>
                  </div>
                  <p className="notification-message">{notification.message}</p>
                  <div className="notification-meta">
                    {notification.related_booking_id && (
                      <small title={notification.related_booking_id}>
                        Booking #{shortId(notification.related_booking_id)}
                      </small>
                    )}
                    {notification.related_review_id && (
                      <small title={notification.related_review_id}>
                        Review #{shortId(notification.related_review_id)}
                      </small>
                    )}
                  </div>
                </div>
                <div className="notification-actions">
                  {isUnread ? (
                    <button
                      className="mark-read-button"
                      type="button"
                      onClick={() => handleMarkRead(notification.id)}
                      disabled={isItemActionLoading}
                      title="Mark as read"
                    >
                      {isItemActionLoading ? 'Saving...' : 'Mark as read'}
                    </button>
                  ) : (
                    <span className="read-status-label">Read</span>
                  )}
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}

function AuthVisual({ view }) {
  const isSignup = view === 'signup'

  return (
    <aside className="auth-visual">
      <BrandMark />
      <div className="visual-copy">
        <p className="visual-kicker">One desk. Every moment.</p>
        <h2>
          Turn plans into
          <span> experiences.</span>
        </h2>
        <p>
          {isSignup
            ? 'Join a place built for effortless discovery, thoughtful planning, and events worth remembering.'
            : 'Your events, bookings, and next great experience are right where you left them.'}
        </p>
      </div>

      <div className="event-preview" aria-hidden="true">
        <div className="preview-date">
          <span>OCT</span>
          <strong>24</strong>
        </div>
        <div className="preview-copy">
          <span className="preview-pill">Featured event</span>
          <strong>Designing tomorrow</strong>
          <small>City Hall · 6:30 PM</small>
        </div>
        <div className="preview-avatars">
          <span>AM</span>
          <span>SK</span>
          <span>+8</span>
        </div>
      </div>

      <p className="visual-footer">Discover · Create · Connect</p>
      <div className="visual-glow visual-glow-one" />
      <div className="visual-glow visual-glow-two" />
    </aside>
  )
}

const APP_PAGES = [
  'events',
  'bookings',
  'reviews',
  'notifications',
  'users',
  'logs',
]

function getInitialAppPage() {
  const page = window.location.pathname.slice(1)
  return APP_PAGES.includes(page) ? page : 'events'
}

function getInitialView() {
  return window.location.pathname === '/signup' ? 'signup' : 'login'
}

function App() {
  const [view, setView] = useState(getInitialView)
  const [appPage, setAppPage] = useState(getInitialAppPage)
  const [loginEmail, setLoginEmail] = useState('')
  const [notice, setNotice] = useState('')
  const [noticeType, setNoticeType] = useState('success')
  const [loggingOut, setLoggingOut] = useState(false)
  const [createEventOpen, setCreateEventOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [currentUser, setCurrentUser] = useState(null)
  const [eventReloadVersion, setEventReloadVersion] = useState(0)
  const [appNotice, setAppNotice] = useState('')
  const [unreadNotificationsCount, setUnreadNotificationsCount] = useState(0)
  const [liveToast, setLiveToast] = useState(null)
  const unreadNotificationIdsRef = useRef(new Set())
  const seenNotificationIdsRef = useRef(new Set())
  const notificationBootstrapRef = useRef(true)
  const notificationListenersRef = useRef(new Set())
  const [session, setSession] = useState(() => {
    const tokens = getStoredTokens()

    if (!tokens) return { status: 'anonymous', tokens: null }
    if (!isAccessTokenExpired(tokens.access_token)) {
      return { status: 'authenticated', tokens }
    }

    return { status: 'restoring', tokens }
  })

  useEffect(() => {
    function handlePopState() {
      setView(getInitialView())
      setAppPage(getInitialAppPage())
      setNotice('')
      setNoticeType('success')
    }

    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  useEffect(() => {
    if (session.status !== 'restoring') return undefined

    let cancelled = false

    async function restoreSession() {
      try {
        const response = await refreshAccessToken(session.tokens.refresh_token)
        const tokens = updateAccessToken(response.access_token)
        if (!cancelled) setSession({ status: 'authenticated', tokens })
      } catch {
        clearTokens()
        if (!cancelled) {
          setSession({ status: 'anonymous', tokens: null })
          setView('login')
          setNoticeType('error')
          setNotice('Your session has expired. Please log in again.')
          window.history.replaceState({}, '', '/login')
        }
      }
    }

    restoreSession()
    return () => {
      cancelled = true
    }
  }, [session])

  function navigate(nextView, event) {
    event?.preventDefault()
    const path = nextView === 'login' ? '/login' : '/signup'
    window.history.pushState({}, '', path)
    setView(nextView)
    setNotice('')
    setNoticeType('success')
  }

  function handleRegistered(user) {
    setLoginEmail(user.email)
    window.history.pushState({}, '', '/login')
    setView('login')
    setNoticeType('success')
    setNotice(`Account created for ${user.email}. Log in to continue.`)
  }

  function handleAuthenticated(tokens, userHint = {}) {
    unreadNotificationIdsRef.current.clear()
    seenNotificationIdsRef.current.clear()
    notificationBootstrapRef.current = true
    setUnreadNotificationsCount(0)
    setLiveToast(null)
    setCurrentUser(userHint)
    setSession({ status: 'authenticated', tokens })
    setAppPage('events')
    setNotice('')
    window.history.replaceState({}, '', '/events')
  }

  const handleTokensChanged = useCallback((tokens) => {
    const refreshedRole = getAccessTokenClaims(tokens.access_token)?.role
    if (typeof refreshedRole === 'string') {
      setCurrentUser((current) => ({ ...current, role: refreshedRole }))
    }
    setSession({ status: 'authenticated', tokens })
  }, [])

  const handleAppNavigate = useCallback((nextPage, event) => {
    event?.preventDefault()
    if (!APP_PAGES.includes(nextPage)) return
    window.history.pushState({}, '', `/${nextPage}`)
    setAppPage(nextPage)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  const syncUnreadNotifications = useCallback((notifications) => {
    const unreadIds = new Set(
      notifications.filter((notification) => !notification.read_at).map(
        (notification) => notification.id,
      ),
    )
    seenNotificationIdsRef.current = new Set(
      notifications.map((notification) => notification.id),
    )
    unreadNotificationIdsRef.current = unreadIds
    setUnreadNotificationsCount(unreadIds.size)
  }, [])

  const handleNotificationRead = useCallback((notification) => {
    if (!notification.read_at) return
    unreadNotificationIdsRef.current.delete(notification.id)
    setUnreadNotificationsCount(unreadNotificationIdsRef.current.size)
  }, [])

  const handleAllNotificationsRead = useCallback(() => {
    unreadNotificationIdsRef.current.clear()
    setUnreadNotificationsCount(0)
  }, [])

  const subscribeToNotifications = useCallback((listener) => {
    notificationListenersRef.current.add(listener)
    return () => notificationListenersRef.current.delete(listener)
  }, [])

  useEffect(() => {
    if (!appNotice) return undefined
    const timer = window.setTimeout(() => setAppNotice(''), 4500)
    return () => window.clearTimeout(timer)
  }, [appNotice])

  const handleSessionExpired = useCallback((message) => {
    clearTokens()
    unreadNotificationIdsRef.current.clear()
    seenNotificationIdsRef.current.clear()
    notificationBootstrapRef.current = true
    setUnreadNotificationsCount(0)
    setLiveToast(null)
    setSession({ status: 'anonymous', tokens: null })
    setLoggingOut(false)
    setCreateEventOpen(false)
    setProfileOpen(false)
    setCurrentUser(null)
    setView('login')
    setNoticeType('error')
    setNotice(message || 'Your session has expired. Please log in again.')
    window.history.replaceState({}, '', '/login')
  }, [])

  const handlePasswordChanged = useCallback(() => {
    clearTokens()
    unreadNotificationIdsRef.current.clear()
    seenNotificationIdsRef.current.clear()
    notificationBootstrapRef.current = true
    setUnreadNotificationsCount(0)
    setLiveToast(null)
    setSession({ status: 'anonymous', tokens: null })
    setCreateEventOpen(false)
    setProfileOpen(false)
    setCurrentUser(null)
    setView('login')
    setNoticeType('success')
    setNotice('Your password was changed. Log in again with your new password.')
    window.history.replaceState({}, '', '/login')
  }, [])

  async function handleLogout() {
    setLoggingOut(true)

    try {
      await logOut(session.tokens.refresh_token)
    } catch {
      // Local credentials still need to be removed if the refresh token is
      // invalid or the API is temporarily unreachable.
    } finally {
      clearTokens()
      unreadNotificationIdsRef.current.clear()
      seenNotificationIdsRef.current.clear()
      notificationBootstrapRef.current = true
      setUnreadNotificationsCount(0)
      setLiveToast(null)
      setSession({ status: 'anonymous', tokens: null })
      setLoggingOut(false)
      setCreateEventOpen(false)
      setProfileOpen(false)
      setCurrentUser(null)
      setView('login')
      window.history.replaceState({}, '', '/login')
      setNoticeType('success')
      setNotice('You have been logged out successfully.')
    }
  }

  const isAuthenticated = session.status === 'authenticated'

  const handleNotificationReceived = useCallback((notification) => {
    if (notification.read_at || seenNotificationIdsRef.current.has(notification.id)) {
      return
    }
    seenNotificationIdsRef.current.add(notification.id)
    unreadNotificationIdsRef.current.add(notification.id)
    setUnreadNotificationsCount(unreadNotificationIdsRef.current.size)
    if (notificationBootstrapRef.current) return
    notificationListenersRef.current.forEach((listener) => listener(notification))
    setLiveToast({
      id: notification.id,
      message: notification.message,
      type: notification.type,
    })
  }, [])

  useNotifications({
    enabled: isAuthenticated,
    tokens: session.tokens,
    onNotificationReceived: handleNotificationReceived,
    onSessionExpired: handleSessionExpired,
    onTokensChanged: handleTokensChanged,
  })

  useEffect(() => {
    if (!isAuthenticated) return undefined

    let cancelled = false
    async function loadInitialUnread() {
      try {
        const result = await listNotifications({
          tokens: session.tokens,
          context: 'all',
        })
        if (!cancelled && validateNotificationList(result.data)) {
          if (result.tokens.access_token !== session.tokens.access_token) {
            handleTokensChanged(result.tokens)
          }
          syncUnreadNotifications(result.data)
        }
      } catch (error) {
        if (!cancelled && error instanceof SessionExpiredError) {
          handleSessionExpired(error.message)
        }
      } finally {
        if (!cancelled) notificationBootstrapRef.current = false
      }
    }

    loadInitialUnread()
    return () => {
      cancelled = true
    }
  }, [
    handleSessionExpired,
    handleTokensChanged,
    isAuthenticated,
    session.tokens,
    syncUnreadNotifications,
  ])

  useEffect(() => {
    if (!liveToast) return undefined
    const timer = window.setTimeout(() => setLiveToast(null), 6000)
    return () => window.clearTimeout(timer)
  }, [liveToast])

  const eventMetadata = useEventMetadata({
    enabled: isAuthenticated,
    tokens: session.tokens,
    onSessionExpired: handleSessionExpired,
    onTokensChanged: handleTokensChanged,
  })
  const claims = isAuthenticated
    ? getAccessTokenClaims(session.tokens.access_token)
    : null
  const tokenRole = typeof claims?.role === 'string' ? claims.role : 'attendee'
  const role = currentUser?.role || tokenRole
  const currentUserId = typeof claims?.sub === 'string' ? claims.sub : null
  const isAdminPage = ['users', 'logs'].includes(appPage)
  const isReviewPage = appPage === 'reviews'
  const isRestrictedPage =
    (isAdminPage && role !== 'admin') ||
    (isReviewPage && !['organizer', 'admin'].includes(role))
  const resolvedPage = isRestrictedPage ? 'events' : appPage

  function handleEventCreated(event) {
    setCreateEventOpen(false)
    setAppPage('events')
    setEventReloadVersion((version) => version + 1)
    setAppNotice(`${event.title} was created and published.`)
    window.history.pushState({}, '', '/events')
  }

  function handleProfileUpdated(updatedUser) {
    setCurrentUser(updatedUser)
    setAppNotice('Your profile was updated.')
  }

  useEffect(() => {
    if (isAuthenticated && resolvedPage !== appPage) {
      window.history.replaceState({}, '', `/${resolvedPage}`)
    }
  }, [appPage, isAuthenticated, resolvedPage])

  if (isAuthenticated) {
    const pageProps = {
      tokens: session.tokens,
      onSessionExpired: handleSessionExpired,
      onTokensChanged: handleTokensChanged,
    }
    const pageContent = {
      events: (
        <EventsPage
          {...pageProps}
          metadata={eventMetadata}
          currentUserId={currentUserId}
          role={role}
          key={`${eventReloadVersion}-${role}`}
        />
      ),
      bookings: <BookingsPage {...pageProps} />,
      reviews: <ReviewsPage {...pageProps} role={role} />,
      notifications: (
        <NotificationsPage
          {...pageProps}
          onNotificationRead={handleNotificationRead}
          onAllNotificationsRead={handleAllNotificationsRead}
          subscribeToNotifications={subscribeToNotifications}
        />
      ),
      users: <UsersPage {...pageProps} />,
      logs: <LogsPage {...pageProps} />,
    }[resolvedPage]

    return (
      <ApplicationShell
        role={role}
        profile={currentUser}
        currentPage={resolvedPage}
        onNavigate={handleAppNavigate}
        onCreateEvent={() => setCreateEventOpen(true)}
        onOpenProfile={() => setProfileOpen(true)}
        onLogout={handleLogout}
        loggingOut={loggingOut}
        unreadNotificationsCount={unreadNotificationsCount}
      >
        {appNotice && <div className="app-toast" role="status">✓ {appNotice}</div>}
        {liveToast && (
          <div className="notification-toast" role="status">
            <div className="notification-toast-content">
              <span className="notification-toast-icon">🔔</span>
              <div>
                <strong>{formatNotificationType(liveToast.type)}</strong>
                <p>{liveToast.message}</p>
              </div>
            </div>
            <button
              className="notification-toast-view"
              type="button"
              onClick={() => {
                setLiveToast(null)
                handleAppNavigate('notifications')
              }}
            >
              View
            </button>
            <button
              className="notification-toast-close"
              type="button"
              onClick={() => setLiveToast(null)}
              aria-label="Dismiss notification toast"
            >
              ×
            </button>
          </div>
        )}
        {pageContent}
        {createEventOpen && ['organizer', 'admin'].includes(role) && (
          <CreateEventModal
            tokens={session.tokens}
            onClose={() => setCreateEventOpen(false)}
            onCreated={handleEventCreated}
            onSessionExpired={handleSessionExpired}
            onTokensChanged={handleTokensChanged}
            metadata={eventMetadata}
          />
        )}
        {profileOpen && (
          <ProfileModal
            tokens={session.tokens}
            profile={currentUser}
            role={role}
            onClose={() => setProfileOpen(false)}
            onUpdated={handleProfileUpdated}
            onPasswordChanged={handlePasswordChanged}
            onSessionExpired={handleSessionExpired}
            onTokensChanged={handleTokensChanged}
          />
        )}
      </ApplicationShell>
    )
  }

  return (
    <main className="auth-page">
      <AuthVisual view={view} />
      <section className="auth-content">
        <div className="mobile-brand">
          <BrandMark />
        </div>

        {session.status === 'restoring' ? (
          <div className="session-loader" role="status">
            <span className="spinner" aria-hidden="true" />
            Restoring your session…
          </div>
        ) : view === 'signup' ? (
          <SignupForm
            onRegistered={handleRegistered}
            onSwitch={(event) => navigate('login', event)}
          />
        ) : (
          <LoginForm
            initialEmail={loginEmail}
            notice={notice}
            noticeType={noticeType}
            onAuthenticated={handleAuthenticated}
            onSwitch={(event) => navigate('signup', event)}
          />
        )}
      </section>
    </main>
  )
}

export default App
