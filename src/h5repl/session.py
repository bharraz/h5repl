"""Session recording and replay for h5repl."""

import re
from pathlib import Path

from . import globals as _globals

_executed_lines: list = []

_META_COMMANDS = {"save_session", "load_session", "list_sessions", "clear_history"}


def record(source: str) -> None:
    """Append a completed source block to the in-memory session history."""
    _executed_lines.append(source)


def clear_history() -> None:
    """Clear the current session recording (does not affect the sessions file)."""
    _executed_lines.clear()
    print("Session history cleared.")


_HEADER = (
    "from h5repl import *\n"
    "import numpy as np\n"
    "import matplotlib.pyplot as plt\n"
)

_PATTERN = staticmethod(lambda name: rf"(?s)(?m)^def {re.escape(name)}\(\):.*?(?=\ndef |\Z)")


def _resolve_sessions_file(directory=None) -> Path:
    d = Path(directory) if directory else _globals.USER_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d / "sessions.py"


def save_session(name: str, directory=None) -> None:
    """
    Save the current REPL history as a named function in sessions.py.
    Overwrites any existing session with the same name.
    Call clear_history() first to start a fresh recording.

        save_session(my_exp)
        save_session(my_exp, directory='/path/to/project')
    """
    if not _executed_lines:
        print("Nothing to save - no commands recorded in this session.")
        return

    sf = _resolve_sessions_file(directory)
    if not sf.exists():
        sf.write_text(_HEADER + "\n")

    content = sf.read_text()
    body = "\n".join(
        "    " + subline
        for block in _executed_lines
        for subline in block.splitlines()
    )
    new_func = f"def {name}():\n{body}\n"

    pattern = _PATTERN(name)
    if re.search(pattern, content):
        new_content = re.sub(pattern, new_func.rstrip(), content)
    else:
        new_content = content.rstrip("\n") + "\n\n" + new_func

    sf.write_text(new_content)
    print(f"Saved session '{name}' -> {sf}")


_BUILTIN_SESSIONS = {'demo'}


def load_session(name: str, exec_locals: dict) -> None:
    """
    Replay a named session from sessions.py in the current REPL namespace.
    Built-in sessions (e.g. 'demo') are loaded from the package itself.

        load_session(my_exp)
        load_session(demo)
    """
    if name in _BUILTIN_SESSIONS:
        import importlib
        mod = importlib.import_module(f'._{name}', package='h5repl')
        getattr(mod, name)()
        return

    sf = _resolve_sessions_file()
    if not sf.exists():
        print(f"No sessions file found at {sf}.")
        return

    content = sf.read_text()
    match = re.search(_PATTERN(name), content)
    if not match:
        print(f"Session '{name}' not found.")
        list_sessions()
        return

    ns = dict(exec_locals)
    exec(compile(match.group(0), f"<session:{name}>", "exec"), ns)
    ns[name]()


def list_sessions() -> None:
    """List all saved sessions in sessions.py."""
    sf = _resolve_sessions_file()
    if not sf.exists():
        print("No sessions file yet.")
        return
    names = re.findall(r"(?m)^def (\w+)\(\):", sf.read_text())
    if names:
        print("Saved sessions:")
        for n in names:
            print(f"  {n}")
    else:
        print("No sessions saved yet.")
