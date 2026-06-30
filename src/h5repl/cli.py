"""Command-line interface entry point for h5repl"""
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import numpy as np
import code
import inspect
import re
from prompt_toolkit import PromptSession
from . import h5utils, globals, PTKCompleter, session as _session

_META_PREFIXES = tuple(_session._META_COMMANDS)


class H5REPL(code.InteractiveConsole):
    def __init__(self):
        import h5repl
        self.variables = {"plt": plt, "np": np, "help": help}
        self.variables.update({
            k: v for k, v in vars(h5repl).items()
            if not k.startswith("_") and k not in {"main", "cli"}
        })

        self.session = PromptSession(
            completer=PTKCompleter.PTKCompleter(self.variables.keys()),
            complete_while_typing=True,
            complete_style="READLINE_LIKE"
        )

        super().__init__(locals=self.variables)

    def preprocess(self, source):
        """Preprocesses source string before it is sent to runsource"""
        source = source.strip()
        # Rewrite bare open(...) → h5open(...) before builtins can intercept it
        source = re.sub(r'(?<![.\w])open\(', 'h5open(', source)
        for key in globals.OPEN_FILES.keys():
            source = re.sub(key, f"\"{key}\"", source)
        source = re.sub(r'get_dataset\(("[^"]*"|[^,]+),\s*([^"\s][^)]*?)\s*\)', r'get_dataset(\1, "\2")', source)
        # Auto-quote bare session names: load_session(name) → load_session("name")
        source = re.sub(r'\b((?:load|save)_session)\(([^"\'\s)][^)]*)\)', r'\1("\2")', source)
        return source

    def runsource(self, source, filename="<input>", symbol="single"):
        """Modified function for running the line of code after preprocessing"""
        source = self.preprocess(source)

        # If input is just a name and callable, print docstring instead of executing
        if source.isidentifier():
            try:
                obj = eval(source, self.locals)
                if callable(obj):
                    doc = inspect.getdoc(obj)
                    print(f"\nDocstring for {source}:\n{'-'*40}")
                    print(doc or "(No docstring available)")
                    print("-"*40 + "\n")
                    return False
            except Exception:
                pass

        result = super().runsource(source, filename, symbol)

        # Record completed, non-trivial, non-meta blocks for save_session
        stripped = source.strip()
        if (not result
                and stripped
                and not stripped.isidentifier()
                and not stripped.startswith(_META_PREFIXES)):
            _session.record(source)

        # Inject any newly created PlotManagers into the REPL namespace
        for name, mgr in globals.PLOT_MANAGERS.items():
            if name not in self.locals:
                self.locals[name] = mgr

        # Redraw any open figures without entering a nested Tk event loop
        if plt.get_fignums():
            try:
                for num in plt.get_fignums():
                    fig = plt.figure(num)
                    fig.canvas.draw_idle()
                    fig.canvas.flush_events()
            except Exception:
                pass

        return result

    def interact(self, banner=None):
        """Overridden function for interactive session to make it a bit cleaner"""
        if banner:
            print(banner)
        while True:
            try:
                line = self.session.prompt(">>> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            else:
                more = self.push(line)
                while more:
                    try:
                        line = self.session.prompt("... ")
                    except (EOFError, KeyboardInterrupt):
                        print()
                        more = False
                    else:
                        more = self.push(line)


def main():
    plt.ion()

    repl = H5REPL()

    # Inject session management as closures so load_session has the REPL namespace
    repl.locals['save_session'] = _session.save_session
    repl.locals['load_session'] = lambda name: _session.load_session(name, repl.locals)
    repl.locals['list_sessions'] = _session.list_sessions
    repl.locals['clear_history'] = _session.clear_history

    try:
        repl.interact(banner="")
    finally:
        h5utils.h5close_all()
