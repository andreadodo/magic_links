const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (iso) =>
  iso ? new Date(iso).toLocaleString("it-IT", { dateStyle: "short", timeStyle: "short" }) : "";

const STATUS = {
  ok: ["Attivo", "var(--success-color, #2e7d32)"],
  expired: ["Scaduto", "var(--error-color, #c62828)"],
  exhausted: ["Usi esauriti", "var(--warning-color, #ef6c00)"],
};

class MagicLinksPanel extends HTMLElement {
  constructor() {
    super();
    this._data = { links: [], targets: [], base_url: "" };
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

  _build() {
    this.shadowRoot.innerHTML = `
      <style>
        :host{display:block;min-height:100%;background:var(--primary-background-color);color:var(--primary-text-color);font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif)}
        header{display:flex;align-items:center;gap:8px;padding:12px 16px;background:var(--app-header-background-color,var(--primary-color));color:var(--app-header-text-color,#fff)}
        header h1{font-size:20px;font-weight:500;margin:0}
        .wrap{max-width:900px;margin:0 auto;padding:16px}
        section{background:var(--card-background-color);border-radius:var(--ha-card-border-radius,12px);padding:16px;margin-bottom:16px;border:1px solid var(--divider-color)}
        h2{font-size:16px;margin:0 0 12px}
        form{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;align-items:end}
        label{display:flex;flex-direction:column;gap:4px;font-size:13px;color:var(--secondary-text-color)}
        input,select{font:inherit;padding:9px 10px;border-radius:8px;border:1px solid var(--divider-color);background:var(--primary-background-color);color:var(--primary-text-color)}
        button{font:inherit;cursor:pointer;padding:9px 14px;border-radius:8px;border:1px solid var(--divider-color);background:transparent;color:var(--primary-text-color)}
        button.primary{background:var(--primary-color);border-color:var(--primary-color);color:var(--text-primary-color,#fff)}
        button.danger{color:var(--error-color,#c62828)}
        .hidden{display:none}
        .link{display:flex;flex-wrap:wrap;gap:8px 16px;justify-content:space-between;padding:12px 0;border-top:1px solid var(--divider-color)}
        .link:first-of-type{border-top:0}
        .meta{font-size:13px;color:var(--secondary-text-color);line-height:1.5}
        .title{font-weight:500;font-size:15px}
        .chip{display:inline-block;font-size:12px;padding:1px 8px;border-radius:10px;color:#fff;margin-left:8px;vertical-align:middle}
        .actions{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
        .empty{color:var(--secondary-text-color);padding:8px 0}
        #msg{min-height:20px;font-size:13px;margin-top:8px;color:var(--secondary-text-color)}
      </style>
      <header><span id="menu"></span><h1>Link rapidi</h1></header>
      <div class="wrap">
        <section>
          <h2>Nuovo link</h2>
          <form id="form">
            <label>Nome del link<input id="label" required placeholder="Es. Cancello ospiti"></label>
            <label>Assegnato a<input id="assigned" placeholder="Es. Marco (idraulico)"></label>
            <label>Azione<select id="target" required></select></label>
            <label>Scadenza
              <select id="exp">
                <option value="24h">Tra 24 ore</option>
                <option value="48h">Tra 48 ore</option>
                <option value="date">Fino a una data</option>
                <option value="never">Sempre valido</option>
              </select>
            </label>
            <label id="dateWrap" class="hidden">Data di scadenza<input id="date" type="date"></label>
            <label>Usi massimi (facoltativo)<input id="max" type="number" min="1" placeholder="Illimitati"></label>
            <button class="primary" type="submit">Crea link</button>
          </form>
          <div id="msg"></div>
        </section>
        <section>
          <h2>Link creati</h2>
          <div id="list"></div>
        </section>
      </div>`;

    const $ = (id) => this.shadowRoot.getElementById(id);
    this._menu = document.createElement("ha-menu-button");
    this._menu.hass = this._hass;
    this._menu.narrow = this._narrow;
    $("menu").appendChild(this._menu);

    $("exp").addEventListener("change", () => $("dateWrap").classList.toggle("hidden", $("exp").value !== "date"));
    $("form").addEventListener("submit", (e) => {
      e.preventDefault();
      this._create();
    });
    $("list").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-act]");
      if (b) this._act(b.dataset.act, b.dataset.id);
    });
  }

  $(id) {
    return this.shadowRoot.getElementById(id);
  }

  _toast(text, error = false) {
    const m = this.$("msg");
    m.textContent = text;
    m.style.color = error ? "var(--error-color,#c62828)" : "var(--secondary-text-color)";
    clearTimeout(this._t);
    this._t = setTimeout(() => (m.textContent = ""), 4000);
  }

  async _load() {
    try {
      this._data = await this._hass.callWS({ type: "magic_links/list" });
    } catch (e) {
      this._toast(e.message || "Errore nel caricamento", true);
      return;
    }
    const sel = this.$("target");
    const prev = sel.value;
    sel.innerHTML = this._data.targets
      .map((t) => `<option value="${esc(t.entity_id)}">${esc(t.name)} (${esc(t.entity_id.split(".")[0])})</option>`)
      .join("");
    if (prev) sel.value = prev;
    this._renderList();
  }

  _url(link) {
    const base = this._data.base_url || location.origin;
    return `${base}/api/magic_link/${link.token}`;
  }

  _renderList() {
    const names = Object.fromEntries(this._data.targets.map((t) => [t.entity_id, t.name]));
    const items = this._data.links.map((l) => {
      const [txt, col] = STATUS[l.status] || STATUS.ok;
      const uses = l.max_uses ? `${l.uses}/${l.max_uses} usi` : `${l.uses} usi`;
      return `<div class="link">
        <div>
          <div class="title">${esc(l.label)}<span class="chip" style="background:${col}">${txt}</span></div>
          <div class="meta">
            ${l.assigned_to ? `Assegnato a <b>${esc(l.assigned_to)}</b><br>` : ""}
            Azione: ${esc(names[l.target] || l.target)}<br>
            Scadenza: ${l.expires_at ? fmt(l.expires_at) : "sempre valido"} · ${uses}${l.last_used ? ` · ultimo uso ${fmt(l.last_used)}` : ""}
          </div>
        </div>
        <div class="actions">
          <button data-act="copy" data-id="${l.id}">Copia</button>
          <button data-act="share" data-id="${l.id}">Condividi</button>
          <button class="danger" data-act="delete" data-id="${l.id}">Elimina</button>
        </div>
      </div>`;
    });
    this.$("list").innerHTML = items.join("") || `<div class="empty">Nessun link. Creane uno qui sopra.</div>`;
  }

  async _create() {
    const exp = this.$("exp").value;
    let expires_at = null;
    if (exp === "24h" || exp === "48h") {
      expires_at = new Date(Date.now() + parseInt(exp) * 3600 * 1000).toISOString();
    } else if (exp === "date") {
      const d = this.$("date").value;
      if (!d) return this._toast("Scegli una data di scadenza", true);
      expires_at = new Date(`${d}T23:59:59`).toISOString();
    }
    const max = parseInt(this.$("max").value);
    try {
      await this._hass.callWS({
        type: "magic_links/create",
        label: this.$("label").value.trim(),
        assigned_to: this.$("assigned").value.trim(),
        target: this.$("target").value,
        expires_at,
        max_uses: Number.isInteger(max) && max > 0 ? max : null,
      });
      this.$("form").reset();
      this.$("dateWrap").classList.add("hidden");
      this._toast("Link creato");
      await this._load();
    } catch (e) {
      this._toast(e.message || "Errore nella creazione", true);
    }
  }

  async _act(act, id) {
    const link = this._data.links.find((l) => l.id === id);
    if (!link) return;
    if (act === "copy") return this._copy(this._url(link));
    if (act === "share") {
      const url = this._url(link);
      if (navigator.share) {
        try {
          await navigator.share({ title: link.label, url });
        } catch (_) {}
      } else {
        window.open(`https://wa.me/?text=${encodeURIComponent(`${link.label}: ${url}`)}`, "_blank", "noopener");
      }
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
    this._toast("Link copiato");
  }
}

customElements.define("magic-links-panel", MagicLinksPanel);
