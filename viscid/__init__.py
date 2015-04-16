""" A set of pure python modules that aid in plotting gridded scientific data.
Plotting depends on matplotlib and/or mayavi and file reading uses h5py and
to read hdf5 / xdmf files.
"""

__all__ = ['calculator',
           'plot',
           'readers',
           'bucket',
           'coordinate',
           'dataset',
           'field',
           'grid',
           'parallel',
           'verror',
           'vlab',
           'vutil',
           'vjson'
          ]

import logging
logger = logging.getLogger("viscid")
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter())
logger.addHandler(_handler)
del _handler

from viscid import readers
load_file = readers.load_file
load_files = readers.load_files
get_file = readers.get_file
save_grid = readers.save_grid
save_field = readers.save_field

from viscid import rc
rc.load_rc_file("~/.viscidrc")