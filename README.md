# h5repl

A Python REPL for interactively exploring, fitting, and plotting Gold System HDF5 experiment data. Open a file by ID, tab-complete your way to the data, fit it, and get a live-updating figure — then save the whole session as a named function you can replay later.

---

## Installation

```sh
pip install -e .
```

## Configuration

Edit `config.toml` to point at your data directories:

```toml
[file_directories]
data = "./data"
# add more named directories as needed
```

---

## Starting the REPL

```sh
h5repl
```

All h5repl functions, `np`, and `plt` are available immediately. No imports needed.

---

## Quick Reference

### File Operations

```python
open(103550)                        # open file by ID — no quotes needed
h5open("103550", nickname="f")      # open with a short nickname
h5print(f)                          # pretty-print file structure (including virtual datasets)
get_dataset(f, pops_0)              # get a dataset — no quotes needed
h5close(f)                          # close one file
h5close_all()                       # close all open files
```

`OPEN_FILES` holds all open file handles keyed by nickname.

Typing a function name alone prints its docstring:
```
>>> h5open
Docstring for h5open:
...
```

### Virtual Datasets (Gold System)

When a file is opened it is wrapped in `GoldH5File`, which adds computed datasets without modifying the file:

| Dataset | Description |
|---|---|
| `params/*` | All experiment parameters extracted from `expid` JSON |
| `pops_N` | Population per scan point for PMT N (relative to center) |
| `errs_N` | Binomial error per scan point for PMT N |
| `num_points` | Number of scan points |
| `num_shots` | Number of shots per point |

PMT numbering: 0 = center, −1 = left of center, +1 = right, etc.

---

## Plotting

The REPL uses `plt.ion()` for live-updating figures. Any open figure redraws after every REPL command automatically.

Create a managed figure with `PlotManager`:

```python
plot = PlotManager()          # single axes
plot = PlotManager(1, 2)      # two side-by-side subplots
```

Add data with `Series`:

```python
s = Series(x, y, label="signal", color="blue", marker='o')
plot.add_series(s)            # subplot 0 by default
plot.add_series(s, ax=1)      # subplot 1
plot.clear()                  # clear all series
plot.replot()                 # force redraw
```

`fig` and `axes` are fully public — any matplotlib call works directly:

```python
plot.axes[0].set_xlabel("frequency (Hz)")
plot.axes[0].set_yscale("log")
plot.fig.suptitle("experiment 42")
```

---

## Fitting

Wrap any function with `FitObj`:

```python
def decay_sine(x, amp, omega, tau, background):
    return -amp/2 * np.cos(omega * x) * np.exp(-x / tau) + background

fit = FitObj(decay_sine)
```

Set initial guesses and bounds by parameter name:

```python
fit.p0.amp       = 1.0
fit.p0.tau       = 50e-6
fit.bounds.tau   = (0, np.inf)
fit.bounds.omega = (0, np.inf)
```

Fix parameters to constants:

```python
fit.fix(background=0.0)
fit.unfix("background")
```

Run and inspect:

```python
result = fit.fit(x, y)
print(result)           # table of all params with uncertainties
print(result.amp)       # "1.234(5)"
print(result.amp.a)     # 1.234  (central value)
print(result.amp.s)     # 0.005  (1-sigma)
```

Attach a fit to a Series to overlay the curve:

```python
s = Series(x, y, label="data", fit=fit)
plot.add_series(s)
```

---

## Sessions

The REPL records every command you run. At any point you can save the session as a named Python function in `user/sessions.py`:

```python
save_session("raman_scan_103550")
```

List and reload saved sessions:

```python
list_sessions()
load_session("raman_scan_103550")   # replays in the current namespace
```

Sessions are stored as plain `def` functions in `user/sessions.py` — open the file in any editor to clean up exploratory commands or tweak parameters before re-running.

`clear_history()` resets the in-session recording without touching the sessions file (useful when you want to save only the commands you run after a certain point).

---

## User Directory

```
user/
  sessions.py   — named session functions (auto-created on first save)
  figures/      — save publication figures here
  fits/         — store reusable fit function definitions here
```

Save a figure:

```python
plot.fig.savefig(USER_DIR / "figures" / "raman_103550.pdf", bbox_inches="tight")
```

---

## Tab Completion

- `get_dataset(f, <TAB>)` — dataset names from that open file
- `np.<TAB>` — numpy attributes
- `plt.<TAB>` — matplotlib.pyplot attributes
- Default — all REPL names and open file nicknames

---

## Project Structure

```
src/h5repl/
  cli.py          — REPL entry point, session tracking, matplotlib setup
  h5utils.py      — file I/O: h5open, get_dataset, h5print
  goldh5file.py   — GoldH5File with virtual datasets
  fitutils.py     — FitObj, FitResult, Unc
  plotting.py     — PlotManager, Series
  session.py      — save_session, load_session, list_sessions
  globals.py      — OPEN_FILES, CFG, USER_DIR
  PTKCompleter.py — tab completion
config.toml       — data directory configuration
user/             — your figures, fits, and saved sessions
```
