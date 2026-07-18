<script lang="ts">
    import {recordUsage, suggest, type Suggestion} from "$lib/api";

    type Props = {
        type: "ITEM" | "PARTY";
        placeholder?: string;
        value?: Suggestion | null;
        onselect: (s: Suggestion) => void;
        oncreate: (typed: string) => void;
        onenter?: () => void;              // fired when Enter pressed on an already-resolved value
    };
    let {type, placeholder = "", value = $bindable(null), onselect, oncreate, onenter}: Props = $props();

    let inputEl: HTMLInputElement | null = $state(null);
    export function focus() {
        inputEl?.focus();
        inputEl?.select();
    }

    let q = $state(value?.name ?? "");
    let open = $state(false);
    let results = $state<Suggestion[]>([]);
    let active = $state(0);
    let loading = $state(false);

    let timer: ReturnType<typeof setTimeout> | null = null;
    let controller: AbortController | null = null;

    function schedule() {
        if (timer) clearTimeout(timer);
        timer = setTimeout(run, 150);
    }

    async function run() {
        const term = q.trim();
        if (!term) {
            results = [];
            open = false;
            return;
        }
        controller?.abort();
        controller = new AbortController();
        loading = true;
        try {
            results = await suggest(type, term, 10, controller.signal);
            active = 0;
            open = true;
        } catch (e) {
            if ((e as Error)?.name !== "AbortError") {
                results = [];
            }
        } finally {
            loading = false;
        }
    }

    function pick(s: Suggestion) {
        value = s;
        q = s.name;
        open = false;
        onselect(s);
        recordUsage(type, s.id);
        onenter?.();                        // move focus to next field after choosing
    }

    function onInput(e: Event) {
        q = (e.target as HTMLInputElement).value;
        value = null;
        schedule();
    }

    const noMatch = $derived(
        open && !loading && q.trim().length > 0 &&
        !results.some((r) => r.name.toLowerCase() === q.trim().toLowerCase())
    );

        function onKey(e: KeyboardEvent) {
        if (e.key === "Enter" && !open) {
            // Nothing to pick from — treat Enter as "advance to next field".
            if (value) {
                e.preventDefault();
                onenter?.();
            }
            return;
        }
        if (!open) return;
        if (e.key === "ArrowDown") {
            active = Math.min(active + 1, results.length - 1);
            e.preventDefault();
        } else if (e.key === "ArrowUp") {
            active = Math.max(active - 1, 0);
            e.preventDefault();
        } else if (e.key === "Enter") {
            e.preventDefault();
            if (results[active]) pick(results[active]);
            else if (q.trim()) oncreate(q.trim());
        } else if (e.key === "Escape") {
            open = false;
        }
    }
</script>

<div class="lookup">
    <input
            bind:this={inputEl}
            autocomplete="off"
            onblur={() => setTimeout(() => (open = false), 120)}
            onfocus={() => { if (results.length) open = true; }}
            oninput={onInput}
            onkeydown={onKey}
            {placeholder}
            value={q}
    />
    {#if open}
        <ul class="menu" role="listbox">
            {#each results as r, i (r.id)}
                <li role="option" aria-selected={i === active} tabindex="-1"
                    class:active={i === active} onmousedown={() => pick(r)}>{r.name}</li>
            {/each}
            {#if noMatch}
                <li role="option" aria-selected="false" tabindex="-1"
                    class="create" onmousedown={() => oncreate(q.trim())}>+ Create “{q.trim()}”
                </li>
            {/if}

            {#if !results.length && !noMatch}
                <li class="empty">{loading ? "Searching…" : "No results"}</li>
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
        font-size: 14px;
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

    .menu li.create {
        color: #4c8bf5;
    }

    .menu li.empty {
        color: #9aa0aa;
        cursor: default;
    }
</style>
