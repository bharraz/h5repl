"""
A Series holds the data, styling, and fit for a single plotted line.
Multiple Series live inside a PlotManager and auto-replot when mutated.
"""

import numpy as np

_MARKER_CHARS = set('.,ov^<>1234sp*hH+xXDd|_')

def _fmt_strip_marker(fmt):
    """Remove any marker character from a fmt string, leaving only line/color spec."""
    return ''.join(c for c in fmt if c not in _MARKER_CHARS)


class Series:
    """
    A data series managed by a PlotManager. Never constructed directly by the user -
    created via quickplot() or pm.add(x, y, ...).

    All attributes auto-trigger a replot on the parent PlotManager when changed:

    Data:
        s.x = new_array       # swap in new x data
        s.y = new_array
        s.yerr = new_array

    Style:
        s.color      = 'steelblue'
        s.alpha      = 0.8
        s.label      = 'center ion'    # also updates the legend
        s.fmt        = 'o'             # marker/line format string
        s.markersize = 4
        s.capsize    = 3

    Fit:
        s.run_fit(fit_obj)             # fits, prints result, attaches, replots
        s.fit = my_result              # attach a pre-computed FitResult
        s.fit_color     = 'red'        # override fit line color (default: same as series)
        s.fit_alpha     = 1.0          # override fit line alpha
        s.fit_linestyle = '--'         # default '--'
    """

    _PLOT_ATTRS = frozenset({
        'x', 'y', 'yerr', 'label', 'color', 'alpha', 'visible',
        'linestyle', 'marker', 'markersize', 'capsize',
        'fit', 'fmt', 'kwargs',
        'fit_color', 'fit_alpha', 'fit_linestyle',
    })

    def __init__(self, x, y, yerr=None, label=None, color=None, alpha=None,
                 visible=True, linestyle=None, marker=None, markersize=None,
                 capsize=3, fit=None, fmt='o', fit_color=None, fit_alpha=None,
                 fit_linestyle='--', **kwargs):
        object.__setattr__(self, '_manager', None)
        self.visible = visible
        self.x = np.asarray(x)
        self.y = np.asarray(y)
        self.yerr = np.asarray(yerr) if yerr is not None else None
        self.label = label
        self.color = color
        self.alpha = alpha
        self.linestyle = linestyle
        self.marker = marker
        self.markersize = markersize
        self.capsize = capsize
        self.fit = fit
        self.fmt = fmt
        self.fit_color = fit_color
        self.fit_alpha = fit_alpha
        self.fit_linestyle = fit_linestyle
        self.kwargs = kwargs

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)      # bypass recursion
        if name in Series._PLOT_ATTRS:
            try:
                mgr = object.__getattribute__(self, '_manager')  # bypass __getattr__
                if mgr is not None:
                    mgr.replot()
            except AttributeError:
                pass

    def plot(self, ax, xscale=1.0, yscale=1.0):
        """Render this series onto ax, applying scale factors."""
        if not self.visible:
            return
        x = self.x * xscale
        y = self.y * yscale
        yerr = self.yerr * yscale if self.yerr is not None else None

        kw = dict(self.kwargs)
        if self.markersize is not None: kw['markersize'] = self.markersize
        if self.linestyle  is not None: kw['linestyle']  = self.linestyle
        if self.marker     is not None: kw['marker']     = self.marker

        # strip marker from fmt when marker kwarg also set; avoids mpl warning
        fmt = _fmt_strip_marker(self.fmt) if self.marker is not None else self.fmt

        ax.errorbar(x, y, yerr=yerr,
                    label=self.label,
                    color=self.color,
                    alpha=self.alpha,
                    fmt=fmt,
                    capsize=self.capsize,
                    **kw)

        if self.fit is not None:
            self._plot_fit(ax, xscale=xscale, yscale=yscale)

    def run_fit(self, fit_obj):
        """Fit this series' data, print the result, attach it, and replot."""
        kw = {}
        if self.yerr is not None:
            yerr = self.yerr
            if np.all(yerr > 0) and np.all(np.isfinite(yerr)):
                kw = {'sigma': yerr, 'absolute_sigma': True}
        result = fit_obj.fit(self.x, self.y, **kw)
        print(result)
        self.fit = result  # triggers replot
        return result

    def _plot_fit(self, ax, xscale=1.0, yscale=1.0):
        from .fitutils import FitObj, FitResult
        fit_label = f"{self.label} (fit)" if self.label else "fit"
        fit_color = self.fit_color if self.fit_color is not None else self.color  # inherit color

        if isinstance(self.fit, FitObj) and self.fit.result is not None:   # FitObj wrapper
            r = self.fit.result
            xs_raw = r.xs if r.xs is not None else np.linspace(np.min(self.x), np.max(self.x), 500)
            ys = (r.ys if r.ys is not None else r.fn(xs_raw, *r.popt)) * yscale
        elif isinstance(self.fit, FitResult):                               # bare FitResult
            xs_raw = self.fit.xs if self.fit.xs is not None else np.linspace(np.min(self.x), np.max(self.x), 500)
            ys = (self.fit.ys if self.fit.ys is not None else self.fit.fn(xs_raw, *self.fit.popt)) * yscale
        elif callable(self.fit):                                             # raw function
            xs_raw = np.linspace(np.min(self.x), np.max(self.x), 500)
            ys = self.fit(xs_raw) * yscale
        else:
            return

        ax.plot(xs_raw * xscale, ys,
                linestyle=self.fit_linestyle,
                color=fit_color,
                alpha=self.fit_alpha,
                label=fit_label)

    def __repr__(self):
        n = len(self.x) if hasattr(self.x, '__len__') else '?'
        parts = [f"{n} pts"]
        if self.label:
            parts.append(f"label={self.label!r}")
        if self.color:
            parts.append(f"color={self.color!r}")
        if self.fit is not None:
            from .fitutils import FitObj, FitResult
            result = None
            if isinstance(self.fit, FitResult):
                result = self.fit
            elif isinstance(self.fit, FitObj) and self.fit.result is not None:
                result = self.fit.result
            if result is not None:
                param_strs = [f"{k}={v}" for k, v in result.params.items()]
                parts.append(f"fit: {', '.join(param_strs)}")
            else:
                parts.append("fit: pending")
        return f"Series({', '.join(parts)})"
