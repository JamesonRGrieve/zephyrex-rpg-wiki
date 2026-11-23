# SPDX-License-Identifier: AGPL-3.0-or-later
"""Setting slugs against contract/slug-cases.json, which the lite edition's slug.test.ts reads too."""

import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import SEED_SETTINGS, SLUG_CASES_PATH  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Records import checked_slug, free_slug, slugify  # type: ignore[import-not-found]

CASES: dict[str, Any] = json.loads(SLUG_CASES_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["derived"], ids=lambda case: case["name"])
def test_a_slug_comes_from_the_name(case: dict[str, str]) -> None:
    assert slugify(case["name"]) == case["slug"]


@pytest.mark.parametrize("case", CASES["deduplicated"], ids=lambda case: ",".join(case["taken"]) or "free")
def test_a_taken_slug_takes_the_next_number(case: dict[str, Any]) -> None:
    assert free_slug(case["slug"], set(case["taken"])) == case["free"]


def test_a_numbered_slug_stays_within_the_length() -> None:
    long = slugify("x" * 100)
    assert len(free_slug(long, {long})) == len(long)


@pytest.mark.parametrize("slug", CASES["invalid"])
def test_a_slug_the_contract_refuses(slug: str) -> None:
    with pytest.raises(ValueError):
        checked_slug(slug)


def test_the_seeded_slugs_are_valid_and_distinct() -> None:
    slugs = [checked_slug(one["slug"]) for one in SEED_SETTINGS]
    assert len(set(slugs)) == len(slugs) == 1  # Reality alone (operator, 2026-11-23: no IP in public code)
