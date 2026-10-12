"""Magic Links: link senza autenticazione per lanciare automazioni, script o scene."""
from __future__ import annotations

import html
import logging
import secrets
import time
from pathlib import Path

import voluptuous as vol
from aiohttp import web

from homeassistant.components import panel_custom, websocket_api
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

DOMAIN = "magic_links"
EVENT_USED = "magic_link_used"
ALLOWED_DOMAINS = ("automation", "script", "scene")
MAX_FAILS = 10  # tentativi falliti per IP...
FAIL_WINDOW = 600  # ...in questa finestra (secondi)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            lambda v: v or {},
            vol.Schema({vol.Optional("external_url"): cv.url}),
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PAGE = """<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>{title}</title>
<style>
body{{margin:0;min-height:100vh;display:grid;place-items:center;font-family:system-ui,sans-serif;
background:#f3f4f6;color:#111827}}
main{{background:#fff;padding:2rem;border-radius:16px;max-width:340px;width:calc(100% - 3rem);
text-align:center;box-shadow:0 2px 12px rgba(0,0,0,.08)}}
h1{{font-size:1.25rem;margin:0 0 1rem}}p{{color:#6b7280;margin:0}}
button{{font:inherit;font-size:1.1rem;width:100%;padding:.9rem;border:0;border-radius:12px;
background:#2563eb;color:#fff;cursor:pointer}}
</style></head><body><main>{body}</main></body></html>"""


def _page(title: str, body: str, status: int = 200) -> web.Response:
    return web.Response(
        text=PAGE.format(title=title, body=body),
        content_type="text/html",
        status=status,
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
    )


class LinkManager:
    """Storage e logica dei link."""

    def __init__(self, hass: HomeAssistant, external_url: str | None) -> None:
        self.hass = hass
        self.external_url = external_url
        self._store: Store = Store(hass, 1, DOMAIN)
        self.links: dict[str, dict] = {}
        self._fails: dict[str, list[float]] = {}

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self.links = data.get("links", {})

    def _save(self) -> None:
        self._store.async_delay_save(lambda: {"links": self.links}, 1)

    def base_url(self) -> str:
        if self.external_url:
            return self.external_url.rstrip("/")
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

    def delete(self, link_id: str) -> bool:
        if self.links.pop(link_id, None) is None:
            return False
        self._save()
        return True

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
        fails = [t for t in self._fails.get(ip, []) if now - t < FAIL_WINDOW]
        self._fails[ip] = fails
        return len(fails) >= MAX_FAILS

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
                "automation",
                "trigger",
                {"entity_id": target, "skip_condition": True},
                blocking=False,
            )
        else:
            await self.hass.services.async_call(
                domain, "turn_on", {"entity_id": target}, blocking=False
            )
        return True


class MagicLinkView(HomeAssistantView):
    """GET mostra la conferma, POST esegue (i preview di WhatsApp/Telegram fanno solo GET)."""

    url = "/api/magic_link/{token}"
    name = "api:magic_link"
    requires_auth = False

    def __init__(self, mgr: LinkManager) -> None:
        self.mgr = mgr

    def _check(self, request: web.Request, token: str):
        ip = request.remote or "?"
        if self.mgr.blocked(ip):
            return None, _page("Troppi tentativi", "<h1>Troppi tentativi</h1><p>Riprova più tardi.</p>", 429)
        link = self.mgr.find(token)
        if link is None:
            self.mgr.fail(ip)
            return None, _page("Link non valido", "<h1>Link non valido</h1>", 404)
        if self.mgr.status(link) != "ok":
            return None, _page("Link scaduto", "<h1>Link scaduto</h1><p>Chiedi un nuovo link.</p>", 410)
        return link, None

    async def get(self, request: web.Request, token: str) -> web.Response:
        link, err = self._check(request, token)
        if err:
            return err
        label = html.escape(link["label"])
        return _page(label, f'<h1>{label}</h1><form method="post"><button type="submit">Conferma</button></form>')

    async def post(self, request: web.Request, token: str) -> web.Response:
        link, err = self._check(request, token)
        if err:
            return err
        if await self.mgr.run(link):
            return _page("Fatto", "<h1>✓ Fatto</h1>")
        return _page("Errore", "<h1>Azione non disponibile</h1>", 500)


# --- websocket (solo admin) -------------------------------------------------
@websocket_api.websocket_command({vol.Required("type"): "magic_links/list"})
@websocket_api.require_admin
@callback
def ws_list(hass, connection, msg):
    mgr: LinkManager = hass.data[DOMAIN]
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
        vol.Optional("max_uses"): vol.Any(None, vol.All(int, vol.Range(min=1))),
    }
)
@websocket_api.require_admin
@callback
def ws_create(hass, connection, msg):
    mgr: LinkManager = hass.data[DOMAIN]
    target = msg["target"]
    if target.split(".", 1)[0] not in ALLOWED_DOMAINS or hass.states.get(target) is None:
        connection.send_error(msg["id"], "invalid_target", "Entità non valida")
        return
    expires_at = None
    if msg.get("expires_at"):
        dt = dt_util.parse_datetime(msg["expires_at"])
        if dt is None:
            connection.send_error(msg["id"], "invalid_date", "Data non valida")
            return
        expires_at = dt_util.as_utc(dt).isoformat()
    link = mgr.create(msg["label"], msg["assigned_to"], target, expires_at, msg.get("max_uses"))
    connection.send_result(msg["id"], {"id": link["id"]})


@websocket_api.websocket_command(
    {vol.Required("type"): "magic_links/delete", vol.Required("link_id"): cv.string}
)
@websocket_api.require_admin
@callback
def ws_delete(hass, connection, msg):
    if hass.data[DOMAIN].delete(msg["link_id"]):
        connection.send_result(msg["id"])
    else:
        connection.send_error(msg["id"], "not_found", "Link non trovato")


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    conf = config.get(DOMAIN) or {}
    mgr = LinkManager(hass, conf.get("external_url"))
    await mgr.async_load()
    hass.data[DOMAIN] = mgr

    hass.http.register_view(MagicLinkView(mgr))
    for cmd in (ws_list, ws_create, ws_delete):
        websocket_api.async_register_command(hass, cmd)

    await hass.http.async_register_static_paths(
        [StaticPathConfig("/magic_links_static/panel.js", str(Path(__file__).parent / "panel.js"), False)]
    )
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name="magic-links-panel",
        frontend_url_path="magic-links",
        module_url="/magic_links_static/panel.js",
        sidebar_title="Link rapidi",
        sidebar_icon="mdi:link-variant",
        require_admin=True,
    )
    return True
