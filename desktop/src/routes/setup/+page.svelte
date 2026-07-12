<script lang="ts">
  import { auth } from "$lib/stores/auth.svelte";
  import { goto } from "$app/navigation";
  import { ApiError } from "$lib/api";
  import { onMount } from "svelte";

  let step = $state<"mode" | "company">("mode");
  let segregation = $state(false);
  let name = $state("");
  let busy = $state(false);
  let error = $state<string | null>(null);

  onMount(() => {
    if (!auth.isAuthed) return void goto("/login");
    if (!auth.needsSetup) return void goto(auth.needsFy ? "/fy" : "/app");
    if (auth.mode === "multi") step = "company";
  });

  function chooseSingle() { step = "company"; }

  async function chooseMulti() {
    busy = true; error = null;
    try {
      await auth.enableMulti(segregation);
      step = "company";
    } catch (e) {
      error = e instanceof ApiError && e.status === 400
        ? "Multi-company is not unlocked on your license."
        : "Could not switch to multi-company mode.";
    } finally { busy = false; }
  }

  async function createCompany(e: Event) {
    e.preventDefault();
    busy = true; error = null;
    try {
      await auth.createCompany(name.trim(), true);
      await goto(auth.needsFy ? "/fy" : "/app");
    } catch (e) {
      error = e instanceof ApiError ? e.message : "Could not create company.";
    } finally { busy = false; }
  }
</script>

<main class="wrap">
  {#if step === "mode"}
    <div class="card">
      <h1>Choose mode</h1>
      <p class="muted">Locked to your license. You can upgrade to multi later.</p>
      <button class="opt" onclick={chooseSingle} disabled={busy}>Single company</button>
      <label class="seg">
        <input type="checkbox" bind:checked={segregation} /> Enable segregation
      </label>
      <button class="opt alt" onclick={chooseMulti} disabled={busy}>
        {busy ? "Working…" : "Multi company"}
      </button>
      {#if error}<p class="err">{error}</p>{/if}
    </div>
  {:else}
    <form class="card" onsubmit={createCompany}>
      <h1>Create your company</h1>
      <input bind:value={name} placeholder="Company name" autofocus />
      {#if error}<p class="err">{error}</p>{/if}
      <button class="opt" disabled={busy || !name.trim()}>
        {busy ? "Creating…" : "Continue"}
      </button>
    </form>
  {/if}
</main>

<style>
  .wrap { display: grid; place-items: center; height: 100vh; background: #0f1115; color: #e6e8ec; }
  .card { display: flex; flex-direction: column; gap: 12px; width: 300px; padding: 28px;
          background: #171a21; border-radius: 12px; }
  h1 { margin: 0; font-size: 20px; }
  .muted { color: #9aa0aa; font-size: 13px; margin: 0; }
  input { padding: 10px 12px; border-radius: 8px; border: 1px solid #2a2f3a;
          background: #0f1115; color: #e6e8ec; }
  .opt { padding: 10px 12px; border-radius: 8px; border: 1px solid #2f6feb;
         background: #2f6feb; color: #fff; cursor: pointer; }
  .opt.alt { background: transparent; }
  .opt:disabled { opacity: .5; cursor: default; }
  .seg { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #9aa0aa; }
  .err { color: #ff6b6b; font-size: 13px; margin: 0; }
</style>
