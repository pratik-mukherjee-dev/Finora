<script lang="ts">
    import { onMount } from "svelte";
    import type { Issue } from "$lib/validation";

    type Props = {
        issues: Issue[];
        onreview: () => void;
        onproceed: () => void;
        oncancel: () => void;
    };
    let {
        issues,
        onreview,
        onproceed,
        oncancel,
    }: Props = $props();

    let armed = $state(false);

    // Ignore the Enter keystroke that opened this dialog; arm on the next tick.
    onMount(() => {
        const id = setTimeout(() => (armed = true), 0);
        return () => clearTimeout(id);
    });

    function focusOnMount(node: HTMLElement) {
        node.focus();
    }

    const hasBlock = $derived(issues.some((i) => i.severity === "block"));

    function onBackdropClick(e: MouseEvent) {
        if (e.target === e.currentTarget) oncancel();
    }

    function onKey(e: KeyboardEvent) {
        if (e.key === "Escape") {
            e.preventDefault();
            e.stopPropagation();
            oncancel();
        } else if (e.key === "Enter") {
            if (!armed) return;
            e.preventDefault();
            e.stopPropagation();
            onreview();
        }
    }
</script>

<svelte:window onkeydown={onKey}/>

<div class="backdrop" role="presentation" onclick={onBackdropClick}>
    <div class="dialog" role="dialog" aria-modal="true">
        <h2>⚠ Heads up</h2>
        <ul class="issues">
            {#each issues as issue (issue.code)}
                <li class:block={issue.severity === "block"}>
                    <span class="dot">{issue.severity === "block" ? "✕" : "!"}</span>
                    <span>{issue.message}</span>
                </li>
            {/each}
        </ul>
        <div class="row">
            <button type="button" class="ghost" onclick={oncancel}>Cancel <kbd>Esc</kbd></button>
            {#if !hasBlock}
                <button type="button" class="ghost" onclick={onproceed}>Save anyway</button>
            {/if}
            <button type="button" onclick={onreview} use:focusOnMount>Review & fix <kbd>⏎</kbd></button>
        </div>
    </div>
</div>

<style>
    .backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, .55);
        display: grid;
        place-items: center;
        z-index: 60;
    }

    .dialog {
        display: flex;
        flex-direction: column;
        gap: 12px;
        width: 400px;
        padding: 22px;
        background: #171a21;
        border: 1px solid var(--border-hi);
        border-radius: 12px;
        color: #e6e8ec;
    }

    h2 {
        margin: 0;
        font-size: 17px;
        color: #fbbf24;
    }

    .issues {
        margin: 0;
        padding: 0;
        list-style: none;
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .issues li {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        font-size: 13px;
        color: var(--text-muted);
        line-height: 1.45;
    }

    .issues li.block {
        color: #ff9b9b;
    }

    .dot {
        flex-shrink: 0;
        width: 18px;
        height: 18px;
        display: grid;
        place-items: center;
        border-radius: 50%;
        font-size: 10px;
        font-weight: 700;
        background: rgba(251, 191, 36, .15);
        color: #fbbf24;
    }

    .issues li.block .dot {
        background: rgba(255, 155, 155, .15);
        color: #ff9b9b;
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
        font-size: 14px;
    }

    button.ghost {
        background: transparent;
        border-color: #2a2f3a;
        color: var(--text);
    }

    kbd {
        background: rgba(0, 0, 0, .25);
        border: 1px solid var(--border-hi);
        border-radius: 4px;
        padding: 0 4px;
        font-size: 11px;
        margin-left: 6px;
    }
</style>