<script lang="ts">
    import {enterFlow} from "$lib/flow";
    import {auth} from "$lib/stores/auth.svelte";
    import {goto} from "$app/navigation";
    import {onMount} from "svelte";
    import {request, type Suggestion} from "$lib/api";
    import SmartLookup from "$lib/components/SmartLookup.svelte";
    import PartyCreateDialog from "$lib/components/PartyCreateDialog.svelte";
    import ItemCreateDialog from "$lib/components/ItemCreateDialog.svelte";
    import ConfirmDialog from "$lib/components/ConfirmDialog.svelte";
    import WarningDialog from "$lib/components/WarningDialog.svelte";
    import type {Issue} from "$lib/validation";
    import LedgerLookup from "$lib/components/LedgerLookup.svelte";
    import {registerScreen} from "$lib/shell/useScreen.svelte";

    onMount(() => {
        if (!auth.isAuthed) return void goto("/login");
        if (auth.needsSetup) return void goto("/setup");
        if (auth.needsFy) return void goto("/fy");
        void loadHistory();
        void loadLedgers();
        void loadModes();
        if (charges.length === 0) charges = [newCharge()];   // default row for the enter-flow
        focusParty();
    });

    type Mapping = { id: number; item: number; item_name: string; company: number; rate: number; stock: number; };
    type Ledger = {
        id: number; company: number | null; name: string;
        kind: "DISCOUNT" | "ROUND_OFF" | "TAX" | "OTHER"; is_system: boolean; gst_rate: number | null;
    };
    type SavedCharge = {
        id: number; ledger: number; ledger_name: string; charge_type: string;
        mode: string; input_value: number; amount: number; sort_order: number;
    };
    type ChargeRow = {
        key: number; ledgerId: number | null; mode: "PERCENT" | "AMOUNT"; value: string;
    };
    type Line = {
        key: number; item: Suggestion | null; mapping: number | null;
        qty: string; rate: string; amount: string;
        resolving: boolean; note: string; noMapping: boolean; creatingMapping: boolean;
    };
    type PurchaseLine = {
        id: number;
        item: number;
        item_name: string;
        mapping: number;
        qty: number;
        rate: number;
        amount: number;
    };
    type Purchase = {
        id: number; company: number; party: number; party_name: string;
        number: string; date: string; total_amount: number; is_cancelled: boolean;
        lines: PurchaseLine[]; charges: SavedCharge[];
    };
    // User-level settlement mode (Cash/UPI/…) for the optional inline settlement.
    type SettlementMode = { id: number; name: string; is_system: boolean; is_active: boolean; sort_order: number; };

    let seq = 0;
    let chargeSeq = 0;
    const newLine = (): Line => ({
        key: ++seq, item: null, mapping: null, qty: "1", rate: "0",
        amount: "0.00", resolving: false, note: "", noMapping: false, creatingMapping: false,
    });
    const newCharge = (ledgerId: number | null = null): ChargeRow => ({
        key: ++chargeSeq, ledgerId, mode: "PERCENT", value: "0",
    });

    const today = new Date().toISOString().slice(0, 10);
    let party = $state<Suggestion | null>(null);
    let date = $state(today);
    let lines = $state<Line[]>([newLine()]);
    let saving = $state(false);
    let error = $state<string | null>(null);
    let saved = $state<{ number: string; total_amount: number } | null>(null);
    let history = $state<Purchase[]>([]);
    let loadingHistory = $state(false);
    let editingId = $state<number | null>(null);
    let partyDialog = $state<string | null>(null);
    let itemDialog = $state<{ text: string; lineKey: number } | null>(null);

    // ── optional inline settlement (creates a PAYMENT against THIS purchase) ───
    let modes = $state<SettlementMode[]>([]);
    let settleAmount = $state("0");
    let settleModeId = $state<number | null>(null);
    let settleNote = $state<string | null>(null);

    // ── charges: ledger catalogue + dynamic charge rows ───────────────────────
    let ledgers = $state<Ledger[]>([]);
    let charges = $state<ChargeRow[]>([]);
    let lastLedgerCompany = $state<number | null>(null);

    // ── enter-flow / confirm state ────────────────────────────────────────────
    let confirmOpen = $state(false);
    let warningIssues = $state<Issue[] | null>(null);
    let warningNext = $state<(() => void) | null>(null);
    let partyLookup = $state<{ focus: () => void } | null>(null);

    const companyId = $derived(auth.currentCompany?.id ?? null);
    const total = $derived(lines.reduce((s, l) => s + (Number(l.amount) || 0), 0));
    const canSave = $derived(!!party && !!companyId && lines.some((l) => l.mapping && Number(l.qty) > 0) && !saving);
    const round2 = (n: number) => (Math.round(n * 100) / 100).toFixed(2);

    const chargeLedgers = $derived(ledgers);
    const ledgerById = $derived(new Map(ledgers.map((l) => [l.id, l])));

    // Inline-settlement helpers (independent of the charge ledgers above).
    const modeOptions = $derived(modes.filter((m) => m.is_active).map((m) => ({id: m.id, name: m.name})));
    const settleModeName = $derived(modes.find((m) => m.id === settleModeId)?.name ?? null);

    // Options for a given charge row: all charge ledgers minus those already
    // chosen in OTHER rows (keep this row's own pick so it still displays).
    function optionsFor(row: ChargeRow) {
        const usedElsewhere = new Set(
            charges.filter((c) => c.key !== row.key && c.ledgerId != null).map((c) => c.ledgerId)
        );
        return chargeLedgers.filter((l) => l.id === row.ledgerId || !usedElsewhere.has(l.id));
    }

    // True when every available charge ledger is already used across rows.
    const allChargesUsed = $derived.by(() => {
        const used = new Set(charges.filter((c) => c.ledgerId != null).map((c) => c.ledgerId));
        return chargeLedgers.length > 0 && chargeLedgers.every((l) => used.has(l.id));
    });

    function focusSave() {
        setTimeout(() => document.querySelector<HTMLElement>('[data-flow="save"]')?.focus(), 0);
    }


    function kindOf(row: ChargeRow): Ledger["kind"] | null {
        return row.ledgerId != null ? (ledgerById.get(row.ledgerId)?.kind ?? null) : null;
    }

    const discountPreview = $derived.by(() => {
        let d = 0;
        for (const c of charges) {
            if (kindOf(c) !== "DISCOUNT") continue;
            const v = Number(c.value) || 0;
            if (v <= 0) continue;
            d += c.mode === "PERCENT" ? (total * v) / 100 : v;
        }
        return d;
    });
    const afterDiscount = $derived(total - discountPreview);
    const hasRoundOff = $derived(charges.some((c) => kindOf(c) === "ROUND_OFF"));
    const roundDelta = $derived(hasRoundOff ? Math.round(afterDiscount) - afterDiscount : 0);
    const finalBill = $derived(afterDiscount + roundDelta);

    function onQtyOrRate(l: Line) {
        l.amount = round2((Number(l.qty) || 0) * (Number(l.rate) || 0));
    }

    function onAmount(l: Line) {
        const q = Number(l.qty) || 0;
        l.rate = q > 0 ? round2((Number(l.amount) || 0) / q) : "0";
    }

    async function loadLedgers() {
        if (companyId == null) return;
        try {
            const p = new URLSearchParams({company: String(companyId)});
            const rows = await request<Ledger[] | { results?: Ledger[] }>(`/api/ledgers/?${p.toString()}`);
            ledgers = Array.isArray(rows) ? rows : (rows?.results ?? []);
            lastLedgerCompany = companyId;
        } catch {
            ledgers = [];
        }
    }

    // User-level settlement modes for the inline settlement picker.
    async function loadModes() {
        try {
            const rows = await request<SettlementMode[] | { results?: SettlementMode[] }>(
                "/api/accounts/settlement-modes/"
            );
            modes = Array.isArray(rows) ? rows : (rows?.results ?? []);
            if (settleModeId == null) {
                const active = modes.filter((m) => m.is_active);
                const sys = active.find((m) => m.is_system);
                settleModeId = sys?.id ?? active[0]?.id ?? null;
            }
        } catch {
            modes = [];
        }
    }

    $effect(() => {
        if (companyId != null && companyId !== lastLedgerCompany) void loadLedgers();
    });

    async function loadHistory() {
        if (!companyId) return;
        loadingHistory = true;
        try {
            const p = new URLSearchParams({company: String(companyId)});
            const rows = await request<Purchase[] | {
                results?: Purchase[]
            }>(`/api/vouchers/purchases/?${p.toString()}`);
            history = Array.isArray(rows) ? rows : (rows?.results ?? []);
        } catch {
            history = [];
        } finally {
            loadingHistory = false;
        }
    }

    async function openForEdit(prow: Purchase) {
        if (prow.is_cancelled) return;
        error = null;
        saved = null;
        editingId = prow.id;
        party = {id: prow.party, name: prow.party_name};
        date = prow.date;
        lines = prow.lines.map((pl) => ({
            key: ++seq, item: {id: pl.item, name: pl.item_name}, mapping: pl.mapping,
            qty: String(pl.qty), rate: String(pl.rate), amount: round2(Number(pl.qty) * Number(pl.rate)),
            resolving: false, note: "", noMapping: false, creatingMapping: false,
        }));
        if (lines.length === 0) lines = [newLine()];
        hydrateCharges(prow.charges ?? []);
    }

    function hydrateCharges(rows: SavedCharge[]) {
        charges = rows.map((c) => ({
            key: ++chargeSeq,
            ledgerId: c.ledger,
            mode: c.mode === "AMOUNT" ? "AMOUNT" : "PERCENT",
            value: String(c.input_value ?? 0),
        }));
    }

    function resetForm() {
        editingId = null;
        party = null;
        date = today;
        lines = [newLine()];
        charges = [newCharge()];
        error = null;
        saved = null;
        focusParty();
    }

    function onPartySelect(s: Suggestion) {
        party = s;
    }

    function onPartyCreate(t: string) {
        partyDialog = t;
    }

    function onPartyCreated(p: Suggestion) {
        party = p;
        partyDialog = null;
        setTimeout(() => (document.getElementById("date") as HTMLElement | null)?.focus(), 0);
    }


    async function resolveMapping(line: Line, itemId: number) {
        if (!companyId) return;
        line.resolving = true;
        line.note = "";
        line.noMapping = false;
        try {
            const params = new URLSearchParams({item: String(itemId), company: String(companyId)});
            const rows = await request<Mapping[]>(`/api/catalogue/mappings/?${params.toString()}`);
            const list = Array.isArray(rows) ? rows : ((rows as { results?: Mapping[] })?.results ?? []);
            if (list.length > 0) {
                line.mapping = list[0].id;
                line.rate = String(list[0].rate ?? 0);
                onQtyOrRate(line);
            } else {
                line.mapping = null;
                line.noMapping = true;
                line.note = "No mapping for this company.";
            }
        } catch (e) {
            line.note = e instanceof Error ? e.message : "Failed to resolve mapping.";
        } finally {
            line.resolving = false;
        }
    }

    async function createMapping(line: Line) {
        if (!companyId || !line.item) return;
        line.creatingMapping = true;
        line.note = "";
        try {
            const m = await request<Mapping>("/api/catalogue/mappings/", {
                method: "POST",
                body: JSON.stringify({
                    item: line.item.id,
                    company: companyId,
                    rate: Number(line.rate) || 0,
                    opening_stock: 0
                }),
            });
            line.mapping = m.id;
            line.noMapping = false;
            line.rate = String(m.rate ?? line.rate ?? 0);
            onQtyOrRate(line);
        } catch (e) {
            line.note = e instanceof Error ? e.message : "Could not create mapping.";
        } finally {
            line.creatingMapping = false;
        }
    }

    function onItemSelect(line: Line, s: Suggestion) {
        line.item = s;
        line.mapping = null;
        line.noMapping = false;
        void resolveMapping(line, s.id);
    }

    function onItemCreate(line: Line, t: string) {
        itemDialog = {text: t, lineKey: line.key};
    }

    function onItemCreated(i: Suggestion) {
        const target = lines.find((l) => l.key === itemDialog?.lineKey);
        const key = itemDialog?.lineKey;
        itemDialog = null;
        if (target) {
            target.item = i;
            void resolveMapping(target, i.id);
            if (key != null) focusRowQty(key);
        }
    }

    function excludeItems(lineKey: number): Set<number> {
        return new Set(
            lines.filter((l) => l.key !== lineKey && l.item != null).map((l) => l.item!.id)
        );
    }

    function addLine() {
        lines = [...lines, newLine()];
    }

    // Enter on the last line's amount: add a new line and focus it (keeps Alt+A too).
    function onLineEnter(e: KeyboardEvent, line: Line) {
        if (e.key !== "Enter" || e.ctrlKey || e.metaKey) return;
        const isLast = lines[lines.length - 1]?.key === line.key;
        if (!isLast) return;               // not last -> let normal flow advance
        e.preventDefault();
        e.stopPropagation();
        addLine();
        const created = lines[lines.length - 1];
        setTimeout(() => {
            const rows = Array.from(document.querySelectorAll<HTMLElement>(".grow"));
            const idx = lines.findIndex((l) => l.key === created.key);
            rows[idx]?.querySelector<HTMLInputElement>('[data-flow="item"]')?.focus();
        }, 0);
    }

    function removeLine(key: number) {
        lines = lines.length > 1 ? lines.filter((l) => l.key !== key) : lines;
    }

    // Enter on an empty item field of the last, blank line: drop it and advance.
    function onLineEmptyEnter(line: Line) {
        const isLast = lines[lines.length - 1]?.key === line.key;
        const blank = !line.item && (line.qty === "" || Number(line.qty) === 0 || line.qty === "1") && Number(line.amount) === 0;
        if (isLast && lines.length > 1 && blank) {
            removeLine(line.key);
        }
        // Move focus to the first charge row's picker (next flow step).
        setTimeout(() => document.querySelector<HTMLElement>('[data-flow="charge"]')?.focus(), 0);
    }

    // ── charge row management ─────────────────────────────────────────────────
    function addCharge() {
        // Default the picker to the first unused charge ledger, if any.
        // const used = new Set(charges.map((c) => c.ledgerId));
        // const first = chargeLedgers.find((l) => !used.has(l.id)) ?? chargeLedgers[0] ?? null;
        // charges = [...charges, newCharge(first?.id ?? null)];
        charges = [...charges, newCharge()];
        setTimeout(() => {
            const rows = document.querySelectorAll<HTMLElement>('[data-flow="charge"]');
            rows[rows.length - 1]?.focus();
        }, 0);
    }

    // Enter on the last charge's value: chain a new charge. Never let it reach
    // the flow root (which would also open the confirm dialog).
    function onChargeEnter(e: KeyboardEvent, charge: ChargeRow) {
        if (e.key !== "Enter" || e.ctrlKey || e.metaKey) return;
        e.preventDefault();
        e.stopImmediatePropagation();        // hard stop: no flow-root, no dialog
        const isLast = charges[charges.length - 1]?.key === charge.key;
        if (isLast) {
            if (allChargesUsed) focusSave();   // nothing left to add -> go to Save
            else addCharge();
        } else {
            // advance to the next charge row's picker manually
            const idx = charges.findIndex((c) => c.key === charge.key);
            const nextKey = charges[idx + 1]?.key;
            setTimeout(() => {
                const rows = Array.from(document.querySelectorAll<HTMLElement>('[data-flow="charge"]'));
                rows[idx + 1]?.focus();
            }, 0);
        }
    }

    // Enter after picking a ledger. For ROUND_OFF (no value field) chain/advance;
    // for DISCOUNT, move focus into its value input instead.
    function onChargePicked(charge: ChargeRow) {
        const kind = kindOf(charge);
        if (kind === "DISCOUNT") {
            setTimeout(() => {
                const rows = Array.from(document.querySelectorAll<HTMLElement>('[data-flow="charge"]'));
                const idx = charges.findIndex((c) => c.key === charge.key);
                const row = rows[idx]?.closest(".chrow");
                row?.querySelector<HTMLInputElement>('[data-flow="charge-val"]')?.focus();
            }, 0);
            return;
        }
        // No-value kind (ROUND_OFF / CGST / SGST): chain if ledgers remain, else Save.
        const isLast = charges[charges.length - 1]?.key === charge.key;
        if (isLast && !allChargesUsed) addCharge();
        else focusSave();
    }



    function removeCharge(key: number) {
        charges = charges.filter((c) => c.key !== key);
    }

    // Enter on an empty charge picker of the last, blank charge: drop it and advance to Save.
    function onChargeEmptyEnter(charge: ChargeRow) {
        const isLast = charges[charges.length - 1]?.key === charge.key;
        if (isLast && charge.ledgerId == null) {
            if (charges.length > 1) removeCharge(charge.key);
            else charges = [];   // collapse the lone default row so flow reaches Save
        }
        setTimeout(() => document.querySelector<HTMLElement>('[data-flow="save"]')?.focus(), 0);
    }


    function focusCharges() {
        if (charges.length === 0) addCharge();
        else setTimeout(() => document.querySelector<HTMLElement>('[data-flow="charge"]')?.focus(), 0);
    }


    function focusParty() {
        setTimeout(() => partyLookup?.focus(), 0);
    }

    function focusRowQty(key: number) {
        setTimeout(() => {
            const rows = Array.from(document.querySelectorAll<HTMLElement>(".grow"));
            const idx = lines.findIndex((l) => l.key === key);
            const el = rows[idx]?.querySelector<HTMLInputElement>('[data-flow="qty"]');
            el?.focus();
            el?.select();
        }, 0);
    }

    // Every started line must have qty; rate may be 0 but mapping must resolve.
    function isComplete(): boolean {
        if (!party || !companyId) return false;
        return lines.every((l) => !l.item || (l.mapping != null && Number(l.qty) > 0));
    }

    // ── pre-save validation (soft warnings, not hard blocks) ──────────────────
    function collectIssues(): Issue[] {
        const issues: Issue[] = [];
        const growRows = () => Array.from(document.querySelectorAll<HTMLElement>(".grow"));

        lines.forEach((l, i) => {
            const isLastLine = i === lines.length - 1;
            const isPristine = l.item === null && l.qty === "1" && Number(l.rate) === 0 && Number(l.amount) === 0;
            if (l.item === null && !(isLastLine && isPristine)) {
                issues.push({
                    code: `line-${i}-no-item`,
                    message: `Line ${i+1}: item was typed but not selected or created - this line will be skipped`,
                    severity: "block",
                    focus: () => {
                        growRows()[i]?.querySelector<HTMLElement>('[data-flow="item"]')?.focus();
                    },
                });
                return
            }
            if (!l.item) return;
            if (l.noMapping) {
                issues.push({
                    code: `line-${i}-no-mapping`,
                    message: `Line ${i + 1} (${l.item.name}): no item-company mapping — line will be skipped.`,
                    severity: "block",
                    focus: () => { growRows()[i]?.querySelector<HTMLElement>('[data-flow="item"]')?.focus(); },
                });
            }
            if (Number(l.qty) <= 0) {
                issues.push({
                    code: `line-${i}-qty-zero`,
                    message: `Line ${i + 1} (${l.item.name}): quantity is 0.`,
                    focus: () => { const el = growRows()[i]?.querySelector<HTMLInputElement>('[data-flow="qty"]'); el?.focus(); el?.select(); },
                });
            }
            if (Number(l.rate) <= 0) {
                issues.push({
                    code: `line-${i}-rate-zero`,
                    message: `Line ${i + 1} (${l.item.name}): rate is 0.`,
                    focus: () => { const el = growRows()[i]?.querySelector<HTMLInputElement>('[data-flow="rate"]'); el?.focus(); el?.select(); },
                });
            }
        });

        charges.forEach((c, i) => {
            if (c.ledgerId == null) return;
            const kind = kindOf(c);
            if (kind === "DISCOUNT" && (Number(c.value) || 0) <= 0) {
                const name = ledgerById.get(c.ledgerId)?.name ?? "Charge";
                issues.push({
                    code: `charge-${i}-value-zero`,
                    message: `${name} discount value is 0 — it will have no effect.`,
                    focus: () => {
                        const rows = Array.from(document.querySelectorAll<HTMLElement>(".chrow"));
                        rows[i]?.querySelector<HTMLInputElement>('[data-flow="charge-val"]')?.focus();
                    },
                });
            }
        });

        const amt = Number(settleAmount) || 0;
        if (amt > 0 && settleModeId == null) {
            issues.push({
                code: "settle-no-mode",
                message: "Settlement amount entered but no mode selected.",
                focus: () => document.getElementById("settle-amount")?.focus(),
            });
        }
        if (amt > 0 && finalBill > 0 && amt > finalBill) {
            issues.push({
                code: "settle-overpay",
                message: `Settlement amount (${amt.toFixed(2)}) exceeds the bill total (${finalBill.toFixed(2)}). The excess will remain as an advance on account.`,
                focus: () => { const el = document.getElementById("settle-amount") as HTMLInputElement | null; el?.focus(); el?.select(); },
            });
        }

        return issues;
    }

    // ── save flow: warning → confirm → save ───────────────────────────────────
    function attemptSave(via: "confirm" | "direct") {
        if (!canSave) return;
        const issues = collectIssues();
        if (issues.length > 0) {
            warningIssues = issues;
            warningNext = via === "confirm" ? () => { confirmOpen = true; } : () => { void save(); };
        } else if (via === "confirm") {
            confirmOpen = true;
        } else {
            void save();
        }
    }

    function closeWarning() {
        warningIssues = null;
        warningNext = null;
        focusParty();
    }

    function reviewWarning() {
        const first = warningIssues?.[0];
        warningIssues = null;
        warningNext = null;
        first?.focus();
    }

    function proceedWarning() {
        const next = warningNext;
        warningIssues = null;
        warningNext = null;
        next?.();
    }

    const flowOpts = $derived({
        onSave: (_opts: { direct: boolean }) => { attemptSave("direct"); },
        isComplete,
        onConfirm: () => { attemptSave("confirm"); },
    });

    function requestSave() {
        attemptSave("confirm");
    }

    async function confirmSave() {
        confirmOpen = false;
        await save();
    }

    function closeConfirm() {
        confirmOpen = false;
        focusParty();
    }

    function buildPayloadCharges() {
        const out: Array<Record<string, unknown>> = [];
        for (const c of charges) {
            if (c.ledgerId == null) continue;
            const kind = ledgerById.get(c.ledgerId)?.kind;
            if (kind === "DISCOUNT") {
                const v = Number(c.value) || 0;
                if (v <= 0) continue;
                out.push({ledger_id: c.ledgerId, charge_type: "DISCOUNT", mode: c.mode, input_value: v});
            } else if (kind === "ROUND_OFF") {
                out.push({ledger_id: c.ledgerId, charge_type: "ROUND_OFF"});
            }
        }
        return out;
    }

    async function save() {
        if (!party || !companyId || saving) return;
        saving = true;
        error = null;
        saved = null;
        settleNote = null;
        try {
            const payloadLines = lines.filter((l) => l.mapping && Number(l.qty) > 0)
                .map((l) => ({mapping: l.mapping, qty: Number(l.qty), rate: Number(l.rate) || 0}));
            if (payloadLines.length === 0) {
                error = "Add at least one item with a quantity.";
                return;
            }
            if (editingId != null) await request(`/api/vouchers/purchases/${editingId}/cancel/`, {method: "POST"});
            const res = await request<{ id: number; number: string; total_amount: number }>("/api/vouchers/purchases/", {
                method: "POST",
                body: JSON.stringify({
                    company: companyId, party: party.id, date, number: null,
                    lines: payloadLines, charges: buildPayloadCharges(),
                }),
            });
            saved = {number: res.number, total_amount: res.total_amount};

            // Optional inline settlement — a SEPARATE, independent write. The purchase
            // is already saved; a settlement failure never rolls it back. Targets this
            // purchase only (target_bill_id), so it won't touch the party's other bills.
            const amt = Number(settleAmount) || 0;
            if (amt > 0) {
                try {
                    await request("/api/vouchers/payments/", {
                        method: "POST",
                        body: JSON.stringify({
                            company: companyId, party: party.id, date,
                            amount: amt, mode: settleModeId, number: null,
                            target_bill_id: res.id,
                        }),
                    });
                    settleNote = `Settled ${amt.toFixed(2)} against #${res.number}${settleModeName ? ` via ${settleModeName}` : ""}.`;
                } catch (se) {
                    settleNote = `Purchase #${res.number} saved, but the settlement did not post${se instanceof Error ? `: ${se.message}` : ""}. You can settle it later from the Settle page.`;
                }
            }

            editingId = null;
            lines = [newLine()];
            charges = [];
            settleAmount = "0";
            await loadHistory();
            focusParty();
        } catch (e) {
            error = e instanceof Error ? e.message : "Could not save purchase.";
        } finally {
            saving = false;
        }
    }

    // Register title, quick actions, history panel, and shortcuts with the shell.
    registerScreen(() => ({
        title: "Purchase",
        actions: [
            {id: "pur-new", label: "New", icon: "＋", shortcut: "Ctrl+N", run: resetForm},
            {id: "pur-add", label: "Add line", icon: "▸", shortcut: "Alt+A", run: addLine},
            {id: "pur-charge", label: "Add charge", icon: "%", shortcut: "Alt+I", run: addCharge},
            {id: "pur-save", label: "Save", icon: "✓", shortcut: "Ctrl+Enter", run: requestSave},
        ],
        shortcuts: [
            {id: "pur-k-new", keychord: "ctrl+n", label: "New", run: resetForm},
            {id: "pur-k-add", keychord: "alt+a", label: "Add line", run: addLine},
            {id: "pur-k-charge", keychord: "alt+i", label: "Add charge", run: addCharge},
            {id: "pur-k-focus-charge", keychord: "alt+g", label: "Focus charges", run: focusCharges},
        ],
        panel: [{id: "history", title: "History", body: historyPanel}],
    }));
</script>

{#snippet historyPanel()}
    <div class="sidehead">
        <span class="muted">Recent purchases</span>
        <button class="refresh" onclick={loadHistory} disabled={loadingHistory}>{loadingHistory ? "…" : "↻"}</button>
    </div>
    {#if history.length === 0}
        <p class="muted">{loadingHistory ? "Loading…" : "No purchases yet."}</p>
    {:else}
        <ul class="hlist">
            {#each history as h (h.id)}
                <li class:cancelled={h.is_cancelled} class:active={h.id === editingId}>
                    <button class="hrow" disabled={h.is_cancelled} onclick={() => openForEdit(h)}>
                        <div class="hline1"><span>#{h.number}</span><span
                                class="htot">{Number(h.total_amount).toFixed(2)}</span></div>
                        <div class="hline2"><span>{h.party_name}</span><span>{h.date}</span></div>
                        {#if h.is_cancelled}<span class="badge">cancelled</span>{/if}
                    </button>
                </li>
            {/each}
        </ul>
    {/if}
{/snippet}

<div class="wrap" use:enterFlow={flowOpts}>
    {#if editingId != null}
        <div class="banner edit">Editing — saving will <strong>cancel the original</strong> and replace it.
            <button class="linkbtn" onclick={resetForm}>Discard</button>
        </div>
    {/if}
    {#if saved}
        <div class="banner ok">Saved purchase <strong>#{saved.number}</strong> · total
            <strong>{saved.total_amount}</strong>.
        </div>
    {/if}
    {#if error}
        <div class="banner err">{error}</div>
    {/if}

    <section class="head">
        <div class="field">
            <label for="party">Party</label>
            <SmartLookup bind:this={partyLookup} flow="party" oncreate={onPartyCreate} onselect={onPartySelect}
                         placeholder="Search or create party…"
                         type="PARTY" value={party}/>
        </div>
        <div class="field date">
            <label for="date">Date</label>
            <input bind:value={date} data-flow="date" id="date" type="date"/>
        </div>
    </section>

    <section class="grid">
        <div class="ghead"><span>Item</span><span>Qty</span><span>Rate</span><span>Amount</span><span></span></div>
        {#each lines as line (line.key)}
            <div class="grow">
                <div class="cell item">
                    <SmartLookup type="ITEM" flow="item"
                                 placeholder="Search or create item ..."
                                 value={line.item}
                                 exclude={excludeItems(line.key)}
                                 onselect={(s) => onItemSelect(line, s)}
                                 oncreate={(t) => onItemCreate(line, t)}
                                 onemptyenter={() => onLineEmptyEnter(line)}
                    />
                    {#if line.resolving}<span class="hint">Resolving mapping…</span>
                    {:else if line.noMapping}
                        <span class="hint warn">{line.note}
                            <button class="linkbtn" disabled={line.creatingMapping} onclick={() => createMapping(line)}>
                                {line.creatingMapping ? "Creating…" : "Create mapping"}</button></span>
                    {:else if line.note}<span class="hint warn">{line.note}</span>{/if}
                </div>
                <div class="qtycell">
                    <input class="num" type="number" min="0" step="0.001" data-flow="qty"
                           bind:value={line.qty} oninput={() => onQtyOrRate(line)}/>
                    {#if line.item?.base_unit}<span class="unit">{line.item.base_unit}</span>{/if}
                </div>
                <input class="num" type="number" min="0" step="0.01" data-flow="rate"
                       bind:value={line.rate} oninput={() => onQtyOrRate(line)}/>
                <input class="num" type="number" min="0" step="0.01" data-flow="amount"
                       bind:value={line.amount} oninput={() => onAmount(line)} onkeydown={(e) => onLineEnter(e, line)}/>
                <button class="del" title="Remove line" onclick={() => removeLine(line.key)}>✕</button>
            </div>
        {/each}
        <button class="addline" onclick={addLine}>+ Add line <kbd>Alt A</kbd></button>
    </section>

    <section class="charges">
        <div class="chhead"><span>Charges</span></div>
        {#each charges as c (c.key)}
            {@const kind = kindOf(c)}
            <div class="chrow">
                <LedgerLookup flow="charge"
                              options={optionsFor(c)}
                              value={c.ledgerId}
                              onselect={(id) => (c.ledgerId = id)}
                              onenter={() => onChargePicked(c)}
                              onemptyenter={() => onChargeEmptyEnter(c)}
                />


                {#if kind === "DISCOUNT"}
                    <div class="chmode">
                        <button type="button" class:active={c.mode === "PERCENT"}
                                onclick={() => (c.mode = "PERCENT")}>%
                        </button>
                        <button type="button" class:active={c.mode === "AMOUNT"}
                                onclick={() => (c.mode = "AMOUNT")}>₹
                        </button>
                    </div>
                    <input class="num" type="number" min="0" step="0.01" data-flow="charge-val"
                           bind:value={c.value}
                           placeholder={c.mode === "PERCENT" ? "0 %" : "0.00"}
                           onkeydown={(e) => onChargeEnter(e, c)}
                    />
                {:else if kind === "ROUND_OFF"}
                    <span class="chspan">auto</span>
                    <span class="chhint">server computes the delta</span>
                {:else}
                    <span class="chspan"></span><span></span>
                {/if}

                <button class="del" title="Remove charge" onclick={() => removeCharge(c.key)}>✕</button>
            </div>
        {/each}
        <button class="addline" disabled={chargeLedgers.length === 0}
                onclick={addCharge}>+ Add charge <kbd>Alt I</kbd></button>
    </section>

    <section class="totals">
        <div class="trow"><span>Line-item total</span><span>{total.toFixed(2)}</span></div>
        {#if discountPreview > 0}
            <div class="trow discount"><span>Discount</span><span>− {discountPreview.toFixed(2)}</span></div>
        {/if}
        {#if hasRoundOff && roundDelta !== 0}
            <div class="trow round"><span>Round off</span>
                <span>{roundDelta >= 0 ? "+" : "−"} {Math.abs(roundDelta).toFixed(2)}</span></div>
        {/if}
        <div class="trow final"><span>Final bill</span><strong>{finalBill.toFixed(2)}</strong></div>
    </section>

    <footer class="foot">
        <button class="save" data-flow="save" disabled={!canSave} onclick={requestSave} type="button">
            {saving ? "Saving…" : (editingId != null ? "Save changes" : "Save purchase")} <kbd>Ctrl ⏎</kbd>
        </button>
    </footer>

    <section class="settle-inline">
        <div class="chhead"><span>Settlement (optional)</span></div>
        <div class="settle-row">
            <div class="field amt">
                <label for="settle-amount">Amount</label>
                <input id="settle-amount" class="num" type="number" min="0" step="0.01"
                       bind:value={settleAmount} placeholder="0.00"/>
            </div>
            <div class="field mode">
                <label for="settle-mode">Mode</label>
                <LedgerLookup options={modeOptions} bind:value={settleModeId}
                              placeholder="Settlement mode…" onselect={(id) => (settleModeId = id)}/>
            </div>
        </div>
        <p class="settle-hint">Leave amount at 0 to save the purchase without settling. Any amount here settles this purchase only.</p>
        {#if settleNote}<div class="settle-note">{settleNote}</div>{/if}
    </section>
</div>


{#if partyDialog !== null}
    <PartyCreateDialog initialName={partyDialog} oncreated={onPartyCreated} oncancel={() => (partyDialog = null)}/>
{/if}
{#if itemDialog !== null && companyId}
    <ItemCreateDialog initialName={itemDialog.text} companyId={companyId} oncreated={onItemCreated}
                      oncancel={() => (itemDialog = null)}/>
{/if}
{#if warningIssues}
    <WarningDialog issues={warningIssues}
                   onreview={reviewWarning}
                   onproceed={proceedWarning}
                   oncancel={closeWarning}/>
{/if}
{#if confirmOpen}
    <ConfirmDialog
            title={editingId != null ? "Replace this purchase?" : "Confirm purchase"}
            message={`Party: ${party?.name ?? "—"} · Final bill ${finalBill.toFixed(2)}. ${editingId != null ? "The original will be cancelled and replaced." : "Post this voucher?"}${Number(settleAmount) > 0 ? ` Then settle ${Number(settleAmount).toFixed(2)}${settleModeName ? ` via ${settleModeName}` : ""} against it.` : ""}`}
            confirmLabel={editingId != null ? "Replace" : "Post purchase"}
            busy={saving}
            onconfirm={confirmSave}
            oncancel={closeConfirm}/>
{/if}

<style>
    .wrap {
        padding: 20px 28px 40px;
        box-sizing: border-box;
    }

    .banner {
        padding: 10px 14px;
        border-radius: var(--radius);
        margin-bottom: 16px;
        font-size: 14px;
    }

    .banner.ok {
        background: var(--ok-soft);
        color: var(--ok);
        border: 1px solid var(--ok-border);
    }

    .banner.err {
        background: var(--danger-soft);
        color: #ff9b9b;
        border: 1px solid var(--danger-border);
    }

    .banner.edit {
        background: #1d2233;
        color: #b9c6ff;
        border: 1px solid #34406b;
        display: flex;
        gap: 10px;
        align-items: center;
    }

    .head {
        display: flex;
        gap: 18px;
        margin-bottom: 22px;
        max-width: 640px;
    }

    .field {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .field.date {
        max-width: 180px;
    }

    label {
        font-size: 12px;
        color: var(--text-muted);
    }

    input[type="date"] {
        padding: 8px 10px;
        border-radius: var(--radius);
        border: 1px solid var(--border-hi);
        background: var(--bg-app);
        color: var(--text);
        font-size: 14px;
    }

    .grid {
        border: 1px solid var(--border);
        border-radius: 10px;
        background: var(--bg-panel);
    }

    .ghead, .grow {
        display: grid;
        grid-template-columns: 1fr 130px 110px 120px 40px;
        gap: 12px;
        align-items: start;
        padding: 12px 14px;
    }

    .ghead {
        color: var(--text-muted);
        font-size: 12px;
        border-bottom: 1px solid var(--border);
    }

    .grow {
        border-bottom: 1px solid #171b23;
    }

    .cell.item {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }

    .hint {
        font-size: 11px;
        color: var(--text-muted);
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
        align-items: center;
    }

    .hint.warn {
        color: var(--warn);
    }

    .linkbtn {
        background: transparent;
        border: 1px solid var(--accent);
        color: var(--accent-text);
        padding: 2px 8px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 11px;
    }

    .qtycell {
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .qtycell .num {
        flex: 1;
    }

    .unit {
        font-size: 12px;
        color: var(--text-muted);
    }

    .num {
        padding: 8px 10px;
        border-radius: var(--radius);
        border: 1px solid var(--border-hi);
        background: var(--bg-app);
        color: var(--text);
        font-size: 14px;
        text-align: right;
        box-sizing: border-box;
        width: 100%;
    }

    .del {
        align-self: center;
        background: transparent;
        border: none;
        color: #6b7280;
        cursor: pointer;
    }

    .del:hover {
        color: var(--danger);
    }

    .addline {
        width: 100%;
        padding: 10px;
        background: transparent;
        border: none;
        color: var(--accent-text);
        cursor: pointer;
        font-size: 14px;
        text-align: left;
    }

    .addline:hover {
        background: var(--accent-soft);
    }

    .addline:disabled {
        opacity: .5;
        cursor: default;
    }

    /* ── charges section ── */
    .charges {
        margin-top: 14px;
        border: 1px solid var(--border);
        border-radius: 10px;
        background: var(--bg-elevated);
        padding: 8px 14px 6px;
        display: flex;
        flex-direction: column;
        gap: 8px;
        max-width: 560px;
        margin-left: auto;
    }

    .chhead {
        color: var(--text-muted);
        font-size: 12px;
        padding: 4px 0 2px;
    }

    .chrow {
        display: grid;
        grid-template-columns: 1fr auto 130px 32px;
        gap: 10px;
        align-items: center;
    }

    .chsel {
        padding: 8px 10px;
        border-radius: var(--radius);
        border: 1px solid var(--border-hi);
        background: var(--bg-app);
        color: var(--text);
        font-size: 13px;
    }

    .chmode {
        display: inline-flex;
        border: 1px solid var(--border-hi);
        border-radius: 6px;
        overflow: hidden;
    }

    .chmode button {
        background: transparent;
        border: none;
        color: var(--text-muted);
        padding: 6px 10px;
        cursor: pointer;
        font-size: 13px;
    }

    .chmode button.active {
        background: var(--accent);
        color: #fff;
    }

    .chspan {
        font-size: 13px;
        color: var(--text-muted);
        text-align: right;
    }

    .chhint {
        font-size: 11px;
        color: var(--text-muted);
    }

    /* ── totals breakdown ── */
    .totals {
        margin-top: 14px;
        max-width: 560px;
        margin-left: auto;
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .trow {
        display: flex;
        justify-content: space-between;
        font-size: 14px;
        color: var(--text);
        padding: 2px 2px;
    }

    .trow.discount {
        color: var(--danger);
    }

    .trow.round {
        color: var(--warn);
    }

    .trow.final {
        border-top: 1px solid var(--border-hi);
        padding-top: 8px;
        margin-top: 4px;
        font-size: 16px;
    }

    .trow.final strong {
        color: var(--ok);
    }

    .foot {
        display: flex;
        justify-content: flex-end;
        gap: 24px;
        align-items: center;
        margin-top: 20px;
    }

    .save {
        padding: 10px 20px;
        border-radius: var(--radius);
        border: 1px solid var(--accent);
        background: var(--accent);
        color: #fff;
        font-size: 14px;
        cursor: pointer;
    }

    .save:disabled {
        opacity: .5;
        cursor: default;
    }

    kbd {
        background: rgba(0, 0, 0, .25);
        border: 1px solid var(--border-hi);
        border-radius: 4px;
        padding: 0 4px;
        font-size: 11px;
        margin-left: 6px;
    }

    /* history panel (rendered inside shell ContextPanel) */
    .sidehead {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }

    .muted {
        color: var(--text-muted);
        font-size: 13px;
    }

    .refresh {
        background: transparent;
        border: 1px solid var(--border-hi);
        color: var(--text-muted);
        width: 28px;
        height: 28px;
        border-radius: 6px;
        cursor: pointer;
    }

    .hlist {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .hrow {
        position: relative;
        width: 100%;
        text-align: left;
        background: var(--bg-app);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 8px 10px;
        cursor: pointer;
        color: var(--text);
    }

    .hrow:disabled {
        cursor: default;
    }

    li.active .hrow {
        border-color: var(--accent);
    }

    li.cancelled .hrow {
        opacity: .55;
    }

    .hline1 {
        display: flex;
        justify-content: space-between;
        font-size: 13px;
        font-weight: 600;
    }

    .htot {
        color: var(--ok);
    }

    .hline2 {
        display: flex;
        justify-content: space-between;
        font-size: 11px;
        color: var(--text-muted);
        margin-top: 2px;
    }

    .badge {
        position: absolute;
        top: 6px;
        right: 8px;
        font-size: 9px;
        text-transform: uppercase;
        color: #ff9b9b;
        background: var(--danger-soft);
        padding: 1px 5px;
        border-radius: 4px;
    }
    /* ── optional inline settlement (matches the charges section) ── */
    .settle-inline {
        margin-top: 14px;
        border: 1px solid var(--border);
        border-radius: 10px;
        background: var(--bg-elevated);
        padding: 8px 14px 12px;
        display: flex;
        flex-direction: column;
        gap: 8px;
        max-width: 560px;
        margin-left: auto;
    }

    .settle-row {
        display: flex;
        gap: 14px;
        align-items: flex-end;
    }

    .settle-row .field {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .settle-row .field.amt {
        max-width: 180px;
    }

    .settle-hint {
        margin: 0;
        font-size: 11px;
        color: var(--text-muted);
    }

    .settle-note {
        font-size: 12px;
        color: #b9c6ff;
        background: #1d2233;
        border: 1px solid #34406b;
        border-radius: var(--radius);
        padding: 6px 10px;
    }
</style>