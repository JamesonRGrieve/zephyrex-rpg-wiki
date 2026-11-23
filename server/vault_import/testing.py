# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test support for the importers: a setting of the test's own to import into, made as an
instance's operator makes one (POST /v1/setting), so no test depends on which settings are seeded."""

from vault_import.api import Api, ApiError


def setting_of(api: Api, slug: str, name: str = "") -> str:
    """The slug of a setting the caller can use: theirs already, else made with this slug, else (the
    slug taken by someone else) made with the next free one."""
    for row in api.list("setting"):
        if row.get("slug") == slug:
            return slug
    try:
        return str(api.create("setting", name=name or slug.replace("-", " ").title(), slug=slug)["slug"])
    except ApiError as error:
        if error.status != 409:
            raise
        return str(api.create("setting", name=name or slug.replace("-", " ").title())["slug"])
