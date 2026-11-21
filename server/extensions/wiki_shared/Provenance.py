# SPDX-License-Identifier: AGPL-3.0-or-later
"""A campaign's provenance (contract/provenance-cases.json): homebrew, official (as published) or
adapted (from a published one), and its source (title, publisher, product or page). The operator
parses official scenarios in for personal use, so every campaign says where it came from."""

from typing import Any, Optional

from zephyrex.extensions.wiki_shared.Contract import LIMITS, PROVENANCES  # type: ignore[import-not-found]

HOMEBREW = PROVENANCES[0]
MAX_SOURCE: int = LIMITS["source_characters"]


def checked_provenance(value: Any) -> str:
    if value not in PROVENANCES:
        raise ValueError(f"provenance is one of {', '.join(PROVENANCES)}")
    return str(value)


def checked_source(value: Any) -> Optional[str]:
    """A source trimmed; an empty one is none."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("A source is text")
    text = value.strip()
    if len(text) > MAX_SOURCE:
        raise ValueError(f"A source has at most {MAX_SOURCE} characters")
    return text or None


def provenance(value: dict[str, Any]) -> dict[str, Any]:
    """A campaign's provenance and source together: what isn't given is homebrew with no source."""
    kind = checked_provenance(value.get("provenance") or HOMEBREW)
    source = checked_source(value.get("source"))
    if kind == HOMEBREW and source is not None:
        raise ValueError("Homebrew has no source")
    return {"provenance": kind, "source": source}
