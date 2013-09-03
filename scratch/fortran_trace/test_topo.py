#!/usr/bin/env python

from __future__ import print_function
import sys
import os
from timeit import default_timer as time
import argparse
import logging

import numpy as np
from mayavi import mlab

_viscid_root = os.path.realpath(os.path.dirname(__file__) + '/../../src/viscid/') #pylint: disable=C0301
if not _viscid_root in sys.path:
    sys.path.append(_viscid_root)

import tracer
from viscid import vutil
from viscid import readers
from viscid import field
# from viscid.plot import mpl
from viscid.plot import mvi
from viscid.calculator import streamline
from viscid.calculator import seed

gsize = (2, 8, 8)

def trace_fortran(fld_bx, fld_by, fld_bz):
    gx, gy, gz = fld_bx.crds.get_crd(('xcc', 'ycc', 'zcc'))
    nz, ny, nx = fld_bx.shape

    bx_farr = np.array(np.ravel(fld_bx.data, order='K').reshape((nx, ny, nz), order="F")) #pylint: disable=C0301
    by_farr = np.array(np.ravel(fld_by.data, order='K').reshape((nx, ny, nz), order="F")) #pylint: disable=C0301
    bz_farr = np.array(np.ravel(fld_bz.data, order='K').reshape((nx, ny, nz), order="F")) #pylint: disable=C0301
    topo = np.zeros(gsize, order='F', dtype='int32')
    nsegs = np.zeros((1,), order='F', dtype='int32')

    logging.info((np.ravel(bx_farr, order='K') == np.ravel(fld_bx.data, order='K')).all()) #pylint: disable=C0301
    logging.info((np.ravel(by_farr, order='K') == np.ravel(fld_by.data, order='K')).all()) #pylint: disable=C0301
    logging.info((np.ravel(bz_farr, order='K') == np.ravel(fld_bz.data, order='K')).all()) #pylint: disable=C0301
    logging.info("bx_arr")
    logging.info(bx_farr.strides)
    logging.info(bx_farr.flags)
    logging.info("topo")
    logging.info(topo.strides)
    logging.info(topo.shape)
    
    t0 = time()
    tracer.get_topo(gx, gy, gz, bx_farr, by_farr, bz_farr, topo, 
                    -10.0, -5.0, -5.0, 5.0, -5.0, 5.0, nsegs)
    t1 = time()
    return t1 - t0, nsegs[0], None, topo

def trace_cython(fld_bx, fld_by, fld_bz):
    B = field.VectorField("B_cc", fld_bx.crds, [fld_bx, fld_by, fld_bz],
                          center="Cell", forget_source=True,
                          info={"force_layout": field.LAYOUT_INTERLACED})
    vol = seed.Volume((-5.0, -5.0, -10.0), (5.0, 5.0, -5.0), gsize)
    t0 = time()
    lines, topo = streamline.streamlines(B, vol, ds0=0.02, ibound=3.7,
                                         maxit=100000, output=streamline.OUTPUT_BOTH)
    t1 = time()

    # mpl.plot_streamlines(lines, show=True)

    b_src = mvi.field_to_source(B)
    mvi.plot_lines(mlab.pipeline, lines, color=(0.0, 0.8, 0.0), tube_radius=0.05)
    mvi.mlab_earth(mlab.pipeline)
    mlab.show()

    nsegs = 1  # keep from divding by 0 is no streamlines
    if lines is not None:
        nsegs = 0
        for line in lines:
            nsegs += len(line[0])

    return t1 - t0, nsegs, lines, topo

def main():
    parser = argparse.ArgumentParser(description="Test xdmf")
    parser.add_argument("--show", "--plot", action="store_true")
    args = vutil.common_argparse(parser) #pylint: disable=W0612

    # f3d = readers.load(_viscid_root + '/../../sample/sample.3df.xdmf')
    # b3d = f3d['b']
    # bx, by, bz = b3d.component_fields() #pylint: disable=W0612

    f3d = readers.load("/Users/kmaynard/dev/work/t1/t1.3df.004320.xdmf")
    bx = f3d["bx"]
    by = f3d["by"]
    bz = f3d["bz"]

    print("Fortran...")
    t, nsegs, lines, topo = trace_fortran(bx, by, bz)
    print("total segments calculated: ", nsegs)
    print("time: {0:.4}s ... {1:.4}s/segment".format(t, t / float(nsegs)))

    print("Cython...")
    t, nsegs, lines, topo = trace_cython(bx, by, bz)
    print("total segments calculated: ", nsegs)
    print("time: {0:.4}s ... {1:.4}s/segment".format(t, t / float(nsegs)))

if __name__ == "__main__":
    main()

##
## EOF
##
