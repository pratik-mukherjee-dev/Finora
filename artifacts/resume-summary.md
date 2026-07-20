# Finora — Session Resume (Enter-flow hardened + Charges UX complete; next: Settlement Modes DB feature)

## 0. How to work on this project
- **Backend is the source of truth.** Read `backend/apps/*` (models, services, selectors,
  serializers, urls, views) before wiring any screen.
- Follow the desktop UI design doc in `artifacts/`. `artifacts/endpoints.md` is the endpoint
  map; if it disagrees with backend code, backend wins.
- Deliver **file contents inline** with exact file paths (not diffs), one layered step at a
  time. For function edits, give the whole function and say where it goes. Do not commit.

## 1. Project snapshot
- **Finora** — offline-first desktop accounting/billing app. GitLab project id `84591925`,
  branch `master`.
- **Shell:** Tauri v2 (Rust) managing portable PostgreSQL + Nuitka-frozen Django sidecar.
  Random localhost port per launch; `runtime.json` carries DB params; prod settings read
  `FINORA_RUNTIME_CONFIG`.
  - **Backend ship process (verified):** migrations are FROZEN into the exe by Nuitka.
    To ship a backend change: `makemigrations` → `migrate` (verify on dev DB) →
    `build_backend.bat` → copy `backend/finora-backend.exe` into
    `desktop/src-tauri/resources/backend/finora-backend.exe` → launch.
    Windowed build swallows migrate output; use `build_backend_debug.bat` to see errors.
- **Backend layout:** Django + DRF under `backend/`. Django project is `backend/config/`
  (settings in `backend/config/settings/`). Apps under `backend/apps/`:
  `common, accounts, financialyear, catalogue, parties, stock, vouchers, search, reports,
  ledgers`. JWT auth. services/ (write) + selectors/ (read) split, atomic txns.
- **common app bases** (`backend/apps/common/models.py`): `TimeStampedModel`
  (created_at/updated_at), `AuditModel(TimeStampedModel)` (+created_by, nullable),
  `SoftCancelModel` (is_cancelled + `NonCancelledManager` as default `objects`,
  `all_objects` = plain manager, `soft_cancel()`).
- **Frontend:** SvelteKit SPA (`adapter-static`, SSR off, **Svelte 5 runes**) in
  `desktop/src/`. Transport = Tauri HTTP plugin. API client `desktop/src/lib/api.ts`
  (`request<T>()`, `suggest()`, `recordUsage()`, `Suggestion`). Store
  `desktop/src/lib/stores/auth.svelte.ts` (`auth.isAuthed/needsSetup/needsFy/
  currentCompany/mode`). Shell: ActivityBar/ContextBar/ContextPanel/CommandPalette;
  screens register via `registerScreen(build)` → `{title, actions[], shortcuts[], panel[]}`
  in `$lib/shell/useScreen.svelte`.
- **Dev:** `npm run tauri dev` from `desktop\`.

## 2. Backend API surface (verified)
- **accounts:** `auth/{register,login,refresh,logout,me,state}/`, `companies/` (CRUD via
  `CompanyViewSet`), `settings/` (`SettingViewSet` + `switch_multi/`, `segregation/`).
  Router in `accounts/urls.py` registers `companies/` + `settings/`.
  Models: `User`, `Company`, `License(mode single|multi, allows_multi)`,
  `UserCompanySetting(active_mode, default_company, segregation_enabled, is_mode_locked)`.
  `register_first_user` seeds License + UserCompanySetting + `seed_default_ledgers`.
- **fy:** list/retrieve/create, `{id}/close/`.
- **catalogue:** `items/` (+ `{id}/add_mapping/`), `categories/`, `mappings/`
  (`?item=&company=` → `{id,item,item_name,company,rate,stock}`).
- **parties:** CRUD, `{id}/ledger/`; `{id}/balance/` still proposed.
- **stock:** `ledger/` (+ `ledger/adjust/`), `conversions/` (+ `{id}/cancel/`).
- **vouchers:** `sales/` (+cancel), `sales-derived/` (`?master=`), `purchases/` (+cancel),
  `received/` & `payments/` (+ `{id}/allocations/`, `open_bills/?party=`, +cancel),
  `number-seqs/`.
  - **Charges (LIVE):** Sale/Purchase POST accept `charges:[{ledger_id, charge_type, mode,
    input_value}]`. Server computes signed `amount` in
    `vouchers/services/charges.py::apply_charges` (DISCOUNT negative; ROUND_OFF delta via
    `tally_default_round`; CGST/SGST accept a precomputed `amount`, v2). Serializers return
    read-only `charges[]`. Master `total_amount` = Σ derived; `prorate_master_charges`
    splits discount/round-off per company. `cancel_charges` soft-cancels on voucher cancel.
  - **Settlement (Received/Payment):** `VoucherBase` (company, financial_year, number, date,
    total_amount) + `party` + `amount`. `Allocation(settlement_type, settlement_id,
    bill_type, bill_id, amount, is_reversal)`. Services `create_received/create_payment`
    call `next_number`, `post_entry`, then `apply_receipt/apply_payment` (oldest→latest
    auto-allocation). **No settlement-mode field yet — that is the next feature (§5).**
- **ledgers:** `api/ledgers/` (`LedgerViewSet`, basename `ledger`, router at `""`), filters
  `?company=&kind=`; system ledgers can't be deleted. `Ledger(AuditModel){user, company?,
  name, kind(DISCOUNT/ROUND_OFF/TAX/OTHER), is_system, gst_rate}`. `seed_default_ledgers`
  seeds Discount, Round Off, CGST, SGST (company=null, is_system).
- **search:** `suggest/?type=&q=`, `record/`. **reports:** `sales/`, `purchases/`, `stock/`,
  `daily-sheet/`; `dashboard/` proposed.
- **Line contract quirk:** Sale lines send `item` (+optional `company`); **Purchase lines
  send `mapping` id.** Do not confuse.

## 3. What we changed THIS session (all frontend, NOT yet committed)
All edits were delivered inline; user is applying them. Verify against repo next session.

### 3a. App-wide Enter-flow, hardened (`desktop/src/lib/flow.ts`)
- `enterFlow` action: plain Enter advances `data-flow` nodes in DOM order; terminal node
  (`data-flow="save"`) or end-of-flow calls `onConfirm()` (opens ConfirmDialog).
  Ctrl/Cmd+Enter anywhere: `onSave({direct:true})` if `isComplete()`, else `onConfirm()`.
- Added `e.stopPropagation()` on the Ctrl+Enter branch.
- Added a **window-level `handleGlobalSave`** so Ctrl+Enter works even when focus left the
  form root (e.g. after Esc closes the dialog); guarded by `root.contains(e.target)` to avoid
  double-handling. Registered/destroyed alongside the root listener.

### 3b. ConfirmDialog (`desktop/src/lib/components/ConfirmDialog.svelte`)
- Added an `armed` guard (`onMount` → `setTimeout(…,0)`) so the SAME Enter that opened the
  dialog does not instantly confirm it. `onKey`: Esc cancels; Enter/Ctrl+Enter confirm only
  when `armed` and not `busy`; both `preventDefault` + `stopPropagation`.

### 3c. Sale + Purchase pages (`routes/app/sale/+page.svelte`, `.../purchase/+page.svelte`)
Same edits mirrored in both:
- `flowOpts`: `onSave` honors `{direct}` and re-guards `canSave`; `onConfirm` ALWAYS opens
  the dialog (removed the `if (canSave)` gate).
- Added `type="button"` to the Save button (kills native Enter-click double-fire).
- `closeConfirm()` restores focus into the form after Esc (sale/purchase → `focusParty()`).
- **Charges UX:**
  - `chargeLedgers` now = ALL ledgers (was filtered to DISCOUNT/ROUND_OFF). Safe because
    `buildPayloadCharges()` only emits DISCOUNT (input_value>0) and ROUND_OFF; TAX/OTHER are
    ignored on payload and inert in the totals preview. (Verified against `apply_charges`.)
  - A default empty charge row is seeded on mount / after save / on `resetForm`
    (`charges = [newCharge()]`) so the Enter-flow always has a `data-flow="charge"` step.
  - `onLineEnter(e,line)`: Enter on the LAST line's `amount` adds a new line (keeps Alt+A).
  - `onChargeEnter(e,charge)`: Enter on the last charge's value chains a new charge; uses
    `e.stopImmediatePropagation()` so it never reaches the flow root (was opening the confirm
    dialog by accident — fixed). Skips chaining and calls `focusSave()` when `allChargesUsed`.
  - `onChargePicked(charge)`: after picking, DISCOUNT → focus its value input; no-value kinds
    (ROUND_OFF/CGST/SGST) → chain a new charge if ledgers remain, else `focusSave()`.
  - `onChargeEmptyEnter(charge)` + `onLineEmptyEnter(line)`: Enter on an empty last row
    collapses that row and advances (charge → Save; line → charges).
  - `allChargesUsed` ($derived) + `focusSave()` helpers added.
  - `optionsFor(row)`: per-row dropdown list that hides ledgers already chosen in OTHER rows.

### 3d. New component `desktop/src/lib/components/LedgerLookup.svelte`
- Searchable, keyboard-driven charge picker modeled on SmartLookup but **no create option**,
  fed from the already-fetched `chargeLedgers` (Option `{id,name}`). Arrow keys + Enter to
  pick; participates in flow via `data-flow="charge"`, sets `data-flow-skip` while menu open.
  Props: `options, value, placeholder, flow, onselect, onenter, onemptyenter`. Both Enter
  branches use `e.stopImmediatePropagation()`.

### 3e. SmartLookup (`desktop/src/lib/components/SmartLookup.svelte`)
- Added `onemptyenter` prop: fires when Enter pressed with no value and menu closed (used by
  line item field to collapse an empty last line and advance).

> NET RESULT: normal Enter walks the whole form and opens the confirm dialog at the end;
> Ctrl+Enter saves directly; charges behave like party/item pickers, grow on Enter, hide
> already-used options, and cleanly fall through to Save when done. Settle page shares
> `flow.ts`/`ConfirmDialog` fixes but has no lines/charges.

## 4. Backend feature designed but NOT yet written: Settlement Modes (Option A = accounts app)
User approved putting it in **accounts** (user-level master data, same tier as
License/UserCompanySetting; seeding lives in `accounts.register_first_user`; keeps the
`vouchers → accounts` dependency direction; mirrors the `Ledger` precedent). It is DB-driven:
seeded defaults at registration, addable later from Settings; chosen on Received/Payment.

Exact plan agreed (inherit `AuditModel`, NOT SoftCancel — use `is_active`, not cancel):

1. `accounts/models.py`: `SettlementMode(AuditModel){user FK, name(60), is_system,
   is_active, sort_order}`, `Meta.ordering=["sort_order","name"]`, unique `(user,name)`
   constraint `uniq_settlement_mode_per_user`. (created_at/updated_at/created_by inherited.)
2. `accounts/services.py`: `DEFAULT_SETTLEMENT_MODES=(("Cash",True),("UPI",False),
   ("Bank Transfer",False))`; `seed_default_settlement_modes(user)` (idempotent
   get_or_create with `created_by=user`); `create_settlement_mode(user,name,sort_order=0)`;
   `delete_settlement_mode(user,mode_id)` (blocks `is_system`). Call
   `seed_default_settlement_modes(user)` in `register_first_user` right after
   `seed_default_ledgers(user)`.
3. `accounts/serializers.py`: `SettlementModeSerializer` fields
   `["id","name","is_system","is_active","sort_order"]`, `is_system` read-only.
4. `accounts/views.py`: `SettlementModeViewSet(ModelViewSet)` (get/post/patch/delete),
   `get_queryset` = user-scoped, `perform_create(user=…, is_system=False, created_by=…)`,
   `destroy` delegates to `delete_settlement_mode`.
5. `accounts/urls.py`: `router.register("settlement-modes", SettlementModeViewSet,
   basename="settlement-mode")`. Endpoint = `<accounts-prefix>/settlement-modes/`.
6. `vouchers/models/settlement.py`: add nullable FK to BOTH Received & Payment:
   `mode = FK("accounts.SettlementMode", on_delete=PROTECT, null=True, blank=True,
   related_name="%(class)s_set")`.
7. `vouchers/services/settlement_service.py`: `create_received/create_payment` accept
   `mode=None` and pass `mode=mode` into `.objects.create(...)`.
8. `vouchers/views.py`: add `_resolve_mode(request)` (validates id against `request.user`),
   pass `mode=_resolve_mode(request)` in ReceivedViewSet.create & PaymentViewSet.create.
9. `vouchers/serializers.py`: add `mode` + `mode_name` (source="mode.name", default=None) to
   ReceivedSerializer & PaymentSerializer field lists.
10. Migrations: accounts (create SettlementMode + RunPython data-migration backfilling
    defaults for all existing Users) and vouchers (add nullable `mode` FK). Then rebuild exe.

STILL TO CONFIRM before writing files:
- Exact accounts mount prefix — read `backend/config/urls.py` (root URLConf under
  `backend/config/`, NOT repo root; earlier `config/urls.py` fetch 404'd).
- Confirm default seed list (currently Cash[system]/UPI/Bank Transfer).
- FY-setup/registration read wiring so the setup flow can preselect a default mode.

## 5. Exact next steps (in order)
1. Read `backend/config/urls.py` to lock the accounts prefix; then deliver merged backend
   files for Settlement Modes (§4 items 1–10) as full inline files.
2. Migrations + rebuild backend exe + copy into `desktop/src-tauri/resources/backend/`.
3. Frontend: Settle page — add a settlement-mode picker (reuse LedgerLookup-style dropdown
   fed from `settlement-modes/`), default to the system/first mode, send `mode` in POST,
   show `mode_name` in history. Add a **Settlement Modes manager** in Settings; optionally a
   mode step in registration + FY-setup flows.
4. Ledgers manager in Settings (`Alt+9`) — still pending from before.
5. Remaining v1 screens per design doc: Home dashboard, Stock (Alt+5), Parties (Alt+6),
   Items (Alt+7), Reports (Alt+8), Settings core.
6. Backend pending: `parties/{id}/balance/`, `reports/dashboard/` (open_bills/ already ships).

## 6. Known caveats / non-blocking
- `cancel_charges` uses default `objects` (NonCancelled) → live rows only; correct (cancel is
  guarded + idempotent).
- Refactored screens self-guard auth on `onMount`; harmless double-guard.
- Set a 32+ byte `SECRET_KEY` in `backend/.env` before shipping (JWT warning).
- Orphaned sidecars on hard-kill: `taskkill /F /IM finora-backend.exe /T` (+ `postgres.exe`).
- `ROTATE_REFRESH_TOKENS` recommended `False` (single-user, no blacklist app).
- Charge rows with a picked DISCOUNT ledger but value 0 are harmlessly dropped by
  `buildPayloadCharges()` (value<=0 skipped). Consider auto-removing them pre-save for polish.
