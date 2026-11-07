"""Origin migration does not trust arbitrary Host headers or break old installers."""

import pytest
from schulpilot.config import settings
from schulpilot.releases import download_url
from starlette.requests import Request


def request(host, scheme="https"):
    return Request({"type": "http", "method": "GET", "scheme": scheme,
        "path": "/api/app-release", "headers": [(b"host", host.encode())], "query_string": b""})


def test_downloads_keep_old_installers_on_their_fixed_origin():
    previous = settings.public_url, settings.public_url_aliases, settings.android_download_filename
    try:
        object.__setattr__(settings, "public_url", "https://new.example")
        object.__setattr__(settings, "public_url_aliases", "https://old.example")
        object.__setattr__(settings, "android_download_filename", "schuleschlau-android.apk")
        digest = "a" * 64
        assert download_url(request("new.example"), digest) == "https://new.example/downloads/schuleschlau-android.apk?v=" + "a" * 16
        assert download_url(request("old.example"), digest) == "https://old.example/downloads/schulpilot-android.apk?v=" + "a" * 16
        assert download_url(request("attacker.invalid"), digest) == "https://new.example/downloads/schuleschlau-android.apk?v=" + "a" * 16
        assert download_url(request("new.example", "http"), digest).startswith("https://new.example/")
        object.__setattr__(settings, "android_download_filename", "../invalid.apk")
        with pytest.raises(ValueError):
            download_url(request("new.example"), digest)
    finally:
        for key, value in zip(("public_url", "public_url_aliases", "android_download_filename"), previous, strict=True):
            object.__setattr__(settings, key, value)
