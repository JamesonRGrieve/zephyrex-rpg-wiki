# SPDX-License-Identifier: AGPL-3.0-or-later
"""python -m system_adopt --app module:factory --setting SLUG [--setting SLUG …] [--apply]

Makes the first setting system level in place (SYSTEM's: every account reads it and plays copies
of its scenarios, only the server changes it): the setting, its canon and pregens, its scenarios and
everything in them, ids unchanged, so its owner's playthroughs keep their links. Each further
setting (another account's copy of the same content) is merged into it: its records matched by
kind and name, references to them (its owner's playthroughs among them) turned to the system copy,
the matched duplicates removed, anything unmatched moved in. A dry run unless --apply. In process
only (the authors of rows are the server's to set): run it from the app's server directory, with
the app's environment. Afterwards run rebuild_world_keys and rebuild_lore_chunks.
"""

import argparse
import sys

from vault_import.connect import connection


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="system_adopt", description="Make a setting's out-of-the-box content system level")
    parser.add_argument("--app", required=True, help="The server app's factory, module:function (rpg_ai_app:create)")
    parser.add_argument("--setting", action="append", required=True, help="A setting's slug; the first becomes system level, each further one merges into it")
    parser.add_argument("--apply", action="store_true", help="Write it (default: a dry run)")
    parser.add_argument("--merge-copies", action="store_true", help="First merge the accounts' copies inside the first setting (each author's scenarios and records) into one")
    parser.add_argument("--keep-owner", help="With --merge-copies: the author whose copy is kept (default: the author of the earliest scenario)")
    args = parser.parse_args(argv)
    with connection(None, False, args.app, None, system=True) as api:
        from zephyrex.extensions.rpg_core.SystemAdopt import adopt_settings  # type: ignore[import-not-found]

        report = adopt_settings(api.model_registry, args.setting, dry_run=not args.apply, merge_copies=args.merge_copies, keep_owner=args.keep_owner)  # type: ignore[attr-defined]
    print(("DRY RUN: nothing written\n" if not args.apply else "") + "\n".join(one.line() for one in report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
