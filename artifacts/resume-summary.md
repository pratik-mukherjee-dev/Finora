# Finora — Session Resume (Ledger-based charges backend added; next: wire charges into Sale/Purchase UI)

## 0. How to work on this project
- **Source of truth is always the backend code.** Read `backend/apps/*` (urls, views,
  serializers, services, selectors) before wiring any screen.
- **Follow the desktop UI design doc in `artifacts/`** (the finalized "Desktop UI
  Design Principles / Source of Truth" md) for all layout, navigation, shortcut,
  and token decisions. Use `artifacts/endpoints.md` (API reference & proposals) for
  the endpoint map — but if it disagrees with backend code, the backend wins.
- Deliver **full file contents inline** with the file path (not diffs). One layered
  step at a time. Precise, minimal-token responses. Verify against real repo code.

## 1. Project snapshot
- **Finora** — offline-first desktop accounting/billing app. GitLab project id
  `84506836`, branch `master`.
- **Shell:** Tauri v2 (Rust) managing portable PostgreSQL + a Nuitka-frozen Django
  backend sidecar. Random localhost port per launch; `runtime.json` carries DB
  params; production settings read `FINORA_RUNTIME_CONFIG`.
- **Backend:** Django + DRF, **ten** apps under `backend/apps/`
  (`common, accounts, financialyear, catalogue, parties, stock, vouchers, search,
  reports, ledgers`). JWT auth. services/ (write) + selectors/ (read) split, atomic txns.
- **Frontend:** SvelteKit SPA (`adapter-static`, SSR off, Svelte 5 runes) in
  `desktop/src/`. Transport = Tauri HTTP plugin. API client `desktop/src/lib/api.ts`;
  app store `desktop/src/lib/stores/auth.svelte.ts`.
- **Dev:** `npm run tauri dev` from `desktop\`. Editing backend logic requires
  rebuilding the exe (`backend/build_backend.bat`) and copying it into
  `desktop/src-tauri/resources/backend/finora-backend.exe`.

## 2. Full backend API surface (verified this project)
- **accounts:** `auth/{register,login,refresh,logout,me,state}/`, `companies/` (CRUD),
  `settings/` (+ `switch_multi/`, `segregation/`).
- **fy:** list/retrieve/create, `{id}/close/`.
- **catalogue:** `items/` (+ `{id}/add_mapping/`), `categories/`, `mappings/`
  (filter `?item=&company=`).
- **parties:** CRUD, `{id}/ledger/`, **`{id}/balance/` (proposed)**. `PartySerializer`
  already returns `balance`.
- **stock:** `ledger/` (+ `ledger/adjust/`), `conversions/` (+ `{id}/cancel/`).
- **vouchers:** `sales/` (+cancel), `sales-derived/` (`?master=`), `purchases/`
  (+cancel), `received/` & `payments/` (+ `{id}/allocations/`, +cancel),
  `number-seqs/`. **Proposed:** `{payments|received}/open_bills/?party=`.
  - **Charges (NEW):** Sale/Purchase create accept a `charges` array in the POST
    body: `[{ledger_id, charge_type, mode, input_value, amount?}]`. Server computes
    signed `amount` (discount negative, round-off delta) via
    `vouchers/services/charges.py::apply_charges` and persists `VoucherCharge` rows.
    Both `SaleMasterSerializer`, `SaleDerivedSerializer`, and `PurchaseSerializer`
    now return a read-only **`charges`** array (`id, ledger, ledger_name,
    charge_type, mode, input_value, amount, sort_order`).
  - `charge_type` ∈ `DISCOUNT | ROUND_OFF | CGST | SGST`; `mode` ∈ `PERCENT | AMOUNT`.
    v1 computes DISCOUNT + ROUND_OFF; CGST/SGST are accepted slots (amount passed in),
    item-wise tax is v2.
  - Master total = **sum of derived totals** (per-company round-off), so
    master == Σ derived; segregation prorates discount/tax by line-value weight and
    computes per-company round-off (`prorate_master_charges`).
  - Cancel reverts charges: `cancel_charges` soft-cancels rows for SALE, SALE_DERIVED,
    and PURCHASE alongside the voucher cancel.
- **ledgers (NEW app):** `Ledger` model (`user`, optional `company`, `name`, `kind`
  ∈ DISCOUNT/ROUND_OFF/TAX/OTHER, `is_system`, `gst_rate`). ViewSet supports
  GET/POST/PATCH/DELETE, filters `?company=&kind=`; system ledgers can't be deleted.
  `seed_default_ledgers(user)` seeds Discount, Round Off, CGST, SGST (company=null,
  is_system).
- **search:** `suggest/?type=&q=`, `record/`.
- **reports:** `sales/`, `purchases/`, `stock/`, `daily-sheet/`,
  **`dashboard/` (proposed)**.
- **Sale line contract quirk:** Sale lines send `item` id + optional `company`
  (server resolves mapping). **Purchase lines send `mapping` id.** Do not confuse.

## 3. Backend contracts DRAFTED / PENDING (not yet in repo or not yet migrated)
Still need commit + migrate + exe rebuild before the desktop can rely on them:
- **Ledger charges wiring (present in code, NOT migrated):** `ledgers` app has
  NO migration yet (`0001_initial` missing) and `VoucherCharge` has NO migration
  (vouchers `0001_initial` predates it). **`makemigrations` + `migrate` + exe rebuild
  required** before any charges/ledger API works. `apps.ledgers` IS in INSTALLED_APPS
  but its URLs are **NOT yet wired** into `config/urls.py` (add
  `path("api/ledgers/", include("apps.ledgers.urls"))`). `seed_default_ledgers` is
  **not yet called** from `register_first_user` (defaults never auto-seed).
- `vouchers/selectors/bills.py` — shared `_open_bills`, excludes cancelled bills,
  adds `open_bills_preview(party, kind)`; `vouchers/selectors/__init__.py` export;
  `vouchers/views.py` `open_bills` action (Received + Payment).
- `parties/views.py` — `balance` action.
- `reports/selectors.py` + `views.py` + `urls.py` — `dashboard/`.
> ⚠️ Charges API will 500/404 until migrations run + `api/ledgers/` is wired.
> Settle's Allocation preview 404s until `open_bills/` is built.

## 4. What is built & verified (pre-existing)
- Tauri shell + sidecar wiring + `api.ts` (JWT, port discovery, `waitForBackend`).
- Auth flow (register/login/logout), company setup, **FY gate** working end-to-end.
- SmartLookup + PartyCreateDialog + ItemCreateDialog components.
- Voucher screens Purchase, Sale, Settle — functionally complete against the
  backend (pre-charges versions; charges block not yet added to UI).
- Desktop-native shell refactor complete (ActivityBar, ContextBar, ContextPanel,
  CommandPalette, theme tokens, per-screen registration via shellContext).

## 5. Charges front-end plan (THIS is the immediate next work)
Ledger charges are **voucher-level totals**, not a new module. They live inside the
existing **Sale (`Alt+2`)** and **Purchase (`Alt+3`)** screens as a **Totals /
Charges block** below the line grid, and a small **Ledgers manager** under Settings.

**Sale + Purchase screen additions (same pattern for both):**
- Below the line grid, a right-aligned **Totals panel**: Subtotal (computed from
  lines) → Discount → CGST/SGST (v2, hidden/disabled in v1) → Round Off → **Grand
  Total**. Uses tokens (`--bg-elevated`, `--row-h`, right-aligned numerics).
- Each charge row: a **ledger SmartLookup** (filtered `?kind=` via `api/ledgers/`),
  a `mode` toggle (`PERCENT`/`AMOUNT`), an `input_value` field. Round-off is a
  single toggle (auto delta, no input).
- On save, POST body gains `charges: [{ledger_id, charge_type, mode, input_value}]`.
  Do NOT compute final amounts client-side for persistence — the server returns the
  authoritative `charges[]` (with signed `amount`) and `total_amount`; render those
  back. A client-side *preview* total is fine while typing.
- New keyboard bindings on voucher screens (register in the screen, per §4.2 pattern):
  `Alt+I` add charge line, `Alt+O` toggle round-off, `Alt+G` focus discount.
  Reuse existing `Ctrl+Enter` save.
- History/Derived panel rows should now show the charges breakup (read from the
  serializer `charges[]`).

**Settings — Ledgers manager (small, under `Alt+9`):**
- List ledgers (`api/ledgers/`), create/edit custom ledgers (name, kind, gst_rate),
  delete non-system only (system delete is blocked server-side → show disabled).

**Design compliance:** no new activity-bar module; no page chrome/back button;
tokens only; charges block is dense (compact rows); ledger picker reuses SmartLookup
per §4.3; all actions have a shortcut shown on the mouse target (§0 One Rule).

## 6. Exact next steps (in order)
1. **Migrate + wire the charges backend (§3):** `makemigrations ledgers vouchers`,
   `migrate`, add `api/ledgers/` to `config/urls.py`, call `seed_default_ledgers`
   in `register_first_user`, rebuild exe. Charges API is dead until this is done.
2. **Apply the other pending backend contracts (§3)** — `open_bills/`,
   `parties/{id}/balance/`, `reports/dashboard/` — and rebuild.
3. **Add the charges block to Sale + Purchase screens** (§5): Totals panel, ledger
   SmartLookup, mode/input rows, round-off toggle, POST `charges[]`, render server
   `charges[]` + `total_amount`. Add `Alt+I / Alt+O / Alt+G` bindings.
4. **Add Ledgers manager to Settings** (§5): list/create/edit/delete via `api/ledgers/`.
5. **Then resume the remaining v1 screens** per design doc order: Home dashboard,
   Stock (`Alt+5`), Parties (`Alt+6`), Items (`Alt+7`), Reports (`Alt+8`),
   Settings core (`Alt+9`).
6. **Optional polish:** `ShortcutCheatSheet.svelte` (`F1`), `Ctrl+P` quick-open,
   shared `DataGrid`.

## 7. Known caveats / non-blocking
- **Charges/ledger migrations not generated** — regenerate locally; if hand-writing,
  add `SALE_DERIVED` to `VoucherCharge.VOUCHER_TYPE_CHOICES` first (segregation +
  SaleDerivedSerializer already use that value).
- `cancel_charges` uses `objects` (NonCancelledManager) → operates on live rows only;
  correct because cancel is guarded and idempotent. Verified — keep as-is.
- `SaleDerivedSerializer.get_charges` omits explicit `is_cancelled=False` but the
  manager already excludes cancelled rows; cosmetic only.
- Refactored screens still self-guard auth on `onMount`; harmless double-guard.
- `open_bills/` live preview 404s until §3 backend is built.
- Set a 32+ byte `SECRET_KEY` in `backend/.env` before shipping (JWT warning).
- Orphaned sidecars on hard-kill: `taskkill /F /IM finora-backend.exe /T` (+ `postgres.exe`).
- `ROTATE_REFRESH_TOKENS` recommended `False` (single-user, no blacklist app).
