# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import DOCUMENT_CASES_PATH  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Documents import ordered_documents  # type: ignore[import-not-found]

CASES: dict[str, Any] = json.loads(DOCUMENT_CASES_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["cases"], ids=lambda case: case["name"])
def test_orders_a_campaigns_documents(case: dict[str, Any]) -> None:
    documents = ordered_documents(case["records"])
    assert [one["id"] for one in documents] == case["ids"]
    if "texts" in case:
        assert [one["text"] for one in documents] == case["texts"]
