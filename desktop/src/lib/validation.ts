/**
 * A soft issue surfaced by the pre-save WarningDialog.
 * Each screen implements `collectIssues(): Issue[]` in visual/flow order
 * (top of form → bottom) so `issues[0].focus()` targets the first problem.
 */
export type Issue = {
    /** Stable identifier, e.g. "line-qty-zero", "settle-no-mode". */
    code: string;
    /** Human-readable message shown in the dialog list. */
    message: string;
    /** Focuses the offending input when the user picks "Review & fix". */
    focus: () => void;
    /** "warn" = saveable but suspicious; "block" = hides "Save anyway". Default: "warn". */
    severity?: "warn" | "block";
};
