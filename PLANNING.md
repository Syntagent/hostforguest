# HostForGuest Planning

## Product Direction

HostForGuest helps Croatian accommodation hosts turn local knowledge into a guest-facing guide experience. The platform should stay practical for hosts: fast onboarding, simple access-code sharing, useful attraction curation, and clear operational workflows.

## Current Priorities

1. Stabilize the host dashboard and guest group flows.
2. Keep attraction recommendations grounded in local database content, host contributions, and explicit guest preferences.
3. Make deployment repeatable on a new server using `env.example`, Docker database services, and the documented FastAPI/Next.js runtime.
4. Keep AI integrations optional and fail-soft when keys are missing.
5. Remove obsolete workflow dependencies and keep the codebase self-contained.

## Architecture Notes

- Backend: FastAPI, SQLAlchemy, PostgreSQL/PostGIS, pgvector.
- Frontend: Next.js App Router.
- Support app: Vite day planner.
- Real-time tourism updates: local scraping/Crawl4AI-oriented services.
- Deployment: Docker Compose for databases by default; app containers are behind the `docker-api` profile.

## Engineering Rules

- Prefer host-based development: API on `127.0.0.1:8000`, UI on `127.0.0.1:3055`.
- Keep `.env`, databases, build output, logs, virtualenvs, and `node_modules` out of Git.
- Add tests around shared behavior and API contracts.
- Use explicit environment configuration for production secrets and public URLs.
- Do not add external workflow/project-management dependencies to runtime code.
