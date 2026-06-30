# h5repl package init

from .h5utils import h5open, get_dataset, h5print, h5close, h5close_all
from .goldh5file import GoldH5File
from .globals import OPEN_FILES, PLOT_MANAGERS, CFG, USER_DIR
from .fitutils import FitObj, FitResult, Unc
from .series import Series
from .plotting import PlotManager
from .session import save_session, load_session, list_sessions, clear_history
from .quickplot import quickplot
from . import h5utils
from . import goldh5file
from . import fitutils
from . import globals
from . import plotting
from . import series
from . import indexer
from . import session
from . import quickplot as quickplot_module
from .cli import main

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
    # plotting
    "PlotManager",
    "Series",
    # session management
    "save_session",
    "load_session",
    "list_sessions",
    "clear_history",
    # quick plotting
    "quickplot",
    # submodules (for advanced use)
    "h5utils",
    "goldh5file",
    "fitutils",
    "globals",
    "plotting",
    "series",
    "indexer",
    "session",
    "quickplot_module",
]
