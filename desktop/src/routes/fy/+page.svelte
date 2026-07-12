<script lang="ts">
  import { auth } from "$lib/stores/auth.svelte";
  import { goto } from "$app/navigation";
  import { ApiError } from "$lib/api";
  import { onMount } from "svelte";

  // Indian FY convention: Apr 1 → Mar 31. Pick the window today falls in.
  function currentIndianFy() {
    const now = new Date();
    const y = now.getFullYear();
    const startYear = now.getMonth() >= 3 ? y : y - 1; // month 3 = April
    return { start: `${startYear}-04-01`, end: `${startYear + 1}-03-31` };
  }

  const def = currentIndianFy();
  let startDate = $state(def.start);
  let endDate = $state(def.end);
  let busy = $state(false);
  let error = $state<string | null>(null);

  onMount(() => {
    if (!auth.isAuthed) return void goto("/login");
    if (auth.needsSetup) return void goto("/setup");
    if (!auth.needsFy) return void goto("/app");
  });

  const label = $derived(
    startDate.length >= 4 && endDate.length >= 4
      ? `${startDate.slice(0, 4)}–${endDate.slice(0, 4)}`
      : ""
  );

  async function submit(e: Event) {
    e.preventDefault();
    if (busy) return;
    if (!startDate || !endDate) return;
    if (new Date(endDate) <= new Date(startDate)) {
      error = "End date must be after the start date.";
      return;
    }
    busy = true;
    error = null;
    try {
      await auth.ensureFy(startDate, endDate);
      await goto("/app");
    } catch (err) {
      error =
        err instanceof ApiError ? err.message : "Could not create the financial year.";
      busy = false; // on success we navigate away, so only reset on failure
    }
  }
</script>

<main class="wrap">
  <form class="card" onsubmit={submit}>
    <h1>Set up your financial year</h1>
    <p class="muted">
      Every voucher is bound to the active financial year. You can close it and
      roll into the next one later.
    </p>

    <label class="field">
      <span>Start date</span>
      <input type="date" bind:value={startDate} />
    </label>

    <label class="field">
      <span>End date</span>
      <input type="date" bind:value={endDate} />
    </label>

    {#if label}<p class="tag">FY {label}</p>{/if}
    {#if error}<p class="err">{error}</p>{/if}

    <button class="opt" disabled={busy || !startDate || !endDate}>
      {busy ? "Creating…" : "Start bookkeeping"}
    </button>
  </form>
</main>

<style>
  .wrap { display: grid; place-items: center; height: 100vh; background: #0f1115; color: #e6e8ec; }
  .card { display: flex; flex-direction: column; gap: 12px; width: 340px; padding: 28px;
          background: #171a21; border-radius: 12px; }
  h1 { margin: 0; font-size: 20px; }
  .muted { color: #9aa0aa; font-size: 13px; margin: 0 0 4px; line-height: 1.45; }
  .field { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: #9aa0aa; }
  input { padding: 10px 12px; border-radius: 8px; border: 1px solid #2a2f3a;
          background: #0f1115; color: #e6e8ec; font-size: 14px; }
  .tag { align-self: flex-start; margin: 0; padding: 4px 10px; border-radius: 999px;
         background: #16233b; color: #6ea8ff; font-size: 12px; font-weight: 600; }
  .opt { margin-top: 4px; padding: 10px 12px; border-radius: 8px; border: 1px solid #2f6feb;
         background: #2f6feb; color: #fff; font-size: 14px; cursor: pointer; }
  .opt:disabled { opacity: .5; cursor: default; }
  .err { color: #ff6b6b; font-size: 13px; margin: 0; }
</style>