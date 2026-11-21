# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lore blocks against contract/lore-cases.json (the client package's lore.test.ts too)."""

import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import LORE_CASES_PATH  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Lore import lore  # type: ignore[import-not-found]

CASES: dict[str, Any] = json.loads(LORE_CASES_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["valid"], ids=lambda case: case["name"])
def test_a_lore_block(case: dict[str, Any]) -> None:
    assert lore(case["value"]) == case["checked"]


@pytest.mark.parametrize("case", CASES["invalid"], ids=lambda case: case["name"])
def test_a_lore_block_refused(case: dict[str, Any]) -> None:
    with pytest.raises(ValueError) as refused:
        lore(case["value"])
    assert str(refused.value) == case["message"]
