# Changelog

## 0.80.7 dev



## 0.80.6

Changes:
  - Ascii dataset field names are now "c[0-9]+" where the number is the column number
  - Add a way to generate your own cubehelix colormaps
  - Sphinx has no more warnings

## 0.80.5

Features:
  - add amr_field.patch_indices to lookup patch index at a location

Bugfixes:
  - AMR slicing bugs

## 0.80.4

Bugfixes:
  - ./setup.py install wasn't installing parsers
  - command line utilities had bugs

## 0.80.3

Bugfixes:
  - Fix size of earth in AMR files
  - Fix matplotlib colorscale options

## 0.80.2

Features:
  - RC file and plot_opts can be given in Yaml syntax if user has PyYaml, otherwise the rc file has to be JSON and the plot_opts have to use the weird comma/space syntax

Bugfixes:
  - amr fields now work with command line utils

## 0.80.1

Bugfix:
  - vjson not found

## 0.80.0

Features:
  - preliminary amr support (1D and 2D matplotlib plots)

Backward Incompatible Changes:
  - rc file is now in JSON format (in the future, this should change to YAML, but JSON is a subset of YAML, so it shouldn't break in the future)

Changes:
  - 1:1 match between plot_opts and plot keyword arguments

Bugfixes:
  - Ionosphere files wouldn't plot with pcolormesh

## 0.60.3

Features:
  - thousands of jrrle files load fast over sshfs
  - when loading xdmf files, one can specify a root directory for hdf5 files
    so one can copy xdmf files locally and read the hdf5 files over sshfs

Changes:
  - Lots of little bugfixes

## 0.60.2

Features:
  - The attribute `grid.Grid.longterm_field_caches` controls how long caches hang around
  - Athena binary / ascii / hst readers (doesn't read SMR grids)
  - Can hyperslice into xdmf/HDF5 datasets so only data that is needed is read
  - Slicing in time can now take H:M:S styled times
  - New ways to print / get the time of a Dataset/Grid/Field
    - `format_time`
    - `time_as_datetime`

Changes:
  - Spatial slices completely rewritten
  - info dicts (for Datasets/Grids/Fields) are now private
    - `get_info(key)`: gets info from a specific object
    - `find_info(key)`: gets info from an object, or its parents
    - `set_info(key)`: sets info for an object
    - `update_info(key)`: updates info wherever in the tree it exists

Other:
  - Customization attributes have their own sphinx page for easy lookup
  - performance enhancements when globbing files on a remote server

## 0.60.1

Bugfix:
  - Time slices were acting silly

## 0.60.0

Features:
  - Implement Ionosphere reading / plotting
  - Implement a Jrrle Openggcm Reader

Backward Incompatible Changes:
  - CHANGE FIELD SLICING SYNTAX! No more trailing 'i' to slice by index. Instead, use an integer to mean an index. For slicing by coordinate value, the decimal now needs to be explicit, so all code that slices like "y=0" now needs to be refactored to "y=0.0"

## 0.50.2

Features:
  - Support for custom grids (this allows for custom readers for GGCM / PSC / etc)
  - Grids can supply derived fields by defining _get_varname
  - Grids can supply generic transformations for fields / crds on load
  - GGCM reader, can translate MHD coordinate system to GSE using `viscid.readers.openggcm.GGCMGrid.mhd_to_gse_on_read = True`
  - PSC reader can calculate psi (flux function)

Refactors:
  - RectilinearCrds -> NonuniformCartesianCrds
  - "Rectilinear" -> "nonuniform_cartesian"

Backward Incompatible Changes:
  - kwargs to field constructors go to deep_meta dict if they start with a '_', else they go to the info dict

Other:
  - Precedence for auto-detecting classes is given to those more recently declared

## 0.50.1

Features:
  - Field slicing semantics are now the same as numpy in terms of when dimensions get reduced. To enforce specific reductions, use Field.slice_reduce() or Field.slice_keep()
  - crds accessible from grids / fields / crds using get_crd_[ncef]c or get_crds_[ncef]c for one or multiple crds respectively
  - rewrite fields to a cleaner, unified interface
  - stringy typed things should be case insensitive if compared with the provided methods (istype() and iscentered()), otherwise everything is lowercase
  - field properties are now even lazier and cachier
  - add reader for 1d gnuplot like files
  - add reader for numpy binary npz files (can also save a list of fields)
  - add super preliminary support for writing hdf5 files with companion xdmf file, still no direct hdf5 reading
  - add pretty_name kwarg to field constructor, this is the name that will appear in plot labels

Refactors:
  - filed.n_points -> filed.nr_points
  - filed.n_comps -> filed.nr_comps
  - grid / dataset n_times -> nr_times
  - trilin_interp -> interp_trilin
  - keyword arg cc_slice -> cc

Backward Incompatible Changes:
  - Coordinate.get_crd used to take a list, now that use case has to call Coordinate.get_crds

Deprecated:
  - readers.load() -> readers.load_file("...") or readers.load_files(["..."])

## 0.50.0 Release

Features:
  - Remove lxml dependency
  - Remove Cython dependency
  - Works with the older Python 2.6