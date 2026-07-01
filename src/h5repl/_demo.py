"""Built-in demo session - loaded via load_session(demo)."""

from h5repl import (h5open, h5print, quickplot, OPEN_FILES,
                    FitObj, sine_fun, decaying_cosine)


def demo():

    def pause(msg=''):
        if msg:
            print(msg)
        input("  [Press Enter to continue...]")

    print()
    print("=" * 60)
    print("  h5repl  -  interactive tutorial")
    print("=" * 60)
    print("""
This tutorial walks through the core workflow using two real
Gold System HDF5 files included with the package:

  103550  RamanScan       (Rabi flop - duration axis)
  103551  RamseySeqScan   (Ramsey fringes - phase axis)
""")
    pause()

    print()
    print("-- Step 1: Opening a file " + "-" * 35)
    print("""
  h5open searches all directories listed in config.toml.
  The file is stored under its RID in OPEN_FILES.

  Command:  h5open(103550)
""")
    h5open(103550)
    print(f"  OPEN_FILES now contains: {list(OPEN_FILES.keys())}")
    pause()

    print()
    print("-- Step 2: Exploring the file structure " + "-" * 21)
    print("""
  h5print shows the full HDF5 tree. The Gold System stores
  scan axes and fixed parameters under datasets/scan.

  Command:  h5print(103550, start_root='datasets/scan')
""")
    h5print(103550, start_root='datasets/scan')
    print()
    print("  The 'duration' key is the varying scan axis (31 points).")
    print("  All other numeric scalars are fixed experiment parameters.")
    pause()

    print()
    print("-- Step 3: Quick-plot the Rabi flop " + "-" * 24)
    print("""
  quickplot() auto-detects the scan axis and active PMT channels,
  builds the PlotManager, and opens the figure window.

  Command:  pm1 = quickplot(103550)
""")
    pm1 = quickplot(103550)
    print()
    print(f"  Created: {pm1}")
    print("  The x axis is in seconds - very small numbers.")
    pause("  Look at the figure window - x values around 1e-4.")

    print()
    print("-- Step 4: Rescaling the x axis " + "-" * 28)
    print("""
  xscale multiplies all x data; xunit regenerates the xlabel.
  Both trigger a full replot automatically.

  Commands:
    pm1.xscale = 1e6
    pm1.xunit  = 'us'
    pm1.title  = 'Rabi flop  |  RID 103550'
""")
    pm1.xscale = 1e6
    pm1.xunit  = 'us'
    pm1.title  = 'Rabi flop  |  RID 103550'
    pause("  X axis is now in us and the title has updated.")

    print()
    print("-- Step 5: Styling a series " + "-" * 32)
    print("""
  All Series attributes trigger an immediate replot when set.
  Access the series by nickname via pm1.pmt0

  Commands:
    pm1.pmt0.color      = 'steelblue'
    pm1.pmt0.markersize = 7
    pm1.grid = True
""")
    pm1.pmt0.color      = 'steelblue'
    pm1.pmt0.markersize = 7
    pm1.grid = True
    pause("  Color, size, and grid updated live.")

    print()
    print("-- Step 6: Adding a second series " + "-" * 26)
    print("""
  pm.add() adds arbitrary (x, y) data to an existing figure.
  Here we plot the same data shifted up by 0.1 to compare.

  Commands:
    x = pm1.pmt0.x
    y = pm1.pmt0.y
    pm1.add(x, y + 0.1, label='shifted +0.1', color='coral', linestyle='--')
    pm1.legend()
""")
    x = pm1.pmt0.x
    y = pm1.pmt0.y
    pm1.add(x, y + 0.1, label='shifted +0.1', color='coral', linestyle='--')
    pm1.legend()
    pause("  Legend now shows both series.")

    print()
    print("-- Step 7: Opening the Ramsey scan for fitting " + "-" * 13)
    print("""
  The 103551 RamseySeqScan has a clean sine-like fringe.

  Command:  pm2 = quickplot(103551)
""")
    pm2 = quickplot(103551)
    print()
    pm2.title = 'Ramsey fringes  |  RID 103551'
    pause("  Second figure opened with the Ramsey phase scan.")

    print()
    print("-- Step 8: Fitting a sine wave " + "-" * 29)
    print("""
  FitObj wraps a function and manages initial guesses and bounds.
  sine_fun(x, amp, freq, phi, offset) is built in.

  Commands:
    fit = FitObj(sine_fun)
    fit.p0.amp    = 0.38
    fit.p0.freq   = 1.0
    fit.p0.phi    = 3.14
    fit.p0.offset = 0.37
    result = pm2.pmt0.run_fit(fit)
""")
    fit = FitObj(sine_fun)
    fit.p0.amp    = 0.38
    fit.p0.freq   = 1.0
    fit.p0.phi    = 3.14
    fit.p0.offset = 0.37
    result = pm2.pmt0.run_fit(fit)
    print()
    print("  Access individual parameters:")
    print(f"    result.amp    = {result.amp}")
    print(f"    result.freq   = {result.freq}")
    print(f"    result.offset = {result.offset}")
    pm2.legend()
    pause("  Fit curve overlaid on the Ramsey data.")

    print()
    print("-- Step 9: Bonus - decaying_cosine " + "-" * 25)
    print("""
  For Rabi/Ramsey experiments with decoherence, use:

    decaying_cosine(x, amp, omega, phi, tau, offset)

  Example (not run here):

    fit2 = FitObj(decaying_cosine)
    fit2.p0.amp    = 0.3
    fit2.p0.omega  = 6.28
    fit2.p0.phi    = 0.0
    fit2.p0.tau    = 80.0
    fit2.p0.offset = 0.5
    result2 = pm1.pmt0.run_fit(fit2)
""")
    pause()

    print()
    print("=" * 60)
    print("  Tutorial complete!")
    print("=" * 60)
    print("""
You now have two live plot windows (pm1, pm2) to explore.
Try:
  pm1.pmt0.color = 'green'
  pm2.xunit = 'rad'
  pm1.clear()

Type  help_repl  for the full command reference.
""")
