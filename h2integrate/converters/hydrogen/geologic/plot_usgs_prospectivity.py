"""
A script to plot the geoH2 prospectivity map from USGS, Gelman et al.
doi.org/10.3133/pp1900
"""

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


ROOT = Path(__file__).parent

if __name__ == "__main__":
    map_path = ROOT / "usgs/cos.csv"
    p_map = np.loadtxt(map_path, skiprows=6, delimiter=",")
    p_map[p_map == -9999] = 0
    p_map = np.flipud(p_map)

    plt.set_cmap("viridis_r")
    plt.contourf(p_map, levels=[-0.01, 0, 0.2, 0.4, 0.6, 0.8, 1])
    plt.axis("equal")
    plt.show()
