# SPDX-License-Identifier: AGPL-3.0-or-later
"""python -m st_import [--card FILE …] [--world-info FILE …] (--campaign NAME | --setting-wide)
       --setting SLUG [--dry-run] (--base-url URL [--lite] | --app module:factory --owner USER_ID)

Character cards (V2/V3, PNG or JSON) become persons with an AI voice and their picture; World Info
(and a card's own lorebook) becomes lore journals with their activation keys and fields. The ways
in are vault_import's (vault_import/connect.py).
"""

import argparse
import sys
from pathlib import Path

from st_import.importer import StImporter
from st_import.sillytavern import read_card, read_world_info
from vault_import.connect import connection


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="st_import", description="Import SillyTavern cards and World Info into the wiki")
    parser.add_argument("--card", type=Path, action="append", default=[], help="A character card (.png or .json); repeat for more")
    parser.add_argument("--world-info", type=Path, action="append", default=[], help="A World Info file (.json); repeat for more")
    parser.add_argument("--campaign", help="The campaign they belong to (made in --setting when missing)")
    parser.add_argument("--setting-wide", action="store_true", help="The setting's canon instead of one campaign's")
    parser.add_argument("--setting", help="The setting's slug (it must exist: POST /v1/setting)")
    parser.add_argument("--dry-run", action="store_true", help="Read and report; write nothing")
    parser.add_argument("--base-url", help="Over HTTP: the wiki's address")
    parser.add_argument("--lite", action="store_true", help="Over HTTP to a lite edition: the API is under /api")
    parser.add_argument("--app", help="In process: the server app's factory, module:function (rpg_ai_app:create)")
    parser.add_argument("--owner", help="In process: the user id whose records these become")
    args = parser.parse_args(argv)
    if not args.card and not args.world_info:
        parser.error("give at least one --card or --world-info")
    if (args.app is None) == (args.base_url is None):
        parser.error("give --base-url (over HTTP) or --app with --owner (in process)")
    if args.app is not None and not args.owner:
        parser.error("--app needs --owner")
    if bool(args.campaign) == args.setting_wide:
        parser.error("give --campaign or --setting-wide")
    cards = [read_card(path) for path in args.card]
    entries = [entry for path in args.world_info for entry in read_world_info(path)]
    with connection(args.base_url, args.lite, args.app, args.owner) as api:
        importer = StImporter(api, args.campaign, args.setting, setting_wide=args.setting_wide, dry_run=args.dry_run)
        report = importer.import_all(cards, entries)
    print(report.text(args.dry_run))
    return 1 if report.refused else 0


if __name__ == "__main__":
    sys.exit(main())
