# h5repl

Interactive Python REPL for exploring, plotting, and fitting HDF5 data. Open a file, plot it, fit it, and save the session — all with tab completion and live-updating figures.

```
h5repl
```

---

## Setup

```sh
pip install -e .
```

Edit `config.toml` to point at your data directories:

```toml
user_dir = "./user"           # sessions, figures, fits

[file_directories]
data = "./data"               # add more named directories as needed
```

---

## Opening files

```python
h5open(103550)                # search configured directories for a file matching this ID
browse()                      # open a file-browser dialog instead
h5open(103550, nickname='f')  # short nickname for the rest of the session
h5print(103550)               # explore file structure (tree view)
h5print(103550, start_root='scan')            # focus on a subtree
get_dataset(103550, 'duration')               # read a dataset by name (recursive search)
h5close(103550)               # close one file
h5close_all()                 # close all files
```

`h5open`/`browse` match files by substring against the ID you pass (so integer RIDs, UUID fragments, or filename stems all work), and return a plain `h5py.File`. `get_dataset` searches recursively so you don't need the full group path.

---

## Building a Series

Unlike the file object, `Series` isn't auto-populated — build one from whatever datasets your file has:

```python
f = h5open(103550)
x = get_dataset(f, 'duration')
y = get_dataset(f, 'signal')
yerr = get_dataset(f, 'signal_err')   # optional

s = Series(x, y, yerr=yerr, label='signal')
```

### Series arithmetic

Series objects support `+`, `-`, `*`, `/`, `**`, and unary `-`. Errors propagate automatically. Addition and subtraction require matching x-axes; `*`, `/`, and `**` accept scalars only.

```python
inversion = 1 - s              # scalar - Series, same errors
combined  = s1 + s2            # errors add in quadrature
half      = combined / 2

result = fit_rabi(half)
```

### Fitting a derived quantity

```python
pm1 = PlotManager()
pm1.add_series(s1)
pm1.add_series(s2)

combined = (pm1.s1 + pm1.s2) / 2   # arithmetic → new unmanaged Series, errors propagated
pm1.add_series(combined, name='combined')
result = fit_rabi(pm1.combined)    # fit overlays automatically
```

---

## Plotting

```python
pm1 = PlotManager()               # new figure, registers as pm1, pm2, ...
pm1.add_series(s)                 # add a pre-built Series
pm1.add_series(s2, name='ref')    # with an explicit name
```

`pm1` is injected directly into the REPL namespace — you can type `pm1` right away.

### PlotManager properties

Setting any of these updates the figure immediately:

```python
pm1.title  = 'My scan'
pm1.xlabel = 'duration (us)'
pm1.ylabel = 'signal'
pm1.grid   = True
pm1.xlim   = (0, 120)
pm1.ylim   = (0, 1)
```

Rescaling triggers a full replot of all data:

```python
pm1.xscale = 1e6              # multiply all x data (e.g. s -> us)
pm1.xunit  = 'us'             # update unit in xlabel (rebuilds label automatically)
```

Legend and adding data:

```python
pm1.legend()                  # show legend; unlabeled series get their nickname
pm1.autoscale()                # reset xlim/ylim to auto
pm1.add_series(Series(x, y, label='ref', color='gray'))    # add a pre-built Series
pm1.remove_series('ref')      # remove a series by name
```

Escape hatches to raw matplotlib:

```python
pm1.ax                        # matplotlib Axes
pm1.fig                        # matplotlib Figure
```

### Subplots

`plot_grid` creates several `PlotManager`s sharing one figure. Each panel is a normal `PlotManager` — registered as `pm1`, `pm2`, ... just like a single `PlotManager()` figure, with the full API (`title`, `add_series`, fit overlays, etc). The returned `PlotGrid` is a thin convenience wrapper for whole-figure operations.

```python
grid = plot_grid(2, 2, sharex=True, sharey=True, title='Overview')

pm1.add_series(s1)            # top-left panel
pm2.add_series(s2)            # top-right panel
pm1.title = 'Panel A'
pm2.title = 'Panel B'

grid[0, 0] is pm1              # True — index by (row, col) or flat index
grid.legend()                  # one shared legend built from every panel's series
grid.export('combined.pdf')    # saves the whole figure
```

### Series properties

Each series updates the plot when you set an attribute:

```python
pm1.s1.color      = 'steelblue'
pm1.s1.alpha      = 0.7
pm1.s1.label      = 'signal'
pm1.s1.linestyle  = '--'        # None = markers only
pm1.s1.marker     = 's'
pm1.s1.markersize = 6
pm1.s1.visible    = False       # hide/show
```

Fit line style (set before or after fitting):

```python
pm1.s1.fit_color     = 'red'   # defaults to same color as series
pm1.s1.fit_linestyle = ':'     # defaults to '--'; shorthands use ':'
pm1.s1.fit_label      = 'custom legend text'  # defaults to '<label> (fit)'
```

Once a series has a fit attached, its fitted parameters are also reachable directly:

```python
pm1.s1.omega          # same as pm1.s1.fit.omega
```

### Styles

```python
pm1.style('publication')          # apply a named style preset
pm1.style(None)                   # clear style

# define a new preset and save it to config.toml
save_style('big_font', {'font.size': 16, 'lines.linewidth': 2.0})
```

### Exporting

```python
pm1.export('scan.pdf')           # saves to user/figures/
pm1.export('scan.png', dpi=600)
pm1.export()                      # uses plot title as filename
pm1.export('out.pdf', dest='/tmp')    # explicit directory
```

---

## Fitting

### Shorthands (recommended)

Each shorthand takes a `Series`, auto-guesses initial parameters from the data, fits, prints the result, overlays a dotted line, and returns a `FitResult`.

```python
result = fit_rabi(pm1.s1)
result = fit_decaying_cosine(pm1.s1)
result = fit_lorentzian(pm1.s1)
result = fit_gaussian(pm1.s1)
result = fit_exp_decay(pm1.s1)
result = fit_ramsey_phase(pm1.s1)
result = fit_ramsey_time(pm1.s1)
result = fit_spectroscopy(pm1.s1, 50e-6)   # pulse_duration must be passed or found in the file
result = fit_linear(pm1.s1)
result = fit_quadratic(pm1.s1)
```

Override any individual initial guess by keyword:

```python
result = fit_rabi(pm1.s1, omega=np.pi * 2e4)
result = fit_ramsey_time(pm1.s1, tau=100e-6)
```

Hold a parameter fixed with `fix=`:

```python
result = fit_rabi(pm1.s1, fix={'offset': 0.0})
```

Type `fit_rabi;` to see the docstring listing all parameters.

### Working with results

All fitted parameters are `Unc` objects with a value (`.a`) and uncertainty (`.s`):

```python
result.amp            # Unc — prints as "0.847(12)"
result.amp.a          # 0.847   (float)
result.amp.s          # 0.012   (1-sigma)

# use in labels and titles
pi_time_us = np.pi / result.omega.a * 1e6
pm1.title = f"Rabi flop  |  pi_time = {pi_time_us:.2f} us"
pm1.s1.label = f"data  (omega = {result.omega})"

# arithmetic propagates uncertainties
two_pi_time = np.pi / result.omega * 2   # returns Unc
```

### Manual fitting

For anything the shorthands don't cover:

```python
fit = FitObj(rabi_flop)           # any function f(x, param1, param2, ...)
fit.p0.amp    = 0.8               # set initial guess by name
fit.p0.omega  = 1e5
fit.bounds.omega = (0, np.inf)    # optional bounds
fit.fix(offset=0.0)               # hold a parameter constant
fit.unfix('offset')               # free it again

result = pm1.s1.run_fit(fit)      # fits, prints, attaches, replots
print(result)                     # table of all params with uncertainties
```

Built-in fit functions:

```
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
```

---

## Sessions

The REPL records every command you run. Save the session as a named function at any time:

```python
save_session(my_session)                     # saves to user/sessions.py
save_session(my_session, directory='/path')  # save elsewhere
load_session(my_session)                     # replay in current namespace
list_sessions()                               # show all saved sessions
clear_history()                               # reset recording (start fresh)
```

Sessions are plain Python `def` functions in `user/sessions.py` — open the file to edit parameters or cut exploratory commands before re-running.

---

## Custom functions

Put personal utility functions in `user/startup.py`. The file is exec'd into the REPL namespace every time the REPL starts, so anything defined there is immediately available — no import needed.

```python
# user/startup.py
from h5repl import *
import numpy as np
import matplotlib.pyplot as plt

def scan_summary(rid):
    """Open a file, print its structure, and plot the first dataset pair found."""
    f = h5open(rid)
    h5print(rid)
    x = get_dataset(f, 'time')
    y = get_dataset(f, 'signal')
    pm = PlotManager()
    pm.add_series(Series(x, y, label='signal'))
    return pm

def my_rabi(series):
    """Fit a Rabi flop and update the title automatically."""
    result = fit_rabi(series)
    pi_us = np.pi / result.omega.a * 1e6
    series._manager.title = f"Rabi flop  |  pi_time = {pi_us:.1f} us"
    return result
```

Then in the REPL:

```python
pm1 = scan_summary(103550)
result = my_rabi(pm1.s1)
```

Functions defined in startup.py are also tab-completed and can be inspected with `;`:

```
>>> my_rabi;
```

`user/startup.py` is gitignored — it's personal to your machine.

---

## Using h5repl as a library

h5repl works as a normal Python package outside the REPL. Import everything:

```python
from h5repl import *
import numpy as np
import matplotlib
matplotlib.use('TkAgg')         # set your preferred backend before importing pyplot
import matplotlib.pyplot as plt
```

The REPL's asyncio figure pump isn't running outside the REPL, so call `plt.show()` (blocking) or `plt.pause()` to render figures:

```python
f = h5open(103550)
x = get_dataset(f, 'time')
y = get_dataset(f, 'signal')

pm1 = PlotManager()
pm1.add_series(Series(x, y, label='signal'))
pm1.title = 'My scan'
pm1.xscale = 1e6
pm1.xunit = 'us'

result = fit_rabi(pm1.s1)
print(result.omega)

plt.show()                      # blocks until figure is closed
```

For non-interactive scripts, `plt.savefig` works without showing the window:

```python
from h5repl import *
import matplotlib
matplotlib.use('Agg')           # non-interactive backend, no display needed
import matplotlib.pyplot as plt

f = h5open(103550)
pm1 = PlotManager()
pm1.add_series(Series(get_dataset(f, 'time'), get_dataset(f, 'signal')))
fit_rabi(pm1.s1)
pm1.export('scan.pdf')
```

In Jupyter, set the backend with the magic before importing:

```python
%matplotlib widget          # or 'inline', 'notebook'
from h5repl import *
```

---

## REPL tips

| Tip | What it does |
|---|---|
| `h5open;` | Show the docstring for any function or object |
| A bare function name (e.g. `fit_rabi`) | Also shows its docstring, if it needs arguments |
| `pm1.s1.<TAB>` | Tab-complete attributes at any depth |
| `fit_rabi(s, fix={<TAB>` | Tab-complete fixable parameter names |
| `load_session(<TAB>` | Tab-complete saved session names |
| `help_repl` | Print the full quick reference |
| Close a plot window | Automatically removes that PlotManager |
| `open(103550)` | Silently rewritten to `h5open(103550)` |
