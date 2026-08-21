# h5repl Roadmap

## What Works

- **`h5open` / `browse` / `get_dataset` / `h5print`** -- open by ID or file dialog, recursive dataset search, plain-text tree view
- **`Series`** -- build directly from arrays (`Series(x, y, yerr=...)`); full arithmetic (`+ - * / **`) with automatic error propagation
- **`PlotManager` + `Series`** -- live-updating figure; all style attrs replot on assignment; `xscale`/`xunit` rescale retroactively; closing a window removes the manager
- **`plot_grid(nrows, ncols)`** -- subplot grid of independent `PlotManager` panels sharing one figure, with a shared legend and whole-figure export
- **`FitObj` / `FitResult` / `Unc`** -- wraps any `f(x, *params)`, dot-accessible `p0`/`bounds`, `fix()`/`unfix()`, pretty uncertainty printing; 11 built-in model functions
- **Fit shorthands** -- `fit_rabi`, `fit_decaying_cosine`, `fit_lorentzian`, `fit_gaussian`, `fit_exp_decay`, `fit_ramsey_phase`, `fit_ramsey_time`, `fit_spectroscopy`, `fit_linear`, `fit_quadratic`; auto-guessed p0, keyword overrides, `fix=` dict, dotted fit line, returns `FitResult`; fitted params reachable directly off the series (`series.omega`)
- **`pm.export(filename, dest, dpi)`** -- saves figure to `user_dir/figures` (or `figures_dir` override); configurable via `config.toml`
- **`pm.style(name)` / `save_style(name, rc)`** -- per-manager rcParams presets stored in `config.toml [styles]`
- **REPL** -- asyncio + prompt_toolkit (figures stay responsive), tab completion at any depth (`pm1.s1.<TAB>`, `fix={<TAB>`), auto-quoting preprocessor, `name;` shows docstring, bare function names with required args also show their docstring, zero-arg callables auto-run when typed alone
- **Sessions** -- `save_session(name, directory)` / `load_session` as plain Python defs; configurable `user_dir` in `config.toml`

---

## Next Steps

### 1. File indexer
`h5open` currently walks all configured dirs on every call. Replace with:
- `reindex()` -- walk once, write ID / file type / date / fixed params to `.h5index.db`
- `ls(n=20)` -- list recent files
- `search(type="...", after="2024-01-01")` -- filter by type/date
- `h5open` checks index first, falls back to walk

### 2. Cross-file aggregation
```python
pm.add_from_files([id1, id2, ...],
    extract=lambda f: fit_rabi(f).omega.a,
    x=lambda f: get_dataset(f, "power"))
```
Fit a quantity per file, collect across files, plot trend.

### 3. Generic demo/tutorial
A synthetic bundled dataset + `load_session(demo)` walkthrough that doesn't depend on any particular experiment's file layout.

---

## Longer-Term

- **2D scan heatmap** -- render a meshgrid dataset as `pcolormesh`
- **Live update mode** -- poll a directory, replot as new files arrive
- **Dataset browser** -- interactive view of a file's parameter/metadata groups
