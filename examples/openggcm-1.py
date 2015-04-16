import viscid
from viscid.readers import openggcm
from viscid.plot import mpl

openggcm.GGCMGrid.mhd_to_gse_on_read = 'auto'

f3d = viscid.load_file(_viscid_root + '/../../sample/sample.3df.xdmf')
pp = f3d["pp"]["x=-20.0:20.0,y=0.0,z=-10.0:10.0"]
mpl.plot(pp, plot_opts="log,x_-30_15", earth=True)
mpl.plt.title(pp.format_time("UT"))