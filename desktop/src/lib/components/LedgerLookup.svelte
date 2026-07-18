<script lang="ts">
    type Option = { id: number; name: string };

    type Props = {
        options: Option[];
        value?: number | null;
        placeholder?: string;
        flow?: string;
        onselect: (id: number) => void;
        onenter?: () => void;   // fired after a pick, to continue the enter-flow
        onemptyenter?: () => void;
    };
    let {options, value = $bindable(null), placeholder = "Select charge…", flow, onselect, onenter, onemptyenter}: Props = $props();

    let inputEl: HTMLInputElement | null = $state(null);

    export function focus() {
        inputEl?.focus();
        inputEl?.select();
    }

    // Show the picked option's name; typing filters the list.
    const selectedName = $derived(options.find((o) => o.id === value)?.name ?? "");
    let q = $state("");
    let dirty = $state(false);          // true once the user types
    let open = $state(false);
    let active = $state(0);

    const shown = $derived(dirty ? (q.trim() === "" ? "" : q) : selectedName);
    const filtered = $derived.by(() => {
        const term = q.trim().toLowerCase();
        if (!dirty || term === "") return options;
        return options.filter((o) => o.name.toLowerCase().includes(term));
    });

    function pick(o: Option) {
        value = o.id;
        q = o.name;
        dirty = false;
        open = false;
        onselect(o.id);
        onenter?.();
    }

    function onInput(e: Event) {
        q = (e.target as HTMLInputElement).value;
        dirty = true;
        open = true;
        active = 0;
    }

    function onKey(e: KeyboardEvent) {
        if (e.key === "Enter" && !open) {
            e.preventDefault();
            e.stopImmediatePropagation();     // don't let the flow root also act
            if (value != null) onenter?.();
            else onemptyenter?.();
            return;
        }

        if (!open) return;
        if (e.key === "ArrowDown") {
            active = Math.min(active + 1, filtered.length - 1);
            e.preventDefault();
        } else if (e.key === "ArrowUp") {
            active = Math.max(active - 1, 0);
            e.preventDefault();
        } else if (e.key === "Enter") {
            e.preventDefault();
            e.stopImmediatePropagation();
            if (filtered[active]) pick(filtered[active]);
        } else if (e.key === "Escape") {
            open = false;
        }
    }
</script>

<div class="lookup">
    <input
            bind:this={inputEl}
            autocomplete="off"
            data-flow={flow}
            data-flow-skip={open ? "1" : undefined}
            onblur={() => setTimeout(() => { open = false; dirty = false; }, 120)}
            onfocus={() => { open = true; active = 0; }}
            oninput={onInput}
            onkeydown={onKey}
            {placeholder}
            value={shown}
    />
    {#if open}
        <ul class="menu" role="listbox">
            {#each filtered as o, i (o.id)}
                <li role="option" aria-selected={i === active} tabindex="-1"
                    class:active={i === active} onmousedown={() => pick(o)}>{o.name}</li>
            {/each}
            {#if filtered.length === 0}
                <li class="empty">No charges</li>
            {/if}
        </ul>
    {/if}
</div>

<style>
    .lookup {
        position: relative;
    }

    input {
        width: 100%;
        padding: 8px 10px;
        border-radius: 8px;
        border: 1px solid #2a2f3a;
        background: #0f1115;
        color: #e6e8ec;
        font-size: 13px;
        box-sizing: border-box;
    }

    .menu {
        position: absolute;
        z-index: 20;
        left: 0;
        right: 0;
        margin: 4px 0 0;
        padding: 4px;
        list-style: none;
        background: #171a21;
        border: 1px solid #2a2f3a;
        border-radius: 8px;
        max-height: 240px;
        overflow-y: auto;
    }

    .menu li {
        padding: 8px 10px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 14px;
    }

    .menu li.active, .menu li:hover {
        background: #1f2530;
    }

    .menu li.empty {
        color: #9aa0aa;
        cursor: default;
    }
</style>
