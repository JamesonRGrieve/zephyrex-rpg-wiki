# SPDX-License-Identifier: AGPL-3.0-or-later
"""A session report's body, held to the cases the lite edition is held to (contract/report-body-cases.json)."""

import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import REPOSITORY_ROOT  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Report import report_entry  # type: ignore[import-not-found]

CASES: dict[str, Any] = json.loads((REPOSITORY_ROOT / "contract" / "report-body-cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["cases"], ids=[case["name"] for case in CASES["cases"]])
def test_report_entry(case: dict[str, Any]) -> None:
    assert report_entry(case["body"], case["mentions"]) == case["entry"]
