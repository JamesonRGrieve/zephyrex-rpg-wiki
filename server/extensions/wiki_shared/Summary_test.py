# SPDX-License-Identifier: AGPL-3.0-or-later
"""A record's summary, held to the cases the lite edition and rpg-ai are held to
(contract/summary-cases.json)."""

import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import REPOSITORY_ROOT  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Summary import SUMMARY_CHARACTERS, summary  # type: ignore[import-not-found]

CASES: dict[str, Any] = json.loads((REPOSITORY_ROOT / "contract" / "summary-cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["cases"], ids=[case["name"] for case in CASES["cases"]])
def test_summary(case: dict[str, Any]) -> None:
    assert summary(case["text"], CASES["limit"]) == case["summary"]


def test_a_summary_never_exceeds_the_contract_limit() -> None:
    assert len(summary("word " * 500)) <= SUMMARY_CHARACTERS
