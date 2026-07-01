"""Session recording and replay for h5repl."""

import re
from pathlib import Path

from .globals import USER_DIR

_executed_lines: list = []

# Commands that are meta/housekeeping and should not be replayed in saved sessions
_META_COMMANDS = {"save_session", "load_session", "list_sessions", "clear_history"}


def record(source: str) -> None:
    """Append a completed source block to the in-memory session history."""
    _executed_lines.append(source)


def clear_history() -> None:
    """Clear the current session recording (does not affect the sessions file)."""
    _executed_lines.clear()
    print("Session history cleared.")


def _sessions_file() -> Path:
    return USER_DIR / "sessions.py"


_HEADER = (
    "from h5repl import *\n"
    "import numpy as np\n"
    "import matplotlib.pyplot as plt\n"
)


def save_session(name: str) -> None:
    """
    Save the current REPL session as a named function in user/sessions.py.
    If a session with that name already exists it is overwritten.
    Call clear_history() first to start a fresh recording.
    """
    if not _executed_lines:
        print("Nothing to save - no commands recorded in this session.")
        return

    sf = _sessions_file()
    if not sf.exists():
        sf.write_text(_HEADER + "\n")

    content = sf.read_text()

    # Flatten all recorded blocks into indented function body
    body = "\n".join(
        "    " + subline
        for block in _executed_lines
        for subline in block.splitlines()
    )
    new_func = f"def {name}():\n{body}\n"

    # Replace existing definition or append
    pattern = rf"(?s)(?m)^def {re.escape(name)}\(\):.*?(?=\ndef |\Z)"
    if re.search(pattern, content):
        new_content = re.sub(pattern, new_func.rstrip(), content)
    else:
        new_content = content.rstrip("\n") + "\n\n" + new_func

    sf.write_text(new_content)
    print(f"Saved session '{name}' -> {sf}")


_BUILTIN_SESSIONS = {'demo'}


def load_session(name: str, exec_locals: dict) -> None:
    """
    Replay a named session from user/sessions.py in the current REPL namespace.
    Built-in sessions (e.g. 'demo') are loaded from the package itself.
    All variables and open files created by the session are available afterwards.
    """
    # built-in sessions live in the package, not in user/sessions.py
    if name in _BUILTIN_SESSIONS:
        import importlib
        mod = importlib.import_module(f'._{name}', package='h5repl')
        getattr(mod, name)()
        return

    sf = _sessions_file()
    if not sf.exists():
        print("No sessions file found. Save a session first with save_session('name').")
        return

    content = sf.read_text()
    pattern = rf"(?s)(?m)^def {re.escape(name)}\(\):.*?(?=\ndef |\Z)"  # full def block
    match = re.search(pattern, content)
    if not match:
        print(f"Session '{name}' not found.")
        list_sessions()
        return

    ns = dict(exec_locals)
    exec(compile(match.group(0), f"<session:{name}>", "exec"), ns)
    ns[name]()


def list_sessions() -> None:
    """List all saved sessions in user/sessions.py."""
    sf = _sessions_file()
    if not sf.exists():
        print("No sessions file yet.")
        return

    names = re.findall(r"(?m)^def (\w+)\(\):", sf.read_text())
    if not names:
        print("No sessions saved yet.")
    else:
        print("Saved sessions:")
        for n in names:
            print(f"  {n}")
