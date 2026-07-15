<script lang="ts">
    import {auth} from "$lib/stores/auth.svelte";
    import {goto} from "$app/navigation";
    import {onMount} from "svelte";
    import {request, type Suggestion} from "$lib/api";
    import SmartLookup from "$lib/components/SmartLookup.svelte";
    import PartyCreateDialog from "$lib/components/PartyCreateDialog.svelte";

    onMount(() => {
        if (!auth.isAuthed) return void goto("/login");
        if (auth.needsSetup) return void goto("/setup");
        if (auth.needsFy) return void goto("/fy");
        void loadHistory();
    });

    type Kind = "PAYMENT" | "RECEIVED";

    type Allocation = {
        id: number; bill_type: string; bill_id: number;
        bill_number: string | null; bill_date: string | null;
        bill_total: number | null; amount: number;
    };
    type SettleResult = {
        id: number; number: string; amount: number; allocations: Allocation[];
    };
    type Voucher = {
        id: number; party: number; party_name: string;
        number: string; date: string; amount: number; is_cancelled: boolean;
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

    let partyDialog = $state<string | null>(null);

    const companyId = $derived(auth.currentCompany?.id ?? null);
    const endpoint = $derived(
        kind === "PAYMENT" ? "/api/vouchers/payments/" : "/api/vouchers/received/"
    );
    const canSave = $derived(!!party && !!companyId && Number(amount) > 0 && !saving);

    const allocated = $derived(
        (result?.allocations ?? []).reduce((s, a) => s + (Number(a.amount) || 0), 0)
    );
    const unallocated = $derived(
        result ? Math.max(0, (Number(result.amount) || 0) - allocated) : 0
    );

    function onPartySelect(s: Suggestion) {
        party = s;
        void loadHistory();
    }

    function onPartyCreate(typed: string) {
        partyDialog = typed;
    }

    function onPartyCreated(p: Suggestion) {
        party = p;
        partyDialog = null;
        void loadHistory();
    }

    function setKind(k: Kind) {
        if (k === kind) return;
        kind = k;
        result = null;
        error = null;
        selectedId = null;
        void loadHistory();
    }

    async function loadHistory() {
        if (!companyId) return;
        loadingHistory = true;
        try {
            const p = new URLSearchParams({company: String(companyId)});
            if (party) p.set("party", String(party.id));
            const rows = await request<Voucher[] | { results?: Voucher[] }>(
                `${endpoint}?${p.toString()}`
            );
            history = Array.isArray(rows) ? rows : (rows?.results ?? []);
        } catch (e) {
            history = [];
        } finally {
            loadingHistory = false;
        }
    }

    async function viewVoucher(v: Voucher) {
        selectedId = v.id;
        error = null;
        try {
            const allocs = await request<Allocation[]>(`${endpoint}${v.id}/allocations/`);
            result = {
                id: v.id, number: v.number, amount: Number(v.amount),
                allocations: allocs ?? [],
            };
        } catch (e) {
            error = e instanceof Error ? e.message : "Could not load allocations.";
        }
    }

    async function save() {
        if (!party || !companyId) return;
        saving = true;
        error = null;
        result = null;
        selectedId = null;
        try {
            const res = await request<SettleResult>(endpoint, {
                method: "POST",
                body: JSON.stringify({
                    company: companyId, party: party.id, date,
                    amount: Number(amount), number: null,
                }),
            });
            result = {
                id: res.id, number: res.number, amount: Number(res.amount),
                allocations: res.allocations ?? [],
            };
            amount = "0";
            await loadHistory();
        } catch (e) {
            error = e instanceof Error ? e.message : "Could not save.";
        } finally {
            saving = false;
        }
    }
</script>

<div class="page">
    <div class="wrap">
        <header class="bar">
            <button class="back" onclick={ () => goto("/app") }>← Home</button>
            <h1>{kind === "PAYMENT" ? "Payment" : "Received"}</h1>
            <div class="ctx"><span class="chip">{auth.currentCompany?.name ?? "—"}</span></div>
        </header>

        <div class="toggle">
            <button class:active={kind === "PAYMENT"} onclick={() => setKind("PAYMENT")}>Payment</button>
            <button class:active={kind === "RECEIVED"} onclick={() => setKind("RECEIVED")}>Received</button>
        </div>
        <p class="sub">
            {kind === "PAYMENT"
                ? "Pay a vendor. Auto-settles open purchases oldest → latest."
                : "Receive from a customer. Auto-settles open sales oldest → latest."}
        </p>

        {#if error}
            <div class="banner err">{error}</div>
        {/if}

        <section class="head">
            <div class="field">
                <label for="party">Party</label>
                <SmartLookup type="PARTY" placeholder="Search or create party…"
                             value={party} onselect={onPartySelect} oncreate={onPartyCreate}/>
            </div>
            <div class="field amt">
                <label for="amount">Amount</label>
                <input id="amount" class="num" type="number" min="0" step="0.01" bind:value={amount}/>
            </div>
            <div class="field date">
                <label for="date">Date</label>
                <input id="date" type="date" bind:value={date}/>
            </div>
        </section>

        <footer class="foot">
            <button class="save" disabled={ !canSave } onclick={ save }>
                {saving ? "Saving…" : `Save ${kind === "PAYMENT" ? "payment" : "receipt"}`}
            </button>
        </footer>

        {#if result}
            <section class="result">
                <div class="banner ok">
                    <strong>#{result.number}</strong> · amount <strong>{result.amount.toFixed(2)}</strong>
                </div>
                <h2>Allocation</h2>
                {#if result.allocations.length === 0}
                    <p class="muted">
                        No open {kind === "PAYMENT" ? "purchases" : "sales"} settled.
                        Amount kept on account.
                    </p>
                {:else}
                    <div class="alloc">
                        <div class="ahead">
                            <span>Bill</span><span>Date</span><span>Bill total</span><span>Settled</span>
                        </div>
                        {#each result.allocations as a (a.id)}
                            <div class="arow">
                                <span>#{a.bill_number ?? a.bill_id}</span>
                                <span>{a.bill_date ?? "—"}</span>
                                <span class="rt">{a.bill_total != null ? Number(a.bill_total).toFixed(2) : "—"}</span>
                                <span class="rt">{Number(a.amount).toFixed(2)}</span>
                            </div>
                        {/each}
                    </div>
                    <div class="summary">
                        <span>Allocated <strong>{allocated.toFixed(2)}</strong></span>
                        {#if unallocated > 0}
                            <span class="adv">On account <strong>{unallocated.toFixed(2)}</strong></span>
                        {/if}
                    </div>
                {/if}
            </section>
        {/if}
    </div>

    <aside class="side">
        <div class="sidehead">
            <h2>{kind === "PAYMENT" ? "Payments" : "Receipts"}{party ? ` · ${party.name}` : ""}</h2>
            <button class="refresh" onclick={loadHistory} disabled={loadingHistory}>
                {loadingHistory ? "…" : "↻"}
            </button>
        </div>
        {#if history.length === 0}
            <p class="muted">{loadingHistory ? "Loading…" : "No records."}</p>
        {:else}
            <ul class="hlist">
                {#each history as v (v.id)}
                    <li class:cancelled={v.is_cancelled} class:active={v.id === selectedId}>
                        <button class="hrow" onclick={() => viewVoucher(v)}>
                            <div class="hline1">
                                <span class="hnum">#{v.number}</span>
                                <span class="htot">{Number(v.amount).toFixed(2)}</span>
                            </div>
                            <div class="hline2">
                                <span>{v.party_name}</span>
                                <span class="hdate">{v.date}</span>
                            </div>
                            {#if v.is_cancelled}<span class="badge">cancelled</span>{/if}
                        </button>
                    </li>
                {/each}
            </ul>
        {/if}
    </aside>
</div>

{#if partyDialog !== null}
    <PartyCreateDialog initialName={ partyDialog } oncreated={ onPartyCreated }
                       oncancel={ () => (partyDialog = null) }/>
{/if}

<style>
    :global(body) {
        margin: 0;
    }

    .page {
        display: grid;
        grid-template-columns: 1fr 300px;
        min-height: 100vh;
        background: #0f1115;
        color: #e6e8ec;
        font-family: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif;
    }

    .wrap {
        padding: 20px 28px 40px;
        box-sizing: border-box;
        min-width: 0;
    }

    .bar {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 16px;
    }

    .back {
        background: transparent;
        border: 1px solid #2a2f3a;
        color: #c3c8d2;
        padding: 6px 12px;
        border-radius: 8px;
        cursor: pointer;
        font-size: 13px;
    }

    .back:hover {
        border-color: #6ea8ff;
        color: #6ea8ff;
    }

    h1 {
        margin: 0;
        font-size: 22px;
    }

    .ctx {
        margin-left: auto;
    }

    .chip {
        padding: 4px 12px;
        border-radius: 999px;
        background: #16233b;
        color: #6ea8ff;
        font-size: 12px;
        font-weight: 600;
    }

    .toggle {
        display: inline-flex;
        border: 1px solid #2a2f3a;
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 8px;
    }

    .toggle button {
        padding: 8px 18px;
        background: transparent;
        border: none;
        color: #9aa0aa;
        cursor: pointer;
        font-size: 14px;
    }

    .toggle button.active {
        background: #2f6feb;
        color: #fff;
    }

    .sub {
        color: #9aa0aa;
        font-size: 13px;
        margin: 0 0 18px;
    }

    .banner {
        padding: 10px 14px;
        border-radius: 8px;
        margin-bottom: 16px;
        font-size: 14px;
    }

    .banner.ok {
        background: #13291d;
        color: #6ee7a8;
        border: 1px solid #1f5138;
    }

    .banner.err {
        background: #2a1517;
        color: #ff9b9b;
        border: 1px solid #5a2a2e;
    }

    .head {
        display: flex;
        gap: 18px;
        margin-bottom: 20px;
        max-width: 720px;
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

    .field.date {
        max-width: 180px;
    }

    label {
        font-size: 12px;
        color: #9aa0aa;
    }

    .num, input[type="date"] {
        padding: 8px 10px;
        border-radius: 8px;
        border: 1px solid #2a2f3a;
        background: #0f1115;
        color: #e6e8ec;
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
        margin-bottom: 24px;
        max-width: 720px;
    }

    .save {
        padding: 10px 20px;
        border-radius: 8px;
        border: 1px solid #2f6feb;
        background: #2f6feb;
        color: #fff;
        font-size: 14px;
        cursor: pointer;
    }

    .save:disabled {
        opacity: .5;
        cursor: default;
    }

    .result {
        max-width: 720px;
    }

    h2 {
        font-size: 16px;
        margin: 8px 0 12px;
    }

    .muted {
        color: #9aa0aa;
        font-size: 14px;
    }

    .alloc {
        border: 1px solid #1f2530;
        border-radius: 10px;
        overflow: hidden;
        background: #12151c;
    }

    .ahead, .arow {
        display: grid;
        grid-template-columns: 1fr 130px 140px 140px;
        gap: 12px;
        padding: 10px 14px;
        font-size: 14px;
    }

    .ahead {
        color: #9aa0aa;
        font-size: 12px;
        border-bottom: 1px solid #1f2530;
    }

    .arow {
        border-bottom: 1px solid #171b23;
    }

    .rt {
        text-align: right;
    }

    .summary {
        display: flex;
        justify-content: flex-end;
        gap: 24px;
        margin-top: 14px;
        font-size: 14px;
        color: #c3c8d2;
    }

    .adv {
        color: #ffc15c;
    }

    /* History panel */
    .side {
        border-left: 1px solid #1f2530;
        background: #12151c;
        padding: 18px 14px;
        overflow: auto;
    }

    .sidehead {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 10px;
        gap: 8px;
    }

    .side h2 {
        font-size: 14px;
        margin: 0;
    }

    .refresh {
        background: transparent;
        border: 1px solid #2a2f3a;
        color: #9aa0aa;
        width: 28px;
        height: 28px;
        border-radius: 6px;
        cursor: pointer;
        flex-shrink: 0;
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
        background: #0f1115;
        border: 1px solid #1f2530;
        border-radius: 8px;
        padding: 8px 10px;
        cursor: pointer;
        color: #e6e8ec;
    }

    .hrow:hover {
        border-color: #34406b;
    }

    li.active .hrow {
        border-color: #2f6feb;
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
        color: #6ee7a8;
    }

    .hline2 {
        display: flex;
        justify-content: space-between;
        font-size: 11px;
        color: #9aa0aa;
        margin-top: 2px;
    }

    .badge {
        position: absolute;
        top: 6px;
        right: 8px;
        font-size: 9px;
        text-transform: uppercase;
        color: #ff9b9b;
        background: #2a1517;
        padding: 1px 5px;
        border-radius: 4px;
    }
</style>
