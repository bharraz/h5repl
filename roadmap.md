# h5repl Roadmap

## What Works

- **`GoldH5File`** -- virtual datasets (`pops_N`, `errs_N`, `params/`) computed on open
- **`h5open` / `get_dataset` / `h5print`** -- open by RID, recursive search, plain-text tree view
- **`PlotManager` + `Series`** -- live-updating figure; all style attrs replot on assignment; `xscale`/`xunit` rescale retroactively; closing a window removes the manager
- **`quickplot(rid)`** -- auto-detects scan axis and active PMTs, generates title with SI-prefixed fixed params, returns `PlotManager` auto-injected into REPL namespace as `pm1`, `pm2`, ...
- **`FitObj` / `FitResult` / `Unc`** -- wraps any `f(x, *params)`, dot-accessible `p0`/`bounds`, `fix()`/`unfix()`, pretty uncertainty printing; 11 built-in model functions
- **Fit shorthands** -- `fit_rabi`, `fit_decaying_cosine`, `fit_lorentzian`, `fit_gaussian`, `fit_exp_decay`, `fit_ramsey_phase`, `fit_ramsey_time`, `fit_spectroscopy`, `fit_linear`, `fit_quadratic`; auto-guessed p0, keyword overrides, dotted fit line, returns `FitResult`
- **`pm.export(filename, dest, dpi)`** -- saves figure to `user_dir/figures` (or `figures_dir` override); configurable via `config.toml`
- **`pm.style(name)` / `save_style(name, rc)`** -- per-manager rcParams presets stored in `config.toml [styles]`
- **REPL** -- asyncio + prompt_toolkit (figures stay responsive), tab completion at any depth (`pm1.pmt0.<TAB>`), auto-quoting preprocessor, `name;` shows docstring, zero-arg callables auto-run when typed alone
- **Sessions** -- `save_session(name, directory)` / `load_session` as plain Python defs; built-in `demo` tutorial; configurable `user_dir` in `config.toml`

---

## Next Steps

### 1. File indexer
`h5open` currently walks all configured dirs on every call. Replace with:
- `reindex()` -- walk once, write RID / experiment class / date / fixed params to `.h5index.db`
- `ls(n=20)` -- list recent files
- `search(type="RamanScan", after="2024-01-01")` -- filter by type/date
- `h5open` checks index first, falls back to walk

### 2. Cross-file aggregation
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
