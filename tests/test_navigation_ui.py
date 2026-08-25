"""Regression coverage for the invariant application navigation shell."""

from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main
from conftest import sign_in


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app" / "templates"


def test_global_header_has_no_page_specific_controls() -> None:
    """Context and task actions belong below global navigation."""
    header = (TEMPLATES / "_site_header.html").read_text(encoding="utf-8")

    for page_specific_control in (
        "context_badge",
        "show_transcript_link",
        "show_viewer",
        "transcript-link",
        "nav-cta",
    ):
        assert page_specific_control not in header


def test_pages_render_exactly_one_shared_global_navbar() -> None:
    """Every normal page renders the same header once through base.html."""
    client = TestClient(main.app)
    sign_in(client, "navigation-shell@casecall.test")

    for path in ("/", "/cases", "/practice", "/profile", "/attempts/example/debrief"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.text.count('<header class="navbar">') == 1, path
        assert 'aria-label="Leo Home"' in response.text, path
        assert 'aria-label="Primary"' in response.text, path


def test_practice_controls_are_a_secondary_toolbar() -> None:
    """The live-session HUD augments the global shell instead of replacing it."""
    client = TestClient(main.app)
    sign_in(client, "practice-toolbar@casecall.test")

    response = client.get("/practice")

    assert response.status_code == 200
    assert response.text.count('<header class="navbar">') == 1
    assert response.text.count('aria-label="Live interview controls"') == 1
    assert response.text.index('<header class="navbar">') < response.text.index(
        'aria-label="Live interview controls"'
    )


def test_page_templates_do_not_define_competing_global_headers() -> None:
    """The base shell is the only owner of the navbar across page templates."""
    page_templates = (
        "landing.html",
        "cases.html",
        "practice.html",
        "profile.html",
        "debrief.html",
        "admin.html",
    )

    for filename in page_templates:
        content = (TEMPLATES / filename).read_text(encoding="utf-8")
        assert '{% extends "base.html" %}' in content, filename
        assert '<header class="navbar">' not in content, filename
        assert "header_partial" not in content, filename


def test_login_can_intentionally_hide_the_application_shell() -> None:
    """Authentication remains the explicit exception to the app shell."""
    client = TestClient(main.app)

    response = client.get("/login")

    assert response.status_code == 200
    assert '<header class="navbar">' not in response.text
