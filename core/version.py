# -*- coding: utf-8 -*-
"""
Version information for JaliMaker
Controlled via GitHub tags - fetched at runtime if network available.
"""

APP_NAME = "JaliMaker"
COMPANY  = "Ajitesh Kannojia"
VERSION  = "3.3.2"
BUILD_DATE = "2025-01-01"
LICENSE  = "MIT"
GITHUB_REPO = "ajitesh1020/JaliMaker"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
HOMEPAGE = f"https://github.com/{GITHUB_REPO}"


def get_version_string() -> str:
    return f"v{VERSION}"


def get_full_version_string() -> str:
    return f"{APP_NAME} v{VERSION} | {COMPANY} | {LICENSE} License"


def check_latest_version() -> dict:
    """
    Check GitHub for latest release.
    Returns dict with 'latest', 'current', 'update_available', 'url'.
    Returns None on network failure.
    """
    try:
        import urllib.request
        import json
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={"User-Agent": f"{APP_NAME}/{VERSION}"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        tag = data.get("tag_name", "").lstrip("v")
        url = data.get("html_url", HOMEPAGE)
        return {
            "latest": tag,
            "current": VERSION,
            "update_available": _version_gt(tag, VERSION),
            "url": url,
        }
    except Exception:
        return None


def _version_gt(a: str, b: str) -> bool:
    """Return True if version a > b."""
    try:
        return tuple(int(x) for x in a.split(".")) > tuple(int(x) for x in b.split("."))
    except Exception:
        return False
