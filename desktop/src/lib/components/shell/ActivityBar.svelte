<script lang="ts">
    import {auth} from "$lib/stores/auth.svelte";
    import {modules, activeModuleId, type Command} from "$lib/commands";
    import {page} from "$app/stores";

    type Props = { expanded: boolean };
    let {expanded}: Props = $props();

    const active = $derived(activeModuleId($page.url.pathname));
    const visible = $derived(
        modules.filter((m) => !m.minMode || auth.mode === m.minMode)
    );

    function run(cmd: Command) {
        cmd.run();
    }
</script>

<nav class="rail" class:exp={expanded} aria-label="Modules">
    <div class="brand">{expanded ? "Finora" : "F"}</div>
    {#each visible as m (m.id)}
        <button
                class="mod"
                class:active={active === m.id}
                title={`${m.label} · ${m.shortcut}`}
                onclick={() => run(m)}
        >
            <span class="ico">{m.icon}</span>
            {#if expanded}<span class="lbl">{m.label}</span>{/if}
            {#if expanded}<span class="sc">{m.shortcut?.replace("Alt+", "⌥")}</span>{/if}
        </button>
    {/each}
</nav>

<style>
    .rail {
        display: flex;
        flex-direction: column;
        gap: 4px;
        width: var(--rail-w);
        background: var(--bg-panel);
        border-right: 1px solid var(--border);
        padding: 10px 8px;
        box-sizing: border-box;
    }

    .rail.exp {
        width: var(--rail-w-exp);
    }

    .brand {
        color: var(--accent-text);
        font-weight: 700;
        font-size: 16px;
        padding: 4px 8px 12px;
    }

    .mod {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 9px 10px;
        border: none;
        border-radius: var(--radius);
        background: transparent;
        color: var(--text-muted);
        cursor: pointer;
        font-size: 14px;
        text-align: left;
    }

    .mod:hover {
        background: var(--bg-elevated);
    }

    .mod.active {
        background: var(--accent-soft);
        color: var(--accent-text);
        font-weight: 600;
    }

    .ico {
        width: 20px;
        text-align: center;
        font-size: 15px;
    }

    .lbl {
        flex: 1;
    }

    .sc {
        font-size: 11px;
        color: var(--text-muted);
    }
</style>
