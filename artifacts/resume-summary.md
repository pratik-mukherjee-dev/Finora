# Finora — Session Resume (FY gate fixed; next: Purchase screen)

## 1. Project snapshot

**Finora** is an offline-first desktop accounting/billing app for small businesses. Repo (GitLab): [byte-force/Finora](https://gitlab.com/byte-force/Finora), branch `master`, project id `84352998`.

- **Shell:** Tauri v2 (Rust), app id `com.byteforce.finora`. Sidecar-manages a portable PostgreSQL 18.4 and a Django backend frozen to a Windows exe via Nuitka.
- **Backend:** Django + DRF, nine apps under `backend/apps/` (`common, accounts, financialyear, catalogue, parties, stock, vouchers, search, reports`). Auth is **JWT** (`rest_framework_simplejwt`); access-token lifetime 12h. Services/selectors split (write vs read), atomic transactions.
- **Frontend:** SvelteKit SPA (`adapter-static`, SSR off, Svelte 5 runes) in `desktop/src/`. Transport is the **Tauri HTTP plugin** (Rust-side fetch, avoids CORS). API client at `desktop/src/lib/api.ts`; app store at `desktop/src/lib/stores/auth.svelte.ts`.
- **Dev workflow:** `npm run tauri dev` from `desktop\`. Windows, PyCharm, project root `E:\PyCharm\Services\Finora\`, user profile `death`.
- **Working style:** deliver full file contents inline (not diffs) with the file path; one layered build-order step at a time; precise, minimal-token responses; double-check against actual repo code before proposing changes.

## 2. Architecture facts worth remembering

- **DB binding:** Tauri `backend.rs` picks a random `pg_port` per launch, keeps `pgdata` in `%APPDATA%\com.byteforce.finora\pgdata`, writes `runtime.json` (app-data copy) with the sidecar's DB params, and injects `FINORA_RUNTIME_CONFIG` into the frozen Django. `production.py` reads that file for `DATABASES`. A plain `manage.py shell` (no `FINORA_RUNTIME_CONFIG`) hits base.py's **5432 defaults — a DIFFERENT DB**, which caused a lot of false "empty table" confusion earlier. Always inspect the sidecar DB, not 5432.
- **FY list endpoint** returns a **bare array** (DRF pagination is commented out in `config/settings/base.py`). Serializer fields: `id, start_date, end_date, is_active, is_closed, is_writable`.
- **Every voucher/stock endpoint requires an active FY** (`vouchers/views.py::_context` → `financialyear.selectors.active_fy`, raises `FinancialYearLocked` if none). Model enforces one active FY per user via a partial `UniqueConstraint` and a `CheckConstraint(end_date > start_date)`.
- **Boot routing cascade** (`desktop/src/routes/+page.svelte`): `waitForBackend` → `authState` (first-run → `/register`) → `auth.restore()` → `if !isAuthed /login` → `if needsSetup /setup` → `if needsFy /fy` → else `/app`.

## 3. What is built and verified

- Tauri shell + Postgres/Django sidecar wiring + `api.ts` (JWT access/refresh, port discovery via `get_django_port`, `waitForBackend`).
- Auth flow: register (first-run only) → login → logout; refresh token persisted in Tauri `plugin-store` (`session.json`, key `refresh`).
- Company setup flow: mode select (single/multi) → create company → routes to `/fy`.
- **FY gate fully working** (this session's outcome): `/fy` creates the initial active FY, `/app` shell renders and sticks. Verified end-to-end even after wiping `pgdata` + `session.json` + `runtime.json` (clean first-run walks register → mode → company → FY → app).
- **SmartLookup + PartyCreateDialog + ItemCreateDialog** exist and are complete under `desktop/src/lib/components/`, but are **not yet consumed by any screen**. They call `/api/search/suggest/`, `/api/search/record/`, `/api/parties/`, `/api/catalogue/items/`, `/api/catalogue/mappings/`.

## 4. What THIS session fixed (the FY gate saga)

The user was stuck on the FY setup screen; "Start Bookkeeping" appeared to error on the second click. After ruling out (via evidence) several red herrings — token rotation, DB port mismatch, stale exe — the **actual root cause** was found:

- **`desktop/src/routes/app/+page.svelte` had been overwritten with a duplicate copy of the FY setup page.** Its `onMount` guard did `if (!auth.needsFy) goto("/app")` — a redirect to itself. So after FY creation, navigating to `/app` just re-rendered the FY form; the re-POST hit the backend's `open_first_fy` guard and returned 400 "An active financial year already exists."
- The FY was in fact being created correctly on the first attempt (confirmed via a devtools console log of the `ensureFy` POST body + refetch showing `is_active:true`).

**Fix applied:** replaced `desktop/src/routes/app/+page.svelte` with a real app shell (nav rail with Home/Purchase/Sale/Payment/Stock/Reports sections, company switcher in multi mode, FY badge, logout, and a route guard that bounces to `/login`/`/setup`/`/fy` when prerequisites are missing — never to itself). The `/fy` page's `ensureFy` (idempotent: POST, and on conflict refetch + adopt the active FY) works as intended.

Supporting hardening also discussed/applied during the session (verify these are actually in the tree before relying on them): `loadContext` tolerating a `{results:[]}` shape; `restore()` only clearing the session on genuine auth failure and persisting refreshed tokens; `ApiError` flattening DRF field errors into a readable message; `request()` forcing `Content-Type: application/json` when a body is present. `SIMPLE_JWT.ROTATE_REFRESH_TOKENS` was recommended to be `False` (single-user app, no `token_blacklist` app installed) — confirm the running exe reflects the intended setting.

## 5. Exact next step — build the Purchase screen (build-order step 4)

First voucher screen and first consumer of the existing SmartLookup + dialogs. Confirmed backend contract:

- Endpoint: `POST /api/vouchers/purchases/` with body:
  ```json
  { "company": <id>, "party": <id>, "date": "YYYY-MM-DD",
    "number": null,
    "lines": [ { "mapping": <mappingId>, "qty": <n>, "rate": <n> } ] }
  ```
- **Critical:** purchase lines take a `mapping` id (`ItemCompanyMapping`), **not** an item id. The item `suggest` endpoint returns only `{ id, name, base_unit }`. After the user picks an item via SmartLookup, resolve to a per-company mapping via `GET /api/catalogue/mappings/?item=<itemId>&company=<currentCompanyId>` (returns `{ id, item, rate, stock, ... }`) to get the `mapping` id and default `rate`. If no mapping exists for the current company, open `ItemCreateDialog` (creates item + mapping for the current company).
- Use `auth.currentCompany.id` for `company`; rely on the server's active FY for `fy` (resolved server-side in `_context`). `number` can be `null` (server auto-numbers via `VoucherNumberSeq`, high-water template).
- Response (`PurchaseSerializer`): `{ id, company, party, number, date, total_amount, is_cancelled, lines: [{ id, item, item_name, mapping, qty, rate, amount }] }`. Show server-computed `number` and `total_amount` after save.
- Party picked via SmartLookup(type="PARTY") → `PartyCreateDialog` on no-match → `POST /api/parties/`.
- Slot the screen into the `app/+page.svelte` "purchase" section (currently a placeholder), or a `routes/app/purchase` route — match the chosen nav pattern. `PurchaseViewSet` also has a `cancel` action (soft-cancel + reversing entries) for later.

**Before coding Purchase, verify against the repo:** `backend/apps/vouchers/` (`views.py`, `serializers.py`, `urls.py`, `models.py`) to confirm the exact purchase payload/response and the `_context` FY resolution, and `backend/apps/catalogue/` mappings endpoint filters (`?item=&company=`). Read `desktop/src/lib/components/SmartLookup*.svelte`, `ItemCreateDialog`, `PartyCreateDialog` for their prop/event contracts.

## 6. Known caveats / non-blocking

- `SECRET_KEY` is the 22-char dev default → `InsecureKeyLengthWarning` on JWT signing. Set a 32+ byte `SECRET_KEY` in `backend/.env` before shipping.
- `WARNING: Unauthorized: /api/accounts/auth/me/` on boot is expected/harmless: `restore()` probes `/me/` with an empty access token, catches 401, refreshes, retries.
- Orphaned sidecars: if the app is hard-killed, `finora-backend.exe`/`postgres.exe` can linger and lock the exe. `taskkill /F /IM finora-backend.exe /T` (+ `postgres.exe`) to clear. Consider hardening `backend.rs` to reap stale sidecars on startup and ensure `stop()` runs on window close/exit.
- Editing backend logic (DB binding, settings, services) requires **rebuilding the Nuitka exe** (`backend/build_backend.bat`) and copying it into `desktop/src-tauri/resources/backend/finora-backend.exe`; a running exe file-locks the target during copy.
- Don't run `manage.py shell` for ground-truth without pointing it at the sidecar's `runtime.json` — it defaults to 5432, a different DB.
