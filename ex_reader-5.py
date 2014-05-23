import viscid
from viscid.plot import mpl

f3d = viscid.load_file(_viscid_root + '/../sample/sample.3df.xdmf')
pp = f3d["pp"]["x=50i:-30i,y=0,z=-10:10"]
mpl.plot(pp, style="contourf", levels=50, plot_opts="log,earth")