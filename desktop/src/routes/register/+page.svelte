<script lang="ts">
    import {auth} from "$lib/stores/auth.svelte";
    import {goto} from "$app/navigation";
    import { advanceOrSubmit } from "$lib/flow";

    let username = $state("");
    let password = $state("");
    let confirm = $state("");
    let error = $state<string | null>(null);
    let busy = $state(false);

    const mismatch = $derived(confirm.length > 0 && password !== confirm);
    const canSubmit = $derived(
        !busy &&
        username.trim().length > 0 &&
        password.length >= 6 &&
        password === confirm
    );

    function focusOnMount(node: HTMLElement) {
        node.focus();
    }

    async function submit(e: Event) {
        e.preventDefault();
        if (!canSubmit) return;
        error = null;
        busy = true;
        try {
            await auth.register(username.trim(), password);
            await goto("/setup");
        } catch {
            error = "Could not create the account. Try again.";
        } finally {
            busy = false;
        }
    }
</script>

<main class="wrap">
    <form class="card" onsubmit={submit} onkeydown={(e) => advanceOrSubmit(e, () => canSubmit, submit)}>
        <h1>Welcome to Finora</h1>
        <p class="muted">Create your account. It lives only on this device.</p>
        <input bind:value={username} placeholder="Username" autocomplete="username" use:focusOnMount/>
        <input bind:value={password} type="password" placeholder="Password (min 6 chars)" autocomplete="new-password"/>
        <input bind:value={confirm} type="password" placeholder="Confirm password" autocomplete="new-password"/>
        {#if mismatch}<p class="err">Passwords don’t match.</p>{/if}
        {#if error}<p class="err">{error}</p>{/if}
        <button disabled={!canSubmit}>{busy ? "Creating…" : "Create account"}</button>
    </form>
</main>


<style>
    .wrap {
        display: grid;
        place-items: center;
        height: 100vh;
        background: #0f1115;
        color: #e6e8ec;
    }

    .card {
        display: flex;
        flex-direction: column;
        gap: 12px;
        width: 300px;
        padding: 28px;
        background: #171a21;
        border-radius: 12px;
    }

    h1 {
        margin: 0 0 2px;
        font-size: 22px;
        text-align: center;
    }

    .muted {
        color: #9aa0aa;
        font-size: 13px;
        margin: 0 0 6px;
        text-align: center;
    }

    input, button {
        padding: 10px 12px;
        border-radius: 8px;
        border: 1px solid #2a2f3a;
        background: #0f1115;
        color: #e6e8ec;
        font-size: 14px;
    }

    button {
        background: #2f6feb;
        border-color: #2f6feb;
        cursor: pointer;
    }

    button:disabled {
        opacity: .5;
        cursor: default;
    }

    .err {
        color: #ff6b6b;
        font-size: 13px;
        margin: 0;
    }
</style>