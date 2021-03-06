#!/usr/bin/env python

from __future__ import print_function
import sys
import argparse

import numpy as np

from viscid import logger
from viscid import vutil
from viscid import readers
from viscid import field
from viscid.calculator import cycalc
from viscid.calculator import streamline
from viscid.calculator import seed
from viscid.plot import mpl
from viscid.plot.mpl import plt

def main():
    parser = argparse.ArgumentParser(description="Streamline a PSC file")
    parser.add_argument("-t", default="2000",
                        help="which time to plot (finds closest)")
    parser.add_argument('infile', nargs=1, help='input file')
    args = vutil.common_argparse(parser)

    # f = readers.load_file("pfd.020000.xdmf")
    # ... or ...
    # using this way of loading files, one probably wants just to give
    # pfd.xdmf to the command line
    f = readers.load_file(args.infile[0])
    f.activate_time(args.t)

    jz = f["jz"]
    # recreate hx as a field of 0 to keep streamlines from moving in
    # that direction
    hx = field.zeros_like(jz, name="hx")
    h1 = field.scalar_fields_to_vector([hx, f["hy"], f["hz"]], name="H",
                                       _force_layout="Interlaced",
                                       forget_source=True)
    e = field.scalar_fields_to_vector([f["ex"], f["ey"], f["ez"]], name="E",
                                      _force_layout="Interlaced",
                                      forget_source=True)

    # plot magnetic fields, just a sanity check
    # ax1 = plt.subplot(211)
    # mpl.plot(f["hy"], flip_plot=True)
    # ax2 = plt.subplot(212, sharex=ax1, sharey=ax1)
    # mpl.plot(f["hz"], flip_plot=True)
    # mpl.mplshow()

    # make a line of 30 seeds straight along the z axis (x, y, z ordered)
    seeds1 = seed.Line((0.0, 0.0, 2.0), (1022.0, 0.0, 0.0), 60)
    # set outer boundary limits for streamlines
    ds = 0.005  # spatial step along the stream line curve
    obound0 = np.array([1, -128, -1000], dtype=h1.dtype)
    obound1 = np.array([1023, 128, 1000], dtype=h1.dtype)
    # calc the streamlines
    lines1, topo1 = streamline.streamlines(h1, seeds1, ds0=ds, maxit=200000,
                                           obound0=obound0, obound1=obound1,
                                           ibound=0.0)
    # run with -v to see this
    logger.info("Topology flags: {0}".format(topo1))

    # rotate plot puts the z axis along the horizontal
    flip_plot = True
    mpl.plot(jz, flip_plot=flip_plot, plot_opts="lin_-.05_.05")
    # mpl.plot_streamlines2d(lines1, "x", flip_plot=flip_plot, color='k')
    plt.xlim([0, 1024])
    plt.ylim([-128, 128])
    plt.show()

    # interpolate e onto each point of the first field line of lines1
    e1 = cycalc.interp_trilin(e, seed.Point(lines1[0]))
    print(e1.shape, lines1[0].shape)
    plt.clf()
    plt.plot(np.linspace(0, ds * e1.shape[0], e1.shape[0]), e1[:, 0])
    plt.xlabel("length along field line")
    plt.ylabel("Ex")
    plt.show()

    return 0

if __name__ == "__main__":
    err = main()
    sys.exit(err)

##
## EOF
##
