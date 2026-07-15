<script lang="ts">
  import { auth } from "$lib/stores/auth.svelte";
  import { goto } from "$app/navigation";
  import { onMount } from "svelte";

  type Section = "home" | "purchase" | "sale" | "payment" | "stock" | "reports";
  let section = $state<Section>("home");

  // Route guard: bounce to the correct earlier step if prerequisites are missing.
  onMount(() => {
    if (!auth.isAuthed) return void goto("/login");
    if (auth.needsSetup) return void goto("/setup");
    if (auth.needsFy) return void goto("/fy");
  });

  const fyLabel = $derived(
    auth.fy
      ? `${auth.fy.start_date.slice(0, 4)}–${auth.fy.end_date.slice(0, 4)}`
      : "—"
  );

  const nav: { id: Section; label: string }[] = [
    { id: "home", label: "Home" },
    { id: "purchase", label: "Purchase" },
    { id: "sale", label: "Sale" },
    { id: "payment", label: "Payment / Received" },
    { id: "stock", label: "Stock" },
    { id: "reports", label: "Reports" },
  ];

  // Sections with a dedicated route navigate there; the rest render inline.
  const routed: Partial<Record<Section, string>> = {
    purchase: "/app/purchase",
  };

  function selectSection(id: Section) {
    const path = routed[id];
    if (path) {
      void goto(path);
      return;
    }
    section = id;
  }

  async function onCompanyChange(e: Event) {
    const id = Number((e.target as HTMLSelectElement).value);
    await auth.setCurrentCompany(id);
  }

  async function doLogout() {
    await auth.logout();
    await goto("/login");
  }
</script>

<div class="shell">
    <aside class="rail">
        <div class="brand">Finora</div>
        <nav>
          {#each nav as item (item.id)}
            <button
                    class="navbtn"
            class:active={ section === item.id }
          onclick={ () => selectSection(item.id) }
            >
            {item.label}
            </button>
          {/each}
        </nav>
        <button class="logout" onclick={ doLogout }>Log out</button>
    </aside>

    <section class="main">
        <header class="topbar">
            <div class="ctx">
              {#if auth.mode === "multi"}
                <select class="company" onchange={ onCompanyChange }>
                  {#each auth.companies as c (c.id)}
                    <option value={ c.id } selected={ c.id === auth.currentCompany?.id }>
                    {c.name}
                    </option>
                  {/each}
                </select>
              {:else}
                <span class="company-static">{auth.currentCompany?.name ?? "—"}</span>
              {/if}
                <span class="fybadge">FY { fyLabel }</span>
            </div>
            <div class="user">{auth.user?.username ?? ""}</div>
        </header>

        <div class="content">
          {#if section === "home"}
            <h1>Welcome{ auth.user ? `, ${auth.user.username}` : "" }</h1>
            <p class="muted">
                Company <strong>{auth.currentCompany?.name ?? "—"}</strong>, financial
                year <strong>{fyLabel}</strong>. Pick a section from the left to begin.
            </p>
          {:else if section === "sale"}
            <h1>Sale</h1>
            <p class="muted">Sale master entry — planned.</p>
          {:else if section === "payment"}
            <h1>Payment / Received</h1>
            <p class="muted">Party reconciliation — planned.</p>
          {:else if section === "stock"}
            <h1>Stock</h1>
            <p class="muted">Stock ledger & conversion — planned.</p>
          {:else if section === "reports"}
            <h1>Reports</h1>
            <p class="muted">Filterable reports & daily sheet — planned.</p>
          {/if}
        </div>
    </section>
</div>

<style>
  :global(body) { margin: 0; }
  .shell { display: grid; grid-template-columns: 220px 1fr; height: 100vh;
           background: #0f1115; color: #e6e8ec;
           font-family: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif; }
  .rail { display: flex; flex-direction: column; gap: 6px; padding: 16px 12px;
          background: #12151c; border-right: 1px solid #1f2530; }
  .brand { font-size: 18px; font-weight: 700; padding: 6px 8px 14px; color: #6ea8ff; }
  nav { display: flex; flex-direction: column; gap: 4px; flex: 1; }
  .navbtn { text-align: left; padding: 10px 12px; border-radius: 8px; border: none;
            background: transparent; color: #c3c8d2; font-size: 14px; cursor: pointer; }
  .navbtn:hover { background: #1a1f28; }
  .navbtn.active { background: #16233b; color: #6ea8ff; font-weight: 600; }
  .logout { margin-top: auto; padding: 9px 12px; border-radius: 8px;
            border: 1px solid #2a2f3a; background: transparent; color: #9aa0aa;
            font-size: 13px; cursor: pointer; }
  .logout:hover { border-color: #ff6b6b; color: #ff6b6b; }
  .main { display: flex; flex-direction: column; min-width: 0; }
  .topbar { display: flex; align-items: center; justify-content: space-between;
            padding: 12px 20px; border-bottom: 1px solid #1f2530; background: #12151c; }
  .ctx { display: flex; align-items: center; gap: 12px; }
  .company { padding: 6px 10px; border-radius: 8px; border: 1px solid #2a2f3a;
             background: #0f1115; color: #e6e8ec; font-size: 13px; }
  .company-static { font-size: 14px; font-weight: 600; }
  .fybadge { padding: 4px 10px; border-radius: 999px; background: #16233b;
             color: #6ea8ff; font-size: 12px; font-weight: 600; }
  .user { font-size: 13px; color: #9aa0aa; }
  .content { padding: 28px; overflow: auto; }
  h1 { margin: 0 0 8px; font-size: 22px; }
  .muted { color: #9aa0aa; font-size: 14px; line-height: 1.5; margin: 0; }
</style>
