"""Command-line interface entry point for h5repl"""
import sys
import asyncio
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import code
import inspect
import re
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from . import h5utils, globals, PTKCompleter, session as _session

_META_PREFIXES = tuple(_session._META_COMMANDS)


async def _gui_pump():
    """Pump matplotlib event loop at ~20 fps while the REPL waits for input."""
    while True:
        for num in plt.get_fignums():
            try:
                fig = plt.figure(num)
                fig.canvas.draw_idle()
                fig.canvas.flush_events()
            except Exception:
                pass
        await asyncio.sleep(0.05)


class H5REPL(code.InteractiveConsole):
    def __init__(self):
        import h5repl
        self.variables = {"plt": plt, "np": np, "help": help}
        self.variables.update({
            k: v for k, v in vars(h5repl).items()
            if not k.startswith("_") and k not in {"main", "cli"}
        })

        self.session = PromptSession(
            completer=PTKCompleter.PTKCompleter(self.variables),  # live dict for eval
            complete_while_typing=True,
            complete_style="READLINE_LIKE"
        )

        super().__init__(locals=self.variables)

    @staticmethod
    def _show_doc(expr, obj):
        """Print the docstring (or repr, for non-callables) of an evaluated expression."""
        doc = inspect.getdoc(obj) if callable(obj) else None
        print(f"\n{expr}:\n{'-'*40}")
        print(doc if doc else repr(obj))
        print('-'*40 + '\n')

    def preprocess(self, source):
        """Preprocesses source string before it is sent to runsource"""
        source = source.strip()
        source = re.sub(r'(?<![.\w])open\(', 'h5open(', source)        # open -> h5open
        for key in globals.OPEN_FILES:
            ek = re.escape(key)
            # 166078.attr  →  OPEN_FILES["166078"].attr
            source = re.sub(r'(?<!["\'\w])' + ek + r'(?=\.)',
                            f'OPEN_FILES["{key}"]', source)
            # bare 166078  →  "166078"  (function args, not followed by . or word char)
            source = re.sub(r'(?<!["\'\w])' + ek + r'(?![\w.])',
                            f'"{key}"', source)
        source = re.sub(r'get_dataset\(("[^"]*"|[^,]+),\s*([^"\s][^)]*?)\s*\)',
                         r'get_dataset(\1, "\2")', source)               # quote dataset name
        source = re.sub(r'\b((?:load|save)_session)\(([^"\'\s)][^)]*)\)',
                         r'\1("\2")', source)                            # quote session name
        return source

    def runsource(self, source, filename="<input>", symbol="single"):
        """Modified function for running the line of code after preprocessing"""
        source = self.preprocess(source)

        stripped = source.rstrip()
        if stripped.endswith(';'):                                   # trailing ; -> show docs
            expr = stripped.rstrip(';').strip()
            try:
                obj = eval(expr, self.locals)
                self._show_doc(expr, obj)
            except Exception:
                pass
            return False

        if source.isidentifier():
            try:
                obj = eval(source, self.locals)
                if callable(obj):
                    sig = inspect.signature(obj)
                    required = [p for p in sig.parameters.values()
                                if p.default is inspect.Parameter.empty
                                and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)]
                    if not required:                                 # zero-arg callable -> run it
                        obj()
                    else:                                            # needs args -> show docs
                        self._show_doc(source, obj)
                    return False
            except Exception:
                pass

        result = super().runsource(source, filename, symbol)

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

        return result

    async def interact_async(self):
        """Async REPL loop - runs alongside _gui_pump so figures stay responsive."""
        print("\nh5repl  |  type help_repl for reference  |  load_session(demo) to start\n")
        with patch_stdout():
            while True:
                try:
                    line = await self.session.prompt_async(">>> ")
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                more = self.push(line)
                while more:
                    try:
                        line = await self.session.prompt_async("... ")
                    except (EOFError, KeyboardInterrupt):
                        print()
                        more = False
                    else:
                        more = self.push(line)


def main():
    matplotlib.use('TkAgg')
    # SelectorEventLoop is required on Windows for Tk + asyncio compatibility.
    # ProactorEventLoop (the Windows default) conflicts with Tk's event handling.
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    plt.ion()
    repl = H5REPL()

    # Load user/startup.py into the REPL namespace if it exists.
    from . import globals as _g
    startup = _g.USER_DIR / 'startup.py'
    if startup.exists():
        try:
            exec(compile(startup.read_text('utf-8'), str(startup), 'exec'), repl.locals)
            print(f"Loaded {startup}")
        except Exception as e:
            print(f"startup.py error: {e}")

    def _load_and_sync(name):
        _session.load_session(name, repl.locals)
        for mgr_name, mgr in globals.PLOT_MANAGERS.items():
            if mgr_name not in repl.locals:
                repl.locals[mgr_name] = mgr

    repl.locals['save_session'] = _session.save_session
    repl.locals['load_session'] = _load_and_sync
    repl.locals['list_sessions'] = _session.list_sessions
    repl.locals['clear_history'] = _session.clear_history

    async def run():
        gui = asyncio.create_task(_gui_pump())
        try:
            await repl.interact_async()
        finally:
            gui.cancel()
            h5utils.h5close_all()

    asyncio.run(run())
