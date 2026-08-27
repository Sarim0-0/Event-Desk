# EventDesk frontend

React and Vite frontend for EventDesk.

## Local development

Start the FastAPI backend on `http://127.0.0.1:8000`, then run:

```sh
npm install
npm run dev
```

The frontend sends requests to `/api` by default. Vite proxies those requests to
the backend address set by `VITE_API_PROXY_TARGET`, avoiding cross-origin browser
requests during local development. Copy `.env.example` to `.env.local` if either
address needs to be changed.

For a deployment, either route `/api` to FastAPI through the web server or set
`VITE_API_BASE_URL` to the public API origin. When using separate origins, add
the public frontend origin to the backend's comma-separated
`CORS_ALLOWED_ORIGINS` setting.

## Authentication behavior

- Signup creates an attendee or organizer through `POST /auth/signup` and then
  sends the user to login.
- Login calls `POST /auth/login` and stores the returned bearer tokens under the
  `eventdesk.auth` local-storage key.
- An expired access token is restored with `POST /auth/refresh` when the app
  opens.
- Logout calls `POST /auth/logout` and always clears the local session.
