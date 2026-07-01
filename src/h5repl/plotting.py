import re
from pathlib import Path
import matplotlib as mpl
import matplotlib.pyplot as plt
from .series import Series
from . import globals as _globals


def _resolve_color_cycle():
    """Resolve COLOR_CYCLE setting to a list of color strings."""
    cycle = _globals.COLOR_CYCLE
    if isinstance(cycle, str):
        cmap = plt.get_cmap(cycle)
        if hasattr(cmap, 'colors'):
            return list(cmap.colors)
        return [cmap(i / 8) for i in range(8)]
    return list(cycle)


def save_style(name, rc):
    """
    Save a style preset to config.toml under [styles.<name>].

        save_style('big_font', {'font.size': 16, 'lines.linewidth': 2.0})
    """
    import tomllib
    import tomli_w

    toml_path = _globals.PKG_ROOT / 'config.toml'
    with open(toml_path, 'rb') as f:
        cfg = tomllib.load(f)

    cfg.setdefault('styles', {})[name] = rc
    _globals.CFG.setdefault('styles', {})[name] = rc  # update live config too

    with open(toml_path, 'wb') as f:
        tomli_w.dump(cfg, f)
    print(f"Saved style '{name}' to config.toml")


def _resolve_style(name):
    """Return rcParams dict for a named style from config.toml [styles], or {} if None/missing."""
    if name is None:
        return {}
    styles = _globals.CFG.get('styles', {})
    rc = styles.get(name)
    if rc is None:
        print(f"Warning: style '{name}' not found in config.toml [styles].")
        return {}
    return dict(rc)


def _series_nickname(name=None, label=None, fallback='s'):
    """Derive a Python-identifier-safe nickname for a series."""
    if name is not None:
        return name
    if label is not None:
        n = re.sub(r'[^a-zA-Z0-9]', '_', label).strip('_')  # non-alnum -> underscore
        n = re.sub(r'_+', '_', n)                             # collapse runs
        if n and n[0].isdigit():
            n = '_' + n                                        # can't start with digit
        if n:
            return n
    return fallback


class PlotManager:
    """
    Manages a single matplotlib figure for the REPL session.

    Display properties update the figure immediately when set:
        pm.title  = "Rabi flop"
        pm.xlabel = "duration (us)"
        pm.ylabel = "population"
        pm.grid   = True
        pm.xlim   = (0, 100)
        pm.ylim   = (0, 1)
        pm.xticks = [0, 25, 50, 75, 100]

    Scale/unit properties trigger a full replot when set:
        pm.xscale = 1e6        # rescales all x data retroactively
        pm.xunit  = 'us'       # regenerates xlabel if quickplot set it automatically
        pm.yscale = 1.0
        pm.yunit  = None

    Series access - all of these are equivalent:
        pm.pmt0.color = 'red'
        pm.pmt0.label = 'center ion'
        pm.series['pmt0'].color = 'red'

    Escape hatches:
        pm.ax      - matplotlib Axes
        pm.fig     - matplotlib Figure
    """

    _DISPLAY = frozenset({
        'title', 'xlabel', 'ylabel', 'grid',
        'xlim', 'ylim', 'xticks', 'yticks',
    })
    _SCALE = frozenset({'xscale', 'yscale', 'xunit', 'yunit'})

    _DISPLAY_DEFAULTS = {
        'title': None, 'xlabel': None, 'ylabel': None, 'grid': False,
        'xlim': None, 'ylim': None, 'xticks': None, 'yticks': None,
    }
    _SCALE_DEFAULTS = {
        'xscale': 1.0, 'yscale': 1.0, 'xunit': None, 'yunit': None,
    }

    def __init__(self):
        object.__setattr__(self, '_disp', dict(self._DISPLAY_DEFAULTS))
        object.__setattr__(self, '_sc',   dict(self._SCALE_DEFAULTS))

        fig, ax = plt.subplots(figsize=(10, 6))
        object.__setattr__(self, 'fig', fig)
        object.__setattr__(self, 'ax', ax)
        fig.canvas.mpl_connect('close_event', self._on_close)
        object.__setattr__(self, 'series', {})
        object.__setattr__(self, '_legend', False)
        object.__setattr__(self, '_color_idx', 0)
        object.__setattr__(self, '_xname', None)
        object.__setattr__(self, '_yname', None)
        object.__setattr__(self, '_style', None)

    # -- attribute routing -----------------------------------------------------

    def __setattr__(self, name, value):
        if name in PlotManager._DISPLAY:             # axis label / limit / grid
            self._disp[name] = value
            self._apply_display()
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()
        elif name in PlotManager._SCALE:             # scale / unit -> full replot
            self._sc[name] = value
            if name == 'xunit':                      # rebuild auto xlabel
                xname = object.__getattribute__(self, '_xname')
                if xname is not None:
                    self._disp['xlabel'] = f"{xname} ({value})" if value else xname
            elif name == 'yunit':                    # rebuild auto ylabel
                yname = object.__getattribute__(self, '_yname')
                if yname is not None:
                    self._disp['ylabel'] = f"{yname} ({value})" if value else yname
            self.replot()
        else:
            object.__setattr__(self, name, value)    # regular attribute

    def __getattr__(self, name):
        try:
            disp = object.__getattribute__(self, '_disp')
            if name in disp:
                return disp[name]
            sc = object.__getattribute__(self, '_sc')
            if name in sc:
                return sc[name]
            series = object.__getattribute__(self, 'series')
            if name in series:
                return series[name]
        except AttributeError:
            pass
        raise AttributeError(f"PlotManager has no attribute '{name}'")

    # -- public API ------------------------------------------------------------

    def _assign_color(self, s):
        """Auto-assign the next color from the cycle to a Series that has none."""
        if s.color is None:
            colors = _resolve_color_cycle()
            idx = object.__getattribute__(self, '_color_idx')
            object.__setattr__(s, 'color', colors[idx % len(colors)])
            object.__setattr__(self, '_color_idx', idx + 1)

    def add(self, x, y, yerr=None, name=None, label=None,
            color=None, linestyle=None, marker=None,
            fit=None, fmt='o', capsize=3, **kwargs):
        """
        Add data as a new series and replot. Returns the nickname.

            pm.add(x, y, label='Rabi', color='steelblue')
            pm.Rabi.color = 'red'
            pm.add(x, y, name='ref')
            pm.ref.linestyle = '--'
        """
        s = Series(x, y, yerr=yerr, label=label, color=color,
                   linestyle=linestyle, marker=marker, fit=fit,
                   fmt=fmt, capsize=capsize, **kwargs)
        nickname = _series_nickname(name, label, fallback=f's{len(self.series) + 1}')
        self._add_series(s, name=nickname)
        print(f"Added as '{nickname}'")
        return nickname

    def _add_series(self, s, name=None):
        if name is None:
            name = _series_nickname(None, getattr(s, 'label', None),
                                    fallback=f's{len(self.series) + 1}')
        self._assign_color(s)
        object.__setattr__(s, '_manager', self)
        self.series[name] = s
        self.replot()
        return name

    def _add_series_batch(self, series_dict):
        for name, s in series_dict.items():
            self._assign_color(s)
            object.__setattr__(s, '_manager', self)
            self.series[name] = s
        self.replot()

    def autoscale(self):
        """Reset axis limits to auto (undo any manual xlim/ylim) and replot."""
        self._disp['xlim'] = None
        self._disp['ylim'] = None
        self.replot()

    def legend(self, loc=None):
        """Show the legend. Unlabeled series get their nickname as label automatically."""
        for name, s in self.series.items():
            if s.label is None:
                object.__setattr__(s, 'label', name)
        object.__setattr__(self, '_legend', loc if loc is not None else True)
        self.replot()

    def remove_series(self, name):
        """Remove a named series and replot."""
        s = self.series.pop(name, None)
        if s is not None:
            object.__setattr__(s, '_manager', None)
        self.replot()

    def clear(self):
        """Remove all series, reset display and scale to defaults, and replot."""
        for s in self.series.values():
            object.__setattr__(s, '_manager', None)
        object.__setattr__(self, 'series', {})
        object.__setattr__(self, '_disp', dict(self._DISPLAY_DEFAULTS))
        object.__setattr__(self, '_sc', dict(self._SCALE_DEFAULTS))
        object.__setattr__(self, '_legend', False)
        object.__setattr__(self, '_color_idx', 0)
        object.__setattr__(self, '_xname', None)
        object.__setattr__(self, '_yname', None)
        self.replot()

    def style(self, name):
        """
        Apply a named style preset from config.toml [styles] to this PlotManager.
        The style re-applies on every replot, so it persists across data changes.
        Use pm.style(None) to clear.

            pm.style('publication')
            pm.style(None)

        Add presets to config.toml:
            [styles.publication]
            font.size = 12
            lines.linewidth = 1.5
            axes.linewidth = 1.0
        """
        object.__setattr__(self, '_style', name)
        self.replot()

    def export(self, filename=None, dest=None, dpi=300):
        """
        Save the figure to disk. Applies tight_layout before saving.
        Supports any matplotlib format: pdf, png, svg, etc.

            pm.export('rabi_flop.pdf')              # saves to figures_dir from config.toml
            pm.export('rabi_flop.png', dpi=600)
            pm.export('out.pdf', dest='/tmp/figs')  # explicit output directory
            pm.export()                             # uses title as filename, saves as .pdf

        Default output directory is set by figures_dir in config.toml.
        """
        if filename is None:
            title = self._disp.get('title') or 'figure'
            filename = title.replace(' ', '_').replace('|', '').replace('/', '_').strip('_') + '.pdf'
        if dest is None:
            cfg_dir = _globals.CFG.get('figures_dir')
            dest = (_globals.PKG_ROOT / cfg_dir).resolve() if cfg_dir else _globals.USER_DIR / 'figures'
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        out = dest / filename
        self.fig.tight_layout()
        self.fig.savefig(out, dpi=dpi)
        print(f"Saved -> {out}")
        return out

    def replot(self):
        """Redraw all series, then apply display properties."""
        style_name = object.__getattribute__(self, '_style')
        style_rc = _resolve_style(style_name)
        with mpl.rc_context(style_rc):
            self.ax.cla()
            xscale = self._sc['xscale']
            yscale = self._sc['yscale']
            for s in self.series.values():
                s.plot(self.ax, xscale=xscale, yscale=yscale)
            self._apply_display()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    # -- internals -------------------------------------------------------------

    def _apply_display(self):
        d = self._disp
        ax = self.ax
        if d['title']  is not None: ax.set_title(d['title'])
        if d['xlabel'] is not None: ax.set_xlabel(d['xlabel'])
        if d['ylabel'] is not None: ax.set_ylabel(d['ylabel'])
        ax.grid(d['grid'])
        if d['xlim']   is not None: ax.set_xlim(d['xlim'])
        if d['ylim']   is not None: ax.set_ylim(d['ylim'])
        if d['xticks'] is not None: ax.set_xticks(d['xticks'])
        if d['yticks'] is not None: ax.set_yticks(d['yticks'])
        leg = object.__getattribute__(self, '_legend')
        if leg is False:
            existing = ax.get_legend()
            if existing:
                existing.remove()
        elif ax.get_legend_handles_labels()[0]:
            ax.legend() if leg is True else ax.legend(loc=leg)

    def _on_close(self, _):
        key = None
        for k, v in _globals.PLOT_MANAGERS.items():
            if v is self:
                key = k
                break
        if key is not None:
            del _globals.PLOT_MANAGERS[key]
            print(f"\n{key} closed.")

    def _set_disp_silent(self, **kwargs):
        """Update display state without triggering a redraw (used by quickplot)."""
        self._disp.update({k: v for k, v in kwargs.items() if k in self._DISPLAY_DEFAULTS})

    def __repr__(self):
        disp = {k: v for k, v in self._disp.items() if v is not None and v is not False}
        sc   = {k: v for k, v in self._sc.items()   if v != 1.0 and v is not None}
        parts = [f"{len(self.series)} series: {list(self.series)}"]
        if disp: parts.append(str(disp))
        if sc:   parts.append(str(sc))
        return f"PlotManager({', '.join(parts)})"
