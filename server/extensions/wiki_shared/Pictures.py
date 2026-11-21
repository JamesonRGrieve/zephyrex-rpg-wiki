# SPDX-License-Identifier: AGPL-3.0-or-later
"""A record's picture by link (contract/picture-url-cases.json): an https address, trimmed; an empty
one is none. It's shown as it is, with no referrer (fandom and other wikis refuse hotlinks that send
one), and it's the record's picture before an uploaded one."""

from typing import Any, Optional
from urllib.parse import urlsplit

from zephyrex.extensions.wiki_shared.Contract import LIMITS  # type: ignore[import-not-found]

MAX_PICTURE_URL: int = LIMITS["picture_url_characters"]


def picture_url(value: Any) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("A picture link is an https address")
    text = value.strip()
    if not text:
        return None
    if len(text) > MAX_PICTURE_URL:
        raise ValueError(f"A picture link has at most {MAX_PICTURE_URL} characters")
    parts = urlsplit(text)
    if parts.scheme != "https" or not parts.hostname:
        raise ValueError("A picture link is an https address")
    return text
