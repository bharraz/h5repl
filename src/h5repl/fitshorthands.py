"""
Fit shorthand functions for common Gold System experiment types.

Each function:
  - accepts a Series, a file ID, or a GoldH5File (auto-selects first active PMT)
  - reads series.x / series.y (and .yerr if present)
  - auto-guesses p0 from the data, reproducing the logic in the system's analysis code
  - accepts keyword overrides for any individual p0 value
  - accepts fix= dict to hold any parameter constant during the fit
  - sets the fit line to dotted (':'), same color as the series
  - prints the FitResult table (param name, value +/- uncertainty)
  - attaches the result to series.fit (triggers replot)
  - returns the FitResult for downstream use

Usage:
    result = fit_rabi(pm1.pmt0)
    result = fit_rabi(166078)                       # auto-picks first active PMT
    result = fit_rabi(pm1.pmt0, omega=np.pi * 2e4)  # override one guess
    result = fit_rabi(pm1.pmt0, fix={'offset': 0.0}) # hold offset fixed at 0
    result.omega          # Unc: prints "6.28(5) * 1e4"
    result.omega.a        # float value
    result.omega.s        # uncertainty
    pm1.title = f"Rabi flop | pi_time = {np.pi / result.omega.a * 1e6:.2f} us"

Show parameters for any shorthand:
    fit_rabi;             # prints docstring listing all params
"""

import numpy as np
from .fitutils import (FitObj,
                       linear, quadratic, exp_decay,
                       lorentzian, gaussian,
                       rabi_flop, decaying_cosine, rabi_spectroscopy,
                       ramsey_phase, ramsey_time)


# -- helpers -------------------------------------------------------------------

def _coerce_series(arg):
    """Accept a Series, file ID (int/str), or GoldH5File; return a Series.
    When given a file, uses the first active PMT (or PMT 0 as fallback).
    """
    from .series import Series
    if isinstance(arg, Series):
        return arg

    from . import globals as _g
    from .goldh5file import GoldH5File

    if isinstance(arg, GoldH5File):
        f = arg
    else:
        key = str(arg)
        f = _g.OPEN_FILES.get(key)
        if f is None:
            raise ValueError(f"No open file '{key}'. Call h5open({arg!r}) first.")

    pmts = getattr(f, 'active_pmts', [])
    pmt_idx = pmts[0] if pmts else 0

    try:
        x = object.__getattribute__(f, '_scan_x')
    except AttributeError:
        x = None

    y    = np.asarray(f[f'pops_{pmt_idx}'][()])
    yerr = np.asarray(f[f'errs_{pmt_idx}'][()])
    if x is None:
        x = np.arange(len(y))
    return Series(x, y, yerr=yerr, label=f'pmt{pmt_idx}')


def _first_peak_time(x, y, inversed=False):
    """
    Estimate the x-position of the first local maximum in the data.

    For inversed=False (data starts near its maximum): scan for the first descent,
    return the x at the peak just before it. Fallback: x at argmax.

    For inversed=True (data starts near its minimum, e.g. a sine starting at 0):
    wait for the initial rise to complete, then return the x at the first local
    maximum (first descent after the initial ascent). Fallback: x at argmax.
    """
    sorted_xy = sorted(zip(x, y))
    ys = [v for _, v in sorted_xy]
    n = len(sorted_xy)

    if not inversed:
        # data starts near peak — find first descent after any initial flat
        fallback_idx = int(np.argmax(ys))
        for i in range(2, n):
            y0, y1, y2 = ys[i-2], ys[i-1], ys[i]
            if y0 > y1 and y1 > y2:          # strict descent
                return sorted_xy[i-2][0]
        return sorted_xy[fallback_idx][0]
    else:
        # data starts near minimum — find first local maximum (peak after initial rise)
        ascending = False
        for i in range(1, n):
            if ys[i] > ys[i-1]:
                ascending = True
            if ascending and (i == n - 1 or ys[i] >= ys[i+1]):
                return sorted_xy[i][0]        # x at the first peak
        return sorted_xy[int(np.argmax(ys))][0]


def _attach_style(series):
    """Set dotted fit line without triggering an extra replot."""
    object.__setattr__(series, 'fit_linestyle', ':')


# -- shorthand fit functions ---------------------------------------------------

def fit_rabi(series, *, amp=None, omega=None, offset=None, fix=None):
    """Fit a Rabi oscillation (rabi_flop) with auto-guessed p0.

    Model: offset + amp * sin(omega * x / 2)^2
      pi_time = pi / omega

    Parameters:
      amp    -- full population swing (max - min of data)
      omega  -- Rabi frequency in rad / [x-unit]
      offset -- baseline (minimum population)
      fix    -- dict of params to hold constant, e.g. fix={'offset': 0.0}

    Override any guess:
      result = fit_rabi(pm1.pmt0, omega=np.pi * 2e4)
      result = fit_rabi(pm1.pmt0, fix={'offset': 0.0})

    Result access (all Unc objects with .a and .s):
      result.amp, result.omega, result.offset
      np.pi / result.omega.a          -- pi-time as a float
      f"omega = {result.omega}"       -- formatted with uncertainty
    """
    series = _coerce_series(series)
    x, y = series.x, series.y

    _offset = float(np.min(y))               if offset is None else offset
    _amp    = float(np.max(y) - np.min(y))  if amp    is None else amp

    if omega is None:
        pi_time = _first_peak_time(x, y)
        _omega  = float(np.pi / pi_time) if pi_time > 0 else 1.0
    else:
        _omega = float(omega)

    _x_range   = float(np.max(x) - np.min(x)) or 1.0
    _omega_min = 2 * np.pi / _x_range * 1e-3   # << 1 period across the full x range

    fit = FitObj(rabi_flop)
    fit.p0.amp    = _amp
    fit.p0.omega  = _omega
    fit.p0.offset = _offset
    fit.bounds.amp   = (0, 1.5 * abs(_amp) + 1e-12)
    fit.bounds.omega = (_omega_min, np.inf)
    if fix:
        fit.fix(**fix)

    _attach_style(series)
    return series.run_fit(fit)


def fit_decaying_cosine(series, *, amp=None, omega=None, phi=None, tau=None,
                        offset=None, fix=None):
    """Fit a decaying cosine oscillation (decaying_cosine) with auto-guessed p0.

    Model: amp * exp(-x / tau) * cos(omega * x + phi) + offset
      phi = 0  -> starts at maximum
      phi = pi -> starts at minimum

    Parameters:
      amp    -- initial oscillation half-amplitude
      omega  -- oscillation angular frequency in rad / [x-unit]
      phi    -- initial phase in radians
      tau    -- decay time constant
      offset -- asymptotic baseline
      fix    -- dict of params to hold constant, e.g. fix={'phi': 0.0}

    Override any guess:
      result = fit_decaying_cosine(pm1.pmt0, tau=50e-6)
      result = fit_decaying_cosine(pm1.pmt0, fix={'phi': 0.0})

    Result access:
      result.amp, result.omega, result.phi, result.tau, result.offset
      f"tau = {result.tau}"
    """
    series = _coerce_series(series)
    x, y = series.x, series.y

    _offset = float((np.max(y) + np.min(y)) / 2) if offset is None else offset
    _amp    = float((np.max(y) - np.min(y)) / 2) if amp    is None else amp

    if omega is None:
        inversed = float(y[0]) < float(_offset)   # start below mean -> inverted cosine
        pi_time  = _first_peak_time(x, y, inversed=inversed)
        _omega   = float(np.pi / pi_time) if pi_time > 0 else 1.0
        _phi     = float(np.pi) if (phi is None and inversed) else (0.0 if phi is None else float(phi))
    else:
        _omega  = float(omega)
        pi_time = float(np.pi / _omega)
        _phi    = 0.0 if phi is None else float(phi)

    _x_range = float(np.max(x) - np.min(x)) or 1.0
    _tau_min = _x_range * 1e-6   # keep tau strictly positive to avoid gradient singularity
    if tau is None:
        _tau = max(float(pi_time * 50), _x_range * 0.5) if pi_time > 0 else _x_range * 0.5
    else:
        _tau = max(float(tau), _tau_min)

    fit = FitObj(decaying_cosine)
    fit.p0.amp    = _amp
    fit.p0.omega  = _omega
    fit.p0.phi    = _phi
    fit.p0.tau    = _tau
    fit.p0.offset = _offset
    fit.bounds.tau = (_tau_min, np.inf)
    if fix:
        fit.fix(**fix)

    _attach_style(series)
    return series.run_fit(fit)


def fit_lorentzian(series, *, center=None, floor=None, amp=None, fwhm=None, fix=None):
    """Fit a Lorentzian peak or dip (lorentzian) with auto-guessed p0.

    Model: floor + amp * (fwhm/2)^2 / ((x - center)^2 + (fwhm/2)^2)
      amp < 0 for a dip (absorption feature)

    Parameters:
      center -- x position of peak / dip
      floor  -- baseline outside the feature
      amp    -- peak / dip amplitude (negative for a dip)
      fwhm   -- full-width at half-maximum in x-units
      fix    -- dict of params to hold constant, e.g. fix={'floor': 0.0}

    Override any guess:
      result = fit_lorentzian(pm1.pmt0, center=6.3e9, fwhm=1e6)

    Result access:
      result.center, result.floor, result.amp, result.fwhm
      f"linewidth = {result.fwhm}"
    """
    series = _coerce_series(series)
    x, y = series.x, series.y

    above = float(np.max(y)) - float(np.median(y))
    below = float(np.median(y)) - float(np.min(y))
    is_dip   = below > above
    peak_idx = int(np.argmin(y) if is_dip else np.argmax(y))

    _center = float(x[peak_idx])                                           if center is None else float(center)
    _floor  = float(np.min(y))                                             if floor  is None else float(floor)
    _amp    = float(np.max(y) - np.min(y)) * (-1.0 if is_dip else 1.0)   if amp    is None else float(amp)
    _fwhm   = float((np.max(x) - np.min(x)) / 4)                          if fwhm   is None else float(fwhm)

    fit = FitObj(lorentzian)
    fit.p0.center = _center
    fit.p0.floor  = _floor
    fit.p0.amp    = _amp
    fit.p0.fwhm   = _fwhm
    fit.bounds.fwhm = (0, np.inf)
    if fix:
        fit.fix(**fix)

    _attach_style(series)
    return series.run_fit(fit)


def fit_gaussian(series, *, center=None, floor=None, amp=None, fwhm=None, fix=None):
    """Fit a Gaussian peak or dip (gaussian) with auto-guessed p0.

    Model: floor + amp * exp(-(x - center)^2 / (2 * sigma^2))
      sigma = fwhm / (2 * sqrt(2 * ln2))  ~  fwhm / 2.355
      amp < 0 for a dip (absorption feature)

    Parameters:
      center -- x position of peak / dip
      floor  -- baseline outside the feature
      amp    -- peak / dip amplitude (negative for a dip)
      fwhm   -- full-width at half-maximum in x-units
      fix    -- dict of params to hold constant, e.g. fix={'floor': 0.0}

    Override any guess:
      result = fit_gaussian(pm1.pmt0, center=6.3e9)

    Result access:
      result.center, result.floor, result.amp, result.fwhm
      f"center = {result.center},  fwhm = {result.fwhm}"
    """
    series = _coerce_series(series)
    x, y = series.x, series.y

    above = float(np.max(y)) - float(np.median(y))
    below = float(np.median(y)) - float(np.min(y))
    is_dip   = below > above
    peak_idx = int(np.argmin(y) if is_dip else np.argmax(y))

    _center = float(x[peak_idx])                                           if center is None else float(center)
    _floor  = float(np.min(y))                                             if floor  is None else float(floor)
    _amp    = float(np.max(y) - np.min(y)) * (-1.0 if is_dip else 1.0)   if amp    is None else float(amp)
    _fwhm   = float((np.max(x) - np.min(x)) / 4)                          if fwhm   is None else float(fwhm)

    fit = FitObj(gaussian)
    fit.p0.center = _center
    fit.p0.floor  = _floor
    fit.p0.amp    = _amp
    fit.p0.fwhm   = _fwhm
    fit.bounds.fwhm = (0, np.inf)
    if fix:
        fit.fix(**fix)

    _attach_style(series)
    return series.run_fit(fit)


def fit_exp_decay(series, *, floor=None, amp=None, tau=None, fix=None):
    """Fit an exponential decay (exp_decay) with auto-guessed p0.

    Model: floor + amp * exp(-x / tau)

    Parameters:
      floor -- asymptotic baseline (value as x -> inf)
      amp   -- initial amplitude above the floor
      tau   -- decay time constant in x-units
      fix   -- dict of params to hold constant, e.g. fix={'floor': 0.0}

    Override any guess:
      result = fit_exp_decay(pm1.pmt0, floor=0.05)

    Result access:
      result.floor, result.amp, result.tau
      f"T1 = {result.tau}"
    """
    series = _coerce_series(series)
    x, y = series.x, series.y

    _floor = float(np.min(y))              if floor is None else float(floor)
    _amp   = float(np.max(y) - np.min(y)) if amp   is None else float(amp)
    _x_range = float(np.max(x) - np.min(x)) or 1.0
    _tau_min = _x_range * 1e-6
    _tau = max(float(np.max(x) / 2), _tau_min) if tau is None else max(float(tau), _tau_min)

    fit = FitObj(exp_decay)
    fit.p0.floor = _floor
    fit.p0.amp   = _amp
    fit.p0.tau   = _tau
    fit.bounds.tau = (_tau_min, np.inf)
    if fix:
        fit.fix(**fix)

    _attach_style(series)
    return series.run_fit(fit)


def fit_ramsey_phase(series, *, amp=None, offset=None, delay=None, fix=None):
    """Fit Ramsey fringes vs scan phase (ramsey_phase) with auto-guessed p0.

    Model: offset + amp * cos(2*pi*(x - delay))
      x is in turns (0 to 1 = full phase cycle)

    Parameters:
      amp    -- fringe half-amplitude
      offset -- center of the fringe (mean population)
      delay  -- phase offset in turns (shift of the cosine zero)
      fix    -- dict of params to hold constant, e.g. fix={'delay': 0.0}

    Override any guess:
      result = fit_ramsey_phase(pm1.pmt0, delay=0.25)

    Result access:
      result.amp, result.offset, result.delay
      f"fringe delay = {result.delay}"
    """
    series = _coerce_series(series)
    x, y = series.x, series.y

    _offset = float((np.max(y) + np.min(y)) / 2) if offset is None else float(offset)
    _amp    = float((np.max(y) - np.min(y)) / 2) if amp    is None else float(amp)
    _delay  = float(x[int(np.argmin(y))])          if delay  is None else float(delay)

    fit = FitObj(ramsey_phase)
    fit.p0.amp    = _amp
    fit.p0.offset = _offset
    fit.p0.delay  = _delay
    if fix:
        fit.fix(**fix)

    _attach_style(series)
    return series.run_fit(fit)


def fit_ramsey_time(series, *, amp=None, omega=None, offset=None, delay=None,
                    tau=None, fix=None):
    """Fit Ramsey fringes vs free-evolution time (ramsey_time) with auto-guessed p0.

    Model: offset + amp * cos(omega * (x - delay)) * exp(-(x - delay) / tau)

    Parameters:
      amp    -- fringe half-amplitude
      omega  -- fringe angular frequency in rad / [x-unit]
      offset -- center of the fringe (mean population)
      delay  -- time offset (typically 0)
      tau    -- coherence decay time (T2)
      fix    -- dict of params to hold constant, e.g. fix={'delay': 0.0}

    Override any guess:
      result = fit_ramsey_time(pm1.pmt0, tau=100e-6)

    Result access:
      result.amp, result.omega, result.offset, result.delay, result.tau
      f"T2 = {result.tau}"
    """
    series = _coerce_series(series)
    x, y = series.x, series.y

    _offset = float((np.max(y) + np.min(y)) / 2) if offset is None else float(offset)
    _amp    = float((np.max(y) - np.min(y)) / 2) if amp    is None else float(amp)
    _delay  = 0.0                                  if delay  is None else float(delay)

    if omega is None:
        pi_time = _first_peak_time(x, y)
        _omega  = float(np.pi / pi_time) if pi_time > 0 else 1.0
    else:
        _omega  = float(omega)
        pi_time = float(np.pi / _omega)

    _x_range = float(np.max(x) - np.min(x)) or 1.0
    _tau_min = _x_range * 1e-6
    _tau = max(float(np.max(x) * 2), _tau_min) if tau is None else max(float(tau), _tau_min)

    _omega_min = 2 * np.pi / _x_range * 1e-3

    fit = FitObj(ramsey_time)
    fit.p0.amp    = _amp
    fit.p0.omega  = _omega
    fit.p0.offset = _offset
    fit.p0.delay  = _delay
    fit.p0.tau    = _tau
    fit.bounds.omega = (_omega_min, np.inf)
    fit.bounds.tau   = (_tau_min, np.inf)
    if fix:
        fit.fix(**fix)

    _attach_style(series)
    return series.run_fit(fit)


_DURATION_KEYS = ('pulse_duration', 'duration', 'scan_duration', 't_pulse')


def _read_pulse_duration(series):
    """Try to read pulse_duration from the HDF5 file that produced this series."""
    file_id = object.__getattribute__(series, '__dict__').get('_file_id')
    if file_id is None:
        return None
    from . import globals as _g
    f = _g.OPEN_FILES.get(file_id)
    if f is None:
        return None
    # search params/ (expid arguments) first, then datasets/scan
    search_roots = ['params', 'datasets/scan']
    for root in search_roots:
        for key in _DURATION_KEYS:
            path = f'{root}/{key}'
            try:
                val = float(f[path][()])
                print(f"  pulse_duration = {val} s  (from {path})")
                return val
            except (KeyError, TypeError, ValueError):
                pass
    return None


def fit_spectroscopy(series, pulse_duration=None, *, scaling=None, floor=None,
                     omega=None, center_freq=None, fix=None):
    """Fit the generalized Rabi lineshape for spectroscopy (rabi_spectroscopy).

    pulse_duration is held fixed during the fit. If omitted it is read from the
    HDF5 file that produced the series (looks for pulse_duration / duration in
    params/ and datasets/scan).

    Model: scaling * omega^2 / omegaG^2 * sin(sqrt(omegaG^2) * t / 2)^2 + floor
      where omegaG^2 = (2*pi*(x - center_freq))^2 + omega^2
      x and center_freq in Hz, omega in rad/s, pulse_duration in seconds

    Parameters:
      pulse_duration -- fixed pulse time in seconds (auto-read from file if omitted)
      scaling        -- peak amplitude (max - min)
      floor          -- baseline
      omega          -- on-resonance Rabi frequency in rad/s
      center_freq    -- resonance frequency in Hz
      fix            -- dict of additional params to hold constant

    Examples:
      result = fit_spectroscopy(pm1.pmt0)                         # reads t from file
      result = fit_spectroscopy(pm1.pmt0, 50e-6)                  # explicit
      result = fit_spectroscopy(pm1.pmt0, center_freq=6.834e9)    # file + override

    Result access:
      result.scaling, result.floor, result.omega, result.center_freq
      f"resonance = {result.center_freq}"
    """
    series = _coerce_series(series)

    if pulse_duration is None:
        pulse_duration = _read_pulse_duration(series)
    if pulse_duration is None:
        raise ValueError(
            "pulse_duration not found in file. Pass it explicitly: "
            "fit_spectroscopy(series, 50e-6)"
        )
    pulse_duration = float(pulse_duration)

    x, y = series.x, series.y

    above = float(np.max(y)) - float(np.median(y))
    below = float(np.median(y)) - float(np.min(y))
    is_dip   = below > above
    peak_idx = int(np.argmin(y) if is_dip else np.argmax(y))

    _center_freq = float(x[peak_idx])            if center_freq is None else float(center_freq)
    _floor       = float(np.min(y))              if floor       is None else float(floor)
    _scaling     = float(np.max(y) - np.min(y))  if scaling     is None else float(scaling)
    _omega       = float(np.pi / pulse_duration)  if omega       is None else float(omega)

    fit = FitObj(rabi_spectroscopy)
    fit.fix(pulse_duration=pulse_duration)
    fit.p0.scaling     = _scaling
    fit.p0.floor       = _floor
    fit.p0.omega       = _omega
    fit.p0.center_freq = _center_freq
    fit.bounds.omega   = (0, np.inf)
    if fix:
        fit.fix(**fix)

    _attach_style(series)
    return series.run_fit(fit)


def fit_linear(series, *, slope=None, intercept=None, fix=None):
    """Fit a straight line (linear) with auto-guessed p0.

    Model: slope * x + intercept

    Parameters:
      slope     -- gradient
      intercept -- y-intercept
      fix       -- dict of params to hold constant, e.g. fix={'intercept': 0.0}

    Override any guess:
      result = fit_linear(pm1.pmt0, slope=0.0)

    Result access:
      result.slope, result.intercept
      f"slope = {result.slope}"
    """
    series = _coerce_series(series)
    x, y = series.x, series.y

    dx = float(x[-1] - x[0]) or 1.0
    _slope     = float((y[-1] - y[0]) / dx)              if slope     is None else float(slope)
    _intercept = float(np.mean(y) - _slope * np.mean(x)) if intercept is None else float(intercept)

    fit = FitObj(linear)
    fit.p0.slope     = _slope
    fit.p0.intercept = _intercept
    if fix:
        fit.fix(**fix)

    _attach_style(series)
    return series.run_fit(fit)


def fit_quadratic(series, *, scale=None, center=None, offset=None, fix=None):
    """Fit a parabola (quadratic) with auto-guessed p0.

    Model: offset + scale * (x - center)^2
      scale > 0 -> valley (minimum),  scale < 0 -> peak (maximum)

    Parameters:
      scale  -- curvature coefficient
      center -- x position of the vertex
      offset -- y value at the vertex
      fix    -- dict of params to hold constant, e.g. fix={'center': 0.0}

    Override any guess:
      result = fit_quadratic(pm1.pmt0, center=0.5)

    Result access:
      result.scale, result.center, result.offset
      f"vertex at x = {result.center}"
    """
    series = _coerce_series(series)
    x, y = series.x, series.y

    above = float(np.max(y)) - float(np.median(y))
    below = float(np.median(y)) - float(np.min(y))
    is_peak = above > below
    ext_idx = int(np.argmax(y) if is_peak else np.argmin(y))

    _center = float(x[ext_idx])  if center is None else float(center)
    _offset = float(y[ext_idx])  if offset is None else float(offset)

    if scale is None:
        dx2 = (float(np.max(x)) - float(np.min(x))) ** 2 or 1.0
        _scale = float((np.max(y) - np.min(y)) / dx2) * (-1.0 if is_peak else 1.0)
    else:
        _scale = float(scale)

    fit = FitObj(quadratic)
    fit.p0.scale  = _scale
    fit.p0.center = _center
    fit.p0.offset = _offset
    if fix:
        fit.fix(**fix)

    _attach_style(series)
    return series.run_fit(fit)
