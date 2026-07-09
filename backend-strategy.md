# Finora Backend Strategy

## Stack
- Django + DRF, Postgres (embedded/portable, shipped via Tauri sidecar)
- Python 3.12+, pg_trgm for search
- Layout: services/ (write), selectors/ (read), pure-function core logic

## Core Locked Decisions
- One user, multiple company. Mode (single/multi) locked at license; upgrade unlocks multi.
- Item = shared master; ItemCompanyMapping = (item, company, category, rate, stock, opening_stock, +future GST). ItemCategory is company-specific.
- Party = unified, non-exclusive (customer+vendor), directional balance.
- Master sale (cashier input) → derived company-sales (read-only, traceable). One company per line, resolved from mapping; multi-mapping → user picks at entry.
- Negative stock allowed on sale.
- Master level: party ledger + payment/receipt reconciliation. Derived level: stock + per-company books.
- Payment/Received: reconcile against PARTY, oldest→latest, recursive, auto.
- Soft-cancel + reversing entries everywhere. No hard deletes.
- FY locking: voucher bound to active FY; closing FY → closing stock becomes next FY opening; closed FY read-only.
- Voucher numbering: template per (company, type, FY), high-water mark, no gap-fill.
- GST v2: nullable placeholder fields only in v1.

## Apps (backend/apps/)
- common: base mixins (TimeStamped, Audit, SoftCancel, FYBound), utils
- accounts: User, Company, UserCompany, license abstraction (LicenseInfo interface + local stub)
- catalogue: Item, ItemCategory, ItemCompanyMapping
- parties: Party, PartyBalance, ledger entries
- vouchers: Voucher (abstract), SaleMaster, SaleDerived, Purchase, Payment, Received, VoucherLine, numbering
- stock: StockLedger, StockConversion, opening/closing
- financialyear: FinancialYear, close/lock logic
- reports: selectors + filter endpoints, daily sheet
- search: trigram suggestion endpoint + per-user usage counter ranking

## Key Models (fields, minimal)
- Company(id, user, name, is_default, created)
- UserCompany(user, company, mode[single|multi], is_locked)
- License(user, plan, mode, valid_till, is_active)  # stub only
- Item(id, user, name, base_unit)
- ItemCategory(id, company, name)
- ItemCompanyMapping(id, item, company, category?, rate, stock, opening_stock, hsn?, gst_rate?, gst_mode?)  # gst_* nullable
- Party(id, user, name, phone?, address?, opening_balance)
- PartyLedger(id, party, voucher_ref, debit, credit, balance, date, fy)
- FinancialYear(id, user, start, end, is_active, is_closed)
- VoucherBase(id, company, party?, number, date, fy, is_cancelled, cancelled_ref?, created)
- SaleMaster(VoucherBase, segregate_flag)
- SaleDerived(VoucherBase, master_fk, source_line_fk)  # read-only
- Purchase(VoucherBase)
- Payment/Received(VoucherBase, party, amount, allocations[])
- VoucherLine(id, voucher, item, company_resolved, qty, rate, amount)
- StockLedger(id, mapping, voucher_ref, qty_in, qty_out, balance, date, fy, is_manual)
- StockConversion(id, source_mapping, target_mapping, source_qty, target_qty, factor, date, fy)
- VoucherNumberSeq(id, company, vtype, fy, template, high_water)

## Services (pure, testable)
- segregation.segregate_master_sale(master) -> [derived]: group lines by company_resolved, create read-only derived sales, write stock ledger per line, link back.
- reconciliation.apply_receipt(party, amount): fetch open sale bills oldest→latest, allocate recursively until amount exhausted or bills done.
- reconciliation.apply_payment(party, amount): same for purchases.
- stock.post_movement(mapping, in, out, ref)
- stock.convert(source, target, sqty, tqty): auto-create target mapping if absent, post out/in.
- numbering.next_number(company, vtype, fy): render template with high_water+1; on manual entry, bump high_water if higher.
- fy.close_year(fy): validate active, carry closing→opening stock, set read-only, activate next.
- cancel.reverse(voucher): soft-cancel + create reversing stock/ledger/derived entries in one transaction.

## Rules / Validation
- No duplicate item per bill unless company differs.
- Non-blocking validation: enforce only truly-required fields.
- All write services run in atomic transactions; use select_for_update on stock/party rows.
- Rate edit on line writes back to ItemCompanyMapping.rate.

## Search
- pg_trgm GIN index on Item.name, Party.name.
- UsageCounter(user, entity_type, entity_id, count) incremented on selection.
- Endpoint: /api/suggest?type=&q= -> top-N ordered by (count desc, trgm sim desc).

## API surface (DRF)
- CRUD: company, item, category, party, purchase, payment, received
- SaleMaster: create (triggers segregation), retrieve (with derived), cancel, edit
- SaleDerived: read-only list/retrieve
- StockConversion: create
- Reports: filterable list endpoints + daily-sheet aggregate
- FY: list, close
- suggest: search

## Packaging
- Portable Postgres in app data dir; initdb on first launch; random localhost port; Tauri sidecar lifecycle; pg_dump backups.

## Build Order
1. common + accounts + FY
2. catalogue + parties
3. stock + numbering
4. vouchers (purchase → payment/received → sale master+segregation)
5. reconciliation, cancel/reverse
6. stock conversion
7. search, reports, daily sheet
