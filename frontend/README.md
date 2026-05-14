# HostForGuest Frontend

Next.js frontend for the HostForGuest platform.

## Features

- Host dashboard for guest groups, attractions, routes, cleaning, maintenance, and integrations.
- Guest access-code flow.
- Guest recommendations and map-based attraction discovery.
- Host onboarding and local content management.

## Development

Run from the repository root:

```bash
npm install --prefix frontend
npm run dev:frontend
```

The local app runs at `http://127.0.0.1:3055`.

The frontend loads the root `.env` in development. The API URL should be:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Optional map configuration:

```env
GOOGLE_MAPS_API_KEY=
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=
```

## Build

```bash
npm run build --prefix frontend
```

`next.config.ts` currently allows build completion despite lint/type errors. Treat that as a deployment convenience, not a replacement for code review.

## Routes

- `/` - public entry point
- `/login` - host login
- `/onboarding` - host onboarding
- `/dashboard` - host dashboard
- `/guest/[accessCode]` - guest access
- `/guest/join` - guest join flow

## Notes

Keep generated files (`.next`, `out`, `*.tsbuildinfo`) out of Git. Public service-worker files in `frontend/public` should be reviewed before production because they affect browser caching.
