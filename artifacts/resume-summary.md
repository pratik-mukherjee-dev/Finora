# Finora — Session Resume (Settings + license mode-switching committed; next: rebuild exe + seed modes, then Parties)

## 0. How to work on this project
- **Backend is the source of truth.** Read `backend/apps/*` (models, services, selectors,
  serializers, urls, views) before wiring any screen.
- Deliver **full file contents** (large files handed over as downloadable files; small
  files/functions inline). Not diffs. Do not commit — the user pushes.
- Do **not** change the Enter-key flow or existing visuals unless asked. New optional fields
  (mode picker, inline settlement) stay **out** of the Enter-flow (no `data-flow`) and out of
  `canSave` unless stated.
- Repo: `github.com/pratik-mukherjee-dev/Finora.git`, branch `master`. Always `git pull` first.

## 1. Project snapshot
- **Finora** — offline-first desktop accounting/billing app for small businesses.
- **Shell:** Tauri v2 (Rust) launches a portable **PostgreSQL 18** sidecar (random localhost
  port per launch, written to `runtime.json` in app-data dir) and a **Nuitka-frozen Django**
  sidecar. `run_server.py` runs `migrate` then serves via waitress (`config.wsgi`).
- **Frontend:** SvelteKit SPA (`adapter-static`, SSR off, **Svelte 5 runes**) in `desktop/src/`.
  Transport via Tauri HTTP plugin. API client `desktop/src/lib/api.ts` (`request<T>()`,
  `ApiError`, token handling). Store `desktop/src/lib/stores/auth.svelte.ts`. Screens register
  via `registerScreen(build)` → `{title, actions[], shortcuts[], panel[]}`. Enter-flow via
  `use:enterFlow` (`$lib/flow.ts`); dialogs `ConfirmDialog.svelte`, `WarningDialog.svelte`.
- **Dev DB vs sidecar DB:** `manage.py` → `config.settings.development` → `.env` →
  **system Postgres at 127.0.0.1:5432, db/user/pw = finora**. Packaged app → sidecar DB on the
  random `runtime.json` port. DIFFERENT databases. For manual commands against the live sidecar
  DB use `dbshell_runtime.py`. `base.py` uses `load_dotenv(override=False)` → OS env vars WIN
  over `.env` (debugging footgun).
- **Ship a backend change:** `makemigrations` → `migrate` (dev DB) → `build_backend.bat` →
  copy `backend/finora-backend.exe` into `desktop/src-tauri/resources/backend/` → launch.
  Migrations are FROZEN into the exe by Nuitka. Windowed build hides migrate output →
  `backend-migrate.log` next to `runtime.json`; `build_backend_debug.bat` shows errors.
- **Dev run:** `npm run tauri dev` from `desktop\`.

## 2. Screen / nav status (ActivityBar shortcuts)
- **Alt+1 Home** — dashboard: DONE (backend + frontend).
- **Alt+2 Sale** — DONE: lines (item), charges (ledger-based), inline per-invoice settlement,
  pre-save warnings.
- **Alt+3 Purchase** — DONE: lines (mapping), charges, inline settlement, warnings.
- **Alt+4 Settle** — DONE: party, amount, settlement mode, oldest→latest allocation, warnings.
- **Alt+9 Settings** — **DONE this session** (see §3). Route `/app/settings`, wired in
  `commands.ts` + shell active-tab detection.
- **Alt+5 Stock, Alt+6 Parties, Alt+7 Items, Alt+8 Reports** — **backend ready, NO frontend
  page yet** (blank nav slots). These are the remaining build targets.

## 3. What we did THIS session (all committed: `899e354`, `c4ee700`)

### 3a. Company mode + license — backend
- **`accounts.License`** gained **`max_companies`** (PositiveSmallIntegerField, default 1);
  migration **`0003_license_max_companies`**. `allows_multi` property = `mode==MULTI and is_active`.
- **`switch_to_single(user)`** service added (sets `active_mode=SINGLE`, clears
  `segregation_enabled`). Non-destructive — companies/data stay; toggling back and forth is safe.
- **`create_company`** now enforces two guards: SINGLE mode + existing company → `LicenseError`;
  and `user.companies.count() >= license.max_companies` → `LicenseError`.
- **`SettingViewSet.list`** now nests the license:
  `GET /api/accounts/settings/` → `{...UserCompanySetting fields, license: {plan, mode,
  is_active, valid_till, allows_multi, max_companies}}`. New action **`switch_single`**
  (`POST /api/accounts/settings/switch_single/`) alongside existing `switch_multi` and
  `segregation`. Route registered (`router.register("settings", SettingViewSet)`).
- `user_license(user)` selector added; `LicenseSerializer` now includes `max_companies`.

### 3b. Company mode + license — frontend
- **`auth.svelte.ts`**: added `License` type; `license` state parsed from the enriched
  `/settings/` response in `loadContext`; getters `license`, `allowsMulti`, `maxCompanies`;
  methods `switchToSingle()`, `setSegregation(enabled)`, `reloadContext()`; license cleared on
  logout.
- **`/app/settings/+page.svelte`** (new, ~604 lines) — four cards:
  1. **Company Mode** — single/multi toggle (multi disabled unless `allowsMulti`), segregation
     checkbox (multi only), company list with count vs `maxCompanies`, add-company input hidden
     when limit reached.
  2. **Settlement Modes** — list with active/inactive toggle + delete (system rows guarded),
     add input. Over `/api/accounts/settlement-modes/`.
  3. **Charge Ledgers** — list with kind tag + delete (system guarded), add with kind selector
     (Discount/Round Off/Tax/Other). Over `/api/ledgers/?company=`.
  4. **Voucher Numbering** — per-sequence editable `template` + live "Next: INV0001" preview
     (client-side `formatPreview` simulating Python `{seq:04d}`). Over
     `/api/vouchers/number-seqs/?company=`. Sequences appear only after the first voucher of
     each type is saved.

### 3c. Rules the user set for mode/license behavior (design intent to preserve)
- License decides: single-only OR multi. If multi is chosen, single is always also allowed.
- User can switch to multi anytime (if licensed), enable/disable segregation freely.
- In multi mode, **max companies always comes from the license** — cannot exceed
  `max_companies`. Above that → blocked.
- License **activation/upgrade API is intentionally NOT built yet** (separate story). Everything
  is built to read `License.mode`/`max_companies`; how the license gets set is deferred.

## 4. Earlier-this-thread work already committed (context)
- **Settlement modes** (`accounts.SettlementMode`, migration `0002`, seeded in
  `register_first_user`, viewset, `mode` FK on Received/Payment via vouchers `0003`).
- **Inline per-invoice settlement** — backend (`reconciliation.apply_*_to_bill`,
  `settlement_service` `target_bill_id`, `views._resolve_target_bill`) + frontend section on
  Sale/Purchase below Save (Amount + Mode, out of flow, independent 2nd POST to
  `/received/`|`/payments/` with `target_bill_id`; failure keeps invoice).
- **WarningDialog + `$lib/validation.ts`** (`Issue` type) — pre-save soft-warning dialog wired
  into Sale/Purchase/Settle via `collectIssues()` + `attemptSave(via)`. Checks: line qty=0,
  line rate=0, unresolved item (typed-but-not-selected, **block**), purchase no-mapping
  (**block**), discount charge value=0, settlement no-mode, settlement/settle overpay. "Review
  & fix" focuses `issues[0]`; blocks hide "Save anyway".
- **SmartLookup `exclude` prop** — item already chosen on another line is filtered from
  suggestions (mirrors charges' `optionsFor`).
- **`addCharge()`** now starts an EMPTY row (old first-ledger pre-fill commented out), so Enter
  on an empty charge row removes it and advances to Save (matches item-line behavior).

## 5. IMMEDIATE NEXT STEPS (in order)

1. **Rebuild the backend exe — REQUIRED before anything is testable.** The committed exe
   (`desktop/src-tauri/resources/backend/finora-backend.exe`, dated 07-20) **predates** the
   07-21 backend changes. Until rebuilt, the running app has NO: settlement-modes endpoint,
   `mode` FK, `target_bill_id` path, `max_companies`, license-in-settings, or `switch_single`.
   Symptoms until then: mode dropdowns empty ("No charges"), Settings license/mode calls 404,
   inline settlement 404. → run `build_backend.bat`, copy exe into `resources/backend/`, launch.
   (Also apply migrations `0003` on the dev DB before building.)

2. **Seed settlement modes for existing users — STILL PENDING (no data migration exists).**
   `migrations/` has only `0001, 0002, 0003` — **no `0004` seed migration**. Migration `0002`
   is schema-only; `seed_default_settlement_modes` runs only at registration, so pre-existing
   users have ZERO modes and every mode dropdown is empty. Fix = add data migration
   `accounts/0004_seed_settlement_modes.py` (`RunPython`, loop users, inline Cash[system]/UPI/
   Bank Transfer via `apps.get_model`, `get_or_create`, `reverse=noop`). Interim: manual seed
   via `dbshell_runtime.py`:
   ```python
   from django.contrib.auth import get_user_model
   from apps.accounts.services import seed_default_settlement_modes
   for u in get_user_model().objects.all():
       seed_default_settlement_modes(u)
   ```

3. **Smoke-test Settings end-to-end** once (1) and (2) are done: switch multi→single→multi,
   toggle segregation, hit the company cap, add/deactivate a settlement mode, add a charge
   ledger, edit a voucher template and confirm next-number preview matches actual output.

## 6. AFTER THAT — remaining v1 screens (suggested order)
1. **Parties (Alt+6)** — closes the accounting loop. Backend ready: `PartyViewSet` with
   `balance` + `ledger` detail actions; selectors `current_balance`, `ledger_entries`. Build a
   list + party detail (running balance, ledger of vouchers). Reuse SmartLookup/PartyCreateDialog.
2. **Items (Alt+7)** — `ItemViewSet`, `MappingViewSet`, suggest endpoint. List + create/edit;
   manage item↔company mappings (rate/unit).
3. **Stock (Alt+5)** — `StockLedgerViewSet`, `StockConversionViewSet`, `stock_report` selector.
   Stock ledger view + conversions.
4. **Reports (Alt+8)** — `sales_report`, `purchase_report`, `stock_report`, `daily_sheet` all
   served. Read-only aggregation screens; benefits from the above being populated.

## 7. Known caveats / non-blocking
- **Exe not rebuilt** since 07-20 — see §5.1. This gates ALL recent backend features.
- **No settlement-mode seed migration** — see §5.2.
- **License activation API deliberately absent** (§3c) — seed a license row as `MULTI` with the
  desired `max_companies` for dev testing; no UI to change `License.mode` yet.
- `_resolve_target_bill` uses `int(bill_id)` — fine for `BigAutoField` pks, revisit if UUIDs.
- `is_mode_locked` on `UserCompanySetting` is set at registration/switch but **never read** —
  dead field; decide to use (admin lock) or drop.
- Voucher template edit: `template` must contain `{seq...}` or `next_number` raises
  `DomainError`. Settings preview shows "Invalid template" but there's no hard save-guard yet —
  consider blocking save when `{seq` is absent.
- `high_water` is read-only in the serializer — Settings can't offer "start numbering at N" yet
  (future: expose with a lower-bound guard).
- Set a 32+ byte `SECRET_KEY` in `backend/.env` before shipping (PyJWT length warning).
- `Unauthorized: /api/accounts/auth/me/` on boot is expected (restore probes `/me/`, refreshes).
- Orphaned sidecars on hard-kill: `taskkill /F /IM finora-backend.exe /T` (+ `postgres.exe`).