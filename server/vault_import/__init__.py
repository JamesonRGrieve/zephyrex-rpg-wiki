# SPDX-License-Identifier: AGPL-3.0-or-later
"""An Obsidian vault into the wiki, through the wiki's own REST API (either edition): each note
with an ``entity_type`` becomes a record in its campaign (or its setting's canon), its Markdown the
record's entry, its frontmatter the record's links, tags, statuses, dispositions and properties.
Re-running it updates what changed and adds nothing twice. ``python -m vault_import --help``."""
