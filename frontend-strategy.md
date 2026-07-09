# Finora Frontend Strategy

## Stack
- Tauri (Rust shell) + SPA. Native window, not web-like.
- Framework: Svelte or React (lightweight). Recommend Svelte for size/speed.
- Talks to local Django API over localhost port (from Tauri config).
- Tauri manages Postgres + Django sidecars.

## Principles
- Voucher-first: login → pick/setup company → start sale/purchase immediately.
- No blocking on blank fields; only truly-required enforced.
- Keyboard-driven, desktop feel (shortcuts, tab flow, no browser chrome).

## Global Components
- SmartLookup: debounced type-ahead calling /api/suggest, frequency-ranked. On no-match after full type → inline create pop-up pre-filled with typed text.
  - PartyLookup: create pop-up (name pre-filled, optional fields).
  - ItemLookup: create pop-up, company defaults to current, editable mapping, category shown per company.
- CompanyPicker dialog: shown for a line only when item maps to multiple companies.
- ConfirmReverse dialog: for cancel/edit chain reactions.

## Screens
- Auth + license mode select (single/multi) on first login.
- Company setup / default company + segregation preference (multi mode).
- Sale (master): grid rows (item, qty, rate auto/editable, amount, resolved company). Duplicate item blocked unless company differs. Save → shows derived company-sales (read-only view, backtrack link).
- Purchase: similar grid, affects stock.
- Payment / Received: party + amount only; shows auto-allocation result (bills settled oldest→latest).
- Stock: list per company mapping, manual override entry.
- Stock Convert: source item+qty → target item+qty (auto-create target), both directions.
- Reports: full filter panel (date, company, party, item, category, voucher type), export.
- Daily Sheet: end-of-day summary + detail, cash vs accounts match.
- Financial Year: list, close-year action (read-only after).
- Settings: voucher number template per (company, type), license info (stub).

## State
- Current user, current company, current FY, mode(single/multi) in app store.
- Derived/cancelled vouchers rendered read-only.

## API Integration
- Central api client with base localhost URL, error toasts.
- Suggest calls debounced (~150ms), abortable.
- All voucher saves show server-computed results (numbering, allocations, derived sales).

## UX Rules
- Rate edit persists back to item mapping (inform user subtly).
- High-water voucher numbering shown, editable manually.
- Negative stock allowed silently on sale (optional soft warning).

## Build Order
1. Tauri shell + sidecar wiring + api client
2. Auth + company setup + app store
3. SmartLookup (party/item) + create pop-ups
4. Purchase screen
5. Payment/Received + allocation display
6. Sale master + company picker + derived view
7. Stock + convert
8. Reports + daily sheet
9. FY + settings
