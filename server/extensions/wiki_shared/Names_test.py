# SPDX-License-Identifier: AGPL-3.0-or-later
"""Aliases, keywords and voices against contract/name-list-cases.json (the lite edition's names.test.ts too)."""

import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import NAME_LIST_CASES_PATH  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Names import names, voice  # type: ignore[import-not-found]

CASES: dict[str, Any] = json.loads(NAME_LIST_CASES_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["lists"], ids=lambda case: case["name"])
def test_a_list_of_names(case: dict[str, Any]) -> None:
    assert names(case["value"]) == case["checked"]


@pytest.mark.parametrize("case", CASES["invalid_lists"], ids=lambda case: case["name"])
def test_a_list_refused(case: dict[str, Any]) -> None:
    with pytest.raises(ValueError) as refused:
        names(case["value"])
    assert str(refused.value) == case["message"]


@pytest.mark.parametrize("case", CASES["voices"], ids=lambda case: case["name"])
def test_a_voice(case: dict[str, Any]) -> None:
    assert voice(case["value"]) == case["checked"]


@pytest.mark.parametrize("case", CASES["invalid_voices"], ids=lambda case: case["name"])
def test_a_voice_refused(case: dict[str, Any]) -> None:
    with pytest.raises(ValueError) as refused:
        voice(case["value"])
    assert str(refused.value) == case["message"]


def test_a_list_holds_at_most_fifty() -> None:
    with pytest.raises(ValueError, match="at most 50"):
        names([f"n{index}" for index in range(51)])
