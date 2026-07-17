<script lang="ts">
    import type {ShellState} from "$lib/shell/shellContext.svelte";

    type Props = { shell: ShellState };
    let {shell}: Props = $props();

    const tabs = $derived(shell.panel);
    const active = $derived(tabs.find((t) => t.id === shell.activeTab) ?? tabs[0] ?? null);
</script>

{#if shell.panelOpen && tabs.length > 0}
    <aside class="panel" aria-label="Context panel">
        <div class="tabs">
            {#each tabs as t (t.id)}
                <button class="tab" class:active={active?.id === t.id}
                        onclick={() => (shell.activeTab = t.id)}>{t.title}</button>
            {/each}
            <button class="close" title="Toggle panel (Ctrl+H)" onclick={() => shell.togglePanel()}>›</button>
        </div>
        <div class="body">
            {#if active}{@render active.body()}{/if}
        </div>
    </aside>
{/if}

<style>
    .panel {
        width: var(--panel-w);
        border-left: 1px solid var(--border);
        background: var(--bg-panel);
        display: flex;
        flex-direction: column;
        min-height: 0;
    }

    .tabs {
        display: flex;
        align-items: center;
        gap: 2px;
        padding: 6px 8px;
        border-bottom: 1px solid var(--border);
    }

    .tab {
        background: transparent;
        border: none;
        color: var(--text-muted);
        padding: 6px 10px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 13px;
    }

    .tab:hover {
        background: var(--bg-elevated);
    }

    .tab.active {
        background: var(--accent-soft);
        color: var(--accent-text);
        font-weight: 600;
    }

    .close {
        margin-left: auto;
        background: transparent;
        border: 1px solid var(--border-hi);
        color: var(--text-muted);
        width: 26px;
        height: 26px;
        border-radius: 6px;
        cursor: pointer;
    }

    .body {
        padding: 14px;
        overflow: auto;
        flex: 1;
    }
</style>
