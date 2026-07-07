<script lang="ts">
  import { onMount } from "svelte";
  import { waitForBackend, health, apiBase, ApiError } from "$lib/api";

  type Phase = "connecting" | "ready" | "error";

  let phase = $state<Phase>("connecting");
  let attempts = $state(0);
  let baseUrl = $state("");
  let healthStatus = $state("");
  let errorMsg = $state("");

  async function boot() {
    phase = "connecting";
    attempts = 0;
    errorMsg = "";
    healthStatus = "";
    try {
      baseUrl = await waitForBackend({
        intervalMs: 400,
        timeoutMs: 30000,
        onAttempt: (n) => (attempts = n),
      });
      const h = await health();
      healthStatus = h.status;
      phase = "ready";
    } catch (e) {
      if (e instanceof ApiError) {
        errorMsg = `HTTP ${e.status}: ${e.message}`;
      } else {
        errorMsg = e instanceof Error ? e.message : String(e);
      }
      phase = "error";
    }
  }

  onMount(boot);
</script>

<main class="wrap">
  {#if phase === "connecting"}
    <div class="spinner"></div>
    <h1>Starting Finora…</h1>
    <p class="muted">Waiting for the local database and server (attempt {attempts}).</p>
  {:else if phase === "ready"}
    <div class="badge ok">✓</div>
    <h1>Backend connected</h1>
    <p class="muted">Base URL: <code>{baseUrl}</code></p>
    <p class="muted">/health/ → <code>{healthStatus}</code></p>
  {:else}
    <div class="badge err">!</div>
    <h1>Couldn’t reach the backend</h1>
    <p class="muted">{errorMsg}</p>
    <p class="muted">Last known base URL: <code>{apiBase() ?? "unresolved"}</code></p>
    <button onclick={boot}>Retry</button>
  {/if}
</main>

<style>
  :global(body) {
    margin: 0;
    background: #0f1115;
    color: #e6e8ec;
    font-family: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif;
  }
  .wrap {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.6rem;
    text-align: center;
    padding: 2rem;
  }
  h1 {
    font-size: 1.25rem;
    font-weight: 600;
    margin: 0.3rem 0 0;
  }
  .muted {
    color: #9aa0aa;
    margin: 0.15rem 0;
    font-size: 0.9rem;
  }
  code {
    background: #1a1d24;
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
    color: #d6dae0;
  }
  .spinner {
    width: 34px;
    height: 34px;
    border: 3px solid #2a2f3a;
    border-top-color: #4c8bf5;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  .badge {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    font-weight: 700;
    font-size: 1.2rem;
  }
  .badge.ok {
    background: #163a2b;
    color: #46d18a;
  }
  .badge.err {
    background: #3a1a1a;
    color: #f57070;
  }
  button {
    margin-top: 0.6rem;
    padding: 0.5rem 1.1rem;
    border-radius: 8px;
    border: 1px solid #2a2f3a;
    background: #1a1d24;
    color: #e6e8ec;
    font-size: 0.9rem;
    cursor: pointer;
  }
  button:hover {
    border-color: #4c8bf5;
  }
</style>