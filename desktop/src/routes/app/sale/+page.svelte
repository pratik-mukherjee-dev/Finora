<script lang="ts">
    import { enterFlow } from "$lib/flow";
    import {auth} from "$lib/stores/auth.svelte";
    import {goto} from "$app/navigation";
    import {onMount} from "svelte";
    import {request, type Suggestion} from "$lib/api";
    import SmartLookup from "$lib/components/SmartLookup.svelte";
    import PartyCreateDialog from "$lib/components/PartyCreateDialog.svelte";
    import ItemCreateDialog from "$lib/components/ItemCreateDialog.svelte";
    import ConfirmDialog from "$lib/components/ConfirmDialog.svelte";
    import {registerScreen} from "$lib/shell/useScreen.svelte";

    onMount(() => {
        if (!auth.isAuthed) return void goto("/login");
        if (auth.needsSetup) return void goto("/setup");
        if (auth.needsFy) return void goto("/fy");
        void loadHistory();
        void loadLedgers();
        focusParty();
    });

    type Mapping = { id: number; item: number; item_name: string; company: number; rate: number; stock: number; };
    // A charge ledger straight from /api/ledgers/. `name` and `kind` drive the UI.
    type Ledger = {
        id: number; company: number | null; name: string;
        kind: "DISCOUNT" | "ROUND_OFF" | "TAX" | "OTHER"; is_system: boolean; gst_rate: number | null;
    };
    // Read-back charge row from a saved voucher.
    type SavedCharge = {
        id: number; ledger: number; ledger_name: string; charge_type: string;
        mode: string; input_value: number; amount: number; sort_order: number;
    };
    // A charge row being edited in the form. Its label/kind come from the picked ledger.
    type ChargeRow = {
        key: number; ledgerId: number | null; mode: "PERCENT" | "AMOUNT"; value: string;
    };
    type Line = {
        key: number; item: Suggestion | null; company: number | null;
        qty: string; rate: string; amount: string; resolving: boolean; note: string;
    };
    type SaleLine = {
        id: number; item: number; item_name: string; mapping: number;
        company_resolved: number; company_name: string; derived: number | null;
        qty: number; rate: number; amount: number;
    };
    type Derived = {
        id: number; company: number; number: string; date: string;
        total_amount: number; master: number; is_cancelled: boolean; lines: SaleLine[];
    };
    type Sale = {
        id: number; company: number; party: number; party_name: string;
        number: string; date: string; segregate: boolean; total_amount: number;
        is_cancelled: boolean; lines: SaleLine[]; derived: Derived[]; charges: SavedCharge[];
    };

    let seq = 0;
    let chargeSeq = 0;
    const newLine = (): Line => ({
        key: ++seq, item: null, company: null, qty: "1", rate: "0", amount: "0.00", resolving: false, note: "",
    });
    const newCharge = (ledgerId: number | null = null): ChargeRow => ({
        key: ++chargeSeq, ledgerId, mode: "PERCENT", value: "0",
    });

    const today = new Date().toISOString().slice(0, 10);
    let party = $state<Suggestion | null>(null);
    let date = $state(today);
    let segregate = $state(false);
    let lines = $state<Line[]>([newLine()]);
    let saving = $state(false);
    let error = $state<string | null>(null);
    let saved = $state<Sale | null>(null);
    let history = $state<Sale[]>([]);
    let loadingHistory = $state(false);
    let editingId = $state<number | null>(null);
    let partyDialog = $state<string | null>(null);
    let itemDialog = $state<{ text: string; lineKey: number } | null>(null);

    // ── charges: ledger catalogue + dynamic charge rows ───────────────────────
    let ledgers = $state<Ledger[]>([]);
    let charges = $state<ChargeRow[]>([]);
    let lastLedgerCompany = $state<number | null>(null);

    // ── enter-flow / confirm state ────────────────────────────────────────────
    let confirmOpen = $state(false);
    let partyLookup = $state<{ focus: () => void } | null>(null);

    const companyId = $derived(auth.currentCompany?.id ?? null);
    const isMulti = $derived(auth.mode === "multi");
    const total = $derived(lines.reduce((s, l) => s + (Number(l.amount) || 0), 0));
    const canSave = $derived(!!party && !!companyId && lines.some((l) => l.item && Number(l.qty) > 0) && !saving);
    const round2 = (n: number) => (Math.round(n * 100) / 100).toFixed(2);

    // Charge ledgers we render in v1: discount + round-off only (TAX/OTHER = v2).
    const chargeLedgers = $derived(ledgers.filter((l) => l.kind === "DISCOUNT" || l.kind === "ROUND_OFF"));
    const ledgerById = $derived(new Map(ledgers.map((l) => [l.id, l])));

    function kindOf(row: ChargeRow): Ledger["kind"] | null {
        return row.ledgerId != null ? (ledgerById.get(row.ledgerId)?.kind ?? null) : null;
    }

    // ── client-side PREVIEW only (server signs & rounds authoritatively) ───────
    // Discounts first (on subtotal), then a single round-off delta on the result.
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

    // Re-fetch ledgers when the active company changes (scoped shared + own).
    $effect(() => {
        if (companyId != null && companyId !== lastLedgerCompany) void loadLedgers();
    });

    async function loadHistory() {
        if (!companyId) return;
        loadingHistory = true;
        try {
            const p = new URLSearchParams({company: String(companyId)});
            const rows = await request<Sale[] | { results?: Sale[] }>(`/api/vouchers/sales/?${p.toString()}`);
            history = Array.isArray(rows) ? rows : (rows?.results ?? []);
        } catch {
            history = [];
        } finally {
            loadingHistory = false;
        }
    }

    async function openForEdit(row: Sale) {
        if (row.is_cancelled) return;
        error = null;
        saved = null;
        editingId = row.id;
        party = {id: row.party, name: row.party_name};
        date = row.date;
        segregate = row.segregate;
        lines = row.lines.map((sl) => ({
            key: ++seq, item: {id: sl.item, name: sl.item_name}, company: sl.company_resolved,
            qty: String(sl.qty), rate: String(sl.rate), amount: round2(Number(sl.qty) * Number(sl.rate)),
            resolving: false, note: "",
        }));
        if (lines.length === 0) lines = [newLine()];
        hydrateCharges(row.charges ?? []);
    }

    // Rebuild editable charge rows from saved charges, keyed on the ledger id.
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
        segregate = false;
        lines = [newLine()];
        charges = [];
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

    async function resolveRate(line: Line, itemId: number) {
        const rc = line.company ?? companyId;
        if (!rc) return;
        line.resolving = true;
        line.note = "";
        try {
            const params = new URLSearchParams({item: String(itemId), company: String(rc)});
            const rows = await request<Mapping[]>(`/api/catalogue/mappings/?${params.toString()}`);
            const list = Array.isArray(rows) ? rows : ((rows as { results?: Mapping[] })?.results ?? []);
            if (list.length > 0) {
                line.rate = String(list[0].rate ?? line.rate ?? 0);
                onQtyOrRate(line);
            } else {
                line.note = "No mapping yet — server uses the default company.";
            }
        } catch (e) {
            line.note = e instanceof Error ? e.message : "Failed to resolve rate.";
        } finally {
            line.resolving = false;
        }
    }

    function onItemSelect(line: Line, s: Suggestion) {
        line.item = s;
        void resolveRate(line, s.id);
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
            void resolveRate(target, i.id);
            if (key != null) focusRowQty(key);
        }
    }

    function addLine() {
        lines = [...lines, newLine()];
    }

    function removeLine(key: number) {
        lines = lines.length > 1 ? lines.filter((l) => l.key !== key) : lines;
    }

    // ── charge row management ─────────────────────────────────────────────────
    function addCharge() {
        // Default the picker to the first unused charge ledger, if any.
        const used = new Set(charges.map((c) => c.ledgerId));
        const first = chargeLedgers.find((l) => !used.has(l.id)) ?? chargeLedgers[0] ?? null;
        charges = [...charges, newCharge(first?.id ?? null)];
        setTimeout(() => {
            const rows = document.querySelectorAll<HTMLElement>('[data-flow="charge"]');
            rows[rows.length - 1]?.focus();
        }, 0);
    }

    function removeCharge(key: number) {
        charges = charges.filter((c) => c.key !== key);
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

    function isComplete(): boolean {
        if (!party || !companyId) return false;
        return lines.every((l) => !l.item || Number(l.qty) > 0);
    }

    const flowOpts = $derived({
        onSave: () => { void save(); },
        isComplete,
        onConfirm: () => { if (canSave) confirmOpen = true; },
    });

    // ── save via confirmation ─────────────────────────────────────────────────
    function requestSave() {
        if (!canSave) return;
        confirmOpen = true;
    }

    async function confirmSave() {
        confirmOpen = false;
        await save();
    }

    // Build the backend charge payload from the dynamic rows, driven by ledger kind.
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
            // TAX / OTHER: v2 — skipped in v1.
        }
        return out;
    }

    async function save() {
        if (!party || !companyId || saving) return;
        saving = true;
        error = null;
        saved = null;
        try {
            const payloadLines = lines.filter((l) => l.item && Number(l.qty) > 0).map((l) => {
                const row: { item: number; qty: number; rate: number; company?: number } = {
                    item: l.item!.id, qty: Number(l.qty), rate: Number(l.rate) || 0,
                };
                if (isMulti && l.company) row.company = l.company;
                return row;
            });
            if (payloadLines.length === 0) {
                error = "Add at least one item with a quantity.";
                return;
            }
            if (editingId != null) await request(`/api/vouchers/sales/${editingId}/cancel/`, {method: "POST"});
            const res = await request<Sale>("/api/vouchers/sales/", {
                method: "POST",
                body: JSON.stringify({
                    company: companyId, party: party.id, date, number: null,
                    segregate: isMulti ? segregate : false, lines: payloadLines,
                    charges: buildPayloadCharges(),
                }),
            });
            saved = res;
            editingId = null;
            party = null;
            segregate = false;
            lines = [newLine()];
            charges = [];
            await loadHistory();
            focusParty();
        } catch (e) {
            error = e instanceof Error ? e.message : "Could not save sale.";
        } finally {
            saving = false;
        }
    }

    function viewDerived(row: Sale) {
        saved = row;
        shell.activeTab = "derived";
    }

    const shell = registerScreen(() => ({
        title: "Sale",
        actions: [
            {id: "sal-new", label: "New", icon: "＋", shortcut: "Ctrl+N", run: resetForm},
            {id: "sal-add", label: "Add line", icon: "▸", shortcut: "Alt+A", run: addLine},
            {id: "sal-charge", label: "Add charge", icon: "%", shortcut: "Alt+I", run: addCharge},
            {id: "sal-save", label: "Save", icon: "✓", shortcut: "Ctrl+Enter", run: requestSave},
        ],
        shortcuts: [
            {id: "sal-k-new", keychord: "ctrl+n", label: "New", run: resetForm},
            {id: "sal-k-add", keychord: "alt+a", label: "Add line", run: addLine},
            {id: "sal-k-charge", keychord: "alt+i", label: "Add charge", run: addCharge},
            {id: "sal-k-focus-charge", keychord: "alt+g", label: "Focus charges", run: focusCharges},
        ],
        panel: [
            {id: "history", title: "History", body: historyPanel},
            {id: "derived", title: "Derived", body: derivedPanel},
        ],
    }));
</script>

{#snippet historyPanel()}
    <div class="sidehead">
        <span class="muted">Recent sales</span>
        <button class="refresh" onclick={loadHistory} disabled={loadingHistory}>{loadingHistory ? "…" : "↻"}</button>
    </div>
    {#if history.length === 0}
        <p class="muted">{loadingHistory ? "Loading…" : "No sales yet."}</p>
    {:else}
        <ul class="hlist">
            {#each history as h (h.id)}
                <li class:cancelled={h.is_cancelled} class:active={h.id === editingId}>
                    <div class="hrow">
                        <button class="hmain" disabled={h.is_cancelled} onclick={() => openForEdit(h)}>
                            <div class="hline1"><span>#{h.number}</span><span class="htot">{Number(h.total_amount).toFixed(2)}</span></div>
                            <div class="hline2"><span>{h.party_name}</span><span>{h.date}</span></div>
                        </button>
                        <button class="viewbtn" title="View derived" onclick={() => viewDerived(h)}>▣</button>
                        {#if h.is_cancelled}<span class="badge">cancelled</span>{/if}
                    </div>
                </li>
            {/each}
        </ul>
    {/if}
{/snippet}

{#snippet derivedPanel()}
    {#if !saved}
        <p class="muted">Save a sale or pick one from History to see its company-sales.</p>
    {:else}
        <div class="sidehead"><span class="muted">Master #{saved.number} · {Number(saved.total_amount).toFixed(2)}</span></div>
        {#if saved.derived.length === 0}
            <p class="muted">No derived sales.</p>
        {:else}
            {#each saved.derived as d (d.id)}
                <div class="derived">
                    <div class="dhead"><span>#{d.number}</span><span class="dtot">{Number(d.total_amount).toFixed(2)}</span></div>
                    <div class="dlines">
                        {#each d.lines as dl (dl.id)}
                            <div class="dline"><span>{dl.item_name}</span>
                                <span class="rt">{Number(dl.qty)}×{Number(dl.rate).toFixed(2)}</span>
                                <span class="rt">{Number(dl.amount).toFixed(2)}</span></div>
                        {/each}
                    </div>
                </div>
            {/each}
        {/if}
    {/if}
{/snippet}

<div class="wrap" use:enterFlow={flowOpts}>
    {#if editingId != null}
        <div class="banner edit">Editing — saving will <strong>cancel the original</strong> and replace it.
            <button class="linkbtn" onclick={resetForm}>Discard</button>
        </div>
    {/if}
    {#if saved}
        <div class="banner ok">Saved sale <strong>#{saved.number}</strong> · total
            <strong>{Number(saved.total_amount).toFixed(2)}</strong>. See <strong>Derived</strong> panel.
        </div>
    {/if}
    {#if error}
        <div class="banner err">{error}</div>
    {/if}

    <section class="head">
        <div class="field">
            <label for="party">Party</label>
            <SmartLookup type="PARTY" flow="party" placeholder="Search or create party…" value={party}
                         bind:this={partyLookup}
                         onselect={onPartySelect} oncreate={onPartyCreate}/>
        </div>
        <div class="field date">
            <label for="date">Date</label>
            <input id="date" type="date" data-flow="date" bind:value={date}/>
        </div>
        {#if isMulti}
            <label class="seg"><input type="checkbox" bind:checked={segregate}/> Segregate</label>
        {/if}
    </section>

    <section class="grid">
        <div class="ghead"><span>Item</span><span>Qty</span><span>Rate</span><span>Amount</span><span></span></div>
        {#each lines as line (line.key)}
            <div class="grow">
                <div class="cell item">
                    <SmartLookup type="ITEM" flow="item" placeholder="Search or create item…" value={line.item}
                                 onselect={(s) => onItemSelect(line, s)} oncreate={(t) => onItemCreate(line, t)}/>
                    {#if line.resolving}<span class="hint">Resolving rate…</span>
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
                       bind:value={line.amount} oninput={() => onAmount(line)}/>
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
                <select class="chsel" data-flow="charge" bind:value={c.ledgerId}>
                    <option value={null} disabled>Select charge…</option>
                    {#each chargeLedgers as l (l.id)}
                        <option value={l.id}>{l.name}</option>
                    {/each}
                </select>

                {#if kind === "DISCOUNT"}
                    <div class="chmode">
                        <button type="button" class:active={c.mode === "PERCENT"}
                                onclick={() => (c.mode = "PERCENT")}>%</button>
                        <button type="button" class:active={c.mode === "AMOUNT"}
                                onclick={() => (c.mode = "AMOUNT")}>₹</button>
                    </div>
                    <input class="num" type="number" min="0" step="0.01" data-flow="charge-val"
                           bind:value={c.value}
                           placeholder={c.mode === "PERCENT" ? "0 %" : "0.00"}/>
                {:else if kind === "ROUND_OFF"}
                    <span class="chspan">auto</span>
                    <span class="chhint">server computes the delta</span>
                {:else}
                    <span class="chspan"></span><span></span>
                {/if}

                <button class="del" title="Remove charge" onclick={() => removeCharge(c.key)}>✕</button>
            </div>
        {/each}
        <button class="addline" onclick={addCharge}
                disabled={chargeLedgers.length === 0}>+ Add charge <kbd>Alt I</kbd></button>
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
        <button class="save" data-flow="save" disabled={!canSave} onclick={requestSave}>
            {saving ? "Saving…" : (editingId != null ? "Save changes" : "Save sale")} <kbd>Ctrl ⏎</kbd>
        </button>
    </footer>
</div>


{#if partyDialog !== null}
    <PartyCreateDialog initialName={partyDialog} oncreated={onPartyCreated} oncancel={() => (partyDialog = null)}/>{/if}
{#if itemDialog !== null && companyId}
    <ItemCreateDialog initialName={itemDialog.text} companyId={companyId} oncreated={onItemCreated}
                      oncancel={() => (itemDialog = null)}/>{/if}
{#if confirmOpen}
    <ConfirmDialog
        title={editingId != null ? "Replace this sale?" : "Confirm sale"}
        message={`Party: ${party?.name ?? "—"} · Final bill ${finalBill.toFixed(2)}. ${editingId != null ? "The original will be cancelled and replaced." : "Post this voucher?"}`}
        confirmLabel={editingId != null ? "Replace" : "Post sale"}
        busy={saving}
        onconfirm={confirmSave}
        oncancel={() => (confirmOpen = false)}/>{/if}

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
        align-items: flex-end;
        margin-bottom: 22px;
        max-width: 720px;
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

    .seg {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: var(--text);
        padding-bottom: 8px;
        white-space: nowrap;
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
        display: flex;
        gap: 6px;
        background: var(--bg-app);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 4px;
    }

    li.active .hrow {
        border-color: var(--accent);
    }

    li.cancelled .hrow {
        opacity: .55;
    }

    .hmain {
        flex: 1;
        text-align: left;
        background: transparent;
        border: none;
        cursor: pointer;
        color: var(--text);
        padding: 4px 6px;
    }

    .hmain:disabled {
        cursor: default;
    }

    .viewbtn {
        background: transparent;
        border: 1px solid var(--border-hi);
        color: var(--text-muted);
        border-radius: 6px;
        cursor: pointer;
        width: 30px;
        flex-shrink: 0;
    }

    .viewbtn:hover {
        border-color: var(--accent-text);
        color: var(--accent-text);
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

    .derived {
        border: 1px solid var(--border);
        border-radius: var(--radius);
        margin-bottom: 10px;
        overflow: hidden;
    }

    .dhead {
        display: flex;
        justify-content: space-between;
        padding: 8px 12px;
        border-bottom: 1px solid var(--border);
        font-size: 13px;
        font-weight: 600;
    }

    .dtot {
        color: var(--ok);
    }

    .dlines {
        padding: 4px 12px 8px;
    }

    .dline {
        display: grid;
        grid-template-columns: 1fr auto auto;
        gap: 10px;
        padding: 4px 0;
        font-size: 12px;
        color: var(--text-muted);
    }

    .rt {
        text-align: right;
    }
</style>
