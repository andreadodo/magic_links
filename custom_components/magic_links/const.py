"""Costanti di Magic Links."""
DOMAIN = "magic_links"
EVENT_USED = "magic_link_used"
ALLOWED_DOMAINS = ("automation", "script", "scene")
PANEL_PATH = "magic-links"
STATIC_URL = "/magic_links_static"

CONF_EXTERNAL_URL = "external_url"
CONF_DEFAULT_EXPIRY = "default_expiry"
CONF_CONFIRM_PAGE = "confirm_page"
CONF_MAX_FAILS = "max_fails"
CONF_FAIL_WINDOW = "fail_window"  # minuti
CONF_SIDEBAR = "show_sidebar"
CONF_SIDEBAR_TITLE = "sidebar_title"

DEFAULTS = {
    CONF_DEFAULT_EXPIRY: "24h",
    CONF_CONFIRM_PAGE: True,
    CONF_MAX_FAILS: 10,
    CONF_FAIL_WINDOW: 10,
    CONF_SIDEBAR: True,
    CONF_SIDEBAR_TITLE: "Link rapidi",
}
