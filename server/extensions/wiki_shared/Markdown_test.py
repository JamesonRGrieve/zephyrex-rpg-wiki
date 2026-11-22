# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import REPOSITORY_ROOT  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Markdown import markdown_entry  # type: ignore[import-not-found]

CASES: dict[str, Any] = json.loads((REPOSITORY_ROOT / "contract" / "markdown-entry-cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["entries"], ids=lambda case: case["name"])
def test_reads_markdown_as_an_entry(case: dict[str, Any]) -> None:
    assert markdown_entry(case["markdown"]) == case["entry"]
