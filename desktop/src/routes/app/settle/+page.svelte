<script lang="ts">
    import ConfirmDialog from "$lib/components/ConfirmDialog.svelte";
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

    type Kind = "PAYMENT" | "RECEIVED";
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
    type OpenBills = { outstanding_total: number; bills: OpenBill[] };
    type SettlementMode = {
        id: number; name: string; is_system: boolean; is_active: boolean; sort_order: number;
    };

    const today = new Date().toISOString().slice(0, 10);
    let kind = $state<Kind>("PAYMENT");
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

    const companyId = $derived(auth.currentCompany?.id ?? null);
    const endpoint = $derived(kind === "PAYMENT" ? "/api/vouchers/payments/" : "/api/vouchers/received/");
    const canSave = $derived(!!party && !!companyId && Number(amount) > 0 && !saving);
    const allocated = $derived((result?.allocations ?? []).reduce((s, a) => s + (Number(a.amount) || 0), 0));
    const unallocated = $derived(result ? Math.max(0, (Number(result.amount) || 0) - allocated) : 0);
    const modeOptions = $derived(modes.filter((m) => m.is_active).map((m) => ({id: m.id, name: m.name})));

    let confirmOpen = $state(false);

    // Party, positive amount, and a date are the potential fields.
    function isComplete(): boolean {
        return !!party && !!companyId && Number(amount) > 0 && !!date;
    }

    function requestSave() {
        if (!canSave) return;
        confirmOpen = true;
    }

    async function confirmSave() {
        confirmOpen = false;
        await save();
    }

    function closeConfirm() {
        confirmOpen = false;
        // return focus into the flow so shortcuts keep working
        setTimeout(() => (document.getElementById("amount") as HTMLElement | null)?.focus(), 0);
    }


    const flowOpts = $derived({
        // Ctrl+Enter on a complete form: save directly, no dialog.
        onSave: (_opts: { direct: boolean }) => {
            if (canSave) void save();
        },
        isComplete,
        // Plain Enter at the end always opens the confirm dialog.
        onConfirm: () => {
            confirmOpen = true;
        },
    });

    // Live preview: how much of `amount` will settle which open bills (oldest->latest).
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

    function setKind(k: Kind) {
        if (k === kind) return;
        kind = k;
        result = null;
        error = null;
        selectedId = null;
        void loadHistory();
        void loadPreview();
    }

    // User-level settlement modes (Cash/UPI/…). Loaded once; shared by both kinds.
    async function loadModes() {
        try {
            const rows = await request<SettlementMode[] | { results?: SettlementMode[] }>(
                "/api/accounts/settlement-modes/"
            );
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

    // New backend contract: GET /api/vouchers/{payments|received}/open_bills/?party=
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
                    company: companyId,
                    party: party.id,
                    date,
                    amount: Number(amount),
                    mode: modeId,
                    number: null
                }),
            });
            result = {id: res.id, number: res.number, amount: Number(res.amount), allocations: res.allocations ?? []};
            amount = "0";
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
        title: "Settle",
        actions: [
            {id: "set-save", label: "Save", icon: "✓", shortcut: "Ctrl+Enter", run: requestSave},
        ],
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
        <p class="muted">Pick a party to preview open {kind === "PAYMENT" ? "purchases" : "sales"}.</p>
    {:else if loadingPreview}
        <p class="muted">Loading open bills…</p>
    {:else if preview}
        <h3>Open bills · outstanding {Number(preview.outstanding_total).toFixed(2)}</h3>
        {#if preview.bills.length === 0}
            <p class="muted">Nothing outstanding.</p>
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
        <span class="muted">{kind === "PAYMENT" ? "Payments" : "Receipts"}{party ? ` · ${party.name}` : ""}</span>
        <button class="refresh" onclick={loadHistory} disabled={loadingHistory}>{loadingHistory ? "…" : "↻"}</button>
    </div>
    {#if history.length === 0}
        <p class="muted">{loadingHistory ? "Loading…" : "No records."}</p>
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
    <div class="toggle">
        <button class:active={kind === "PAYMENT"} onclick={() => setKind("PAYMENT")}>Payment</button>
        <button class:active={kind === "RECEIVED"} onclick={() => setKind("RECEIVED")}>Received</button>
    </div>
    <p class="sub">{kind === "PAYMENT"
        ? "Pay a vendor. Auto-settles open purchases oldest → latest."
        : "Receive from a customer. Auto-settles open sales oldest → latest."}</p>

    {#if error}
        <div class="banner err">{error}</div>
    {/if}

    <section class="head">
        <div class="field">
            <label for="party">Party</label>
            <SmartLookup flow="party" oncreate={onPartyCreate} onselect={onPartySelect} placeholder="Search or create party…"
                         type="PARTY" value={party}/>
        </div>
        <div class="field amt">
            <label for="amount">Amount</label>
            <input bind:value={amount} class="num" data-flow="amount" id="amount" min="0" step="0.01" type="number"/>
        </div>
        <div class="field mode">
            <label for="mode">Mode</label>
            <LedgerLookup bind:value={modeId} flow="mode" onselect={onModeSelect} options={modeOptions}
                          placeholder="Settlement mode…"/>
        </div>
        <div class="field date">
            <label for="date">Date</label>
            <input bind:value={date} data-flow="date" id="date" type="date"/>
        </div>
    </section>

    <footer class="foot">
        <button class="save" data-flow="save" disabled={!canSave} onclick={requestSave} type="button">
            {saving ? "Saving…" : `Save ${kind === "PAYMENT" ? "payment" : "receipt"}`} <kbd>Ctrl ⏎</kbd>
        </button>
    </footer>
</div>

{#if partyDialog !== null}
    <PartyCreateDialog initialName={partyDialog} oncreated={onPartyCreated} oncancel={() => (partyDialog = null)}/>
{/if}
{#if confirmOpen}
    <ConfirmDialog
            title={kind === "PAYMENT" ? "Confirm payment" : "Confirm receipt"}
            message={`Party: ${party?.name ?? "—"} · Amount ${Number(amount).toFixed(2)}. Auto-settle oldest → latest?`}
            confirmLabel={kind === "PAYMENT" ? "Post payment" : "Post receipt"}
            busy={saving}
            onconfirm={confirmSave}
            oncancel={closeConfirm}/>
{/if}

<style>
    .wrap {
        padding: 20px 28px 40px;
        box-sizing: border-box;
        max-width: 760px;
    }

    .toggle {
        display: inline-flex;
        border: 1px solid var(--border-hi);
        border-radius: var(--radius);
        overflow: hidden;
        margin-bottom: 8px;
    }

    .toggle button {
        padding: 8px 18px;
        background: transparent;
        border: none;
        color: var(--text-muted);
        cursor: pointer;
        font-size: 14px;
    }

    .toggle button.active {
        background: var(--accent);
        color: #fff;
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

    label {
        font-size: 12px;
        color: var(--text-muted);
    }

    .num, input[type="date"] {
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

    /* panels */
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
</style>