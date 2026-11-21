# SPDX-License-Identifier: AGPL-3.0-or-later
"""The ids GET /v1/world_entity?ids= names (contract/entity-ids-cases.json)."""

from zephyrex.extensions.wiki_shared.Contract import LIMITS  # type: ignore[import-not-found]

MAX_IDS: int = LIMITS["world_entity_ids"]


class EntityIdsError(ValueError):
    pass


def entity_ids(values: list[str]) -> list[str]:
    """Each id trimmed, blanks dropped, repeats kept once in first order; none, or more than the
    contract's limit, is refused."""
    ids = list(dict.fromkeys(value.strip() for value in values if value.strip()))
    if not ids:
        raise EntityIdsError("no ids")
    if len(ids) > MAX_IDS:
        raise EntityIdsError(f"at most {MAX_IDS} ids")
    return ids
