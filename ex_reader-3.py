from matplotlib import pyplot as plt

import viscid
from viscid.plot import mpl

f3d = viscid.load_file(_viscid_root + '/../sample/sample.3df.xdmf')

ax1 = plt.subplot2grid((2, 1), (0, 0))
f3d.activate_time(0)

# notice y=0.0, this is different from y=0; y=0 is the 0th index in
# y, which is this case will be y=-50.0
mpl.plot(f3d["vz"]["x=-20.0:20.0,y=0.0,z=-10.0:10.0"], style="contourf",
         levels=50, plot_opts="lin_0,earth")

# share axes so this plot pans/zooms with the first
plt.subplot2grid((2, 1), (1, 0), sharex=ax1, sharey=ax1)
f3d.activate_time(-1)
mpl.plot(f3d["vz"]["x=-20.0:20.0,y=0.0,z=-10.0:10.0"], style="contourf",
         levels=50, plot_opts="lin_0,earth")