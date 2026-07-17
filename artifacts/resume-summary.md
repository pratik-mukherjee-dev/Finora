# Finora — Session Resume (Desktop shell refactor complete; next: new screens)

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
- **Backend:** Django + DRF, nine apps under `backend/apps/`
  (`common, accounts, financialyear, catalogue, parties, stock, vouchers, search,
  reports`). JWT auth. services/ (write) + selectors/ (read) split, atomic txns.
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
- **search:** `suggest/?type=&q=`, `record/`.
- **reports:** `sales/`, `purchases/`, `stock/`, `daily-sheet/`,
  **`dashboard/` (proposed)**.
- **Sale line contract quirk:** Sale lines send `item` id + optional `company`
  (server resolves mapping). **Purchase lines send `mapping` id.** Do not confuse.

## 3. Backend contracts DRAFTED but NOT yet applied to repo
Provided as full file contents in an earlier turn; still need to be committed +
exe rebuilt before the desktop can call them:
- `vouchers/selectors/bills.py` — shared `_open_bills`, **excludes cancelled bills**
  (also a correctness fix), adds `open_bills_preview(party, kind)`.
- `vouchers/selectors/__init__.py` — export `open_bills_preview`.
- `vouchers/views.py` — `open_bills` action on Received + Payment (`detail=False`).
- `parties/views.py` — `balance` action.
- `reports/selectors.py` + `reports/views.py` + `reports/urls.py` — `dashboard/`.
> ⚠️ These are pending. The refactored Settle screen already calls
> `open_bills/`; it will 404 until the backend change is built into the exe.

## 4. What is built & verified (pre-existing)
- Tauri shell + sidecar wiring + `api.ts` (JWT, port discovery, `waitForBackend`).
- Auth flow (register/login/logout), company setup, **FY gate** working end-to-end.
- SmartLookup + PartyCreateDialog + ItemCreateDialog components.
- Voucher screens Purchase, Sale, Settle (Payment/Received) — functionally complete
  against the backend (pre-refactor versions).

## 5. What THIS session did — desktop-native shell refactor
Moved the app from browser-style (per-page chrome, back buttons, route nav) to a
**persistent desktop shell** per the design doc. New/changed files (all delivered
inline as full contents this session):

**Foundation (new):**
- `desktop/src/lib/theme.css` — design tokens (surfaces, text, accent/state,
  metrics, focus ring). Single source for color/metrics.
- `desktop/src/lib/commands.ts` — single command/module registry (Alt+1..9),
  `activeModuleId(pathname)`.
- `desktop/src/lib/shortcuts.ts` — `keychordOf(e)`, `inEditable(target)`.
- `desktop/src/lib/shell/shellContext.svelte.ts` — **teleport/context API**:
  `createShellState()`, `setShell/useShell`, screens register
  `{title, actions, panel[], shortcuts[]}`; supports tabbed panel + `activeTab`.
- `desktop/src/lib/shell/useScreen.svelte.ts` — `registerScreen(build)` helper
  (auto-dispose on unmount).

**Shell components (new):**
- `components/shell/ActivityBar.svelte` — module rail, active state, collapse,
  shortcut hints, mode filtering.
- `components/shell/ContextBar.svelte` — screen title + quick-action buttons
  (each shows its shortcut) + palette trigger.
- `components/shell/ContextPanel.svelte` — **shell-hosted tabbed right dock**;
  renders the active screen's panel tab snippet.
- `components/shell/CommandPalette.svelte` — `Ctrl+K` fuzzy module jump.

**Shell host (new/replaced):**
- `routes/app/+layout.svelte` — persistent shell: ActivityBar + topbar
  (company picker, FY badge, logout) + ContextBar + workspace + ContextPanel +
  status bar. Owns the global key listener: `Ctrl+K` palette, `Ctrl+H` toggle
  panel, `Ctrl+,` settings, `Alt+1..9` modules, and dispatches screen-registered
  contextual shortcuts (modified chords fire even inside inputs).
- `routes/app/+page.svelte` — trimmed to a lean **Home** workspace (chrome removed;
  now lives in the layout). Placeholder for dashboard KPIs.

**Screens refactored to the shell (full files delivered):**
- `routes/app/purchase/+page.svelte` — no page chrome/back button; tokens; History
  moved into a shell **panel tab**; actions/shortcuts (`Ctrl+N`, `Alt+A`,
  `Ctrl+Enter`) registered.
- `routes/app/sale/+page.svelte` — same, with **two panel tabs: History + Derived**
  (read-only company-sales moved out of the workspace into the Derived tab);
  history "▣" jumps to Derived tab.
- `routes/app/settle/+page.svelte` — **two panel tabs: History + Allocation**.
  Allocation tab shows a **live open-bills preview** (calls proposed
  `open_bills/`) with a client-side "will settle" plan as the amount is typed;
  after save it shows the actual allocation; picking a history row loads
  `{id}/allocations/`.

**Design decisions locked this session:**
- Not two "modes" — mouse + keyboard are always-on paths to the same commands;
  the shortcut is shown on its mouse target. No input-mode toggle. Preferences
  (rail density, hint visibility) instead of modes.
- **Context panel is fully shell-hoisted** via the context API (chosen over
  in-screen panels) for clean separation; screens only declare panel tab snippets.
- **Pre-auth screens stay full-page** (boot `routes/+page.svelte`, login, register,
  setup, fy) — they render before the shell exists; only theme tokens apply.

## 6. Exact next steps (in order)
1. **Apply the pending backend contracts (§3)** and rebuild the exe, so
   `open_bills/`, `parties/{id}/balance/`, `reports/dashboard/` exist. Settle's
   Allocation preview depends on `open_bills/`.
2. **Build the new v1 screens** (all inside the shell, register title/actions/
   panel/shortcuts; use tokens; no back buttons). Per design doc module order:
   - **Home dashboard** (`reports/dashboard/`) — replace the placeholder.
   - **Stock** (`Alt+5`) — tabs Ledger · Adjust · Convert
     (`stock/ledger/`, `ledger/adjust/`, `conversions/` + cancel).
   - **Parties** (`Alt+6`) — list + ledger drill-down + balance
     (`parties/`, `{id}/ledger/`, `{id}/balance/`).
   - **Items** (`Alt+7`) — items + per-company mappings + categories
     (`catalogue/items/`, `mappings/`, `categories/`, `items/{id}/add_mapping/`).
   - **Reports** (`Alt+8`) — filter panel + grid + totals + export; daily-sheet tab
     (`reports/*`).
   - **Settings** (`Alt+9`) — numbering (`number-seqs/`), FY close
     (`fy/{id}/close/`), mode/segregation, Preferences (rail density, hints).
3. **Optional polish:** `ShortcutCheatSheet.svelte` (`F1`) reading `commands.ts`;
   `Ctrl+P` quick-open record; DataGrid shared component for lists/reports.

## 7. Known caveats / non-blocking
- Refactored screens still have their own `onMount` auth-gate redirect; the layout
  also gates. Harmless double-guard; can centralize later.
- `open_bills/` live preview will 404 until §3 backend is built — expected.
- `low_stock_count` in proposed dashboard uses `stock <= 0`; threshold is a v2
  setting.
- Set a 32+ byte `SECRET_KEY` in `backend/.env` before shipping (JWT warning).
- Orphaned sidecars on hard-kill can lock the exe: `taskkill /F /IM
  finora-backend.exe /T` (+ `postgres.exe`).
- `ROTATE_REFRESH_TOKENS` recommended `False` (single-user, no blacklist app).
