# SPDX-License-Identifier: AGPL-3.0-or-later
"""An entry's plain-text copy, held to the cases the lite edition is held to
(contract/entry-text-cases.json; client/src/lib/entry.test.ts)."""

import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import ENTRY_TEXT_CASES_PATH, LIMITS  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Entry import parse, plain_text  # type: ignore[import-not-found]

CASES: dict[str, Any] = json.loads(ENTRY_TEXT_CASES_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["cases"], ids=[case["name"] for case in CASES["cases"]])
def test_plain_text(case: dict[str, Any]) -> None:
    assert plain_text(case["entry"]) == case["text"]


@pytest.mark.parametrize("case", CASES["refusals"], ids=[case["name"] for case in CASES["refusals"]])
def test_refusal(case: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        plain_text(case["entry"])


def test_parse_takes_the_value_or_its_json_text() -> None:
    value = CASES["cases"][1]["entry"]
    assert parse(value) == parse(json.dumps(value))
    assert parse(value)[1] == "A port city."


def test_an_entry_past_the_size_limit_is_refused() -> None:
    big = [{"type": "p", "children": [{"text": "x" * (LIMITS["entry_bytes"] + 1)}]}]
    with pytest.raises(ValueError):
        parse(big)


def test_an_entry_nested_past_the_depth_limit_is_refused() -> None:
    node: dict[str, Any] = {"text": "deep"}
    for _ in range(LIMITS["entry_depth"] + 1):
        node = {"type": "div", "children": [node]}
    with pytest.raises(ValueError):
        plain_text([node])
