from matplotlib import pyplot as plt

import viscid
from viscid.plot import mpl

iono_file = viscid.load_file(_viscid_root + '/../../sample/cen2000.iof.xdmf')

fac_tot = 1e9 * iono_file["fac_tot"]

ax1 = plt.subplot(121)
mpl.plot(fac_tot, ax=ax1, hemisphere="north", style="contourf",
         plot_opts="lin_-300_300", extend="both",
         levels=50, drawcoastlines=True)
ax2 = plt.subplot(122)
mpl.plot(fac_tot, ax=ax2, hemisphere="south", style="contourf",
         plot_opts="lin_-300_300", extend="both",
         levels=50, drawcoastlines=True)
plt.gcf().set_size_inches(12, 4.5)
mpl.tighten()