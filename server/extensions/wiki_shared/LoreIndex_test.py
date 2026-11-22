# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import REPOSITORY_ROOT  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.LoreIndex import chunk_entry, fuse, in_scope, pack, tokens  # type: ignore[import-not-found]

CASES: dict[str, Any] = json.loads((REPOSITORY_ROOT / "contract" / "lore-index-cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["tokens"], ids=lambda case: case["name"])
def test_counts_tokens(case: dict[str, Any]) -> None:
    assert tokens(case["text"]) == case["tokens"]


@pytest.mark.parametrize("case", CASES["chunks"], ids=lambda case: case["name"])
def test_cuts_passages(case: dict[str, Any]) -> None:
    assert chunk_entry(case["record"], case["entry"], case["max_tokens"], case["min_tokens"]) == case["passages"]


@pytest.mark.parametrize("case", CASES["scopes"], ids=lambda case: case["name"])
def test_keeps_to_the_campaigns_scope(case: dict[str, Any]) -> None:
    assert [chunk["id"] for chunk in case["chunks"] if in_scope(case["campaign"], chunk)] == case["visible"]


@pytest.mark.parametrize("case", CASES["fusions"], ids=lambda case: case["name"])
def test_fuses_rankings(case: dict[str, Any]) -> None:
    assert [one for one, _score in fuse(case["rankings"], case["exact"])] == case["order"]


@pytest.mark.parametrize("case", CASES["packs"], ids=lambda case: case["name"])
def test_packs_to_a_budget(case: dict[str, Any]) -> None:
    assert [chunk["id"] for chunk in pack(case["chunks"], case["budget"])] == case["packed"]
