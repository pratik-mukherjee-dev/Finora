<script lang="ts">
  import { suggest, recordUsage, type Suggestion } from "$lib/api";

  type Props = {
    type: "ITEM" | "PARTY";
    placeholder?: string;
    value?: Suggestion | null;
    onselect: (s: Suggestion) => void;
    oncreate: (typed: string) => void;
  };
  let { type, placeholder = "", value = $bindable(null), onselect, oncreate }: Props = $props();

  let q = $state(value?.name ?? "");
  let open = $state(false);
  let results = $state<Suggestion[]>([]);
  let active = $state(0);
  let loading = $state(false);

  let timer: ReturnType<typeof setTimeout> | null = null;
  let controller: AbortController | null = null;

  function schedule() {
    if (timer) clearTimeout(timer);
    timer = setTimeout(run, 150);
  }

  async function run() {
    const term = q.trim();
    if (!term) { results = []; open = false; return; }
    controller?.abort();
    controller = new AbortController();
    loading = true;
    try {
      results = await suggest(type, term, 10, controller.signal);
      active = 0;
      open = true;
    } catch (e) {
      if ((e as Error)?.name !== "AbortError") { results = []; }
    } finally {
      loading = false;
    }
  }

  function pick(s: Suggestion) {
    value = s;
    q = s.name;
    open = false;
    onselect(s);
    recordUsage(type, s.id);
  }

  function onInput(e: Event) {
    q = (e.target as HTMLInputElement).value;
    value = null;
    schedule();
  }

  const noMatch = $derived(
    open && !loading && q.trim().length > 0 &&
    !results.some((r) => r.name.toLowerCase() === q.trim().toLowerCase())
  );

  function onKey(e: KeyboardEvent) {
    if (!open) return;
    if (e.key === "ArrowDown") { active = Math.min(active + 1, results.length - 1); e.preventDefault(); }
    else if (e.key === "ArrowUp") { active = Math.max(active - 1, 0); e.preventDefault(); }
    else if (e.key === "Enter") {
      e.preventDefault();
      if (results[active]) pick(results[active]);
      else if (q.trim()) oncreate(q.trim());
    } else if (e.key === "Escape") { open = false; }
  }
</script>

<div class="lookup">
  <input
    {placeholder}
    value={q}
    oninput={onInput}
    onkeydown={onKey}
    onfocus={() => { if (results.length) open = true; }}
    onblur={() => setTimeout(() => (open = false), 120)}
    autocomplete="off"
  />
  {#if open}
    <ul class="menu">
      {#each results as r, i (r.id)}
        <li class:active={i === active} onmousedown={() => pick(r)}>{r.name}</li>
      {/each}
      {#if noMatch}
        <li class="create" onmousedown={() => oncreate(q.trim())}>+ Create “{q.trim()}”</li>
      {/if}
      {#if !results.length && !noMatch}
        <li class="empty">{loading ? "Searching…" : "No results"}</li>
      {/if}
    </ul>
  {/if}
</div>

<style>
  .lookup { position: relative; }
  input { width: 100%; padding: 8px 10px; border-radius: 8px; border: 1px solid #2a2f3a;
          background: #0f1115; color: #e6e8ec; font-size: 14px; box-sizing: border-box; }
  .menu { position: absolute; z-index: 20; left: 0; right: 0; margin: 4px 0 0; padding: 4px;
          list-style: none; background: #171a21; border: 1px solid #2a2f3a; border-radius: 8px;
          max-height: 240px; overflow-y: auto; }
  .menu li { padding: 8px 10px; border-radius: 6px; cursor: pointer; font-size: 14px; }
  .menu li.active, .menu li:hover { background: #1f2530; }
  .menu li.create { color: #4c8bf5; }
  .menu li.empty { color: #9aa0aa; cursor: default; }
</style>
