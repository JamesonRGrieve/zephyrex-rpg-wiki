# SPDX-License-Identifier: AGPL-3.0-or-later
"""A vault's notes: each Markdown file with frontmatter naming an ``entity_type``."""

import glob
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

ENTITY_TYPES = ("person", "location", "faction", "item", "journal", "hook")
# Obsidian links: [[Name]], [[Name|shown]], [[Name#heading]], [[Name#heading|shown]].
LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n?", re.S)
SKIPPED_DIRS = {"Templates"}
# A record's picture sits beside its note under the same name (Characters/Ilsa Marrow.jpg).
PICTURE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


@dataclass
class Note:
    path: str
    meta: dict[str, Any]
    body: str
    problems: list[str] = field(default_factory=list)
    # The same-name image beside the note, if there is one (its full path).
    picture: Optional[Path] = None

    @property
    def entity_type(self) -> str:
        return str(self.meta.get("entity_type") or "")

    @property
    def name(self) -> str:
        return str(self.meta.get("name") or Path(self.path).stem).strip()


def link_name(value: Any) -> Optional[str]:
    """The note a frontmatter value links to: ``"[[Holst]]"`` or a bare ``Holst``; none when empty."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    found = LINK.search(text)
    return found.group(1).strip() if found else text


def read_note(root: Path, path: Path) -> Optional[Note]:
    """The note at ``path``, or none when it has no frontmatter or no entity_type."""
    text = path.read_text(encoding="utf-8")
    found = FRONTMATTER.match(text)
    if not found:
        return None
    try:
        meta = yaml.safe_load(found.group(1)) or {}
    except yaml.YAMLError as error:
        note = Note(str(path.relative_to(root)), {}, "")
        note.problems.append(f"frontmatter is not YAML: {error}")
        return note
    if not isinstance(meta, dict) or not meta.get("entity_type"):
        return None
    return Note(str(path.relative_to(root)), meta, text[found.end():], picture=picture_beside(path))


def picture_beside(path: Path) -> Optional[Path]:
    """The image beside a note with its name (jpg, jpeg, png or webp, any letter case), or none."""
    for sibling in sorted(path.parent.glob(f"{glob.escape(path.stem)}.*")):
        if sibling.stem == path.stem and sibling.suffix.lower() in PICTURE_TYPES and sibling.is_file():
            return sibling
    return None


def read_vault(root: Path) -> list[Note]:
    """Every note with an entity_type, in path order; Templates/ and hidden folders left out."""
    notes: list[Note] = []
    for path in sorted(root.rglob("*.md")):
        parts = path.relative_to(root).parts
        if any(part.startswith(".") or part in SKIPPED_DIRS for part in parts[:-1]):
            continue
        note = read_note(root, path)
        if note is not None:
            notes.append(note)
    return notes
