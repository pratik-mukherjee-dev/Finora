<script lang="ts">
    import "$lib/theme.css";
    import {auth} from "$lib/stores/auth.svelte";
    import {goto} from "$app/navigation";
    import {onMount} from "svelte";
    import type {Snippet} from "svelte";
    import ActivityBar from "$lib/components/shell/ActivityBar.svelte";
    import ContextBar from "$lib/components/shell/ContextBar.svelte";
    import ContextPanel from "$lib/components/shell/ContextPanel.svelte";
    import CommandPalette from "$lib/components/shell/CommandPalette.svelte";
    import {modules} from "$lib/commands";
    import {keychordOf, inEditable} from "$lib/shortcuts";
    import {createShellState, setShell} from "$lib/shell/shellContext.svelte";

    let {children}: { children: Snippet } = $props();

    const shell = createShellState();
    setShell(shell);

    let railExpanded = $state(true);
    let paletteOpen = $state(false);

    onMount(() => {
        if (!auth.isAuthed) return void goto("/login");
        if (auth.needsSetup) return void goto("/setup");
        if (auth.needsFy) return void goto("/fy");
    });

    const fyLabel = $derived(
        auth.fy ? `${auth.fy.start_date.slice(0, 4)}–${auth.fy.end_date.slice(0, 4)}` : "—"
    );

    async function onCompanyChange(e: Event) {
        await auth.setCurrentCompany(Number((e.target as HTMLSelectElement).value));
    }

    async function doLogout() {
        await auth.logout();
        await goto("/login");
    }

    function onGlobalKey(e: KeyboardEvent) {
        const chord = keychordOf(e);

        if (chord === "ctrl+k") {
            e.preventDefault();
            paletteOpen = !paletteOpen;
            return;
        }
        if (chord === "ctrl+h") {
            e.preventDefault();
            shell.togglePanel();
            return;
        }
        if (chord === "ctrl+,") {
            e.preventDefault();
            goto("/app/settings");
            return;
        }
        // Module jumps (Alt+n) fire even while typing.
        const mod = modules.find((m) => m.keychord === chord);
        if (mod && e.altKey) {
            e.preventDefault();
            mod.run();
            return;
        }
        // Contextual (screen-registered) shortcuts.
        const sc = shell.shortcuts.find((s) => s.keychord === chord);
        if (sc) {
            // Voucher chords like Ctrl+Enter must work from inside inputs;
            // plain-letter chords should not hijack typing.
            const isModified = e.ctrlKey || e.metaKey || e.altKey;
            if (isModified || !inEditable(e.target)) {
                e.preventDefault();
                sc.run();
            }
        }
    }
</script>

<svelte:window onkeydown={onGlobalKey}/>

<div class="shell">
    <ActivityBar expanded={railExpanded}/>

    <section class="main">
        <header class="topbar">
            <button class="collapse" title="Toggle sidebar"
                    onclick={() => (railExpanded = !railExpanded)}>☰
            </button>
            <div class="ctx">
                {#if auth.mode === "multi"}
                    <select class="company" onchange={onCompanyChange}>
                        {#each auth.companies as c (c.id)}
                            <option value={c.id} selected={c.id === auth.currentCompany?.id}>{c.name}</option>
                        {/each}
                    </select>
                {:else}
                    <span class="company-static">{auth.currentCompany?.name ?? "—"}</span>
                {/if}
                <span class="fybadge">FY {fyLabel}</span>
            </div>
            <div class="spacer"></div>
            <span class="user">{auth.user?.username ?? ""}</span>
            <button class="logout" onclick={doLogout}>Log out</button>
        </header>

        <ContextBar {shell} onpalette={() => (paletteOpen = true)}/>

        <div class="body">
            <div class="workspace">
                {@render children()}
            </div>
            <ContextPanel {shell}/>
        </div>

        <footer class="statusbar">
            <span>{auth.mode === "multi" ? "Multi-company" : "Single-company"}</span>
            <span class="dot" class:ok={auth.fy?.is_writable}></span>
            <span>FY {auth.fy?.is_writable ? "writable" : "locked"}</span>
            <span class="hint">Ctrl+K commands · Alt+1..9 modules · Ctrl+H panel</span>
        </footer>
    </section>
</div>

<CommandPalette open={paletteOpen} onclose={() => (paletteOpen = false)}/>

<style>
    .shell {
        display: flex;
        height: 100vh;
        overflow: hidden;
    }

    .main {
        flex: 1;
        display: flex;
        flex-direction: column;
        min-width: 0;
    }

    .topbar {
        display: flex;
        align-items: center;
        gap: 12px;
        height: var(--topbar-h);
        padding: 0 14px;
        border-bottom: 1px solid var(--border);
        background: var(--bg-panel);
    }

    .collapse, .logout {
        background: transparent;
        border: 1px solid var(--border-hi);
        color: var(--text-muted);
        border-radius: 6px;
        cursor: pointer;
        padding: 5px 10px;
        font-size: 13px;
    }

    .collapse:hover, .logout:hover {
        border-color: var(--accent-text);
        color: var(--accent-text);
    }

    .ctx {
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .company {
        padding: 5px 8px;
        border-radius: 6px;
        border: 1px solid var(--border-hi);
        background: var(--bg-app);
        color: var(--text);
        font-size: 13px;
    }

    .company-static {
        font-weight: 600;
        font-size: 14px;
    }

    .fybadge {
        padding: 3px 10px;
        border-radius: 999px;
        background: var(--accent-soft);
        color: var(--accent-text);
        font-size: 12px;
        font-weight: 600;
    }

    .spacer {
        flex: 1;
    }

    .user {
        font-size: 13px;
        color: var(--text-muted);
    }

    .body {
        flex: 1;
        display: flex;
        min-height: 0;
    }

    .workspace {
        flex: 1;
        overflow: auto;
        min-width: 0;
    }

    .statusbar {
        display: flex;
        align-items: center;
        gap: 12px;
        height: var(--statusbar-h);
        padding: 0 14px;
        border-top: 1px solid var(--border);
        background: var(--bg-panel);
        font-size: 12px;
        color: var(--text-muted);
    }

    .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--danger);
    }

    .dot.ok {
        background: var(--ok);
    }

    .hint {
        margin-left: auto;
    }
</style>
