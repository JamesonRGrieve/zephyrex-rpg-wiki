# SPDX-License-Identifier: AGPL-3.0-or-later
"""Code the wiki's extensions share: the contract (contract/wiki.json), the entry rule (Plate →
plain text), and the checks every record takes (a name, a kind from the contract, a parent that
never closes a cycle). A plain package, not an extension: it has no manifest and is never
loaded, so sharing it adds no dependency between extensions (OBJECT_PLAN §3 lists those)."""
