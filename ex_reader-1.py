import viscid
from viscid.plot import mpl

f3d = viscid.load_file(_viscid_root + '/../sample/sample.3df.xdmf')
pp = f3d["pp"]["y=0"]
mpl.plot(pp, plot_opts="log")