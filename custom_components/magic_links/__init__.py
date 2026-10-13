"""Magic Links: link senza autenticazione per lanciare automazioni, script o scene."""
from __future__ import annotations

import html
import logging
import secrets
import time
from pathlib import Path

import voluptuous as vol
from aiohttp import web

from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import (
    ALLOWED_DOMAINS,
    CONF_CONFIRM_PAGE,
    CONF_DEFAULT_EXPIRY,
    CONF_EXTERNAL_URL,
    CONF_FAIL_WINDOW,
    CONF_MAX_FAILS,
    CONF_SIDEBAR,
    CONF_SIDEBAR_TITLE,
    DEFAULTS,
    DOMAIN,
    EVENT_USED,
    PANEL_PATH,
    STATIC_URL,
)

_LOGGER = logging.getLogger(__name__)

# Compatibilità: la vecchia configurazione YAML viene importata una volta sola.
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            lambda v: v or {},
            vol.Schema({vol.Optional(CONF_EXTERNAL_URL): cv.url}),
        )
    },
    extra=vol.ALLOW_EXTRA,
)

LOGO = (
    '<svg viewBox="0 0 64 64" width="56" height="56"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#38bdf8"/><stop offset="1" stop-color="#1d4ed8"/></linearGradient></defs>'
    '<rect width="64" height="64" rx="15" fill="url(#g)"/>'
    '<g fill="none" stroke="#fff" stroke-width="5.5" stroke-linecap="round" transform="rotate(-45 32 32)">'
    '<rect x="9" y="23" width="26" height="18" rx="9"/><rect x="29" y="23" width="26" height="18" rx="9"/></g>'
    '<path d="M38 8 25 30h8l-4 14 14-22h-9z" fill="#fde047" stroke="#1d4ed8" stroke-width="2" '
    'stroke-linejoin="round" transform="translate(8.5 13.8) scale(.7)"/></svg>'
)

PAGE = """<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>{title}</title>
<style>
:root{{color-scheme:light dark;--bg:#eef2f7;--card:#fff;--fg:#0f172a;--mut:#64748b}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0b1220;--card:#111a2e;--fg:#e2e8f0;--mut:#94a3b8}}}}
body{{margin:0;min-height:100vh;display:grid;place-items:center;font-family:system-ui,-apple-system,sans-serif;
background:radial-gradient(circle at 20% 0,#38bdf833,transparent 50%),var(--bg);color:var(--fg)}}
main{{background:var(--card);padding:2rem 1.5rem;border-radius:22px;max-width:340px;width:calc(100% - 3rem);
text-align:center;box-shadow:0 10px 40px rgba(15,23,42,.15)}}
main svg{{margin-bottom:.75rem}}h1{{font-size:1.3rem;margin:0 0 1.25rem}}p{{color:var(--mut);margin:0}}
button{{font:inherit;font-weight:600;font-size:1.05rem;width:100%;padding:1rem;border:0;border-radius:14px;
background:linear-gradient(135deg,#38bdf8,#1d4ed8);color:#fff;cursor:pointer}}
button:active{{transform:scale(.98)}}.ok{{font-size:3rem;margin:0}}
</style></head><body><main>{logo}{body}</main></body></html>"""


def _page(title: str, body: str, status: int = 200) -> web.Response:
    return web.Response(
        text=PAGE.format(title=title, body=body, logo=LOGO),
        content_type="text/html",
        status=status,
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
    )


class LinkManager:
    """Storage e logica dei link."""

    def __init__(self, hass: HomeAssistant, options: dict) -> None:
        self.hass = hass
        self.opts = {**DEFAULTS, **options}
        self._store: Store = Store(hass, 1, DOMAIN)
        self.links: dict[str, dict] = {}
        self.favorites: list[str] = []
        self._fails: dict[str, list[float]] = {}

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self.links = data.get("links", {})
        self.favorites = data.get("favorites", [])

    def _payload(self) -> dict:
        return {"links": self.links, "favorites": self.favorites}

    def _save(self) -> None:
        self._store.async_delay_save(self._payload, 1)

    async def async_flush(self) -> None:
        await self._store.async_save(self._payload())

    def base_url(self) -> str:
        if self.opts.get(CONF_EXTERNAL_URL):
            return self.opts[CONF_EXTERNAL_URL].rstrip("/")
        try:
            return get_url(self.hass, prefer_external=True)
        except NoURLAvailableError:
            return ""

    # --- CRUD -----------------------------------------------------------
    def create(self, label, assigned_to, target, expires_at, max_uses) -> dict:
        link_id = secrets.token_hex(4)
        link = {
            "id": link_id,
            "token": secrets.token_urlsafe(24),
            "label": label,
            "assigned_to": assigned_to,
            "target": target,
            "created_at": dt_util.utcnow().isoformat(),
            "expires_at": expires_at,
            "max_uses": max_uses,
            "uses": 0,
            "last_used": None,
        }
        self.links[link_id] = link
        self._save()
        return link

    def update(self, link_id, *, label, assigned_to, target, expires_at, keep_expiry, max_uses, reset_uses, regenerate) -> bool:
        link = self.links.get(link_id)
        if link is None:
            return False
        link.update(label=label, assigned_to=assigned_to, target=target, max_uses=max_uses)
        if not keep_expiry:
            link["expires_at"] = expires_at
        if reset_uses:
            link["uses"] = 0
        if regenerate:
            link["token"] = secrets.token_urlsafe(24)
        self._save()
        return True

    def delete(self, link_id: str) -> bool:
        if self.links.pop(link_id, None) is None:
            return False
        self._save()
        return True

    def set_favorite(self, entity_id: str, favorite: bool) -> None:
        if favorite and entity_id not in self.favorites:
            self.favorites.append(entity_id)
        elif not favorite and entity_id in self.favorites:
            self.favorites.remove(entity_id)
        self._save()

    # --- validazione ----------------------------------------------------
    def find(self, token: str) -> dict | None:
        found = None
        for link in self.links.values():  # niente early-exit: tempo costante
            if secrets.compare_digest(link["token"].encode(), token.encode()):
                found = link
        return found

    @staticmethod
    def status(link: dict) -> str:
        exp = link.get("expires_at")
        if exp:
            dt = dt_util.parse_datetime(exp)
            if dt is None or dt <= dt_util.utcnow():
                return "expired"
        max_uses = link.get("max_uses")
        if max_uses and link["uses"] >= max_uses:
            return "exhausted"
        return "ok"

    # --- anti brute-force -------------------------------------------------
    def blocked(self, ip: str) -> bool:
        now = time.monotonic()
        window = int(self.opts[CONF_FAIL_WINDOW]) * 60
        fails = [t for t in self._fails.get(ip, []) if now - t < window]
        self._fails[ip] = fails
        return len(fails) >= int(self.opts[CONF_MAX_FAILS])

    def fail(self, ip: str) -> None:
        self._fails.setdefault(ip, []).append(time.monotonic())

    # --- esecuzione -------------------------------------------------------
    async def run(self, link: dict) -> bool:
        target = link["target"]
        domain = target.split(".", 1)[0]
        if domain not in ALLOWED_DOMAINS or self.hass.states.get(target) is None:
            return False
        link["uses"] += 1
        link["last_used"] = dt_util.utcnow().isoformat()
        self._save()
        self.hass.bus.async_fire(
            EVENT_USED,
            {
                "link_id": link["id"],
                "label": link["label"],
                "assigned_to": link["assigned_to"],
                "target": target,
            },
        )
        if domain == "automation":
            await self.hass.services.async_call(
                "automation", "trigger", {"entity_id": target, "skip_condition": True}, blocking=False
            )
        else:
            await self.hass.services.async_call(domain, "turn_on", {"entity_id": target}, blocking=False)
        return True


class MagicLinkView(HomeAssistantView):
    """GET mostra la conferma, POST esegue (i preview di WhatsApp/Telegram fanno solo GET)."""

    url = "/api/magic_link/{token}"
    name = "api:magic_link"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    def _check(self, request: web.Request, token: str):
        mgr: LinkManager | None = self.hass.data[DOMAIN]["mgr"]
        if mgr is None:
            return None, None, _page("Non disponibile", "<h1>Servizio non disponibile</h1>", 503)
        ip = request.remote or "?"
        if mgr.blocked(ip):
            return None, None, _page("Troppi tentativi", "<h1>Troppi tentativi</h1><p>Riprova più tardi.</p>", 429)
        link = mgr.find(token)
        if link is None:
            mgr.fail(ip)
            return None, None, _page("Link non valido", "<h1>Link non valido</h1>", 404)
        if mgr.status(link) != "ok":
            return None, None, _page("Link scaduto", "<h1>Link scaduto</h1><p>Chiedi un nuovo link.</p>", 410)
        return mgr, link, None

    async def _execute(self, mgr: LinkManager, link: dict) -> web.Response:
        if await mgr.run(link):
            return _page("Fatto", '<p class="ok">✅</p><h1>Fatto!</h1>')
        return _page("Errore", "<h1>Azione non disponibile</h1>", 500)

    async def get(self, request: web.Request, token: str) -> web.Response:
        mgr, link, err = self._check(request, token)
        if err:
            return err
        if not mgr.opts[CONF_CONFIRM_PAGE]:
            return await self._execute(mgr, link)
        label = html.escape(link["label"])
        return _page(label, f'<h1>{label}</h1><form method="post"><button type="submit">Conferma</button></form>')

    async def post(self, request: web.Request, token: str) -> web.Response:
        mgr, link, err = self._check(request, token)
        if err:
            return err
        return await self._execute(mgr, link)


# --- websocket (solo admin) -------------------------------------------------
def _mgr(hass: HomeAssistant) -> LinkManager:
    return hass.data[DOMAIN]["mgr"]


def _valid_target(hass: HomeAssistant, target: str) -> bool:
    return target.split(".", 1)[0] in ALLOWED_DOMAINS and hass.states.get(target) is not None


def _parse_expiry(value):
    """Restituisce (ok, iso_utc | None)."""
    if not value:
        return True, None
    dt = dt_util.parse_datetime(value)
    if dt is None:
        return False, None
    return True, dt_util.as_utc(dt).isoformat()


MAX_USES = vol.Any(None, vol.All(int, vol.Range(min=1)))


@websocket_api.websocket_command({vol.Required("type"): "magic_links/list"})
@websocket_api.require_admin
@callback
def ws_list(hass, connection, msg):
    mgr = _mgr(hass)
    targets = sorted(
        ({"entity_id": s.entity_id, "name": s.name} for s in hass.states.async_all(ALLOWED_DOMAINS)),
        key=lambda t: t["name"].lower(),
    )
    links = sorted(mgr.links.values(), key=lambda x: x["created_at"], reverse=True)
    connection.send_result(
        msg["id"],
        {
            "base_url": mgr.base_url(),
            "targets": targets,
            "favorites": mgr.favorites,
            "default_expiry": mgr.opts[CONF_DEFAULT_EXPIRY],
            "sidebar_title": mgr.opts[CONF_SIDEBAR_TITLE],
            "links": [{**x, "status": mgr.status(x)} for x in links],
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "magic_links/create",
        vol.Required("label"): cv.string,
        vol.Optional("assigned_to", default=""): cv.string,
        vol.Required("target"): cv.entity_id,
        vol.Optional("expires_at"): vol.Any(None, cv.string),
        vol.Optional("max_uses"): MAX_USES,
    }
)
@websocket_api.require_admin
@callback
def ws_create(hass, connection, msg):
    if not _valid_target(hass, msg["target"]):
        connection.send_error(msg["id"], "invalid_target", "Entità non valida")
        return
    ok, expires_at = _parse_expiry(msg.get("expires_at"))
    if not ok:
        connection.send_error(msg["id"], "invalid_date", "Data non valida")
        return
    link = _mgr(hass).create(msg["label"], msg["assigned_to"], msg["target"], expires_at, msg.get("max_uses"))
    connection.send_result(msg["id"], {"id": link["id"]})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "magic_links/update",
        vol.Required("link_id"): cv.string,
        vol.Required("label"): cv.string,
        vol.Optional("assigned_to", default=""): cv.string,
        vol.Required("target"): cv.entity_id,
        vol.Optional("expires_at"): vol.Any(None, cv.string),
        vol.Optional("keep_expiry", default=False): bool,
        vol.Optional("max_uses"): MAX_USES,
        vol.Optional("reset_uses", default=False): bool,
        vol.Optional("regenerate_token", default=False): bool,
    }
)
@websocket_api.require_admin
@callback
def ws_update(hass, connection, msg):
    mgr = _mgr(hass)
    link = mgr.links.get(msg["link_id"])
    if link is None:
        connection.send_error(msg["id"], "not_found", "Link non trovato")
        return
    # il target può restare invariato anche se l'entità non esiste più
    if msg["target"] != link["target"] and not _valid_target(hass, msg["target"]):
        connection.send_error(msg["id"], "invalid_target", "Entità non valida")
        return
    ok, expires_at = _parse_expiry(msg.get("expires_at"))
    if not ok:
        connection.send_error(msg["id"], "invalid_date", "Data non valida")
        return
    mgr.update(
        msg["link_id"],
        label=msg["label"],
        assigned_to=msg["assigned_to"],
        target=msg["target"],
        expires_at=expires_at,
        keep_expiry=msg["keep_expiry"],
        max_uses=msg.get("max_uses"),
        reset_uses=msg["reset_uses"],
        regenerate=msg["regenerate_token"],
    )
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {vol.Required("type"): "magic_links/delete", vol.Required("link_id"): cv.string}
)
@websocket_api.require_admin
@callback
def ws_delete(hass, connection, msg):
    if _mgr(hass).delete(msg["link_id"]):
        connection.send_result(msg["id"])
    else:
        connection.send_error(msg["id"], "not_found", "Link non trovato")


@websocket_api.websocket_command(
    {
        vol.Required("type"): "magic_links/favorite",
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("favorite"): bool,
    }
)
@websocket_api.require_admin
@callback
def ws_favorite(hass, connection, msg):
    _mgr(hass).set_favorite(msg["entity_id"], msg["favorite"])
    connection.send_result(msg["id"], {"favorites": _mgr(hass).favorites})


# --- setup ------------------------------------------------------------------
async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {"mgr": None, "registered": False})
    if DOMAIN in config:
        _LOGGER.info("Configurazione YAML di Magic Links importata: ora puoi rimuoverla da configuration.yaml")
        hass.async_create_task(
            hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_IMPORT}, data=config[DOMAIN])
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    state = hass.data.setdefault(DOMAIN, {"mgr": None, "registered": False})
    mgr = LinkManager(hass, dict(entry.options))
    await mgr.async_load()
    state["mgr"] = mgr

    panel_js = Path(__file__).parent / "panel.js"
    if not state["registered"]:
        hass.http.register_view(MagicLinkView(hass))
        for cmd in (ws_list, ws_create, ws_update, ws_delete, ws_favorite):
            websocket_api.async_register_command(hass, cmd)
        await hass.http.async_register_static_paths([StaticPathConfig(f"{STATIC_URL}/panel.js", str(panel_js), False)])
        state["registered"] = True

    mtime = int(await hass.async_add_executor_job(lambda: panel_js.stat().st_mtime))
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name="magic-links-panel",
        frontend_url_path=PANEL_PATH,
        module_url=f"{STATIC_URL}/panel.js?v={mtime}",
        sidebar_title=mgr.opts[CONF_SIDEBAR_TITLE] if mgr.opts[CONF_SIDEBAR] else None,
        sidebar_icon="mdi:link-variant" if mgr.opts[CONF_SIDEBAR] else None,
        require_admin=True,
    )
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    state = hass.data[DOMAIN]
    if state["mgr"] is not None:
        await state["mgr"].async_flush()
        state["mgr"] = None
    frontend.async_remove_panel(hass, PANEL_PATH)
    return True
