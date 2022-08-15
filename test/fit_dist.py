import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

# Create a Continuous Variable:
X = stats.rayleigh(loc=10, scale=5)

# Sample from this Random variable
x0 = X.rvs(size=10000, random_state=123)

# Adjust Distribution parameters
loc, scale = stats.rayleigh.fit(x0) # (9.990726961181025, 4.9743913760956335)

# Tabulate over sample range (PDF display):
xl = np.linspace(x0.min(), x0.max(), 100)

# Display Results:
fig, axe = plt.subplots()
axe.hist(x0, density=1, label="Sample")
axe.plot(xl, X.pdf(xl), label="Exact Distribution")
axe.plot(xl, stats.rayleigh(scale=scale, loc=loc).pdf(xl), label="Adjusted Distribution")
axe.set_title("Distribution Fit")
axe.set_xlabel("Variable, $x$ $[\mathrm{AU}]$")
axe.set_ylabel("Density, $f(x)$ $[\mathrm{AU}^{-1}]$")
axe.legend()
axe.grid()
