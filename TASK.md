# HostForGuest — Comprehensive QA & Bug Fix Sprint

## Context
- HostForGuest: Croatian tourist host platform (Next.js frontend + FastAPI backend + PostgreSQL/pgvector)
- Prod on H1: http://127.0.0.1:8000 (API), port 3055 (frontend proxy)
- Docker: hostforguest_prod_api, hostforguest_prod_frontend, hostforguest_prod_postgres, hostforguest_prod_channel_sync

## Known Issues (from user)

### 1. 🔴 My Place — geolocation not auto-filling
**File:** `frontend/src/components/onboarding/host-onboarding.tsx`
**Bug:** When host types an address (e.g. "Oprić 71, Lovran"), the system does NOT automatically geocode it to lat/lng. User has to manually select from Google Places dropdown. If they just type and skip, coordinates stay null.
**Fix:** 
- Add server-side geocode fallback: when address is saved without coordinates, backend should call geocoding API (Nominatim/Google) to resolve lat/lng
- Add `app/api/v1/locations.py` — `/geocode` endpoint that accepts address string, returns {lat, lng, formatted_address}
- Frontend: after address input blurs, call geocode endpoint and auto-populate coordinates
- Show "📍 Location verified" / "⚠️ Could not verify" indicator

### 2. 🔴 Dashboard performance — slow loading
**File:** `frontend/src/components/dashboard/overview-tab.tsx` and widgets
**Bug:** Dashboard loads slowly, especially with lots of data.
**Fix:**
- Add loading skeletons (shimmer) for all dashboard widgets
- Cache host stats in backend (TTL 60s)
- Check for N+1 queries in dashboard API endpoints — use `selectinload` for relationships
- Add `/api/v1/hosts/dashboard/stats` endpoint that returns all dashboard data in ONE call
- Frontend: use React Query/SWR for caching and background refresh

### 3. 🔴 Guest Groups — not saving properly
**Files:** `app/api/v1/guest_groups.py`, `frontend/src/components/dashboard/guest-groups-tab.tsx`, `frontend/src/components/dashboard/group-modals.tsx`
**Bug:** Group creation/update does not persist correctly.
**Fix:**
- Add comprehensive error handling with user-friendly messages
- Validate that group data is complete before save (name, dates required)
- Add save confirmation toast/feedback
- Test: create group → refresh → verify it persists
- Add e2e test for group CRUD

### 4. 🔴 Routes/TNT Points — not saving, needs full feature
**Files:** `frontend/src/components/dashboard/routes-tab.tsx` (725 lines), `app/api/v1/itineraries.py`
**Bug:** Routes tab has NO save functionality. TNT (tourist navigation track) points don't exist yet.
**Fix:**
- Add save/update mutation for routes with all waypoints
- Build TNT point management: add/edit/delete/reorder points on route
- Each TNT point needs: name, lat/lng, description, order_index, estimated_duration
- Backend: `POST/PUT/DELETE /api/v1/routes/{id}/points`
- Frontend: drag-to-reorder points, inline editing
- Map integration: click on map to add TNT point, visualize route path

### 5. 🟡 channel_sync — unhealthy
**Container:** hostforguest_prod_channel_sync (unhealthy)
**Bug:** Health check fails because no channel accounts configured (0 accounts, 0 results)
**Fix:**
- Make health check succeed even with 0 accounts (healthy = running, not healthy = has data)
- OR seed a test channel account for demo purposes
- Fix health endpoint in channel_sync worker

### 6. 🟡 General QA & Polish
- Test ALL host dashboard tabs: Overview, Stay, Routes, Map, Discover, Groups, Insights, Cleaning, Maintenance, Channels, Adaptation
- Test guest flow: login → dashboard → map → preferences
- Verify all CRUD operations work end-to-end
- Fix any console errors in browser
- Mobile responsive check for dashboard

## Technical Constraints
- Next.js App Router, FastAPI, PostgreSQL/pgvector
- Google Maps/Places API for geolocation
- Use Nominatim (free) as geocode fallback
- All mutations must have proper error handling + user feedback
- After fixes, rebuild docker: `docker compose -f docker-compose.vps-prod.yml up -d --build`

## Deliverables
1. Auto-geocoding for My Place addresses
2. Dashboard performance optimizations (skeletons + caching)
3. Guest group save fix with e2e test
4. Routes save + TNT point management (full feature)
5. channel_sync health fix
6. Comprehensive QA report

## Success Criteria
- User types address → coordinates auto-populate
- Dashboard loads in <2s with skeletons
- Groups persist after page refresh
- Routes can be saved with TNT points
- All containers healthy
- At least 3 new e2e tests passing
