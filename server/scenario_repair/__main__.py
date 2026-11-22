# SPDX-License-Identifier: AGPL-3.0-or-later
"""python -m scenario_repair [--apply] [--origins origins.json] [--seated ids.txt] (--base-url URL | --app module:create --owner ID)

Without --apply it is a dry run: every scenario and playthrough reported, nothing written.
origins.json maps a campaign's id or name to "imported" or "stereotypical" (a vault-imported one is
known by its framing's vault path); ids.txt lists persons seated in play (they become PCs)."""

import argparse
import json
import sys
from pathlib import Path

from vault_import.connect import connection


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scenario_repair", description="Mend the owner's scenarios and playthroughs")
    parser.add_argument("--apply", action="store_true", help="Write the repairs (default: a dry run)")
    parser.add_argument("--origins", type=Path, help="JSON: campaign id or name → imported | stereotypical")
    parser.add_argument("--seated", type=Path, help="Person ids seated in play, one per line (they become PCs)")
    parser.add_argument("--base-url", help="Over HTTP: the wiki's address (WIKI_TOKEN is the owner's token)")
    parser.add_argument("--lite", action="store_true", help="Over HTTP to a lite edition")
    parser.add_argument("--app", help="In process: the server app's factory, module:function")
    parser.add_argument("--owner", help="In process: the owner's user id")
    args = parser.parse_args(argv)
    origins = json.loads(args.origins.read_text(encoding="utf-8")) if args.origins else {}
    seated = {line.strip() for line in args.seated.read_text(encoding="utf-8").splitlines() if line.strip()} if args.seated else set()
    with connection(args.base_url, args.lite, args.app, args.owner) as api:
        # The rules import the wiki's shared code (zephyrex.extensions.wiki_shared), which exists
        # only once the connection has made the app (in process) or put the checkout's on the path.
        from scenario_repair.repair import repair

        report = repair(api, dry_run=not args.apply, origins=origins, seated=seated)
    print(("DRY RUN: nothing written\n" if not args.apply else "") + "\n".join(mended.line() for mended in report))
    return 1 if any(mended.problems_after for mended in report) else 0


if __name__ == "__main__":
    sys.exit(main())
