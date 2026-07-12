    <script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { waitForBackend, authState, ApiError } from "$lib/api";
  import { auth } from "$lib/stores/auth.svelte";

  type Phase = "connecting" | "restoring" | "error";

  let phase = $state<Phase>("connecting");
  let attempts = $state(0);
  let errorMsg = $state("");

  async function boot() {
    phase = "connecting";
    attempts = 0;
    errorMsg = "";
    try {
      await waitForBackend({
        intervalMs: 400,
        timeoutMs: 30000,
        onAttempt: (n) => (attempts = n),
      });
      phase = "restoring";

      // First launch on this device → no account yet → go create one.
      const { initialized } = await authState();
      if (!initialized) {
        await goto("/register");
        return;
      }

      await auth.restore();
      await goto(auth.isAuthed ? "/app" : "/login");
    } catch (e) {
      errorMsg =
        e instanceof ApiError ? `HTTP ${e.status}: ${e.message}`
        : e instanceof Error ? e.message
        : String(e);
      phase = "error";
    }
  }

  onMount(boot);
</script>

<main class="wrap">
  {#if phase === "error"}
    <div class="badge err">!</div>
    <h1>Couldn’t reach the backend</h1>
    <p class="muted">{errorMsg}</p>
    <button onclick={ boot }>Retry</button>
  {:else}
    <div class="spinner"></div>
    <h1>{phase === "connecting" ? "Starting Finora…" : "Restoring session…"}</h1>
  {#if phase === "connecting"}
    <p class="muted">Waiting for the local database and server (attempt { attempts }).</p>
  {/if}
  {/if}
</main>

<style>
  :global(body) {
    margin: 0; background: #0f1115; color: #e6e8ec;
    font-family: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif;
  }
  .wrap {
    min-height: 100vh; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 0.6rem;
    text-align: center; padding: 2rem;
  }
  h1 { font-size: 1.25rem; font-weight: 600; margin: 0.3rem 0 0; }
  .muted { color: #9aa0aa; margin: 0.15rem 0; font-size: 0.9rem; }
  .spinner {
    width: 34px; height: 34px; border: 3px solid #2a2f3a;
    border-top-color: #4c8bf5; border-radius: 50%; animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .badge {
    width: 40px; height: 40px; border-radius: 50%;
    display: grid; place-items: center; font-weight: 700; font-size: 1.2rem;
  }
  .badge.err { background: #3a1a1a; color: #f57070; }
  button {
    margin-top: 0.6rem; padding: 0.5rem 1.1rem; border-radius: 8px;
    border: 1px solid #2a2f3a; background: #1a1d24; color: #e6e8ec;
    font-size: 0.9rem; cursor: pointer;
  }
  button:hover { border-color: #4c8bf5; }
</style>