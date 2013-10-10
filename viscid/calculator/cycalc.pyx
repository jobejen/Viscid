# cython: boundscheck=False, wraparound=False, cdivision=True, profile=False
#
# Note: a _c_FUNCTION can only be called from another cdef-ed function, or
# a def-ed _py_FUNCTION function because of the use of the fused real_t
# to template both float32 and float64 versions

from __future__ import print_function
import logging

import numpy as np

from cython.operator cimport dereference as deref
from cython.view cimport array as cvarray
# from cython.parallel import prange

from .. import field
from .. import coordinate
from . import seed

###########
# cimports
cimport cython
cimport numpy as cnp

from libc.math cimport sqrt

from cycalc_util cimport *
from cycalc cimport *

# cdef extern from "math.h":
#     bint isnan(double x)

#####################
# now the good stuff

cdef inline int _c_int_max(int a, int b):
    if a >= b:
        return a
    else:
        return b

cdef inline int _c_int_min(int a, int b):
    if a <= b:
        return a
    else:
        return b


cdef inline int _c_closest_ind(real_t[:] crd, real_t point, int *startind):
    cdef int i
    cdef int fallback
    cdef int n = crd.shape[0]
    cdef int forward = n > 1 and crd[1] > crd[0]

    if deref(startind) < 0:
        startind[0] = 0
    elif deref(startind) > n - 1:
        startind[0] = n - 1

    # search linearly... maybe branch prediction makes this better
    # than bisection for smallish arrays...
    # point is 'upward' (index wise) of crd[startind]... only search up
    if ((forward and crd[deref(startind)] <= point) or \
        (not forward and crd[deref(startind)] >= point)):
        for i from deref(startind) <= i < n - 1:
            if forward and crd[i + 1] >= point:
                startind[0] = i
                return i
            if not forward and crd[i + 1] <= point:
                startind[0] = i
                return i
        # if we've gone too far, pick the last index
        fallback = _c_int_max(n - 2, 0)
        startind[0] = fallback
        return fallback

    # startind was too large... go backwards
    for i from deref(startind) - 1 >= i >= 0:
        if forward and crd[i] <= point:
            startind[0] = i
            return i
        if not forward and crd[i] >= point:
            startind[0] = i
            return i
    # if we've gone too far, pick the first index
    fallback = 0
    startind[0] = fallback
    return fallback


def trilin_interp(fld, seeds):
    """ Points can be list of 3-tuples or a SeedGen instance. If fld
    is a scalar field, the output array has shape (npts,) where npts
    is the number of seed points. If it's a vector, the output has shape
    (npts, ncomp), where ncomp is the number of components of the vector.
    The data type of the output is the same as the original field.
    The output is always an array, even if only one point is given.
    """
    if fld.iscentered("Cell"):
        crdz, crdy, crdx = fld.crds.get_crd(center="Cell")
    elif fld.iscentered("Node"):
        crdz, crdy, crdx = fld.crds.get_crd()
    else:
        raise RuntimeError("Dont touch me with that centering.")

    dtype = fld.dtype

    if fld.istype("Vector"):
        if not fld.layout == field.LAYOUT_INTERLACED:
            raise ValueError("Trilin interp only written for interlaced data.")
        ncomp = fld.ncomp
        npts = seeds.n_points(center=fld.center)
        ret = np.empty((npts, ncomp), dtype=dtype)

        for j from 0 <= j < ncomp:
            # print(ret.shape, npts, ncomp)
            ret[:,j] = _py_trilin_interp(dtype, fld.data, j, crdz, crdy, crdx,
                                seeds.iter_points(center=fld.center),
                                npts)
        return ret

    elif fld.istype("Scalar"):
        dat = fld.data.reshape(fld.shape + [1])
        npts = seeds.n_points(center=fld.center)
        ret = np.empty((npts,), dtype=dtype)
        ret[:] = _py_trilin_interp(dtype, dat, 0, crdz, crdy, crdx,
                                   seeds.iter_points(center=fld.center),
                                   npts)
        return ret

    else:
        raise RuntimeError("That centering is not supported for trilin_interp")

def _py_trilin_interp(dtype, real_t[:,:,:,::1] s, np.intp_t m,
                      real_t[:] crdz, real_t[:] crdy, real_t[:] crdx, points,
                      int n_points):
    """ return the scalar value of 3d scalar array s trilinearly interpolated
    to the point x (in z, y, x order) """
    cdef unsigned int i
    cdef real_t[:] *crds = [crdz, crdy, crdx]
    cdef int* start_inds = [0, 0, 0]

    cdef real_t[:] x = np.empty((3,), dtype=dtype)
    cdef real_t[:] ret = np.empty((n_points,), dtype=dtype)

    # print("n_points: ", n_points)
    for i , pt in enumerate(points):
        x[0] = pt[0]
        x[1] = pt[1]
        x[2] = pt[2]
        ret[i] = _c_trilin_interp(s, m, crds, x, start_inds)
    return ret

cdef real_t _c_trilin_interp(real_t[:,:,:,::1] s, np.intp_t m, real_t[:] *crds,
                             real_t[:] x, int start_inds[3]):
    cdef int i, j, ind, ncells
    cdef int[3] ix
    cdef int[3] p  # increment, used for 2d fields
    cdef real_t[3] xd

    # cdef real_t[:] *crds = [crdz, crdy, crdx]
    cdef real_t c00, c10, c01, c11, c0, c1, c

    # find closest inds
    for i from 0 <= i < 3:
        # this 'if' is to support 2d fields... could probably be handled
        # more efficiently
        ncells = crds[i].shape[0]
        if ncells > 1:
            # find the closest ind
            # ind = _c_closest_ind[real_t](crds[i], x[i], &start_inds[i])
            # this implementation only works for monotonically increasing crds
            ind = _c_int_max(_c_int_min(start_inds[i], ncells - 2), 0)

            if crds[i][ind] <= x[i]:
                for j from ind <= j < ncells - 1:
                    if crds[i][j + 1] >= x[i]:
                        break
                ind = _c_int_min(j, ncells - 2)
            else:
                for j from ind - 1 >= j >= 0:
                    if crds[i][j] <= x[i]:
                        break
                ind = _c_int_max(j, 0)
            start_inds[i] = ind

            ix[i] = ind
            p[i] = 1
            xd[i] = (x[i] - crds[i][ind]) / (crds[i][ind + 1] - crds[i][ind])
        else:
            ind = 0
            ix[i] = ind
            p[i] = 0
            xd[i] = 1.0

    # INTERLACED ... z first
    c00 = s[ix[0], ix[1]       , ix[2]       , m] + xd[0] * (s[ix[0] + p[0], ix[1]       , ix[2]       , m] - s[ix[0], ix[1]       , ix[2]       , m])
    c10 = s[ix[0], ix[1] + p[1], ix[2]       , m] + xd[0] * (s[ix[0] + p[0], ix[1] + p[1], ix[2]       , m] - s[ix[0], ix[1] + p[1], ix[2]       , m])
    c01 = s[ix[0], ix[1]       , ix[2] + p[2], m] + xd[0] * (s[ix[0] + p[0], ix[1]       , ix[2] + p[2], m] - s[ix[0], ix[1]       , ix[2] + p[2], m])
    c11 = s[ix[0], ix[1] + p[1], ix[2] + p[2], m] + xd[0] * (s[ix[0] + p[0], ix[1] + p[1], ix[2] + p[2], m] - s[ix[0], ix[1] + p[1], ix[2] + p[2], m])
    c0 = c00 + xd[1] * (c10 - c00)
    c1 = c01 + xd[1] * (c11 - c01)
    c = c0 + xd[2] * (c1 - c0)

    return c

##
## EOF
##
