# SPDX-License-Identifier: AGPL-3.0-or-later
"""A property kit's keys (S4b, W4): what a kit holds, checked and normalised the same way by both
back ends (the lite edition's client/src/lib/properties.ts), held to contract/property-kit-cases.json.

A kit is a list of properties, each ``{key, value_type, default, is_private, ordinal}``, which
applying it adds to a record's own key/values (the framework's record_metadata) where the record
doesn't have the key yet."""

from typing import Any

from zephyrex.extensions.wiki_shared.Contract import LIMITS, PROPERTY_VALUE_TYPES  # type: ignore[import-not-found]

MAX_KEY = LIMITS["property_key_characters"]
MAX_VALUE = LIMITS["property_value_characters"]
MAX_PROPERTIES = LIMITS["properties_per_record"]


class KitError(ValueError):
    """Why a kit's properties are refused, in words for the person who wrote them."""


def _default(value: Any) -> Any:
    """A default as the record's value is kept: text (a number or a switch written as text), or none."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if not isinstance(value, str):
        raise KitError("A default is text, a number or true/false")
    if len(value) > MAX_VALUE:
        raise KitError(f"A default has at most {MAX_VALUE} characters")
    return value


def checked_kit(properties: Any) -> list[dict[str, Any]]:
    """A kit's properties, normalised: each key trimmed and named once, its type from the contract
    (text when not given), its place (its position when not given), private only when said."""
    if not isinstance(properties, list):
        raise KitError("A kit's properties are a list")
    if len(properties) > MAX_PROPERTIES:
        raise KitError(f"A kit has at most {MAX_PROPERTIES} properties")
    seen: set[str] = set()
    checked: list[dict[str, Any]] = []
    for place, item in enumerate(properties):
        if not isinstance(item, dict):
            raise KitError("Each property is an object with a key")
        key = str(item.get("key") or "").strip()
        if not key:
            raise KitError("Each property has a key")
        if len(key) > MAX_KEY:
            raise KitError(f"A key has at most {MAX_KEY} characters")
        if key in seen:
            raise KitError(f"The key {key!r} is in the kit twice")
        seen.add(key)
        value_type = item.get("value_type") or "text"
        if value_type not in PROPERTY_VALUE_TYPES:
            raise KitError(f"A value type is one of: {', '.join(PROPERTY_VALUE_TYPES)}")
        ordinal = item.get("ordinal", place)
        if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0:
            raise KitError("A property's place is a whole number of zero or more")
        is_private = item.get("is_private", False)
        if not isinstance(is_private, bool):
            raise KitError("is_private is true or false")
        checked.append(
            {"key": key, "value_type": value_type, "default": _default(item.get("default")), "is_private": is_private, "ordinal": ordinal}
        )
    return checked
