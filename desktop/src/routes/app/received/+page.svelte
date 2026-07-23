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
    });

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
    type OpenBills = {
        outstanding_total: number;
        balance: number;
        on_account: number;
        bills: OpenBill[]
    };
    type SettlementMode = {
        id: number; name: string; is_system: boolean; is_active: boolean; sort_order: number;
    };

    type SettleCategory = "CASH" | "BANK";
    type BankSubMode = "UPI" | "TRANSFER" | "CHEQUE" | "OTHER";

    const today = new Date().toISOString().slice(0, 10);
    let party = $state<Suggestion | null>(null);
    let date = $state(today);
    let amount = $state("0");
    let saving = $state(false);
    let error = $state<string | null>(null);
    let result = $state<SettleResult | null>(null);
    let history = $state<Voucher[]>([]);
    let loadingHistory = $state(false);
    let selectedId = $state<number | null>(null);
    let preview = $state<OpenBills | null>(null);
    let loadingPreview = $state(false);
    let partyDialog = $state<string | null>(null);
    let modes = $state<SettlementMode[]>([]);
    let modeId = $state<number | null>(null);

    let settleCategory = $state<SettleCategory>("CASH");
    let bankSubMode = $state<BankSubMode>("UPI");
    let transactionRef = $state("");

    const companyId = $derived(auth.currentCompany?.id ?? null);
    const endpoint = "/api/vouchers/received/";
    const canSave = $derived(!!party && !!companyId && Number(amount) > 0 && !saving);
    const allocated = $derived((result?.allocations ?? []).reduce((s, a) => s + (Number(a.amount) || 0), 0));
    const unallocated = $derived(result ? Math.max(0, (Number(result.amount) || 0) - allocated) : 0);
    const modeOptions = $derived(modes.filter((m) => m.is_active).map((m) => ({id: m.id, name: m.name})));

    let confirmOpen = $state(false);
    let warningIssues = $state<Issue[] | null>(null);
    let warningNext = $state<(() => void) | null>(null);

    function isComplete(): boolean {
        return !!party && !!companyId && Number(amount) > 0 && !!date;
    }

    function collectIssues(): Issue[] {
        const issues: Issue[] = [];
        const amt = Number(amount) || 0;
        if (amt > 0 && modeId == null) {
            issues.push({
                code: "settle-no-mode",
                message: "No settlement mode selected.",
                focus: () => document.getElementById("amount")?.focus()
            });
        }
        if (settleCategory === "BANK" && bankSubMode === "CHEQUE" && !transactionRef.trim()) {
            issues.push({
                code: "settle-no-cheque-no",
                message: "Cheque number is empty. You can proceed without it.",
                focus: () => document.getElementById("txn-ref")?.focus()
            });
        }
        const outstanding = Number(preview?.outstanding_total ?? 0);
        if (amt > 0 && outstanding > 0 && amt > outstanding) {
            issues.push({
                code: "settle-overpay",
                message: `Amount (${amt.toFixed(2)}) exceeds the outstanding total (${outstanding.toFixed(2)}). The excess will remain as an advance on account.`,
                focus: () => {
                    const el = document.getElementById("amount") as HTMLInputElement | null;
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
        setTimeout(() => (document.getElementById("amount") as HTMLElement | null)?.focus(), 0);
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

    function requestSave() {
        attemptSave("confirm");
    }

    async function confirmSave() {
        confirmOpen = false;
        await save();
    }

    function closeConfirm() {
        confirmOpen = false;
        setTimeout(() => (document.getElementById("amount") as HTMLElement | null)?.focus(), 0);
    }

    const flowOpts = $derived({
        onSave: (_opts: { direct: boolean }) => {
            attemptSave("direct");
        },
        isComplete,
        onConfirm: () => {
            attemptSave("confirm");
        },
    });

    const previewPlan = $derived.by(() => {
        if (!preview) return [];
        let remaining = Number(amount) || 0;
        return preview.bills.map((b) => {
            const take = Math.min(remaining, Number(b.open));
            remaining = Math.max(0, remaining - take);
            return {...b, willSettle: take};
        });
    });

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

    function setCategory(c: SettleCategory) {
        settleCategory = c;
        transactionRef = "";
        if (c === "CASH") bankSubMode = "UPI";
    }

    async function loadModes() {
        try {
            const rows = await request<SettlementMode[] | {
                results?: SettlementMode[]
            }>("/api/accounts/settlement-modes/");
            modes = Array.isArray(rows) ? rows : (rows?.results ?? []);
            if (modeId == null) {
                const active = modes.filter((m) => m.is_active);
                const sys = active.find((m) => m.is_system);
                modeId = sys?.id ?? active[0]?.id ?? null;
            }
        } catch {
            modes = [];
        }
    }

    function onModeSelect(id: number) {
        modeId = id;
    }

    async function loadHistory() {
        if (!companyId) return;
        loadingHistory = true;
        try {
            const p = new URLSearchParams({company: String(companyId)});
            if (party) p.set("party", String(party.id));
            const rows = await request<Voucher[] | { results?: Voucher[] }>(`${endpoint}?${p.toString()}`);
            history = Array.isArray(rows) ? rows : (rows?.results ?? []);
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
            result = {id: v.id, number: v.number, amount: Number(v.amount), allocations: allocs ?? []};
            shell.activeTab = "allocation";
        } catch (e) {
            error = e instanceof Error ? e.message : "Could not load allocations.";
        }
    }

    async function save() {
        if (!party || !companyId || saving) return;
        saving = true;
        error = null;
        result = null;
        selectedId = null;
        try {
            const res = await request<SettleResult>(endpoint, {
                method: "POST",
                body: JSON.stringify({
                    company: companyId, party: party.id, date,
                    amount: Number(amount), mode: modeId, number: null,
                    settle_category: settleCategory,
                    bank_sub_mode: settleCategory === "BANK" ? bankSubMode : null,
                    transaction_ref: (settleCategory === "BANK" && transactionRef.trim()) ? transactionRef.trim() : null,
                }),
            });
            result = {id: res.id, number: res.number, amount: Number(res.amount), allocations: res.allocations ?? []};
            amount = "0";
            transactionRef = "";
            await loadHistory();
            await loadPreview();
            shell.activeTab = "allocation";
        } catch (e) {
            error = e instanceof Error ? e.message : "Could not save.";
        } finally {
            saving = false;
        }
    }

    const shell = registerScreen(() => ({
        title: "Received",
        actions: [{id: "set-save", label: "Save", icon: "✓", shortcut: "Ctrl+Enter", run: requestSave}],
        shortcuts: [],
        panel: [
            {id: "allocation", title: "Allocation", body: allocationPanel},
            {id: "history", title: "History", body: historyPanel},
        ],
    }));
</script>

{#snippet allocationPanel()}
    {#if result}
        <div class="banner ok">#{result.number} · {result.amount.toFixed(2)}</div>
        <h3>Settled</h3>
        {#if result.allocations.length === 0}
            <p class="muted">No open bills settled. Kept on account.</p>
        {:else}
            {#each result.allocations as a (a.id)}
                <div class="arow"><span>#{a.bill_number ?? a.bill_id}</span>
                    <span class="rt">{Number(a.amount).toFixed(2)}</span></div>
            {/each}
            <div class="sumline"><span>Allocated</span><strong>{allocated.toFixed(2)}</strong></div>
            {#if unallocated > 0}
                <div class="sumline adv"><span>On account</span><strong>{unallocated.toFixed(2)}</strong></div>
            {/if}
        {/if}
    {:else if !party}
        <p class="muted">Pick a party to preview open sales.</p>
    {:else if loadingPreview}
        <p class="muted">Loading open bills…</p>
    {:else if preview}
        {@const bal = Number(preview.balance)}
        {@const outstanding = Number(preview.outstanding_total)}
        {@const onAcc = Number(preview.on_account)}
        <div class="preview-summary">
            <div class="ps-row"><span>Balance</span>
                <strong class={bal > 0 ? 'recv' : bal < 0 ? 'pay' : ''}>{Math.abs(bal).toFixed(2)}
                    <span class="bal-tag">{bal > 0 ? 'receivable' : bal < 0 ? 'payable' : 'settled'}</span></strong>
            </div>
            {#if onAcc > 0.001}
                <div class="ps-row on-acc"><span>On account (advance)</span><strong>{onAcc.toFixed(2)}</strong></div>
            {/if}
            <div class="ps-row"><span>Open bills</span><strong>{outstanding.toFixed(2)}</strong></div>
        </div>
        {#if preview.bills.length === 0}<p class="muted">Nothing outstanding.</p>
        {:else}
            <div class="ahead"><span>Bill</span><span class="rt">Open</span><span class="rt">Will settle</span></div>
            {#each previewPlan as b (b.bill_id)}
                <div class="arow"><span>#{b.number}</span>
                    <span class="rt">{Number(b.open).toFixed(2)}</span>
                    <span class="rt" class:hot={b.willSettle > 0}>{b.willSettle.toFixed(2)}</span></div>
            {/each}
        {/if}
    {/if}
{/snippet}

{#snippet historyPanel()}
    <div class="sidehead">
        <span class="muted">Receipts{party ? ` · ${party.name}` : ""}</span>
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
    <h2 class="page-title">Received</h2>
    <p class="sub">Receive from a customer. Auto-settles open sales oldest → latest.</p>

    {#if error}
        <div class="banner err">{error}</div>
    {/if}

    <section class="head">
        <div class="field"><label for="party">Party</label>
            <SmartLookup flow="party" oncreate={onPartyCreate} onselect={onPartySelect}
                         placeholder="Search or create party…" type="PARTY" value={party}/>
        </div>
        <div class="field amt"><label for="amount">Amount</label>
            <input bind:value={amount} class="num" data-flow="amount" id="amount" min="0" step="0.01" type="number"/>
        </div>
        <div class="field date"><label for="date">Date</label>
            <input bind:value={date} data-flow="date" id="date" type="date"/></div>
    </section>

    <section class="mode-section">
        <div class="field mode"><label>Mode</label>
            <LedgerLookup bind:value={modeId} flow="mode" onselect={onModeSelect} options={modeOptions}
                          placeholder="Settlement mode…"/>
        </div>
        <div class="field category"><label>Category</label>
            <div class="toggle">
                <button class:active={settleCategory === "CASH"} onclick={() => setCategory("CASH")}>Cash</button>
                <button class:active={settleCategory === "BANK"} onclick={() => setCategory("BANK")}>Bank</button>
            </div>
        </div>
        {#if settleCategory === "BANK"}
            <div class="field sub-mode"><label>Bank Mode</label>
                <div class="toggle">
                    <button class:active={bankSubMode === "UPI"} onclick={() => (bankSubMode = "UPI")}>UPI</button>
                    <button class:active={bankSubMode === "TRANSFER"} onclick={() => (bankSubMode = "TRANSFER")}>
                        Transfer
                    </button>
                    <button class:active={bankSubMode === "CHEQUE"} onclick={() => (bankSubMode = "CHEQUE")}>Cheque
                    </button>
                    <button class:active={bankSubMode === "OTHER"} onclick={() => (bankSubMode = "OTHER")}>Other
                    </button>
                </div>
            </div>
            <div class="field ref"><label
                    for="txn-ref">{bankSubMode === "CHEQUE" ? "Cheque No." : bankSubMode === "UPI" ? "UPI Ref / UTR" : "Transaction ID"}</label>
                <input bind:value={transactionRef} data-flow="txn-ref" id="txn-ref" type="text"
                       placeholder={bankSubMode === "CHEQUE" ? "Cheque number (optional)" : "Reference (optional)"}/>
            </div>
        {/if}
    </section>

    <footer class="foot">
        <button class="save" data-flow="save" disabled={!canSave} onclick={requestSave} type="button">
            {saving ? "Saving…" : "Save receipt"} <kbd>Ctrl ⏎</kbd>
        </button>
    </footer>
</div>

{#if partyDialog !== null}
    <PartyCreateDialog initialName={partyDialog} oncreated={onPartyCreated} oncancel={() => (partyDialog = null)}/>
{/if}
{#if warningIssues}
    <WarningDialog issues={warningIssues} onreview={reviewWarning} onproceed={proceedWarning} oncancel={closeWarning}/>
{/if}
{#if confirmOpen}
    <ConfirmDialog title="Confirm receipt"
                   message={`Party: ${party?.name ?? "—"} · Amount ${Number(amount).toFixed(2)} · ${settleCategory}${settleCategory === "BANK" ? ` (${bankSubMode})` : ""}${transactionRef ? ` · Ref: ${transactionRef}` : ""}. Auto-settle oldest → latest?`}
                   confirmLabel="Post receipt" busy={saving} onconfirm={confirmSave} oncancel={closeConfirm}/>
{/if}

<style>
    .wrap {
        padding: 20px 28px 40px;
        box-sizing: border-box;
        max-width: 760px;
    }

    .page-title {
        margin: 0 0 4px;
        font-size: 18px;
        color: var(--text);
    }

    .sub {
        color: var(--text-muted);
        font-size: 13px;
        margin: 0 0 18px;
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

    .head {
        display: flex;
        gap: 18px;
        margin-bottom: 20px;
    }

    .field {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .field.amt {
        max-width: 200px;
    }

    .field.mode {
        max-width: 200px;
    }

    .field.date {
        max-width: 180px;
    }

    .field.category {
        max-width: 160px;
    }

    .field.sub-mode {
        max-width: 280px;
    }

    .field.ref {
        max-width: 260px;
    }

    label {
        font-size: 12px;
        color: var(--text-muted);
    }

    .num, input[type="date"], input[type="text"] {
        padding: 8px 10px;
        border-radius: var(--radius);
        border: 1px solid var(--border-hi);
        background: var(--bg-app);
        color: var(--text);
        font-size: 14px;
        box-sizing: border-box;
    }

    .num {
        text-align: right;
        width: 100%;
    }

    input[type="text"] {
        width: 100%;
    }

    .mode-section {
        display: flex;
        gap: 18px;
        align-items: flex-end;
        margin-bottom: 20px;
        flex-wrap: wrap;
    }

    .toggle {
        display: inline-flex;
        border: 1px solid var(--border-hi);
        border-radius: var(--radius);
        overflow: hidden;
    }

    .toggle button {
        padding: 8px 16px;
        background: transparent;
        border: none;
        color: var(--text-muted);
        cursor: pointer;
        font-size: 13px;
    }

    .toggle button.active {
        background: var(--accent);
        color: #fff;
    }

    .foot {
        display: flex;
        justify-content: flex-end;
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

    h3 {
        font-size: 13px;
        margin: 8px 0;
        color: var(--text);
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

    .sumline {
        display: flex;
        justify-content: space-between;
        font-size: 13px;
        margin-top: 8px;
    }

    .adv {
        color: var(--warn);
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
