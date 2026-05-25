import matplotlib.pyplot as plt
import numpy as np

from .fitutils import FitObj

class Series:
    """
    A data series to be plotted on a PlotManager axis.

    Args:
        x, y        : array-like data
        label       : legend label
        color       : matplotlib color string
        linestyle   : default '-'
        marker      : matplotlib marker string e.g. 'o', '.'
        fit         : FitObj instance. If provided and fit.result exists, 
                      the fit curve is plotted as a dashed line alongside the data.
        **kwargs    : any additional kwargs are passed directly to ax.plot()

    Example:
        s = Series(x, y, label="signal", color="blue", marker='o')
        s = Series(x, y, label="data", fit=my_fit)
        plot.add_series(s)
    """
    def __init__(self, x, y, label=None, color=None, linestyle='-', marker=None, fit=None, **kwargs):
        self.x = x
        self.y = y
        self.label = label
        self.color = color
        self.linestyle = linestyle
        self.marker = marker
        self.fit = fit  # optional callable f(x) or FitResult with .fn
        self.kwargs = kwargs

    def plot(self, ax):
        ax.plot(self.x, self.y, label=self.label, color=self.color,
                linestyle=self.linestyle, marker=self.marker, **self.kwargs)
        if self.fit is not None:
            fn = self.fit.fn if isinstance(self.fit, FitObj) else (self.fit if callable(self.fit) else self.fit.fn)
            ax.plot(self.x, fn(self.x), linestyle='--',
                    color=self.color, label=f"{self.label} (fit)" if self.label else "fit")


class PlotManager:
    """
    Manages a single persistent matplotlib figure for the REPL session.
    Wraps subplots but exposes fig and axes directly for full matplotlib control.

    Args:
        nrows, ncols : subplot layout, default (1, 1)

    Attributes:
        fig          : the matplotlib Figure — use freely for titles, sizing, etc.
        axes         : list of Axes (flattened). Single plot: axes[0].
        series       : list of lists of Series, one per subplot.

    Example:
        plot = PlotManager()          # single plot
        plot = PlotManager(1, 2)      # two side-by-side subplots

        # Full matplotlib access
        plot.axes[0].set_xlabel("time (s)")
        plot.axes[0].set_yscale("log")
        plot.fig.suptitle("experiment 42")

        # Convenience methods
        plot.add_series(Series(x, y, label="data"), ax=0)
        plot.clear(ax=0)
        plot.replot()
    """
    def __init__(self, nrows=1, ncols=1):
        self.fig, axes = plt.subplots(nrows, ncols)
        if nrows == 1 and ncols == 1:
            self.axes = [axes]
        else:
            self.axes = list(np.array(axes).flatten())
        self.series = [[] for _ in self.axes]
        plt.show(block=False)

    def add_series(self, s, ax=0):
        """Add a Series to subplot ax (0-indexed) and replot."""
        self.series[ax].append(s)
        self.replot()

    def clear(self, ax=None):
        """Clear series from one subplot (or all if ax=None) and replot."""
        if ax is None:
            self.series = [[] for _ in self.axes]
        else:
            self.series[ax] = []
        self.replot()

    def replot(self):
        for i, ax in enumerate(self.axes):
            ax.cla()
            for s in self.series[i]:
                s.plot(ax)
            if any(s.label for s in self.series[i]):
                ax.legend()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()