<script lang="ts">
  import { auth } from "$lib/stores/auth.svelte";
  import { goto } from "$app/navigation";

  let username = $state("");
  let password = $state("");
  let error = $state<string | null>(null);
  let busy = $state(false);

  async function submit(e: Event) {
    e.preventDefault();
    error = null; busy = true;
    try {
      await auth.login(username, password);
      await goto("/app");
    } catch {
      error = "Invalid username or password";
    } finally {
      busy = false;
    }
  }
</script>

<main class="wrap">
  <form onsubmit={submit} class="card">
    <h1>Finora</h1>
    <input bind:value={username} placeholder="Username" autocomplete="username" autofocus />
    <input bind:value={password} type="password" placeholder="Password" autocomplete="current-password" />
    {#if error}<p class="err">{error}</p>{/if}
    <button disabled={busy || !username || !password}>{busy ? "Signing in…" : "Sign in"}</button>
  </form>
</main>

<style>
  .wrap { display: grid; place-items: center; height: 100vh; background: #0f1115; color: #e6e8ec; }
  .card { display: flex; flex-direction: column; gap: 12px; width: 280px; padding: 28px;
          background: #171a21; border-radius: 12px; }
  h1 { margin: 0 0 8px; font-size: 22px; text-align: center; }
  input, button { padding: 10px 12px; border-radius: 8px; border: 1px solid #2a2f3a;
                  background: #0f1115; color: #e6e8ec; font-size: 14px; }
  button { background: #2f6feb; border-color: #2f6feb; cursor: pointer; }
  button:disabled { opacity: .5; cursor: default; }
  .err { color: #ff6b6b; font-size: 13px; margin: 0; }
</style>
