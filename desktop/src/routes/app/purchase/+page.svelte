<script lang="ts">
    import {auth} from "$lib/stores/auth.svelte";
    import {goto} from "$app/navigation";
    import {onMount} from "svelte";
    import {request, type Suggestion} from "$lib/api";
    import SmartLookup from "$lib/components/SmartLookup.svelte";
    import PartyCreateDialog from "$lib/components/PartyCreateDialog.svelte";
    import ItemCreateDialog from "$lib/components/ItemCreateDialog.svelte";

    onMount(() => {
        if (!auth.isAuthed) return void goto("/login");
        if (auth.needsSetup) return void goto("/setup");
        if (auth.needsFy) return void goto("/fy");
        void loadHistory();
    });

    type Mapping = {
        id: number; item: number; item_name: string;
        company: number; rate: number; stock: number;
    };

    type Line = {
        key: number;
        item: Suggestion | null;
        mapping: number | null;
        qty: string;
        rate: string;
        amount: string;
        resolving: boolean;
        note: string;
        noMapping: boolean;
        creatingMapping: boolean;
    };

    type PurchaseLine = {
        id: number; item: number; item_name: string;
        mapping: number; qty: number; rate: number; amount: number;
    };
    type Purchase = {
        id: number; company: number; party: number; party_name: string;
        number: string; date: string; total_amount: number;
        is_cancelled: boolean; lines: PurchaseLine[];
    };

    let seq = 0;
    const newLine = (): Line => ({
        key: ++seq, item: null, mapping: null, qty: "1", rate: "0",
        amount: "0.00", resolving: false, note: "", noMapping: false,
        creatingMapping: false,
    });

    const today = new Date().toISOString().slice(0, 10);
    let party = $state<Suggestion | null>(null);
    let date = $state(today);
    let lines = $state<Line[]>([newLine()]);

    let saving = $state(false);
    let error = $state<string | null>(null);
    let saved = $state<{ number: string; total_amount: number } | null>(null);

    // History + edit state
    let history = $state<Purchase[]>([]);
    let loadingHistory = $state(false);
    let editingId = $state<number | null>(null);   // purchase being edited (will be cancelled on save)

    let partyDialog = $state<string | null>(null);
    let itemDialog = $state<{ text: string; lineKey: number } | null>(null);

    const companyId = $derived(auth.currentCompany?.id ?? null);

    const total = $derived(
        lines.reduce((sum, l) => sum + (Number(l.amount) || 0), 0)
    );
    const canSave = $derived(
        !!party && !!companyId &&
        lines.some((l) => l.mapping && Number(l.qty) > 0) && !saving
    );

    const round2 = (n: number) => (Math.round(n * 100) / 100).toFixed(2);

    function onQtyOrRate(line: Line) {
        line.amount = round2((Number(line.qty) || 0) * (Number(line.rate) || 0));
    }

    function onAmount(line: Line) {
        const qty = Number(line.qty) || 0;
        line.rate = qty > 0 ? round2((Number(line.amount) || 0) / qty) : "0";
    }

    // ---- History ----
    async function loadHistory() {
        if (!companyId) return;
        loadingHistory = true;
        try {
            const p = new URLSearchParams({company: String(companyId)});
            const rows = await request<Purchase[] | { results?: Purchase[] }>(
                `/api/vouchers/purchases/?${p.toString()}`
            );
            history = Array.isArray(rows) ? rows : (rows?.results ?? []);
        } catch (e) {
            // non-fatal; leave history empty
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
        // Load party (id + name is enough for the payload).
        party = {id: prow.party, name: prow.party_name};
        date = prow.date;
        lines = prow.lines.map((pl) => ({
            key: ++seq,
            item: {id: pl.item, name: pl.item_name},
            mapping: pl.mapping,
            qty: String(pl.qty),
            rate: String(pl.rate),
            amount: round2(Number(pl.qty) * Number(pl.rate)),
            resolving: false, note: "", noMapping: false, creatingMapping: false,
        }));
        if (lines.length === 0) lines = [newLine()];
    }

    function cancelEdit() {
        editingId = null;
        party = null;
        date = today;
        lines = [newLine()];
        error = null;
        saved = null;
    }

    // ---- Party ----
    function onPartySelect(s: Suggestion) {
        party = s;
    }

    function onPartyCreate(typed: string) {
        partyDialog = typed;
    }

    function onPartyCreated(p: Suggestion) {
        party = p;
        partyDialog = null;
    }

    // ---- Item -> mapping ----
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

    function onItemCreate(line: Line, typed: string) {
        itemDialog = {text: typed, lineKey: line.key};
    }

    function onItemCreated(i: Suggestion) {
        const target = lines.find((l) => l.key === itemDialog?.lineKey);
        itemDialog = null;
        if (target) {
            target.item = i;
            void resolveMapping(target, i.id);
        }
    }

    function addLine() {
        lines = [...lines, newLine()];
    }

    function removeLine(key: number) {
        lines = lines.length > 1 ? lines.filter((l) => l.key !== key) : lines;
    }

    async function save() {
        if (!party || !companyId) return;
        saving = true;
        error = null;
        saved = null;
        try {
            const payloadLines = lines
                .filter((l) => l.mapping && Number(l.qty) > 0)
                .map((l) => ({mapping: l.mapping, qty: Number(l.qty), rate: Number(l.rate) || 0}));
            if (payloadLines.length === 0) {
                error = "Add at least one item with a quantity.";
                return;
            }
            // Editing an existing purchase => cancel the original first (soft-cancel + reversals).
            if (editingId != null) {
                await request(`/api/vouchers/purchases/${editingId}/cancel/`, {method: "POST"});
            }
            const res = await request<{ number: string; total_amount: number }>(
                "/api/vouchers/purchases/",
                {
                    method: "POST",
                    body: JSON.stringify({
                        company: companyId, party: party.id, date,
                        number: null, lines: payloadLines,
                    }),
                }
            );
            saved = {number: res.number, total_amount: res.total_amount};
            editingId = null;
            lines = [newLine()];
            await loadHistory();
        } catch (e) {
            error = e instanceof Error ? e.message : "Could not save purchase.";
        } finally {
            saving = false;
        }
    }
</script>

<div class="page">
    <div class="wrap">
        <header class="bar">
            <button class="back" onclick={ () => goto("/app") }>← Home</button>
            <h1>Purchase</h1>
            <div class="ctx"><span class="chip">{auth.currentCompany?.name ?? "—"}</span></div>
        </header>

        {#if editingId != null}
            <div class="banner edit">
                Editing purchase — saving will <strong>cancel the original</strong> and create a
                replacement.
                <button class="linkbtn" onclick={cancelEdit}>Discard</button>
            </div>
        {/if}
        {#if saved}
            <div class="banner ok">
                Saved purchase <strong>#{ saved.number }</strong> · total
                <strong>{saved.total_amount}</strong>.
            </div>
        {/if}
        {#if error}
            <div class="banner err">{error}</div>
        {/if}

        <section class="head">
            <div class="field">
                <label for="party">Party</label>
                <SmartLookup type="PARTY" placeholder="Search or create party…"
                             value={party} onselect={onPartySelect} oncreate={onPartyCreate}/>
            </div>
            <div class="field date">
                <label for="date">Date</label>
                <input id="date" type="date" bind:value={date}/>
            </div>
        </section>

        <section class="grid">
            <div class="ghead">
                <span>Item</span><span>Qty</span><span>Rate</span><span>Amount</span><span></span>
            </div>

            {#each lines as line (line.key)}
                <div class="grow">
                    <div class="cell item">
                        <SmartLookup type="ITEM" placeholder="Search or create item…"
                                     value={line.item}
                                     onselect={(s) => onItemSelect(line, s)}
                                     oncreate={(t) => onItemCreate(line, t)}/>
                        {#if line.resolving}
                            <span class="hint">Resolving mapping…</span>
                        {:else if line.noMapping}
                            <span class="hint warn">{line.note}
                                <button class="linkbtn" disabled={line.creatingMapping}
                                        onclick={() => createMapping(line)}>
                                    {line.creatingMapping ? "Creating…" : "Create mapping"}</button>
                            </span>
                        {:else if line.note}
                            <span class="hint warn">{line.note}</span>
                        {/if}
                    </div>
                    <div class="qtycell">
                        <input class="num" type="number" min="0" step="0.001"
                               bind:value={ line.qty } oninput={() => onQtyOrRate(line)}/>
                        {#if line.item?.base_unit}<span class="unit">{line.item.base_unit}</span>{/if}
                    </div>
                    <input class="num" type="number" min="0" step="0.01"
                           bind:value={ line.rate } oninput={() => onQtyOrRate(line)}/>
                    <input class="num" type="number" min="0" step="0.01"
                           bind:value={ line.amount } oninput={() => onAmount(line)}/>
                    <button class="del" title="Remove line" onclick={ () => removeLine(line.key) }>✕</button>
                </div>
            {/each}

            <button class="addline" onclick={ addLine }>+ Add line</button>
        </section>

        <footer class="foot">
            <div class="total">Total <strong>{total.toFixed(2)}</strong></div>
            <button class="save" disabled={ !canSave } onclick={ save }>
                {saving ? "Saving…" : (editingId != null ? "Save changes" : "Save purchase")}
            </button>
        </footer>
    </div>

    <aside class="side">
        <div class="sidehead">
            <h2>History</h2>
            <button class="refresh" onclick={loadHistory} disabled={loadingHistory}>
                {loadingHistory ? "…" : "↻"}
            </button>
        </div>
        {#if history.length === 0}
            <p class="muted">{loadingHistory ? "Loading…" : "No purchases yet."}</p>
        {:else}
            <ul class="hlist">
                {#each history as h (h.id)}
                    <li class:cancelled={h.is_cancelled} class:active={h.id === editingId}>
                        <button class="hrow" disabled={h.is_cancelled} onclick={() => openForEdit(h)}>
                            <div class="hline1">
                                <span class="hnum">#{h.number}</span>
                                <span class="htot">{Number(h.total_amount).toFixed(2)}</span>
                            </div>
                            <div class="hline2">
                                <span>{h.party_name}</span>
                                <span class="hdate">{h.date}</span>
                            </div>
                            {#if h.is_cancelled}<span class="badge">cancelled</span>{/if}
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
{#if itemDialog !== null && companyId}
    <ItemCreateDialog initialName={ itemDialog.text } companyId={ companyId }
                      oncreated={ onItemCreated } oncancel={ () => (itemDialog = null) }/>
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
        margin-bottom: 20px;
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

    .banner.edit {
        background: #1d2233;
        color: #b9c6ff;
        border: 1px solid #34406b;
        display: flex;
        align-items: center;
        gap: 10px;
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
        color: #9aa0aa;
    }

    input[type="date"] {
        padding: 8px 10px;
        border-radius: 8px;
        border: 1px solid #2a2f3a;
        background: #0f1115;
        color: #e6e8ec;
        font-size: 14px;
    }

    .grid {
        border: 1px solid #1f2530;
        border-radius: 10px;
        overflow: visible;
        background: #12151c;
    }

    .ghead, .grow {
        display: grid;
        grid-template-columns: 1fr 130px 110px 120px 40px;
        gap: 12px;
        align-items: start;
        padding: 12px 14px;
    }

    .ghead {
        color: #9aa0aa;
        font-size: 12px;
        border-bottom: 1px solid #1f2530;
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
        color: #9aa0aa;
        display: flex;
        align-items: center;
        gap: 6px;
        flex-wrap: wrap;
    }

    .hint.warn {
        color: #ffc15c;
    }

    .linkbtn {
        background: transparent;
        border: 1px solid #2f6feb;
        color: #6ea8ff;
        padding: 2px 8px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 11px;
    }

    .linkbtn:hover:not(:disabled) {
        background: #16233b;
    }

    .linkbtn:disabled {
        opacity: .5;
        cursor: default;
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
        color: #9aa0aa;
        white-space: nowrap;
    }

    .num {
        padding: 8px 10px;
        border-radius: 8px;
        border: 1px solid #2a2f3a;
        background: #0f1115;
        color: #e6e8ec;
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
        font-size: 14px;
    }

    .del:hover {
        color: #ff6b6b;
    }

    .addline {
        width: 100%;
        padding: 10px;
        background: transparent;
        border: none;
        color: #6ea8ff;
        cursor: pointer;
        font-size: 14px;
        text-align: left;
    }

    .addline:hover {
        background: #16233b;
    }

    .foot {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 24px;
        margin-top: 20px;
    }

    .total {
        font-size: 15px;
        color: #c3c8d2;
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
    }

    .side h2 {
        font-size: 15px;
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
    }

    .muted {
        color: #9aa0aa;
        font-size: 13px;
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

    .hrow:hover:not(:disabled) {
        border-color: #34406b;
    }

    .hrow:disabled {
        cursor: default;
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
