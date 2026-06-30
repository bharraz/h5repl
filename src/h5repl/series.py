"""
A Series holds the data, styling, and fit for a single plotted line.
Multiple Series live inside a PlotManager and auto-replot when mutated.
"""

import numpy as np


class Series:
    """
    A data series to be plotted on a PlotManager axis.

    All plot-relevant attributes (x, y, yerr, label, color, linestyle, marker,
    fit, fmt) auto-trigger a replot on the parent PlotManager when changed.

    Args:
        x, y      : array-like data
        yerr      : optional error bars (same shape as y)
        label     : legend label
        color     : matplotlib color string
        linestyle : line style, default '-'
        marker    : marker string e.g. 'o', '.'
        fmt       : errorbar format string e.g. 'o-'. If set, ax.errorbar is
                    used instead of ax.plot regardless of yerr.
        fit       : FitObj, FitResult, or callable f(x). Overlaid as dashed line.
        **kwargs  : passed directly to ax.plot / ax.errorbar

    Example:
        s = Series(x, y, yerr=err, label='pops_0', color='steelblue', fmt='o-')
        s.label = 'center ion'   # immediately redraws if added to a PlotManager
    """

    _PLOT_ATTRS = frozenset({'x', 'y', 'yerr', 'label', 'color',
                             'linestyle', 'marker', 'fit', 'fmt', 'kwargs'})

    def __init__(self, x, y, yerr=None, label=None, color=None,
                 linestyle='-', marker=None, fit=None, fmt=None, **kwargs):
        object.__setattr__(self, '_manager', None)
        object.__setattr__(self, '_ax_idx', 0)
        self.x = x
        self.y = y
        self.yerr = yerr
        self.label = label
        self.color = color
        self.linestyle = linestyle
        self.marker = marker
        self.fit = fit
        self.fmt = fmt
        self.kwargs = kwargs

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        if name in Series._PLOT_ATTRS:
            try:
                mgr = object.__getattribute__(self, '_manager')
                if mgr is not None:
                    mgr.replot()
            except AttributeError:
                pass

    def plot(self, ax):
        """Render this series onto ax."""
        kw = dict(self.kwargs)
        use_errorbar = self.yerr is not None or self.fmt is not None
        if use_errorbar:
            ax.errorbar(self.x, self.y, yerr=self.yerr,
                        label=self.label, color=self.color,
                        fmt=self.fmt or 'o-', **kw)
        else:
            ax.plot(self.x, self.y, label=self.label, color=self.color,
                    linestyle=self.linestyle, marker=self.marker, **kw)

        if self.fit is not None:
            self._plot_fit(ax)

    def _plot_fit(self, ax):
        from .fitutils import FitObj, FitResult
        xs = np.linspace(np.min(self.x), np.max(self.x), 500)
        fit_label = f"{self.label} (fit)" if self.label else "fit"
        if isinstance(self.fit, FitObj) and self.fit.result is not None:
            ys = self.fit.result.fn(xs, *self.fit.result.popt)
        elif isinstance(self.fit, FitResult):
            ys = self.fit.fn(xs, *self.fit.popt)
        elif callable(self.fit):
            ys = self.fit(xs)
        else:
            return
        ax.plot(xs, ys, linestyle='--', color=self.color, label=fit_label)

    def __repr__(self):
        n = len(self.x) if hasattr(self.x, '__len__') else '?'
        return (f"Series({n} pts, label={self.label!r}, "
                f"color={self.color!r}, fit={self.fit is not None})")
