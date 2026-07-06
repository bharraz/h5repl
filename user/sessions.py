from h5repl import *
import numpy as np
import matplotlib.pyplot as plt


def test_export():
    """Test pm.export() and pm.style(). Check user/figures/ for the output files."""
    pm1 = quickplot(103550)
    pm1.xscale = 1e6
    pm1.xunit = 'us'
    pm1.title = 'Rabi flop export test'
    pm1.legend()
    input("  Plot open. Press Enter to apply 'publication' style...")

    pm1.style('publication')
    input("  Style applied (ticks inward, no legend frame). Press Enter to export...")

    pm1.export('rabi_flop.pdf')
    pm1.export('rabi_flop.png', dpi=150)
    print()
    print("  Check user/figures/ for rabi_flop.pdf and rabi_flop.png")
    print(f"  figures_dir = {CFG.get('figures_dir', './user/figures')}")


def test_fit_shorthands():
    """Test fit shorthands on the two standard files."""
    pm1 = quickplot(103550)
    pm1.xscale = 1e6
    pm1.xunit = 'us'
    input("  Rabi flop plotted. Press Enter to fit...")

    result = fit_rabi(pm1.pmt0)
    pi_time_us = np.pi / result.omega.a * 1e6
    pm1.title = f"Rabi flop  |  pi_time = {pi_time_us:.2f} us  |  omega = {result.omega}"
    print(f"  pi_time = {pi_time_us:.2f} us")
    print(f"  omega   = {result.omega}")
    print(f"  amp     = {result.amp}")
    input("  Fit applied (dotted line). Press Enter to continue to Ramsey...")

    pm2 = quickplot(103551)
    pm2.xscale = 1e6
    pm2.xunit = 'us'
    input("  Ramsey plotted. Press Enter to fit...")

    result2 = fit_ramsey_time(pm2.pmt0)
    pm2.title = f"Ramsey  |  T2 = {result2.tau}"
    print(f"  T2    = {result2.tau}")
    print(f"  omega = {result2.omega}")
    print()
    print("  Done. Try: result.amp, result.omega.a, result.omega.s")

def test_Jij():
    pm1 = quickplot(166078, joint_states=['01'])
    fit_decaying_cosine(pm1.pop01)
