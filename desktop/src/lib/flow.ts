// desktop/src/lib/flow.ts
// App-wide "Enter to advance, last field to save" keyboard flow.
// Opt in per screen with `use:enterFlow={{ onSave, isComplete }}` on the form
// root, and mark participating fields with `data-flow="..."`. Order follows DOM
// order; the LAST data-flow node is the terminal (save) step.

export type FlowOptions = {
    // Called to actually persist. Receives whether the user forced a direct save.
    onSave: (opts: { direct: boolean }) => void;
    // Return true when every "potential" (required) field is filled.
    // Used by Ctrl+Enter to skip confirmation when the form is complete.
    isComplete: () => boolean;
    // Called when Enter reaches the terminal step and the form is NOT complete,
    // or on a normal save — the screen shows its confirm dialog here.
    onConfirm: () => void;
};

const SEL = "[data-flow]";

function visibleFlowNodes(root: HTMLElement): HTMLElement[] {
    return Array.from(root.querySelectorAll<HTMLElement>(SEL))
        .filter((n) => n.offsetParent !== null && !(n as HTMLButtonElement).disabled);
}

/** Focus a node and, for text inputs, select its contents; for date, open picker. */
export function focusFlowNode(n: HTMLElement | undefined | null) {
    if (!n) return;
    n.focus();
    if (n instanceof HTMLInputElement) {
        if (n.type === "date") {
            try { (n as any).showPicker?.(); } catch { /* no gesture / unsupported */ }
        } else {
            n.select();
        }
    }
}

// Lightweight Enter-flow for plain <form> dialogs/pages that don't use the full
// enterFlow action. Attach with onkeydown={(e) => advanceOrSubmit(e, canSubmit, submit)}.
//   • Ctrl/Cmd+Enter anywhere → submit directly (if canSubmit()).
//   • Enter on a non-last input → focus + select the next input.
//   • Enter on the last input   → submit (if canSubmit()).
// Ignores checkboxes/buttons for advancement and lets textareas keep newlines.
export function advanceOrSubmit(
    e: KeyboardEvent,
    canSubmit: () => boolean,
    submit: (e: Event) => void,
) {
    if (e.key !== "Enter") return;
    const el = e.target as HTMLElement;
    if (el.tagName === "TEXTAREA" && !e.ctrlKey && !e.metaKey) return;

    // Direct save from anywhere.
    if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        if (canSubmit()) submit(e);
        return;
    }

    if (el.tagName !== "INPUT") return;
    e.preventDefault();

    const form = el.closest("form");
    if (!form) return;
    const fields = Array.from(
        form.querySelectorAll<HTMLInputElement>('input:not([type="hidden"]):not([disabled])'),
    ).filter((n) => n.type !== "checkbox" && n.offsetParent !== null);

    const i = fields.indexOf(el as HTMLInputElement);
    const next = fields[i + 1];
    if (next) {
        next.focus();
        if (next.type === "date") { try { (next as any).showPicker?.(); } catch { /* ignore */ } }
        else next.select?.();
    } else if (canSubmit()) {
        submit(e);
    }
}


/** Advance from `current` to the next visible flow node. Returns false at the end. */
export function advance(root: HTMLElement, current: HTMLElement): boolean {
    const nodes = visibleFlowNodes(root);
    const i = nodes.indexOf(current);
    if (i === -1) return false;
    const next = nodes[i + 1];
    if (!next) return false;
    focusFlowNode(next);
    return true;
}

/** Svelte action applied to the form root element. */
export function enterFlow(root: HTMLElement, opts: FlowOptions) {
    let current = opts;

    function handleKey(e: KeyboardEvent) {
        const el = e.target as HTMLElement;

        // Ctrl/Cmd+Enter anywhere: direct save. Confirm only if incomplete.
        if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            e.stopPropagation();               // don't let a mounted dialog also react
            if (current.isComplete()) current.onSave({ direct: true });
            else current.onConfirm();
            return;
        }

        if (e.key !== "Enter") return;

        // Let composite widgets (lookup with an open menu, textareas) handle Enter.
        if (el.dataset.flowSkip === "1") return;
        if (el.tagName === "TEXTAREA" && !e.ctrlKey) return;

        // Only react to elements that participate in the flow.
        const node = el.closest<HTMLElement>(SEL);
        if (!node || !root.contains(node)) return;

        e.preventDefault();

        // Terminal step (save) or no further node -> confirm (opens dialog).
        const isTerminal = node.dataset.flow === "save";
        const moved = isTerminal ? false : advance(root, node);
        if (!moved) {
            current.onConfirm();
        }
    }

    // Ctrl/Cmd+Enter should work anywhere in the app, even if focus left the form
    // root (e.g. after closing a dialog with Esc).
    function handleGlobalSave(e: KeyboardEvent) {
        if (e.key !== "Enter" || !(e.ctrlKey || e.metaKey)) return;
        // If the event already targets inside root, the root listener handles it.
        if (root.contains(e.target as Node)) return;
        e.preventDefault();
        if (current.isComplete()) current.onSave({ direct: true });
        else current.onConfirm();
    }

    root.addEventListener("keydown", handleKey);
    window.addEventListener("keydown", handleGlobalSave);
    return {
        update(next: FlowOptions) { current = next; },
        destroy() {
            root.removeEventListener("keydown", handleKey);
            window.removeEventListener("keydown", handleGlobalSave);
        },
    };

}
