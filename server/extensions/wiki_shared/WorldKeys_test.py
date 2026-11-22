# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import REPOSITORY_ROOT  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.WorldKeys import normalised, record_keys, text_grams  # type: ignore[import-not-found]

CASES: dict[str, Any] = json.loads((REPOSITORY_ROOT / "contract" / "world-keys-cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["normalised"], ids=lambda case: case["name"])
def test_normalises(case: dict[str, Any]) -> None:
    assert normalised(case["value"]) == case["normalised"]


@pytest.mark.parametrize("case", CASES["keys"], ids=lambda case: case["name"])
def test_a_records_keys(case: dict[str, Any]) -> None:
    record = case["record"]
    assert record_keys(record["name"], record["aliases"], record["keywords"], record["always_active"]) == case["keys"]


@pytest.mark.parametrize("case", CASES["matches"], ids=lambda case: case["name"])
def test_a_text_matches_its_keys(case: dict[str, Any]) -> None:
    grams = text_grams(case["text"])
    assert sorted(key for key in case["keys"] if key in grams) == case["matched"]
