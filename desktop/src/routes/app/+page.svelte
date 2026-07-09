<script lang="ts">
  import { auth } from "$lib/stores/auth.svelte";
  import { goto } from "$app/navigation";
  import { onMount } from "svelte";

  onMount(() => {
    if (!auth.isAuthed) return void goto("/login");
    if (auth.needsSetup) return void goto("/setup");
  });
</script>

{#if auth.isAuthed && !auth.needsSetup}
  <main class="shell">
    <header>
      <strong>Finora</strong>
      <span>{auth.user?.username} · {auth.mode}</span>
      <button onclick={() => auth.logout().then(() => goto("/login"))}>Logout</button>
    </header>
    <p class="body">Ready. {auth.companies.length} company(ies). Voucher screens come next.</p>
  </main>
{/if}

<style>
  .shell { height: 100vh; background: #0f1115; color: #e6e8ec; }
  header { display: flex; align-items: center; gap: 12px; padding: 12px 16px;
           border-bottom: 1px solid #2a2f3a; }
  header span { margin-left: auto; color: #9aa0aa; }
  .body { padding: 16px; }
  button { padding: 6px 12px; border-radius: 8px; border: 1px solid #2a2f3a;
           background: #171a21; color: #e6e8ec; cursor: pointer; }
</style>
