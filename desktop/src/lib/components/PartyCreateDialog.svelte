<script lang="ts">
    import {request, type Suggestion} from "$lib/api";
    import {untrack} from "svelte";

    type Props = { initialName: string; oncreated: (p: Suggestion) => void; oncancel: () => void };
    let {initialName, oncreated, oncancel}: Props = $props();

    let name = $state(untrack(() => initialName));
    let phone = $state("");
    let address = $state("");
    let opening = $state("0");
    let busy = $state(false);
    let error = $state<string | null>(null);

    async function save(e: Event) {
        e.preventDefault();
        busy = true;
        error = null;
        try {
            const p = await request<Suggestion>("/api/parties/", {
                method: "POST",
                body: JSON.stringify({
                    name: name.trim(),
                    phone: phone.trim() || null,
                    address: address.trim() || null,
                    opening_balance: Number(opening) || 0,
                }),
            });
            oncreated(p);
        } catch (err) {
            error = err instanceof Error ? err.message : "Could not create party.";
        } finally {
            busy = false;
        }
    }

    function focusOnMount(node: HTMLElement) {
        node.focus();
    }

</script>

<div class="backdrop" role="presentation" onmousedown={oncancel}>
    <form class="dialog" onmousedown={(e) => { if (e.target === e.currentTarget) oncancel(); }} onsubmit={save}>
        <h2>New party</h2>
        <input bind:value={name} placeholder="Name" use:focusOnMount/>
        <input bind:value={phone} placeholder="Phone (optional)"/>
        <input bind:value={address} placeholder="Address (optional)"/>
        <input bind:value={opening} type="number" step="0.01" placeholder="Opening balance"/>
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
        width: 320px;
        padding: 22px;
        background: #171a21;
        border-radius: 12px;
        color: #e6e8ec;
    }

    h2 {
        margin: 0 0 4px;
        font-size: 17px;
    }

    input {
        padding: 9px 11px;
        border-radius: 8px;
        border: 1px solid #2a2f3a;
        background: #0f1115;
        color: #e6e8ec;
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
