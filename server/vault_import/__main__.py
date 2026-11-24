# SPDX-License-Identifier: AGPL-3.0-or-later
"""python -m vault_import <vault> [<vault> …] --setting SLUG [--dry-run]
       (--base-url URL [--lite]  |  --app module:factory --owner USER_ID)

Over HTTP, the wiki's token is read from WIKI_TOKEN (a SaaS server); a lite edition needs none.
In process (--app), it boots the server app in this process, as VTT's import does, with the app's
environment loaded: run it from the app's server directory. It signs in as --owner for an hour (a
session the auth_session extension records and can revoke) and goes through the app's own routes,
so every rule holds as over HTTP. Several vaults import in the order given: a setting's canon
before the campaigns that link to it.
"""

import argparse
import sys
from pathlib import Path

from vault_import.connect import connection
from vault_import.notes import read_vault


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vault_import", description="Import Obsidian vaults into the wiki")
    parser.add_argument("vaults", type=Path, nargs="+", help="Vault folders, imported in this order")
    parser.add_argument("--setting", help="The setting's slug for the vaults' campaigns (it must exist: POST /v1/setting)")
    parser.add_argument("--dry-run", action="store_true", help="Read and report; write nothing")
    parser.add_argument("--base-url", help="Over HTTP: the wiki's address, e.g. http://localhost:2000")
    parser.add_argument("--lite", action="store_true", help="Over HTTP to a lite edition: the API is under /api")
    parser.add_argument("--app", help="In process: the server app's factory, module:function (rpg_ai_app:create)")
    parser.add_argument("--owner", help="In process: the user id whose records these become")
    parser.add_argument(
        "--default-campaign",
        help="The campaign of a note that names none and isn't setting_wide (a campaign vault's own root notes)",
    )
    args = parser.parse_args(argv)
    if (args.app is None) == (args.base_url is None):
        parser.error("give --base-url (over HTTP) or --app with --owner (in process)")
    if args.app is not None and not args.owner:
        parser.error("--app needs --owner")
    connect = connection(args.base_url, args.lite, args.app, args.owner)
    notes = [note for vault in args.vaults for note in read_vault(vault)]
    if args.default_campaign:
        for note in notes:
            if not note.meta.get("campaign") and note.meta.get("setting_wide") is not True:
                note.meta["campaign"] = args.default_campaign
    with connect as api:
        # The importer imports the wiki's shared code (zephyrex.extensions.wiki_shared), which exists
        # only once the connection has made the app (in process) or put the checkout's on the path.
        from vault_import.importer import Importer

        report = Importer(api, setting_slug=args.setting, dry_run=args.dry_run).run(notes)
    print(report.text(args.dry_run))
    return 1 if report.refused or report.unplayable else 0


if __name__ == "__main__":
    sys.exit(main())
