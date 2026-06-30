import numpy as np
import matplotlib.pyplot as plt

from .series import Series

# ── PlotManager ───────────────────────────────────────────────────────────────

class PlotManager:
    """
    Manages a persistent matplotlib figure for the REPL session.

    Display properties update the figure immediately when set:
        plot.title  = "Rabi flop"
        plot.xlabel = "duration (µs)"
        plot.ylabel = "population"
        plot.grid   = True
        plot.xlim   = (0, 100)
        plot.ylim   = (0, 1)
        plot.xticks = [0, 25, 50, 75, 100]
        plot.yticks = [0, 0.5, 1]

    Scale/unit properties are read by quickplot() for automatic axis setup:
        plot.xscale = 1e6        # multiply x values by this before plotting
        plot.xunit  = 'µs'       # appended to auto-generated xlabel
        plot.yscale = 1.0
        plot.yunit  = None

    Data access:
        plot.axes[0]   — matplotlib Axes (full control)
        plot.fig       — matplotlib Figure
        plot.series[0] — list of Series on subplot 0

    Example:
        plot = PlotManager()
        plot = PlotManager(1, 2)   # two subplots side by side
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

    def __init__(self, nrows=1, ncols=1):
        object.__setattr__(self, '_disp', dict(self._DISPLAY_DEFAULTS))
        object.__setattr__(self, '_sc',   dict(self._SCALE_DEFAULTS))

        fig, axes_raw = plt.subplots(nrows, ncols)
        object.__setattr__(self, 'fig', fig)

        if nrows == 1 and ncols == 1:
            ax_list = [axes_raw]
        else:
            ax_list = list(np.array(axes_raw).flatten())
        object.__setattr__(self, 'axes', ax_list)
        object.__setattr__(self, 'series', [[] for _ in ax_list])

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    # ── attribute routing ─────────────────────────────────────────────────────

    def __setattr__(self, name, value):
        if name in PlotManager._DISPLAY:
            self._disp[name] = value
            self._apply_display()
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()
        elif name in PlotManager._SCALE:
            self._sc[name] = value
        else:
            object.__setattr__(self, name, value)

    def __getattr__(self, name):
        try:
            disp = object.__getattribute__(self, '_disp')
            if name in disp:
                return disp[name]
            sc = object.__getattribute__(self, '_sc')
            if name in sc:
                return sc[name]
        except AttributeError:
            pass
        raise AttributeError(f"PlotManager has no attribute '{name}'")

    # ── public API ────────────────────────────────────────────────────────────

    def add_series(self, s, ax=0):
        """Add a Series to subplot ax (0-indexed) and replot."""
        object.__setattr__(s, '_manager', self)
        object.__setattr__(s, '_ax_idx', ax)
        self.series[ax].append(s)
        self.replot()

    def add_series_batch(self, series_list, ax=0):
        """Add multiple Series at once with a single replot."""
        for s in series_list:
            object.__setattr__(s, '_manager', self)
            object.__setattr__(s, '_ax_idx', ax)
            self.series[ax].append(s)
        self.replot()

    def clear(self, ax=None):
        """Clear series from one subplot (or all) and replot."""
        if ax is None:
            for sl in self.series:
                for s in sl:
                    object.__setattr__(s, '_manager', None)
            object.__setattr__(self, 'series', [[] for _ in self.axes])
        else:
            for s in self.series[ax]:
                object.__setattr__(s, '_manager', None)
            self.series[ax] = []
        self.replot()

    def replot(self):
        """Redraw all axes from stored series, then apply display properties."""
        for i, ax in enumerate(self.axes):
            ax.cla()
            for s in self.series[i]:
                s.plot(ax)
            if any(s.label for s in self.series[i]):
                ax.legend()
        self._apply_display()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    # ── internals ─────────────────────────────────────────────────────────────

    def _apply_display(self):
        d = self._disp
        for ax in self.axes:
            if d['title']  is not None: ax.set_title(d['title'])
            if d['xlabel'] is not None: ax.set_xlabel(d['xlabel'])
            if d['ylabel'] is not None: ax.set_ylabel(d['ylabel'])
            ax.grid(d['grid'])
            if d['xlim']   is not None: ax.set_xlim(d['xlim'])
            if d['ylim']   is not None: ax.set_ylim(d['ylim'])
            if d['xticks'] is not None: ax.set_xticks(d['xticks'])
            if d['yticks'] is not None: ax.set_yticks(d['yticks'])

    def _set_disp_silent(self, **kwargs):
        """Update display state without triggering a redraw (used by quickplot)."""
        self._disp.update({k: v for k, v in kwargs.items() if k in self._DISPLAY_DEFAULTS})

    def __repr__(self):
        disp = {k: v for k, v in self._disp.items() if v is not None and v is not False}
        sc   = {k: v for k, v in self._sc.items()   if v != 1.0 and v is not None}
        parts = [f"{len(self.axes)}-axis"]
        parts += [f"{len(sl)} series" for sl in self.series]
        if disp: parts.append(str(disp))
        if sc:   parts.append(str(sc))
        return f"PlotManager({', '.join(parts)})"
