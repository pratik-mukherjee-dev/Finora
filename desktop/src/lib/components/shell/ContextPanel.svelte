<script lang="ts">
    import type {ShellState} from "$lib/shell/shellContext.svelte";

    type Props = { shell: ShellState };
    let {shell}: Props = $props();

    const tabs = $derived(shell.panel);
    const active = $derived(tabs.find((t) => t.id === shell.activeTab) ?? tabs[0] ?? null);

    // Open a specific tab (also ensures the panel is visible).
    function openTab(id: string) {
        shell.activeTab = id;
        if (!shell.panelOpen) shell.togglePanel();
    }
</script>

{#if tabs.length > 0}
    {#if shell.panelOpen}
        <aside class="panel" aria-label="Context panel">
            <div class="tabs">
                {#each tabs as t (t.id)}
                    <button class="tab" class:active={active?.id === t.id}
                            onclick={() => (shell.activeTab = t.id)}>{t.title}</button>
                {/each}
                <button class="close" title="Hide panel (Ctrl+H)" aria-label="Hide panel"
                        onclick={() => shell.togglePanel()}>›</button>
            </div>
            <div class="body">
                <div class="content">
                  {#if active}{@render active.body()}{/if}
                </div>
            </div>
        </aside>
    {:else}
        <!-- Collapsed: thin rail to reopen. Each tab is clickable to reopen at that tab. -->
        <div class="railcol" aria-label="Show context panel">
            <button class="reopen" title="Show panel (Ctrl+H)" aria-label="Show panel"
                    onclick={() => shell.togglePanel()}>‹</button>
            {#each tabs as t (t.id)}
                <button class="vtab" title={`Show ${t.title} (Ctrl+H)`}
                        onclick={() => openTab(t.id)}>{t.title}</button>
            {/each}
        </div>
    {/if}
{/if}

<style>
    .body {
      flex: 1;
      overflow: auto;
    }

    .panel {
        width: var(--panel-w);
        border-left: 1px solid var(--border);
        background: var(--bg-panel);
        display: flex;
        flex-direction: column;
        min-height: 0;
        margin-left: 6px;
    }

    .content {
        padding: 20px 18px 16px;
    }

    .tabs {
        display: flex;
        align-items: center;
        gap: 2px;
        padding: 8px 12px;
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
        margin-right: 5px;

        display: flex;
        align-items: center;
        justify-content: center;
        background: transparent;
        border: 1px solid var(--border-hi);
        color: var(--text-muted);
        width: 26px;
        height: 26px;
        border-radius: 6px;
        cursor: pointer;
    }

    .close:hover {
        border-color: var(--accent-text);
        color: var(--accent-text);
    }

    /* Collapsed reopen rail */
    .railcol {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        width: 30px;
        padding: 8px 0;
        border-left: 1px solid var(--border);
        background: var(--bg-panel);
    }

    .reopen {
        background: transparent;
        border: 1px solid var(--border-hi);
        color: var(--text-muted);
        width: 24px;
        height: 26px;
        border-radius: 6px;
        cursor: pointer;
    }

    .reopen:hover {
        border-color: var(--accent-text);
        color: var(--accent-text);
    }

    .vtab {
        writing-mode: vertical-rl;
        transform: rotate(180deg);
        background: transparent;
        border: none;
        color: var(--text-muted);
        font-size: 12px;
        padding: 8px 2px;
        cursor: pointer;
        border-radius: 6px;
    }

    .vtab:hover {
        background: var(--bg-elevated);
        color: var(--accent-text);
    }
</style>
