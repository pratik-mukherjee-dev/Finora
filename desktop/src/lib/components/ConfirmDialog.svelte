<script lang="ts">
    import { onMount } from "svelte";

    type Props = {
        title?: string;
        message?: string;
        confirmLabel?: string;
        cancelLabel?: string;
        busy?: boolean;
        onconfirm: () => void;
        oncancel: () => void;
    };
    let {
        title = "Confirm",
        message = "",
        confirmLabel = "Confirm",
        cancelLabel = "Cancel",
        busy = false,
        onconfirm,
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

    function onBackdropClick(e: MouseEvent) {
        if (e.target === e.currentTarget) oncancel();
    }

    function onKey(e: KeyboardEvent) {
        if (e.key === "Escape") {
            e.preventDefault();
            oncancel();
        } else if (e.key === "Enter") {
            if (!armed) return;            // swallow the opening keystroke
            e.preventDefault();
            e.stopPropagation();
            if (!busy) onconfirm();
        }
    }

</script>

<svelte:window onkeydown={onKey}/>

<div class="backdrop" role="presentation" onclick={onBackdropClick}>
    <div class="dialog" role="dialog" aria-modal="true">
        <h2>{title}</h2>
        {#if message}<p class="msg">{message}</p>{/if}
        <div class="row">
            <button type="button" class="ghost" onclick={oncancel}>{cancelLabel} <kbd>Esc</kbd></button>
            <button type="button" disabled={busy} onclick={onconfirm} use:focusOnMount>
                {busy ? "Saving…" : confirmLabel} <kbd>⏎</kbd>
            </button>
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
        width: 360px;
        padding: 22px;
        background: #171a21;
        border: 1px solid var(--border-hi);
        border-radius: 12px;
        color: #e6e8ec;
    }

    h2 {
        margin: 0;
        font-size: 17px;
    }

    .msg {
        margin: 0;
        font-size: 14px;
        color: var(--text-muted);
        line-height: 1.5;
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

    button:disabled {
        opacity: .5;
        cursor: default;
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
