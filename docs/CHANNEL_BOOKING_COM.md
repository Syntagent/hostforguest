# Booking.com channel integration

## Environment variables

| Variable | Purpose |
|----------|---------|
| `BOOKING_COM_API_BASE` | Connectivity API base URL (default `https://supply-xml.booking.com`) |
| `BOOKING_COM_MOCK` | `true` to use mock responses (no network; tests / local) |
| `BOOKING_COM_REQUEST_TIMEOUT_SECONDS` | HTTP timeout |
| `BOOKING_COM_MAX_RETRIES` | Retry count for transient failures |
| `CHANNEL_WEBHOOK_SECRET` | HMAC SHA256 secret; webhook must send matching `X-Channel-Signature` header |
| `CHANNEL_ENCRYPTION_KEY` | Optional Fernet key for credentials at rest; if unset, key is derived from `SECRET_KEY` (dev only) |
| `CHANNEL_SYNC_INTERVAL_SEC` | Worker poll interval (default 300) |

## API (authenticated host)

- `POST /api/v1/channel-integrations/booking-com/connect`
- `DELETE /api/v1/channel-integrations/booking-com/disconnect`
- `GET /api/v1/channel-integrations/status`
- `POST /api/v1/channel-integrations/{account_id}/mappings`
- `GET /api/v1/channel-integrations/{account_id}/mappings`
- `POST /api/v1/channel-integrations/{account_id}/sync/full`
- `POST /api/v1/channel-integrations/{account_id}/sync/reservations`
- `POST /api/v1/channel-integrations/{account_id}/push/availability`
- `POST /api/v1/channel-integrations/{account_id}/push/rates`
- `GET /api/v1/channel-integrations/{account_id}/health`
- `POST /api/v1/channel-integrations/events/{event_id}/replay`
- `PATCH /api/v1/channel-integrations/bookings/{booking_id}/ota-override`

## Webhook (no session token)

`POST /api/v1/channel-webhooks/booking-com`  
JSON body: `hotel_id` plus `reservations` array or single reservation object.

## Docker

```bash
docker compose --profile docker-api --profile full up -d --build
```

Services: `api`, `frontend` (if in compose), `channel_sync`, `postgres`.
