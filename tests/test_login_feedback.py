"""Login page must surface API failures (not clear errors immediately)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGIN_PAGE = REPO_ROOT / "frontend" / "src" / "app" / "login" / "page.tsx"
AUTH_CONTEXT = REPO_ROOT / "frontend" / "src" / "contexts" / "auth-context.tsx"


def test_login_page_does_not_clear_auth_error_on_every_render() -> None:
    text = LOGIN_PAGE.read_text(encoding="utf-8")
    assert "useEffect(() => {\n    clearError();" not in text
    assert "result.ok" in text
    assert "setLocalError(result.error)" in text


def test_auth_context_clear_error_is_stable_and_login_returns_message() -> None:
    text = AUTH_CONTEXT.read_text(encoding="utf-8")
    assert "useCallback(() => {" in text
    assert "export type LoginResult" in text
    assert "loginMessageForFailure" in text
    assert "return { ok: false, error: msg }" in text
