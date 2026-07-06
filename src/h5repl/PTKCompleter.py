"""Prompt toolkit (PTK) based autocomplete for expanded functionality"""
import re
import inspect
import h5py
from prompt_toolkit.completion import Completer, Completion
from . import globals, goldh5file, session as _session


class PTKCompleter(Completer):
    def __init__(self, variables):
        # variables is the live REPL locals dict, not just keys
        self.variables = variables

    def get_completions(self, document, complete_event):
        full_line = document.text_before_cursor
        last_token = re.split(r'[\s(,\[]', full_line)[-1]  # token after last delimiter
        options = []

        # session name completion — accumulates into options, falls through to kwargs below
        m = re.match(r'(?:load|save)_session\(\s*["\']?(.*?)["\']?\s*$', full_line)
        if m:
            prefix = m.group(1)
            names = list(_session._BUILTIN_SESSIONS)
            sf = _session._resolve_sessions_file()
            if sf.exists():
                names += re.findall(r'(?m)^def (\w+)\(\):', sf.read_text())
            options += [n for n in names if n.startswith(prefix)]

        # dataset name completion inside get_dataset(file, <TAB>)
        m = re.match(r'get_dataset\(\s*([^,]+?)\s*,\s*["\']?(.*?)["\']?\s*$', full_line)
        if m:
            file_id, ds_prefix = m.group(1).strip('"\''), m.group(2)
            f = globals.OPEN_FILES.get(file_id)
            if f:
                def _collect(name, obj):
                    if isinstance(obj, (h5py.Dataset, goldh5file._VirtualDataset)):
                        if name.startswith(ds_prefix):
                            options.append(name)
                try:
                    f.visititems(_collect)
                except Exception:
                    pass

        elif '.' in last_token:
            # dotted access: resolve left side, dir() the result
            obj_expr, attr_prefix = last_token.rsplit('.', 1)
            obj = self._resolve(obj_expr)
            if obj is not None:
                attrs = self._attrs(obj)
                options += [f"{obj_expr}.{a}" for a in attrs if a.startswith(attr_prefix)]

        else:
            # bare token: all REPL names + open files + plot managers
            universe = set(self.variables) | set(globals.OPEN_FILES) | set(globals.PLOT_MANAGERS)
            options += [n for n in universe if n.startswith(last_token)]

        # kwarg completions: when inside a function call and not already past the '='
        if '=' not in last_token:
            options += self._kwarg_completions(full_line, last_token)

        seen = set()
        for opt in sorted(options):
            if opt not in seen:
                seen.add(opt)
                yield Completion(opt, start_position=-len(last_token))

    def _kwarg_completions(self, full_line, partial):
        """Return 'name=' completions when the cursor is inside a function call."""
        # find the innermost unclosed '('
        depth = 0
        call_start = -1
        for i in range(len(full_line) - 1, -1, -1):
            c = full_line[i]
            if c == ')':
                depth += 1
            elif c == '(':
                if depth == 0:
                    call_start = i
                    break
                depth -= 1
        if call_start < 0:
            return []

        # function expression is the identifier (or dotted name) immediately before '('
        fn_expr = full_line[:call_start].rstrip()
        m = re.search(r'[\w.]+$', fn_expr)
        if not m:
            return []

        obj = self._resolve(m.group(0))
        if not callable(obj):
            return []

        try:
            sig = inspect.signature(obj)
        except Exception:
            return []

        return [
            f'{name}='
            for name, p in sig.parameters.items()
            if p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
            and name != 'self'
            and name.startswith(partial)
        ]

    def _resolve(self, expr):
        """Eval an expression in the live REPL namespace; return None on failure."""
        try:
            return eval(expr, dict(self.variables))  # snapshot to avoid mutation
        except Exception:
            return None

    def _attrs(self, obj):
        """Non-private attributes of obj; augmented for PlotManager virtual attrs."""
        from .plotting import PlotManager
        attrs = {a for a in dir(obj) if not a.startswith('_')}  # skip private
        if isinstance(obj, PlotManager):
            # __getattr__ exposes these but dir() misses them
            attrs |= set(PlotManager._DISPLAY) | set(PlotManager._SCALE) | set(obj.series)
        return attrs
