# SPDX-License-Identifier: AGPL-3.0-or-later
"""The wiki's REST API as the importer uses it: the framework's envelopes ({resource: {...}}), lists
paged by offset and limit, and updates guarded by the record's ETag. It wraps any client with
``request(method, url, json=, params=, headers=)``: httpx for a running wiki, the server's
TestClient in tests."""

from __future__ import annotations

from typing import Any, Optional, Protocol

PAGE = 100


class HttpClient(Protocol):
    def request(self, method: str, url: str, **kwargs: Any) -> Any: ...


# The most records one plural create takes (server-framework's MAX_BATCH_SIZE).
BATCH = 100


class ApiError(Exception):
    """The wiki refused a request: its status and its reason."""

    def __init__(self, status: int, method: str, path: str, detail: Any) -> None:
        super().__init__(f"{method} {path}: {status} {detail}")
        self.status = status
        self.detail = detail


def _detail(response: Any) -> Any:
    try:
        body = response.json()
    except ValueError:
        return response.text
    return body.get("detail", body) if isinstance(body, dict) else body


def etag_of(row: dict[str, Any]) -> str:
    """A row's version as the server tags it (its updated_at, else created_at, quoted), read from the
    row itself so a change needs no GET first."""
    return f'"{row.get("updated_at") or row.get("created_at") or ""}"'


class Api:
    def __init__(self, http: HttpClient, headers: Optional[dict[str, str]] = None, prefix: str = "") -> None:
        self.http = http
        self.headers = headers or {}
        self._plurals: dict[str, str] = {}
        # "/api" for a lite edition served by Next, "" for the server.
        self.prefix = prefix

    def _call(self, method: str, path: str, ok: tuple[int, ...], **kwargs: Any) -> Any:
        headers = {**self.headers, **kwargs.pop("headers", {})}
        response = self.http.request(method, f"{self.prefix}{path}", headers=headers, **kwargs)
        if response.status_code not in ok:
            raise ApiError(response.status_code, method, path, _detail(response))
        return response

    def list(self, resource: str, **filters: Any) -> list[dict[str, Any]]:
        """Every record of ``resource`` matching ``filters``, page by page."""
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            body = self._call("GET", f"/v1/{resource}", (200,), params={**filters, "offset": offset, "limit": PAGE}).json()
            page = next((value for value in body.values() if isinstance(value, list)), []) if isinstance(body, dict) else []
            rows.extend(page)
            if len(page) < PAGE:
                return rows
            offset += PAGE

    def get(self, resource: str, record_id: str) -> tuple[dict[str, Any], str]:
        response = self._call("GET", f"/v1/{resource}/{record_id}", (200,))
        record: dict[str, Any] = response.json()[resource]
        return record, response.headers.get("etag", "")

    def create(self, resource: str, **fields: Any) -> dict[str, Any]:
        record: dict[str, Any] = self._call("POST", f"/v1/{resource}", (200, 201), json={resource: fields}).json()[resource]
        return record

    def plural(self, resource: str) -> str:
        """The name a resource's list answers under (its plural, as the framework names it)."""
        if resource not in self._plurals:
            try:
                body = self._call("GET", f"/v1/{resource}", (200,), params={"limit": 1}).json()
                self._plurals[resource] = next(key for key, value in body.items() if isinstance(value, list))
            except ApiError:
                # A resource with no list (record_metadata): its plural as the framework names its routes'
                # plural key, the same function the create route reads; over HTTP from a machine without
                # the framework, its regular plural.
                try:
                    from zephyrex.lib.Environment import plural_noun  # type: ignore[import-not-found]
                except ImportError:
                    self._plurals[resource] = f"{resource}s"
                else:
                    self._plurals[resource] = str(plural_noun(resource))
        return self._plurals[resource]

    def create_many(self, resource: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Many records in one plural create (each runs the resource's hooks), in the order given."""
        if not rows:
            return []
        plural = self.plural(resource)
        made: list[dict[str, Any]] = []
        # A plural create takes at most BATCH records (the framework's MAX_BATCH_SIZE).
        for start in range(0, len(rows), BATCH):
            made.extend(self._call("POST", f"/v1/{resource}", (200, 201), json={plural: rows[start : start + BATCH]}).json()[plural])
        return made

    def create_batch(self, resource: str, rows: list[dict[str, Any]]) -> list[Optional[str]]:
        """Many records in plural creates of at most BATCH each, every row attempted: per row None when
        it was created, else why it was refused (a 207's per-row error, or the whole chunk's refusal)."""
        outcomes: list[Optional[str]] = []
        if not rows:
            return outcomes
        plural = self.plural(resource)
        for start in range(0, len(rows), BATCH):
            chunk = rows[start : start + BATCH]
            response = self.http.request(
                "POST", f"{self.prefix}/v1/{resource}", headers=dict(self.headers), json={plural: chunk}
            )
            if response.status_code in (200, 201):
                outcomes.extend([None] * len(chunk))
            elif response.status_code == 207:
                by_index = {int(one["index"]): one for one in response.json().get("results", [])}
                for index in range(len(chunk)):
                    one = by_index.get(index, {})
                    outcomes.append(None if one.get("outcome") == "created" else str(one.get("error") or one))
            else:
                outcomes.extend([str(_detail(response))] * len(chunk))
        return outcomes

    def update_batch(self, resource: str, changes: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[Optional[str]]:
        """Many records changed in plural PUTs of at most BATCH each, every row attempted: each change is
        (the row as last read, its new fields), sent with that row's version as its If-Match. Per change
        None when it was saved, else why it was refused (a 207's per-row error, or the chunk's refusal)."""
        outcomes: list[Optional[str]] = []
        if not changes:
            return outcomes
        plural = self.plural(resource)
        for start in range(0, len(changes), BATCH):
            chunk = changes[start : start + BATCH]
            rows = [{"id": str(row["id"]), "if_match": etag_of(row), **fields} for row, fields in chunk]
            response = self.http.request("PUT", f"{self.prefix}/v1/{resource}", headers=dict(self.headers), json={plural: rows})
            if response.status_code == 200:
                outcomes.extend([None] * len(chunk))
            elif response.status_code == 207:
                by_index = {int(one["index"]): one for one in response.json().get("results", [])}
                for index in range(len(chunk)):
                    one = by_index.get(index, {})
                    outcomes.append(None if one.get("outcome") == "updated" else str(one.get("error") or one))
            else:
                outcomes.extend([str(_detail(response))] * len(chunk))
        return outcomes

    def update(self, resource: str, record_id: str, **fields: Any) -> dict[str, Any]:
        _current, etag = self.get(resource, record_id)
        response = self._call("PUT", f"/v1/{resource}/{record_id}", (200,), json={resource: fields}, headers={"If-Match": etag})
        record: dict[str, Any] = response.json()[resource]
        return record

    def properties(self, kind: str, record_id: str) -> list[dict[str, Any]]:
        body = self._call("GET", "/v1/record_metadata/of", (200,), params={"target_entity_type": kind, "target_entity_id": record_id}).json()
        rows: list[dict[str, Any]] = body["metadata"]
        return rows

    def add_property(self, kind: str, record_id: str, key: str, value: str, value_type: str = "text", is_private: bool = False) -> None:
        body = {"target_entity_type": kind, "target_entity_id": record_id, "key": key, "value": value, "value_type": value_type, "is_private": is_private}
        self._call("POST", "/v1/record_metadata", (200, 201), json={"record_metadata": body})

    def change_property(self, row: dict[str, Any], value: str) -> None:
        self._call("PATCH", f"/v1/record_metadata/{row['id']}", (200,), json={"record_metadata": {"value": value}})

    # ---- files (S2c, the framework's attachments) ----------------------------------------

    def upload(self, name: str, content_type: str, content: bytes) -> dict[str, Any]:
        """A file stored as the caller's asset (its raw bytes, its type and its name)."""
        response = self._call(
            "POST", "/v1/asset/upload", (200, 201), params={"name": name}, content=content, headers={"Content-Type": content_type}
        )
        asset: dict[str, Any] = response.json()["asset"]
        return asset

    def attachments(self, kind: str, record_id: str, role: str) -> list[dict[str, Any]]:
        body = self._call(
            "GET", "/v1/attachment/of", (200,), params={"target_entity_type": kind, "target_entity_id": record_id, "role": role}
        ).json()
        rows: list[dict[str, Any]] = body["attachments"]
        return rows

    def attach(self, asset_id: str, kind: str, record_id: str, role: str) -> None:
        body = {"asset_id": asset_id, "target_entity_type": kind, "target_entity_id": record_id, "role": role}
        self._call("POST", "/v1/attachment", (200, 201), json={"attachment": body})

    def extensions(self) -> set[str]:
        """The extensions the wiki's back end serves (GET /v1/extension)."""
        body = self._call("GET", "/v1/extension", (200,)).json()
        rows = body.get("extensions", []) if isinstance(body, dict) else []
        return {str(row.get("name")) for row in rows if isinstance(row, dict)}
