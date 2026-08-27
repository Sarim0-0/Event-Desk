import { useEffect, useMemo, useState } from 'react'
import {
  ApiError,
  logIn,
  logOut,
  refreshAccessToken,
  signUp,
} from './api/auth.js'
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

function LoginForm({ initialEmail, notice, onAuthenticated, onSwitch }) {
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

      <Alert type="success">{notice}</Alert>
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

function AuthenticatedPanel({ tokens, onLogout, loggingOut }) {
  const claims = getAccessTokenClaims(tokens.access_token)
  const role = claims?.role

  return (
    <div className="auth-form-panel session-panel">
      <div className="success-orbit" aria-hidden="true">
        <span>✓</span>
      </div>
      <div className="form-heading">
        <p className="eyebrow">You’re all set</p>
        <h1>Welcome to EventDesk</h1>
        <p>
          You’re securely signed in{role ? ` as an ${role}` : ''}. Your session
          is ready for the rest of the app.
        </p>
      </div>
      <div className="session-note">
        <span className="status-dot" aria-hidden="true" />
        Active session
      </div>
      <button
        className="secondary-button"
        type="button"
        onClick={onLogout}
        disabled={loggingOut}
      >
        {loggingOut ? 'Logging out…' : 'Log out'}
      </button>
    </div>
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
  return window.location.pathname === '/login' ? 'login' : 'signup'
}

function App() {
  const [view, setView] = useState(getInitialView)
  const [loginEmail, setLoginEmail] = useState('')
  const [notice, setNotice] = useState('')
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
        if (!cancelled) setSession({ status: 'anonymous', tokens: null })
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
  }

  function handleRegistered(user) {
    setLoginEmail(user.email)
    window.history.pushState({}, '', '/login')
    setView('login')
    setNotice(`Account created for ${user.email}. Log in to continue.`)
  }

  function handleAuthenticated(tokens) {
    setSession({ status: 'authenticated', tokens })
    setNotice('')
  }

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
      setNotice('You have been logged out successfully.')
    }
  }

  const isAuthenticated = session.status === 'authenticated'

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
        ) : isAuthenticated ? (
          <AuthenticatedPanel
            tokens={session.tokens}
            onLogout={handleLogout}
            loggingOut={loggingOut}
          />
        ) : view === 'signup' ? (
          <SignupForm
            onRegistered={handleRegistered}
            onSwitch={(event) => navigate('login', event)}
          />
        ) : (
          <LoginForm
            initialEmail={loginEmail}
            notice={notice}
            onAuthenticated={handleAuthenticated}
            onSwitch={(event) => navigate('signup', event)}
          />
        )}
      </section>
    </main>
  )
}

export default App
