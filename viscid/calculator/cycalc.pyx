#cython: boundscheck=True, wraparound=True
# Note: a _c_FUNCTION can only be called from another cdef-ed function, or
# a def-ed _py_FUNCTION function because of the use of the fused real_t
# to template both float32 and float64 versions
from __future__ import print_function

import numpy as np
from .. import field
from .. import coordinate
from . import seed

cimport cython
cimport numpy as np
from libc.math cimport sqrt
from cycalc_util cimport *

#from cython.parallel import prange

import time

cdef:
    int DIR_FORWARD = 1
    int DIR_BACKWARD = 2
    int DIR_BOTH = 3  # = DIR_FORWARD | DIR_BACKWARD

def scalar3d_shape(fld):
    return list(fld.shape) + [1] * (3 - len(fld.shape))

def vector3d_shape(fld):
    return list(fld.shape) + [1] * (3 - len(fld.shape)) + [-1]


def magnitude(fld):
    if not fld.layout == field.LAYOUT_INTERLACED:
        raise ValueError("I am only written for interlaced data.")
    nptype = fld.data.dtype.name
    vect = fld.data.reshape(vector3d_shape(fld))
    mag = np.empty(scalar3d_shape(fld), dtype=nptype)
    _py_magnitude3d(vect, mag)
    mag = mag.reshape(fld.shape)
    return field.wrap_field("Scalar", fld.name + " magnitude", fld.crds, mag,
                            center=fld.center, time=fld.time,
                            forget_source=True)

def _py_magnitude3d(real_t[:,:,:,:] vect, real_t[:,:,:] mag):
    return _c_magnitude3d(vect, mag)

cdef _c_magnitude3d(real_t[:,:,:,:] vect, real_t[:,:,:] mag):
    cdef unsigned int nz = vect.shape[0]
    cdef unsigned int ny = vect.shape[1]
    cdef unsigned int nx = vect.shape[2]
    cdef unsigned int nc = vect.shape[3]
    cdef unsigned int i, j, k, c
    cdef real_t val

    for k from 0 <= k < nz:
        for j from 0 <= j < ny:
            for i from 0 <= i < nx:
                val = 0.0
                for c from 0 <= c < nc:
                    val += vect[k, j, i, c]**2
                mag[k,j,i] = sqrt(val)
    return None

def div(fld):
    if not fld.layout == field.LAYOUT_INTERLACED:
        raise ValueError("Div is only written for interlaced data.")
    if fld.dim != 3:
        raise ValueError("Div is only written in 3D.")

    nptype = fld.data.dtype.name
    vect = fld.data

    if fld.center == "Cell":
        crdz, crdy, crdx = fld.crds.get_cc()
        divcenter = "Cell"
        divcrds = coordinate.RectilinearCrds(fld.crds.get_clist(np.s_[1:-1]))
        dest_shape = [n - 2 for n in fld.crds.shape_cc]
        div_arr = np.empty(dest_shape, dtype=nptype)
    elif fld.center == "Node":
        crdz, crdy, crdx = fld.crds.get_nc()
        divcenter = "Node"
        divcrds = coordinate.RectilinearCrds(fld.crds.get_clist(np.s_[1:-1]))
        dest_shape = [n - 2 for n in fld.crds.shape_nc]
        div_arr = np.empty(dest_shape, dtype=nptype)
    else:
        raise NotImplementedError("Can only do cell and node centered divs")

    if crdx.dtype != nptype or crdy.dtype != nptype or crdz.dtype != nptype:
        raise TypeError("Coords must be same dtype as vector data")

    _py_div3d(vect, crdx, crdy, crdz, div_arr)

    return field.wrap_field("Scalar", fld.name + " div", divcrds, div_arr,
                            center=divcenter, time=fld.time,
                            forget_source=True)

def _py_div3d(real_t[:,:,:,:] vect, real_t[:] crdx, real_t[:] crdy,
               real_t[:] crdz, real_t[:,:,:] div_arr):
    return _c_div3d(vect, crdx, crdy, crdz, div_arr)

cdef _c_div3d(real_t[:,:,:,:] vect, real_t[:] crdx, real_t[:] crdy,
              real_t[:] crdz, real_t[:,:,:] div_arr):
    cdef unsigned int nz = div_arr.shape[0]
    cdef unsigned int ny = div_arr.shape[1]
    cdef unsigned int nx = div_arr.shape[2]
    cdef unsigned int i, j, k
    cdef real_t val

    for k from 0 <= k < nz:
        for j from 0 <= j < ny:
            for i from 0 <= i < nx:
                # Note, the centering for the crds isnt correct here
                div_arr[k, j, i] = (vect[k, j, i + 2, 0] - vect[k, j, i, 0]) / \
                                                     (crdx[i + 2] - crdx[i]) + \
                                   (vect[k, j + 2, i, 1] - vect[k, j, i, 1]) / \
                                                     (crdy[j + 2] - crdy[j]) + \
                                   (vect[k + 2, j, i, 2] - vect[k, j, i, 2]) / \
                                                     (crdz[k + 2] - crdz[k])
    return None

def _py_closest_ind(real_t[:] crd, real_t point):
    """ returns the integer such that crd[i] < point < crd[i+1] """
    return _c_closest_ind(crd, point)

cdef int _c_closest_ind(real_t[:] crd, real_t point) except -1:
    cdef int i
    cdef unsigned int n = crd.shape[0]

    # search linearly... maybe branch prediction makes this better
    # than bisection for smallish arrays...
    # TODO: make this work for arrays that go backward
    for i from 1 <= i < n:
        if crd[i] >= point:
            return i - 1
    if crd.shape[0] >= 2:
        return crd.shape[0] - 2  # if we've gone too far, pick the last index
    else:  # crd.shape[0] <= 1
        return 0


def _py_trilin_interp(real_t[:,:,:] s, real_t[:] crdz, real_t[:] crdy,
                      real_t[:] crdx, real_t[:] x):
    """ return the scalar value of 3d scalar array s trilinearly interpolated
    to the point x (in z, y, x order) """
    return _c_trilin_interp(s, crdz, crdy, crdx, x)

cdef real_t _c_trilin_interp(real_t[:,:,:] s, real_t[:] crdz,
                             real_t[:] crdy, real_t[:] crdx, real_t[:] x):
    cdef int i, ind
    cdef int[3] ix
    cdef int[3] p  # increment, used for 2d fields
    cdef real_t[3] xd
    cdef real_t[3] xdm  # will be 1 - xd
    cdef real_t c00, c10, c01, c11, c0, c1, c

    zp = 1 if crdz.shape[0] > 1 else 0
    yp = 1 if crdy.shape[0] > 1 else 0
    xp = 1 if crdx.shape[0] > 1 else 0

    for i, crd in enumerate([crdz, crdy, crdx]):
        ind = _c_closest_ind[real_t](crd, x[i])
        ix[i] = ind
        # this bit to support 2d fields could probably be handled
        # more efficiently
        if crd.shape[0] > 1:
            p[i] = 1
            xd[i] = (x[i] - crd[ind]) / (crd[ind + 1] - crd[ind])
        else:
            p[i] = 0
            xd[i] = 1.0
        xdm[i] = 1.0 - xd[i]

    # this algorithm is shamelessly taken from the trilinear interpolation
    # wikipedia article
    c00 = s[ix[0]       , ix[1]       , ix[2]       ] * xdm[0] + \
          s[ix[0] + p[0], ix[1]       , ix[2]       ] * xd[0]
    c10 = s[ix[0]       , ix[1] + p[1], ix[2]       ] * xdm[0] + \
          s[ix[0] + p[0], ix[1] + p[1], ix[2]       ] * xd[0]
    c01 = s[ix[0]       , ix[1]       , ix[2] + p[2]] * xdm[0] + \
          s[ix[0] + p[0], ix[1]       , ix[2] + p[2]] * xd[0]
    c11 = s[ix[0]       , ix[1] + p[1], ix[2] + p[2]] * xdm[0] + \
          s[ix[0] + p[0], ix[1] + p[1], ix[2] + p[2]] * xd[0]
    c0 = c00 * xdm[1] + c10 * xd[1]
    c1 = c01 * xdm[1] + c11 * xd[1]
    c = c0 * xdm[2] + c1 * xd[2]
    return c

cdef int _c_euler1(real_t[:,:,:,:] s, real_t[:] crdz, real_t[:] crdy,
                         real_t[:] crdx, real_t ds, real_t[:] x) except -1:
    vx = _c_trilin_interp[real_t](s[...,0], crdz, crdy, crdx, x)
    vy = _c_trilin_interp[real_t](s[...,1], crdz, crdy, crdx, x)
    vz = _c_trilin_interp[real_t](s[...,2], crdz, crdy, crdx, x)
    vmag = sqrt(vx**2 + vy**2 + vz**2)
    if vmag == 0.0:
        return 1
    x[0] += ds * vz / vmag
    x[1] += ds * vy / vmag
    x[2] += ds * vx / vmag
    return 0

# cdef real_t _c_rk4(real_t[:,:,:] s, real_t[:] crdz, real_t[:] crdy,
#                       real_t[:] crdx, real_t[:] x):
#     _c_trilin_interp[real_t](s, crdz, crdy, crdx, x)
#     return x[0]

# cdef real_t _c_rk45(real_t[:,:,:] s, real_t[:] crdz, real_t[:] crdy,
#                        real_t[:] crdx, real_t[:] x):
#     return x[0]

def streamlines(fld, seeds, *args, **kwargs):
    if not fld.layout == field.LAYOUT_INTERLACED:
        raise ValueError("Streamlines only written for interlaced data.")
    if fld.dim != 3:
        raise ValueError("Streamlines are only written in 3D.")
    nptype = fld.data.dtype.name

    dat = fld.data
    crdz, crdy, crdx = fld.crds.get_cc()

    if isinstance(seeds, seed.SeedGen):
        x0 = seeds.points
    else:
        x0 = np.array(seeds, dtype=dat.dtype).reshape((-1, 3))

    lines = []
    for start in x0:
        line = _py_streamline(dat, crdz, crdy, crdx,
                              start, *args, **kwargs)
        lines.append(line)
    return lines

def _py_streamline(real_t[:,:,:,:] v_arr, real_t[:] crdz, real_t[:] crdy,
                   real_t[:] crdx, real_t[:] x0, ds0=-1.0, ibound=0.0,
                   obound0=None, obound1=None, dir=DIR_BOTH, maxit=10000):
    """ Start calculating a streamline at x0
    dir:         DIR_FORWARD, DIR_BACKWARD, DIR_BOTH
    ibound:      stop streamline if within inner_bound of the origin
                 ignored if 0
    obound0:     corner of box beyond which to stop streamline (smallest values)
    obound1:     corner of box beyond which to stop streamline (smallest values)
    ds0:         initial spatial step for the streamline """
    cdef:
        # cdefed versions of arguments
        real_t c_ds0 = ds0
        real_t c_ibound = ibound
        real_t c_obound0_arr[3]
        real_t c_obound1_arr[3]
        real_t[:] c_obound0 = c_obound0_arr
        real_t[:] c_obound1 = c_obound1_arr
        real_t[:] py_obound0
        real_t[:] py_obound1
        int c_dir = dir
        int c_maxit = maxit

        # just for c
        int i, j, it
        int ret
        int done
        real_t s_arr[3]
        real_t[:] s = s_arr
        real_t px, py, pz
        real_t d
        real_t rsq, distsq

    line = []

    if obound0 is None:
        c_obound0[0] = crdz[0]
        c_obound0[1] = crdy[0]
        c_obound0[2] = crdx[0]
    else:
        py_obound0 = obound0
        c_obound0[...] = py_obound0

    if obound0 is None:
        c_obound1[0] = crdz[-1]
        c_obound1[1] = crdy[-1]
        c_obound1[2] = crdx[-1]
    else:
        py_obound1 = obound1
        c_obound1[...] = py_obound1

    if c_ds0 <= 0.0:
        # FIXME: calculate something reasonable here
        c_ds0 = 0.01

    lseg = [[[x0[0], x0[1], x0[2]]], []]
    for i, d in enumerate([-1.0, 1.0]):
        if d < 0 and not (c_dir & DIR_BACKWARD):
            continue
        elif d > 0 and not (c_dir & DIR_FORWARD):
            continue

        ds = d * c_ds0

        s[0] = x0[0]
        s[1] = x0[1]
        s[2] = x0[2]

        it = 0
        done = 0
        while it <= c_maxit:
            # print("point (x, y, z): ", s[2], s[1], s[0])
            # components run x, y, z, but coords run z, y, x
            ret = _c_euler1[real_t](v_arr, crdz, crdy, crdx, ds, s)
            # ret is non 0 when |varr| == 0
            if ret != 0:
                done = 1
                break

            lseg[i].append([s[0], s[1], s[2]])
            it += 1

            # end conditions
            rsq = s[0]**2 + s[1]**2 + s[2]**2

            # hit the inner boundary
            if rsq <= c_ibound**2:
                # print("inner boundary")
                done = 1
                break

            for j from 0 <= j < 3:
                # hit the outer boundary
                if s[j] <= c_obound0[j] or s[j] >= c_obound1[j]:
                    # print("outer boundary")
                    done = 1
                    break

            # if we are within 0.99 * ds0 of the initial position
            distsq = (x0[0] - s[0])**2 + (x0[1] - s[1])**2 + (x0[2] - s[2])**2
            if distsq < (0.99 * ds0)**2:
                # print("cyclic field line")
                done = 1
                break

            if done:
                break
        if not done:
            pass
            # print("maxit")

    # reverse the 'backward' line segment
    # print("-- first: ", lseg[0][:4], " last: ", lseg[0][-4:])
    # print("++ first: ", lseg[1][:4], " last: ", lseg[1][-4:])
    line = (lseg[0][::-1] + lseg[1])
    return line


    # _c_streamline(v_arr, crdz, crdy, crdx, x, dir, inner_bound, cbound0, cbound1,
    #               ds0)
# cdef _c_streamline(real_t[:,:,:,:] v_arr, real_t[:] crdz, real_t[:] crdy,
#                    real_t[:] crdx, real_t[:] x, dir, real_t inner_bound,
#                    real_t[:] cbound0, real_t[:] cbound1, ds0):
#     real_t[3] v


# def make_real(np.ndarray arr):
#     return

# def _ind(real_t x, real_t y, real_t z, real_t[:] crdx, real_t[:] crdy,
#          real_t[:] crdz):
#     """ """
#     cdef unsigned int nx = len(crdx)
#     cdef unsigned int ny = len(crdy)
#     cdef unsigned int nz = len(crdz)


# cdef np.ndarray[real_t, ndim=4] calc_div1(np.ndarray[real_t, ndim=4] arr):# except 0:
#     cdef unsigned int nz = arr.shape[0]
#     cdef unsigned int ny = arr.shape[1]
#     cdef unsigned int nx = arr.shape[2]
#     cdef unsigned int nc = arr.shape[3]  # number of components
#     cdef unsigned int i, j, k, c
#     cdef double val

#     cdef np.ndarray[real_t, ndim=4] div = np.empty([nz, ny, nx, 1], dtype=arr.dtype)
#     # print(nz, ny, nx, nc)
#     for i from 0 <= i < nz:
#         for j from 0 <= j < ny:
#             for k from 0 <= k < nx:
#                 val = 0.0
#                 for c from 0 <= c < nc:
#                     val += arr[i,j,k,c]**2
#                 div[i,j,k,0] = sqrt(val)
#     return div

# def print_arr(np.ndarray[np.float64_t, ndim=3] arr):
#     c_print_arr(<double*>arr.data, arr.size)
#     print(arr.flags)

# cdef void c_print_arr(double *arr, int N):
#     for i in range(N):
#         print("{0} ".format(arr[i]))
