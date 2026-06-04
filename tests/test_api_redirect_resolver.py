"""
Regression: same-origin dev proxy 308 must not resolve redirect target to "/".

Mirrors frontend ApiClient.resolveEndpointFromRedirect when baseURL is empty.
"""


def resolve_endpoint_from_redirect(location: str, request_url: str, base_url: str = "") -> str | None:
    if not location:
        return None
    try:
        from urllib.parse import urlparse, urlunparse
        from urllib.parse import urljoin

        resolved = urljoin(request_url, location)
        parsed = urlparse(resolved)
        if not base_url:
            return f"{parsed.path}{('?' + parsed.query) if parsed.query else ''}"
        base_parsed = urlparse(base_url if "://" in base_url else f"http://x{base_url}")
        if parsed.netloc and base_parsed.netloc and parsed.netloc != base_parsed.netloc:
            return f"{parsed.path}{('?' + parsed.query) if parsed.query else ''}"
        base_path = (base_parsed.path or "").rstrip("/")
        path = parsed.path or ""
        if base_path and path.startswith(base_path):
            remainder = path[len(base_path) :]
            path = remainder or path
        return f"{path}{('?' + parsed.query) if parsed.query else ''}"
    except Exception:
        return location if location.startswith("/") else None


def test_next_dev_attractions_redirect_not_root():
    request_url = "http://127.0.0.1:3055/api/v1/attractions/"
    location = "/api/v1/attractions"
    assert resolve_endpoint_from_redirect(location, request_url) == "/api/v1/attractions"
