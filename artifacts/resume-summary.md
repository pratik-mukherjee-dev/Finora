Before the handoff, one honest note: the fact that it landed on `/fy` again means boot decided `needsFy` is true, which means `loadContext()` fetched `GET /api/fy/` and found no active, open financial year — even though the earlier "already exists" proves one was created. That read/write mismatch is the crux the next session has to resolve empirically (it can't be reasoned out from here without seeing the actual table + the actual API response). The resume below front-loads exactly how to do that.

Here's a complete handoff you can save to `read_here_to_resume.txt` (or `artifacts/resume-summary.md`) and open a fresh Opus 4.8 session with.

---

# Finora — Session Resume (Frontend: FY gate + app shell)

## 1. Project snapshot

**Finora** is an offline-first desktop accounting/billing app for small businesses. Repo: `github.com/pratik-mukherjee-dev/Finora.git`.

- **Shell:** Tauri v2 (Rust), app id `com.byteforce.finora`. Sidecar-manages a portable PostgreSQL 18.4 and a Django backend frozen to a Windows exe via Nuitka.
- **Backend:** Django + DRF, nine apps under `backend/apps/` (`common, accounts, financialyear, catalogue, parties, stock, vouchers, search, reports`). Auth is **JWT** (`rest_framework_simplejwt`), access-token lifetime 12h.
- **Frontend:** SvelteKit SPA (`adapter-static`, SSR off, Svelte 5 runes) in `desktop/src/`. Transport is the **Tauri HTTP plugin** (Rust-side fetch) to avoid CORS, not webview fetch. API client at `desktop/src/lib/api.ts`.
- **Dev workflow:** `npm run tauri dev` from `desktop\`. Windows, PyCharm, project root `E:\PyCharm\Services\Finora\`, user profile `death`.
- **Working style:** deliver full file contents inline (not diffs), one layered build-order step at a time.

## 2. What is already built and verified

- Tauri shell + Postgres/Django sidecar wiring + `api.ts` (JWT access/refresh, port discovery via `get_django_port`, `waitForBackend`).
- Auth flow: register (first-run only) → login → logout, tokens persisted in Tauri `plugin-store` (`session.json`, key `refresh`).
- Company setup flow: mode select (single/multi) → create company.
- **SmartLookup + PartyCreateDialog + ItemCreateDialog** components exist and are complete (`desktop/src/lib/components/`), but are **not yet consumed by any screen**. They call `/api/search/suggest/`, `/api/search/record/`, `/api/parties/`, `/api/catalogue/items/`, `/api/catalogue/mappings/`.

## 3. What this session added (the FY gate + real app shell)

Goal was the next build-order step. Discovered a hard prerequisite: **every voucher/stock endpoint requires an active financial year** (`vouchers/views.py::_context` → `financialyear.selectors.active_fy`, raising `FinancialYearLocked` if none), but nothing in register→login→mode→company ever creates an FY, and the store didn't track one. So the step became: FY bootstrap + a real app shell, which unblocks the Purchase screen.

Files changed this session:

- `desktop/src/lib/stores/auth.svelte.ts` — extended the app store: loads/tracks the active FY and a persisted current-company selection; added getters `fy`, `currentCompany`, `needsFy`; actions `ensureFy`, `setCurrentCompany`.
- `desktop/src/routes/fy/+page.svelte` — **new** FY-setup gate screen (prefills Indian FY Apr 1–Mar 31, editable).
- `desktop/src/routes/app/+page.svelte` — replaced the placeholder with a real shell (nav rail, company switcher in multi mode, FY badge, Home summary, section placeholders).
- `desktop/src/routes/+page.svelte` — boot cascade now includes the FY gate.
- `desktop/src/routes/setup/+page.svelte` — after creating the first company, routes to `/fy`.

**Boot routing cascade** (`routes/+page.svelte`, after backend ready + `authState`):
```ts
await auth.restore();
if (!auth.isAuthed) { await goto("/login"); return; }
if (auth.needsSetup) { await goto("/setup"); return; }
if (auth.needsFy)   { await goto("/fy");    return; }
await goto("/app");
```

**Store context loader** (the code central to the current bug):
```ts
async function loadContext() {
  setting = await request<Setting>("/api/accounts/settings/");
  companies = await request<Company[]>("/api/accounts/companies/");
  const years = await request<FinancialYear[]>("/api/fy/");
  fy = years.find((y) => y.is_active && !y.is_closed) ?? null;
  await resolveCurrentCompany();
}
```
`needsFy` getter: `user !== null && companies.length > 0 && fy === null`.

**Idempotent FY create** (added to fix an earlier double-submit; adopts an existing FY on conflict):
```ts
async ensureFy(startDate, endDate) {
  try {
    fy = await request<FinancialYear>("/api/fy/", {
      method: "POST",
      body: JSON.stringify({ start_date: startDate, end_date: endDate }),
    });
  } catch (e) {
    const years = await request<FinancialYear[]>("/api/fy/");
    fy = years.find((y) => y.is_active && !y.is_closed) ?? null;
    if (!fy) throw e;
  }
  return fy;
}
```

## 4. THE CURRENT BUG — and how to resolve it

**Symptom:** After restart, boot routes to `/fy` ("Set up your financial year"). That means `needsFy === true`, i.e. `loadContext()` fetched `GET /api/fy/` and `find(is_active && !is_closed)` returned nothing — so `fy` stayed `null`.

**The contradiction:** In an earlier attempt, the backend returned **"An active financial year already exists"** (HTTP 400 from `DomainError`). That message is only raised by `open_first_fy` when `active_fy(user)` returns a row — i.e. the **write path** saw an active, open FY. Yet the **read path** (`GET /api/fy/` list) is returning none. Company/account data persists across restarts (login works, companies exist), so the DB is not being reset.

**This must be resolved by inspecting actual state, in this order:**

1. **Webview devtools → Network.** Right-click in the Tauri window → Inspect. Reload. Find the boot `GET /api/fy/` request and read its JSON response body. Also check the Console for errors.
   - If the response **contains the FY** but `fy` is still null → frontend parsing bug. Log `years` in `loadContext` and check the field names/types (`is_active`/`is_closed` should be JSON booleans). Fix the `find` predicate accordingly.
   - If the response is **`[]`** → the read path returns nothing for this user → go to step 2.

2. **Ground-truth the table.** From the backend source run `python manage.py shell` (point it at the live portable Postgres — the port is printed at launch as `Finora backend ready on 127.0.0.1:<port>`, DB creds in `backend/.env`), then:
   ```python
   from apps.financialyear.models import FinancialYear
   from apps.accounts.models import User
   list(FinancialYear.objects.values("id","user_id","start_date","end_date","is_active","is_closed"))
   list(User.objects.values("id","username"))
   ```
   - If **no FY row exists** → the earlier 201 never persisted → backend/DB write issue (investigate `open_first_fy`, the Nuitka-frozen exe's DB connection/transaction commit, and whether anything runs `flush`/reinit on startup). Note: company writes DO persist, so compare the two code paths.
   - If an FY row exists but **`user_id` differs** from the restored user's id → auth/ownership mismatch (a second user was created at some point). Reconcile accounts.
   - If an FY row exists, is `is_active=true`, `is_closed=false`, and owned by the right user, yet `GET /api/fy/` returns `[]` → **read/write inconsistency** in the FY viewset/queryset; inspect `FinancialYearViewSet.get_queryset` and the request user resolution.

**Fastest unblock while investigating:** manually create/activate an FY (Django admin — `financialyear/admin.py` exists — or the shell). Once one active, open FY exists and is visible to `GET /api/fy/`, boot will skip `/fy` and land on the app shell, letting you proceed. Also confirm the `ensureFy` fix is actually compiled in (a stale Vite build is a cheap thing to rule out): with it applied, hitting "Start bookkeeping" once should adopt any existing FY and navigate rather than dead-ending.

**Backend contract (verified) — `POST /api/fy/`** body `{ "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD" }`; `open_first_fy` raises `DomainError` (→ 400) if an active FY already exists. `GET /api/fy/` returns a **bare array** (DRF pagination is commented out in `config/settings/base.py`). Serializer fields: `id, start_date, end_date, is_active, is_closed, is_writable`.

## 5. Exact next step (after the FY bug is resolved)

**Build the Purchase screen** — build-order step 4, the first voucher screen and first consumer of the existing SmartLookup + dialogs. Integration facts already confirmed from the backend:

- Endpoint: `POST /api/vouchers/purchases/` with body:
  ```json
  { "company": <id>, "party": <id>, "date": "YYYY-MM-DD",
    "number": null,
    "lines": [ { "mapping": <mappingId>, "qty": <n>, "rate": <n> } ] }
  ```
- **Critical:** purchase lines take a `mapping` id (`ItemCompanyMapping`), **not** an item id. The item `suggest` endpoint returns only `{ id, name, base_unit }`. So after the user picks an item via SmartLookup, resolve it to a per-company mapping via `GET /api/catalogue/mappings/?item=<itemId>&company=<currentCompanyId>` (returns `{ id, item, rate, stock, ... }`) to obtain the `mapping` id and default `rate`. If no mapping exists for the current company, open `ItemCreateDialog` (it creates the item + mapping for the current company).
- Use `auth.currentCompany.id` for `company` and rely on the server's active FY for `fy` (resolved server-side in `_context`). `number` can be null (server auto-numbers via `VoucherNumberSeq`, high-water template).
- Response (`PurchaseSerializer`): `{ id, company, party, number, date, total_amount, is_cancelled, lines: [{ id, item, item_name, mapping, qty, rate, amount }] }`. Show the server-computed `number` and `total_amount` after save.
- Party is picked via SmartLookup(type="PARTY") → `PartyCreateDialog` on no-match; posts to `POST /api/parties/`.
- Slot the screen into the `app/+page.svelte` "purchase" section (currently a placeholder), or a `routes/app/purchase` route — match whatever nav pattern is chosen. `PurchaseViewSet` also has `cancel` (soft-cancel + reversing entries) for later.

## 6. Known caveats / hardening (non-blocking)

- `SECRET_KEY` defaults to the 22-char `"dev-insecure-change-me"`, which is what triggers the `InsecureKeyLengthWarning` (JWTs are signed with it). Set a 32+ byte `SECRET_KEY` in `backend/.env` before shipping.
- `WARNING: Unauthorized: /api/accounts/auth/me/` on every boot is **expected/harmless** — `restore()` probes `/me/` with an empty access token, catches the 401, refreshes, and retries.
- `loadContext` assumes DRF returns bare arrays (true today, pagination is off). If pagination is ever enabled, `companies`/`years` become `{results: []}` and `.length`/`.find` break — guard for it then.
- Route guards assume boot always runs at `/` first (Tauri loads the dev root), so hard-refreshing directly on `/app` without going through boot isn't handled. Fine for normal flow.

---

That should let a fresh session pick up cold. Want me to keep going on the FY read/write investigation right now instead, or hold here?