from h5repl import *
import numpy as np
import matplotlib.pyplot as plt

def test_session():
    h5open(103550)
    h5print("103550")
    xs = get_dataset("103550", "duration")
    ys = get_dataset("103550", "pops_0")
    plot = PlotManager()
    plot.add_series(Series(xs, ys, label="pops_0", marker="o"))
