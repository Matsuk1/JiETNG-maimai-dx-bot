import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"

USER_PORTAL_TEMPLATES = (
    "settings.html",
    "bind_form.html",
    "success.html",
    "error.html",
    "unbind_form.html",
    "loading.html",
    "liff_bootstrap.html",
)


def test_every_user_portal_page_uses_the_current_shared_stylesheet():
    for filename in USER_PORTAL_TEMPLATES:
        source = (TEMPLATES / filename).read_text()
        assert "/static/user-portal.css?v=20261027-8" in source


def test_every_html_brand_surface_uses_the_project_logo_asset():
    filenames = (*USER_PORTAL_TEMPLATES, "admin_login.html", "admin_panel.html")
    for filename in filenames:
        source = (TEMPLATES / filename).read_text()
        assert 'src="/static/pics/logo.png"' in source
        assert 'href="/static/pics/logo.png"' in source
        assert "logo-padded.png" not in source
        assert '>J</span>' not in source


def test_shared_and_admin_stylesheets_have_current_cache_versions():
    common = (TEMPLATES / "common_styles.html").read_text()
    admin_login = (TEMPLATES / "admin_login.html").read_text()
    admin_panel = (TEMPLATES / "admin_panel.html").read_text()

    assert "/static/ui-system.css?v=20261027-6" in common
    assert "/static/admin-login.css?v=20261027-4" in admin_login
    assert "/static/admin-control-center.css?v=20261027-11" in admin_panel
    assert "/static/admin-panel.js?v=20261027-6" in admin_panel


def test_logo_css_preserves_transparency_and_safe_space():
    shared = (ROOT / "assets" / "ui-system.css").read_text()
    portal = (ROOT / "assets" / "user-portal.css").read_text()
    admin = (ROOT / "assets" / "admin-control-center.css").read_text()

    for source in (shared, portal, admin):
        assert "object-fit: contain" in source
        assert "background: transparent" in source
        assert "border-radius: 0" in source


def test_mobile_settings_layout_is_flat_and_uses_single_arrow_selects():
    shared = (ROOT / "assets" / "ui-system.css").read_text()
    portal = (ROOT / "assets" / "user-portal.css").read_text()
    settings = (TEMPLATES / "settings.html").read_text()

    assert "appearance: none" in shared
    assert ".user-portal { padding: 0; background: var(--portal-paper); }" in portal
    assert "border: 0; border-radius: 0; box-shadow: none" in portal
    assert '<button type="submit" id="submit-btn"' in settings
    assert '<input type="submit" id="submit-btn"' not in settings


def test_admin_web_app_icon_uses_transparent_logo_and_paper_palette():
    main_source = (ROOT / "main.py").read_text()
    icon_template = (TEMPLATES / "images" / "admin_icon.html").read_text()
    manifest = json.loads((ROOT / "assets" / "manifest.json").read_text())

    assert '"pics", "logo.png"' in main_source
    assert '"pics", "logo-padded.png"' not in main_source
    assert "background: rgb(247,243,237)" in icon_template
    assert "padding: 88px" in icon_template
    assert "object-fit: contain" in icon_template
    assert manifest["background_color"] == "#f7f3ed"
    assert manifest["theme_color"] == "#cf6846"


def test_admin_panel_uses_flat_monitor_layout_and_icon_actions():
    panel = (TEMPLATES / "admin_panel.html").read_text()
    styles = (ROOT / "assets" / "admin-control-center.css").read_text()
    script = (ROOT / "assets" / "admin-panel.js").read_text()

    assert ".tab-content { display: none; width: min(100%,1280px); margin-inline: auto; }" in styles
    assert ".chart-panel { min-height: 0; }" in styles
    assert "grid-template-columns: repeat(2,minmax(0,1fr))" in styles
    assert 'id="ai-monitor-send" type="submit" aria-label="Send diagnosis"' in panel
    assert 'id="create-backup-btn" onclick="createBackup()" aria-label="Create backup"' in panel
    assert 'id="notice-save-btn" aria-label="Save notice"' in panel
    assert "setAdminIconButtonState(button, busy ? 'Stop diagnosis' : 'Send diagnosis'" in script

    forbidden_text_actions = (
        ">Clear Cache<",
        ">Load More<",
        ">Create New Notice<",
        ">Update &amp; Check<",
        ">Create New Tip/Ad<",
        ">Send<",
        ">Save Changes<",
    )
    for action in forbidden_text_actions:
        assert action not in panel


def test_admin_mobile_safe_area_and_user_list_hierarchy():
    panel = (TEMPLATES / "admin_panel.html").read_text()
    styles = (ROOT / "assets" / "admin-control-center.css").read_text()
    script = (ROOT / "assets" / "admin-panel.js").read_text()

    assert "navigator.standalone" not in panel
    assert "document.body.style.paddingTop" not in panel
    assert "padding-top: 0 !important" in styles
    assert 'id="user-result-count"' in panel
    assert 'class="user-search-field"' in panel
    assert 'class="user-identity"' in script
    assert 'class="user-id-row"' in script
    assert 'class="user-meta-row"' in script
    assert 'class="user-link-state ${linked ? \'is-linked\' : \'is-unbound\'}"' in script
    assert "toggleIcon?.classList.toggle('is-open', expanded)" in script
