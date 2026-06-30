"""One-liner plotting for Gold System HDF5 files."""

import json
import numpy as np
import matplotlib.pyplot as plt
import h5py

from . import globals as _globals
from .plotting import PlotManager
from .series import Series
from .fitutils import FitObj, FitResult


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_scan_info(f):
    """Returns (scan_axes, fixed_params) or (None, None) if no scan group."""
    try:
        scan_group = f['datasets/scan']
    except KeyError:
        return None, None

    scan_axes, fixed_params = {}, {}
    for k in scan_group.keys():
        if k == 'product':
            continue
        child = scan_group[k]
        if isinstance(child, h5py.Group):
            continue
        try:
            arr = child[()]
            if (hasattr(arr, '__len__')
                    and len(arr) > 1
                    and np.issubdtype(arr.dtype, np.number)):
                scan_axes[k] = arr
            else:
                fixed_params[k] = float(arr.flat[0]) if hasattr(arr, 'flat') else float(arr)
        except Exception:
            pass
    return scan_axes, fixed_params


def _infer_active_pmts(f):
    """PMT indices whose mean population exceeds 5%."""
    active = []
    for k in f.keys():
        if not k.startswith('pops_'):
            continue
        try:
            if np.mean(f[k][()]) > 0.05:
                active.append(int(k[5:]))
        except Exception:
            pass
    return sorted(active, key=abs)


_PARAM_UNIT_KEYWORDS = [
    (['detun', 'freq'], 'Hz'),
    (['duration', 'time', 'pulse', 'delay', 'wait'], 's'),
    (['attenuation', 'atten'], 'dB'),
]


def _infer_unit(name):
    """Infer physical unit from a parameter name via case-insensitive substring match."""
    n = name.lower()
    for keywords, unit in _PARAM_UNIT_KEYWORDS:
        if any(kw in n for kw in keywords):
            return unit
    return ''


def _fmt_val(v, unit=''):
    if v == 0:
        return f'0 {unit}'.strip() if unit else '0'
    av = abs(v)
    if av >= 1e6:  s = f'{v*1e-6:.4g} M'
    elif av >= 1e3:  s = f'{v*1e-3:.4g} k'
    elif av < 1e-6:  s = f'{v*1e9:.4g} n'
    elif av < 1e-3:  s = f'{v*1e6:.4g} µ'
    else:            s = f'{v:.4g} '
    return s + unit if unit else s.rstrip()


def _last_alive_manager():
    """Return the most recently created PlotManager whose figure is still open."""
    for name in reversed(list(_globals.PLOT_MANAGERS)):
        mgr = _globals.PLOT_MANAGERS[name]
        if plt.fignum_exists(mgr.fig.number):
            return name, mgr
    return None, None


# ── main function ─────────────────────────────────────────────────────────────

def quickplot(file_id, pmt=None, fit=None, title=None,
              xlabel=None, xunit=None, xscale=None,
              ylabel=None, yunit=None, yscale=None,
              add=False, fmt='o-', capsize=3, **kwargs):
    """
    Plot populations from a Gold System HDF5 file with automatic x-axis,
    active-PMT detection, and title generation. Returns the PlotManager.

    Args:
        file_id  : RID or nickname (file opened automatically if not already open).
        pmt      : int, list of ints, or 'all'. Default: auto-detect active channels.
        fit      : FitObj or FitResult to overlay as a dashed fit curve.
        title    : Override the auto-generated title.
        xlabel   : Override x-axis label (default: scan axis name [+ xunit]).
        xunit    : Unit string appended to xlabel, e.g. 'µs'.
        xscale   : Multiply x values by this factor, e.g. 1e6 for s→µs.
                   Defaults to the current manager's xscale if set, otherwise 1.0.
        ylabel   : Override y-axis label (default: 'population').
        yunit    : Unit string appended to ylabel.
        yscale   : Multiply population values by this factor.
        add      : If True, overlay on the existing figure instead of clearing.
        fmt      : errorbar format string, default 'o-'.
        capsize  : errorbar cap size in points.
        **kwargs : Passed to ax.errorbar (color, markersize, linewidth, alpha, …).

    Returns:
        PlotManager — also stored in PLOT_MANAGERS (e.g. PLOT_MANAGERS['pm1']).

    Examples:
        quickplot(103550)                    # auto-everything
        pm = quickplot(103550)               # keep a reference
        pm = quickplot(103550, xscale=1e6, xunit='µs')
        pm.title = 'Rabi flop'              # live update
        pm.series[0][0].color = 'red'
        quickplot(103551, add=True)          # overlay on same figure
    """
    file_id = str(file_id)
    if file_id not in _globals.OPEN_FILES:
        from . import h5utils
        if not h5utils.h5open(file_id):
            return None
    f = _globals.OPEN_FILES[file_id]

    # ── scan axis ─────────────────────────────────────────────────────────────
    scan_axes, fixed_params = _get_scan_info(f)
    if scan_axes is None:
        print(f"No datasets/scan in {file_id}. Use h5print({file_id}) to explore.")
        return None
    if not scan_axes:
        print(f"No varying scan axis found in {file_id}.")
        return None

    if len(scan_axes) == 1:
        x_name, x_raw = list(scan_axes.items())[0]
    else:
        names = list(scan_axes.keys())
        x_name, x_raw = names[0], scan_axes[names[0]]
        print(f"2D scan — axes: {names}. Plotting '{x_name}' only for now.")

    # ── figure: reuse last alive manager, or create new ───────────────────────
    last_name, last_mgr = _last_alive_manager()

    if last_mgr is not None:
        mgr = last_mgr
        mgr_name = last_name
        if not add:
            for sl in mgr.series:
                for s in sl:
                    object.__setattr__(s, '_manager', None)
            object.__setattr__(mgr, 'series', [[] for _ in mgr.axes])
            mgr.axes[0].cla()
    else:
        mgr_name = f"pm{len(_globals.PLOT_MANAGERS) + 1}"
        mgr = PlotManager()
        _globals.PLOT_MANAGERS[mgr_name] = mgr
        print(f"Created {mgr_name}")

    # ── scale: kwarg overrides manager default ────────────────────────────────
    eff_xscale = xscale if xscale is not None else mgr.xscale
    eff_yscale = yscale if yscale is not None else mgr.yscale
    eff_xunit  = xunit  if xunit  is not None else mgr.xunit
    eff_yunit  = yunit  if yunit  is not None else mgr.yunit

    x_data = x_raw * eff_xscale

    # ── PMT selection ─────────────────────────────────────────────────────────
    if pmt is None:
        active_pmts = _infer_active_pmts(f)
        if not active_pmts:
            print("No active PMT channels detected (mean pops < 5%). "
                  "Try quickplot(..., pmt='all') to override.")
            return mgr
        print(f"Auto-detected active PMTs: {active_pmts}")
    elif pmt == 'all':
        active_pmts = sorted(
            [int(k[5:]) for k in f.keys() if k.startswith('pops_')], key=abs)
    elif isinstance(pmt, int):
        active_pmts = [pmt]
    else:
        active_pmts = list(pmt)

    # ── title + labels ────────────────────────────────────────────────────────
    if title is None:
        try:
            expclass = json.loads(f['expid'][()].decode()).get('class_name', '?')
        except Exception:
            expclass = '?'
        try:
            rid = int(f['rid'][()])
        except Exception:
            rid = file_id
        fixed_str = '  |  '.join(
            f'{k} = {_fmt_val(v, _infer_unit(k))}' for k, v in fixed_params.items()
        )
        title = f"{expclass}  |  {rid}" + (f"  |  {fixed_str}" if fixed_str else "")

    if xlabel is None:
        xlabel = f"{x_name} ({eff_xunit})" if eff_xunit else x_name
    if ylabel is None:
        ylabel = f"population ({eff_yunit})" if eff_yunit else "population"

    # ── build series ──────────────────────────────────────────────────────────
    new_series = []
    label_kwarg = kwargs.pop('label', None)

    for pmt_idx in active_pmts:
        pops_key = f'pops_{pmt_idx}'
        errs_key = f'errs_{pmt_idx}'
        if pops_key not in f:
            print(f"Warning: {pops_key} not found, skipping.")
            continue

        y    = np.asarray(f[pops_key][()]) * eff_yscale
        yerr = np.asarray(f[errs_key][()]) * eff_yscale if errs_key in f else None

        if label_kwarg is not None:
            s_label = label_kwarg if len(active_pmts) == 1 else f"{label_kwarg} {pmt_idx}"
        else:
            s_label = f'PMT {pmt_idx}' if len(active_pmts) > 1 else None

        s = Series(x_data, y, yerr=yerr, label=s_label,
                   fit=fit if len(active_pmts) == 1 else None,
                   fmt=fmt, capsize=capsize, **kwargs)
        new_series.append(s)

    mgr.add_series_batch(new_series)

    mgr._set_disp_silent(title=title, xlabel=xlabel, ylabel=ylabel)
    mgr._apply_display()
    if len(active_pmts) > 1 or fit is not None:
        mgr.axes[0].legend()
    mgr.fig.canvas.draw()
    mgr.fig.canvas.flush_events()

    return mgr
