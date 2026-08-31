import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ApiError,
  logIn,
  logOut,
  refreshAccessToken,
  signUp,
} from './api/auth.js'
import { listEvents } from './api/events.js'
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
}) {
  const [passwordVisible, setPasswordVisible] = useState(false)
  const checks = useMemo(() => getPasswordChecks(value), [value])
  const strength = getPasswordStrength(value, checks)
  const describedBy = [
    error ? 'password-error' : null,
    showStrength ? 'password-strength' : null,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className="form-field">
      <label htmlFor="password">Password</label>
      <div className={`password-input ${error ? 'input-error' : ''}`}>
        <input
          id="password"
          name="password"
          type={passwordVisible ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          autoComplete={autoComplete}
          maxLength={128}
          aria-invalid={Boolean(error)}
          aria-describedby={describedBy || undefined}
          placeholder={
            showStrength ? 'Create a strong password' : 'Enter your password'
          }
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
      <FieldError id="password-error">{error}</FieldError>

      {showStrength && (
        <div className="password-strength" id="password-strength">
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
      onAuthenticated(tokens)
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

function EventCard({ event, index }) {
  const date = formatEventDate(event.event_datetime)
  const ticketsAvailable = Number(event.tickets_available)
  const ticketLabel =
    ticketsAvailable === 0
      ? 'Sold out'
      : `${ticketsAvailable} ticket${ticketsAvailable === 1 ? '' : 's'} available`

  return (
    <button
      className="event-card"
      type="button"
      aria-label={`View ${event.title}`}
      title="Event details coming soon"
    >
      <div className={`event-card-cover event-theme-${index % EVENT_CARD_THEME_COUNT}`}>
        <span className="event-status">{event.status}</span>
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

function EventsPage({ tokens, onLogout, loggingOut, onSessionExpired }) {
  const [page, setPage] = useState(1)
  const [eventPage, setEventPage] = useState(null)
  const [activeTokens, setActiveTokens] = useState(tokens)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [retryCount, setRetryCount] = useState(0)
  const claims = getAccessTokenClaims(activeTokens.access_token)
  const role = typeof claims?.role === 'string' ? claims.role : 'user'
  const profileInitial = role.charAt(0).toUpperCase()

  useEffect(() => {
    let cancelled = false

    async function loadPage() {
      setLoading(true)
      setError(null)

      try {
        const response = await listEvents({
          accessToken: activeTokens.access_token,
          page,
        })

        if (!validateEventPage(response)) {
          throw new UnexpectedEventResponseError(
            'Invalid paginated event response.',
          )
        }

        if (!cancelled) {
          setEventPage(response)
          setLoading(false)
        }
      } catch (requestError) {
        if (cancelled) return

        if (requestError instanceof ApiError && requestError.status === 401) {
          try {
            const refreshed = await refreshAccessToken(
              activeTokens.refresh_token,
            )
            const nextTokens = updateAccessToken(refreshed.access_token)

            if (!nextTokens) {
              onSessionExpired('Your session has expired. Please log in again.')
              return
            }

            if (!cancelled) setActiveTokens(nextTokens)
          } catch (refreshError) {
            if (cancelled) return

            if (
              refreshError instanceof ApiError &&
              [401, 403].includes(refreshError.status)
            ) {
              onSessionExpired(
                typeof refreshError.payload?.detail === 'string'
                  ? refreshError.payload.detail
                  : 'Your session has expired. Please log in again.',
              )
              return
            }

            setError(getEventErrorMessage(refreshError))
            setLoading(false)
          }
          return
        }

        if (requestError instanceof ApiError && requestError.status === 403) {
          onSessionExpired(
            typeof requestError.payload?.detail === 'string'
              ? requestError.payload.detail
              : 'Your account cannot access events.',
          )
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
  }, [activeTokens, onSessionExpired, page, retryCount])

  const firstVisibleItem = eventPage?.total_items
    ? (eventPage.page - 1) * eventPage.page_size + 1
    : 0
  const lastVisibleItem = eventPage?.total_items
    ? Math.min(
        eventPage.page * eventPage.page_size,
        eventPage.total_items,
      )
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
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <main className="events-page">
      <header className="events-header">
        <BrandMark />
        <div className="events-header-actions">
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
            aria-label={`${role} profile. Profile page coming soon.`}
            title="Profile coming soon"
          >
            {profileInitial}
          </button>
        </div>
      </header>

      <section className="events-content" aria-labelledby="events-title">
        <div className="events-intro">
          <div>
            <p className="eyebrow">Upcoming experiences</p>
            <h1 id="events-title">Explore events</h1>
            <p>Find something worth showing up for.</p>
          </div>
          {!loading && eventPage && (
            <p className="events-count">
              {eventPage.total_items}{' '}
              {eventPage.total_items === 1 ? 'event' : 'events'} available
            </p>
          )}
        </div>

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
            <h2>No upcoming events yet</h2>
            <p>Published events will appear here as soon as they are available.</p>
          </div>
        ) : (
          <>
            <div className="events-grid">
              {eventPage.items.map((event, index) => (
                <EventCard event={event} index={index} key={event.id} />
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
      </section>
    </main>
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

function getInitialView() {
  return ['/login', '/events'].includes(window.location.pathname)
    ? 'login'
    : 'signup'
}

function App() {
  const [view, setView] = useState(getInitialView)
  const [loginEmail, setLoginEmail] = useState('')
  const [notice, setNotice] = useState('')
  const [noticeType, setNoticeType] = useState('success')
  const [loggingOut, setLoggingOut] = useState(false)
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

  function handleAuthenticated(tokens) {
    setSession({ status: 'authenticated', tokens })
    setNotice('')
    window.history.replaceState({}, '', '/events')
  }

  const handleSessionExpired = useCallback((message) => {
    clearTokens()
    setSession({ status: 'anonymous', tokens: null })
    setLoggingOut(false)
    setView('login')
    setNoticeType('error')
    setNotice(message || 'Your session has expired. Please log in again.')
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
      setSession({ status: 'anonymous', tokens: null })
      setLoggingOut(false)
      setView('login')
      window.history.replaceState({}, '', '/login')
      setNoticeType('success')
      setNotice('You have been logged out successfully.')
    }
  }

  const isAuthenticated = session.status === 'authenticated'

  if (isAuthenticated) {
    return (
      <EventsPage
        tokens={session.tokens}
        onLogout={handleLogout}
        loggingOut={loggingOut}
        onSessionExpired={handleSessionExpired}
      />
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
