# SPDX-License-Identifier: AGPL-3.0-or-later
"""A Foundry VTT system's compendium packs, read from their source files (packs/_source/<pack>/**,
YAML or JSON, one document each), with each document's compendium UUID."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

import yaml


@dataclass
class Document:
    """One compendium document: its pack, its Foundry type and its data."""

    pack: str
    document_type: str  # Actor, Item, JournalEntry, RollTable, …
    data: dict[str, Any]
    path: str
    uuid: str

    @property
    def name(self) -> str:
        return str(self.data.get("name") or "").strip()

    @property
    def type(self) -> str:
        """The system's own type (npc, spell, weapon, …); a journal has none."""
        return str(self.data.get("type") or "")

    @property
    def system(self) -> dict[str, Any]:
        value = self.data.get("system")
        return value if isinstance(value, dict) else {}


def _load(path: Path) -> Optional[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    loaded = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
    return loaded if isinstance(loaded, dict) else None


def read_packs(system_dir: Path, packs: Optional[Iterable[str]] = None) -> list[Document]:
    """The documents of ``packs`` (all the system's packs when none), in pack then path order.
    Folders are left out. The source tree is ``packs/_source/<pack>`` beside system.json."""
    manifest = json.loads((system_dir / "system.json").read_text(encoding="utf-8"))
    system_id = str(manifest["id"])
    declared = {str(pack["name"]): str(pack["type"]) for pack in manifest.get("packs", [])}
    wanted = list(packs) if packs is not None else sorted(declared)
    documents: list[Document] = []
    for pack in wanted:
        if pack not in declared:
            raise ValueError(f"{system_id} has no pack {pack!r}")
        root = system_dir / "packs" / "_source" / pack
        for path in sorted(root.rglob("*")):
            if path.suffix not in (".yml", ".yaml", ".json") or not path.is_file():
                continue
            data = _load(path)
            if data is None or str(data.get("_key", "")).startswith("!folders") or not data.get("_id"):
                continue
            document_type = declared[pack]
            uuid = f"Compendium.{system_id}.{pack}.{document_type}.{data['_id']}"
            documents.append(Document(pack, document_type, data, str(path.relative_to(system_dir)), uuid))
    return documents
