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
        assert "/static/user-portal.css?v=20261027-6" in source


def test_every_html_brand_surface_uses_the_project_logo_asset():
    filenames = (*USER_PORTAL_TEMPLATES, "admin_login.html", "admin_panel.html")
    for filename in filenames:
        source = (TEMPLATES / filename).read_text()
        assert 'src="/static/pics/logo.png"' in source
        assert '>J</span>' not in source


def test_shared_and_admin_stylesheets_have_current_cache_versions():
    common = (TEMPLATES / "common_styles.html").read_text()
    admin_login = (TEMPLATES / "admin_login.html").read_text()
    admin_panel = (TEMPLATES / "admin_panel.html").read_text()

    assert "/static/ui-system.css?v=20261027-4" in common
    assert "/static/admin-login.css?v=20261027-3" in admin_login
    assert "/static/admin-control-center.css?v=20261027-7" in admin_panel
