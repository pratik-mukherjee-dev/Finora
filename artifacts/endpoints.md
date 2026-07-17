
# Finora — API Endpoint Reference & Proposals

> Scope: complete backend API surface (as implemented on `master`), frontend
> binding status, and proposed additions to unblock upcoming screens.
> Base prefix for all app routes below: `/api/`.

---

## 1. Available endpoints (implemented)

### Auth & Accounts — `/api/accounts/`
| Method | Path | Purpose |
| --- | --- | --- |
| POST | `auth/register/` | First-run user registration |
| POST | `auth/login/` | Obtain JWT access/refresh pair |
| POST | `auth/refresh/` | Refresh access token |
| POST | `auth/logout/` | Invalidate session |
| GET  | `auth/me/` | Current user profile |
| GET  | `auth/state/` | Bootstrap state (first-run / needs setup) |
| GET/POST/PUT/PATCH/DELETE | `companies/` | Company CRUD |
| GET  | `settings/` | Read user/company settings |
| POST | `settings/switch_multi/` | Upgrade to multi-company mode |
| POST | `settings/segregation/` | Toggle segregation preference |

### Financial Year — `/api/fy/`
| Method | Path | Purpose |
| --- | --- | --- |
| GET  | `` (list) | List financial years (bare array) |
| GET  | `{id}/` | Retrieve one FY |
| POST | `` | Open first / initial active FY |
| POST | `{id}/close/` | Close year, carry closing→opening stock |

### Catalogue — `/api/catalogue/`
| Method | Path | Purpose |
| --- | --- | --- |
| GET/POST/PUT/PATCH/DELETE | `items/` | Item CRUD |
| POST | `items/{id}/add_mapping/` | Add company mapping to an item |
| GET/POST/PUT/PATCH/DELETE | `categories/` | ItemCategory CRUD (filterable) |
| GET/POST/PUT/PATCH/DELETE | `mappings/` | ItemCompanyMapping CRUD; filter `?item=&company=` |

### Parties — `/api/parties/`
| Method | Path | Purpose |
| --- | --- | --- |
| GET/POST/PUT/PATCH/DELETE | `` | Party CRUD |
| GET | `{id}/ledger/` | Party ledger entries |

### Stock — `/api/stock/`
| Method | Path | Purpose |
| --- | --- | --- |
| GET  | `ledger/` | Stock ledger list (filterable) |
| POST | `ledger/adjust/` | Manual stock adjustment |
| GET  | `conversions/` | Stock conversion list |
| GET  | `conversions/{id}/` | Retrieve conversion |
| POST | `conversions/` | Create conversion (source→target) |
| POST | `conversions/{id}/cancel/` | Cancel/reverse conversion |

### Vouchers — `/api/vouchers/`
| Method | Path | Purpose |
| --- | --- | --- |
| GET  | `sales/` , `sales/{id}/` | Sale master list/retrieve (filter `?company=&party=`) |
| POST | `sales/` | Create sale master (triggers segregation) |
| POST | `sales/{id}/cancel/` | Soft-cancel + reversing entries |
| GET  | `sales-derived/` , `sales-derived/{id}/` | Derived company-sales (filter `?master=`) |
| GET  | `purchases/` , `purchases/{id}/` | Purchase list/retrieve (filter `?company=&party=`) |
| POST | `purchases/` | Create purchase |
| POST | `purchases/{id}/cancel/` | Soft-cancel + reversing entries |
| GET  | `received/` , `received/{id}/` | Receipt list/retrieve |
| POST | `received/` | Create receipt (auto-allocates open sales) |
| GET  | `received/{id}/allocations/` | Allocation breakdown |
| POST | `received/{id}/cancel/` | Soft-cancel + reverse allocations |
| GET  | `payments/` , `payments/{id}/` | Payment list/retrieve |
| POST | `payments/` | Create payment (auto-allocates open purchases) |
| GET  | `payments/{id}/allocations/` | Allocation breakdown |
| POST | `payments/{id}/cancel/` | Soft-cancel + reverse allocations |
| GET/POST/PATCH | `number-seqs/` | Voucher numbering templates per (company, type, FY) |

### Search — `/api/search/`
| Method | Path | Purpose |
| --- | --- | --- |
| GET  | `suggest/?type=&q=&limit=` | Type-ahead (ITEM / PARTY), frequency-ranked |
| POST | `record/` | Record a selection (usage counter) |

### Reports — `/api/reports/`
| Method | Path | Purpose |
| --- | --- | --- |
| GET  | `sales/` | Sales report (filter: company, party, date_from, date_to, category, item) |
| GET  | `purchases/` | Purchase report (same filters) |
| GET  | `stock/` | Stock movement report (company, mapping, date range) |
| GET  | `daily-sheet/?date=&company=` | End-of-day summary |

### Misc
| Method | Path | Purpose |
| --- | --- | --- |
| GET  | `/health/` | Sidecar health check |
| —    | `/admin/` | Django admin |

---

## 2. Frontend binding status

| Area | Status |
| --- | --- |
| Auth, companies, settings | ✅ Bound |
| Financial year (create/list) | ✅ Bound |
| FY close (`{id}/close/`) | ⚠️ Endpoint exists, no UI |
| Catalogue items / mappings | ✅ Bound (via SmartLookup + dialogs) |
| Categories CRUD | ⚠️ Endpoint exists, no UI |
| Parties (create/suggest) | ✅ Bound |
| Party ledger (`{id}/ledger/`) | ⚠️ Endpoint exists, no UI |
| Search suggest / record | ✅ Bound |
| Purchase | ✅ Screen built |
| Payment / Received | ✅ Screen built |
| Sale master + derived view | ✅ Screen built |
| `sales-derived/` standalone + backtrack | ⚠️ Partial (embedded only) |
| Stock ledger / adjust / conversions | ❌ No screen (build step 7) |
| Reports + daily sheet | ❌ No screen (build step 8) |
| `number-seqs/` (Settings) | ❌ No screen (build step 9) |

---

## 3. Proposed new endpoints

These fill gaps where a screen needs data the current API cannot supply cleanly.

### 3.1 Settlement — open-bills preview (highest priority)
**Problem:** Payment/Received screens can only show what *did* settle (post-save,
via `{id}/allocations/`). There is no way to preview what *will* settle, or to
show the party's outstanding before the user commits an amount.

**Proposal:**
```
GET /api/vouchers/payments/open_bills/?party=<id>&company=<id>
GET /api/vouchers/received/open_bills/?party=<id>&company=<id>
```
Returns outstanding bills oldest→latest (dry-run of the reconciliation selector),
so the UI can show a live allocation preview as the amount is typed.

Suggested response:
```json
{
  "party": 12,
  "outstanding_total": 4200.00,
  "bills": [
    { "bill_type": "PURCHASE", "bill_id": 55, "number": "P-0007",
      "date": "2026-04-02", "total": 1500.00, "settled": 500.00, "open": 1000.00 }
  ]
}
```
Implementation: reuse `reconciliation` logic in read-only mode (no writes).

### 3.2 Party balance (lightweight)
**Problem:** No cheap way to show a party's current directional balance without
pulling the full ledger.

**Proposal:** add `balance` (and optionally `open_receivable` / `open_payable`)
to `PartySerializer`, **or**:
```
GET /api/parties/{id}/balance/
```
Enables showing outstanding on the Payment/Received party pick and a party badge.

### 3.3 Home dashboard aggregate
**Problem:** `/app` home is static.

**Proposal:**
```
GET /api/reports/dashboard/?company=<id>&date=<YYYY-MM-DD>
```
Returns today's sale/purchase/receipt/payment totals + counts and a few KPIs
(open receivables, open payables, low-stock count) for the landing screen.

### 3.4 Sale-derived backtrack convenience (optional)
**Problem:** From a derived company-sale, jumping back to its master requires the
client to already hold `master`. This is available via the `master` FK, so likely
**no new endpoint needed** — confirm `sales-derived/{id}/` includes `master` and
`sales/{id}/` returns embedded `derived[]` (it does today).

---

## 4. Confirmations to verify before building
- `mappings/?item=<id>` **without** `company` returns *all* mappings for that item
  (needed for the multi-company **CompanyPicker** on Sale lines).
- Report list endpoints paginate consistently (pagination is currently disabled
  in `base.py`; large report result sets may need it re-enabled with an opt-in).
- `number-seqs/` PATCH bumps `high_water` correctly on manual voucher numbers.

---

## 5. Suggested build order for remaining bindings
1. **Settlement open-bills preview** (3.1) — biggest UX win, small backend change.
2. **Stock** screen + **Stock Convert** (ledger/adjust/conversions).
3. **Reports** + **Daily Sheet**.
4. **Party ledger** view (+ balance, 3.2).
5. **Settings**: voucher number templates (`number-seqs/`), FY close action.
6. **Home dashboard** aggregate (3.3).