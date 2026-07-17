# Finora — Session Resume (Charges backend migrated + exe placed; next: charges UI in Sale/Purchase)

## 0. How to work on this project
- **Source of truth is always the backend code.** Read `backend/apps/*` (urls, views,
  serializers, services, selectors) before wiring any screen.
- **Follow the desktop UI design doc in `artifacts/`** ("Desktop UI Design Principles /
  Source of Truth") for all layout, navigation, shortcut, token decisions. Use
  `artifacts/endpoints.md` for the endpoint map — if it disagrees with backend code,
  the backend wins.
- Deliver **full file contents inline** with the file path (not diffs). One layered
  step at a time. Precise, minimal-token responses. Verify against real repo code.

## 1. Project snapshot
- **Finora** — offline-first desktop accounting/billing app. GitLab project id
  `84506836`, branch `master`.
- **Shell:** Tauri v2 (Rust) managing portable PostgreSQL + a Nuitka-frozen Django
  backend sidecar. Random localhost port per launch; `runtime.json` carries DB
  params; production settings read `FINORA_RUNTIME_CONFIG`.
  - **Backend change process (verified):** `run_server.py` runs `migrate` on every
    startup, but Nuitka **freezes** migration files into the exe. To ship a backend
    change: `makemigrations` → `migrate` (verify on dev DB) → `build_backend.bat`
    → copy `backend/finora-backend.exe` into
    `desktop/src-tauri/resources/backend/finora-backend.exe` → launch.
    migrate output is swallowed in the windowed build; use `build_backend_debug.bat`
    to see startup/migration errors.
- **Backend:** Django + DRF, **ten** apps under `backend/apps/`
  (`common, accounts, financialyear, catalogue, parties, stock, vouchers, search,
  reports, ledgers`). JWT auth. services/ (write) + selectors/ (read) split, atomic txns.
- **Frontend:** SvelteKit SPA (`adapter-static`, SSR off, **Svelte 5 runes**) in
  `desktop/src/`. Transport = Tauri HTTP plugin. API client `desktop/src/lib/api.ts`
  (`request<T>()`, `Suggestion` type); app store `desktop/src/lib/stores/auth.svelte.ts`
  (`auth.isAuthed/needsSetup/needsFy/currentCompany/mode`).
- **Dev:** `npm run tauri dev` from `desktop\`.

## 2. Full backend API surface (verified this project)
- **accounts:** `auth/{register,login,refresh,logout,me,state}/`, `companies/` (CRUD),
  `settings/` (+ `switch_multi/`, `segregation/`).
- **fy:** list/retrieve/create, `{id}/close/`.
- **catalogue:** `items/` (+ `{id}/add_mapping/`), `categories/`, `mappings/`
  (filter `?item=&company=`; returns `{id,item,item_name,company,rate,stock}`).
- **parties:** CRUD, `{id}/ledger/`, **`{id}/balance/` (proposed)**.
- **stock:** `ledger/` (+ `ledger/adjust/`), `conversions/` (+ `{id}/cancel/`).
- **vouchers:** `sales/` (+cancel), `sales-derived/` (`?master=`), `purchases/`
  (+cancel), `received/` & `payments/` (+ `{id}/allocations/`, +cancel),
  `number-seqs/`. **Proposed:** `{payments|received}/open_bills/?party=`.
  - **Charges (LIVE now — migrated + exe placed):** Sale/Purchase POST accept a
    `charges` array: `[{ledger_id, charge_type, mode, input_value, amount?}]`.
    Server computes signed `amount` (DISCOUNT negative, ROUND_OFF delta) in
    `vouchers/services/charges.py::apply_charges` and persists `VoucherCharge`.
    `SaleMasterSerializer`, `SaleDerivedSerializer`, `PurchaseSerializer` return a
    read-only **`charges[]`**: `{id, ledger, ledger_name, charge_type, mode,
    input_value, amount, sort_order}`.
  - `charge_type` ∈ DISCOUNT|ROUND_OFF|CGST|SGST; `mode` ∈ PERCENT|AMOUNT.
    v1 computes DISCOUNT + ROUND_OFF; CGST/SGST are accepted slots (v2, hide in UI).
  - Master `total_amount` = **Σ derived totals** (per-company round-off); segregation
    prorates discount/tax by line-value weight (`prorate_master_charges`).
  - Cancel reverts charges (`cancel_charges` for SALE, SALE_DERIVED, PURCHASE).
- **ledgers:** `api/ledgers/` ViewSet — GET/POST/PATCH/DELETE, filters `?company=&kind=`;
  system ledgers can't be deleted. `Ledger{user, company?, name, kind
  (DISCOUNT/ROUND_OFF/TAX/OTHER), is_system, gst_rate}`. `seed_default_ledgers` seeds
  Discount, Round Off, CGST, SGST (company=null, is_system).
- **search:** `suggest/?type=&q=`, `record/`.
- **reports:** `sales/`, `purchases/`, `stock/`, `daily-sheet/`, **`dashboard/` (proposed)**.
- **Sale line contract quirk:** Sale lines send `item` id + optional `company`
  (server resolves mapping). **Purchase lines send `mapping` id.** Do not confuse.

## 3. Backend contracts still PENDING (not in repo yet)
- `vouchers/selectors/bills.py` (`open_bills_preview`, excludes cancelled) + export
  + `open_bills` action on Received/Payment.
- `parties/views.py` `balance` action.
- `reports/` `dashboard/`.
> Charges + ledgers are DONE (migrated, exe placed, `api/ledgers/` wired). Only the
> above remain; Settle's Allocation preview 404s until `open_bills/` ships.

## 4. What is built & verified
- Tauri shell + sidecar + `api.ts` (JWT, port discovery, `waitForBackend`).
- Auth / company setup / FY gate end-to-end.
- SmartLookup + PartyCreateDialog + ItemCreateDialog.
- Desktop-native shell refactor complete (ActivityBar, ContextBar, ContextPanel,
  CommandPalette, theme tokens; screens register via `registerScreen(build)` →
  `{title, actions[], shortcuts[], panel[]}` in `$lib/shell/useScreen.svelte`).
- Sale/Purchase/Settle screens working (Sale has History + Derived panel tabs).
  **Charges block NOT yet in the UI — that is the immediate next task.**

## 5. Charges UI — EXACT layout to build (Sale first, mirror to Purchase)
Ledger charges are **voucher-level totals**, not a new module. Insert into the
**existing** Sale screen `desktop/src/routes/app/sale/+page.svelte` (then the same
into `purchase/+page.svelte`). Current structure inside `<div class="wrap">`:
`banners → <section class="head"> → <section class="grid"> (item rows, ends with
"+ Add line Alt A") → <footer class="foot"> (Total + Save)`.

**Insert TWO new sections between `</section>` (grid) and `<footer class="foot">`,
and shrink the footer to just Save:**

1. **Charges section** (new `<section class="charges">`), directly **below the
   grid's "Add line (Alt+A)"**:
   - Repeatable charge rows, each: a **ledger SmartLookup** (new lookup filtered via
     `api/ledgers/?kind=DISCOUNT` etc., or a plain select of fetched ledgers), a
     `mode` toggle (`PERCENT`/`AMOUNT`), an `input_value` numeric.
   - **Discount** row (PERCENT default) and a **Round Off** toggle (single switch —
     no input; server computes the delta). CGST/SGST rows hidden in v1.
   - "+ Add charge" affordance mirroring the `.addline` style, with `<kbd>Alt I</kbd>`.

2. **Totals-breakdown section** (new `<section class="totals">`), **below charges**,
   right-aligned dense rows using tokens, replacing the single "Total" line:
   - `Line-item total` = current `total` (sum of line amounts). Positive.
   - `Discount` = discount amount **shown negative** (e.g. `− 120.00`, color
     `--danger` or muted).
   - `Round off` = signed delta (`+ 0.40` / `− 0.30`), color `--warn`.
   - (`CGST/SGST` rows appear only in v2.)
   - **`Final bill` = grand total** — bold, prominent, same value the old `Total`
     showed; after save use server `saved.total_amount` as authoritative.

3. **Footer** now holds only the **Save button** (`<kbd>Ctrl ⏎</kbd>`); the numeric
   total moved into the Totals section above it.

**Data / behavior rules:**
- Add a `charges` state array in the `<script>` alongside `lines`. Build a
  `payloadCharges = [{ledger_id, charge_type, mode, input_value}]` (omit round-off
  input_value) and include it in the `save()` POST body next to `lines`.
- **Do NOT persist client-computed amounts.** A client *preview* of discount/round/
  final is fine while typing, but on success render `saved.charges[]` + `saved.total_amount`
  from the response as the source of truth (server signs and rounds).
- Fetch ledgers once (on mount) via `request('/api/ledgers/?kind=…')`; cache for the
  lookup. Reuse the existing `round2` helper for preview math only.
- On `openForEdit`, hydrate the charges array from `row.charges[]` so editing
  (cancel + replace) round-trips.

**New shortcuts to register in the screen's `registerScreen(...)` (actions +
shortcuts arrays, same pattern as `sal-add`):**
- `Alt+I` → add charge row (`addCharge`).
- `Alt+O` → toggle round-off (`toggleRoundOff`).
- `Alt+G` → focus discount input (`focusDiscount`).
Keep existing `Ctrl+N` new, `Alt+A` add line, `Ctrl+Enter` save.

**Design compliance:** no new activity-bar module; no page chrome/back button;
tokens only (`--bg-elevated`, `--row-h`, `--danger`, `--warn`, `--ok`); dense rows;
ledger picker reuses SmartLookup per design §4.3; every action's shortcut shown on
its mouse target (One Rule). Purchase mirrors this exactly minus segregate/derived.

**Settings later:** a small **Ledgers manager** under `Alt+9` (list/create/edit,
delete non-system only via `api/ledgers/`).

## 6. Exact next steps (in order)
1. **Sale charges UI (§5):** add charges state, ledger fetch, the two new sections
   (Charges + Totals breakdown), slim footer to Save-only, `Alt+I/O/G` bindings,
   POST `charges[]`, render server `charges[]`/`total_amount`. Deliver full
   `sale/+page.svelte` inline.
2. **Purchase charges UI:** mirror §5 into `purchase/+page.svelte` (no segregate,
   no derived; purchase lines still send `mapping` id).
3. **Ledgers manager** in Settings (`Alt+9`).
4. **Then resume remaining v1 screens** per design doc order: Home dashboard, Stock
   (`Alt+5`), Parties (`Alt+6`), Items (`Alt+7`), Reports (`Alt+8`), Settings core.
5. Backend pending (§3): `open_bills/`, `parties/{id}/balance/`, `reports/dashboard/`.

## 7. Known caveats / non-blocking
- `cancel_charges` uses `objects` (NonCancelledManager) → live rows only; correct
  because cancel is guarded + idempotent. Verified — keep as-is.
- `SaleDerivedSerializer.get_charges` omits explicit `is_cancelled=False` but the
  manager already excludes cancelled rows; cosmetic only.
- Refactored screens still self-guard auth on `onMount`; harmless double-guard.
- `open_bills/` live preview 404s until §3 backend ships.
- Set a 32+ byte `SECRET_KEY` in `backend/.env` before shipping (JWT warning).
- Orphaned sidecars on hard-kill: `taskkill /F /IM finora-backend.exe /T` (+ `postgres.exe`).
- `ROTATE_REFRESH_TOKENS` recommended `False` (single-user, no blacklist app).

## 8. Context I still need before writing the code
- To deliver the full `sale/+page.svelte` cleanly in the next turn, I have the Sale screen, charges.py, models, serializers, and the shell registration pattern. Two small things I have not yet read that will affect exact wiring:
- `desktop/src/lib/components/SmartLookup.svelte` — to know if it can be reused for a ledger picker (does it accept a generic list, or is it hardcoded to type PARTY/ITEM via /api/search/suggest/?). If it's search-endpoint-bound, the ledger picker will be a plain select from a fetched api/ledgers/ list instead.
- `backend/apps/ledgers/urls.py` router basename — already seen (basename="ledger", router at ""), so GET /api/ledgers/?kind=DISCOUNT is correct.
-  yet need to verify from backend as source of truth
