// Normalizes keyboard events into a comparable "keychord" string and provides a
// global dispatcher that ignores typing inside inputs (except explicit chords).
export function keychordOf(e: KeyboardEvent): string {
    const parts: string[] = [];
    if (e.ctrlKey || e.metaKey) parts.push("ctrl");
    if (e.altKey) parts.push("alt");
    if (e.shiftKey) parts.push("shift");
    const k = e.key.length === 1 ? e.key.toLowerCase() : e.key.toLowerCase();
    parts.push(k);
    return parts.join("+");
}

/** True when focus is in a text field, so we don't hijack typing. */
export function inEditable(target: EventTarget | null): boolean {
    const el = target as HTMLElement | null;
    if (!el) return false;
    const tag = el.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || el.isContentEditable;
}
