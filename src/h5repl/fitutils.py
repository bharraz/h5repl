import inspect
import numpy as np
from math import floor, log10
from scipy.optimize import curve_fit


# -- Uncertainty arithmetic ----------------------------------------------------

def format_unc(a, s):
    if s <= 0 or np.isnan(s):
        return '%f' % a
    sci = (s >= 100) or max(abs(a), s) < .1
    try:
        la = int(floor(log10(abs(a)) / 3) * 3)
    except Exception:
        la = 0
    ls = int(floor(log10(s)))
    fs = floor(s * 10**(1 - ls))
    if sci:
        fa = a * 10**-la
        dl = la - ls + 1
    else:
        fa = a
        dl = 1 - ls
    dl = dl if dl > 0 else 0
    ss = '%.0f' % fs
    if sci:
        return ('%.' + ('%d' % dl) + 'f(%s) * 1e%d') % (fa, ss, la)
    else:
        return ('%.' + ('%d' % dl) + 'f(%s)') % (fa, ss)


class Unc:
    def __init__(self, a, s):
        self.a = float(a)
        self.s = float(s)

    @property
    def err(self):
        return self.s

    def __str__(self):
        return format_unc(self.a, self.s)

    def __repr__(self):
        return format_unc(self.a, self.s)

    def __float__(self):
        return self.a

    def _coerce(self, other):
        if isinstance(other, Unc):
            return other.a, other.s
        return float(other), 0.0

    def __mul__(self, other):
        a2, s2 = self._coerce(other)
        a = self.a * a2
        return Unc(a, abs(a) * np.sqrt((self.s/self.a)**2 + (s2/a2)**2) if a2 != 0 else 0)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        a2, s2 = self._coerce(other)
        a = self.a / a2
        return Unc(a, abs(a) * np.sqrt((self.s/self.a)**2 + (s2/a2)**2) if a2 != 0 else 0)

    def __rtruediv__(self, other):
        a2, s2 = self._coerce(other)
        a = a2 / self.a
        return Unc(a, abs(a) * np.sqrt((s2/a2)**2 + (self.s/self.a)**2) if a2 != 0 else 0)

    def __add__(self, other):
        a2, s2 = self._coerce(other)
        return Unc(self.a + a2, np.sqrt(self.s**2 + s2**2))

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        a2, s2 = self._coerce(other)
        return Unc(self.a - a2, np.sqrt(self.s**2 + s2**2))

    def __rsub__(self, other):
        a2, s2 = self._coerce(other)
        return Unc(a2 - self.a, np.sqrt(self.s**2 + s2**2))


# -- Fit result ----------------------------------------------------------------

class FitResult:
    """
    Holds the result of a curve fit. Parameters are accessible as attributes.
    e.g. result.amp, result.tau - each is an Unc with .a and .s
    """
    def __init__(self, fn, param_names, popt, pcov):
        self.fn = fn
        self.param_names = param_names
        self.params = {
            name: Unc(val, np.sqrt(pcov[i, i]))
            for i, (name, val) in enumerate(zip(param_names, popt))
        }
        self.popt = popt
        self.pcov = pcov
        self.xs = None
        self.ys = None
        self.ys_max = None
        self.ys_min = None

    def __getattr__(self, name):
        # Allow result.amp instead of result.params["amp"]
        if name in self.__dict__.get('params', {}):
            return self.params[name]
        raise AttributeError(f"FitResult has no parameter '{name}'")

    def __repr__(self):
        lines = []
        max_name = max(len(n) for n in self.param_names)
        for name, unc in self.params.items():
            lines.append(f"  {name:<{max_name}} : {unc}")
        return "FitResult:\n" + "\n".join(lines)


# -- Fit object ----------------------------------------------------------------

class FitObj:
    """
    Wraps a fit function for easy parameter management and curve fitting.
    Introspects the function signature to expose parameters by name.
    All parameters except the first (x) are treated as fit parameters.

    Args:
        fn : fit function of the form f(x, param1, param2, ...)

    Attributes:
        p0      : dot-accessible initial guesses.  fit.p0.amp = 1.0
        bounds  : dot-accessible (lower, upper) bounds.  fit.bounds.tau = (0, np.inf)
        result  : FitResult after a successful fit, None otherwise.

    Example:
        fit = FitObj(decay_sine_fit)

        fit.p0.amp = 1.0
        fit.p0.tau = 50e-6
        fit.bounds.tau = (0, np.inf)
        fit.fix(background=0.0, high=1.0)   # hold these constant

        result = fit.fit(x, y)
        print(result)           # pretty table of all fitted params with uncertainties
        print(result.amp)       # Unc object: prints as "1.234(5)"
        print(result.amp.a)     # float: 1.234
        print(result.amp.s)     # uncertainty: 0.005

        fit.unfix("background") # free a previously fixed parameter
    """

    class _ParamProxy:
        """Dot-accessible dict for p0 and bounds."""
        def __init__(self, names):
            object.__setattr__(self, '_data', {n: None for n in names})

        def __setattr__(self, name, value):
            if name in object.__getattribute__(self, '_data'):
                object.__getattribute__(self, '_data')[name] = value
            else:
                raise AttributeError(f"Unknown parameter '{name}'")

        def __getattr__(self, name):
            data = object.__getattribute__(self, '_data')
            if name in data:
                return data[name]
            raise AttributeError(f"Unknown parameter '{name}'")

        def __repr__(self):
            return repr(object.__getattribute__(self, '_data'))

    def __init__(self, fn):
        self.fn = fn
        sig = inspect.signature(fn)
        self.param_names = list(sig.parameters.keys())[1:]
        self.p0 = self._ParamProxy(self.param_names)
        self.bounds = self._ParamProxy(self.param_names)
        self.constants = {}
        self.result = None

    def fix(self, **kwargs):
        """Fix parameters to constant values, e.g. fit.fix(tau=50e-6, background=0)"""
        for k, v in kwargs.items():
            if k not in self.param_names:
                raise ValueError(f"Unknown parameter '{k}'")
            self.constants[k] = v

    def unfix(self, *args):
        """Unfix previously fixed parameters so they are fitted again."""
        for k in args:
            self.constants.pop(k, None)

    def fit(self, x, y, **kwargs):
        """
        Run the fit against x, y. Returns a FitResult and stores it as self.result.
        Any extra kwargs are passed directly to scipy.optimize.curve_fit.
        """
        popt, pcov = curve_fit(
            self._wrapped_fn(), x, y,
            p0=self._resolve_p0(),
            bounds=self._resolve_bounds(),
            maxfev=10000,
            **kwargs
        )
        self.result = FitResult(self._wrapped_fn(), self._free_params(), popt, pcov)
        self.result.xs = np.linspace(np.min(x), np.max(x), 500)
        self.result.ys = self._wrapped_fn()(self.result.xs, *popt)
        perr = np.sqrt(np.diag(pcov))
        self.result.ys_max = self._wrapped_fn()(self.result.xs, *(popt + perr))
        self.result.ys_min = self._wrapped_fn()(self.result.xs, *(popt - perr))
        return self.result

    def _free_params(self):
        return [n for n in self.param_names if n not in self.constants]

    def _resolve_p0(self):
        data = object.__getattribute__(self.p0, '_data')
        return [data[n] if data[n] is not None else 1.0 for n in self._free_params()]

    def _resolve_bounds(self):
        data = object.__getattribute__(self.bounds, '_data')
        lower, upper = [], []
        for n in self._free_params():
            b = data[n]
            if b is None:
                lower.append(-np.inf)
                upper.append(np.inf)
            else:
                lower.append(b[0])
                upper.append(b[1])
        return (lower, upper)

    def _wrapped_fn(self):
        """Returns a function over only free parameters, with constants filled in."""
        free = set(self._free_params())
        constants = self.constants
        fn = self.fn
        all_params = self.param_names
        def wrapper(x, *args):
            free_iter = iter(args)
            kwargs = {n: (next(free_iter) if n in free else constants[n]) for n in all_params}
            return fn(x, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper

    def __repr__(self):
        lines = [f"FitObj({self.fn.__name__})"]
        max_name = max(len(n) for n in self.param_names)
        data_p0     = object.__getattribute__(self.p0,     '_data')
        data_bounds = object.__getattribute__(self.bounds, '_data')
        for n in self.param_names:
            if n in self.constants:
                lines.append(f"  {n:<{max_name}} : fixed={self.constants[n]}")
                continue
            p = data_p0[n]
            b = data_bounds[n]
            p_str = f"p0={p}" if p is not None else "p0=auto"
            b_str = f"bounds={b}" if b is not None else "bounds=(-inf, inf)"
            lines.append(f"  {n:<{max_name}} : {p_str}, {b_str}")
        if self.result:
            lines.append(repr(self.result))
        return "\n".join(lines)


############################
# Built-in fitting functions
############################

# All functions have signature f(x, param1, param2, ...) and work directly with FitObj.
# Parameter order convention: shape params first, then position (center/offset/delay), then amplitude, then width/decay.

# -- general curves -----------------------------------------------------------

def linear(x, slope, intercept):
    """slope * x + intercept"""
    return slope * x + intercept


def quadratic(x, scale, center, offset):
    """offset + scale * (x - center)^2    (scale < 0 gives inverted parabola)"""
    return offset + scale * (x - center) ** 2


def exp_decay(x, floor, amp, tau):
    """floor + amp * exp(-x / tau)"""
    return floor + amp * np.exp(-x / tau)


# -- peaks --------------------------------------------------------------------

def lorentzian(x, center, floor, amp, fwhm):
    """Lorentzian: floor + amp * (fwhm/2)^2 / ((x - center)^2 + (fwhm/2)^2)"""
    hwhm2 = (fwhm / 2) ** 2
    return floor + amp * hwhm2 / ((x - center) ** 2 + hwhm2)


def gaussian(x, center, floor, amp, fwhm):
    """Gaussian parameterized by FWHM: floor + amp * exp(-(x-center)^2 / (2*sigma^2))
    sigma = fwhm / (2*sqrt(2*ln2)) ~ fwhm / 2.355"""
    sigma = fwhm / (2 * np.sqrt(2 * np.log(2)))
    return floor + amp * np.exp(-(x - center) ** 2 / (2 * sigma ** 2))


# -- Rabi oscillations --------------------------------------------------------

def sine_fun(x, amp, freq, phi, offset):
    """amp * sin(2*pi*freq*x + phi) + offset    (freq in Hz if x in seconds)"""
    return amp * np.sin(2 * np.pi * freq * x + phi) + offset


def rabi_flop(x, amp, omega, offset):
    """Rabi population oscillation: offset + amp * sin(omega*x / 2)^2
    pi_time = pi / omega;  amp is the full population swing"""
    return offset + amp * np.sin(omega * x / 2) ** 2


def decaying_cosine(x, amp, omega, phi, tau, offset):
    """Damped oscillation: amp * exp(-x/tau) * cos(omega*x + phi) + offset"""
    return amp * np.exp(-x / tau) * np.cos(omega * x + phi) + offset


def rabi_spectroscopy(x, pulse_duration, scaling, floor, omega, center_freq):
    """Generalized Rabi lineshape for frequency spectroscopy (fixed pulse time).
    x and center_freq in Hz, omega in rad/s, pulse_duration in seconds.
    Fix pulse_duration before fitting:  fit.fix(pulse_duration=50e-6)"""
    omega2   = omega ** 2
    omegaG2  = (2 * np.pi * (x - center_freq)) ** 2 + omega2   # generalized Rabi freq^2
    return scaling * omega2 / omegaG2 * np.sin(np.sqrt(omegaG2) * pulse_duration / 2) ** 2 + floor


# -- Ramsey -------------------------------------------------------------------

def ramsey_phase(x, amp, offset, delay):
    """Ramsey fringe vs phase (x in turns 0-1): offset + amp * cos(2*pi*(x - delay))
    delay is the phase offset in turns"""
    return offset + amp * np.cos(2 * np.pi * (x - delay))


def ramsey_time(x, amp, omega, offset, delay, tau):
    """Ramsey fringe vs time with exponential decay:
    offset + amp * cos(omega*(x - delay)) * exp(-(x - delay) / tau)"""
    dt = x - delay
    return offset + amp * np.cos(omega * dt) * np.exp(-dt / tau)