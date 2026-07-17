<script lang="ts">
    import {auth} from "$lib/stores/auth.svelte";
    import {modules, type Command} from "$lib/commands";

    type Props = { open: boolean; onclose: () => void };
    let {open, onclose}: Props = $props();

    let q = $state("");
    let active = $state(0);
    // Element refs for the rendered result rows, so we can scroll the active one.
    let items = $state<HTMLLIElement[]>([]);

    const all = $derived(modules.filter((m) => !m.minMode || auth.mode === m.minMode));
    const results = $derived(
        q.trim()
            ? all.filter((c) => c.label.toLowerCase().includes(q.trim().toLowerCase()))
            : all
    );

    $effect(() => {
        if (open) {
            q = "";
            active = 0;
        }
    });

    // Keep the highlighted row visible when navigating by keyboard.
    $effect(() => {
        const el = items[active];
        if (open && el) el.scrollIntoView({block: "nearest"});
    });

    function choose(c: Command) {
        onclose();
        c.run();
    }

    function onKey(e: KeyboardEvent) {
        if (e.key === "ArrowDown") {
            active = Math.min(active + 1, results.length - 1);
            e.preventDefault();
        } else if (e.key === "ArrowUp") {
            active = Math.max(active - 1, 0);
            e.preventDefault();
        } else if (e.key === "Enter") {
            if (results[active]) choose(results[active]);
        } else if (e.key === "Escape") {
            onclose();
        }
    }

    function focusOnMount(node: HTMLElement) {
        node.focus();
    }
</script>

{#if open}
    <div class="backdrop" role="presentation" onclick={onclose}>
        <div class="palette" role="dialog" onclick={(e) => e.stopPropagation()}>
            <input
                    use:focusOnMount
                    placeholder="Jump to… (type a module)"
                    bind:value={q}
                    onkeydown={onKey}
            />
            <ul>
                {#each results as c, i (c.id)}
                    <li bind:this={items[i]} class:active={i === active} onmousedown={() => choose(c)}>
                        <span class="ico">{c.icon}</span>
                        <span class="lbl">{c.label}</span>
                        <span class="sc">{c.shortcut}</span>
                    </li>
                {/each}
                {#if results.length === 0}
                    <li class="empty">No matches</li>
                {/if}
            </ul>
        </div>
    </div>
{/if}

<style>
    .backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, .5);
        display: grid;
        place-items: start center;
        padding-top: 12vh;
        z-index: 100;
    }

    .palette {
        width: 480px;
        background: var(--bg-elevated);
        border: 1px solid var(--border-hi);
        border-radius: 12px;
        overflow: hidden;
    }

    input {
        width: 100%;
        box-sizing: border-box;
        padding: 14px 16px;
        border: none;
        border-bottom: 1px solid var(--border);
        background: transparent;
        color: var(--text);
        font-size: 15px;
    }

    ul {
        list-style: none;
        margin: 0;
        padding: 6px;
        max-height: 320px;
        overflow: auto;
        scroll-behavior: smooth;
    }

    li {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 9px 12px;
        border-radius: var(--radius);
        cursor: pointer;
    }

    li.active, li:hover {
        background: var(--accent-soft);
    }

    .ico {
        width: 18px;
        text-align: center;
    }

    .lbl {
        flex: 1;
        font-size: 14px;
    }

    .sc {
        font-size: 11px;
        color: var(--text-muted);
    }

    .empty {
        color: var(--text-muted);
        cursor: default;
        justify-content: center;
    }
</style>
