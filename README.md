# h5repl

Interactive Python REPL for Gold System HDF5 experiment data. Open a file, plot it, fit it, and save the session — all with tab completion and live-updating figures.

```
h5repl
```

> New here? Run `load_session(demo)` to walk through an interactive tutorial.

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
h5print(103550, start_root='datasets/scan')   # focus on a subtree
get_dataset(103550, 'duration')               # read a dataset by name (recursive search)
h5close(103550)               # close one file
h5close_all()                 # close all files
```

When opened, the file is wrapped as a `GoldH5File` which adds computed virtual datasets:

| Dataset | What it is |
|---|---|
| `params/*` | All experiment arguments from the `expid` JSON |
| `pops_N` | Population per scan point for PMT N |
| `errs_N` | Binomial error per scan point for PMT N |
| `num_points` / `num_shots` | Scan size |

PMT numbering: 0 = center, -1 = left, +1 = right, etc.

---

## Plotting

### One-liner

```python
pm1 = quickplot(103550)       # auto-detects scan axis and active PMTs; returns PlotManager
pm1 = quickplot(103550, xscale=1e6, xunit='us')   # rescale x at creation time
pm1 = quickplot(103550, pmt=0)                    # specific PMT only
pm1 = quickplot(103550, pmt='all')                # all PMT channels
```

`pm1` is also injected directly into the REPL namespace — you can type `pm1` right away.

### PlotManager properties

Setting any of these updates the figure immediately:

```python
pm1.title  = 'Rabi flop'
pm1.xlabel = 'duration (us)'
pm1.ylabel = 'population'
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
pm1.autoscale()               # reset xlim/ylim to auto
pm1.add(x, y, label='ref', color='gray')    # add an extra series
pm1.remove_series('ref')      # remove a series by name
```

Escape hatches to raw matplotlib:

```python
pm1.ax                        # matplotlib Axes
pm1.fig                       # matplotlib Figure
```

### Series properties

Each series updates the plot when you set an attribute:

```python
pm1.pmt0.color      = 'steelblue'
pm1.pmt0.alpha      = 0.7
pm1.pmt0.label      = 'center ion'
pm1.pmt0.linestyle  = '--'        # None = markers only
pm1.pmt0.marker     = 's'
pm1.pmt0.markersize = 6
pm1.pmt0.visible    = False       # hide/show
```

Fit line style (set before or after fitting):

```python
pm1.pmt0.fit_color     = 'red'   # defaults to same color as series
pm1.pmt0.fit_linestyle = ':'     # defaults to '--'; shorthands use ':'
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
pm1.export('rabi_flop.pdf')           # saves to user/figures/
pm1.export('rabi_flop.png', dpi=600)
pm1.export()                          # uses plot title as filename
pm1.export('out.pdf', dest='/tmp')    # explicit directory
```

---

## Fitting

### Shorthands (recommended)

Each shorthand auto-guesses initial parameters from the data, fits, prints the result, overlays a dotted line, and returns a `FitResult`.

```python
result = fit_rabi(pm1.pmt0)
result = fit_decaying_cosine(pm1.pmt0)
result = fit_lorentzian(pm1.pmt0)
result = fit_gaussian(pm1.pmt0)
result = fit_exp_decay(pm1.pmt0)
result = fit_ramsey_phase(pm1.pmt0)
result = fit_ramsey_time(pm1.pmt0)
result = fit_spectroscopy(pm1.pmt0)   # reads pulse_duration from file automatically
result = fit_linear(pm1.pmt0)
result = fit_quadratic(pm1.pmt0)
```

Override any individual initial guess by keyword:

```python
result = fit_rabi(pm1.pmt0, omega=np.pi * 2e4)
result = fit_ramsey_time(pm1.pmt0, tau=100e-6)
result = fit_spectroscopy(pm1.pmt0, 50e-6, center_freq=6.834e9)
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
pm1.pmt0.label = f"data  (omega = {result.omega})"

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

result = pm1.pmt0.run_fit(fit)    # fits, prints, attaches, replots
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
save_session(rabi_103550)                     # saves to user/sessions.py
save_session(rabi_103550, directory='/path')  # save elsewhere
load_session(rabi_103550)                     # replay in current namespace
list_sessions()                               # show all saved sessions
clear_history()                               # reset recording (start fresh)
```

Sessions are plain Python `def` functions in `user/sessions.py` — open the file to edit parameters or cut exploratory commands before re-running.

---

## REPL tips

| Tip | What it does |
|---|---|
| `quickplot;` | Show the docstring for any function or object |
| `pm1.pmt0.<TAB>` | Tab-complete attributes at any depth |
| `load_session(<TAB>` | Tab-complete saved session names |
| `help_repl` | Print the full quick reference |
| `load_session(demo)` | Interactive tutorial |
| Close a plot window | Automatically removes that PlotManager |
| `open(103550)` | Silently rewritten to `h5open(103550)` |
