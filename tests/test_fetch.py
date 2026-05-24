from unittest.mock import MagicMock, patch

import pytest

from readpack.fetch import FetchError, fetch_html


def test_fetch_rejects_siteground_captcha():
    html = '<html><head><meta http-equiv="refresh" content="0;/.well-known/sgcaptcha/?r=x"></head></html>'
    resp = MagicMock()
    resp.read.return_value = html.encode()
    resp.headers.get_content_charset.return_value = "utf-8"
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=resp), pytest.raises(FetchError):
        fetch_html("https://example.com")
