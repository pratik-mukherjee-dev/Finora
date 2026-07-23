<script lang="ts">
    import {auth} from "$lib/stores/auth.svelte";
    import {goto} from "$app/navigation";
    import {onMount} from "svelte";
    import {request, ApiError} from "$lib/api";
    import ConfirmDialog from "$lib/components/ConfirmDialog.svelte";
    import PartyCreateDialog from "$lib/components/PartyCreateDialog.svelte";
    import {registerScreen} from "$lib/shell/useScreen.svelte";
    import type {Suggestion} from "$lib/api";

    onMount(() => {
        if (!auth.isAuthed) return void goto("/login");
        if (auth.needsSetup) return void goto("/setup");
        if (auth.needsFy) return void goto("/fy");
        void loadParties();
    });

    // ── types ──────────────────────────────────────────────────────────────────
    type Party = {
        id: number;
        name: string;
        phone: string | null;
        address: string | null;
        opening_balance: number;
        balance: number;
        created_at: string;
    };
    type LedgerEntry = {
        id: number;
        date: string;
        voucher_type: string;
        voucher_id: number;
        debit: number;
        credit: number;
        balance: number;
        is_reversal: boolean;
    };

    // ── state ──────────────────────────────────────────────────────────────────
    let parties = $state<Party[]>([]);
    let loading = $state(false);
    let search = $state("");
    let selectedId = $state<number | null>(null);
    let ledger = $state<LedgerEntry[]>([]);
    let ledgerLoading = $state(false);
    let ledgerFilter = $state<string>("ALL");
    let partyOutstanding = $state<{
        outstanding: number;
        on_account: number;
        receivable_outstanding: number;
        payable_outstanding: number;
        receivable_on_account: number;
        payable_on_account: number;
    } | null>(null);
    let error = $state<string | null>(null);

    // create dialog
    let createOpen = $state(false);

    // inline edit
    let editParty = $state<Party | null>(null);
    let editPhone = $state("");
    let editAddress = $state("");
    let editOpening = $state("0");
    let editBusy = $state(false);
    let editError = $state<string | null>(null);

    // delete confirm
    let deleteTarget = $state<Party | null>(null);
    let deleteBusy = $state(false);

    // derived
    const filtered = $derived(
        search.trim()
            ? parties.filter((p) =>
                p.name.toLowerCase().includes(search.trim().toLowerCase()) ||
                (p.phone ?? "").includes(search.trim())
            )
            : parties
    );
    const selected = $derived(parties.find((p) => p.id === selectedId) ?? null);
    const totalReceivable = $derived(
        parties.reduce((s, p) => s + Math.max(0, Number(p.balance)), 0)
    );
    const totalPayable = $derived(
        parties.reduce((s, p) => s + Math.max(0, -Number(p.balance)), 0)
    );
    const filteredLedger = $derived(
        ledgerFilter === "ALL"
            ? ledger
            : ledger.filter((e) => e.voucher_type === ledgerFilter)
    );


    // ── data loading ──────────────────────────────────────────────────────────
    async function loadParties() {
        loading = true;
        try {
            const rows = await request<Party[] | { results?: Party[] }>("/api/parties/");
            parties = Array.isArray(rows) ? rows : (rows?.results ?? []);
        } catch {
            parties = [];
        } finally {
            loading = false;
        }
    }

    async function loadLedger(partyId: number) {
        ledgerLoading = true;
        ledger = [];
        try {
            const rows = await request<LedgerEntry[]>(`/api/parties/${partyId}/ledger/`);
            ledger = Array.isArray(rows) ? rows : [];
        } catch {
            ledger = [];
        } finally {
            ledgerLoading = false;
        }
    }

    async function loadOutstanding(partyId: number) {
        try {
            const [recv, pay] = await Promise.all([
                request<{ outstanding_total: number; on_account: number }>(
                    `/api/vouchers/received/open_bills/?party=${partyId}`
                ),
                request<{ outstanding_total: number; on_account: number }>(
                    `/api/vouchers/payments/open_bills/?party=${partyId}`
                ),
            ]);
            partyOutstanding = {
                outstanding: Number(recv.outstanding_total) + Number(pay.outstanding_total),
                on_account: Number(recv.on_account) + Number(pay.on_account),
                receivable_outstanding: Number(recv.outstanding_total),
                payable_outstanding: Number(pay.outstanding_total),
                receivable_on_account: Number(recv.on_account),
                payable_on_account: Number(pay.on_account),
            };
        } catch {
            partyOutstanding = null;
        }
    }


    function selectParty(p: Party) {
        selectedId = p.id;
        ledgerFilter = "ALL";
        startEdit(p);
        void loadLedger(p.id);
        void loadOutstanding(p.id);
        shell.activeTab = "ledger";
    }

    // ── create ────────────────────────────────────────────────────────────────
    function openCreate() {
        createOpen = true;
    }

    function onCreated(s: Suggestion) {
        createOpen = false;
        void loadParties().then(() => {
            const found = parties.find((p) => p.id === s.id);
            if (found) selectParty(found);
        });
    }

    // ── edit ──────────────────────────────────────────────────────────────────
    function startEdit(p: Party) {
        editParty = p;
        editPhone = p.phone ?? "";
        editAddress = p.address ?? "";
        editOpening = String(p.opening_balance);
        editError = null;
    }

    async function saveEdit() {
        if (!editParty) return;
        editBusy = true;
        editError = null;
        try {
            await request(`/api/parties/${editParty.id}/`, {
                method: "PATCH",
                body: JSON.stringify({
                    phone: editPhone.trim() || null,
                    address: editAddress.trim() || null,
                    opening_balance: Number(editOpening) || 0,
                }),
            });
            await loadParties();
            if (selectedId === editParty.id) void loadLedger(editParty.id);
            const updated = parties.find((p) => p.id === editParty!.id);
            if (updated) editParty = updated;
        } catch (e) {
            editError = e instanceof ApiError ? e.message : "Could not save.";
        } finally {
            editBusy = false;
        }
    }

    // ── delete ────────────────────────────────────────────────────────────────
    function requestDelete(p: Party) {
        deleteTarget = p;
    }

    async function confirmDelete() {
        if (!deleteTarget) return;
        deleteBusy = true;
        try {
            await request(`/api/parties/${deleteTarget.id}/`, {method: "DELETE"});
            if (selectedId === deleteTarget.id) {
                selectedId = null;
                ledger = [];
                editParty = null;
            }
            deleteTarget = null;
            await loadParties();
        } catch (e) {
            error = e instanceof ApiError ? e.message : "Could not delete party.";
            deleteTarget = null;
        } finally {
            deleteBusy = false;
        }
    }

    // ── helpers ───────────────────────────────────────────────────────────────
    const VOUCHER_LABELS: Record<string, string> = {
        SALE: "Sale", PURCHASE: "Purchase", RECEIVED: "Receipt",
        PAYMENT: "Payment", OPENING: "Opening",
    };

    function balanceLabel(bal: number): string {
        if (bal > 0) return "receivable";
        if (bal < 0) return "payable";
        return "settled";
    }

    function balanceClass(bal: number): string {
        if (bal > 0) return "recv";
        if (bal < 0) return "pay";
        return "";
    }

    // ── shell registration ───────────────────────────────────────────────────
    const shell = registerScreen(() => ({
        title: "Parties",
        actions: [
            {id: "pty-new", label: "New party", icon: "＋", shortcut: "Ctrl+N", run: openCreate},
            {id: "pty-refresh", label: "Refresh", icon: "↻", run: () => void loadParties()},
        ],
        shortcuts: [
            {id: "pty-k-new", keychord: "ctrl+n", label: "New party", run: openCreate},
        ],
        panel: [
            {id: "ledger", title: "Ledger", body: ledgerPanel},
            {id: "info", title: "Info", body: infoPanel},
        ],
    }));
</script>

{#snippet ledgerPanel()}
    {#if !selected}
        <p class="muted">Select a party to view their ledger.</p>
    {:else}
        <div class="sidehead">
            <span class="panel-party">{selected.name}</span>
            <button class="refresh" onclick={() => loadLedger(selected.id)} disabled={ledgerLoading}>
                {ledgerLoading ? "…" : "↻"}
            </button>
        </div>
        <div class="bal-summary">
            <div class="bal-row">
                <span>Balance</span>
                <strong class={balanceClass(Number(selected.balance))}>
                    {Math.abs(Number(selected.balance)).toFixed(2)}
                    <span class="bal-tag">{balanceLabel(Number(selected.balance))}</span>
                </strong>
            </div>
            {#if partyOutstanding}
                {#if partyOutstanding.receivable_outstanding > 0.001}
                    <div class="bal-row bal-detail">
                        <span class="muted">Unpaid sales</span>
                        <span>{partyOutstanding.receivable_outstanding.toFixed(2)}</span>
                    </div>
                {/if}
                {#if partyOutstanding.payable_outstanding > 0.001}
                    <div class="bal-row bal-detail">
                        <span class="muted">Unpaid purchases</span>
                        <span>{partyOutstanding.payable_outstanding.toFixed(2)}</span>
                    </div>
                {/if}
                {#if partyOutstanding.receivable_on_account > 0.001}
                    <div class="bal-row bal-detail on-acc">
                        <span>Excess receipts (advance)</span>
                        <span>{partyOutstanding.receivable_on_account.toFixed(2)}</span>
                    </div>
                {/if}
                {#if partyOutstanding.payable_on_account > 0.001}
                    <div class="bal-row bal-detail on-acc">
                        <span>Excess payments (advance)</span>
                        <span>{partyOutstanding.payable_on_account.toFixed(2)}</span>
                    </div>
                {/if}
            {/if}
        </div>


        <div class="lfilter">
            <button class:active={ledgerFilter === "ALL"} onclick={() => (ledgerFilter = "ALL")}>All</button>
            <button class:active={ledgerFilter === "SALE"} onclick={() => (ledgerFilter = "SALE")}>Sale</button>
            <button class:active={ledgerFilter === "PURCHASE"} onclick={() => (ledgerFilter = "PURCHASE")}>Purchase
            </button>
            <button class:active={ledgerFilter === "RECEIVED"} onclick={() => (ledgerFilter = "RECEIVED")}>Receipt
            </button>
            <button class:active={ledgerFilter === "PAYMENT"} onclick={() => (ledgerFilter = "PAYMENT")}>Payment
            </button>
        </div>
        {#if filteredLedger.length === 0}
            <p class="muted">{ledgerLoading ? "Loading…" : "No transactions yet."}</p>
        {:else}
            <div class="lhead">
                <span>Voucher</span>
                <span class="rt">Dr</span>
                <span class="rt">Cr</span>
                <span class="rt">Bal</span>
            </div>
            {#each filteredLedger as e (e.id)}
                <div class="lrow" class:reversal={e.is_reversal}>
                    <span class="ltype">
                        <span class="lvoucher">{VOUCHER_LABELS[e.voucher_type] ?? e.voucher_type} #{e.voucher_id}</span>
                        {#if e.is_reversal}<span class="rev-tag">rev</span>{/if}
                        <span class="ldate">{e.date}</span>
                    </span>
                    <span class="rt lnum">{Number(e.debit) > 0 ? Number(e.debit).toFixed(2) : ""}</span>
                    <span class="rt lnum">{Number(e.credit) > 0 ? Number(e.credit).toFixed(2) : ""}</span>
                    <span class="rt lbal">{Number(e.balance).toFixed(2)}</span>
                </div>
            {/each}
        {/if}
    {/if}
{/snippet}


{#snippet infoPanel()}
    {#if !editParty}
        <p class="muted">Select a party to view and edit details.</p>
    {:else}
        <div class="sidehead">
            <span class="panel-party">{editParty.name}</span>
        </div>
        <div class="info-form">
            <label class="info-label">
                Phone
                <input class="info-input" bind:value={editPhone} placeholder="Phone number"/>
            </label>
            <label class="info-label">
                Address
                <textarea class="info-textarea" bind:value={editAddress} placeholder="Address" rows="2"></textarea>
            </label>
            <label class="info-label">
                Opening balance
                <input class="info-input num" type="number" step="0.01" bind:value={editOpening}/>
            </label>
            {#if editError}<p class="err">{editError}</p>{/if}
            <button class="info-save" disabled={editBusy} onclick={saveEdit}>
                {editBusy ? "Saving…" : "Save changes"}
            </button>
        </div>
        <div class="info-meta">
            <span class="muted">Created: {new Date(editParty.created_at).toLocaleDateString()}</span>
        </div>
    {/if}
{/snippet}

<div class="wrap">
    {#if error}
        <div class="banner err">{error}</div>
    {/if}

    <!-- ── summary bar ── -->
    <div class="summary">
        <div class="stat">
            <span class="stat-label">Parties</span>
            <span class="stat-value">{parties.length}</span>
        </div>
        <div class="stat">
            <span class="stat-label">Total receivable</span>
            <span class="stat-value recv">{totalReceivable.toFixed(2)}</span>
        </div>
        <div class="stat">
            <span class="stat-label">Total payable</span>
            <span class="stat-value pay">{totalPayable.toFixed(2)}</span>
        </div>
    </div>

    <!-- ── toolbar ── -->
    <div class="toolbar">
        <input bind:value={search} class="search" placeholder="Search parties…" type="text"/>
        <button class="add-btn" onclick={openCreate}>+ New party <kbd>Ctrl N</kbd></button>
    </div>

    <!-- ── party list ── -->
    <section class="list-section">
        {#if loading}
            <p class="muted center">Loading parties…</p>
        {:else if filtered.length === 0}
            <p class="muted center">
                {search.trim() ? "No parties match your search." : "No parties yet. Create one to get started."}
            </p>
        {:else}
            <div class="list-head">
                <span class="col-name">Name</span>
                <span class="col-phone">Phone</span>
                <span class="col-bal rt">Balance</span>
                <span class="col-act"></span>
            </div>
            <ul class="party-list">
                {#each filtered as p (p.id)}
                    {@const bal = Number(p.balance)}
                    <li class:active={p.id === selectedId}>
                        <button class="party-row" onclick={() => selectParty(p)}>
                            <span class="col-name">{p.name}</span>
                            <span class="col-phone muted">{p.phone ?? ""}</span>
                            <span class="col-bal rt" class:recv={bal > 0} class:pay={bal < 0}>
                                {Math.abs(bal).toFixed(2)}
                                <span class="bal-hint">{balanceLabel(bal)}</span>
                            </span>
                        </button>
                        <button class="del-btn" title="Delete party" onclick={() => requestDelete(p)}>✕</button>
                    </li>
                {/each}
            </ul>
        {/if}
    </section>
</div>

{#if createOpen}
    <PartyCreateDialog initialName="" oncreated={onCreated} oncancel={() => (createOpen = false)}/>
{/if}
{#if deleteTarget}
    <ConfirmDialog
            title="Delete party"
            message={`Delete "${deleteTarget.name}"? This cannot be undone if the party has ledger entries.`}
            confirmLabel="Delete"
            busy={deleteBusy}
            onconfirm={confirmDelete}
            oncancel={() => (deleteTarget = null)}
    />
{/if}

<style>
    .wrap {
        padding: 20px 28px 40px;
        box-sizing: border-box;
        max-width: 860px;
    }

    /* ── summary bar ── */
    .summary {
        display: flex;
        gap: 20px;
        margin-bottom: 20px;
    }

    .stat {
        flex: 1;
        border: 1px solid var(--border);
        border-radius: 10px;
        background: var(--bg-elevated);
        padding: 14px 18px;
        display: flex;
        flex-direction: column;
        gap: 4px;
    }

    .stat-label {
        font-size: 11px;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .stat-value {
        font-size: 20px;
        font-weight: 700;
        color: var(--text);
    }

    .stat-value.recv {
        color: var(--ok);
    }

    .stat-value.pay {
        color: var(--danger);
    }

    /* ── toolbar ── */
    .toolbar {
        display: flex;
        gap: 12px;
        margin-bottom: 16px;
        align-items: center;
    }

    .search {
        flex: 1;
        padding: 9px 12px;
        border-radius: var(--radius);
        border: 1px solid var(--border-hi);
        background: var(--bg-app);
        color: var(--text);
        font-size: 14px;
        box-sizing: border-box;
    }

    .add-btn {
        padding: 9px 16px;
        border-radius: var(--radius);
        border: 1px solid var(--accent);
        background: var(--accent);
        color: #fff;
        cursor: pointer;
        font-size: 13px;
        white-space: nowrap;
    }

    .add-btn:hover {
        opacity: 0.9;
    }

    kbd {
        background: rgba(0, 0, 0, .25);
        border: 1px solid var(--border-hi);
        border-radius: 4px;
        padding: 0 4px;
        font-size: 10px;
        margin-left: 6px;
    }

    /* ── party list ── */
    .list-section {
        border: 1px solid var(--border);
        border-radius: 10px;
        background: var(--bg-panel);
        overflow: hidden;
    }

    .list-head {
        display: grid;
        grid-template-columns: 1fr 140px 160px 36px;
        gap: 12px;
        padding: 10px 16px;
        font-size: 11px;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.3px;
        border-bottom: 1px solid var(--border);
    }

    .party-list {
        list-style: none;
        margin: 0;
        padding: 0;
    }

    .party-list li {
        display: flex;
        align-items: center;
        border-bottom: 1px solid #171b23;
    }

    .party-list li:last-child {
        border-bottom: none;
    }

    .party-list li:hover {
        background: rgba(255, 255, 255, .02);
    }

    .party-list li.active {
        background: rgba(47, 111, 235, .06);
    }

    .party-row {
        flex: 1;
        display: grid;
        grid-template-columns: 1fr 140px 160px;
        gap: 12px;
        padding: 12px 16px;
        background: transparent;
        border: none;
        color: var(--text);
        cursor: pointer;
        text-align: left;
        font-size: 14px;
    }

    .col-name {
        font-weight: 500;
    }

    .col-phone {
        font-size: 13px;
    }

    .col-bal {
        font-weight: 600;
        font-size: 14px;
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 1px;
    }

    .bal-hint {
        font-size: 10px;
        font-weight: 400;
        color: var(--text-muted);
    }

    .recv {
        color: var(--ok);
    }

    .pay {
        color: var(--danger);
    }

    .del-btn {
        background: transparent;
        border: none;
        color: #6b7280;
        cursor: pointer;
        padding: 8px;
        font-size: 13px;
    }

    .del-btn:hover {
        color: var(--danger);
    }

    .rt {
        text-align: right;
    }

    .muted {
        color: var(--text-muted);
        font-size: 13px;
    }

    .center {
        text-align: center;
        padding: 32px 16px;
    }

    .banner {
        padding: 10px 14px;
        border-radius: var(--radius);
        margin-bottom: 16px;
        font-size: 14px;
    }

    .banner.err {
        background: var(--danger-soft);
        color: #ff9b9b;
        border: 1px solid var(--danger-border);
    }

    .err {
        margin: 0;
        font-size: 12px;
        color: #ff9b9b;
    }

    /* ── ledger panel ── */
    .sidehead {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }

    .panel-party {
        font-weight: 600;
        font-size: 14px;
        color: var(--text);
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

    .bal-summary {
        display: flex;
        flex-direction: column;
        gap: 6px;
        padding: 8px 10px;
        border-radius: var(--radius);
        background: var(--bg-elevated);
        margin-bottom: 12px;
        font-size: 13px;
    }

    .bal-tag {
        font-size: 10px;
        font-weight: 400;
        margin-left: 4px;
        color: var(--text-muted);
    }

    .lfilter {
        display: flex;
        gap: 2px;
        margin-bottom: 8px;
        flex-wrap: wrap;
    }

    .lfilter button {
        padding: 3px 8px;
        font-size: 10px;
        border-radius: 4px;
        border: 1px solid var(--border-hi);
        background: transparent;
        color: var(--text-muted);
        cursor: pointer;
    }

    .lfilter button.active {
        background: var(--accent-soft);
        color: var(--accent-text);
        border-color: var(--accent);
    }

    .lfilter button:hover:not(.active) {
        background: var(--bg-elevated);
    }


    /* ── ledger panel (compact, no h-scroll) ── */
    .lhead {
        display: grid;
        grid-template-columns: 1fr 48px 48px 56px;
        gap: 2px;
        font-size: 10px;
        color: var(--text-muted);
        text-transform: uppercase;
        padding: 4px 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 2px;
    }

    .lrow {
        display: grid;
        grid-template-columns: 1fr 48px 48px 56px;
        gap: 2px;
        font-size: 12px;
        padding: 4px 0;
        border-bottom: 1px solid rgba(255, 255, 255, .02);
        align-items: start;
    }

    .lrow.reversal {
        opacity: 0.55;
    }

    .ltype {
        display: flex;
        flex-direction: column;
        gap: 1px;
        min-width: 0;
    }

    .lvoucher {
        font-size: 12px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .ldate {
        font-size: 10px;
        color: var(--text-muted);
    }

    .rev-tag {
        font-size: 9px;
        text-transform: uppercase;
        color: var(--warn);
        background: rgba(255, 193, 92, .1);
        padding: 0 4px;
        border-radius: 3px;
        align-self: flex-start;
    }

    .lnum {
        font-size: 11px;
        white-space: nowrap;
    }

    .lbal {
        font-weight: 600;
        font-size: 11px;
        white-space: nowrap;
    }


    /* ── info panel ── */
    .info-form {
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin-top: 8px;
    }

    .info-label {
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 11px;
        color: var(--text-muted);
    }

    .info-input, .info-textarea {
        padding: 7px 10px;
        border-radius: var(--radius);
        border: 1px solid var(--border-hi);
        background: var(--bg-app);
        color: var(--text);
        font-size: 13px;
        box-sizing: border-box;
        width: 100%;
        font-family: inherit;
    }

    .info-input.num {
        text-align: right;
    }

    .info-textarea {
        resize: vertical;
        min-height: 40px;
    }

    .info-save {
        padding: 7px 14px;
        border-radius: var(--radius);
        border: 1px solid var(--accent);
        background: var(--accent);
        color: #fff;
        cursor: pointer;
        font-size: 12px;
        align-self: flex-start;
    }

    .info-save:disabled {
        opacity: .5;
        cursor: default;
    }

    .info-meta {
        margin-top: 14px;
        padding-top: 10px;
        border-top: 1px solid var(--border);
    }

    .bal-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .bal-detail {
        font-size: 11px;
        margin-top: 2px;
    }

    .on-acc {
        color: var(--warn);
    }

</style>
