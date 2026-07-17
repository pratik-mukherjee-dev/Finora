<script lang="ts">
    import {auth} from "$lib/stores/auth.svelte";
    import {goto} from "$app/navigation";
    import {onMount} from "svelte";
    import {request} from "$lib/api";
    import {registerScreen} from "$lib/shell/useScreen.svelte";
    import {modules} from "$lib/commands";

    onMount(() => {
        if (!auth.isAuthed) return void goto("/login");
        if (auth.needsSetup) return void goto("/setup");
        if (auth.needsFy) return void goto("/fy");
        void loadDashboard();
        void loadRecent();
    });

    // Backend contract: GET /api/reports/dashboard/?company=&date=
    type Today = {
        date: string; sales: number; purchases: number;
        received: number; paid: number; net_cash: number;
    };
    type Dashboard = {
        date: string; today: Today;
        open_receivable: number; open_payable: number; low_stock_count: number;
    };

    type VoucherRow = {
        id: number; number: string; date: string;
        party_name?: string; total_amount?: number; amount?: number;
    };
    type Recent = { kind: string; label: string; to: string; rows: VoucherRow[] };

    const today = new Date().toISOString().slice(0, 10);
    const companyId = $derived(auth.currentCompany?.id ?? null);
    const fyLabel = $derived(
        auth.fy ? `${auth.fy.start_date.slice(0, 4)}–${auth.fy.end_date.slice(0, 4)}` : "—"
    );

    let data = $state<Dashboard | null>(null);
    let loading = $state(false);
    let error = $state<string | null>(null);

    let recent = $state<Recent[]>([]);
    let loadingRecent = $state(false);

    const money = (n: number | undefined) => (Number(n) || 0).toFixed(2);

    async function loadDashboard() {
        if (!companyId) return;
        loading = true;
        error = null;
        try {
            const p = new URLSearchParams({company: String(companyId), date: today});
            data = await request<Dashboard>(`/api/reports/dashboard/?${p.toString()}`);
        } catch (e) {
            error = e instanceof Error ? e.message : "Could not load dashboard.";
            data = null;
        } finally {
            loading = false;
        }
    }

    // Recent vouchers for the panel tab. Best-effort; each list is small + latest-first not
    // guaranteed by the API, so we just take the tail few as "recent".
    async function loadRecent() {
        if (!companyId) return;
        loadingRecent = true;
        const defs = [
            {kind: "sale", label: "Sales", to: "/app/sale", url: "/api/vouchers/sales/"},
            {kind: "purchase", label: "Purchases", to: "/app/purchase", url: "/api/vouchers/purchases/"},
            {kind: "received", label: "Receipts", to: "/app/settle", url: "/api/vouchers/received/"},
            {kind: "payment", label: "Payments", to: "/app/settle", url: "/api/vouchers/payments/"},
        ];
        try {
            const out: Recent[] = [];
            for (const d of defs) {
                const p = new URLSearchParams({company: String(companyId)});
                const rows = await request<VoucherRow[] | { results?: VoucherRow[] }>(`${d.url}?${p.toString()}`);
                const list = Array.isArray(rows) ? rows : (rows?.results ?? []);
                out.push({kind: d.kind, label: d.label, to: d.to, rows: list.slice(-5).reverse()});
            }
            recent = out;
        } catch {
            recent = [];
        } finally {
            loadingRecent = false;
        }
    }

    function refresh() {
        void loadDashboard();
        void loadRecent();
    }

    // Quick-launch tiles reuse the module registry so nav stays single-source.
    const quick = modules.filter((m) => ["sale", "purchase", "settle", "stock"].includes(m.id));

    registerScreen(() => ({
        title: "Home",
        actions: [
            {id: "home-refresh", label: "Refresh", icon: "↻", shortcut: "Ctrl+R", run: refresh},
        ],
        shortcuts: [
            {id: "home-k-refresh", keychord: "ctrl+r", label: "Refresh", run: refresh},
        ],
        panel: [{id: "recent", title: "Recent", body: recentPanel}],
    }));
</script>

{#snippet recentPanel()}
    <div class="sidehead">
        <span class="muted">Latest vouchers</span>
        <button class="refresh" onclick={loadRecent} disabled={loadingRecent}>{loadingRecent ? "…" : "↻"}</button>
    </div>
    {#if recent.length === 0}
        <p class="muted">{loadingRecent ? "Loading…" : "Nothing yet."}</p>
    {:else}
        {#each recent as group (group.kind)}
            {#if group.rows.length > 0}
                <div class="rgroup">
                    <button class="rlabel" onclick={() => goto(group.to)}>{group.label} ›</button>
                    {#each group.rows as r (r.id)}
                        <div class="rrow">
                            <span class="rnum">#{r.number}</span>
                            <span class="rtot">{money(r.total_amount ?? r.amount)}</span>
                            <span class="rdate">{r.date}</span>
                        </div>
                    {/each}
                </div>
            {/if}
        {/each}
    {/if}
{/snippet}

<div class="home">
    <div class="hero">
        <h1>Welcome{auth.user ? `, ${auth.user.username}` : ""}</h1>
        <p class="muted">
            <strong>{auth.currentCompany?.name ?? "—"}</strong> · FY <strong>{fyLabel}</strong> ·
            {today}
        </p>
    </div>

    {#if error}
        <div class="banner err">{error}</div>
    {/if}

    <section class="kpis">
        <div class="kpi">
            <span class="klabel">Sales today</span>
            <span class="kval ok">{loading ? "…" : money(data?.today.sales)}</span>
        </div>
        <div class="kpi">
            <span class="klabel">Purchases today</span>
            <span class="kval">{loading ? "…" : money(data?.today.purchases)}</span>
        </div>
        <div class="kpi">
            <span class="klabel">Received today</span>
            <span class="kval ok">{loading ? "…" : money(data?.today.received)}</span>
        </div>
        <div class="kpi">
            <span class="klabel">Paid today</span>
            <span class="kval">{loading ? "…" : money(data?.today.paid)}</span>
        </div>
        <div class="kpi">
            <span class="klabel">Net cash today</span>
            <span class="kval" class:ok={(data?.today.net_cash ?? 0) >= 0}
                  class:neg={(data?.today.net_cash ?? 0) < 0}>{loading ? "…" : money(data?.today.net_cash)}</span>
        </div>
    </section>

    <section class="kpis second">
        <div class="kpi wide">
            <span class="klabel">Open receivable</span>
            <span class="kval ok">{loading ? "…" : money(data?.open_receivable)}</span>
        </div>
        <div class="kpi wide">
            <span class="klabel">Open payable</span>
            <span class="kval warn">{loading ? "…" : money(data?.open_payable)}</span>
        </div>
        <div class="kpi wide">
            <span class="klabel">Low stock items</span>
            <span class="kval" class:neg={(data?.low_stock_count ?? 0) > 0}>
                {loading ? "…" : (data?.low_stock_count ?? 0)}</span>
        </div>
    </section>

    <section class="quick">
        <h2>Start a voucher</h2>
        <div class="tiles">
            {#each quick as m (m.id)}
                <button class="tile" onclick={m.run} title={m.shortcut}>
                    <span class="tico">{m.icon}</span>
                    <span class="tlbl">{m.label}</span>
                    <span class="tsc">{m.shortcut}</span>
                </button>
            {/each}
        </div>
        <p class="muted small">Tip: <kbd>Ctrl</kbd>+<kbd>K</kbd> jumps anywhere · <kbd>Alt</kbd>+<kbd>1..9</kbd> modules.</p>
    </section>
</div>

<style>
    .home {
        padding: 28px;
        max-width: 900px;
    }

    .hero h1 {
        margin: 0 0 6px;
        font-size: 22px;
    }

    .muted {
        color: var(--text-muted);
        font-size: 14px;
        margin: 0;
    }

    .small {
        font-size: 13px;
        margin-top: 12px;
    }

    .banner {
        padding: 10px 14px;
        border-radius: var(--radius);
        margin: 16px 0;
        font-size: 14px;
    }

    .banner.err {
        background: var(--danger-soft);
        color: #ff9b9b;
        border: 1px solid var(--danger-border);
    }

    .kpis {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 12px;
        margin-top: 22px;
    }

    .kpis.second {
        grid-template-columns: repeat(3, 1fr);
    }

    .kpi {
        display: flex;
        flex-direction: column;
        gap: 8px;
        padding: 16px;
        background: var(--bg-panel);
        border: 1px solid var(--border);
        border-radius: 10px;
    }

    .klabel {
        font-size: 12px;
        color: var(--text-muted);
    }

    .kval {
        font-size: 22px;
        font-weight: 700;
    }

    .kval.ok {
        color: var(--ok);
    }

    .kval.warn {
        color: var(--warn);
    }

    .kval.neg {
        color: var(--danger);
    }

    .quick {
        margin-top: 30px;
    }

    .quick h2 {
        font-size: 16px;
        margin: 0 0 12px;
    }

    .tiles {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
    }

    .tile {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 6px;
        padding: 16px;
        background: var(--bg-panel);
        border: 1px solid var(--border);
        border-radius: 10px;
        cursor: pointer;
        color: var(--text);
    }

    .tile:hover {
        border-color: var(--accent);
        background: var(--accent-soft);
    }

    .tico {
        font-size: 20px;
        color: var(--accent-text);
    }

    .tlbl {
        font-size: 14px;
        font-weight: 600;
    }

    .tsc {
        font-size: 11px;
        color: var(--text-muted);
    }

    kbd {
        background: var(--bg-elevated);
        border: 1px solid var(--border-hi);
        border-radius: 4px;
        padding: 0 5px;
        font-size: 12px;
    }

    /* recent panel */
    .sidehead {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }

    .refresh {
        background: transparent;
        border: 1px solid var(--border-hi);
        color: var(--text-muted);
        width: 28px;
        height: 28px;
        border-radius: 6px;
        cursor: pointer;
    }

    .rgroup {
        margin-bottom: 14px;
    }

    .rlabel {
        background: transparent;
        border: none;
        color: var(--accent-text);
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
        padding: 0 0 6px;
    }

    .rrow {
        display: grid;
        grid-template-columns: 1fr auto;
        grid-template-areas: "num tot" "date tot";
        gap: 0 8px;
        padding: 5px 0;
        border-bottom: 1px solid var(--border);
        font-size: 12px;
    }

    .rnum {
        grid-area: num;
        font-weight: 600;
    }

    .rtot {
        grid-area: tot;
        align-self: center;
        color: var(--ok);
    }

    .rdate {
        grid-area: date;
        color: var(--text-muted);
    }
</style>
