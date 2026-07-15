<script lang="ts">
    import {auth} from "$lib/stores/auth.svelte";
    import {goto} from "$app/navigation";
    import {onMount} from "svelte";
    import {request, type Suggestion} from "$lib/api";
    import SmartLookup from "$lib/components/SmartLookup.svelte";
    import PartyCreateDialog from "$lib/components/PartyCreateDialog.svelte";
    import ItemCreateDialog from "$lib/components/ItemCreateDialog.svelte";

    // ---- Route guard: same prerequisites as the app shell. ----
    onMount(() => {
        if (!auth.isAuthed) return void goto("/login");
        if (auth.needsSetup) return void goto("/setup");
        if (auth.needsFy) return void goto("/fy");
    });

    type Mapping = {
        id: number;
        item: number;
        item_name: string;
        company: number;
        rate: number;
        stock: number;
    };

    type Line = {
        key: number;
        item: Suggestion | null;
        mapping: number | null;
        qty: string;
        rate: string;
        resolving: boolean;
        note: string; // e.g. "no mapping — create item"
    };

    let seq = 0;
    const newLine = (): Line => ({
        key: ++seq,
        item: null,
        mapping: null,
        qty: "1",
        rate: "0",
        resolving: false,
        note: "",
    });

    // ---- Voucher-level state ----
    const today = new Date().toISOString().slice(0, 10);
    let party = $state<Suggestion | null>(null);
    let date = $state(today);
    let lines = $state<Line[]>([newLine()]);

    let saving = $state(false);
    let error = $state<string | null>(null);
    let saved = $state<{ number: string; total_amount: number } | null>(null);

    // ---- Create-dialog state ----
    let partyDialog = $state<string | null>(null);          // typed text or null
    let itemDialog = $state<{ text: string; lineKey: number } | null>(null);

    const companyId = $derived(auth.currentCompany?.id ?? null);

    const total = $derived(
        lines.reduce((sum, l) => sum + (Number(l.qty) || 0) * (Number(l.rate) || 0), 0)
    );

    const canSave = $derived(
        !!party &&
        !!companyId &&
        lines.some((l) => l.mapping && Number(l.qty) > 0) &&
        !saving
    );

    // ---- Party lookup handlers ----
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

    // ---- Item lookup: resolve item -> per-company mapping ----
    async function resolveMapping(line: Line, itemId: number) {
        if (!companyId) return;
        line.resolving = true;
        line.note = "";
        try {
            const params = new URLSearchParams({
                item: String(itemId),
                company: String(companyId),
            });
            const rows = await request<Mapping[]>(
                `/api/catalogue/mappings/?${params.toString()}`
            );
            const list = Array.isArray(rows)
                ? rows
                : ((rows as { results?: Mapping[] })?.results ?? []);
            if (list.length > 0) {
                line.mapping = list[0].id;
                line.rate = String(list[0].rate ?? 0);
            } else {
                // Item exists but has no mapping for the current company.
                line.mapping = null;
                line.note = "No mapping for this company — recreate via + Create.";
            }
        } catch (e) {
            line.note = e instanceof Error ? e.message : "Failed to resolve mapping.";
        } finally {
            line.resolving = false;
        }
    }

    function onItemSelect(line: Line, s: Suggestion) {
        line.item = s;
        line.mapping = null;
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
            // The dialog just created item + mapping for the current company; resolve it.
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
                .map((l) => ({
                    mapping: l.mapping,
                    qty: Number(l.qty),
                    rate: Number(l.rate) || 0,
                }));
            if (payloadLines.length === 0) {
                error = "Add at least one item with a quantity.";
                return;
            }
            const res = await request<{ number: string; total_amount: number }>(
                "/api/vouchers/purchases/",
                {
                    method: "POST",
                    body: JSON.stringify({
                        company: companyId,
                        party: party.id,
                        date,
                        number: null,
                        lines: payloadLines,
                    }),
                }
            );
            saved = {number: res.number, total_amount: res.total_amount};
            // Reset for the next entry, keep party/date for fast repeat.
            lines = [newLine()];
        } catch (e) {
            error = e instanceof Error ? e.message : "Could not save purchase.";
        } finally {
            saving = false;
        }
    }
</script>

<div class="wrap">
    <header class="bar">
        <button class="back" onclick={ () => goto("/app") }>← Home</button>
        <h1>Purchase</h1>
        <div class="ctx">
            <span class="chip">{auth.currentCompany?.name ?? "—"}</span>
        </div>
    </header>

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
            <SmartLookup
                    type="PARTY"
                    placeholder="Search or create party…"
                    value={party}
                    onselect={onPartySelect}
                    oncreate={onPartyCreate}
            />
        </div>
        <div class="field date">
            <label for="date">Date</label>
            <input id="date" type="date" bind:value={date}/>
        </div>
    </section>


    <section class="grid">
        <div class="ghead">
            <span>Item</span>
            <span>Qty</span>
            <span>Rate</span>
            <span>Amount</span>
            <span></span>
        </div>

        {#each lines as line (line.key)}
            <div class="grow">
                <div class="cell item">
                    <SmartLookup
                            type="ITEM"
                            placeholder="Search or create item…"
                            value={line.item}
                            onselect={(s) => onItemSelect(line, s)}
                            oncreate={(t) => onItemCreate(line, t)}
                    />

                    {#if line.resolving}
                        <span class="hint">Resolving mapping…</span>
                    {:else if line.note}
                        <span class="hint warn">{line.note}</span>
                    {/if}
                </div>
                <input class="num" type="number" min="0" step="0.01" bind:value={ line.qty }/>
                <input class="num" type="number" min="0" step="0.01" bind:value={ line.rate }/>
                <span class="amount">
            {((Number(line.qty) || 0) * (Number(line.rate) || 0)).toFixed(2)}
            </span>
                <button class="del" title="Remove line" onclick={ () => removeLine(line.key) }>✕</button>
            </div>
        {/each}

        <button class="addline" onclick={ addLine }>+ Add line</button>
    </section>

    <footer class="foot">
        <div class="total">Total <strong>{total.toFixed(2)}</strong></div>
        <button class="save" disabled={ !canSave } onclick={ save }>
            {saving ? "Saving…" : "Save purchase"}
        </button>
    </footer>
</div>

{#if partyDialog !== null}
    <PartyCreateDialog
            initialName={ partyDialog }
            oncreated={ onPartyCreated }
            oncancel={ () => (partyDialog = null) }
    />
{/if}

{#if itemDialog !== null && companyId}
    <ItemCreateDialog
            initialName={ itemDialog.text }
            companyId={ companyId }
            oncreated={ onItemCreated }
            oncancel={ () => (itemDialog = null) }
    />
{/if}

<style>
    :global(body) {
        margin: 0;
    }

    .wrap {
        min-height: 100vh;
        background: #0f1115;
        color: #e6e8ec;
        font-family: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif;
        padding: 20px 28px 40px;
        box-sizing: border-box;
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
        grid-template-columns: 1fr 110px 110px 120px 40px;
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
    }

    .hint.warn {
        color: #ffc15c;
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

    .amount {
        align-self: center;
        text-align: right;
        font-size: 14px;
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
</style>
