<script lang="ts">
    import ConfirmDialog from "$lib/components/ConfirmDialog.svelte";
    import WarningDialog from "$lib/components/WarningDialog.svelte";
    import type {Issue} from "$lib/validation";
    import {enterFlow} from "$lib/flow";
    import {auth} from "$lib/stores/auth.svelte";
    import {goto} from "$app/navigation";
    import {onMount} from "svelte";
    import {request, type Suggestion} from "$lib/api";
    import SmartLookup from "$lib/components/SmartLookup.svelte";
    import LedgerLookup from "$lib/components/LedgerLookup.svelte";
    import PartyCreateDialog from "$lib/components/PartyCreateDialog.svelte";
    import {registerScreen} from "$lib/shell/useScreen.svelte";

    onMount(() => {
        if (!auth.isAuthed) return void goto("/login");
        if (auth.needsSetup) return void goto("/setup");
        if (auth.needsFy) return void goto("/fy");
        void loadModes();
        void loadHistory();
        if (rows.length === 0) rows = [newRow()];
        focusParty();
    });

    type SettlementMode = {
        id: number; name: string; category: "CASH" | "BANK";
        bank_type: "UPI" | "TRANSFER" | "CHEQUE" | "OTHER" | null;
        is_system: boolean; is_active: boolean; sort_order: number;
        needs_reference: boolean;
    };
    type Allocation = {
        id: number; bill_type: string; bill_id: number; bill_number: string | null;
        bill_date: string | null; bill_total: number | null; amount: number;
    };
    type SettleResult = { id: number; number: string; amount: number; allocations: Allocation[]; };
    type Voucher = {
        id: number; party: number; party_name: string; number: string;
        date: string; amount: number; is_cancelled: boolean;
    };
    type OpenBill = {
        bill_type: string; bill_id: number; number: string;
        date: string; total: number; settled: number; open: number;
    };
    type OpenBills = { outstanding_total: number; balance: number; on_account: number; bills: OpenBill[] };

    type SettleRow = { key: number; modeId: number | null; amount: string; transactionRef: string; };

    let rowSeq = 0;
    const newRow = (): SettleRow => ({key: ++rowSeq, modeId: null, amount: "", transactionRef: ""});

    const today = new Date().toISOString().slice(0, 10);
    let party = $state<Suggestion | null>(null);
    let date = $state(today);
    let rows = $state<SettleRow[]>([newRow()]);
    let saving = $state(false);
    let error = $state<string | null>(null);
    let results = $state<SettleResult[]>([]);
    let history = $state<Voucher[]>([]);
    let loadingHistory = $state(false);
    let selectedId = $state<number | null>(null);
    let selectedResult = $state<SettleResult | null>(null);
    let preview = $state<OpenBills | null>(null);
    let loadingPreview = $state(false);
    let partyDialog = $state<string | null>(null);
    let modes = $state<SettlementMode[]>([]);
    let partyLookup = $state<{ focus: () => void } | null>(null);

    let confirmOpen = $state(false);
    let warningIssues = $state<Issue[] | null>(null);
    let warningNext = $state<(() => void) | null>(null);

    const companyId = $derived(auth.currentCompany?.id ?? null);
    const endpoint = "/api/vouchers/received/";
    const modeById = $derived(new Map(modes.map((m) => [m.id, m])));
    const modeOptions = $derived(modes.filter((m) => m.is_active).map((m) => ({id: m.id, name: m.name})));
    const totalAmount = $derived(rows.reduce((s, r) => s + (Number(r.amount) || 0), 0));
    const canSave = $derived(!!party && !!companyId && totalAmount > 0 && !saving);

    function modeOf(row: SettleRow): SettlementMode | undefined {
        return row.modeId != null ? modeById.get(row.modeId) : undefined;
    }

    function needsRef(row: SettleRow): boolean {
        return modeOf(row)?.needs_reference ?? false;
    }

    function isComplete(): boolean {
        return !!party && !!companyId && totalAmount > 0 && !!date;
    }

    function collectIssues(): Issue[] {
        const issues: Issue[] = [];
        const rowEls = () => Array.from(document.querySelectorAll<HTMLElement>(".srow"));
        rows.forEach((r, i) => {
            const amt = Number(r.amount) || 0;
            if (amt > 0 && r.modeId == null) {
                issues.push({
                    code: `row-${i}-no-mode`, message: `Row ${i + 1}: amount entered but no mode selected.`,
                    focus: () => rowEls()[i]?.querySelector<HTMLElement>('[data-flow="mode"]')?.focus()
                });
            }
            const mode = modeOf(r);
            if (amt > 0 && mode?.category === "BANK" && mode?.bank_type === "CHEQUE" && !r.transactionRef.trim()) {
                issues.push({
                    code: `row-${i}-no-cheque`, message: `Row ${i + 1} (${mode.name}): cheque number is empty.`,
                    focus: () => rowEls()[i]?.querySelector<HTMLInputElement>('[data-flow="txn-ref"]')?.focus()
                });
            }
        });
        const outstanding = Number(preview?.outstanding_total ?? 0);
        if (totalAmount > 0 && outstanding > 0 && totalAmount > outstanding) {
            issues.push({
                code: "settle-overpay",
                message: `Total (${totalAmount.toFixed(2)}) exceeds outstanding (${outstanding.toFixed(2)}). Excess stays on account.`,
                focus: () => {
                    const el = document.querySelector<HTMLInputElement>('.srow [data-flow="amount"]');
                    el?.focus();
                    el?.select();
                }
            });
        }
        return issues;
    }

    function attemptSave(via: "confirm" | "direct") {
        if (!canSave) return;
        const issues = collectIssues();
        if (issues.length > 0) {
            warningIssues = issues;
            warningNext = via === "confirm" ? () => {
                confirmOpen = true;
            } : () => {
                void save();
            };
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
        const f = warningIssues?.[0];
        warningIssues = null;
        warningNext = null;
        f?.focus();
    }

    function proceedWarning() {
        const n = warningNext;
        warningIssues = null;
        warningNext = null;
        n?.();
    }

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

    const flowOpts = $derived({
        onSave: () => {
            attemptSave("direct");
        }, isComplete, onConfirm: () => {
            attemptSave("confirm");
        }
    });

    const previewPlan = $derived.by(() => {
        if (!preview) return [];
        let remaining = totalAmount;
        return preview.bills.map((b) => {
            const take = Math.min(remaining, Number(b.open));
            remaining = Math.max(0, remaining - take);
            return {...b, willSettle: take};
        });
    });

    function addRow() {
        rows = [...rows, newRow()];
        setTimeout(() => {
            const els = document.querySelectorAll<HTMLElement>('.srow [data-flow="mode"]');
            els[els.length - 1]?.focus();
        }, 0);
    }

    function removeRow(key: number) {
        rows = rows.length > 1 ? rows.filter((r) => r.key !== key) : rows;
    }

    function onAmountEnter(e: KeyboardEvent, row: SettleRow) {
        if (e.key !== "Enter" || e.ctrlKey || e.metaKey) return;
        e.preventDefault();
        e.stopImmediatePropagation();
        const isLast = rows[rows.length - 1]?.key === row.key;
        if (!isLast) {
            const idx = rows.findIndex((r) => r.key === row.key);
            setTimeout(() => {
                document.querySelectorAll<HTMLElement>('.srow [data-flow="mode"]')[idx + 1]?.focus();
            }, 0);
            return;
        }
        if ((Number(row.amount) || 0) > 0) addRow();
        else {
            if (rows.length > 1) removeRow(row.key);
            setTimeout(() => document.querySelector<HTMLElement>('[data-flow="save"]')?.focus(), 0);
        }
    }

    function onRefEnter(e: KeyboardEvent, row: SettleRow) {
        if (e.key !== "Enter" || e.ctrlKey || e.metaKey) return;
        e.preventDefault();
        e.stopImmediatePropagation();
        const isLast = rows[rows.length - 1]?.key === row.key;
        if (!isLast) {
            const idx = rows.findIndex((r) => r.key === row.key);
            setTimeout(() => {
                document.querySelectorAll<HTMLElement>('.srow [data-flow="mode"]')[idx + 1]?.focus();
            }, 0);
        } else {
            if ((Number(row.amount) || 0) > 0) addRow(); else {
                if (rows.length > 1) removeRow(row.key);
                setTimeout(() => document.querySelector<HTMLElement>('[data-flow="save"]')?.focus(), 0);
            }
        }
    }

    function onModePicked(_row: SettleRow) { /* LedgerLookup onenter advances to amount via data-flow */
    }

    function onModeEmptyEnter(row: SettleRow) {
        const isLast = rows[rows.length - 1]?.key === row.key;
        if (isLast && rows.length > 1 && row.modeId == null && (Number(row.amount) || 0) === 0) removeRow(row.key);
        setTimeout(() => document.querySelector<HTMLElement>('[data-flow="save"]')?.focus(), 0);
    }

    function onPartySelect(s: Suggestion) {
        party = s;
        void loadHistory();
        void loadPreview();
    }

    function onPartyCreate(t: string) {
        partyDialog = t;
    }

    function onPartyCreated(p: Suggestion) {
        party = p;
        partyDialog = null;
        void loadHistory();
        void loadPreview();
    }

    function focusParty() {
        setTimeout(() => partyLookup?.focus(), 0);
    }

    async function loadModes() {
        try {
            const res = await request<SettlementMode[] | {
                results?: SettlementMode[]
            }>("/api/accounts/settlement-modes/");
            modes = Array.isArray(res) ? res : (res?.results ?? []);
        } catch {
            modes = [];
        }
    }

    async function loadHistory() {
        if (!companyId) return;
        loadingHistory = true;
        try {
            const p = new URLSearchParams({company: String(companyId)});
            if (party) p.set("party", String(party.id));
            const res = await request<Voucher[] | { results?: Voucher[] }>(`${endpoint}?${p.toString()}`);
            history = Array.isArray(res) ? res : (res?.results ?? []);
        } catch {
            history = [];
        } finally {
            loadingHistory = false;
        }
    }

    async function loadPreview() {
        if (!party) {
            preview = null;
            return;
        }
        loadingPreview = true;
        try {
            const p = new URLSearchParams({party: String(party.id)});
            preview = await request<OpenBills>(`${endpoint}open_bills/?${p.toString()}`);
            shell.activeTab = "allocation";
        } catch {
            preview = null;
        } finally {
            loadingPreview = false;
        }
    }

    async function viewVoucher(v: Voucher) {
        selectedId = v.id;
        error = null;
        try {
            const allocs = await request<Allocation[]>(`${endpoint}${v.id}/allocations/`);
            selectedResult = {id: v.id, number: v.number, amount: Number(v.amount), allocations: allocs ?? []};
            shell.activeTab = "allocation";
        } catch (e) {
            error = e instanceof Error ? e.message : "Could not load allocations.";
        }
    }

    async function save() {
        if (!party || !companyId || saving) return;
        const validRows = rows.filter((r) => r.modeId != null && (Number(r.amount) || 0) > 0);
        if (validRows.length === 0) {
            error = "Add at least one row with a mode and amount.";
            return;
        }
        saving = true;
        error = null;
        results = [];
        selectedId = null;
        selectedResult = null;
        try {
            const posted: SettleResult[] = [];
            for (const r of validRows) {
                const res = await request<SettleResult>(endpoint, {
                    method: "POST",
                    body: JSON.stringify({
                        company: companyId,
                        party: party.id,
                        date,
                        amount: Number(r.amount),
                        mode: r.modeId,
                        number: null,
                        transaction_ref: r.transactionRef.trim() || null
                    })
                });
                posted.push({
                    id: res.id,
                    number: res.number,
                    amount: Number(res.amount),
                    allocations: res.allocations ?? []
                });
            }
            results = posted;
            rows = [newRow()];
            await loadHistory();
            await loadPreview();
            shell.activeTab = "allocation";
        } catch (e) {
            error = e instanceof Error ? e.message : "Could not save.";
        } finally {
            saving = false;
        }
    }

    function resetForm() {
        party = null;
        date = today;
        rows = [newRow()];
        error = null;
        results = [];
        selectedId = null;
        selectedResult = null;
        focusParty();
    }

    const confirmMessage = $derived.by(() => {
        const validRows = rows.filter((r) => r.modeId != null && (Number(r.amount) || 0) > 0);
        const parts = validRows.map((r) => {
            const mode = modeOf(r);
            return `${Number(r.amount).toFixed(2)} via ${mode?.name ?? "?"}${r.transactionRef.trim() ? ` (${r.transactionRef.trim()})` : ""}`;
        });
        return `Party: ${party?.name ?? "—"}\n${parts.join("\n")}\nTotal: ${totalAmount.toFixed(2)}. Auto-settle oldest → latest?`;
    });

    const shell = registerScreen(() => ({
        title: "Received",
        actions: [
            {id: "rcv-new", label: "New", icon: "＋", shortcut: "Ctrl+N", run: resetForm},
            {id: "rcv-add", label: "Add row", icon: "▸", shortcut: "Alt+A", run: addRow},
            {id: "rcv-save", label: "Save", icon: "✓", shortcut: "Ctrl+Enter", run: requestSave},
        ],
        shortcuts: [
            {id: "rcv-k-new", keychord: "ctrl+n", label: "New", run: resetForm},
            {id: "rcv-k-add", keychord: "alt+a", label: "Add row", run: addRow},
        ],
        panel: [
            {id: "allocation", title: "Allocation", body: allocationPanel},
            {id: "history", title: "History", body: historyPanel},
        ],
    }));
</script>

{#snippet allocationPanel()}
    {#if results.length > 0}
        {#each results as r (r.id)}
            <div class="banner ok">#{r.number} · {r.amount.toFixed(2)}</div>
            {#if r.allocations.length > 0}
                {#each r.allocations as a (a.id)}
                    <div class="arow"><span>#{a.bill_number ?? a.bill_id}</span><span
                            class="rt">{Number(a.amount).toFixed(2)}</span></div>
                {/each}
            {:else}<p class="muted">Kept on account.</p>{/if}
        {/each}
    {:else if selectedResult}
        <div class="banner ok">#{selectedResult.number} · {selectedResult.amount.toFixed(2)}</div>
        {#if selectedResult.allocations.length === 0}<p class="muted">No open bills settled. Kept on account.</p>
        {:else}
            {#each selectedResult.allocations as a (a.id)}
                <div class="arow"><span>#{a.bill_number ?? a.bill_id}</span><span
                        class="rt">{Number(a.amount).toFixed(2)}</span></div>
            {/each}
        {/if}
    {:else if !party}<p class="muted">Pick a party to preview open sales.</p>
    {:else if loadingPreview}<p class="muted">Loading open bills…</p>
    {:else if preview}
        {@const bal = Number(preview.balance)}
        {@const outstanding = Number(preview.outstanding_total)}
        {@const onAcc = Number(preview.on_account)}
        <div class="preview-summary">
            <div class="ps-row"><span>Balance</span><strong
                    class={bal > 0 ? 'recv' : bal < 0 ? 'pay' : ''}>{Math.abs(bal).toFixed(2)} <span
                    class="bal-tag">{bal > 0 ? 'receivable' : bal < 0 ? 'payable' : 'settled'}</span></strong></div>
            {#if onAcc > 0.001}
                <div class="ps-row on-acc"><span>On account (advance)</span><strong>{onAcc.toFixed(2)}</strong></div>
            {/if}
            <div class="ps-row"><span>Open bills</span><strong>{outstanding.toFixed(2)}</strong></div>
        </div>
        {#if preview.bills.length === 0}<p class="muted">Nothing outstanding.</p>
        {:else}
            <div class="ahead"><span>Bill</span><span class="rt">Open</span><span class="rt">Will settle</span></div>
            {#each previewPlan as b (b.bill_id)}
                <div class="arow"><span>#{b.number}</span><span class="rt">{Number(b.open).toFixed(2)}</span><span
                        class="rt" class:hot={b.willSettle > 0}>{b.willSettle.toFixed(2)}</span></div>
            {/each}
        {/if}
    {/if}
{/snippet}

{#snippet historyPanel()}
    <div class="sidehead"><span class="muted">Receipts{party ? ` · ${party.name}` : ""}</span>
        <button class="refresh" onclick={loadHistory} disabled={loadingHistory}>{loadingHistory ? "…" : "↻"}</button>
    </div>
    {#if history.length === 0}<p class="muted">{loadingHistory ? "Loading…" : "No records."}</p>
    {:else}
        <ul class="hlist">
            {#each history as v (v.id)}
                <li class:cancelled={v.is_cancelled} class:active={v.id === selectedId}>
                    <button class="hrow-btn" onclick={() => viewVoucher(v)}>
                        <div class="hline1"><span>#{v.number}</span><span
                                class="htot">{Number(v.amount).toFixed(2)}</span></div>
                        <div class="hline2"><span>{v.party_name}</span><span>{v.date}</span></div>
                        {#if v.is_cancelled}<span class="badge">cancelled</span>{/if}
                    </button>
                </li>
            {/each}
        </ul>
    {/if}
{/snippet}

<div class="wrap" use:enterFlow={flowOpts}>
    {#if error}
        <div class="banner err">{error}</div>
    {/if}
    {#if results.length > 0}
        <div class="banner ok">Posted {results.length} receipt{results.length > 1 ? "s" : ""} ·
            total {results.reduce((s, r) => s + r.amount, 0).toFixed(2)}.
        </div>
    {/if}

    <section class="head">
        <div class="field"><label for="party">Party</label>
            <SmartLookup bind:this={partyLookup} flow="party" oncreate={onPartyCreate} onselect={onPartySelect}
                         placeholder="Search or create party…" type="PARTY" value={party}/>
        </div>
        <div class="field date"><label for="date">Date</label>
            <input bind:value={date} data-flow="date" id="date" type="date"/></div>
    </section>

    <section class="grid">
        <div class="ghead"><span>Mode</span><span>Amount</span><span>Category</span><span>Bank Mode</span><span>Reference</span><span></span>
        </div>
        {#each rows as row (row.key)}
            {@const mode = modeOf(row)}
            {@const isBank = mode?.category === "BANK"}
            <div class="srow">
                <div class="cell mode-cell">
                    <LedgerLookup flow="mode" options={modeOptions} value={row.modeId} placeholder="Pick mode…"
                                  onselect={(id) => (row.modeId = id)} onenter={() => onModePicked(row)}
                                  onemptyenter={() => onModeEmptyEnter(row)}/>
                </div>
                <div class="cell"><input class="num" type="number" min="0" step="0.01" data-flow="amount"
                                         bind:value={row.amount} placeholder="0.00"
                                         onkeydown={(e) => !needsRef(row) ? onAmountEnter(e, row) : undefined}/></div>
                <div class="cell cat-cell">
                    {#if mode}<span class="tag" class:bank={isBank}>{mode.category}</span>{:else}<span
                            class="tag empty">—</span>{/if}
                </div>
                <div class="cell bt-cell">
                    {#if isBank && mode?.bank_type}<span class="tag bank-type">{mode.bank_type}</span>{:else}<span
                            class="tag empty">—</span>{/if}
                </div>
                <div class="cell ref-cell">
                    {#if isBank}<input type="text" data-flow="txn-ref" bind:value={row.transactionRef}
                                       placeholder={mode?.bank_type === "CHEQUE" ? "Cheque no." : mode?.bank_type === "UPI" ? "UPI ref / UTR" : "Txn ID"}
                                       onkeydown={(e) => onRefEnter(e, row)}/>
                    {:else}<span class="tag empty">—</span>{/if}
                </div>
                <button class="del" title="Remove row" onclick={() => removeRow(row.key)}>✕</button>
            </div>
        {/each}
        <button class="addline" onclick={addRow}>+ Add row <kbd>Alt A</kbd></button>
    </section>

    <section class="totals">
        <div class="trow final"><span>Total</span><strong>{totalAmount.toFixed(2)}</strong></div>
    </section>

    <footer class="foot">
        <button class="save" data-flow="save" disabled={!canSave} onclick={requestSave} type="button">
            {saving ? "Saving…" : "Post receipt"} <kbd>Ctrl ⏎</kbd></button>
    </footer>
</div>

{#if partyDialog !== null}
    <PartyCreateDialog initialName={partyDialog} oncreated={onPartyCreated} oncancel={() => (partyDialog = null)}/>
{/if}
{#if warningIssues}
    <WarningDialog issues={warningIssues} onreview={reviewWarning} onproceed={proceedWarning} oncancel={closeWarning}/>
{/if}
{#if confirmOpen}
    <ConfirmDialog title="Confirm receipt" message={confirmMessage} confirmLabel="Post receipt" busy={saving}
                   onconfirm={confirmSave} oncancel={closeConfirm}/>
{/if}

<style>
    .wrap {
        padding: 20px 28px 40px;
        box-sizing: border-box;
    }

    .head {
        display: flex;
        gap: 18px;
        align-items: flex-end;
        margin-bottom: 22px;
        max-width: 520px;
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

    .grid {
        border: 1px solid var(--border);
        border-radius: 10px;
        background: var(--bg-panel);
    }

    .ghead, .srow {
        display: grid;
        grid-template-columns: 1fr 130px 80px 90px 1fr 36px;
        gap: 10px;
        align-items: center;
        padding: 10px 14px;
    }

    .ghead {
        color: var(--text-muted);
        font-size: 12px;
        border-bottom: 1px solid var(--border);
    }

    .srow {
        border-bottom: 1px solid #171b23;
    }

    .cell {
        min-width: 0;
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

    input[type="text"] {
        padding: 8px 10px;
        border-radius: var(--radius);
        border: 1px solid var(--border-hi);
        background: var(--bg-app);
        color: var(--text);
        font-size: 13px;
        box-sizing: border-box;
        width: 100%;
    }

    .tag {
        font-size: 11px;
        text-transform: uppercase;
        padding: 3px 8px;
        border-radius: 4px;
        background: rgba(255, 255, 255, .06);
        color: var(--text-muted);
        display: inline-block;
    }

    .tag.bank {
        background: rgba(47, 111, 235, .12);
        color: var(--accent-text);
    }

    .tag.bank-type {
        background: rgba(52, 211, 153, .1);
        color: #34d399;
    }

    .tag.empty {
        opacity: .4;
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

    .totals {
        margin-top: 14px;
        max-width: 300px;
        margin-left: auto;
    }

    .trow {
        display: flex;
        justify-content: space-between;
        font-size: 16px;
        color: var(--text);
        padding: 2px 2px;
    }

    .trow.final strong {
        color: var(--ok);
    }

    .foot {
        display: flex;
        justify-content: flex-end;
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

    .muted {
        color: var(--text-muted);
        font-size: 13px;
    }

    .ahead, .arow {
        display: grid;
        grid-template-columns: 1fr auto auto;
        gap: 10px;
        font-size: 13px;
        padding: 5px 0;
    }

    .ahead {
        color: var(--text-muted);
        font-size: 11px;
        border-bottom: 1px solid var(--border);
    }

    .rt {
        text-align: right;
    }

    .hot {
        color: var(--ok);
        font-weight: 600;
    }

    .sidehead {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
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

    .hrow-btn {
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

    li.active .hrow-btn {
        border-color: var(--accent);
    }

    li.cancelled .hrow-btn {
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

    .preview-summary {
        background: var(--bg-elevated);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 8px 10px;
        margin-bottom: 10px;
        display: flex;
        flex-direction: column;
        gap: 4px;
    }

    .ps-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 13px;
    }

    .ps-row.on-acc {
        color: var(--warn);
        font-size: 12px;
    }

    .bal-tag {
        font-size: 10px;
        font-weight: 400;
        margin-left: 4px;
        color: var(--text-muted);
    }

    .recv {
        color: var(--ok);
    }

    .pay {
        color: var(--danger);
    }
</style>
