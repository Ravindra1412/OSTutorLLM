"""
tests/frontend/test_page_rendering.py

Part 3.11, Section 8 — Frontend Testing.

Honest scope note (documented once, here): this sandbox has no
headless browser binary available (no Chromium/Firefox install), so
true rendered-DOM/visual/cross-browser testing (Selenium/Playwright)
is not possible in this environment — flagged as a real, known
limitation in docs/project-report-part3.11.md Section 22, and listed
as a Future Improvement (Section 25) exactly as the phase brief
itself anticipates ("Automated UI Testing").

What this module DOES verify, for real, via BeautifulSoup parsing the
actual server-rendered HTML the Flask test client returns: navigation
links resolve to real routes (not dead hrefs), forms have properly
associated labels, buttons carry real text (not empty), interactive
JS-driven elements have the DOM hooks their driver script expects
(same element IDs the *.js files already reference), the viewport meta
tag for responsive design is present, and basic accessibility markers
(lang attribute, alt text on any img, label/input association).
"""

import pytest
from bs4 import BeautifulSoup

from tests.fixtures.factories import make_student, make_faculty, login

pytestmark = pytest.mark.frontend


def _soup(html_bytes) -> BeautifulSoup:
    return BeautifulSoup(html_bytes, "html.parser")


# --- Base template / responsive design (Section 8) ---

class TestBaseTemplate:
    def test_public_pages_have_viewport_meta_tag(self, client, app):
        resp = client.get("/")
        soup = _soup(resp.data)
        viewport = soup.find("meta", attrs={"name": "viewport"})
        assert viewport is not None
        assert "width=device-width" in viewport["content"]

    def test_html_lang_attribute_present(self, client, app):
        resp = client.get("/")
        soup = _soup(resp.data)
        assert soup.html.get("lang") == "en"

    def test_bootstrap_and_icons_loaded(self, client, app):
        resp = client.get("/")
        soup = _soup(resp.data)
        stylesheets = [link.get("href", "") for link in soup.find_all("link", rel="stylesheet")]
        assert any("bootstrap" in href for href in stylesheets)
        assert any("bootstrap-icons" in href for href in stylesheets)


# --- Forms (Section 8) ---

class TestForms:
    def test_login_form_fields_have_labels_or_placeholders(self, client, app):
        resp = client.get("/login")
        soup = _soup(resp.data)
        inputs = soup.find_all("input", attrs={"type": ["email", "password", "text"]})
        assert len(inputs) >= 2  # email + password at minimum
        for inp in inputs:
            has_label = bool(inp.get("id") and soup.find("label", attrs={"for": inp["id"]}))
            has_placeholder = bool(inp.get("placeholder"))
            has_aria = bool(inp.get("aria-label"))
            assert has_label or has_placeholder or has_aria, f"Input {inp.get('name', inp.get('id'))} has no accessible label"

    def test_registration_form_has_role_selector(self, client, app):
        resp = client.get("/register")
        soup = _soup(resp.data)
        # A role selector is required for registration to make sense —
        # could be a <select> or radio group; either satisfies this.
        assert soup.find("select", attrs={"name": "role"}) or soup.find_all("input", attrs={"name": "role"})


# --- Navigation (Section 8) ---

class TestNavigation:
    def test_faculty_dashboard_nav_links_are_real_routes(self, client, app):
        make_faculty(email="navfac@example.com")
        login(client, "navfac@example.com")
        resp = client.get("/faculty")
        soup = _soup(resp.data)

        nav_hrefs = [a["href"] for a in soup.find_all("a", href=True) if a["href"].startswith("/faculty")]
        assert len(nav_hrefs) >= 5  # students, analytics, content, quizzes, assignments, etc.

        for href in nav_hrefs:
            # Every linked faculty page must itself resolve (no dead links).
            page_resp = client.get(href)
            assert page_resp.status_code == 200, f"Faculty nav link {href} did not resolve"

    def test_student_dashboard_nav_links_are_real_routes(self, client, app):
        make_student(email="navstud@example.com")
        login(client, "navstud@example.com")
        resp = client.get("/dashboard")
        soup = _soup(resp.data)

        nav_hrefs = [a["href"] for a in soup.find_all("a", href=True) if a["href"].startswith("/dashboard")]
        for href in nav_hrefs:
            page_resp = client.get(href)
            assert page_resp.status_code == 200, f"Student nav link {href} did not resolve"


# --- Buttons (Section 8) ---

class TestButtons:
    def test_dashboard_buttons_have_visible_text_or_icon(self, client, app):
        make_student(email="btncheck@example.com")
        login(client, "btncheck@example.com")
        resp = client.get("/dashboard")
        soup = _soup(resp.data)

        buttons = soup.find_all("button")
        assert len(buttons) > 0
        for btn in buttons:
            has_text = bool(btn.get_text(strip=True))
            has_icon = bool(btn.find("i", class_=lambda c: c and "bi-" in c))
            assert has_text or has_icon, "A button has neither text nor an icon — inaccessible/confusing"


# --- Charts (Section 8) — presence of the canvas + chart library the JS targets ---

class TestCharts:
    def test_progress_page_has_chart_canvases_and_chartjs(self, client, app):
        make_student(email="chartcheck@example.com")
        login(client, "chartcheck@example.com")
        resp = client.get("/dashboard/progress")
        soup = _soup(resp.data)

        canvases = soup.find_all("canvas")
        assert len(canvases) >= 1
        scripts = [s.get("src", "") for s in soup.find_all("script", src=True)]
        assert any("chart.js" in s for s in scripts)

    def test_faculty_analytics_page_has_chart_canvases(self, client, app):
        make_faculty(email="factcharts@example.com")
        login(client, "factcharts@example.com")
        resp = client.get("/faculty/analytics")
        soup = _soup(resp.data)
        assert len(soup.find_all("canvas")) >= 2  # topic chart + trend chart


# --- Dashboard <-> JS driver contract (Section 8) ---

class TestDashboardJSContract:
    """The *.js files reference specific element IDs by getElementById —
    this confirms the HTML the server actually renders still has every
    ID its own driver script depends on (a real, common source of
    silent frontend breakage when a template is edited without
    checking its script)."""

    @pytest.mark.parametrize("page,required_ids", [
        ("/dashboard", ["dashboard-loading", "dashboard-content", "stat-overall", "stat-level"]),
        ("/faculty", ["loading", "content", "stat-total", "stat-active"]),
    ])
    def test_required_element_ids_present(self, client, app, page, required_ids):
        if page == "/dashboard":
            make_student(email="idcheck1@example.com")
            login(client, "idcheck1@example.com")
        else:
            make_faculty(email="idcheck2@example.com")
            login(client, "idcheck2@example.com")

        resp = client.get(page)
        soup = _soup(resp.data)
        for element_id in required_ids:
            assert soup.find(id=element_id) is not None, f"{page} is missing #{element_id}, which its JS driver depends on"


# --- Accessibility basics (Section 8) ---

class TestAccessibilityBasics:
    def test_images_have_alt_text(self, client, app):
        resp = client.get("/")
        soup = _soup(resp.data)
        for img in soup.find_all("img"):
            assert img.get("alt") is not None, f"<img src={img.get('src')}> is missing alt text"

    def test_no_empty_links(self, client, app):
        resp = client.get("/")
        soup = _soup(resp.data)
        for a in soup.find_all("a", href=True):
            has_text = bool(a.get_text(strip=True))
            has_icon = bool(a.find("i"))
            has_aria = bool(a.get("aria-label"))
            assert has_text or has_icon or has_aria, f"Empty, inaccessible link: {a}"
