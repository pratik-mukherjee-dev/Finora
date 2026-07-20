<script lang="ts">
    import {auth} from "$lib/stores/auth.svelte";
    import {goto} from "$app/navigation";
    import {onMount} from "svelte";
    import {request, ApiError} from "$lib/api";
    import {registerScreen} from "$lib/shell/useScreen.svelte";

    onMount(() => {
        if (!auth.isAuthed) return void goto("/login");
        if (auth.needsSetup) return void goto("/setup");
        if (auth.needsFy) return void goto("/fy");
        void loadModes();
        void loadLedgers();
        void loadSeqs();
    });

    // ── types ──────────────────────────────────────────────────────────────────
    type SettlementMode = { id: number; name: string; is_system: boolean; is_active: boolean; sort_order: number; };
    type Ledger = { id: number; company: number | null; name: string; kind: string; is_system: boolean; gst_rate: number | null; };
    type Seq = { id: number; company: number; financial_year: number; voucher_type: string; template: string; high_water: number; };

    // ── state ──────────────────────────────────────────────────────────────────
    let busy = $state(false);
    let modeError = $state<string | null>(null);

    // settlement modes
    let modes = $state<SettlementMode[]>([]);
    let newModeName = $state("");
    let modesBusy = $state(false);
    let modesError = $state<string | null>(null);

    // ledgers
    let ledgers = $state<Ledger[]>([]);
    let newLedgerName = $state("");
    let newLedgerKind = $state<string>("DISCOUNT");
    let ledgersBusy = $state(false);
    let ledgersError = $state<string | null>(null);

    // voucher numbering
    let seqs = $state<Seq[]>([]);
    let seqsBusy = $state(false);
    let seqsError = $state<string | null>(null);

    // new company
    let newCompanyName = $state("");
    let companyBusy = $state(false);
    let companyError = $state<string | null>(null);

    // derived
    const companyId = $derived(auth.currentCompany?.id ?? null);
    const mode = $derived(auth.mode);
    const allowsMulti = $derived(auth.allowsMulti);
    const maxCompanies = $derived(auth.maxCompanies);
    const companyCount = $derived(auth.companies.length);
    const canAddCompany = $derived(companyCount < maxCompanies);
    const segregation = $derived(auth.setting?.segregation_enabled ?? false);

    // ── company mode ───────────────────────────────────────────────────────────
    async function switchToMulti() {
        busy = true; modeError = null;
        try {
            await auth.enableMulti(false);
        } catch (e) {
            modeError = e instanceof ApiError ? e.message : "Could not switch to multi-company mode.";
        } finally { busy = false; }
    }

    async function switchToSingle() {
        busy = true; modeError = null;
        try {
            await auth.switchToSingle();
        } catch (e) {
            modeError = e instanceof ApiError ? e.message : "Could not switch to single-company mode.";
        } finally { busy = false; }
    }

    async function toggleSegregation() {
        busy = true; modeError = null;
        try {
            await auth.setSegregation(!segregation);
            await auth.reloadContext();
        } catch (e) {
            modeError = e instanceof ApiError ? e.message : "Could not update segregation.";
        } finally { busy = false; }
    }

    async function addCompany() {
        const name = newCompanyName.trim();
        if (!name) return;
        companyBusy = true; companyError = null;
        try {
            await auth.createCompany(name, false);
            newCompanyName = "";
        } catch (e) {
            companyError = e instanceof ApiError ? e.message : "Could not create company.";
        } finally { companyBusy = false; }
    }

    // ── settlement modes ───────────────────────────────────────────────────────
    async function loadModes() {
        try {
            const rows = await request<SettlementMode[]>("/api/accounts/settlement-modes/");
            modes = Array.isArray(rows) ? rows : [];
        } catch { modes = []; }
    }

    async function addMode() {
        const name = newModeName.trim();
        if (!name) return;
        modesBusy = true; modesError = null;
        try {
            await request("/api/accounts/settlement-modes/", {
                method: "POST", body: JSON.stringify({name, sort_order: modes.length}),
            });
            newModeName = "";
            await loadModes();
        } catch (e) {
            modesError = e instanceof ApiError ? e.message : "Could not add mode.";
        } finally { modesBusy = false; }
    }

    async function toggleModeActive(m: SettlementMode) {
        try {
            await request(`/api/accounts/settlement-modes/${m.id}/`, {
                method: "PATCH", body: JSON.stringify({is_active: !m.is_active}),
            });
            await loadModes();
        } catch {}
    }

    async function deleteMode(m: SettlementMode) {
        if (m.is_system) return;
        try {
            await request(`/api/accounts/settlement-modes/${m.id}/`, {method: "DELETE"});
            await loadModes();
        } catch (e) {
            modesError = e instanceof ApiError ? e.message : "Could not delete.";
        }
    }

    // ── charge ledgers ─────────────────────────────────────────────────────────
    async function loadLedgers() {
        if (!companyId) return;
        try {
            const p = new URLSearchParams({company: String(companyId)});
            const rows = await request<Ledger[]>(`/api/ledgers/?${p.toString()}`);
            ledgers = Array.isArray(rows) ? rows : [];
        } catch { ledgers = []; }
    }

    async function addLedger() {
        const name = newLedgerName.trim();
        if (!name || !companyId) return;
        ledgersBusy = true; ledgersError = null;
        try {
            await request("/api/ledgers/", {
                method: "POST",
                body: JSON.stringify({name, kind: newLedgerKind, company: companyId}),
            });
            newLedgerName = "";
            await loadLedgers();
        } catch (e) {
            ledgersError = e instanceof ApiError ? e.message : "Could not add ledger.";
        } finally { ledgersBusy = false; }
    }

    async function deleteLedger(l: Ledger) {
        if (l.is_system) return;
        try {
            await request(`/api/ledgers/${l.id}/`, {method: "DELETE"});
            await loadLedgers();
        } catch (e) {
            ledgersError = e instanceof ApiError ? e.message : "Could not delete.";
        }
    }

    // ── voucher numbering ──────────────────────────────────────────────────────
    async function loadSeqs() {
        if (!companyId) return;
        try {
            const p = new URLSearchParams({company: String(companyId)});
            const rows = await request<Seq[]>(`/api/vouchers/number-seqs/?${p.toString()}`);
            seqs = Array.isArray(rows) ? rows : [];
        } catch { seqs = []; }
    }

    async function saveTemplate(s: Seq, newTemplate: string) {
        seqsBusy = true; seqsError = null;
        try {
            await request(`/api/vouchers/number-seqs/${s.id}/`, {
                method: "PATCH", body: JSON.stringify({template: newTemplate}),
            });
            await loadSeqs();
        } catch (e) {
            seqsError = e instanceof ApiError ? e.message : "Could not save template.";
        } finally { seqsBusy = false; }
    }

    function previewNumber(template: string, hw: number): string {
        try { return template.replace(/\{seq[^}]*\}/, template.includes("{seq") ? template.split("{")[0] + String(hw + 1).padStart(4, "0") : "?"); } catch { return "?"; }
        // Proper preview: simulate the format
    }

    function handleTemplateChange(s: Seq, e: Event) {
        const input = e.currentTarget as  HTMLInputElement;
        void saveTemplate(s, input.value)
    }

    function formatPreview(template: string, n: number): string {
        try {
            // Simulate Python's {seq:04d} style formatting
            const match = template.match(/\{seq(?::(\d*)d)?\}/);
            if (!match) return "Invalid template";
            const pad = parseInt(match[1] || "0", 10);
            const numStr = String(n).padStart(pad, "0");
            return template.replace(/\{seq[^}]*\}/, numStr);
        } catch { return "Invalid template"; }
    }

    const VOUCHER_LABELS: Record<string, string> = {
        SALE: "Sale", PURCHASE: "Purchase", RECEIVED: "Receipt", PAYMENT: "Payment",
    };

    const shell = registerScreen(() => ({
        title: "Settings",
        actions: [],
        shortcuts: [],
        panel: [],
    }));
</script>

<div class="wrap">
    <!-- ── Company Mode ──────────────────────────────────────── -->
    <section class="card">
        <h2>Company Mode</h2>
        <p class="hint">Your license: <strong>{auth.license?.plan ?? "base"}</strong>
            · max {maxCompanies} {maxCompanies === 1 ? "company" : "companies"}
            {#if allowsMulti}<span class="tag ok">multi unlocked</span>{/if}
        </p>

        <div class="mode-toggle">
            <button class:active={mode === "single"} disabled={busy || mode === "single"} onclick={switchToSingle}>
                Single
            </button>
            <button class:active={mode === "multi"} disabled={busy || mode === "multi" || !allowsMulti}
                    onclick={switchToMulti}>
                Multi
            </button>
        </div>

        {#if mode === "multi"}
            <label class="check">
                <input type="checkbox" checked={segregation} onchange={toggleSegregation} disabled={busy}/>
                Enable segregation (split sales across companies)
            </label>
        {/if}

        {#if modeError}<p class="err">{modeError}</p>{/if}

        <h3>Companies ({companyCount} / {maxCompanies})</h3>
        <ul class="list">
            {#each auth.companies as c (c.id)}
                <li class:active={c.id === auth.currentCompany?.id}>
                    <span>{c.name}</span>
                    {#if c.is_default}<span class="tag">default</span>{/if}
                </li>
            {/each}
        </ul>
        {#if canAddCompany}
            <div class="add-row">
                <input bind:value={newCompanyName} placeholder="New company name…"
                       onkeydown={(e) => { if (e.key === "Enter") addCompany(); }}/>
                <button disabled={companyBusy || !newCompanyName.trim()} onclick={addCompany}>
                    {companyBusy ? "…" : "Add"}
                </button>
            </div>
        {:else}
            <p class="hint">Company limit reached for your license.</p>
        {/if}
        {#if companyError}<p class="err">{companyError}</p>{/if}
    </section>

    <!-- ── Settlement Modes ──────────────────────────────────── -->
    <section class="card">
        <h2>Settlement Modes</h2>
        <p class="hint">Used in Settle, Sale, and Purchase for payment method tracking.</p>
        <ul class="list">
            {#each modes as m (m.id)}
                <li>
                    <span class:muted={!m.is_active}>{m.name}</span>
                    <span class="actions">
                        {#if m.is_system}<span class="tag">system</span>{/if}
                        <button class="sm" class:active={m.is_active} onclick={() => toggleModeActive(m)}>
                            {m.is_active ? "Active" : "Inactive"}
                        </button>
                        {#if !m.is_system}
                            <button class="sm del" onclick={() => deleteMode(m)}>✕</button>
                        {/if}
                    </span>
                </li>
            {/each}
        </ul>
        <div class="add-row">
            <input bind:value={newModeName} placeholder="New mode name…"
                   onkeydown={(e) => { if (e.key === "Enter") addMode(); }}/>
            <button disabled={modesBusy || !newModeName.trim()} onclick={addMode}>
                {modesBusy ? "…" : "Add"}
            </button>
        </div>
        {#if modesError}<p class="err">{modesError}</p>{/if}
    </section>

    <!-- ── Charge Ledgers ────────────────────────────────────── -->
    <section class="card">
        <h2>Charge Ledgers</h2>
        <p class="hint">Discount, round-off, and tax ledgers used in the charges section of Sale and Purchase.</p>
        <ul class="list">
            {#each ledgers as l (l.id)}
                <li>
                    <span>{l.name}</span>
                    <span class="actions">
                        <span class="tag">{l.kind}</span>
                        {#if l.is_system}<span class="tag">system</span>{/if}
                        {#if !l.is_system}
                            <button class="sm del" onclick={() => deleteLedger(l)}>✕</button>
                        {/if}
                    </span>
                </li>
            {/each}
        </ul>
        <div class="add-row">
            <select bind:value={newLedgerKind}>
                <option value="DISCOUNT">Discount</option>
                <option value="ROUND_OFF">Round Off</option>
                <option value="TAX">Tax</option>
                <option value="OTHER">Other</option>
            </select>
            <input bind:value={newLedgerName} placeholder="New ledger name…"
                   onkeydown={(e) => { if (e.key === "Enter") addLedger(); }}/>
            <button disabled={ledgersBusy || !newLedgerName.trim()} onclick={addLedger}>
                {ledgersBusy ? "…" : "Add"}
            </button>
        </div>
        {#if ledgersError}<p class="err">{ledgersError}</p>{/if}
    </section>

    <!-- ── Voucher Numbering ─────────────────────────────────── -->
    <section class="card">
        <h2>Voucher Numbering</h2>
        <p class="hint">Edit the template for each voucher type. Use <code>{"{seq:04d}"}</code> for zero-padded numbers.
            Sequences are created automatically on first use.</p>
        {#if seqs.length === 0}
            <p class="muted">No sequences yet — they appear after the first voucher of each type is saved.</p>
        {:else}
            <ul class="list seqlist">
                {#each seqs as s (s.id)}
                    {@const label = VOUCHER_LABELS[s.voucher_type] ?? s.voucher_type}
                    <li>
                        <span class="seqlabel">{label}</span>
                        <input class="seqinput" value={s.template}
                               onchange={(e) => handleTemplateChange(s, e)}/>
                        <span class="seqpreview">Next: {formatPreview(s.template, s.high_water + 1)}</span>
                    </li>
                {/each}
            </ul>
        {/if}
        {#if seqsError}<p class="err">{seqsError}</p>{/if}
    </section>
</div>

<style>
    .wrap {
        padding: 20px 28px 40px;
        box-sizing: border-box;
        max-width: 680px;
        display: flex;
        flex-direction: column;
        gap: 24px;
    }

    .card {
        border: 1px solid var(--border);
        border-radius: 10px;
        background: var(--bg-elevated);
        padding: 18px 20px;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }

    h2 {
        margin: 0;
        font-size: 15px;
        color: var(--text);
    }

    h3 {
        margin: 8px 0 0;
        font-size: 13px;
        color: var(--text);
    }

    .hint {
        margin: 0;
        font-size: 12px;
        color: var(--text-muted);
    }

    code {
        background: rgba(255, 255, 255, .06);
        padding: 1px 5px;
        border-radius: 4px;
        font-size: 12px;
    }

    .muted {
        color: var(--text-muted);
        font-size: 13px;
    }

    .err {
        margin: 0;
        font-size: 12px;
        color: #ff9b9b;
    }

    .tag {
        font-size: 10px;
        text-transform: uppercase;
        padding: 1px 6px;
        border-radius: 4px;
        background: rgba(255, 255, 255, .06);
        color: var(--text-muted);
    }

    .tag.ok {
        background: rgba(52, 211, 153, .12);
        color: #34d399;
    }

    /* ── mode toggle ── */
    .mode-toggle {
        display: inline-flex;
        border: 1px solid var(--border-hi);
        border-radius: var(--radius);
        overflow: hidden;
    }

    .mode-toggle button {
        padding: 8px 20px;
        background: transparent;
        border: none;
        color: var(--text-muted);
        cursor: pointer;
        font-size: 13px;
    }

    .mode-toggle button.active {
        background: var(--accent);
        color: #fff;
    }

    .mode-toggle button:disabled {
        opacity: .5;
        cursor: default;
    }

    .check {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        color: var(--text-muted);
        cursor: pointer;
    }

    /* ── list + add row ── */
    .list {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 4px;
    }

    .list li {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 10px;
        border-radius: 6px;
        font-size: 13px;
        color: var(--text);
    }

    .list li.active {
        background: rgba(47, 111, 235, .08);
    }

    .list li:hover {
        background: rgba(255, 255, 255, .03);
    }

    .actions {
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .sm {
        padding: 2px 8px;
        font-size: 11px;
        border-radius: 4px;
        border: 1px solid var(--border-hi);
        background: transparent;
        color: var(--text-muted);
        cursor: pointer;
    }

    .sm.active {
        border-color: rgba(52, 211, 153, .3);
        color: #34d399;
    }

    .sm.del {
        border-color: rgba(255, 155, 155, .2);
        color: #ff9b9b;
    }

    .sm.del:hover {
        background: rgba(255, 155, 155, .1);
    }

    .add-row {
        display: flex;
        gap: 8px;
        align-items: center;
    }

    .add-row input, .add-row select {
        flex: 1;
        padding: 7px 10px;
        border-radius: var(--radius);
        border: 1px solid var(--border-hi);
        background: var(--bg-app);
        color: var(--text);
        font-size: 13px;
        box-sizing: border-box;
    }

    .add-row select {
        flex: 0 0 auto;
        width: 130px;
    }

    .add-row button {
        padding: 7px 14px;
        border-radius: var(--radius);
        border: 1px solid var(--accent);
        background: var(--accent);
        color: #fff;
        cursor: pointer;
        font-size: 13px;
        white-space: nowrap;
    }

    .add-row button:disabled {
        opacity: .5;
        cursor: default;
    }

    /* ── voucher numbering ── */
    .seqlist li {
        display: grid;
        grid-template-columns: 100px 1fr auto;
        gap: 10px;
        align-items: center;
    }

    .seqlabel {
        font-size: 12px;
        color: var(--text-muted);
        font-weight: 600;
    }

    .seqinput {
        padding: 6px 8px;
        border-radius: var(--radius);
        border: 1px solid var(--border-hi);
        background: var(--bg-app);
        color: var(--text);
        font-size: 13px;
        font-family: monospace;
        box-sizing: border-box;
        width: 100%;
    }

    .seqpreview {
        font-size: 11px;
        color: var(--text-muted);
        white-space: nowrap;
    }
</style>