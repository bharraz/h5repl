# h5repl package init

from .h5utils import h5open, get_dataset, h5print, h5close, h5close_all
from .goldh5file import GoldH5File
from .globals import OPEN_FILES, PLOT_MANAGERS, CFG, USER_DIR
from .fitutils import (FitObj, FitResult, Unc,
                       linear, quadratic, exp_decay,
                       lorentzian, gaussian,
                       sine_fun, rabi_flop, decaying_cosine, rabi_spectroscopy,
                       ramsey_phase, ramsey_time)
from .plotting import PlotManager, save_style
from .fitshorthands import (fit_rabi, fit_decaying_cosine,
                             fit_lorentzian, fit_gaussian, fit_exp_decay,
                             fit_ramsey_phase, fit_ramsey_time, fit_spectroscopy,
                             fit_linear, fit_quadratic)
from .session import save_session, load_session, list_sessions, clear_history
from .quickplot import quickplot
from . import h5utils
from . import goldh5file
from . import fitutils
from . import fitshorthands
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

  Built-in fit functions (use with FitObj):
    linear(x, slope, intercept)
    quadratic(x, scale, center, offset)
    exp_decay(x, floor, amp, tau)
    lorentzian(x, center, floor, amp, fwhm)
    gaussian(x, center, floor, amp, fwhm)
    sine_fun(x, amp, freq, phi, offset)
    rabi_flop(x, amp, omega, offset)
    decaying_cosine(x, amp, omega, phi, tau, offset)
    rabi_spectroscopy(x, pulse_duration, scaling, floor, omega, center_freq)
    ramsey_phase(x, amp, offset, delay)
    ramsey_time(x, amp, omega, offset, delay, tau)

  Fit shorthands (auto-guess p0, dotted line, returns FitResult):
    fit_rabi(series, *, amp, omega, offset)
    fit_decaying_cosine(series, *, amp, omega, phi, tau, offset)
    fit_lorentzian(series, *, center, floor, amp, fwhm)
    fit_gaussian(series, *, center, floor, amp, fwhm)
    fit_exp_decay(series, *, floor, amp, tau)
    fit_ramsey_phase(series, *, amp, offset, delay)
    fit_ramsey_time(series, *, amp, omega, offset, delay, tau)
    fit_spectroscopy(series, [pulse_duration], *, scaling, floor, omega, center_freq)
    fit_linear(series, *, slope, intercept)
    fit_quadratic(series, *, scale, center, offset)
  -> All keyword args are optional p0 overrides (None = auto-guessed from data)
  -> Type  fit_rabi;  for full docstring with usage examples

-- Sessions ---------------------------------------------------------------
  save_session(my_session)        save current REPL history to a session
  load_session(my_session)        replay a saved session
  load_session(demo)              interactive tutorial  <- start here
  list_sessions()                 show all saved sessions
  clear_history()                 wipe the current session log

-- Tips -------------------------------------------------------------------
  * Tab-completion works for everything, including pm.pmt0.<TAB>
  * Add ; to see docs for anything: quickplot;  pm1.pmt0;
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
    # fitting infrastructure
    "FitObj",
    "FitResult",
    "Unc",
    # general curves
    "linear",
    "quadratic",
    "exp_decay",
    # peaks
    "lorentzian",
    "gaussian",
    # Rabi
    "sine_fun",
    "rabi_flop",
    "decaying_cosine",
    "rabi_spectroscopy",
    # Ramsey
    "ramsey_phase",
    "ramsey_time",
    # fit shorthands
    "fit_rabi",
    "fit_decaying_cosine",
    "fit_lorentzian",
    "fit_gaussian",
    "fit_exp_decay",
    "fit_ramsey_phase",
    "fit_ramsey_time",
    "fit_spectroscopy",
    "fit_linear",
    "fit_quadratic",
    # plotting
    "PlotManager",
    "save_style",
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
