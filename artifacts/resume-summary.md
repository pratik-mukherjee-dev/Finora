## FINORA — RESUME SUMMARY (portable)

**Project:** Offline-first desktop accounting app. Tauri v2 (Rust) manages two sidecars: Django/DRF backend (frozen exe) + portable PostgreSQL 18.4. Frontend SvelteKit SPA (`ssr=false`, adapter-static) + Svelte 5 runes + TS, talks to Django over a random localhost port via `@tauri-apps/plugin-http` (CORS-free). One user, multiple companies. Repo: `gitlab.com/finora-1/Finora` (**branch: `master`**). Strategy files `backend-strategy.md` / `frontend-strategy.md` in root.

**Status:** Backend logic complete (build steps 1-7), frozen. Packaging + sidecar wiring proven. Frontend transport proven. **Currently in frontend build step 2-3.**

**Auth decision:** JWT via `djangorestframework-simplejwt` (NOT authtoken, NOT sessions). Endpoints to add under `/api/accounts/`: `auth/login/` (TokenObtainPair), `auth/refresh/`, `auth/logout/` (blacklist), `auth/me/`. **Backend JWT views/urls/settings still need to be applied** (gap). License: keyed by user + device, cloud platform not built yet, build behind `LicenseInfo` interface + stub provider + device UUID captured at first launch; local cache shaped for future signed token.

**Confirmed backend API surface (branch master):**
- Accounts: `GET/POST /api/accounts/companies/` `{id,name,is_default,created_at}`; `GET /api/accounts/settings/`, `POST .../settings/switch_multi/ {segregation_enabled}` (license-gated, raises LicenseError→400), `POST .../settings/segregation/ {enabled}`. Setting fields: `active_mode`(single|multi, read-only), `default_company`, `segregation_enabled`, `is_mode_locked`.
- Search: `GET /api/search/suggest/?type=ITEM|PARTY&q=&limit=` → `[{id,name,...}]`; `POST /api/search/record/ {type,id}`.
- Parties: `POST /api/parties/ {name,phone?,address?,opening_balance?}` → `{id,name,phone,address,opening_balance,balance,created_at}`.
- Catalogue: `POST /api/catalogue/items/ {name,base_unit}` → `{id,name,base_unit,created_at,mappings[]}`; `POST /api/catalogue/mappings/ {item,company,category?,rate,opening_stock?,hsn_code?,gst_rate?,gst_mode?}` (`stock` read-only).
- Other mounts: `/api/fy/`, `/api/stock/`, `/api/vouchers/`, `/api/reports/`, `/health/`.
- Models: shared `Item`; per-company `ItemCompanyMapping`; unified `Party` w/ directional `balance`; `License.allows_multi = mode==multi and is_active`; mode truth lives in `UserCompanySetting.active_mode` (license only gates whether multi is allowed).

**Frontend files built (in repo, master):**
- `desktop/src/lib/api.ts` — JWT-aware: `_access/_refresh`, `setTokens/clearTokens`, `request` (Bearer + 401→refresh retry via internal `rawRequest`), `login/logout`, `waitForBackend`, `apiBase`, `health`, `suggest/recordUsage`, `ApiError(status,message,body)`, `tauriFetch`. **Note: `request` signature `(path, init={}, _retried=false)`.**
- `desktop/src/lib/stores/auth.svelte.ts` — runes store: user/setting/companies/mode/needsSetup/ready; `restore/login/logout/enableMulti/createCompany`; persists refresh token via plugin-store (`load(STORE,{autoSave:true,defaults:{}})`).
- Routes: `+page.svelte` (boot gate: waitForBackend→restore→route), `login/+page.svelte`, `setup/+page.svelte` (mode select + first company), `app/+page.svelte` (shell, routes to /setup if no company).
- Components: `SmartLookup.svelte` (debounced 150ms, abortable, keyboard nav, no-match→create, role=listbox/option), `PartyCreateDialog.svelte`, `ItemCreateDialog.svelte` (creates item + current-company mapping).
- Warnings.txt all resolved (unused auth import removed, `untrack(()=>initialName)`, `use:focusOnMount`, backdrop `role=presentation` + `e.target===e.currentTarget` close guard, listbox roles). errors.txt empty.

**Plugin prerequisites:** `@tauri-apps/plugin-store@^2.4.3` installed (package.json ✅). `@tauri-apps/plugin-http` ✅. Cargo `tauri-plugin-store="2"` + `lib.rs` `.plugin(...)` + capabilities store perms = **the current fix in progress.**

**Immediate next steps:**
1. Apply store capability fix above (unblocks boot/session restore).
2. Apply backend JWT layer (login/refresh/logout/me + simplejwt settings + migrate + rebuild exe) — still pending.
3. Add `currentCompany` to auth store (default = `is_default` company; switchable in multi).
4. **Build step 4: Purchase screen** (first consumer of SmartLookup/ItemLookup) — needs `backend/apps/vouchers/urls.py` + purchase serializer/service shapes read first.
5. Then: Payment/Received (auto-allocation) → Sale master + company picker + derived view → Stock/convert → Reports/daily sheet → FY/settings.

**Watch-fors:** Python 3.14+Nuitka experimental (downgrade 3.13 before ship); `backend/.env` committed (move before ship); window-close-during-boot orphan edge; release resource-path branch unvalidated; store perms must list explicit `allow-*` commands.

