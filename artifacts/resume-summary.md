**Finora - Session Resume Summary**

**Date:** 2026-07-22

#### What Finora Is
A Tally-inspired desktop accounting application built with **Svelte 5 (Runes)** frontend + **Tauri** desktop shell + **Django REST** backend + **embedded PostgreSQL**. Targets small Indian businesses needing offline-first invoicing, party management, and settlement tracking.

#### Architecture
- **Frontend:** `desktop/src/` - SvelteKit with Svelte 5 runes (`$state`, `$derived`, `$effect`), custom shell system (`registerScreen`), enter-key flow navigation (`enterFlow`), `SmartLookup`/`LedgerLookup` components
- **Backend:** `backend/apps/` - Django with service-layer pattern (models → selectors → services → views). Key apps: `accounts`, `parties`, `vouchers`, `catalogue`, `stock`, `ledgers`, `financialyear`
- **Voucher system:** `VoucherBase` (abstract) → `SaleMaster`, `SaleDerived`, `Purchase`, `Received`, `Payment`. All use `SoftCancelModel` (soft-delete with `is_cancelled` flag, `NonCancelledManager` as default)
- **Charges:** `VoucherCharge` model stores discount/round-off/GST per voucher. `apply_charges()` is the pure calculator, `persist_charges()` writes to DB
- **Segregation:** Multi-company sales split into `SaleDerived` per company with prorated charges and per-company round-off
- **Settlement:** `Allocation` model links receipts/payments to bills. `reconciliation.py` handles auto-allocation (oldest→latest). Inline settlement from sale/purchase pages targets a specific bill via `target_bill_id`
- **Party ledger:** `PartyLedger` tracks every debit/credit with running balance. `current_balance()` = `opening + sum(dr) - sum(cr)`

#### What's Been Built (Functional)
1. **Company/user/FY management** - multi-company mode, financial year locking
2. **Catalogue** - items, item-company mappings, rate tracking
3. **Stock** - movement tracking (qty_in/qty_out per mapping)
4. **Sale flow** - master + derived (segregation), line items, charges (discount + round-off), inline settlement, cancel with reversal
5. **Purchase flow** - similar to sale, stock posting, charges, inline settlement, cancel
6. **Settle page** - standalone payment/received with auto-allocation oldest→latest, open bills preview, settlement modes (Cash/UPI/etc.)
7. **Parties page** - CRUD, ledger view with voucher-type filter, balance display, inline edit
8. **Desktop shell** - command palette, keyboard shortcuts, tab panels, enter-key flow navigation
9. **Validation** - warning dialogs (soft blocks), confirm dialogs, overpay warnings
10. **License/settings** - max companies, license switching (partial)

#### Bugs Fixed This Session

1. **Round-off precision bug** (critical): `tally_default_round()` in `charges.py` used `precision=0.01` (round to paisa) instead of `precision=1` (round to rupee). This caused all round-off charges to compute as 0.00, making the stored `total_amount` exclude the round-off. **Fix:** Changed default precision to `1`.

2. **Balance vs Outstanding confusion** (UX): Settle page showed raw bill outstanding while Parties page showed ledger balance. These differ when on-account (advance) money exists. **Discussed but not yet committed:** Backend `open_bills_preview` should return both `balance` and `on_account` fields; both pages should show the breakdown.

#### Known Gaps / Not Yet Implemented

1. **Cancel from frontend** - Backend has full cancel support (`cancel_sale`, `cancel_purchase`, `cancel_received`, `cancel_payment`) but no cancel buttons exist in the frontend UI
2. **Orphaned allocations on bill cancel** - When a sale/purchase is cancelled, allocations from receipts/payments pointing at that bill are NOT reversed. Need `_reverse_bill_allocations()` in `cancel.py`
3. **On-account visibility** - Neither page shows on-account (advance) amounts. Backend needs to return `balance` + `on_account` from `open_bills_preview`; both Settle and Parties pages need the breakdown UI
4. **GST/Tax charges** - Slots exist (`CGST`, `SGST` in `VoucherCharge`) but v2 item-wise tax computation is not implemented
5. **Reports** - `reports` app exists but is empty (only `selectors.py` has some code). No P&L, balance sheet, or GSTR reports
6. **Search** - `search` app with trigram extension is set up but not wired to all entities
7. **Settings page** - Partially built frontend, needs completion
8. **Multi-company segregation edge cases** - Per-company round-off sum may differ from master round-off by a paisa across many companies (acceptable but worth documenting)
9. **Edit vouchers** - Currently "edit" = cancel old + create new. No true in-place edit
10. **Print/export** - No invoice printing or PDF/Excel export

#### Recommended Next Steps (Priority Order)

1. **Wire cancel buttons** in Sale, Purchase, and Settle page frontends (backend is ready)
2. **Fix orphaned allocations** - add `_reverse_bill_allocations` to `cancel_sale` and `cancel_purchase`
3. **On-account visibility** - add `balance` + `on_account` to `open_bills_preview` response; update Settle + Parties UI
4. **GST charges (v2)** - item-wise CGST/SGST computation, HSN codes, GSTR-1 data shape
5. **Reports** - Party statement, day book, outstanding reports
6. **Invoice print** - PDF generation for sale/purchase vouchers
