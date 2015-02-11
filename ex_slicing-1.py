import viscid
from viscid.plot import mpl

f3d = viscid.load_file(_viscid_root + '/../sample/sample.3df.xdmf')

# notice how slices by index appear as integers, and slices by location
# are done with floats... this means "y=0" is not the same as "y=0.0"
pp = f3d["pp"]["x=50:-30,y=0.0,z=-10.0:10.0"]
mpl.plot(pp, style="contourf", levels=50, plot_opts="log,earth")