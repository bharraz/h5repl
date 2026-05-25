from h5repl import *
import numpy as np
import matplotlib.pyplot as plt
f = h5open("161")
print("Open files:", globals.OPEN_FILES)

def decay_sine_fit(x, amp, tau, freq, phase, background):
    """Example: decaying sine wave"""
    return background + amp * np.exp(-x/tau) * np.sin(2*np.pi*freq*x + phase)

fit = FitObj(decay_sine_fit)
xs = get_dataset('161', "n")
ys = get_dataset('161', 'pops_0')
print(xs)
print(ys)
result = fit.fit(xs, ys)
print(result)
plt.scatter(xs, ys)
plt.plot(result.xs, result.ys)
plt.show()

# Close files when done
for fh in globals.OPEN_FILES.values():
    try:
        fh.close()
    except Exception:
        pass

