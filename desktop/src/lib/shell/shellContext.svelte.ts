// Shell context API. The shell (app/+layout.svelte) creates one instance and
// puts it on Svelte context under SHELL_KEY. Screens read it and register their
// context-panel content and contextual commands. This is the teleport bridge:
// screens declare what the persistent shell should show, without owning chrome.
import {getContext, setContext} from "svelte";
import type {Snippet} from "svelte";
import type {Command} from "$lib/commands";

export const SHELL_KEY = Symbol("finora-shell");

export interface PanelTab {
    id: string;
    title: string;
    /** Rendered into the shell's ContextPanel body. */
    body: Snippet;
}

export interface ScreenRegistration {
    /** Screen title shown in the context bar. */
    title?: string;
    /** Quick actions shown in the context bar (right of the title). */
    actions?: Command[];
    /** Right-dock panel tabs (history, allocations, ledger, …). */
    panel?: PanelTab[];
    /** Contextual keychords active only while this screen is mounted. */
    shortcuts?: Command[];
}

export function createShellState() {
    let title = $state<string>("");
    let actions = $state<Command[]>([]);
    let panel = $state<PanelTab[]>([]);
    let shortcuts = $state<Command[]>([]);
    let panelOpen = $state(true);
    let activeTab = $state<string | null>(null);

    return {
        get title() {
            return title;
        },
        get actions() {
            return actions;
        },
        get panel() {
            return panel;
        },
        get shortcuts() {
            return shortcuts;
        },
        get panelOpen() {
            return panelOpen;
        },
        get activeTab() {
            return activeTab;
        },
        set activeTab(v: string | null) {
            activeTab = v;
        },
        togglePanel() {
            panelOpen = !panelOpen;
        },
        /** Called by a screen on mount. Returns a disposer to run on unmount. */
        register(reg: ScreenRegistration) {
            title = reg.title ?? "";
            actions = reg.actions ?? [];
            panel = reg.panel ?? [];
            shortcuts = reg.shortcuts ?? [];
            activeTab = panel.length ? panel[0].id : null;
            return () => {
                title = "";
                actions = [];
                panel = [];
                shortcuts = [];
                activeTab = null;
            };
        },
    };
}

export type ShellState = ReturnType<typeof createShellState>;

export function setShell(s: ShellState) {
    setContext(SHELL_KEY, s);
}

export function useShell(): ShellState {
    return getContext<ShellState>(SHELL_KEY);
}
