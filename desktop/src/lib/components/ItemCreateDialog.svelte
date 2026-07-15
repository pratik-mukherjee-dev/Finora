<script lang="ts">
    import {request, type Suggestion} from "$lib/api";
    import {untrack} from "svelte";

    type Props = {
        initialName: string;
        companyId: number;
        oncreated: (i: Suggestion) => void;
        oncancel: () => void;
    };
    let {initialName, companyId, oncreated, oncancel}: Props = $props();

    // eslint-disable-next-line -- intentional: dialog is mounted once per open
    let name = $state(untrack(() => initialName));

    let baseUnit = $state("PCS");
    let rate = $state("0");
    let openingStock = $state("0");
    let busy = $state(false);
    let error = $state<string | null>(null);

    async function save(e: Event) {
        e.preventDefault();
        busy = true;
        error = null;
        try {
            const item = await request<Suggestion & { id: number }>("/api/catalogue/items/", {
                method: "POST",
                body: JSON.stringify({name: name.trim(), base_unit: baseUnit.trim() || "PCS"}),
            });
            await request("/api/catalogue/mappings/", {
                method: "POST",
                body: JSON.stringify({
                    item: item.id,
                    company: companyId,
                    rate: Number(rate) || 0,
                    opening_stock: Number(openingStock) || 0,
                }),
            });
            oncreated(item);
        } catch (err) {
            error = err instanceof Error ? err.message : "Could not create item.";
        } finally {
            busy = false;
        }
    }

    function focusOnMount(node: HTMLElement) {
        node.focus();
    }

    // Only cancel when the interaction both starts and ends on the backdrop
    // itself. A plain onmousedown on the backdrop also fires while dragging a
    // selection out of an input, and (because mousedown bubbles) closes the
    // dialog on any inner click — so guard on the target and use click.
    function onBackdropClick(e: MouseEvent) {
        if (e.target === e.currentTarget) oncancel();
    }
</script>

<div class="backdrop" role="presentation" onclick={onBackdropClick}>
    <form class="dialog" onsubmit={save}>
        <h2>New item</h2>
        <p class="muted">Mapped to current company.</p>
        <input bind:value={name} placeholder="Item name" use:focusOnMount/>
        <input bind:value={baseUnit} placeholder="Base unit (e.g. PCS)"/>
        <div class="grid">
            <input bind:value={rate} type="number" step="0.01" placeholder="Rate"/>
            <input bind:value={openingStock} type="number" step="0.01" placeholder="Opening stock"/>
        </div>
        {#if error}<p class="err">{error}</p>{/if}
        <div class="row">
            <button type="button" class="ghost" onclick={oncancel}>Cancel</button>
            <button disabled={busy || !name.trim()}>{busy ? "Saving…" : "Create"}</button>
        </div>
    </form>
</div>

<style>
    .backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, .55);
        display: grid;
        place-items: center;
        z-index: 50;
    }

    .dialog {
        display: flex;
        flex-direction: column;
        gap: 10px;
        width: 340px;
        padding: 22px;
        background: #171a21;
        border-radius: 12px;
        color: #e6e8ec;
    }

    h2 {
        margin: 0;
        font-size: 17px;
    }

    .muted {
        color: #9aa0aa;
        font-size: 12px;
        margin: 0;
    }

    input {
        padding: 9px 11px;
        border-radius: 8px;
        border: 1px solid #2a2f3a;
        background: #0f1115;
        color: #e6e8ec;
    }

    .grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
    }

    .row {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        margin-top: 4px;
    }

    button {
        padding: 8px 14px;
        border-radius: 8px;
        border: 1px solid #2f6feb;
        background: #2f6feb;
        color: #fff;
        cursor: pointer;
    }

    button.ghost {
        background: transparent;
        border-color: #2a2f3a;
    }

    button:disabled {
        opacity: .5;
        cursor: default;
    }

    .err {
        color: #ff6b6b;
        font-size: 13px;
        margin: 0;
    }
</style>
