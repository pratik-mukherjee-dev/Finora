# Finora — Desktop UI Design Principles (Source of Truth)

> The single source of truth for building and refactoring all Finora screens.
> Goal: a **native desktop ERP feel** — persistent chrome, keyboard-first,
> mouse-complete, no browser-style navigation.
>
> **Scope:** v1 (current version). v2 hooks (GST, e-invoice, multi-branch) are
> designed as structural slots only — **not implemented in v1**.

---

## 0. The One Rule

> **Every action is reachable by mouse and keyboard at all times.
> The shortcut is always shown on its mouse target. There is no input "mode".**

Mouse and keyboard are two always-on paths to the *same* action, never a toggle.
Mouse users learn shortcuts because the app keeps showing them; keyboard users
never need the mouse. This single principle drives every decision below.

---

## 1. Core Principles

1. **Persistent shell, swapping workspace.** The app frame (activity bar, context
   bar, workspace, context panel, status bar) never unmounts. Screens render into
   one `<Workspace>` slot. No per-screen "← Back" buttons.
2. **One command registry, many surfaces.** All actions live in `lib/commands.ts`.
   Activity bar, menus, command palette, and the key listener all dispatch the
   *same* `run()`. No duplicated logic, no divergence.
3. **Keyboard-first, mouse-complete.** Every navigation and primary action has a
   shortcut *and* a click target. Nothing is keyboard-only or mouse-only.
4. **Discoverability without modes.** Shortcuts are shown inline on their mouse
   targets (tooltip, menu hint, palette badge). Learning is passive.
5. **Voucher-first flow.** Login → company/FY resolved → land ready to start a
   voucher. Enforce only truly-required fields.
6. **Modal for creation, inline for editing.** Create dialogs are modal; row edits
   happen inline in grids.
7. **Density over whitespace.** Compact rows, tab-driven grids, right-docked
   context panels — desktop users want information density.
8. **Adjustable, not rewritten.** Modules, commands, grid columns, panels, reports,
   and settings are registries/slots so v2 is additive.

---

## 2. Global Layout (persistent chrome)

```
┌───────────────────────────────────────────────────────────────────────────┐
│  TITLE BAR   Finora · [Company ▾]  · FY 2026–2027        [user]  [– □ ✕]    │  (A)
├──────┬────────────────────────────────────────────────────────────────────┤
│      │  CONTEXT BAR: screen title · quick actions            [Ctrl+K Search]│  (C)
│  A   ├────────────────────────────────────────────────────────────────────┤
│  C   │                                                             ┌───────┐│
│  T   │                                                             │       ││
│  I   │                     WORKSPACE  (screen slot)                │ CTX   ││
│  V   │                                                             │ PANEL ││
│  I   │                                                             │ (D)   ││
│  T   │                                                             │       ││
│  Y   │                                                             └───────┘│
│ (B)  │                                                                      │
├──────┴────────────────────────────────────────────────────────────────────┤
│  STATUS BAR:  mode(single/multi) · FY writable ● · sync ● · shortcut hint   │  (E)
└───────────────────────────────────────────────────────────────────────────┘
```

- **(A) Title bar** — app name, **CompanyPicker** (multi mode only), FY badge,
  user menu. Custom Tauri window chrome.
- **(B) Activity bar** — primary module navigation (icons, optional labels),
  always visible. Density is a user preference (§6), not a mode.
- **(C) Context bar** — current screen title, screen-level quick actions,
  command-palette trigger.
- **(D) Context panel** — right dock: history, allocation preview, party ledger,
  validation. Collapsible; screens register its tabs.
- **(E) Status bar** — persistent state indicators + rotating shortcut hint
  (hint visibility is a preference).

Only the **workspace** and **context panel** scroll; there is no page-level scroll.

---

## 3. Modules (Activity Bar)

Each module is a command with a fixed shortcut. `Alt+<n>` jumps directly; the icon
is clickable and shows its shortcut on hover. Order follows daily workflow.

| # | Module | Shortcut | v1 Screen(s) | Endpoints | v2 hook |
| --- | --- | --- | --- | --- | --- |
| 1 | **Home / Dashboard** | `Alt+1` | KPI landing | `reports/dashboard/` (proposed) | widgets |
| 2 | **Sale** | `Alt+2` | Sale master + derived view | `vouchers/sales/`, `sales-derived/` | GST cols |
| 3 | **Purchase** | `Alt+3` | Purchase grid | `vouchers/purchases/` | GST, e-invoice |
| 4 | **Settle** | `Alt+4` | Payment / Received | `vouchers/{payments,received}/`, `.../allocations/`, `open_bills/` (proposed) | TDS |
| 5 | **Stock** | `Alt+5` | Ledger · Adjust · Convert | `stock/ledger/`, `ledger/adjust/`, `conversions/` | batch/serial |
| 6 | **Parties** | `Alt+6` | List + ledger + balance | `parties/`, `parties/{id}/ledger/`, `.../balance/` (proposed) | GSTIN |
| 7 | **Items** | `Alt+7` | Items + mappings + categories | `catalogue/items/`, `mappings/`, `categories/` | HSN, GST rate |
| 8 | **Reports** | `Alt+8` | Sales/Purchase/Stock/Daily sheet | `reports/*` | GSTR exports |
| 9 | **Settings** | `Alt+9` | Numbering, FY, mode, prefs | `number-seqs/`, `fy/`, `settings/` | license, GST cfg |

---

## 4. Keyboard Map

All bindings live in `lib/commands.ts`. The `F1` cheat-sheet and `Ctrl+K` palette
read from the same registry; screens register/unregister contextual commands on
mount/unmount.

### 4.1 Global (always active)
| Shortcut | Action |
| --- | --- |
| `Alt+1..9` | Jump to module |
| `Ctrl+K` | Command palette (fuzzy: modules, actions, records) |
| `Ctrl+P` | Quick-open a record (voucher #, party, item) |
| `Ctrl+,` | Settings |
| `Ctrl+Shift+C` | Switch company (multi mode) |
| `F1` | Shortcut cheat-sheet overlay |
| `Esc` | Close panel / dialog / palette (never navigates "back") |

### 4.2 Voucher screens (Sale / Purchase / Settle)
| Shortcut | Action |
| --- | --- |
| `Ctrl+N` | New voucher (clear form) |
| `Ctrl+Enter` | Save voucher |
| `Alt+A` | Add line |
| `Alt+D` | Delete focused line |
| `Tab` / `Shift+Tab` | Next/prev field (last cell → new line) |
| `Ctrl+↑ / Ctrl+↓` | Move between line rows |
| `Ctrl+E` | Edit selected history record (cancel + replace) |
| `Ctrl+H` | Toggle context/history panel |
| `F2` | Focus party field |
| `F4` | Open lookup for focused field |

### 4.3 Lookups & dialogs (SmartLookup)
| Shortcut | Action |
| --- | --- |
| `↑ / ↓` | Move highlight |
| `Enter` | Select highlighted / create if no match |
| `Ctrl+Enter` | Force "create new" with typed text |
| `Esc` | Close dropdown |

### 4.4 Grids / lists (Reports, Parties, Items, Stock)
| Shortcut | Action |
| --- | --- |
| `↑ / ↓` | Row navigation |
| `Enter` | Open / drill down |
| `Ctrl+F` | Focus filter |
| `Ctrl+R` | Refresh |
| `Ctrl+Shift+E` | Export (Reports) |

---

## 5. Screen Blueprints (v1)

- **Home (`Alt+1`)** — KPI cards (today's sales/purchases/receipts/payments, open
  receivables/payables, low-stock). Recent vouchers in context panel.
  Data: `reports/dashboard/` (proposed) or composed from `reports/*`.
- **Sale (`Alt+2`)** — header (party `F2`, date, segregate toggle in multi) + line
  grid; after save, read-only derived company-sales with backtrack. `F4` opens
  CompanyPicker when an item maps to multiple companies (`mappings/?item=`).
  Context panel: sale history (`Ctrl+E` to edit).
- **Purchase (`Alt+3`)** — same skeleton, single grid, affects stock. Lines send
  `mapping` id.
- **Settle (`Alt+4`)** — kind toggle, party, amount, date. Context panel shows a
  **live allocation preview** while typing (`open_bills/` proposed), replaced by
  actual allocation after save (`{id}/allocations/`).
- **Stock (`Alt+5`)** — tabs Ledger · Adjust · Convert
  (`ledger/`, `ledger/adjust/`, `conversions/` + cancel).
- **Parties (`Alt+6`)** — searchable list; row → ledger drill-down + running
  balance (`parties/{id}/ledger/`, `.../balance/` proposed).
- **Items (`Alt+7`)** — item list; detail shows per-company mappings (rate, stock,
  category); categories manager.
- **Reports (`Alt+8`)** — filter panel + results grid + totals + export; daily
  sheet as a tab (`reports/*`).
- **Settings (`Alt+9`)** — numbering templates (`number-seqs/`), FY list + close
  (`fy/{id}/close/`), mode/segregation (`settings/switch_multi/`,
  `settings/segregation/`), **Preferences** (§6), license (stub).

---

## 6. Preferences (not modes)

Presentation/binding preferences that respect user style without changing behavior:

- **Activity-bar density:** icons-only ↔ icons+labels.
- **Shortcut hints:** show/hide tooltips + status-bar hint.
- **Keymap profile (v2):** default ↔ Tally-style — a registry lookup swap.
- **Remappable keys (v2):** bindings are data; rebinding needs no code change.

No preference introduces hidden behavioral state; they only affect presentation
and key bindings.

---

## 7. Visual System (tokens)

Centralize in `lib/theme.css`; every screen consumes variables (enables v2 theming).

```css
:root {
  /* surfaces */
  --bg-app:      #0f1115;
  --bg-panel:    #12151c;
  --bg-elevated: #171a21;
  --border:      #1f2530;
  --border-hi:   #2a2f3a;
  /* text */
  --text:        #e6e8ec;
  --text-muted:  #9aa0aa;
  /* accent / state */
  --accent:      #2f6feb;
  --accent-soft: #16233b;
  --accent-text: #6ea8ff;
  --ok:          #6ee7a8;
  --warn:        #ffc15c;
  --danger:      #ff6b6b;
  /* metrics */
  --radius:      8px;
  --rail-w:      64px;   /* activity bar, icon mode */
  --rail-w-exp:  200px;  /* activity bar, expanded */
  --panel-w:     300px;  /* context panel */
  --row-h:       36px;   /* grid density */
  --font: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif;
}
```

- **Focus ring:** 2px `--accent` outline on every focusable element.
- **Density:** grid rows `--row-h`; spacing 12–14px, not 24px+.

---

## 8. Component Contract (shell)

| Component | Responsibility |
| --- | --- |
| `AppShell.svelte` | Renders A–E; owns global key listener; workspace slot |
| `ActivityBar.svelte` | Module list, active state, `Alt+n`, density preference |
| `ContextBar.svelte` | Screen title, quick-action slot, palette trigger |
| `ContextPanel.svelte` | Collapsible right dock; screens register tabs |
| `StatusBar.svelte` | Mode / FY / sync indicators, shortcut hint |
| `CommandPalette.svelte` | `Ctrl+K`; reads `lib/commands.ts` |
| `ShortcutCheatSheet.svelte` | `F1` overlay; reads `lib/commands.ts` |
| `SmartLookup.svelte` | (exists) type-ahead + create; keyboard per §4.3 |
| `PartyCreateDialog` / `ItemCreateDialog` | (exist) modal create |
| `DataGrid.svelte` | Shared keyboard-navigable grid for lists/reports |

**Single registry:** `lib/commands.ts` entries are
`{ id, label, icon, shortcut, run, when }`. Modules are commands that navigate.
Tooltips, menus, palette, and cheat-sheet all render from it.

---

## 9. v2 Adjustability Hooks (structural only in v1)

Ship these as **empty registries/slots** now — not placeholder screens:

- **Command/module registry** — add GST Returns, e-Invoice as one entry each.
- **Column-driven voucher grids** — GST columns (HSN, tax %, CGST/SGST/IGST) drop
  in via config, no markup rewrite.
- **Context-panel providers** — screens register panel tabs (e.g. "Tax summary").
- **Status-bar slots** — sync/backup/GST-filing indicators later.
- **Settings-section registry** — GST config, e-invoice creds, branches.
- **Theme tokens** — light mode / branding.
- **Report registry** — GSTR-1/3B register alongside existing reports.

---

## 10. Refactor Checklist (current → this scheme)

1. Introduce `AppShell` with regions A–E; wrap `/app/*`. Screens become workspace
   content (routes kept for deep-linking).
2. Build `lib/commands.ts` (merges modules + shortcuts into one registry).
3. Replace per-screen "← Home" with activity-bar navigation.
4. Convert Purchase/Sale/Settle history sidebars into `ContextPanel` tabs.
5. Add `CommandPalette` (`Ctrl+K`) and `ShortcutCheatSheet` (`F1`).
6. Extract colors to `lib/theme.css`.
7. Add missing v1 screens: Home, Parties, Items, Reports, Stock, Settings.
8. Add Preferences (§6) to Settings.
9. Wire proposed endpoints (`open_bills/`, `parties/{id}/balance/`,
   `reports/dashboard/`) where marked.
