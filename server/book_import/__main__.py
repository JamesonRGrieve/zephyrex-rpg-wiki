# SPDX-License-Identifier: AGPL-3.0-or-later
"""python -m book_import <books/<line> folders or .md files> --setting <slug> --app module:create --owner ID [--dry-run] [--unscoped] [--system slug]

Each book's line (its header's line:) names its game system (LINE_SYSTEMS, or --system for every
book given); a book whose system this server doesn't have is skipped and reported, since its pages
would reach every campaign of the setting; --unscoped imports it with no system anyway. Sheets,
handouts and screens are left out (--exclude). In process only: the operator's instance alone
holds book text."""

import argparse
import re
import sys
from pathlib import Path

from book_import.reader import read_book
from vault_import.connect import in_process

LINE_SYSTEMS = {
    "dh2": "dark-heresy-2e",
    "dh1": "dark-heresy",
    "rt": "rogue-trader",
    "dw": "deathwatch",
    "bc": "black-crusade",
    "ow": "only-war",
    "im": "imperium-maledictum",
}
EXCLUDE = r"(sheet|folio|handout|screen|form-fillable)"


def books_in(paths: list[Path], exclude: str) -> list[Path]:
    found = sorted({one for path in paths for one in ([path] if path.is_file() else path.rglob("*.md"))})
    return [one for one in found if not re.search(exclude, one.stem, re.IGNORECASE)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="book_import", description="Transcribed books into the lore index")
    parser.add_argument("paths", type=Path, nargs="+", help="Book .md files, or folders of them (books/dh2, …)")
    parser.add_argument("--setting", required=True, help="The setting's slug (it must exist: POST /v1/setting)")
    parser.add_argument("--system", help="The game system's slug for every book given (else each book's line)")
    parser.add_argument("--unscoped", action="store_true", help="Import a book whose system this server lacks, with none")
    parser.add_argument("--exclude", default=EXCLUDE, help=f"Books whose file name matches are left out (default {EXCLUDE!r})")
    parser.add_argument("--dry-run", action="store_true", help="Read and count; write nothing")
    parser.add_argument("--app", required=True, help="The server app's factory, module:function")
    parser.add_argument("--owner", required=True, help="The owner's user id")
    args = parser.parse_args(argv)
    from zephyrex.extensions.AbstractExtensionProvider import loaded_ability

    lines: list[str] = []
    failed = False
    with in_process(args.app, args.owner) as api:
        registry, owner = api.model_registry, api.owner_id  # type: ignore[attr-defined]
        settings = [row for row in api.list("setting") if row.get("slug") == args.setting]
        if not settings:
            print(f"no setting {args.setting!r}")
            return 1
        setting_id = str(settings[0]["id"])
        systems = {str(row["slug"]): str(row["id"]) for row in api.list("game_system")} if "rpg_systems" in api.extensions() else {}
        load = loaded_ability(registry, "rpg_core", "import_book")
        if load is None:
            print("this server's rpg_core has no import_book (wiki 2026-11-22 or later)")
            return 1
        for path in books_in(args.paths, args.exclude):
            book = read_book(path)
            slug = args.system or LINE_SYSTEMS.get(book.line or "")
            system_id = systems.get(slug or "")
            if system_id is None and not args.unscoped:
                lines.append(f"skipped {book.slug}: no game system {slug!r} on this server (--unscoped imports it for every campaign of the setting)")
                continue
            try:
                made = load(registry, owner, setting_id, system_id, book.slug, book.title, book.pages, args.dry_run)["passages"]
            except Exception as error:  # noqa: BLE001 - reported per book; the rest go on
                failed = True
                lines.append(f"FAILED {book.slug}: {error}")
                continue
            lines.append(f"{'would import' if args.dry_run else 'imported'} {book.slug}: {len(book.pages)} pages, {made} passages, system {slug or 'none'}")
    print("\n".join(lines))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
