import viscid
from viscid.readers import openggcm
from viscid.plot import mpl

openggcm.GGCMGrid.mhd_to_gse_on_read = True

f3d = viscid.load_file(_viscid_root + '/../../sample/sample.3df.xdmf')
pp = f3d["pp"]["x=-20:20,y=0,z=-10:10"]
mpl.plot(pp, plot_opts="log,x_-30_15", earth=True)