<script lang="ts">
    import type {ShellState} from "$lib/shell/shellContext.svelte";

    type Props = { shell: ShellState; onpalette: () => void };
    let {shell, onpalette}: Props = $props();
</script>

<div class="ctxbar">
    <span class="title">{shell.title}</span>
    <div class="actions">
        {#each shell.actions as a (a.id)}
            <button class="qa" title={a.shortcut ? `${a.label} · ${a.shortcut}` : a.label}
                    onclick={a.run}>
                {#if a.icon}<span class="ico">{a.icon}</span>{/if}{a.label}
                {#if a.shortcut}<kbd>{a.shortcut}</kbd>{/if}
            </button>
        {/each}
    </div>
    <button class="palette-btn" onclick={onpalette}>Search <kbd>Ctrl K</kbd></button>
</div>

<style>
    .ctxbar {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 16px;
        border-bottom: 1px solid var(--border);
        background: var(--bg-app);
    }

    .title {
        font-size: 15px;
        font-weight: 600;
    }

    .actions {
        display: flex;
        gap: 8px;
        flex: 1;
    }

    .qa {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: transparent;
        border: 1px solid var(--border-hi);
        color: var(--text);
        border-radius: 6px;
        padding: 5px 10px;
        font-size: 13px;
        cursor: pointer;
    }

    .qa:hover {
        border-color: var(--accent);
    }

    .ico {
        color: var(--accent-text);
    }

    .palette-btn {
        background: transparent;
        border: 1px solid var(--border-hi);
        color: var(--text-muted);
        border-radius: 6px;
        padding: 5px 10px;
        font-size: 13px;
        cursor: pointer;
    }

    kbd {
        background: var(--bg-app);
        border: 1px solid var(--border-hi);
        border-radius: 4px;
        padding: 0 4px;
        font-size: 11px;
        margin-left: 4px;
    }
</style>
