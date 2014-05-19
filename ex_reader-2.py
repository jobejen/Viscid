from matplotlib import pyplot as plt

import viscid
from viscid.plot import mpl

f3d = viscid.load_file(_viscid_root + '/../../sample/sample.3df.xdmf')

ax1 = plt.subplot2grid((2, 1), (0, 0))
mpl.plot(f3d["pp"]["y=0"], plot_opts="log,earth")

# share axes so this plot pans/zooms with the first
plt.subplot2grid((2, 1), (1, 0), sharex=ax1, sharey=ax1)
mpl.plot(f3d["vx"]["y=0"], plot_opts="earth")

plt.xlim((-20, 20))
plt.ylim((-10, 10))