# h5repl package init

from .h5utils import h5open, get_dataset, h5print, h5close, h5close_all
from .goldh5file import GoldH5File
from .globals import OPEN_FILES, PLOT_MANAGERS, CFG, USER_DIR
from .fitutils import FitObj, FitResult, Unc, sine_fun, decaying_cosine
from .plotting import PlotManager
from .session import save_session, load_session, list_sessions, clear_history
from .quickplot import quickplot
from . import h5utils
from . import goldh5file
from . import fitutils
from . import globals
from . import plotting
from . import series
from . import session
from . import quickplot as quickplot_module
from .cli import main


def help_repl():
    """Print the h5repl quick reference."""
    print("""
==========================================================================
                       h5repl  quick reference
==========================================================================

-- Files ------------------------------------------------------------------
  h5open(103550)                  open file by RID (searches config dirs)
  h5open(103550, nickname='rabi') open under custom name
  h5print(103550)                 explore file structure
  h5print(103550, start_root='datasets/scan')   show subtree
  get_dataset(103550, 'duration') read a dataset by name (recursive search)
  h5close(103550)                 close one file
  h5close_all()                   close all files

-- Plotting ---------------------------------------------------------------
  quickplot(103550)               auto-plot from file: detects PMTs & x-axis
  quickplot(103550, xscale=1e6, xunit='us')     rescale x at creation time
  quickplot(103550, pmt=0)        plot only PMT 0
  quickplot(103550, pmt='all')    plot all PMT channels

-- PlotManager (pm1, pm2, ...) -------------------------------------------
  pm1.title  = 'Rabi flop'        set title
  pm1.xlabel = 'duration (us)'    set axis labels
  pm1.grid   = True               toggle grid
  pm1.xlim   = (0, 120)           set axis limits
  pm1.xscale = 1e6                rescale all x data (triggers full replot)
  pm1.xunit  = 'us'               update unit in xlabel (auto-rebuilds label)
  pm1.legend()                    show legend (auto-labels unlabeled series)
  pm1.autoscale()                 reset xlim/ylim to auto
  pm1.clear()                     remove all series and reset to defaults
  pm1.ax / pm1.fig                escape hatch to raw matplotlib objects

-- Series (pm1.pmt0, pm1.s1, ...) ----------------------------------------
  pm1.pmt0.color      = 'red'     change color (redraws immediately)
  pm1.pmt0.linestyle  = '--'      line style (None = markers only)
  pm1.pmt0.marker     = 's'       marker shape
  pm1.pmt0.markersize = 8         marker size
  pm1.pmt0.alpha      = 0.5       transparency
  pm1.pmt0.label      = 'data'    update legend entry
  pm1.pmt0.visible    = False     hide/show series
  pm1.add(x, y, yerr=e, label='ref', color='gray')   add a new series
  pm1.remove_series('pmt0')       remove a named series

-- Fitting ----------------------------------------------------------------
  fit = FitObj(sine_fun)         create a fit object
  fit.p0.amp    = 0.4             set initial guess
  fit.p0.freq   = 1.0
  fit.bounds.amp = (0, 1)         set bounds (optional)
  fit.fix(offset=0.5)             hold a parameter constant
  result = pm1.pmt0.run_fit(fit)  fit and attach to series (auto-replots)
  print(result)                   show all params with uncertainties
  result.amp                      access a param as Unc
  result.amp.a / result.amp.s     float value / std dev

  Built-in functions:
    sine_fun(x, amp, freq, phi, offset)
    decaying_cosine(x, amp, omega, phi, tau, offset)

-- Sessions ---------------------------------------------------------------
  save_session(my_session)        save current REPL history to a session
  load_session(my_session)        replay a saved session
  load_session(demo)              interactive tutorial  <- start here
  list_sessions()                 show all saved sessions
  clear_history()                 wipe the current session log

-- Tips -------------------------------------------------------------------
  * Tab-completion works for everything, including pm.pmt0.<TAB>
  * Typing a function name alone (e.g. quickplot) prints its docstring
  * Closing a plot window auto-removes its PlotManager
  * open(103550) is silently rewritten to h5open(103550)
""")


__all__ = [
    # h5 utilities
    "h5open",
    "get_dataset",
    "h5print",
    "h5close",
    "h5close_all",
    "GoldH5File",
    "OPEN_FILES",
    "PLOT_MANAGERS",
    "CFG",
    "USER_DIR",
    # fitting
    "FitObj",
    "FitResult",
    "Unc",
    "sine_fun",
    "decaying_cosine",
    # plotting
    "PlotManager",
    # session management
    "save_session",
    "load_session",
    "list_sessions",
    "clear_history",
    # quick plotting
    "quickplot",
    # help
    "help_repl",
    # submodules (for advanced use)
    "h5utils",
    "goldh5file",
    "fitutils",
    "globals",
    "plotting",
    "series",
    "session",
    "quickplot_module",
]
