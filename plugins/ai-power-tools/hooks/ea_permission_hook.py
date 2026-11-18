"""PreToolUse hook: approve reads, ask for writes, on the AI Power Tools meta-tools.

Claude Code matches permission rules on the tool name, and every meta-tool (ea_model,
ea_diagram, ...) holds reads and writes together. This hook looks inside the call: it reads
`operation` (and `allow_writes` for `execute_sql`) from the tool input and answers from
`operations.json`, a list generated from the server's own read/write flags.

  read                          -> allow
  write, profile, disk          -> ask
  sql (execute_sql)             -> allow only when params.allow_writes is false AND the connected
                                   server is 3.6.6 or later (see below), else ask
  anything the list lacks       -> no answer, so Claude Code's normal permission flow decides

It works in Claude Code only. Claude Desktop and VS Code do not run plugin hooks and still
approve per tool.

Claude Code documentation, https://code.claude.com/docs/en/hooks :
  input   JSON on stdin with `tool_name` (an MCP tool is `mcp__<server>__<tool>`) and `tool_input`.
  output  exit 0 and one JSON object on stdout:
          {"hookSpecificOutput": {"hookEventName": "PreToolUse",
           "permissionDecision": "allow" | "ask" | "deny", "permissionDecisionReason": "..."}}
          No output and exit 0 leaves the decision to the normal permission flow.
Plugin hook registration, https://code.claude.com/docs/en/plugins-reference (hooks):
  `hooks/hooks.json` with a top-level "hooks" key; `${CLAUDE_PLUGIN_ROOT}` is the plugin folder.

Which server is connected: a 3.6.6 or later server writes
`%LOCALAPPDATA%/AIPowerTools/ea-server/<pid>.json` when it starts and deletes it when it exits:
`{"version": "...", "pid": n, "parent_pid": n, "started": "..."}`. Older servers write none. The
hook and the servers are children of Claude Code (exec form, no shell; one step further down when
`python` is a launcher that starts the real interpreter as its child, as a Windows virtual
environment's does). In the Claude desktop app, the servers of the app's extensions are the app's
children instead, so when Claude Code's parent is the desktop app (recognized by its full program
path, the Microsoft Store build's package folder) the app's servers count too. A parent named
claude.exe that cannot be confirmed as that app makes the call ask. The hook lists the
processes Claude Code (and that app) started that really are servers (the
program `ea-mcp-server.exe`, or a Python whose command line runs `ea_mcp_server`) and allows
execute_sql with allow_writes false only when there is at least one and every one has a marker of
its own: named after its pid, naming this Claude Code or that app as its parent, written no earlier than the
process started (else a crash left it and the pid was reused), and saying 3.6.6 or later. A server
without one is an older server, so the call asks. A marker for any other process, and any other
file in the folder, is ignored. No server, an unreadable marker, a command line that cannot be read,
an older version or any error: ask. Windows only; elsewhere the call asks.

Standard library only. Any failure to read the input or the list gives no answer.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

LIST_PATH = Path(__file__).resolve().with_name("operations.json")

# The server segment of `mcp__<server>__<tool>` that is this product's server. The server names
# itself "AI-Power-Tools-for-Sparx-EA" (FastMCP name, .mcpb manifest and the sample config). A
# plugin-bundled server is scoped as `plugin_<plugin>_<server>` (Claude Code hooks documentation).
# Any other server gets no answer, even if it has a tool called ea_model.
SERVER_NAME = "AI-Power-Tools-for-Sparx-EA"
SERVER_SEGMENTS = (SERVER_NAME, f"plugin_ai-power-tools_{SERVER_NAME}")


#: The first server version whose execute_sql the hook lets through with allow_writes false.
SQL_READ_MIN_VERSION = (3, 6, 6)
_VERSION = re.compile(r"^\d+(\.\d+)*$")
#: How much later than the marker's `started` (whole seconds, written once the server is up) its process
#: may have started and still be the process that wrote it. Later than that, the pid was reused.
START_TOLERANCE_SECONDS = 5


def _marker_dir():
    base = os.environ.get("LOCALAPPDATA")
    return Path(base) / "AIPowerTools" / "ea-server" if base else None


#: A Python program that may start the real interpreter as its child (a Windows virtual environment's
#: `python.exe`, the `py` launcher), or may itself be the interpreter. Same pattern as the server's.
_PYTHON_IMAGE = re.compile(r"^(?:python|pythonw|py)[0-9.]*w?\.exe$", re.IGNORECASE)
#: The built server's program name.
SERVER_IMAGE = "ea-mcp-server.exe"
#: What a server run from source has on its command line (`python -m ea_mcp_server`).
SERVER_MODULE = "ea_mcp_server"
#: The Claude desktop app's program, by its full path: the Microsoft Store build, in its package folder
#: under `Program Files\WindowsApps` (writable only by Windows itself), with the Store's publisher id for
#: Anthropic, which is the same on every machine. Claude Code's own binary, also named claude.exe, lives
#: elsewhere and does not match. Measured 17 Nov 2026 on one machine:
#: `C:\Program Files\WindowsApps\AnthropicPBC.Claude_<version>_<arch>__fnn82j28hfe8t\app\claude.exe`.
_DESKTOP_APP = re.compile(r"^[A-Za-z]:\\Program Files\\WindowsApps\\AnthropicPBC\.Claude_[^\\_]+_[^\\_]+"
                          r"__fnn82j28hfe8t\\app\\claude\.exe\Z", re.IGNORECASE)   # \Z: no trailing newline
#: A parent with this program name that is not confirmed as the desktop app above makes SQL ask: its
#: servers would not be counted, and this session's calls may go to them.
_CLAUDE_IMAGE = "claude.exe"


def _kernel32():
    import ctypes
    from ctypes import wintypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.restype = wintypes.HANDLE
    k.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    k.CloseHandle.argtypes = (wintypes.HANDLE,)
    k.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
    k.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
    return k


def _processes():
    """`{pid: (parent pid, program name)}` for every process, from one Windows snapshot; None elsewhere or
    when the snapshot cannot be taken."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class Entry(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260)]

    kernel32 = _kernel32()
    kernel32.Process32FirstW.argtypes = (wintypes.HANDLE, ctypes.POINTER(Entry))
    kernel32.Process32NextW.argtypes = (wintypes.HANDLE, ctypes.POINTER(Entry))
    snap = kernel32.CreateToolhelp32Snapshot(0x2, 0)          # TH32CS_SNAPPROCESS
    if not snap or snap == wintypes.HANDLE(-1).value:
        return None
    try:
        out = {}
        entry = Entry()
        entry.dwSize = ctypes.sizeof(Entry)
        ok = kernel32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            out[int(entry.th32ProcessID)] = (int(entry.th32ParentProcessID), entry.szExeFile)
            ok = kernel32.Process32NextW(snap, ctypes.byref(entry))
        return out
    finally:
        kernel32.CloseHandle(snap)


def _command_line(pid: int):
    """Process `pid`'s command line (Windows 8.1 and later, NtQueryInformationProcess), or None when it
    cannot be read."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes
    kernel32 = _kernel32()
    query = ctypes.WinDLL("ntdll").NtQueryInformationProcess
    query.restype = ctypes.c_long
    query.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.ULONG,
                      ctypes.POINTER(wintypes.ULONG))

    class UnicodeString(ctypes.Structure):
        _fields_ = [("Length", wintypes.USHORT), ("MaximumLength", wintypes.USHORT),
                    ("Buffer", ctypes.c_void_p)]

    handle = kernel32.OpenProcess(0x1000, False, pid)         # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        size = wintypes.ULONG(0)
        query(handle, 60, None, 0, ctypes.byref(size))       # ProcessCommandLineInformation
        if not size.value:
            return None
        buf = ctypes.create_string_buffer(size.value)
        if query(handle, 60, buf, size, ctypes.byref(size)) != 0:
            return None
        text = UnicodeString.from_buffer(buf)
        return ctypes.wstring_at(text.Buffer, text.Length // 2) if text.Buffer else None
    finally:
        kernel32.CloseHandle(handle)


def _image_path(pid: int):
    """Process `pid`'s full program path (QueryFullProcessImageNameW), or None when it cannot be read."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes
    kernel32 = _kernel32()
    kernel32.QueryFullProcessImageNameW.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                    ctypes.POINTER(wintypes.DWORD))
    handle = kernel32.OpenProcess(0x1000, False, pid)         # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        size = wintypes.DWORD(32768)
        buf = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return None
        return buf.value
    finally:
        kernel32.CloseHandle(handle)


def _is_desktop_app(pid: int) -> bool:
    """Whether process `pid` is the Claude desktop app, judged by its full program path."""
    return bool(_DESKTOP_APP.match(_image_path(pid) or ""))


def _roots(claude: set, procs: dict):
    """Whose servers count: this hook's Claude Code, and, when Claude Code was started by the Claude desktop
    app, the desktop app too (it runs the servers of the extensions it holds). None, meaning ask, when
    Claude Code's parent is named claude.exe but cannot be confirmed as the desktop app (its path cannot be
    read, or it is another install): its servers could not be counted, and calls may go to them."""
    roots = set(claude)
    for pid in claude:
        own = procs.get(pid)
        if own is None or _PYTHON_IMAGE.match(own[1] or ""):
            continue                     # a Python launcher between Claude Code and the hook
        parent = own[0]
        if parent not in procs or parent in roots:
            continue
        if _is_desktop_app(parent):
            roots.add(parent)
        elif (procs[parent][1] or "").lower() == _CLAUDE_IMAGE:
            return None
    return roots


def _parent_pids(procs=None) -> set:
    """The pid of the Claude Code that ran this hook: the hook's parent, or, when the parent is a Python
    launcher that started the real interpreter as its child, the launcher's parent too."""
    pids = {os.getppid()}
    try:
        procs = procs if procs is not None else (_processes() or {})
        me = procs.get(os.getpid())
        if me and me[0] in procs and _PYTHON_IMAGE.match(procs[me[0]][1] or ""):
            pids.add(procs[me[0]][0])
    except Exception:
        pass
    return pids


def _is_server(pid: int, image: str) -> bool:
    """Whether process `pid` is an AI Power Tools server: the built program, or a Python whose command line
    runs the server module. A command line that cannot be read is not a server's."""
    name = (image or "").lower()
    if name == SERVER_IMAGE:
        return True
    if _PYTHON_IMAGE.match(name):
        line = _command_line(pid)
        return bool(line) and SERVER_MODULE in line
    return False


def _servers_of(claude: set, procs: dict) -> set:
    """The servers this Claude Code started: its children that are servers, and where such a child is a
    Python launcher whose own child is a server, that child instead (one level)."""
    children: dict = {}
    for pid, (parent, image) in procs.items():
        children.setdefault(parent, []).append((pid, image))
    out = set()
    for parent in claude:
        for pid, image in children.get(parent, []):
            if pid == os.getpid() or not _is_server(pid, image):
                continue
            inner = [c for c, img in children.get(pid, []) if _is_server(c, img)]
            out.update(inner or [pid])
    return out


def _process_start(pid: int):
    """When process `pid` started, as an aware UTC datetime, or None when it cannot be read.
    Windows: GetProcessTimes. Linux: /proc. Elsewhere: None, and the start time is not compared."""
    import datetime
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel32 = _kernel32()
        handle = kernel32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return None
        try:
            times = [wintypes.FILETIME() for _ in range(4)]
            if not kernel32.GetProcessTimes(handle, *(ctypes.byref(x) for x in times)):
                return None
            ticks = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime   # 100 ns since 1601
            return (datetime.datetime(1601, 1, 1, tzinfo=datetime.timezone.utc)
                    + datetime.timedelta(microseconds=ticks // 10))
        finally:
            kernel32.CloseHandle(handle)
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
        since_boot = int(stat.rpartition(")")[2].split()[19]) / os.sysconf("SC_CLK_TCK")
        boot = next(int(line.split()[1]) for line in Path("/proc/stat").read_text().splitlines()
                    if line.startswith("btime "))
        return datetime.datetime.fromtimestamp(boot + since_boot, datetime.timezone.utc)
    except (OSError, ValueError, IndexError, StopIteration, AttributeError):
        return None


def _started_after_marker(pid: int, started) -> bool:
    """True when the running process `pid` began after its marker says the server started, beyond the
    tolerance: the server that wrote the marker is gone and its pid was reused. A marker with no readable
    `started`, or one more than the tolerance in the future, raises, so it counts as unreadable; a process
    whose start cannot be read is not compared."""
    import datetime
    if not isinstance(started, str):
        raise ValueError("no started time")
    stamp = datetime.datetime.fromisoformat(started.strip().replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("started time without a zone")
    if stamp > datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            seconds=START_TOLERANCE_SECONDS):
        raise ValueError("started time in the future")
    began = _process_start(pid)
    if began is None:
        return False
    return began > stamp + datetime.timedelta(seconds=START_TOLERANCE_SECONDS)


def _version(text) -> tuple:
    if not isinstance(text, str) or not _VERSION.match(text.strip()):
        raise ValueError("not a version")
    parts = tuple(int(x) for x in text.strip().split("."))
    return parts + (0,) * (len(SQL_READ_MIN_VERSION) - len(parts))


def _valid_marker(folder, pid: int, claude: set) -> bool:
    """Whether server `pid` has a marker of its own saying 3.6.6 or later."""
    path = folder / f"{pid}.json" if folder is not None else None
    if path is None or not path.is_file():
        return False                                    # no marker: an older server
    marker = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(marker, dict):
        return False
    own, owner = marker.get("pid"), marker.get("parent_pid")
    if type(own) is not int or type(owner) is not int:     # 4242.0, "4242" and true are refused
        return False
    if own != pid or owner not in claude:
        return False
    if _started_after_marker(pid, marker.get("started")):
        return False                                    # a crash left it, and the pid was reused
    return _version(marker.get("version")) >= SQL_READ_MIN_VERSION


def server_reads_sql_safely() -> bool:
    """True only when at least one server counts and every counted server has a marker of its own saying
    3.6.6 or later. Counted: the servers this hook's Claude Code started, and when the Claude desktop app
    started Claude Code, the servers the app started too. Anything else, errors included, is False."""
    try:
        procs = _processes()
        if not procs:
            return False
        roots = _roots(_parent_pids(procs), procs)
        if roots is None:
            return False
        servers = _servers_of(roots, procs)
        if not servers:
            return False
        folder = _marker_dir()
        return all(_valid_marker(folder, pid, roots) for pid in servers)
    except Exception:
        return False


def load_list(path: Path = LIST_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _params(tool_input: dict) -> dict:
    params = tool_input.get("params")
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except ValueError:
            return {}
    return params if isinstance(params, dict) else {}


def decide(event: dict, data: dict):
    """(decision, reason) for a PreToolUse event, or None to leave it to the normal flow."""
    if not isinstance(event, dict):
        return None
    tool_name = event.get("tool_name")
    tool_input = event.get("tool_input")
    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        return None
    parts = tool_name.split("__")
    if len(parts) != 3 or parts[0] != "mcp" or parts[1] not in SERVER_SEGMENTS:
        return None
    meta_tool = parts[2]
    operations = data.get("operations", {}).get(meta_tool)
    operation = tool_input.get("operation")
    if operations is None or not isinstance(operation, str):
        return None
    access = operations.get(operation)
    if access is None:
        return None
    label = f"{meta_tool}.{operation}"
    if access == "read":
        return "allow", f"{label} only reads"
    if access == "sql":
        if _params(tool_input).get("allow_writes") is not False:
            return "ask", f"{label} can write unless allow_writes is false"
        if server_reads_sql_safely():
            return "allow", f"{label} with allow_writes false only reads"
        return "ask", (f"{label}: the hook could not confirm that the connected server is 3.6.6 or "
                       f"later, so a query with allow_writes false still asks")
    return "ask", f"{label} changes the model, a diagram, the repository database or files on disk"


def main() -> int:
    try:
        event = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
        result = decide(event, load_list())
    except Exception:
        return 0
    if result is None:
        return 0
    decision, reason = result
    out = {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                  "permissionDecision": decision,
                                  "permissionDecisionReason": reason}}
    sys.stdout.write(json.dumps(out))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
