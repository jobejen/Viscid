""" module for common parallel processing """

from __future__ import print_function
import multiprocessing as mp
import multiprocessing.pool
from itertools import repeat
try:
    from itertools import izip
except ImportError:
    izip = zip

import numpy as np


# Non daemonic processes are probably a really bad idea
class NoDaemonProcess(mp.Process):
    # make 'daemon' attribute always return False
    @staticmethod
    def _get_daemon():
        return False
    def _set_daemon(self, value):
        pass
    daemon = property(_get_daemon, _set_daemon)

class NoDaemonPool(multiprocessing.pool.Pool): #pylint: disable=W0223
    """ I am vulnerable to armies of undead worker processes, chances
    are you don't actually want to use me """
    Process = NoDaemonProcess


def chunk_list(seq, nchunks):
    """
    slice seq into chunks if nchunks size, seq can be a anything sliceable
    such as lists, numpy arrays, etc. These chunks will be 'contiguous', see
    chunk_interslice for picking every nth element.

    Note: Use chunk_iterator to chunk up iterators

    Returns: nchunks slices of length N = (len(lst) // nchunks) or N - 1

    ex: it1, it2, it3 = chunk_list(range(8), 3)
    it1 == range(0, 3)  # 3 vals
    it2 == range(3, 6)  # 3 vals
    it3 == range(6, 8)  # 2 vals
    """
    nel = len(seq)
    ret = chunk_slices(nel, nchunks)
    for i in range(nchunks):
        ret[i] = seq[slice(*ret[i])]
    return ret

def chunk_slices(nel, nchunks):
    """
    Get the slice info (can be unpacked & passed to the slice builtin as in
    slice(*ret[i])) for nchunks contiguous chunks in a list with nel elements

    nel: how many elements are in one pass of the original list
    nchunks: how many chunks to make
    Returns: a list of (start, stop) tuples with length nchunks

    ex: sl1, sl2 = chunk_slices(5, 2)
    -> sl1 == (0, 3)  # 3 vals
    -> sl2 == (3, 5)  # 2 vals
    """
    nlong = nel % nchunks  # nshort guarenteed < nchunks
    lenshort = nel // nchunks
    lenlong = lenshort + 1

    ret = [None] * nchunks
    start = 0
    for i in range(nlong):
        ret[i] = (start, start + lenlong)
        start += lenlong
    for i in range(nlong, nchunks):
        ret[i] = (start, start + lenshort)
        start += lenshort
    return ret

def chunk_interslices(nchunks):
    """
    Similar to chunk_slices, but pick every nth element instead of getting
    a contiguous block for each chunk

    nchunks: how many chunks to make
    Returns: a list of (start, stop, step) tuples with length nchunks

    ex: chunk_slices(2) == [(0, None, 2), (1, None, 2)]
    """
    ret = [None] * nchunks
    for i in range(nchunks):
        ret[i] = (i, None, nchunks)
    return ret

def chunk_sizes(nel, nchunks):
    """
    nel: how many elements are in one pass of the original list
    nchunks: is inferred from the length of iter_list
    Returns: an ndarray of the number of elements in each chunk, this
             should be the same for chunk_list, chunk_slices and
             chunk_interslices

    ex: nel1, nel2 = chunk_sizes(5, 2)
    -> nel1 == 2
    -> nel2 == 3
    """
    nlong = nel % nchunks  # nshort guarenteed < nchunks
    lenshort = nel // nchunks
    lenlong = lenshort + 1
    ret = np.empty((nchunks,), dtype="int")
    ret[:nlong] = lenlong
    ret[nlong:] = lenshort
    return ret

def _star_passthrough(args):
    """ this is so we can give a zipped iterable to func """
    # args[0] is function, args[1] is positional args, and args[2] is kwargs
    return args[0](*(args[1]), **(args[2]))

def run(nr_procs, func, args_iter, timeout=1e8, daemonic=True,
        **kwargs):
    """
    run func on nr_procs with arguments given by args_iter. args_iter
    should be an iterable of the list of arguments that can be unpacked
    for each invocation. kwargs are passed to func as keyword arguments
    IMPORTANT: daemonic can be set to False if one needs to spawn child
               processes in func, BUT this could be vulnerable to creating
               an undead army of worker processes, only use this if you
               really really need it, and know what you're doing
    ex:
    func = lambda i, letter: print i, letter
    run(2, func, itertools.izip(itertools.count(), ['a', 'b', 'c']))
    will print
    0 a
    1 b
    2 c
    on two processes
    """
    args_iter = izip(repeat(func), args_iter, repeat(kwargs))
    if nr_procs == 1:
        return [_star_passthrough(args) for args in args_iter]
    else:
        if daemonic:
            pool = mp.Pool(nr_procs)
        else:
            # hope you know what you're doing if you got here
            pool = NoDaemonPool(nr_procs)
        ret = pool.map_async(_star_passthrough, args_iter).get(timeout)
        return ret

##
## EOF
##
