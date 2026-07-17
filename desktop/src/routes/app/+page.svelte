<script lang="ts">
    import {auth} from "$lib/stores/auth.svelte";

    const fyLabel = $derived(
        auth.fy ? `${auth.fy.start_date.slice(0, 4)}–${auth.fy.end_date.slice(0, 4)}` : "—"
    );
</script>

<div class="home">
    <h1>Welcome{auth.user ? `, ${auth.user.username}` : ""}</h1>
    <p class="muted">
        Company <strong>{auth.currentCompany?.name ?? "—"}</strong>, financial year
        <strong>{fyLabel}</strong>. Press <kbd>Ctrl</kbd>+<kbd>K</kbd> to jump anywhere,
        or use <kbd>Alt</kbd>+<kbd>1..9</kbd> for modules.
    </p>
    <p class="muted small">Dashboard KPIs land here next (reports/dashboard/).</p>
</div>

<style>
    .home {
        padding: 28px;
    }

    h1 {
        margin: 0 0 8px;
        font-size: 22px;
    }

    .muted {
        color: var(--text-muted);
        font-size: 14px;
        line-height: 1.6;
        margin: 0 0 8px;
        max-width: 620px;
    }

    .small {
        font-size: 13px;
        opacity: .8;
    }

    kbd {
        background: var(--bg-elevated);
        border: 1px solid var(--border-hi);
        border-radius: 4px;
        padding: 0 5px;
        font-size: 12px;
    }
</style>
