#!/usr/bin/env python3
"""Path C: upload an Open Mirroring landing-zone folder to Fabric, wait until it is applied,
then reframe the Direct Lake model once.

    parquet_tables.py --layout open-mirroring  ->  <landing-zone folder>
    onelake_upload.py <folder> --workspace-id W --item-id M [--semantic-model D]

WHAT IT DOES, IN ORDER
----------------------
1. Finds the new files. `<folder>.upload.json`, beside the folder (never inside it), records
   per target (workspace/item) the last file number uploaded for each table. A table's files
   above that number are new. A table new to the target is uploaded from file 1, with its
   `_metadata.json` FIRST (the landing zone needs it before data; `keyColumns` cannot change
   once set, so it is never re-sent to a table the target already has). The state is written
   after every table, so a failed run resumes where it stopped.
   A table with files an earlier run uploaded and never saw applied is waited on FIRST, and gets nothing more
   until they are confirmed (Open Mirroring applies in order, so a late apply of the earlier file could
   otherwise be counted as the new file's). The sync time each table is compared with is taken per upload.
   If Fabric never confirms it (the sync time does not move), the table's error says what to check in
   Fabric; once the person has checked, `--confirm-applied <table>` clears it from the record.
2. Uploads through OneLake's DFS API (create, append, flush) with a bearer token, each file under a
   temporary name in its table folder (`_uploading_<name>`), then a rename into the final name (DFS
   `x-ms-rename-source`), so a failed write never leaves a file under a name the mirror reads. Measured
   2026-10-16: the three calls against `onelake.dfs.fabric.microsoft.com/<workspace>/<item>/Files/LandingZone/<table>/...`;
   the rename, and an overwrite by rename, measured 2026-11-17.
3. Polls the mirrored database's table status until every uploaded table has synced after the
   upload, or the timeout passes. A table is reported per table: applied yes or no.
4. Only if EVERY uploaded table applied, and a semantic model was named: reframes it ONCE
   (Power BI REST refresh on a Direct Lake model reloads its Delta table references), so
   the model never shows a mix of two refreshes. A table that failed or timed out means no reframe. The
   refresh is followed by its own id. A reframe that is owed (tables applied, reframe failed or held back)
   is recorded in the upload record under `reframe_owed` and retried by the next run.
5. Prints one JSON result; exit code 0 only when `ok` is true.

ENDPOINTS (what was measured and what was only documented)
-----------------------------------------------------------
- OneLake DFS PUT `?resource=file`, PATCH `?action=append&position=N`, PATCH
  `?action=flush&position=N`: MEASURED (2026-10-16), token resource `https://storage.azure.com/`.
- POST `https://api.fabric.microsoft.com/v1/workspaces/{ws}/mirroredDatabases/{item}/
  getTablesMirroringStatus` (Fabric REST, "Mirroring - Get Tables Mirroring Status"): MEASURED
  (2026-11-13 and 2026-11-16, four refreshes); token resource `https://api.fabric.microsoft.com`.
  `lastSyncDateTime` moves once a table's new file is applied, except for a file with no rows,
  which Fabric never marks (so the writer no longer writes one on a later run).
- POST `https://api.powerbi.com/v1.0/myorg/groups/{ws}/datasets/{model}/refreshes` (Power BI REST,
  "Datasets - Refresh Dataset In Group"): MEASURED on a Direct Lake on OneLake model (2026-11-13 and
  2026-11-16, about 13 s); token resource `https://analysis.windows.net/powerbi/api`. The 202 carries
  `Location` (`.../refreshes/<id>`, on a regional host) and `x-ms-request-id`, holding the same id; the id
  is read from them. GET `.../refreshes/<id>` ("Datasets - Get Refresh Execution Details In Group") is
  polled: 202 while it runs, 200 once completed or failed. Both measured 2026-11-17 on a Direct Lake on
  OneLake model (202 with status Unknown and extendedStatus NotStarted three times, then 200 Completed,
  about 19 s).
Measured apply waits were 177 s to 226 s for a 40-table refresh on a trial capacity. With the
model's automatic updates off, the model kept the previous refresh until this tool's single
reframe (2026-11-16).

SIGN-IN
-------
The token comes from the Azure CLI (`az account get-access-token --resource ...`), held in
memory only. Whoever signed the Azure CLI in (a person, or a service principal) decides who this
is; this tool does not care and never asks for, prints, logs or stores a secret or a token.
Every message the tool writes is scrubbed of the tokens it holds.

Not measured: a service principal's rights on the workspace. The result says what it saw.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

ONELAKE = "https://onelake.dfs.fabric.microsoft.com"
FABRIC_API = "https://api.fabric.microsoft.com/v1"
POWERBI_API = "https://api.powerbi.com/v1.0/myorg"
RESOURCE_STORAGE = "https://storage.azure.com/"
RESOURCE_FABRIC = "https://api.fabric.microsoft.com"
RESOURCE_POWERBI = "https://analysis.windows.net/powerbi/api"
DFS_VERSION = "2023-11-03"
CHUNK = 4 * 1024 * 1024
STATE_VERSION = 1
_SEQUENCE = re.compile(r"^\d{20}\.parquet$")
#: Table statuses Fabric reports while a table is mirroring normally / when it has failed.
OK_STATUSES = {"replicating", "running"}
FAILED_STATUSES = {"failed"}
#: Reframe statuses (Power BI refresh history).
#: How many times in a row a 429 or 5xx on the refresh poll is waited out before the reframe is given up.
POLL_RETRIES = 3
REFRAME_DONE, REFRAME_FAILED = {"completed"}, {"failed", "disabled", "cancelled", "timedout"}

#: transport(method, url, headers, body) -> (status code, response bytes, response headers). The one place
#: HTTP happens. The headers are a dict with lower-case names; a transport that returns only (status, bytes)
#: is accepted and has no headers.
Transport = Callable[[str, str, dict, bytes], tuple]
#: token_provider(resource) -> bearer token (a string, kept in memory only).
TokenProvider = Callable[[str], str]


class UploadError(Exception):
    pass


# ------------------------------------------------------------------ plumbing


class _StripAuthOnRedirect(urllib.request.HTTPRedirectHandler):
    """Follow a redirect without the bearer token.

    urllib keeps every header, `Authorization` included, when it follows a redirect, so a
    redirect to another path or host would receive the person's token. The redirected request
    is sent without it; a service that needs the token on the new address answers 401, which
    the caller reports.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None:
            for name in list(new.headers):
                if name.lower() == "authorization":
                    del new.headers[name]
            for name in list(new.unredirected_hdrs):
                if name.lower() == "authorization":
                    del new.unredirected_hdrs[name]
        return new


_OPENER = urllib.request.build_opener(_StripAuthOnRedirect)


def urllib_transport(method: str, url: str, headers: dict, body: bytes) -> tuple:
    req = urllib.request.Request(url, data=body if method != "GET" else None, method=method,
                                 headers=headers)
    try:
        with _OPENER.open(req, timeout=120) as resp:
            return resp.status, resp.read(), {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as e:
        return e.code, e.read(), {k.lower(): v for k, v in e.headers.items()}


def az_token(resource: str) -> str:
    """A bearer token from the signed-in Azure CLI, in memory only."""
    az = shutil.which("az")
    if not az:
        raise UploadError("the Azure CLI (az) is not installed or not on PATH; install it and "
                          "run `az login` (a person, or a service principal)")
    p = subprocess.run([az, "account", "get-access-token", "--resource", resource,
                        "--query", "accessToken", "-o", "tsv"],
                       capture_output=True, text=True)
    tok = p.stdout.strip()
    if p.returncode != 0 or not tok:
        # stderr only: stdout may hold a token
        raise UploadError(f"az could not give a token for {resource}: "
                          f"{(p.stderr or 'no output').strip()[:300]}. Run `az login`.")
    return tok


class Client:
    """All HTTP goes through `call`, so a test can fake the transport and the sign-in."""

    def __init__(self, transport: Transport, token_provider: TokenProvider):
        self._transport, self._provider = transport, token_provider
        self._tokens: dict[str, str] = {}

    def scrub(self, text) -> str:
        text = str(text)
        for t in self._tokens.values():
            if t:
                text = text.replace(t, "***")
        return re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer ***", text)

    def token(self, resource: str) -> str:
        if resource not in self._tokens:
            try:
                self._tokens[resource] = self._provider(resource)
            except UploadError:
                raise
            except Exception as e:  # its message is left out: it could carry a token
                raise UploadError(f"sign-in failed for {resource}: {type(e).__name__}") from None
        return self._tokens[resource]

    def call(self, method: str, url: str, resource: str, body: bytes = b"",
             headers: dict | None = None) -> tuple:
        """`(status, data, response headers with lower-case names)`."""
        h = {"Authorization": f"Bearer {self.token(resource)}", "Content-Length": str(len(body))}
        h.update(headers or {})
        try:
            got = self._transport(method, url, h, body)
        except Exception as e:
            raise UploadError(self.scrub(f"{method} {url} failed: {e}")) from None
        status, data = got[0], got[1]
        raw_headers = got[2] if len(got) > 2 and got[2] else {}   # None: no headers
        resp_headers = {str(k).lower(): v for k, v in raw_headers.items()}
        return status, data, resp_headers

    def expect(self, ok: tuple, method: str, url: str, resource: str, body: bytes = b"",
               headers: dict | None = None) -> bytes:
        return self.expect_response(ok, method, url, resource, body, headers)[0]

    def expect_response(self, ok: tuple, method: str, url: str, resource: str, body: bytes = b"",
                        headers: dict | None = None) -> tuple:
        """Like `expect`, but returns `(data, response headers)`."""
        status, data, resp_headers = self.call(method, url, resource, body, headers)
        if status not in ok:
            # Scrub the whole body before cutting it, so no part of a token can survive the cut.
            body = self.scrub(data.decode("utf-8", "replace"))[:300]
            raise UploadError(self.scrub(f"{method} {url} returned {status}: {body}"))
        return data, resp_headers


def _empty_files(files: list[Path]) -> bool:
    """True when every file holds zero rows (read from the Parquet footer). Fabric's Open Mirroring never
    moves a table's lastSyncDateTime for an empty file. Without pyarrow, or for a file it cannot read,
    False: the table is then waited on as before."""
    try:
        import pyarrow.parquet as pq
        return bool(files) and all(pq.ParquetFile(f).metadata.num_rows == 0 for f in files)
    except Exception:
        return False


# -------------------------------------------------------------------- state


def state_path(folder) -> Path:
    f = Path(folder)
    return f.with_name(f.name + ".upload.json")


def _load_state(sp: Path) -> dict:
    if not sp.exists():
        return {"version": STATE_VERSION, "targets": {}}
    try:
        st = json.loads(sp.read_text(encoding="utf-8"))
        assert st["version"] == STATE_VERSION and isinstance(st["targets"], dict)
        return st
    except (ValueError, KeyError, TypeError, AssertionError):
        raise UploadError(f"{sp} is not an upload record this tool wrote; delete it to upload "
                          f"every file again") from None


def _save_state(sp: Path, st: dict) -> None:
    tmp = sp.with_name("." + sp.name + ".tmp")
    tmp.write_text(json.dumps(st), encoding="utf-8")
    replace_file(tmp, sp)


def replace_file(src: Path, dst: Path) -> None:
    """`os.replace`, retried a few times: on Windows a virus scanner or indexer that holds the file for a
    moment makes it fail with PermissionError, and the next try succeeds. Shared with parquet_tables.py."""
    for attempt in range(6):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.05 * (attempt + 1))


def scan(folder: Path) -> dict[str, list[Path]]:
    """`{table: [numbered files, ascending]}` for every table folder that has a `_metadata.json`."""
    if not folder.is_dir():
        raise UploadError(f"{folder} is not a folder")
    out = {}
    for d in sorted(p for p in folder.iterdir() if p.is_dir() and not p.name.startswith(".")):
        if not (d / "_metadata.json").is_file():
            continue
        out[d.name] = sorted(p for p in d.iterdir() if _SEQUENCE.match(p.name))
    if not out:
        raise UploadError(f"{folder} holds no table folder with a _metadata.json; write it with "
                          f"parquet_tables.py --layout open-mirroring")
    return out


# ------------------------------------------------------------------- upload


def _dfs_url(ws: str, item: str, path: str, query: str) -> str:
    # The workspace and item ids are one path segment each, so `/`, `..` and `?` in one cannot reach
    # another path; the path below them keeps its `/` separators.
    url = f"{ONELAKE}/{_q(ws)}/{_q(item)}/{urllib.parse.quote(path)}"
    return f"{url}?{query}" if query else url


#: A file is written under this prefix, in its own table folder, and renamed to its final name once it is
#: flushed. Open Mirroring reads a table folder for `_metadata.json` and for data files named with 20 digits
#: ("Open Mirroring Landing Zone Requirements and Formats", learn.microsoft.com/fabric/mirroring/
#: open-mirroring-landing-zone-format, content updated 2026-02-03), and keeps its own bookkeeping under
#: underscore names (`_metadata.json`, `_partnerEvents.json`, `_ProcessedFiles`). The page does not say in so
#: many words that other names are skipped; a name that is neither a data file's name nor a
#: documented service name is the best available reading. Measured 2026-11-17 on a mirrored database: a
#: file with this prefix left in a table folder for 3 minutes (real files apply in 177 to 226 s) was not
#: consumed or deleted, and the table stayed Replicating.
TEMP_PREFIX = "_uploading_"


def _temp_path(path: str) -> str:
    head, _, name = path.rpartition("/")
    return f"{head}/{TEMP_PREFIX}{name}" if head else TEMP_PREFIX + name


def put_file(cl: Client, ws: str, item: str, path: str, data: bytes) -> None:
    """Write one file in OneLake so that a failure never leaves a file under its final name: create,
    append (chunked) and flush it under a temporary name beside it, then rename it (DFS Path - Create with
    `x-ms-rename-source`). A failed write removes the temporary file, best effort; a rerun overwrites it."""
    hdr = {"x-ms-version": DFS_VERSION}
    tmp = _temp_path(path)
    try:
        cl.expect((200, 201), "PUT", _dfs_url(ws, item, tmp, "resource=file"), RESOURCE_STORAGE,
                  headers=hdr)
        pos = 0
        while pos < len(data):
            chunk = data[pos:pos + CHUNK]
            cl.expect((200, 202), "PATCH", _dfs_url(ws, item, tmp, f"action=append&position={pos}"),
                      RESOURCE_STORAGE, chunk, hdr)
            pos += len(chunk)
        cl.expect((200,), "PATCH", _dfs_url(ws, item, tmp, f"action=flush&position={len(data)}"),
                  RESOURCE_STORAGE, headers=hdr)
        # The rename source is "/<file system>/<path>" (OneLake: workspace, then item), URL-encoded.
        source = "/" + _q(ws) + "/" + _q(item) + "/" + urllib.parse.quote(tmp)
        cl.expect((200, 201), "PUT", _dfs_url(ws, item, path, ""), RESOURCE_STORAGE,
                  headers={**hdr, "x-ms-rename-source": source})
    except UploadError:
        try:
            cl.call("DELETE", _dfs_url(ws, item, tmp, ""), RESOURCE_STORAGE, headers=hdr)
        except UploadError:
            pass
        raise


# ------------------------------------------------------------------- status


def check_id(label: str, value) -> str:
    """`value` as an id, or `UploadError`. An id made only of dots (`.`, `..` and longer) would be a path
    step in the URL, and a server may decode even an encoded one into `..`, so it is refused, as is an
    empty id."""
    text = str(value or "").strip()
    if not text or set(text) == {"."}:
        raise UploadError(f"{label} {value!r} is not an id: it is empty or made only of dots")
    return str(value)


def _q(value: str) -> str:
    """One id as one URL path segment: `/`, `..` and `?` in it cannot reach another path, and an id made
    only of dots is refused (`check_id`)."""
    return urllib.parse.quote(check_id("id", value), safe="")


def table_status(cl: Client, ws: str, item: str) -> dict[str, dict]:
    """`{table: {"status", "last_sync"}}` from getTablesMirroringStatus."""
    out, token = {}, None
    while True:
        url = f"{FABRIC_API}/workspaces/{_q(ws)}/mirroredDatabases/{_q(item)}/getTablesMirroringStatus"
        if token:
            url += "?continuationToken=" + urllib.parse.quote(token)
        body = json.loads(cl.expect((200,), "POST", url, RESOURCE_FABRIC, b"{}",
                                    {"Content-Type": "application/json"}) or b"{}")
        for e in body.get("data", []):
            m = e.get("metrics") or {}
            out[e.get("sourceTableName")] = {"status": str(e.get("status", "")),
                                             "last_sync": m.get("lastSyncDateTime")}
        token = body.get("continuationToken")
        if not token:
            return out


def _applied(now: dict | None, before: dict | None) -> bool:
    """Applied: reported with an OK status, and synced after the baseline taken before upload
    (no baseline: any sync time at all). Compared as the service's own strings, so no clock
    of ours is involved."""
    if not now or now["status"].lower() not in OK_STATUSES or not now["last_sync"]:
        return False
    return before is None or not before["last_sync"] or now["last_sync"] > before["last_sync"]


# ------------------------------------------------------------------ reframe


_UUID = re.compile(r"^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")


def _refresh_id(headers: dict) -> str | None:
    """The id of the refresh the POST started. Power BI REST, "Datasets - Refresh Dataset In Group": the 202
    carries `Location` (`.../refreshes/<id>`) and `x-ms-request-id`, which held the same id when measured
    2026-11-17. The `Location` is read first."""
    loc = str(headers.get("location") or "").split("?")[0].rstrip("/")
    last = loc.rpartition("/")[2]
    if loc and _UUID.match(last):
        return last
    rid = str(headers.get("x-ms-request-id") or headers.get("requestid") or "").strip()
    return rid if _UUID.match(rid) else None


def reframe(cl: Client, ws: str, model: str, *, timeout: float, interval: float,
            sleep: Callable, clock: Callable) -> dict:
    """Start one refresh and poll THAT refresh (Power BI REST, "Datasets - Get Refresh Execution Details In
    Group": 202 while it runs, 200 once it completed or failed). The newest entry of the refresh history is
    never read: it could be an older refresh's."""
    url = f"{POWERBI_API}/groups/{_q(ws)}/datasets/{_q(model)}/refreshes"
    t0 = clock()
    res = {"requested": True, "status": "unknown", "seconds": None, "error": None, "refresh_id": None}
    try:
        _, headers = cl.expect_response((200, 202), "POST", url, RESOURCE_POWERBI,
                                        json.dumps({"type": "full"}).encode(),
                                        {"Content-Type": "application/json"})
        rid = _refresh_id(headers)
        if not rid:
            raise UploadError("Power BI accepted the refresh but returned no refresh id (Location or "
                              "x-ms-request-id header), so its result cannot be followed")
        res["refresh_id"] = rid
        busy = 0
        while True:
            status, data, _ = cl.call("GET", f"{url}/{urllib.parse.quote(rid, safe='')}", RESOURCE_POWERBI)
            st = ""
            if status == 429 or status >= 500:
                # Throttled or a service hiccup: wait a little and ask again, a few times. The refresh itself
                # is running; a poll that never gets through leaves the reframe owed for the next run.
                busy += 1
                if busy > POLL_RETRIES:
                    raise UploadError(cl.scrub(f"GET refresh {rid} returned {status} {busy} times in a row"))
                sleep(min(interval, 2.0 ** busy))
                continue
            busy = 0
            if status in (200, 202):
                detail = json.loads(data or b"{}")
                st = str(detail.get("status", ""))
                ext = str(detail.get("extendedStatus", ""))
                if st.lower() not in REFRAME_DONE | REFRAME_FAILED and ext.lower() in REFRAME_FAILED:
                    st = ext  # status stays "Unknown" for a refresh that timed out
            elif status != 404:  # 404: the new refresh is not visible yet
                # Scrubbed before it is cut, so no part of a token can survive the cut (as expect_response).
                body = cl.scrub(data.decode("utf-8", "replace"))[:300]
                raise UploadError(cl.scrub(f"GET refresh {rid} returned {status}: {body}"))
            if st.lower() in REFRAME_DONE | REFRAME_FAILED:
                res["status"] = st
                break
            if clock() - t0 >= timeout:
                res["status"], res["error"] = st or "unknown", "timed out waiting for the reframe"
                break
            sleep(interval)
    except UploadError as e:
        res["error"] = str(e)
        res["status"] = "error"
    res["seconds"] = round(clock() - t0, 1)
    return res


# --------------------------------------------------------------------- main


def _blank() -> dict:
    return {"uploaded": [], "metadata_uploaded": False, "applied": False, "status": None,
            "seconds_to_apply": None, "error": None}


def _wait_applied(cl: Client, ws: str, item: str, started: dict, pending: dict, result: dict, *,
                  timeout: float, interval: float, sleep: Callable, clock: Callable) -> bool:
    """Poll the mirrored database until every table in `started` (`{table: clock time its files went up, or
    when the wait began}`) is applied, failed or out of time. An applied table leaves `pending`. Returns True
    when any table failed or timed out."""
    failed = False
    waiting = {n for n in started if not result["tables"][n]["error"]}
    # Each table is compared with the sync time recorded when ITS files went up (`pending[n]["baseline"]`).
    before_of = {n: ({"last_sync": pending[n]["baseline"]} if pending[n]["baseline"] else None)
                 for n in waiting}
    # A table whose only new files hold zero rows (and is not new to the target: Fabric made the table
    # from the first file) will never show a later sync time. It is not waited on once the rest applied.
    empty_only = {n for n in waiting if pending[n]["empty"]}
    deadline = clock() + timeout
    while waiting:
        try:
            now = table_status(cl, ws, item)
        except UploadError as e:
            now = {}
            result["status_error"] = str(e)
        for n in sorted(waiting):
            result["tables"][n]["status"] = (now.get(n) or {}).get("status")
            if (now.get(n) or {}).get("status", "").lower() in FAILED_STATUSES:
                result["tables"][n]["error"] = "Fabric reports the table as failed"
                waiting.discard(n)
                failed = True
            elif _applied(now.get(n), before_of[n]):
                result["tables"][n]["applied"] = True
                pending.pop(n, None)
                result["tables"][n]["seconds_to_apply"] = round(clock() - started[n], 1)
                waiting.discard(n)
        if not waiting:
            break
        if waiting <= empty_only:
            for n in sorted(waiting):
                result["tables"][n]["applied"] = True
                result["tables"][n]["applied_assumed"] = True
                result["tables"][n]["seconds_to_apply"] = None
            for n in waiting:
                pending.pop(n, None)
            result["empty_files_assumed_applied"] = sorted(
                set(result.get("empty_files_assumed_applied", [])) | waiting)
            result["note"] = ("tables whose only new file holds zero rows were treated as applied: "
                              "Fabric does not move a table's sync time for an empty file")
            waiting = set()
            break
        if clock() >= deadline:
            for n in waiting:
                result["tables"][n]["error"] = f"not applied within {timeout:g} s"
            failed = True
            break
        sleep(interval)
    return failed


def _unconfirmed(name: str, last_file: int, record: Path) -> str:
    """What a table blocked by an unconfirmed earlier upload reports: what to check, and how to clear it."""
    return (f"an earlier upload of this table (its files up to {last_file:020d}.parquet) is not confirmed "
            f"applied, so nothing more is uploaded to it. Check the table in Fabric: open the mirrored "
            f"database, choose Monitor replication, and see that the table's last completed time is after "
            f"that upload and its row count includes those files. Once it has applied, run again with "
            f"--confirm-applied \"{name}\", which clears the table from \"pending\" in {record}. If "
            f"Fabric shows an error for the table, fix that first")


def run(folder, workspace_id: str, item_id: str, *, semantic_model: str | None = None,
        transport: Transport = urllib_transport, token_provider: TokenProvider = az_token,
        timeout: float = 300.0, interval: float = 5.0,
        sleep: Callable = time.sleep, clock: Callable = time.monotonic,
        confirm_applied=()) -> dict:
    """Upload, wait, reframe. Returns the result dict; `ok` is the verdict.

    `confirm_applied` names tables whose earlier upload the person has checked in Fabric and found applied:
    they are cleared from the record's `pending` before anything else happens, so they take new files
    again, and the model is reframed for them. A name that is not pending is refused before anything is
    sent."""
    # Every id is checked before anything is read, asked for or sent.
    check_id("workspace_id", workspace_id)
    check_id("item_id", item_id)
    if semantic_model is not None:
        check_id("semantic_model", semantic_model)
    cl = Client(transport, token_provider)
    t_start = clock()
    folder = Path(folder)
    found = scan(folder)
    sp = state_path(folder)
    state = _load_state(sp)
    key = f"{workspace_id}/{item_id}"
    done = state["targets"].setdefault(key, {})
    # Files uploaded but not yet confirmed applied, per table: the sync time seen before THIS table's most
    # recent upload went up, and whether they are all empty.
    pending = state.setdefault("pending", {}).setdefault(key, {})
    # Whether the model still has to be reframed for tables that applied (a reframe that failed, or that a
    # failed table held back, is retried by the next run).
    owed = state.setdefault("reframe_owed", {})
    confirmed = []
    for name in confirm_applied:
        if name not in pending:
            raise UploadError(f"--confirm-applied {name!r}: {sp} holds no unconfirmed upload of that table "
                              f"for this mirrored database; unconfirmed: {sorted(pending) or 'none'}")
    for name in confirm_applied:
        if pending.pop(name, None) is not None:
            confirmed.append(name)
            owed[key] = True      # it applied, so the model still has to show it
    if confirmed:
        _save_state(sp, state)
    pending_at_start = {n: dict(v) for n, v in pending.items()}

    result = {"ok": False, "target": {"workspace_id": workspace_id, "item_id": item_id},
              "tables": {}, "reframe": None, "seconds": None}
    if confirmed:
        result["confirmed_applied"] = confirmed
    for n in pending_at_start:
        result["tables"][n] = _blank()
    failed = False

    # 1. Files an earlier run uploaded and never saw applied come first. Open Mirroring applies a table's files
    #    in order, so while an earlier file is unconfirmed, a sync time that moves cannot be told from the
    #    new file's: nothing more goes up to that table until the earlier upload is confirmed.
    if pending_at_start:
        start = clock()
        failed = _wait_applied(cl, workspace_id, item_id, {n: start for n in pending_at_start},
                               pending, result, timeout=timeout, interval=interval, sleep=sleep,
                               clock=clock)
        _save_state(sp, state)
        for n in pending_at_start:
            if n in pending:   # still unconfirmed: say what to check and how to clear it
                t_n = result["tables"][n]
                hint = _unconfirmed(n, done.get(n, 0), sp)
                t_n["error"] = f"{t_n['error']}; {hint}" if t_n["error"] else hint

    plan = {}
    for name, files in found.items():
        last = done.get(name, 0)
        new = [f for f in files if int(f.stem) > last]
        result["tables"].setdefault(name, _blank())
        if new and name in pending:   # its error, set above, says how to recover
            result["tables"][name]["not_uploaded"] = [f.name for f in new]
            failed = True
        elif new:
            plan[name] = (last == 0, new)

    try:
        baseline = table_status(cl, workspace_id, item_id) if plan else {}
    except UploadError as e:
        baseline = {}
        result["status_baseline_error"] = str(e)

    uploaded_at = {}
    try:
        for name, (first, new) in plan.items():  # metadata first, for every new table
            if first:
                put_file(cl, workspace_id, item_id, f"Files/LandingZone/{name}/_metadata.json",
                         (found[name][0].parent / "_metadata.json").read_bytes())
                result["tables"][name]["metadata_uploaded"] = True
        for name, (first, new) in plan.items():
            t = result["tables"][name]
            try:
                for f in new:
                    put_file(cl, workspace_id, item_id, f"Files/LandingZone/{name}/{f.name}",
                             f.read_bytes())
                    t["uploaded"].append(f.name)
                    done[name] = int(f.stem)
                    if name not in pending:  # the baseline is this table's, from before this upload
                        pending[name] = {"baseline": (baseline.get(name) or {}).get("last_sync"),
                                         "empty": None}
                    _save_state(sp, state)
                new_empty = (not first) and _empty_files(new)
                prev = pending[name]["empty"]
                pending[name]["empty"] = new_empty if prev is None else (prev and new_empty)
                _save_state(sp, state)
                uploaded_at[name] = clock()
            except UploadError as e:
                t["error"] = str(e)
                failed = True
            except OSError as e:
                t["error"] = f"could not read {f}: {e}"
                failed = True
    except UploadError as e:  # a _metadata.json upload failed: nothing of that table landed
        for name in plan:
            if not result["tables"][name]["uploaded"] and not result["tables"][name]["error"]:
                result["tables"][name]["error"] = str(e)
        failed = True

    if _wait_applied(cl, workspace_id, item_id, uploaded_at, pending, result, timeout=timeout,
                     interval=interval, sleep=sleep, clock=clock):
        failed = True

    if any(t["applied"] for t in result["tables"].values()):
        owed[key] = True
    _save_state(sp, state)
    nothing_new = not plan and not pending_at_start
    if semantic_model and not failed and owed.get(key):
        result["reframe"] = reframe(cl, workspace_id, semantic_model, timeout=timeout,
                                    interval=interval, sleep=sleep, clock=clock)
        if result["reframe"]["status"].lower() in REFRAME_DONE:
            owed.pop(key, None)  # a failed reframe stays recorded, and the next run retries it
        else:
            failed = True
        result["reframe_retry"] = nothing_new
        _save_state(sp, state)
    elif semantic_model:
        result["reframe"] = {"requested": False, "status": "skipped",
                             "reason": ("nothing new to upload" if nothing_new and not failed
                                        else "a table did not land, so the model was left as it was")}
    result["nothing_new"] = nothing_new
    result["ok"] = not failed
    result["seconds"] = round(clock() - t_start, 1)
    return result


def main(argv=None, **run_kw) -> int:
    ap = argparse.ArgumentParser(
        description="Upload an Open Mirroring landing-zone folder to a Fabric mirrored database, "
                    "wait until Fabric has applied it, then reframe the Direct Lake model once.")
    ap.add_argument("folder", help="the folder parquet_tables.py --layout open-mirroring wrote")
    ap.add_argument("--workspace-id", required=True)
    ap.add_argument("--item-id", required=True, help="the mirrored database's id")
    ap.add_argument("--semantic-model", default=None,
                    help="the Direct Lake semantic model's id; reframed once after every table landed")
    ap.add_argument("--timeout", type=float, default=300.0,
                    help="seconds to wait for Fabric to apply the tables, and again for the reframe")
    ap.add_argument("--poll-interval", type=float, default=5.0)
    ap.add_argument("--result-file", default=None, help="also write the JSON result here")
    ap.add_argument("--confirm-applied", action="append", default=[], metavar="TABLE",
                    help="a table whose earlier upload you checked in Fabric (Monitor replication) and "
                         "found applied: clears it from the upload record's pending list so it takes new "
                         "files again. Repeat for more tables")
    a = ap.parse_args(argv)
    try:
        res = run(a.folder, a.workspace_id, a.item_id, semantic_model=a.semantic_model,
                  timeout=a.timeout, interval=a.poll_interval, confirm_applied=a.confirm_applied,
                  **run_kw)
    except UploadError as e:
        res = {"ok": False, "error": str(e)}
    text = json.dumps(res, indent=2)
    if a.result_file:
        Path(a.result_file).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
