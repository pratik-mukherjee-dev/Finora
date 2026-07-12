import {
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  setTokens,
  clearTokens,
  request,
} from "$lib/api";
import { load } from "@tauri-apps/plugin-store";

type User = { user_id: number; username: string };
type Mode = "single" | "multi";
type Setting = {
  active_mode: Mode;
  default_company: number | null;
  segregation_enabled: boolean;
  is_mode_locked: boolean;
};
type Company = { id: number; name: string; is_default: boolean; created_at: string };

const STORE = "session.json";
const REFRESH_KEY = "refresh";

let user = $state<User | null>(null);
let setting = $state<Setting | null>(null);
let companies = $state<Company[]>([]);
let ready = $state(false);

async function persistRefresh(token: string | null) {
  const s = await load(STORE, { autoSave: true, defaults: {} });
  if (token) await s.set(REFRESH_KEY, token);
  else await s.delete(REFRESH_KEY);
}

async function loadContext() {
  setting = await request<Setting>("/api/accounts/settings/");
  companies = await request<Company[]>("/api/accounts/companies/");
}

export const auth = {
  get user() { return user; },
  get setting() { return setting; },
  get companies() { return companies; },
  get mode(): Mode | null { return setting?.active_mode ?? null; },
  get ready() { return ready; },
  get isAuthed() { return user !== null; },
  get needsSetup() { return companies.length === 0; },

  async restore() {
    const s = await load(STORE, { autoSave: true, defaults: {} });
    const refresh = await s.get<string>(REFRESH_KEY);
    if (refresh) {
      setTokens({ access: "", refresh });
      try {
        user = await request<User>("/api/accounts/auth/me/");
        await loadContext();
      } catch {
        clearTokens();
        await persistRefresh(null);
        user = null;
      }
    }
    ready = true;
  },

  async register(username: string, password: string) {
    const r = await apiRegister(username, password);
    await persistRefresh(r.refresh);
    user = await request<User>("/api/accounts/auth/me/");
    await loadContext();
  },

  async login(username: string, password: string) {
    const r = await apiLogin(username, password);
    await persistRefresh(r.refresh);
    user = await request<User>("/api/accounts/auth/me/");
    await loadContext();
  },

  async logout() {
    await apiLogout();
    await persistRefresh(null);
    user = null;
    setting = null;
    companies = [];
  },

  async enableMulti(segregation: boolean) {
    setting = await request<Setting>("/api/accounts/settings/switch_multi/", {
      method: "POST",
      body: JSON.stringify({ segregation_enabled: segregation }),
    });
  },

  async createCompany(name: string, isDefault: boolean) {
    await request("/api/accounts/companies/", {
      method: "POST",
      body: JSON.stringify({ name, is_default: isDefault }),
    });
    companies = await request<Company[]>("/api/accounts/companies/");
  },
};
