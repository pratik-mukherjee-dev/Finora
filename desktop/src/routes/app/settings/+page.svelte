<script lang="ts">
    import {auth} from "$lib/stores/auth.svelte";
    import {goto} from "$app/navigation";
    import {onMount, tick} from "svelte";
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
    type SettlementMode = {
        id: number; name: string; category: "CASH" | "BANK";
        bank_type: "UPI" | "TRANSFER" | "CHEQUE" | "OTHER" | null;
        is_system: boolean; is_active: boolean; sort_order: number;
        needs_reference: boolean;
    };
    type Ledger = {
        id: number;
        company: number | null;
        name: string;
        kind: string;
        is_system: boolean;
        gst_rate: number | null;
    };
    type Seq = {
        id: number;
        company: number;
        financial_year: number;
        voucher_type: string;
        template: string;
        high_water: number;
    };

    // ── navigation ────────────────────────────────────────────────────────────
    type NavSection = {
        id: string;
        label: string;
        icon: string;
        description: string;
        keywords: string[];
    };

    const sections: NavSection[] = [
        {
            id: "company",
            label: "Company",
            icon: "⌂",
            description: "Mode, companies, segregation",
            keywords: ["company", "mode", "single", "multi", "segregation", "license"]
        },
        {
            id: "settlement",
            label: "Settlement Modes",
            icon: "↗",
            description: "Payment & receipt methods",
            keywords: ["settlement", "mode", "payment", "cash", "bank", "upi", "transfer", "cheque"]
        },
        {
            id: "ledgers",
            label: "Charge Ledgers",
            icon: "▤",
            description: "Discount, tax, round-off",
            keywords: ["ledger", "charge", "discount", "tax", "round", "gst"]
        },
        {
            id: "numbering",
            label: "Voucher Numbering",
            icon: "＃",
            description: "Invoice & receipt sequences",
            keywords: ["voucher", "number", "sequence", "template", "invoice", "receipt", "sale", "purchase"]
        },
    ];

    let activeSection = $state("company");
    let searchQuery = $state("");
    let searchInput = $state<HTMLInputElement | null>(null);

    const filteredSections = $derived.by(() => {
        if (!searchQuery.trim()) return sections;
        const q = searchQuery.toLowerCase().trim();
        return sections.filter((s) =>
            s.label.toLowerCase().includes(q) ||
            s.description.toLowerCase().includes(q) ||
            s.keywords.some((k) => k.includes(q))
        );
    });

    // Auto-select first match when search narrows results
    $effect(() => {
        if (searchQuery.trim() && filteredSections.length > 0) {
            const currentVisible = filteredSections.find((s) => s.id === activeSection);
            if (!currentVisible) activeSection = filteredSections[0].id;
        }
    });

    function selectSection(id: string) {
        activeSection = id;
        searchQuery = "";
    }

    function onSearchKeydown(e: KeyboardEvent) {
        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
            e.preventDefault();
            const idx = filteredSections.findIndex((s) => s.id === activeSection);
            const next = e.key === "ArrowDown"
                ? Math.min(idx + 1, filteredSections.length - 1)
                : Math.max(idx - 1, 0);
            activeSection = filteredSections[next].id;
        } else if (e.key === "Enter") {
            e.preventDefault();
            if (filteredSections.length > 0) {
                activeSection = filteredSections[0].id;
                searchQuery = "";
            }
        } else if (e.key === "Escape") {
            searchQuery = "";
            searchInput?.blur();
        }
    }

    // ── state ──────────────────────────────────────────────────────────────────
    let busy = $state(false);
    let modeError = $state<string | null>(null);

    // settlement modes
    let modes = $state<SettlementMode[]>([]);
    let newModeName = $state("");
    let newModeCategory = $state<"CASH" | "BANK">("CASH");
    let newModeBankType = $state<"UPI" | "TRANSFER" | "CHEQUE" | "OTHER" | "">("");
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
    const companyMode = $derived(auth.mode);
    const allowsMulti = $derived(auth.allowsMulti);
    const maxCompanies = $derived(auth.maxCompanies);
    const companyCount = $derived(auth.companies.length);
    const canAddCompany = $derived(companyCount < maxCompanies);
    const segregation = $derived(auth.setting?.segregation_enabled ?? false);

    // ── company mode ───────────────────────────────────────────────────────────
    async function switchToMulti() {
        busy = true;
        modeError = null;
        try {
            await auth.enableMulti(false);
        } catch (e) {
            modeError = e instanceof ApiError ? e.message : "Could not switch to multi-company mode.";
        } finally {
            busy = false;
        }
    }

    async function switchToSingle() {
        busy = true;
        modeError = null;
        try {
            await auth.switchToSingle();
        } catch (e) {
            modeError = e instanceof ApiError ? e.message : "Could not switch to single-company mode.";
        } finally {
            busy = false;
        }
    }

    async function toggleSegregation() {
        busy = true;
        modeError = null;
        try {
            await auth.setSegregation(!segregation);
            await auth.reloadContext();
        } catch (e) {
            modeError = e instanceof ApiError ? e.message : "Could not update segregation.";
        } finally {
            busy = false;
        }
    }

    async function addCompany() {
        const name = newCompanyName.trim();
        if (!name) return;
        companyBusy = true;
        companyError = null;
        try {
            await auth.createCompany(name, false);
            newCompanyName = "";
        } catch (e) {
            companyError = e instanceof ApiError ? e.message : "Could not create company.";
        } finally {
            companyBusy = false;
        }
    }

    async function upgradeLicense() {
        busy = true;
        modeError = null;
        try {
            await auth.upgradeLicense(5);
        } catch (e) {
            modeError = e instanceof ApiError ? e.message : "Could not upgrade license.";
        } finally {
            busy = false;
        }
    }

    async function downgradeLicense() {
        busy = true;
        modeError = null;
        try {
            await auth.downgradeLicense();
        } catch (e) {
            modeError = e instanceof ApiError ? e.message : "Could not downgrade license.";
        } finally {
            busy = false;
        }
    }

    async function toggleCompanyActive(c: { id: number; is_active: boolean }) {
        companyBusy = true;
        companyError = null;
        try {
            await auth.toggleCompanyActive(c.id, !c.is_active);
        } catch (e) {
            companyError = e instanceof ApiError ? e.message : "Could not update company.";
        } finally {
            companyBusy = false;
        }
    }

    async function makeDefault(c: { id: number }) {
        companyBusy = true;
        companyError = null;
        try {
            await auth.makeDefaultCompany(c.id);
        } catch (e) {
            companyError = e instanceof ApiError ? e.message : "Could not set default.";
        } finally {
            companyBusy = false;
        }
    }

    // ── settlement modes ───────────────────────────────────────────────────────
    async function loadModes() {
        try {
            const rows = await request<SettlementMode[]>("/api/accounts/settlement-modes/");
            modes = Array.isArray(rows) ? rows : [];
        } catch {
            modes = [];
        }
    }

    async function addMode() {
        const name = newModeName.trim();
        if (!name) return;
        modesBusy = true;
        modesError = null;
        try {
            const body: Record<string, unknown> = {
                name,
                sort_order: modes.length,
                category: newModeCategory,
            };
            if (newModeCategory === "BANK" && newModeBankType) {
                body.bank_type = newModeBankType;
            } else {
                body.bank_type = null;
            }
            await request("/api/accounts/settlement-modes/", {
                method: "POST", body: JSON.stringify(body),
            });
            newModeName = "";
            newModeCategory = "CASH";
            newModeBankType = "";
            await loadModes();
        } catch (e) {
            modesError = e instanceof ApiError ? e.message : "Could not add mode.";
        } finally {
            modesBusy = false;
        }
    }

    async function toggleModeActive(m: SettlementMode) {
        try {
            await request(`/api/accounts/settlement-modes/${m.id}/`, {
                method: "PATCH", body: JSON.stringify({is_active: !m.is_active}),
            });
            await loadModes();
        } catch {
        }
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
        } catch {
            ledgers = [];
        }
    }

    async function addLedger() {
        const name = newLedgerName.trim();
        if (!name || !companyId) return;
        ledgersBusy = true;
        ledgersError = null;
        try {
            await request("/api/ledgers/", {
                method: "POST",
                body: JSON.stringify({name, kind: newLedgerKind, company: companyId}),
            });
            newLedgerName = "";
            await loadLedgers();
        } catch (e) {
            ledgersError = e instanceof ApiError ? e.message : "Could not add ledger.";
        } finally {
            ledgersBusy = false;
        }
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
        } catch {
            seqs = [];
        }
    }

    async function saveTemplate(s: Seq, newTemplate: string) {
        seqsBusy = true;
        seqsError = null;
        try {
            await request(`/api/vouchers/number-seqs/${s.id}/`, {
                method: "PATCH", body: JSON.stringify({template: newTemplate}),
            });
            await loadSeqs();
        } catch (e) {
            seqsError = e instanceof ApiError ? e.message : "Could not save template.";
        } finally {
            seqsBusy = false;
        }
    }

    function handleTemplateChange(s: Seq, e: Event) {
        const input = e.currentTarget as HTMLInputElement;
        void saveTemplate(s, input.value);
    }

    function formatPreview(template: string, n: number): string {
        try {
            const match = template.match(/\{seq(?::(\d*)d)?\}/);
            if (!match) return "Invalid template";
            const pad = parseInt(match[1] || "0", 10);
            const numStr = String(n).padStart(pad, "0");
            return template.replace(/\{seq[^}]*\}/, numStr);
        } catch {
            return "Invalid template";
        }
    }

    const VOUCHER_LABELS: Record<string, string> = {
        SALE: "Sale", PURCHASE: "Purchase", RECEIVED: "Receipt", PAYMENT: "Payment",
    };

    const shell = registerScreen(() => ({
        title: "Settings",
        actions: [],
        shortcuts: [
            {
                id: "settings-search", keychord: "ctrl+f", label: "Search settings", run: () => {
                    searchInput?.focus();
                }
            },
        ],
        panel: [],
    }));
</script>

<div class="settings-layout">
    <!-- ── Left Sidebar ──────────────────────────────────────── -->
    <aside class="sidebar">
        <div class="search-box">
            <span class="search-icon">⌕</span>
            <input bind:this={searchInput} bind:value={searchQuery}
                   class="search-input" onkeydown={onSearchKeydown}
                   placeholder="Search settings…"
                   type="text"/>
            {#if searchQuery}
                <button class="search-clear" onclick={() => (searchQuery = "")}>✕</button>
            {/if}
        </div>

        <nav class="nav-list">
            {#each filteredSections as s (s.id)}
                <button class="nav-item" class:active={activeSection === s.id}
                        onclick={() => selectSection(s.id)}>
                    <span class="nav-icon">{s.icon}</span>
                    <div class="nav-text">
                        <span class="nav-label">{s.label}</span>
                        <span class="nav-desc">{s.description}</span>
                    </div>
                </button>
            {/each}
            {#if filteredSections.length === 0}
                <p class="nav-empty">No matching settings</p>
            {/if}
        </nav>

        <div class="sidebar-footer">
            <span class="sidebar-hint">↑↓ navigate · ⏎ select</span>
        </div>
    </aside>

    <!-- ── Right Content ─────────────────────────────────────── -->
    <main class="content">
        {#if activeSection === "company"}
            <div class="section-header">
                <h2>Company</h2>
                <p class="section-desc">Manage company mode, add companies, and configure segregation.</p>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3>License & Mode</h3>
                    <span class="license-badge">
                        {auth.license?.plan ?? "base"}
                        {#if allowsMulti}<span class="tag ok">multi unlocked</span>{:else}<span
                                class="tag">single only</span>{/if}
                    </span>
                </div>
                <p class="hint">Max {maxCompanies} {maxCompanies === 1 ? "company" : "companies"} on your current
                    plan.</p>

                {#if !allowsMulti}
                    <div class="upgrade-box">
                        <p class="hint">Multi-company mode is locked. Upgrade your license to unlock it.</p>
                        <button class="btn-primary" disabled={busy} onclick={upgradeLicense}>
                            {busy ? "Upgrading…" : "Unlock Multi-Company"}
                        </button>
                    </div>
                {:else}
                    <div class="mode-toggle">
                        <button class:active={companyMode === "single"} disabled={busy || companyMode === "single"}
                                onclick={switchToSingle}>
                            Single
                        </button>
                        <button class:active={companyMode === "multi"}
                                disabled={busy || companyMode === "multi"}
                                onclick={switchToMulti}>
                            Multi
                        </button>
                    </div>

                    {#if companyMode === "multi"}
                        <label class="check">
                            <input type="checkbox" checked={segregation} onchange={toggleSegregation} disabled={busy}/>
                            Enable segregation (split data across companies)
                        </label>
                    {/if}

                    <div class="downgrade-box">
                        <button class="btn-sm danger" disabled={busy || companyCount > 1} onclick={downgradeLicense}>
                            Downgrade to Single
                        </button>
                        {#if companyCount > 1}
                            <span class="hint">Delete extra companies before downgrading.</span>
                        {/if}
                    </div>
                {/if}

                {#if modeError}<p class="err">{modeError}</p>{/if}
            </div>

            <div class="card">
                <div class="card-header">
                    <h3>Companies</h3>
                    <span class="counter">{companyCount} / {maxCompanies}</span>
                </div>
                <ul class="item-list">
                    {#each auth.companies as c (c.id)}
                        <li class:active={c.id === auth.currentCompany?.id} class:dimmed={!c.is_active}>
                            <span class="item-name">{c.name}</span>
                            <span class="item-actions">
                                {#if c.is_default}<span class="tag">default</span>{/if}
                                {#if c.id === auth.currentCompany?.id}<span class="tag ok">current</span>{/if}
                                {#if !c.is_active}<span class="tag danger-tag">inactive</span>{/if}
                                {#if companyMode === "multi"}
                                    {#if !c.is_default}
                                        <button class="btn-sm" onclick={() => makeDefault(c)} disabled={companyBusy}>
                                            Set default
                                        </button>
                                    {/if}
                                    <button class="btn-sm" class:active={c.is_active}
                                            onclick={() => toggleCompanyActive(c)}
                                            disabled={companyBusy || c.is_default}>
                                        {c.is_active ? "Deactivate" : "Activate"}
                                    </button>
                                {/if}
                            </span>
                        </li>
                    {/each}
                </ul>
                {#if canAddCompany && (companyMode === "multi" || companyCount === 0)}
                    <div class="add-row">
                        <input bind:value={newCompanyName} placeholder="New company name…"
                               onkeydown={(e) => { if (e.key === "Enter") addCompany(); }}/>
                        <button class="btn-primary" disabled={companyBusy || !newCompanyName.trim()}
                                onclick={addCompany}>
                            {companyBusy ? "…" : "Add"}
                        </button>
                    </div>
                {:else if !canAddCompany}
                    <p class="hint">Company limit reached for your license.</p>
                {/if}
                {#if companyError}<p class="err">{companyError}</p>{/if}
            </div>

        {:else if activeSection === "settlement"}
            <div class="section-header">
                <h2>Settlement Modes</h2>
                <p class="section-desc">Configure payment and receipt methods used across Payment, Received, and Settle
                    screens.</p>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3>Active Modes</h3>
                    <span class="counter">{modes.filter(m => m.is_active).length} active</span>
                </div>
                <ul class="item-list">
                    {#each modes as m (m.id)}
                        <li class:dimmed={!m.is_active}>
                            <span class="item-name">
                                {m.name}
                                <span class="mode-tags">
                                    <span class="tag" class:bank={m.category === "BANK"}>{m.category}</span>
                                    {#if m.category === "BANK" && m.bank_type}
                                        <span class="tag bank-type">{m.bank_type}</span>
                                    {/if}
                                </span>
                            </span>
                            <span class="item-actions">
                                {#if m.is_system}<span class="tag">system</span>{/if}
                                <button class="btn-sm" class:active={m.is_active} onclick={() => toggleModeActive(m)}>
                                    {m.is_active ? "Active" : "Inactive"}
                                </button>
                                {#if !m.is_system}
                                    <button class="btn-sm danger" onclick={() => deleteMode(m)}>✕</button>
                                {/if}
                            </span>
                        </li>
                    {/each}
                </ul>
            </div>

            <div class="card">
                <h3>Add New Mode</h3>
                <div class="form-grid">
                    <div class="form-field">
                        <label>Name</label>
                        <input bind:value={newModeName} placeholder="e.g. PhonePe, HDFC Cheque…"
                               onkeydown={(e) => { if (e.key === "Enter") addMode(); }}/>
                    </div>
                    <div class="form-field">
                        <label>Category</label>
                        <select bind:value={newModeCategory}
                                onchange={() => { if (newModeCategory === "CASH") newModeBankType = ""; }}>
                            <option value="CASH">Cash</option>
                            <option value="BANK">Bank</option>
                        </select>
                    </div>
                    {#if newModeCategory === "BANK"}
                        <div class="form-field">
                            <label>Bank Type</label>
                            <select bind:value={newModeBankType}>
                                <option value="">Select type…</option>
                                <option value="UPI">UPI</option>
                                <option value="TRANSFER">Transfer</option>
                                <option value="CHEQUE">Cheque</option>
                                <option value="OTHER">Other</option>
                            </select>
                        </div>
                    {/if}
                </div>
                <div class="form-actions">
                    <button class="btn-primary"
                            disabled={modesBusy || !newModeName.trim() || (newModeCategory === "BANK" && !newModeBankType)}
                            onclick={addMode}>
                        {modesBusy ? "Adding…" : "Add mode"}
                    </button>
                </div>
                {#if modesError}<p class="err">{modesError}</p>{/if}
            </div>

        {:else if activeSection === "ledgers"}
            <div class="section-header">
                <h2>Charge Ledgers</h2>
                <p class="section-desc">Discount, round-off, and tax ledgers used in the charges section of Sale and
                    Purchase.</p>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3>Ledgers</h3>
                    <span class="counter">{ledgers.length} total</span>
                </div>
                <ul class="item-list">
                    {#each ledgers as l (l.id)}
                        <li>
                            <span class="item-name">{l.name}</span>
                            <span class="item-actions">
                                <span class="tag">{l.kind}</span>
                                {#if l.is_system}<span class="tag">system</span>{/if}
                                {#if !l.is_system}
                                    <button class="btn-sm danger" onclick={() => deleteLedger(l)}>✕</button>
                                {/if}
                            </span>
                        </li>
                    {/each}
                </ul>
            </div>

            <div class="card">
                <h3>Add New Ledger</h3>
                <div class="form-grid">
                    <div class="form-field">
                        <label>Kind</label>
                        <select bind:value={newLedgerKind}>
                            <option value="DISCOUNT">Discount</option>
                            <option value="ROUND_OFF">Round Off</option>
                            <option value="TAX">Tax</option>
                            <option value="OTHER">Other</option>
                        </select>
                    </div>
                    <div class="form-field wide">
                        <label>Name</label>
                        <input bind:value={newLedgerName} placeholder="New ledger name…"
                               onkeydown={(e) => { if (e.key === "Enter") addLedger(); }}/>
                    </div>
                </div>
                <div class="form-actions">
                    <button class="btn-primary" disabled={ledgersBusy || !newLedgerName.trim()} onclick={addLedger}>
                        {ledgersBusy ? "Adding…" : "Add ledger"}
                    </button>
                </div>
                {#if ledgersError}<p class="err">{ledgersError}</p>{/if}
            </div>

        {:else if activeSection === "numbering"}
            <div class="section-header">
                <h2>Voucher Numbering</h2>
                <p class="section-desc">Edit the template for each voucher type. Use <code>{"{seq:04d}"}</code> for
                    zero-padded numbers. Sequences are created automatically on first use.</p>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3>Sequences</h3>
                    <span class="counter">{seqs.length} configured</span>
                </div>
                {#if seqs.length === 0}
                    <p class="empty-state">No sequences yet. They appear after the first voucher of each type is
                        saved.</p>
                {:else}
                    <ul class="item-list seq-list">
                        {#each seqs as s (s.id)}
                            {@const label = VOUCHER_LABELS[s.voucher_type] ?? s.voucher_type}
                            <li class="seq-item">
                                <span class="seq-label">{label}</span>
                                <input class="seq-input" value={s.template}
                                       onchange={(e) => handleTemplateChange(s, e)}/>
                                <span class="seq-preview">Next: {formatPreview(s.template, s.high_water + 1)}</span>
                            </li>
                        {/each}
                    </ul>
                {/if}
                {#if seqsError}<p class="err">{seqsError}</p>{/if}
            </div>
        {/if}
    </main>
</div>

<style>
    /* ── Layout ── */
    .settings-layout {
        display: flex;
        height: 100%;
        overflow: hidden;
    }

    /* ── Sidebar ── */
    .sidebar {
        width: 260px;
        min-width: 260px;
        display: flex;
        flex-direction: column;
        border-right: 1px solid var(--border);
        background: var(--bg-panel);
    }

    .search-box {
        position: relative;
        padding: 14px 14px 10px;
    }

    .search-icon {
        position: absolute;
        left: 24px;
        top: 50%;
        transform: translateY(-50%);
        color: var(--text-muted);
        font-size: 14px;
        pointer-events: none;
    }

    .search-input {
        width: 100%;
        padding: 9px 32px 9px 32px;
        border-radius: var(--radius);
        border: 1px solid var(--border-hi);
        background: var(--bg-app);
        color: var(--text);
        font-size: 13px;
        box-sizing: border-box;
        outline: none;
    }

    .search-input::placeholder {
        color: var(--text-muted);
    }

    .search-input:focus {
        border-color: var(--accent);
    }

    .search-clear {
        position: absolute;
        right: 22px;
        top: 50%;
        transform: translateY(-50%);
        background: none;
        border: none;
        color: var(--text-muted);
        cursor: pointer;
        font-size: 12px;
        padding: 2px 4px;
    }

    .search-clear:hover {
        color: var(--text);
    }

    .nav-list {
        flex: 1;
        overflow-y: auto;
        padding: 4px 8px;
        display: flex;
        flex-direction: column;
        gap: 2px;
    }

    .nav-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 12px;
        border: none;
        border-radius: var(--radius);
        background: transparent;
        color: var(--text-muted);
        cursor: pointer;
        text-align: left;
        width: 100%;
        transition: background 0.1s;
    }

    .nav-item:hover {
        background: var(--bg-elevated);
        color: var(--text);
    }

    .nav-item.active {
        background: var(--accent-soft);
        color: var(--accent-text);
    }

    .nav-icon {
        width: 22px;
        text-align: center;
        font-size: 15px;
        flex-shrink: 0;
    }

    .nav-text {
        display: flex;
        flex-direction: column;
        gap: 1px;
        min-width: 0;
    }

    .nav-label {
        font-size: 13px;
        font-weight: 600;
        line-height: 1.3;
    }

    .nav-desc {
        font-size: 11px;
        opacity: 0.6;
        line-height: 1.3;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .nav-empty {
        padding: 20px 12px;
        color: var(--text-muted);
        font-size: 13px;
        text-align: center;
    }

    .sidebar-footer {
        padding: 10px 14px;
        border-top: 1px solid var(--border);
    }

    .sidebar-hint {
        font-size: 11px;
        color: var(--text-muted);
        opacity: 0.6;
    }

    /* ── Content ── */
    .content {
        flex: 1;
        overflow-y: auto;
        padding: 28px 36px 48px;
        min-width: 0;
    }

    .section-header {
        margin-bottom: 24px;
    }

    .section-header h2 {
        margin: 0 0 6px;
        font-size: 20px;
        font-weight: 700;
        color: var(--text);
    }

    .section-desc {
        margin: 0;
        font-size: 13px;
        color: var(--text-muted);
        line-height: 1.5;
    }

    /* ── Cards ── */
    .card {
        border: 1px solid var(--border);
        border-radius: 10px;
        background: var(--bg-elevated);
        padding: 20px 22px;
        margin-bottom: 18px;
        display: flex;
        flex-direction: column;
        gap: 12px;
    }

    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .card h3 {
        margin: 0;
        font-size: 14px;
        font-weight: 600;
        color: var(--text);
    }

    .counter {
        font-size: 12px;
        color: var(--text-muted);
        padding: 2px 10px;
        background: rgba(255, 255, 255, .04);
        border-radius: 999px;
    }

    .license-badge {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        font-weight: 600;
        color: var(--accent-text);
        text-transform: capitalize;
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

    .err {
        margin: 0;
        font-size: 12px;
        color: #ff9b9b;
    }

    .empty-state {
        color: var(--text-muted);
        font-size: 13px;
        padding: 16px 0;
        text-align: center;
    }

    /* ── Tags ── */
    .tag {
        font-size: 10px;
        text-transform: uppercase;
        padding: 2px 7px;
        border-radius: 4px;
        background: rgba(255, 255, 255, .06);
        color: var(--text-muted);
        font-weight: 500;
    }

    .tag.ok {
        background: rgba(52, 211, 153, .12);
        color: #34d399;
    }

    .tag.bank {
        background: rgba(47, 111, 235, .12);
        color: var(--accent-text);
    }

    .tag.bank-type {
        background: rgba(52, 211, 153, .1);
        color: #34d399;
    }

    /* ── Mode toggle ── */
    .mode-toggle {
        display: inline-flex;
        border: 1px solid var(--border-hi);
        border-radius: var(--radius);
        overflow: hidden;
    }

    .mode-toggle button {
        padding: 8px 22px;
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

    /* ── Item list ── */
    .item-list {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 2px;
    }

    .item-list li {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 13px;
        color: var(--text);
        transition: background 0.1s;
    }

    .item-list li:hover {
        background: rgba(255, 255, 255, .03);
    }

    .item-list li.active {
        background: rgba(47, 111, 235, .08);
    }

    .item-list li.dimmed {
        opacity: 0.5;
    }

    .item-name {
        display: flex;
        align-items: center;
        gap: 8px;
        min-width: 0;
    }

    .mode-tags {
        display: inline-flex;
        gap: 4px;
    }

    .item-actions {
        display: flex;
        align-items: center;
        gap: 6px;
        flex-shrink: 0;
    }

    /* ── Buttons ── */
    .btn-sm {
        padding: 3px 9px;
        font-size: 11px;
        border-radius: 4px;
        border: 1px solid var(--border-hi);
        background: transparent;
        color: var(--text-muted);
        cursor: pointer;
    }

    .btn-sm.active {
        border-color: rgba(52, 211, 153, .3);
        color: #34d399;
    }

    .btn-sm.danger {
        border-color: rgba(255, 155, 155, .2);
        color: #ff9b9b;
    }

    .btn-sm.danger:hover {
        background: rgba(255, 155, 155, .1);
    }

    .btn-primary {
        padding: 8px 18px;
        border-radius: var(--radius);
        border: 1px solid var(--accent);
        background: var(--accent);
        color: #fff;
        cursor: pointer;
        font-size: 13px;
        font-weight: 500;
        white-space: nowrap;
    }

    .btn-primary:disabled {
        opacity: .5;
        cursor: default;
    }

    .btn-primary:not(:disabled):hover {
        filter: brightness(1.1);
    }

    /* ── Forms ── */
    .form-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 14px;
    }

    .form-field {
        display: flex;
        flex-direction: column;
        gap: 5px;
    }

    .form-field.wide {
        grid-column: span 2;
    }

    .form-field label {
        font-size: 12px;
        color: var(--text-muted);
        font-weight: 500;
    }

    .form-field input,
    .form-field select {
        padding: 8px 11px;
        border-radius: var(--radius);
        border: 1px solid var(--border-hi);
        background: var(--bg-app);
        color: var(--text);
        font-size: 13px;
        box-sizing: border-box;
    }

    .form-field input:focus,
    .form-field select:focus {
        border-color: var(--accent);
        outline: none;
    }

    .form-actions {
        display: flex;
        justify-content: flex-end;
        padding-top: 4px;
    }

    .add-row {
        display: flex;
        gap: 8px;
        align-items: center;
    }

    .add-row input {
        flex: 1;
        padding: 8px 11px;
        border-radius: var(--radius);
        border: 1px solid var(--border-hi);
        background: var(--bg-app);
        color: var(--text);
        font-size: 13px;
        box-sizing: border-box;
    }

    .add-row input:focus {
        border-color: var(--accent);
        outline: none;
    }

    /* ── Sequences ── */
    .seq-list li {
        display: grid;
        grid-template-columns: 100px 1fr auto;
        gap: 12px;
        align-items: center;
    }

    .seq-label {
        font-size: 12px;
        color: var(--text-muted);
        font-weight: 600;
    }

    .seq-input {
        padding: 7px 9px;
        border-radius: var(--radius);
        border: 1px solid var(--border-hi);
        background: var(--bg-app);
        color: var(--text);
        font-size: 13px;
        font-family: monospace;
        box-sizing: border-box;
        width: 100%;
    }

    .seq-input:focus {
        border-color: var(--accent);
        outline: none;
    }

    .seq-preview {
        font-size: 11px;
        color: var(--text-muted);
        white-space: nowrap;
    }

    .upgrade-box {
        display: flex;
        flex-direction: column;
        gap: 10px;
        padding: 14px 16px;
        border: 1px dashed var(--border-hi);
        border-radius: var(--radius);
        background: rgba(47, 111, 235, .04);
    }

    .downgrade-box {
        display: flex;
        align-items: center;
        gap: 10px;
        padding-top: 4px;
    }

    .tag.danger-tag {
        background: rgba(255, 155, 155, .12);
        color: #ff9b9b;
    }

</style>
