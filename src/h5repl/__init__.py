# h5repl package init

from .h5utils import h5open, get_dataset, h5print, h5close, h5close_all
from .goldh5file import GoldH5File
from .globals import OPEN_FILES, CFG
from .fitutils import FitObj, FitResult, Unc
from .plotting import PlotManager, Series
from . import series as file_series

from . import h5utils
from . import goldh5file
from . import fitutils
from . import globals
from . import plotting
from . import series
from . import indexer
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
    "CFG",
    # fitting
    "FitObj",
    "FitResult",
    "Unc",
    # plotting
    "PlotManager",
    "Series",
    # submodules (for advanced use)
    "h5utils",
    "goldh5file",
    "fitutils",
    "globals",
    "plotting",
    "series",
    "indexer",
]
