# SPDX-License-Identifier: AGPL-3.0-or-later
"""The two ways an importer reaches the wiki (vault_import, st_import): over HTTP, or in process.

Over HTTP, the wiki's token is read from WIKI_TOKEN (a SaaS server); a lite edition needs none. In
process, the server app is booted in this process, as VTT's import does, with the app's
environment loaded: run it from the app's server directory. It signs in as the owner for an hour
(a session the auth_session extension records and can revoke) and goes through the app's own
routes, so every rule holds as over HTTP.
"""

import importlib
import os
import sys
from contextlib import contextmanager
from typing import Any, ContextManager, Iterator, Optional

from vault_import.api import Api

SESSION_HOURS = 1


@contextmanager
def over_http(base_url: str, lite: bool) -> Iterator[Api]:
    import httpx

    token = os.environ.get("WIKI_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if lite:
        # The lite edition refuses cross-site writes; a same-origin fetch says so.
        headers["Sec-Fetch-Site"] = "same-origin"
    with httpx.Client(base_url=base_url, timeout=60) as http:
        yield Api(http, headers, prefix="/api" if lite else "")


@contextmanager
def in_process(app_path: str, owner: str) -> Iterator[Api]:
    from fastapi.testclient import TestClient
    from zephyrex.lib.Environment import env
    from zephyrex.logic.BLL_Auth import UserManager

    sys.path.insert(0, os.getcwd())
    module, _, factory = app_path.partition(":")
    app: Any = getattr(importlib.import_module(module), factory or "create")()
    with TestClient(app) as http:
        registry = app.state.model_registry
        user = UserManager(requester_id=env("ROOT_ID"), model_registry=registry).get(id=owner)
        token = UserManager.generate_jwt_token(
            user_id=str(user.id), email=str(user.email), expiration_hours=SESSION_HOURS, model_registry=registry
        )
        api = Api(http, {"Authorization": f"Bearer {token}"})
        # For an importer that calls an ability in process (book_import): the app's registry and owner.
        api.model_registry = registry  # type: ignore[attr-defined]
        api.owner_id = str(user.id)  # type: ignore[attr-defined]
        yield api



def connection(base_url: Optional[str], lite: bool, app: Optional[str], owner: Optional[str]) -> ContextManager[Api]:
    """In process when ``app`` is given (with ``owner``), else over HTTP to ``base_url``."""
    if app is not None:
        if not owner:
            raise ValueError("in process needs the owner's user id")
        return in_process(app, owner)
    if base_url is None:
        raise ValueError("give a base URL (over HTTP) or an app with its owner (in process)")
    return over_http(base_url, lite)
