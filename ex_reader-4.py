import numpy as np
from matplotlib import pyplot as plt

import viscid
from viscid.plot import mpl

f3d = viscid.load_file(_viscid_root + '/../../sample/sample.3df.xdmf')

times = np.array([grid.time for grid in f3d.iter_times()])
nr_times = len(times)

for i, grid in enumerate(f3d.iter_times()):
    plt.subplot2grid((nr_times, 1), (i, 0))
    mpl.plot(f3d["vz"]["x=-20:20,y=0,z=-10:10"], plot_opts="lin_0,earth")