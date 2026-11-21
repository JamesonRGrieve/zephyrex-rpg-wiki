# SPDX-License-Identifier: AGPL-3.0-or-later
"""A campaign's documents (contract/document-cases.json): the full plain text of each record's entry,
journals first, then the contract's document_kinds order, by name within a kind; a record with no
text is left out. Parity's data bank reads them."""

from typing import Any

from zephyrex.extensions.wiki_shared.Contract import DOCUMENT_KINDS  # type: ignore[import-not-found]


def ordered_documents(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Each record with text, as a document {id, kind, name, text, ...}, in the documents' order."""
    kept = [{**record, "text": str(record.get("text") or "").strip()} for record in records]
    kept = [record for record in kept if record["text"]]
    rank = {kind: index for index, kind in enumerate(DOCUMENT_KINDS)}
    return sorted(kept, key=lambda record: (rank.get(record["kind"], len(rank)), str(record["name"]).lower(), record["id"]))
