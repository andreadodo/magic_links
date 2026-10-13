const LOGO = `<svg viewBox="0 0 64 64" width="40" height="40" aria-hidden="true"><defs><linearGradient id="mlg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#38bdf8"/><stop offset="1" stop-color="#1d4ed8"/></linearGradient></defs><rect width="64" height="64" rx="15" fill="url(#mlg)"/><g fill="none" stroke="#fff" stroke-width="5.5" stroke-linecap="round" transform="rotate(-45 32 32)"><rect x="9" y="23" width="26" height="18" rx="9"/><rect x="29" y="23" width="26" height="18" rx="9"/></g><path d="M38 8 25 30h8l-4 14 14-22h-9z" fill="#fde047" stroke="#1d4ed8" stroke-width="2" stroke-linejoin="round" transform="translate(8.5 13.8) scale(.7)"/></svg>`;

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (iso) => (iso ? new Date(iso).toLocaleString("it-IT", { dateStyle: "short", timeStyle: "short" }) : "");
const rel = (iso) => {
  const d = new Date(iso) - Date.now();
  const m = Math.max(1, Math.round(Math.abs(d) / 60000));
  const t = m < 60 ? `${m} min` : m < 1440 ? `${Math.round(m / 60)} h` : `${Math.round(m / 1440)} g`;
  return d > 0 ? `tra ${t}` : `${t} fa`;
};
const pad = (n) => String(n).padStart(2, "0");
const toDateInput = (iso) => {
  const d = new Date(iso);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

const DOMAINS = {
  automation: ["Automazioni", "mdi:robot"],
  script: ["Script", "mdi:script-text"],
  scene: ["Scene", "mdi:palette"],
};
const STATUS = {
  ok: ["Attivo", "ok"],
  expired: ["Scaduto", "off"],
  exhausted: ["Usi esauriti", "warn"],
};

const STYLE = `
:host{display:block;min-height:100%;background:var(--primary-background-color);color:var(--primary-text-color);
  --ml-accent:var(--primary-color,#03a9f4);--ml-ok:var(--success-color,#2e9d57);--ml-warn:var(--warning-color,#f59e0b);--ml-off:var(--error-color,#dc2626);
  --ml-card:var(--card-background-color,#fff);--ml-line:var(--divider-color,#e2e8f0);--ml-mut:var(--secondary-text-color,#64748b)}
*{box-sizing:border-box}
header{display:flex;align-items:center;gap:12px;padding:14px 20px;background:var(--app-header-background-color,var(--ml-card));
  border-bottom:1px solid var(--ml-line);position:sticky;top:0;z-index:5}
header .t{flex:1;display:flex;align-items:center;gap:12px;min-width:0}
header h1{font-size:20px;font-weight:600;margin:0;line-height:1.1}
header small{display:block;color:var(--ml-mut);font-weight:400;font-size:12px;margin-top:2px}
.wrap{max-width:980px;margin:0 auto;padding:20px 16px 80px}
button{font:inherit;cursor:pointer;color:inherit;border:1px solid var(--ml-line);background:transparent;border-radius:12px;padding:9px 14px;
  display:inline-flex;align-items:center;gap:6px;transition:.15s}
button:hover{background:color-mix(in srgb,var(--ml-accent) 10%,transparent)}
button.primary{background:linear-gradient(135deg,#38bdf8,#1d4ed8);border:0;color:#fff;font-weight:600;box-shadow:0 4px 14px rgba(29,78,216,.35)}
button.primary:hover{filter:brightness(1.08)}
button.icon{padding:8px;border-radius:10px;border-color:transparent;color:var(--ml-mut)}
button.icon:hover{color:var(--ml-accent)}button.icon.del:hover{color:var(--ml-off);background:color-mix(in srgb,var(--ml-off) 12%,transparent)}
ha-icon{--mdc-icon-size:20px;display:inline-flex}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px}
.stat{background:var(--ml-card);border:1px solid var(--ml-line);border-radius:16px;padding:14px 16px}
.stat b{display:block;font-size:26px;line-height:1.1}.stat span{color:var(--ml-mut);font-size:13px}
.favs{margin-bottom:20px}
.favs h3,.sect{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--ml-mut);margin:0 0 8px}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.fav{border-radius:999px;padding:7px 14px 7px 10px;background:var(--ml-card);border-color:var(--ml-line)}
.fav ha-icon{color:#f59e0b}
.toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:14px}
.toolbar input{flex:1;min-width:180px}
input,select{font:inherit;color:var(--primary-text-color);background:var(--ml-card);border:1px solid var(--ml-line);border-radius:12px;padding:10px 12px;width:100%}
input:focus,select:focus{outline:2px solid var(--ml-accent);outline-offset:-1px}
.seg{display:flex;border:1px solid var(--ml-line);border-radius:12px;overflow:hidden}
.seg button{border:0;border-radius:0;padding:9px 14px;color:var(--ml-mut)}
.seg button.on{background:color-mix(in srgb,var(--ml-accent) 16%,transparent);color:var(--ml-accent);font-weight:600}
.list{display:grid;gap:12px}
.card{display:flex;gap:14px;align-items:center;background:var(--ml-card);border:1px solid var(--ml-line);border-left:4px solid var(--ml-ok);
  border-radius:16px;padding:14px 16px;transition:.15s}
.card:hover{box-shadow:0 6px 20px rgba(0,0,0,.08)}
.card.off{border-left-color:var(--ml-off);opacity:.78}.card.warn{border-left-color:var(--ml-warn);opacity:.85}
.ico{flex:none;width:44px;height:44px;border-radius:12px;display:grid;place-items:center;background:color-mix(in srgb,var(--ml-accent) 14%,transparent);color:var(--ml-accent)}
.body{flex:1;min-width:0}
.top{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.title{font-weight:600;font-size:16px}
.chip{font-size:11px;font-weight:600;padding:2px 9px;border-radius:999px;color:#fff;background:var(--ml-ok)}
.chip.off{background:var(--ml-off)}.chip.warn{background:var(--ml-warn)}
.sub{color:var(--primary-text-color);font-size:14px;margin-top:3px;display:flex;gap:14px;flex-wrap:wrap}
.sub span{display:inline-flex;align-items:center;gap:4px}.sub ha-icon{--mdc-icon-size:16px;color:var(--ml-mut)}
.meta{color:var(--ml-mut);font-size:12.5px;margin-top:4px}
.actions{display:flex;gap:2px;flex:none}
.empty{text-align:center;color:var(--ml-mut);padding:48px 16px;border:2px dashed var(--ml-line);border-radius:16px}
.empty ha-icon{--mdc-icon-size:44px;opacity:.5}
dialog{border:0;border-radius:20px;padding:0;width:min(520px,calc(100vw - 24px));background:var(--ml-card);color:var(--primary-text-color);box-shadow:0 20px 60px rgba(0,0,0,.35)}
dialog::backdrop{background:rgba(15,23,42,.55);backdrop-filter:blur(3px)}
dialog form{padding:22px;display:grid;gap:14px}
dialog h2{margin:0;font-size:19px}
label{display:grid;gap:5px;font-size:13px;color:var(--ml-mut)}
.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.pick{display:flex;gap:8px}.pick select{flex:1}
.star.on ha-icon{color:#f59e0b}
.check{display:flex;align-items:center;gap:8px;font-size:14px;color:var(--primary-text-color)}
.check input{width:auto}
.foot{display:flex;justify-content:flex-end;gap:10px;margin-top:4px}
.hidden{display:none!important}
#toast{position:fixed;left:50%;bottom:24px;transform:translate(-50%,20px);background:#0f172a;color:#fff;padding:11px 18px;border-radius:12px;
  opacity:0;pointer-events:none;transition:.25s;z-index:20;font-size:14px;box-shadow:0 8px 24px rgba(0,0,0,.3)}
#toast.show{opacity:1;transform:translate(-50%,0)}#toast.err{background:#b91c1c}
@media(max-width:600px){.card{flex-wrap:wrap}.actions{width:100%;justify-content:flex-end}.row{grid-template-columns:1fr}.stats{gap:8px}.stat{padding:10px 12px}}
`;

class MagicLinksPanel extends HTMLElement {
  constructor() {
    super();
    this._data = { links: [], targets: [], favorites: [], base_url: "", default_expiry: "24h", sidebar_title: "Link rapidi" };
    this._filter = "all";
    this._q = "";
    this._edit = null;
    this.attachShadow({ mode: "open" });
  }

  set hass(h) {
    const first = !this._hass;
    this._hass = h;
    if (first) {
      this._build();
      this._load();
    }
    if (this._menu) this._menu.hass = h;
  }
  set narrow(n) {
    this._narrow = n;
    if (this._menu) this._menu.narrow = n;
  }
  set panel(_) {}
  set route(_) {}

  $(id) {
    return this.shadowRoot.getElementById(id);
  }

  _build() {
    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <header>
        <span id="menu"></span>
        <div class="t">${LOGO}<h1>Magic Links<small>Link rapidi senza accesso per le tue automazioni</small></h1></div>
        <button class="primary" id="new"><ha-icon icon="mdi:plus"></ha-icon><span>Nuovo link</span></button>
      </header>
      <div class="wrap">
        <div class="stats" id="stats"></div>
        <div class="favs hidden" id="favs"><h3>Azioni preferite</h3><div class="chips" id="favchips"></div></div>
        <div class="toolbar">
          <input id="q" type="search" placeholder="Cerca per nome, persona o azione…">
          <div class="seg" id="seg">
            <button data-f="all" class="on">Tutti</button><button data-f="ok">Attivi</button><button data-f="off">Non attivi</button>
          </div>
        </div>
        <div class="list" id="list"></div>
      </div>
      <dialog id="dlg">
        <form id="form" method="dialog">
          <h2 id="dtitle">Nuovo link</h2>
          <label>Nome del link<input id="label" required maxlength="80" placeholder="Es. Cancello ospiti"></label>
          <label>Assegnato a<input id="assigned" maxlength="80" placeholder="Es. Marco (idraulico)"></label>
          <label>Azione da eseguire
            <div class="pick"><select id="target" required></select>
              <button type="button" class="icon star" id="star" title="Aggiungi/rimuovi dai preferiti"><ha-icon icon="mdi:star-outline"></ha-icon></button></div>
          </label>
          <div class="row">
            <label>Scadenza<select id="exp"></select></label>
            <label id="dateWrap" class="hidden">Data di scadenza<input id="date" type="date"></label>
          </div>
          <label>Usi massimi (facoltativo)<input id="max" type="number" min="1" placeholder="Illimitati"></label>
          <div id="editOpts" class="hidden">
            <label class="check"><input type="checkbox" id="reset"> Azzera il contatore degli usi</label>
            <label class="check"><input type="checkbox" id="regen"> Genera un nuovo link (quello attuale smette di funzionare)</label>
          </div>
          <div class="foot"><button type="button" id="cancel">Annulla</button><button class="primary" type="submit" id="save">Crea link</button></div>
        </form>
      </dialog>
      <div id="toast"></div>`;

    this._menu = document.createElement("ha-menu-button");
    this._menu.hass = this._hass;
    this._menu.narrow = this._narrow;
    this.$("menu").appendChild(this._menu);

    this.$("new").onclick = () => this._open(null);
    this.$("cancel").onclick = () => this.$("dlg").close();
    this.$("form").onsubmit = (e) => {
      e.preventDefault();
      this._save();
    };
    this.$("exp").onchange = () => this.$("dateWrap").classList.toggle("hidden", this.$("exp").value !== "date");
    this.$("star").onclick = () => this._toggleFav(this.$("target").value);
    this.$("target").onchange = () => this._syncStar();
    this.$("q").oninput = (e) => {
      this._q = e.target.value.toLowerCase();
      this._renderList();
    };
    this.$("seg").onclick = (e) => {
      const b = e.target.closest("button[data-f]");
      if (!b) return;
      this._filter = b.dataset.f;
      this.$("seg").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
      this._renderList();
    };
    this.$("list").onclick = (e) => {
      const b = e.target.closest("button[data-act]");
      if (b) this._act(b.dataset.act, b.dataset.id);
    };
    this.$("favchips").onclick = (e) => {
      const b = e.target.closest("button[data-t]");
      if (b) this._open(null, b.dataset.t);
    };
  }

  _toast(text, error = false) {
    const t = this.$("toast");
    t.textContent = text;
    t.className = `show${error ? " err" : ""}`;
    clearTimeout(this._tt);
    this._tt = setTimeout(() => (t.className = ""), 3200);
  }

  async _load() {
    try {
      this._data = await this._hass.callWS({ type: "magic_links/list" });
    } catch (e) {
      return this._toast(e.message || "Errore nel caricamento", true);
    }
    this._render();
  }

  _name(eid) {
    return this._data.targets.find((t) => t.entity_id === eid)?.name || eid;
  }
  _icon(eid) {
    return (DOMAINS[eid.split(".")[0]] || ["", "mdi:link-variant"])[1];
  }
  _url(l) {
    return `${this._data.base_url || location.origin}/api/magic_link/${l.token}`;
  }

  _render() {
    this._renderStats();
    this._renderFavs();
    this._renderList();
  }

  _renderStats() {
    const L = this._data.links;
    const active = L.filter((l) => l.status === "ok").length;
    const uses = L.reduce((a, l) => a + (l.uses || 0), 0);
    this.$("stats").innerHTML = `
      <div class="stat"><b>${active}</b><span>Link attivi</span></div>
      <div class="stat"><b>${L.length - active}</b><span>Scaduti / esauriti</span></div>
      <div class="stat"><b>${uses}</b><span>Usi totali</span></div>`;
  }

  _renderFavs() {
    const favs = this._data.favorites.filter((f) => this._data.targets.some((t) => t.entity_id === f));
    this.$("favs").classList.toggle("hidden", !favs.length);
    this.$("favchips").innerHTML = favs
      .map((f) => `<button class="fav" data-t="${esc(f)}" title="Crea un link per questa azione"><ha-icon icon="mdi:star"></ha-icon>${esc(this._name(f))}</button>`)
      .join("");
  }

  _renderList() {
    const favs = new Set(this._data.favorites);
    let items = this._data.links.filter((l) => {
      if (this._filter === "ok" && l.status !== "ok") return false;
      if (this._filter === "off" && l.status === "ok") return false;
      const hay = `${l.label} ${l.assigned_to} ${this._name(l.target)}`.toLowerCase();
      return !this._q || hay.includes(this._q);
    });
    // i link con azione preferita salgono in cima, poi i più recenti
    items = items.sort((a, b) => favs.has(b.target) - favs.has(a.target));
    if (!items.length) {
      this.$("list").innerHTML = `<div class="empty"><ha-icon icon="mdi:link-variant-off"></ha-icon><p>${
        this._data.links.length ? "Nessun link corrisponde alla ricerca." : "Nessun link creato. Premi «Nuovo link» per iniziare."
      }</p></div>`;
      return;
    }
    this.$("list").innerHTML = items
      .map((l) => {
        const [txt, cls] = STATUS[l.status] || STATUS.ok;
        const uses = l.max_uses ? `${l.uses}/${l.max_uses} usi` : `${l.uses} usi`;
        const exp = l.expires_at ? `${l.status === "expired" ? "scaduto" : "scade"} ${rel(l.expires_at)} (${fmt(l.expires_at)})` : "sempre valido";
        return `<div class="card ${cls === "ok" ? "" : cls}">
          <div class="ico"><ha-icon icon="${this._icon(l.target)}"></ha-icon></div>
          <div class="body">
            <div class="top"><span class="title">${esc(l.label)}</span><span class="chip ${cls}">${txt}</span>${favs.has(l.target) ? '<ha-icon icon="mdi:star" style="--mdc-icon-size:16px;color:#f59e0b"></ha-icon>' : ""}</div>
            <div class="sub">
              ${l.assigned_to ? `<span><ha-icon icon="mdi:account"></ha-icon>${esc(l.assigned_to)}</span>` : ""}
              <span><ha-icon icon="mdi:play-circle-outline"></ha-icon>${esc(this._name(l.target))}</span>
            </div>
            <div class="meta">${exp} · ${uses}${l.last_used ? ` · ultimo uso ${fmt(l.last_used)}` : ""}</div>
          </div>
          <div class="actions">
            <button class="icon" data-act="copy" data-id="${l.id}" title="Copia link"><ha-icon icon="mdi:content-copy"></ha-icon></button>
            <button class="icon" data-act="share" data-id="${l.id}" title="Condividi"><ha-icon icon="mdi:share-variant"></ha-icon></button>
            <button class="icon" data-act="edit" data-id="${l.id}" title="Modifica"><ha-icon icon="mdi:pencil"></ha-icon></button>
            <button class="icon del" data-act="delete" data-id="${l.id}" title="Elimina"><ha-icon icon="mdi:trash-can-outline"></ha-icon></button>
          </div>
        </div>`;
      })
      .join("");
  }

  // ---- dialog -------------------------------------------------------------
  _targetOptions(selected) {
    const favs = new Set(this._data.favorites);
    const T = this._data.targets;
    const opt = (t) => `<option value="${esc(t.entity_id)}"${t.entity_id === selected ? " selected" : ""}>${esc(t.name)}</option>`;
    let html = "";
    const f = T.filter((t) => favs.has(t.entity_id));
    if (f.length) html += `<optgroup label="★ Preferiti">${f.map(opt).join("")}</optgroup>`;
    for (const [dom, [label]] of Object.entries(DOMAINS)) {
      const g = T.filter((t) => t.entity_id.startsWith(dom + ".") && !favs.has(t.entity_id));
      if (g.length) html += `<optgroup label="${label}">${g.map(opt).join("")}</optgroup>`;
    }
    if (selected && !T.some((t) => t.entity_id === selected))
      html = `<option value="${esc(selected)}" selected>${esc(selected)} (non disponibile)</option>` + html;
    return html;
  }

  _syncStar() {
    const on = this._data.favorites.includes(this.$("target").value);
    this.$("star").classList.toggle("on", on);
    this.$("star").querySelector("ha-icon").setAttribute("icon", on ? "mdi:star" : "mdi:star-outline");
  }

  async _toggleFav(eid) {
    if (!eid) return;
    const fav = !this._data.favorites.includes(eid);
    try {
      const r = await this._hass.callWS({ type: "magic_links/favorite", entity_id: eid, favorite: fav });
      this._data.favorites = r.favorites;
    } catch (e) {
      return this._toast(e.message || "Errore", true);
    }
    this.$("target").innerHTML = this._targetOptions(eid);
    this._syncStar();
    this._renderFavs();
    this._renderList();
  }

  _open(link, presetTarget) {
    this._edit = link;
    const exp = this.$("exp");
    const opts = [
      ...(link ? [["keep", "Mantieni attuale"]] : []),
      ["24h", "Tra 24 ore"],
      ["48h", "Tra 48 ore"],
      ["date", "Fino a una data"],
      ["never", "Sempre valido"],
    ];
    exp.innerHTML = opts.map(([v, t]) => `<option value="${v}">${t}</option>`).join("");
    this.$("dtitle").textContent = link ? "Modifica link" : "Nuovo link";
    this.$("save").textContent = link ? "Salva modifiche" : "Crea link";
    this.$("editOpts").classList.toggle("hidden", !link);
    this.$("label").value = link?.label || "";
    this.$("assigned").value = link?.assigned_to || "";
    this.$("max").value = link?.max_uses || "";
    this.$("reset").checked = false;
    this.$("regen").checked = false;
    const sel = link?.target || presetTarget || this._data.favorites.find((f) => this._data.targets.some((t) => t.entity_id === f)) || this._data.targets[0]?.entity_id;
    this.$("target").innerHTML = this._targetOptions(sel);
    exp.value = link ? "keep" : this._data.default_expiry || "24h";
    this.$("date").value = link?.expires_at ? toDateInput(link.expires_at) : "";
    this.$("dateWrap").classList.toggle("hidden", exp.value !== "date");
    this._syncStar();
    this.$("dlg").showModal();
    this.$("label").focus();
  }

  async _save() {
    const exp = this.$("exp").value;
    let expires_at = null;
    if (exp === "24h" || exp === "48h") expires_at = new Date(Date.now() + parseInt(exp) * 3600 * 1000).toISOString();
    else if (exp === "date") {
      const d = this.$("date").value;
      if (!d) return this._toast("Scegli una data di scadenza", true);
      expires_at = new Date(`${d}T23:59:59`).toISOString();
    }
    const max = parseInt(this.$("max").value);
    const payload = {
      label: this.$("label").value.trim(),
      assigned_to: this.$("assigned").value.trim(),
      target: this.$("target").value,
      expires_at,
      max_uses: Number.isInteger(max) && max > 0 ? max : null,
    };
    try {
      if (this._edit) {
        await this._hass.callWS({
          type: "magic_links/update",
          link_id: this._edit.id,
          ...payload,
          keep_expiry: exp === "keep",
          reset_uses: this.$("reset").checked,
          regenerate_token: this.$("regen").checked,
        });
        this._toast(this.$("regen").checked ? "Salvato · nuovo link generato" : "Modifiche salvate");
      } else {
        await this._hass.callWS({ type: "magic_links/create", ...payload });
        this._toast("Link creato");
      }
      this.$("dlg").close();
      await this._load();
    } catch (e) {
      this._toast(e.message || "Errore nel salvataggio", true);
    }
  }

  async _act(act, id) {
    const link = this._data.links.find((l) => l.id === id);
    if (!link) return;
    if (act === "copy") return this._copy(this._url(link));
    if (act === "edit") return this._open(link);
    if (act === "share") {
      const url = this._url(link);
      if (navigator.share) {
        try {
          await navigator.share({ title: link.label, url });
        } catch (_) {}
      } else window.open(`https://wa.me/?text=${encodeURIComponent(`${link.label}: ${url}`)}`, "_blank", "noopener");
      return;
    }
    if (act === "delete") {
      if (!confirm(`Eliminare il link "${link.label}"? Smetterà di funzionare subito.`)) return;
      try {
        await this._hass.callWS({ type: "magic_links/delete", link_id: id });
        this._toast("Link eliminato");
        await this._load();
      } catch (e) {
        this._toast(e.message || "Errore nell'eliminazione", true);
      }
    }
  }

  async _copy(text) {
    try {
      await navigator.clipboard.writeText(text);
    } catch (_) {
      const t = document.createElement("textarea");
      t.value = text;
      document.body.appendChild(t);
      t.select();
      document.execCommand("copy");
      t.remove();
    }
    this._toast("Link copiato negli appunti");
  }
}

customElements.define("magic-links-panel", MagicLinksPanel);
