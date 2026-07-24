/**
 * desktop/src/lib/stores/auth.svelte.ts
 */
import {
    clearTokens,
    getRefresh,
    login as apiLogin,
    logout as apiLogout,
    register as apiRegister,
    request,
    setTokens,
} from "$lib/api";
import {load} from "@tauri-apps/plugin-store";

type User = { user_id: number; username: string };
type Mode = "single" | "multi";
type Setting = {
    active_mode: Mode;
    default_company: number | null;
    segregation_enabled: boolean;
    is_mode_locked: boolean;
};
type Company = {
    id: number;
    name: string;
    is_default: boolean;
    is_active: boolean;
    created_at: string
};
type License = {
    plan: string;
    mode: Mode;
    is_active: boolean;
    valid_till: string | null;
    allows_multi: boolean;
    max_companies: number;
};
type FinancialYear = {
    id: number;
    start_date: string;
    end_date: string;
    is_active: boolean;
    is_closed: boolean;
    is_writable: boolean;
};

const STORE = "session.json";
const REFRESH_KEY = "refresh";
const COMPANY_KEY = "current_company";

let user = $state<User | null>(null);
let setting = $state<Setting | null>(null);
let license = $state<License | null>(null);
let companies = $state<Company[]>([]);
let fy = $state<FinancialYear | null>(null);
let currentCompanyId = $state<number | null>(null);
let ready = $state(false);

async function persist(key: string, value: string | number | null) {
    const s = await load(STORE, {autoSave: true, defaults: {}});
    if (value === null) await s.delete(key);
    else await s.set(key, value);
}

/**
 * Resolve which company is "current": the persisted choice if it still exists,
 * otherwise the default company, otherwise the first one. Persists the result.
 */
async function resolveCurrentCompany() {
    if (companies.length === 0) {
        currentCompanyId = null;
        await persist(COMPANY_KEY, null);
        return;
    }
    const s = await load(STORE, {autoSave: true, defaults: {}});
    const saved = await s.get<number>(COMPANY_KEY);
    const exists = saved != null && companies.some((c) => c.id === saved);
    const fallback = companies.find((c) => c.is_default)?.id ?? companies[0].id;
    currentCompanyId = exists ? (saved as number) : fallback;
    await persist(COMPANY_KEY, currentCompanyId);
}

async function loadContext() {
    const raw = await request<Setting & { license?: License }>("/api/accounts/settings/");
    license = raw.license ?? null;
    setting = raw;
    companies = await request<Company[]>("/api/accounts/companies/");
    const years = await request<FinancialYear[]>("/api/fy/");
    // Tolerate a paginated {results:[]} shape if DRF pagination is ever enabled.
    const list = Array.isArray(years)
        ? years
        : ((years as { results?: FinancialYear[] })?.results ?? []);
    fy = list.find((y) => y.is_active && !y.is_closed) ?? null;
    await resolveCurrentCompany();
}

export const auth = {
    get user() {
        return user;
    },
    get setting() {
        return setting;
    },
    get license() {
        return license;
    },
    get allowsMulti() {
        return license?.allows_multi ?? false;
    },
    get maxCompanies() {
        return license?.max_companies ?? 1;
    },
    get companies() {
        return companies;
    },
    get fy() {
        return fy;
    },
    get mode(): Mode | null {
        return setting?.active_mode ?? null;
    },
    get ready() {
        return ready;
    },
    get isAuthed() {
        return user !== null;
    },
    get needsSetup() {
        return companies.length === 0;
    },
    get needsFy() {
        return user !== null && companies.length > 0 && fy === null;
    },
    get currentCompany(): Company | null {
        return companies.find((c) => c.id === currentCompanyId) ?? null;
    },

    async restore() {
        const s = await load(STORE, {autoSave: true, defaults: {}});
        const refresh = await s.get<string>(REFRESH_KEY);
        if (!refresh) {
            ready = true;
            return;
        }

        setTokens({access: "", refresh});
        try {
            user = await request<User>("/api/accounts/auth/me/");
        } catch (e) {
            // Only a genuine auth failure invalidates the session.
            console.error("[restore] /me/ failed, clearing session:", e);
            clearTokens();
            await persist(REFRESH_KEY, null);
            user = null;
            ready = true;
            return;
        }
        // Persist any refreshed token so the next launch starts from a valid one.
        await persist(REFRESH_KEY, getRefresh());
        try {
            await loadContext();
        } catch (e) {
            // Auth is valid but context failed transiently: keep the user signed in
            // rather than bouncing them to /login or misrouting the gate.
            console.error("[restore] loadContext failed (auth still valid):", e);
        }
        ready = true;
    },

    async register(username: string, password: string) {
        const r = await apiRegister(username, password);
        await persist(REFRESH_KEY, r.refresh);
        user = await request<User>("/api/accounts/auth/me/");
        await loadContext();
    },

    async login(username: string, password: string) {
        const r = await apiLogin(username, password);
        await persist(REFRESH_KEY, r.refresh);
        user = await request<User>("/api/accounts/auth/me/");
        await loadContext();
    },

    async logout() {
        await apiLogout();
        await persist(REFRESH_KEY, null);
        await persist(COMPANY_KEY, null);
        user = null;
        setting = null;
        license = null;
        companies = [];
        fy = null;
        currentCompanyId = null;
    },

    async enableMulti(segregation: boolean) {
        setting = await request<Setting>("/api/accounts/settings/switch_multi/", {
            method: "POST",
            body: JSON.stringify({segregation_enabled: segregation}),
        });
        await loadContext();
    },

    async switchToSingle() {
        setting = await request<Setting>("/api/accounts/settings/switch_single/", {
            method: "POST",
        });
        await loadContext();
    },

    async setSegregation(enabled: boolean) {
        setting = await request<Setting>("/api/accounts/settings/segregation/", {
            method: "POST",
            body: JSON.stringify({enabled}),
        });
    },

    async reloadContext() {
        await loadContext();
    },

    async createCompany(name: string, isDefault: boolean) {
        await request("/api/accounts/companies/", {
            method: "POST",
            body: JSON.stringify({name, is_default: isDefault}),
        });
        companies = await request<Company[]>("/api/accounts/companies/");
        await resolveCurrentCompany();
    },

    async upgradeLicense(maxCompanies: number = 5) {
        license = await request<License>("/api/accounts/settings/upgrade_multi/", {
            method: "POST",
            body: JSON.stringify({ max_companies: maxCompanies }),
        });
        await loadContext();
    },

    async downgradeLicense() {
        license = await request<License>("/api/accounts/settings/downgrade_single/", {
            method: "POST",
        });
        await loadContext();
    },

    async toggleCompanyActive(companyId: number, isActive: boolean) {
        await request<Company>(`/api/accounts/companies/${companyId}/toggle_active/`, {
            method: "POST",
            body: JSON.stringify({ is_active: isActive }),
        });
        await loadContext();
    },

    async makeDefaultCompany(companyId: number) {
        await request<Company>(`/api/accounts/companies/${companyId}/make_default/`, {
            method: "POST",
        });
        await loadContext();
    },

    async ensureFy(startDate: string, endDate: string) {
        const payload = {start_date: startDate, end_date: endDate};
        console.log("[ensureFy] POST /api/fy/ payload:", JSON.stringify(payload));
        try {
            fy = await request<FinancialYear>("/api/fy/", {
                method: "POST",
                body: JSON.stringify(payload),
            });
            console.log("[ensureFy] created:", fy);
        } catch (e) {
            // Surface the exact server validation body.
            const anyErr = e as { status?: number; message?: string; body?: unknown };
            console.error(
                "[ensureFy] POST failed:",
                "status=", anyErr.status,
                "message=", anyErr.message,
                "body=", JSON.stringify(anyErr.body)
            );
            const years = await request<FinancialYear[]>("/api/fy/");
            console.log("[ensureFy] refetched years:", JSON.stringify(years));
            const list = Array.isArray(years)
                ? years
                : ((years as { results?: FinancialYear[] })?.results ?? []);
            fy = list.find((y) => y.is_active && !y.is_closed) ?? null;
            if (!fy) throw e;
        }
        return fy;
    },


    /** Backward-compatible alias used by routes/fy/+page.svelte. */
    async createFy(startDate: string, endDate: string) {
        return this.ensureFy(startDate, endDate);
    },

    async setCurrentCompany(id: number) {
        if (!companies.some((c) => c.id === id)) return;
        currentCompanyId = id;
        await persist(COMPANY_KEY, id);
    },
};