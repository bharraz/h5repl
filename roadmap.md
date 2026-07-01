# h5repl Roadmap

## What Works

- **`GoldH5File`** -- virtual datasets (`pops_N`, `errs_N`, `params/`) computed on open
- **`h5open` / `get_dataset` / `h5print`** -- open by RID, recursive search, tree view
- **`PlotManager` + `Series`** -- live-updating figure; all style attrs replot on assignment; `xscale`/`xunit` rescale retroactively; closing a window removes the manager
- **`quickplot(rid)`** -- auto-detects scan axis and active PMTs, generates title with SI-prefixed fixed params, returns `PlotManager` auto-injected into REPL namespace as `pm1`, `pm2`, ...
- **`FitObj` / `FitResult` / `Unc`** -- wraps any `f(x, *params)`, dot-accessible `p0`/`bounds`, `fix()`/`unfix()`, pretty uncertainty printing; built-in `sine_fun`, `decaying_cosine`
- **REPL** -- asyncio + prompt_toolkit (figures stay responsive), tab completion at any depth (`pm1.pmt0.<TAB>`), auto-quoting preprocessor, `name;` shows docstring, zero-arg callables auto-run when typed alone
- **Sessions** -- `save_session` / `load_session` as plain Python defs in `user/sessions.py`; built-in `demo` session as interactive tutorial

---

## Next Steps

### 1. File indexer
`h5open` currently walks all configured dirs on every call. Replace with:
- `reindex()` -- walk once, write RID / experiment class / date / fixed params to `.h5index.db`
- `ls(n=20)` -- list recent files
- `search(type="RamanScan", after="2024-01-01")` -- filter by type/date
- `h5open` checks index first, falls back to walk

### 2. Built-in fit shorthands
Common experiment types need a one-liner:
```python
fit_rabi(pm.pmt0)       # fits, replots, prints result
fit_ramsey(pm.pmt0)
```
`FitObj` + `sine_fun` / `decaying_cosine` are ready; this is just a thin wrapper with sensible default p0.

### 3. Publication figure helpers
```python
pm.export("rabi.pdf")       # tight layout, saves to user/figures/
pm.style("publication")     # applies rcParams preset
```
Style presets in `user/style.py` so the user can edit them.

### 4. Cross-file aggregation
```python
pm.add_from_files([rid1, rid2, ...],
    extract=lambda f: fit_rabi(f).omega.a,
    x=lambda f: get_dataset(f, "power"))
```
Fit a quantity per file, collect across files, plot trend.

---

## Longer-Term

- **2D scan heatmap** -- `product/` subgroup has the meshgrid; render as `pcolormesh`
- **Live update mode** -- poll directory, replot as new files arrive during an active experiment
- **Parameter browser** -- `browse(rid)` interactive view of `params/` virtual group
