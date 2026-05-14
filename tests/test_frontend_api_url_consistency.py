"""
Guards against hard-coded backend URLs in the Next.js app.
All browser fetches should use API_BASE_URL from frontend/src/lib/api.ts.
"""
from pathlib import Path


def test_no_hardcoded_localhost_8000_outside_api_module():
    root = Path(__file__).resolve().parents[1] / "frontend" / "src"
    needle = "http://localhost:8000"
    offenders = []
    for path in root.rglob("*.tsx"):
        text = path.read_text(encoding="utf-8")
        if needle in text:
            offenders.append(path.relative_to(root))
    for path in root.rglob("*.ts"):
        if path.name == "api.ts":
            continue
        text = path.read_text(encoding="utf-8")
        if needle in text:
            offenders.append(path.relative_to(root))
    assert not offenders, (
        "Use API_BASE_URL from @/lib/api instead of hard-coded localhost:8000 in:\n"
        + "\n".join(str(p) for p in offenders)
    )
