# HostForGuest Task Notes

## Ready For Distribution

- [x] Sanitized hardcoded browser API key from the support app.
- [x] Added `DEPLOYMENT.md`.
- [x] Parameterized Docker Compose database credentials.
- [x] Added support app lockfile.
- [x] Published a clean-history snapshot to `https://github.com/Syntagent/hostforguest`.
- [x] Removed obsolete workflow references from active code and public docs.

## Next Technical Work

- [ ] Run a full test pass against a fresh PostgreSQL/Neo4j stack.
- [ ] Add a production reverse-proxy example.
- [ ] Add database migration runner guidance for existing deployments.
- [ ] Review frontend build output and remove generated service-worker files if they are not intentionally source-controlled.
- [ ] Decide whether `.cursor/plans` should stay in the public repo.

## Validation Commands

```bash
docker compose config --quiet
python -m compileall -q app
python -m pytest
npm run build --prefix frontend
npm run build --prefix support_app/day_planner
```

## Deployment Checklist

- [ ] Create `.env` from `env.example`.
- [ ] Set strong `SECRET_KEY`, `POSTGRES_PASSWORD`, and `NEO4J_PASSWORD`.
- [ ] Set `POSTGRES_HOST_AUTH_METHOD=md5` or stronger outside local development.
- [ ] Set `NEXT_PUBLIC_API_URL` to the public API URL.
- [ ] Set `CORS_ORIGINS` to the frontend origin.
- [ ] Keep `BOOKING_COM_MOCK=true` until real channel credentials are ready.
