"""Convenience module for making matplotlib plots

Your best friend in this module is the :meth:`plot` function, but the
best reference for all quirky options is :meth:`plot2d_field`.

Note:
    You can't set rc parameters for this module!
"""

# FIXME: this module is way too long

from __future__ import print_function
from distutils.version import LooseVersion
from itertools import count

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize, LogNorm
try:
    from mpl_toolkits.basemap import Basemap  # pylint: disable=no-name-in-module
    _HAS_BASEMAP = True
except ImportError:
    _HAS_BASEMAP = False

import viscid
from viscid import pyeval
from viscid import logger
from viscid.compat import izip, string_types
from viscid import coordinate
from viscid.plot import mpl_extra
from viscid.plot import vseaborn

__mpl_ver__ = matplotlib.__version__
has_colorbar_gridspec = LooseVersion(__mpl_ver__) > LooseVersion("1.1.1")
vseaborn.activate_from_viscid()

if mpl_extra.default_cmap:
    plt.rcParams['image.cmap'] = mpl_extra.default_cmap


def plot(fld, selection=":", force_cartesian=False, **kwargs):
    """Plot a field by dispatching to the most appropiate funciton

    * If fld has 1 spatial dimensions, call
      :meth:`plot1d_field(fld[selection], **kwargs)`
    * If fld has 2 spatial dimensions, call
      :meth:`plot2d_field(fld[selection], **kwargs)`
    * If fld is 2-D and has spherical coordinates (as is the case for
      ionospheric fields), try to use :meth:`plot2d_mapfield` which
      uses basemap to make its axes.

    Parameters:
        fld (Field): Some Field
        selection (optional): something that describes a field slice
        force_cartesian (bool): if false, then spherical plots will use
            plot_mapfield
        **kwargs: Passed on to plotting function

    Returns:
        tuple: (plot, colorbar)
            plot: matplotlib plot object
            colorbar: matplotlib colorbar object

    See Also:
        * :meth:`plot1d_field`: target for 1d fields
        * :meth:`plot2d_mapfield`: target for 2d spherical fields
        * :meth:`plot2d_field`: target for 2d fields

    Note:
        Field slices are done using "slice_reduce", meaning extra
        dimensions are reduced out.

    Raises:
        TypeError: Description
        ValueError: Description
    """
    fld = fld.slice_reduce(selection)

    if not hasattr(fld, "patches"):
        raise TypeError("Selection '{0}' sliced away too many "
                        "dimensions".format(selection))
    if fld.nr_comps > 1:
        raise TypeError("Scalar Fields only")

    patch0 = fld.patches[0]
    nr_sdims = patch0.nr_sdims
    if nr_sdims == 1:
        return plot1d_field(fld, **kwargs)
    elif nr_sdims == 2:
        is_spherical = patch0.is_spherical()
        if is_spherical and not force_cartesian:
            return plot2d_mapfield(fld, **kwargs)
        else:
            return plot2d_field(fld, **kwargs)
    else:
        raise ValueError("mpl can only do 1-D or 2-D fields. Either slice the "
                         "field yourself, or use the selection keyword "
                         "argument")

def plot_opts_to_kwargs(plot_opts, plot_kwargs):
    """Turn plot options from string to items in plot_kwargs

    The Reason for this to to be able to specify arbitrary plotting
    kwargs from the command line

    Args:
        plot_opts (str): plot kwargs as string
        plot_kwargs (dict): kwargs to be popped by hand or passed to
            plotting function

    Returns:
        None, the plot_opts are stuffed into plot_kwargs
    """
    if not plot_opts:
        return

    plot_opts = plot_opts.strip()
    if plot_opts[0] == '{' and plot_opts[-1] == '}':
        try:
            import yaml
            d = yaml.load(plot_opts)
            # if an option is given without a value, Yaml defaults to
            # None, but it was probably a flag, so turn None -> True
            for k in list(d.keys()):
                if d[k] is None:
                    d[k] = True
            plot_kwargs.update(d)
        except ImportError:
            raise ImportError("You gave plot options in YAML syntax, but "
                              "PyYaml is not installed. Either install PyYaml "
                              "or use the old comma/underscore syntax.")
    else:
        plot_opts = plot_opts.split(",")

        for opt in plot_opts:
            opt = opt.replace("=", "_").split("_")
            opt[0] = opt[0].strip()
            opt[1:] = [pyeval.parse(o) for o in opt[1:]]
            if len(opt) == 0 or opt == ['']:
                continue
            elif len(opt) == 1:
                plot_kwargs[opt[0]] = True
            elif len(opt) == 2:
                plot_kwargs[opt[0]] = opt[1]
            else:
                # if opt[1:] are all strings, re-combine them since some legit
                # options have underscores in them, like reversed cmap names
                try:
                    opt[1:] = "_".join(opt[1:])
                except TypeError:
                    pass
                plot_kwargs[opt[0]] = opt[1:]


def _extract_actions_and_norm(axis, plot_kwargs, defaults=None):
    """
    Some plot options will want to call a function after the plot is
    made, like setting xlim and the like. Those are 'actions'.

    Args:
        axis: matplotlib axis for current plot
        plot_kwargs (dict): kwargs dict containing all the options for
            the current plot
        defaults (dict): default values to merge plot_kwargs into

    Returns:
        (actions, norm_dict)

        actions: list of tuples... the first erement of the tuple is
            a function to call, while the 2nd is a list of arguments
            to unpack when calling that function

        norm_dict: will look like {'crdscale': 'lin'|'log',
                                   'vscale': 'lin'|'log|none',
                                   'clim': [None|number, None|number],
                                   'symmetric': True|False}
    """
    for k, v in defaults.items():
        if k not in plot_kwargs:
            plot_kwargs[k] = v

    actions = []
    if not axis:
        axis = plt.gca()

    if "equalaxis" in plot_kwargs:
        if plot_kwargs.pop('equalaxis'):
            actions.append((axis.axis, 'equal'))
    if "x" in plot_kwargs:
        actions.append((axis.set_xlim, plot_kwargs.pop('x')))
    if "y" in plot_kwargs:
        actions.append((axis.set_ylim, plot_kwargs.pop('y')))
    if "own" in plot_kwargs:
        opt = plot_kwargs.pop('own')
        logger.warn("own axis doesn't seem to work yet...")
    if "ownx" in plot_kwargs:
        opt = plot_kwargs.pop('ownx')
        logger.warn("own axis doesn't seem to work yet...")
    if "owny" in plot_kwargs:
        opt = plot_kwargs.pop('owny')
        logger.warn("own axis doesn't seem to work yet...")

    norm_dict = {'crdscale': 'lin',
                 'vscale': 'lin',
                 'clim': [None, None],
                 'symmetric': False
                }

    if plot_kwargs.pop('logscale', False):
        norm_dict['vscale'] = 'log'

    if "clim" in plot_kwargs:
        clim = plot_kwargs.pop('clim')
        norm_dict['clim'][:len(clim)] = clim

    if "vmin" in plot_kwargs:
        norm_dict['clim'][0] = plot_kwargs.pop('vmin')

    if "vmax" in plot_kwargs:
        norm_dict['clim'][1] = plot_kwargs.pop('vmax')

    sym = plot_kwargs.pop('symmetric', False)
    sym = plot_kwargs.pop('sym', False) or sym
    norm_dict['symmetric'] = sym

    # parse shorthands for specifying color scale
    if "lin" in plot_kwargs:
        opt = plot_kwargs.pop('lin')
        norm_dict['vscale'] = 'lin'
        if opt == 0:
            norm_dict['symmetric'] = True
        elif opt is not True:
            if not isinstance(opt, (list, tuple)):
                opt = [opt]
            norm_dict['clim'][:len(opt)] = opt
    if "log" in plot_kwargs:
        opt = plot_kwargs.pop('log')
        norm_dict['vscale'] = 'log'
        if opt is not True:
            if not isinstance(opt, (list, tuple)):
                opt = [opt]
            norm_dict['clim'][:len(opt)] = opt
    if "loglog" in plot_kwargs:
        opt = plot_kwargs.pop('loglog')
        norm_dict['crdscale'] = 'log'
        norm_dict['vscale'] = 'log'
        if opt is not True:
            if not isinstance(opt, (list, tuple)):
                opt = [opt]
            norm_dict['clim'][:len(opt)] = opt

    # replace 'None' or 'none' with None in clim, this is kinda hacky, non?
    for i in range(len(norm_dict['clim'])):
        if norm_dict['clim'][i] in ["None", "none"]:
            norm_dict['clim'][i] = None

    # hack so that the value axis is not rescaled
    if plot_kwargs.pop('norescale', False):
        norm_dict['vscale'] = None

    return actions, norm_dict

def _apply_actions(acts):
    for act in acts:
        act_args = act[1]
        if not isinstance(act_args, (list, tuple)):
            act_args = [act_args]
        act[0](*act_args)

def _apply_axfmt(ax, majorfmt=None, minorfmt=None, majorloc=None, minorloc=None,
                 which_axes="xy"):
    ax_axes = {'x': ax.xaxis, 'y': ax.yaxis}

    if majorfmt == "steve":
        majorfmt = mpl_extra.steve_axfmt
    if minorfmt == "steve":
        minorfmt = mpl_extra.steve_axfmt

    for axis_name in which_axes:
        _axis = ax_axes[axis_name]

        if majorfmt:
            _axis.set_major_formatter(majorfmt)
        if minorfmt:
            _axis.set_minor_formatter(minorfmt)

        if majorloc:
            _axis.set_major_locator(majorloc)
        if minorloc:
            _axis.set_minor_locator(minorloc)

def _plot2d_single(ax, fld, style, namex, namey, mod, scale,
                   masknan, latlon, flip_plot, patchec, patchlw, patchaa,
                   all_masked, extra_args, **kwargs):
    """Make a 2d plot of a single patch

    Returns:
        result of the actual matplotlib plotting command
        (pcolormesh, contourf, etc.)
    """
    assert fld.nr_patches == 1

    # pcolor mesh uses node coords, and cell data, if we have
    # node data, fake it by using cell centered coords and
    # trim the edges of the data... maybe i should just be
    # extapolating the crds and keeping the edges...
    if style in ["pcolormesh", "pcolor"]:
        fld = fld.as_cell_centered()
        X, Y = fld.get_crds_nc((namex, namey))
    else:
        if fld.iscentered("Node"):
            X, Y = fld.get_crds_nc((namex, namey))
        elif fld.iscentered("Cell"):
            X, Y = fld.get_crds_cc((namex, namey))
            # this is a hack to get rid or the white space
            # between patches when contouring
            Xnc, Ync = fld.get_crds_nc((namex, namey))
            X[0], X[-1] = Xnc[0], Xnc[-1]
            Y[0], Y[-1] = Ync[0], Ync[-1]

    if latlon:
        # translate latitude from 0..180 to -90..90
        X, Y = np.meshgrid(X, 90 - Y)
    if mod:
        X *= mod[0]
        Y *= mod[1]

    dat = fld.data.T
    if scale is not None:
        dat *= scale
    if masknan:
        dat = np.ma.masked_where(np.isnan(dat), dat)
        all_masked = all_masked and dat.mask.all()

    # Field.data is now xyz as are the crds

    if flip_plot:
        X, Y = Y.T, X.T
        dat = dat.T
        namex, namey = namey, namex

    if style == "pcolormesh":
        p = ax.pcolormesh(X, Y, dat, *extra_args, **kwargs)
    elif style == "contour":
        p = ax.contour(X, Y, dat, *extra_args, **kwargs)
    elif style == "contourf":
        p = ax.contourf(X, Y, dat, *extra_args, **kwargs)
    elif style == "pcolor":
        p = ax.pcolor(X, Y, dat, *extra_args, **kwargs)
    else:
        raise RuntimeError("I don't understand {0} 2d plot style".format(style))

    try:
        if masknan:
            p.get_cmap().set_bad(masknan)
        else:
            raise ValueError()
    except ValueError:
        p.get_cmap().set_bad('y')

    # show patches?
    if patchec and patchlw:
        _xl = X[0]
        _yl = Y[0]
        _width = X[-1] - _xl
        _height = Y[-1] - _yl
        rect = plt.Rectangle((_xl, _yl), _width, _height,
                             edgecolor=patchec, linewidth=patchlw,
                             fill=False, antialiased=patchaa, zorder=5)
        ax.add_artist(rect)

    return p, all_masked

def plot2d_field(fld, ax=None, plot_opts=None, **plot_kwargs):
    """Plot a 2D Field using pcolormesh, contour, etc.

    Parameters:
        ax (matplotlib axis, optional): Plot in a specific axis object
        plot_opts (str, optional): plot options
        **plot_kwargs (str, optional): plot options

    Returns:
        (plot_object, colorbar_object)

    See Also:
        * :doc:`/plot_options`: Contains a full list of plot options
    """
    patch0 = fld.patches[0]
    if patch0.nr_sdims != 2:
        raise RuntimeError("I will only contour a 2d field")

    # raise some deprecation errors
    if "extra_args" in plot_kwargs:
        raise ValueError("extra_args is deprecated and for internal use only")

    # init the plot by figuring out the options to use
    extra_args = []

    if not ax:
        ax = plt.gca()

    # parse plot_opts
    plot_opts_to_kwargs(plot_opts, plot_kwargs)
    actions, norm_dict = _extract_actions_and_norm(ax, plot_kwargs,
                                                   defaults={'equalaxis': True})

    # everywhere options
    scale = plot_kwargs.pop("scale", None)
    masknan = plot_kwargs.pop("masknan", True)
    flip_plot = plot_kwargs.pop("flip_plot", False)
    flip_plot = plot_kwargs.pop("flipplot", flip_plot)
    nolabels = plot_kwargs.pop("nolabels", False)
    xlabel = plot_kwargs.pop("xlabel", None)
    ylabel = plot_kwargs.pop("ylabel", None)
    majorfmt = plot_kwargs.pop("majorfmt", mpl_extra.default_majorfmt)
    minorfmt = plot_kwargs.pop("minorfmt", mpl_extra.default_minorfmt)
    majorloc = plot_kwargs.pop("majorloc", mpl_extra.default_majorloc)
    minorloc = plot_kwargs.pop("minorloc", mpl_extra.default_minorloc)
    show = plot_kwargs.pop("show", False)

    # 2d plot options
    style = plot_kwargs.pop("style", "pcolormesh")
    levels = plot_kwargs.pop("levels", 10)
    show_grid = plot_kwargs.pop("show_grid", False)
    show_grid = plot_kwargs.pop("g", show_grid)
    gridec = plot_kwargs.pop("gridec", None)
    gridlw = plot_kwargs.pop("gridlw", 0.25)
    gridaa = plot_kwargs.pop("gridaa", True)
    show_patches = plot_kwargs.pop("show_patches", False)
    show_patches = plot_kwargs.pop("p", show_patches)
    patchec = plot_kwargs.pop("patchec", None)
    patchlw = plot_kwargs.pop("patchlw", 0.25)
    patchaa = plot_kwargs.pop("patchaa", True)
    mod = plot_kwargs.pop("mod", None)
    colorbar = plot_kwargs.pop("colorbar", True)
    cbarlabel = plot_kwargs.pop("cbarlabel", None)
    earth = plot_kwargs.pop("earth", False)

    # undocumented options
    latlon = plot_kwargs.pop("latlon", None)
    norm = plot_kwargs.pop("norm", None)
    action_ax = plot_kwargs.pop("action_ax", ax)  # for basemap projections

    # some plot_kwargs need a little more info
    if show_grid:
        if not isinstance(show_grid, string_types):
            show_grid = 'k'
        if not gridec:
            gridec = show_grid
    if gridec and gridlw:
        plot_kwargs["edgecolors"] = gridec
        plot_kwargs["linewidths"] = gridlw
        plot_kwargs["antialiased"] = gridaa

    if show_patches:
        if not isinstance(show_patches, string_types):
            show_patches = 'k'
        if not patchec:
            patchec = show_patches

    if colorbar:
        if not isinstance(colorbar, dict):
            colorbar = {}
    else:
        colorbar = None

    #########################
    # figure out the norm...
    if norm is None:
        vscale = norm_dict['vscale']
        vmin, vmax = norm_dict['clim']

        if vmin is None:
            vmin = np.nanmin([np.nanmin(blk) for blk in fld.patches])
        if vmax is None:
            vmax = np.nanmax([np.nanmax(blk) for blk in fld.patches])

        # vmin / vmax will only be nan if all values are nan
        if np.isnan(vmin) or np.isnan(vmax):
            logger.warn("All-Nan encountered in Field, {0}"
                        "".format(patch0.name))
            vmin, vmax = 1e38, 1e38
            norm_dict['symmetric'] = False

        if vscale == "lin":
            if norm_dict['symmetric']:
                maxval = max(abs(vmin), abs(vmax))
                vmin = -1.0 * maxval
                vmax = +1.0 * maxval
            norm = Normalize(vmin, vmax)
        elif vscale == "log":
            if norm_dict['symmetric']:
                raise ValueError("Can't use symmetric color bar with logscale")
            if vmax <= 0.0:
                logger.warn("Using log scale on a field with no "
                            "positive values")
                vmin, vmax = 1e-20, 1e-20
            elif vmin <= 0.0:
                logger.warn("Using log scale on a field with values "
                            "<= 0. Only plotting 4 decades.")
                vmin, vmax = vmax / 1e4, vmax
            norm = LogNorm(vmin, vmax)
        elif vscale is None:
            norm = None
        else:
            raise ValueError("Unknown norm vscale: {0}".format(vscale))

        if norm is not None:
            plot_kwargs['norm'] = norm
    else:
        if isinstance(norm, Normalize):
            vscale = "lin"
        elif isinstance(norm, LogNorm):
            vscale = "log"
        else:
            raise TypeError("Unrecognized norm type: {0}".format(type(norm)))
        vmin, vmax = norm.vmin, norm.vmax

    if "cmap" not in plot_kwargs and np.isclose(vmax, -1 * vmin):
        # by default, the symmetric_cmap is seismic (blue->white->red)
        if mpl_extra.symmetric_cmap:
            plot_kwargs['cmap'] = plt.get_cmap(mpl_extra.symmetric_cmap)
        symmetric_vlims = True
    else:
        symmetric_vlims = False

    # ok, here's some hackery for contours
    if style in ["contourf", "contour"]:
        if isinstance(levels, int):
            if vscale == "log":
                levels = np.logspace(np.log10(vmin), np.log10(vmax), levels)
            else:
                levels = np.linspace(vmin, vmax, levels)
        extra_args = [levels]

    ##############################
    # now actually make the plots
    namex, namey = patch0.crds.axes # fld.crds.get_culled_axes()

    all_masked = False
    for patch in fld.patches:
        p, all_masked = _plot2d_single(action_ax, patch, style,
                                       namex, namey, mod, scale, masknan,
                                       latlon, flip_plot,
                                       patchec, patchlw, patchaa,
                                       all_masked, extra_args, **plot_kwargs)

    # apply option actions... this is for setting xlim / xscale / etc.
    _apply_actions(actions)

    if norm_dict['crdscale'] == 'log':
        ax.set_xscale('log')
        ax.set_yscale('log')

    # figure out the colorbar...
    if style == "contour":
        if "colors" in plot_kwargs:
            colorbar = None
    if colorbar is not None:
        # unless otherwise specified, use_gridspec for colorbar
        if "use_gridspec" not in colorbar:
            colorbar["use_gridspec"] = True

        if "ticks" not in colorbar:
            if vscale == "log":
                colorbar["ticks"] = matplotlib.ticker.LogLocator()
            elif symmetric_vlims:
                colorbar["ticks"] = matplotlib.ticker.MaxNLocator()
            else:
                colorbar["ticks"] = matplotlib.ticker.LinearLocator()

        cbarfmt = colorbar.pop("format", mpl_extra.default_cbarfmt)
        if cbarfmt == "steve":
            cbarfmt = mpl_extra.steve_cbarfmt
        if cbarfmt:
            colorbar["format"] = cbarfmt

        # ok, this way to pass options to colorbar is bad!!!
        # but it's kind of the cleanest way to affect the colorbar?
        if masknan and all_masked:
            cbar = None
        else:
            cbar = plt.colorbar(p, **colorbar)
            if not nolabels:
                if not cbarlabel:
                    cbarlabel = patch0.pretty_name
                cbar.set_label(cbarlabel)
    else:
        cbar = None

    if not nolabels:
        # Field.data is now xyz as are the crds
        if flip_plot:
            namex, namey = namey, namex
        if not xlabel:
            xlabel = namex
        if not ylabel:
            ylabel = namey
        plt.xlabel(namex)
        plt.ylabel(namey)

    _apply_axfmt(ax, majorfmt=majorfmt, minorfmt=minorfmt,
                 majorloc=majorloc, minorloc=minorloc)

    if earth:
        plot_earth(fld, axis=ax)
    if show:
        mplshow()
    return p, cbar

def _mlt_labels(longitude):
    return "{0:g}".format(longitude * 24.0 / 360.0)

def plot2d_mapfield(fld, ax=None, plot_opts=None, **plot_kwargs):
    """Plot data on a map projection of a sphere

    The default projection is polar, but any other basemap projection
    can be used.

    Parameters:
        ax (matplotlib axis, optional): Plot in a specific axis object
        plot_opts (str, optional): plot options
        **plot_kwargs (str, optional): plot options

    Returns:
        (plot_object, colorbar_object)

    Note:
        Parameters are in degrees, but if the projection is 'polar',
        then the plot is actually made in radians, which is important
        if you want to annotate a plot.

    See Also:
        * :doc:`/plot_options`: Contains a full list of plot options
    """
    if fld.nr_patches > 1:
        raise TypeError("plot2d_mapfield doesn't do multi-patch fields yet")

    # parse plot_opts
    plot_opts_to_kwargs(plot_opts, plot_kwargs)

    axgridec = plot_kwargs.pop("axgridec", 'grey')
    axgridls = plot_kwargs.pop("axgridls", ':')
    axgridlw = plot_kwargs.pop("axgridlw", 1.0)

    projection = plot_kwargs.pop("projection", "polar")
    hemisphere = plot_kwargs.pop("hemisphere", "north").lower().strip()
    drawcoastlines = plot_kwargs.pop("drawcoastlines", False)
    lon_0 = plot_kwargs.pop("lon_0", 0.0)
    lat_0 = plot_kwargs.pop("lat_0", None)
    bounding_lat = plot_kwargs.pop("bounding_lat", 40.0)
    title = plot_kwargs.pop("title", True)
    label_lat = plot_kwargs.pop("label_lat", True)
    label_mlt = plot_kwargs.pop("label_mlt", True)

    if hemisphere == "north":
        # def_projection = "nplaea"
        # def_boundinglat = 40.0
        latlabel_arr = np.linspace(50.0, 80.0, 4)
    elif hemisphere == "south":
        # def_projection = "splaea"
        # def_boundinglat = -40.0
        # FIXME: should I be doing this?
        if bounding_lat > 0.0:
            bounding_lat *= -1.0
        latlabel_arr = -1.0 * np.linspace(50.0, 80.0, 4)
    else:
        raise ValueError("hemisphere is either 'north' or 'south'")

    # boundinglat = kwargs.pop("boundinglat", def_boundinglat)
    # lon_0 = kwargs.pop("lon_0", 0.0)
    # lat_0 = kwargs.pop("lat_0", None)
    # drawcoastlines = kwargs.pop("drawcoastlines", False)

    if projection != "polar" and not _HAS_BASEMAP:
        viscid.logger.error("NOTE: install the basemap for the desired "
                            "spherical projection; falling back to "
                            "matplotlib's polar plot.")
        projection = "polar"

    if projection == "polar":
        if LooseVersion(__mpl_ver__) < LooseVersion("1.1"):
            raise RuntimeError("polar plots are annoying for matplotlib < ",
                               "version 1.1. Update your matplotlib and "
                               "profit.")

        absboundinglat = np.abs(bounding_lat)

        ax = _get_polar_axis(ax=ax)

        if hemisphere == "north":
            sl_fld = fld["lat=:{0}f".format(absboundinglat)]
            maxlat = sl_fld.get_crd_nc('lat')[-1]
        elif hemisphere == "south":
            sl_fld = fld["lat={0}f:".format(180.0 - absboundinglat)]["lat=::-1"]
            maxlat = 180.0 - sl_fld.get_crd_nc('lat')[-1]

        lat, lon = sl_fld.get_crds_nc(['lat', 'lon'])
        new_lat = (np.pi / 180.0) * np.linspace(0.0, maxlat, len(lat))
        # FIXME: Matt's code had a - 0.5 * (lon[1] - lon[0]) here...
        # I'm omiting it
        ax.set_theta_offset(-90 * np.pi / 180.0)
        # new_lon = (lon - 90.0) * np.pi / 180.0
        new_lon = lon * np.pi / 180.0
        new_crds = coordinate.wrap_crds("uniform_spherical",
                                        [('lon', [new_lon[0], new_lon[-1],
                                                  len(new_lon)]),
                                         ('lat', [new_lat[0], new_lat[-1],
                                                  len(new_lat)])])
        new_fld = fld.wrap(sl_fld.data, context=dict(crds=new_crds))

        plot_kwargs['nolabels'] = True
        plot_kwargs['equalaxis'] = False
        ret = plot2d_field(new_fld, ax=ax, **plot_kwargs)

        if title:
            if not isinstance(title, string_types):
                title = new_fld.pretty_name
            plt.title(title)
        if axgridec:
            ax.grid(True, color=axgridec, linestyle=axgridls,
                    linewidth=axgridlw)
            ax.set_axisbelow(False)

            mlt_grid_pos = (0, 45, 90, 135, 180, 225, 270, 315)
            mlt_labels = (24, 3, 6, 9, 12, 15, 18, 21)
            if not label_mlt:
                mlt_labels = []
            ax.set_thetagrids(mlt_grid_pos, mlt_labels)

            abs_grid_dr = 10
            # grid_dr = abs_grid_dr * np.sign(bounding_lat)
            lat_grid_pos = np.arange(abs_grid_dr, absboundinglat, abs_grid_dr)
            lat_labels = np.arange(abs_grid_dr, absboundinglat, abs_grid_dr)
            if label_lat == "from_pole":
                lat_labels = ["{0:g}".format(l) for l in lat_labels]
            elif label_lat:
                if hemisphere == 'north':
                    lat_labels = 90 - lat_labels
                else:
                    lat_labels = -90 + lat_labels
                lat_labels = ["{0:g}".format(l) for l in lat_labels]
            else:
                lat_labels = []
            ax.set_rgrids((np.pi / 180.0) * lat_grid_pos, lat_labels)
        else:
            ax.grid(False)
            ax.set_xticklabels([])
            ax.set_yticklabels([])
        return ret

    else:
        if not ax:
            ax = plt.gca()
        m = Basemap(projection=projection, lon_0=lon_0, lat_0=lat_0,
                    boundinglat=bounding_lat, ax=ax)
        plot_kwargs['latlon'] = True
        plot_kwargs['nolabels'] = True
        plot_kwargs['equalaxis'] = False
        ret = plot2d_field(fld, ax=ax, action_ax=m, **plot_kwargs)
        if axgridec:
            if label_lat:
                lat_lables = [1, 1, 1, 1]
            else:
                lat_lables = [0, 0, 0, 0]
            m.drawparallels(latlabel_arr, labels=lat_lables,
                            color=axgridec, linestyle=axgridls,
                            linewidth=axgridlw)

            if label_mlt:
                mlt_labels = [1, 1, 1, 1]
            else:
                mlt_labels = [0, 0, 0, 0]
            m.drawmeridians(np.linspace(360.0, 0.0, 8, endpoint=False),
                            labels=mlt_labels, fmt=_mlt_labels,
                            color=axgridec, linestyle=axgridls,
                            linewidth=axgridlw)
        if drawcoastlines:
            m.drawcoastlines(linewidth=0.25)
        return ret

def plot1d_field(fld, ax=None, plot_opts=None, **plot_kwargs):
    """Plot a 1D Field using lines

    Parameters:
        ax (matplotlib axis, optional): Plot in a specific axis object
        plot_opts (str, optional): plot options
        **plot_kwargs (str, optional): plot options

    See Also:
        * :doc:`/plot_options`: Contains a full list of plot options
    """
    patch0 = fld.patches[0]
    if not ax:
        ax = plt.gca()

    # parse plot_opts
    plot_opts_to_kwargs(plot_opts, plot_kwargs)
    actions, norm_dict = _extract_actions_and_norm(ax, plot_kwargs,
                                                   defaults={'equalaxis': False})

    # everywhere options
    scale = plot_kwargs.pop("scale", None)
    masknan = plot_kwargs.pop("masknan", True)
    nolabels = plot_kwargs.pop("nolabels", False)
    xlabel = plot_kwargs.pop("xlabel", None)
    ylabel = plot_kwargs.pop("ylabel", None)
    majorfmt = plot_kwargs.pop("majorfmt", mpl_extra.default_majorfmt)
    minorfmt = plot_kwargs.pop("minorfmt", mpl_extra.default_minorfmt)
    majorloc = plot_kwargs.pop("majorloc", mpl_extra.default_majorloc)
    minorloc = plot_kwargs.pop("minorloc", mpl_extra.default_minorloc)
    show = plot_kwargs.pop("show", False)

    # 1d plot options
    legend = plot_kwargs.pop("legend", False)
    label = plot_kwargs.pop("label", patch0.pretty_name)
    mod = plot_kwargs.pop("mod", None)

    plot_kwargs["label"] = label
    namex, = patch0.crds.axes

    if patch0.iscentered("Node"):
        x = np.concatenate([blk.get_crd_nc(namex) for blk in fld.patches])
    elif patch0.iscentered("Cell"):
        x = np.concatenate([blk.get_crd_cc(namex) for blk in fld.patches])
    else:
        raise ValueError("1d plots can do node or cell centered data only")

    dat = np.concatenate([blk.data for blk in fld.patches])

    if mod:
        x *= mod
    if scale:
        dat *= scale
    if masknan:
        dat = np.ma.masked_where(np.isnan(dat), dat)
    p = ax.plot(x, dat, **plot_kwargs)

    _apply_actions(actions)

    ###############################
    # set scale based on norm_dict
    vmin, vmax = norm_dict['clim']
    if norm_dict['crdscale'] == 'log':
        plt.xscale('log')
    if norm_dict['vscale'] == 'log':
        plt.yscale('log')
    if norm_dict['symmetric']:
        if norm_dict['vscale'] == 'log':
            raise ValueError("log scale can't be symmetric about 0")
        maxval = max(abs(max(dat)), abs(min(dat)))
        vmin, vmax = -maxval, maxval
    if norm_dict['vscale'] is not None:
        plt.ylim((vmin, vmax))

    ########################
    # apply labels and such
    if not nolabels:
        if xlabel is None:
            xlabel = namex
        if ylabel is None:
            ylabel = label
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)

    _apply_axfmt(ax, majorfmt=majorfmt, minorfmt=minorfmt,
                 majorloc=majorloc, minorloc=minorloc)

    if legend:
        if isinstance(legend, bool):
            legend = 0
        plt.legend(loc=0)

    if show:
        mplshow()
    return p, None

def plot2d_lines(lines, scalars=None, symdir="", ax=None,
                 show=False, flip_plot=False, subsample=1,
                 pts_interp='linear', scalar_interp='linear',
                 marker=None, marker_kwargs=None, **kwargs):
    """Plot a list of lines in 2D

    Args:
        lines (list): list of 3xN ndarrays describing N xyz points
            along a line
        scalars (list, ndarray): a bunch of floats, rgb tuples, or
            '#0000ff' colors. These can be given as one per line,
            or one per vertex. See
            :py:func:`viscid.vutil.prepare_lines` for more info.
        symdir (str): direction perpendiclar to plane; one of 'xyz'
        ax (matplotlib Axis, optional): axis on which to plot (should
            be a 3d axis)
        show (bool): call plt.show when finished?
        flip_plot (bool): flips x and y axes on the plot
        subsample (int): Number of additional vertices per line
            segment. Since each line segment us uniformly colored, this
            is used to make lines appear smoothly colored. If 0, then
            the line segments are colored with the value of its
            preceeding vertex, so chances are you want a value >= 1.
        pts_interp (str): What kind of interpolation to use for
            vertices if subsample > 0. Must be a value recognized by
            :py:func:`scipy.interpolate.interp1d`.
        scalar_interp (str): What kind of interpolation to use for
            scalars if subsample > 0. Must be a value recognized by
            :py:func:`scipy.interpolate.interp1d`.
        marker (str): if given, plot the vertices using plt.scatter
        marker_kwargs (dict): additional kwargs for plt.scatter
        **kwargs: passed to matplotlib.collections.LineCollection

    Raises:
        ValueError: If a 2D plane can't be determined

    Returns:
        a LineCollection
    """
    if not ax:
        ax = plt.gca()
    r = _prep_lines(lines, scalars=scalars, subsample=subsample,
                    pts_interp=pts_interp, scalar_interp=scalar_interp)
    verts, segments, vert_scalars, seg_scalars, vert_colors, seg_colors, other = r  # pylint: disable=unused-variable
    # alpha = other['alpha']

    symdir = symdir.strip().lower()
    if segments.shape[2] == 2:
        xind, yind, zind = 0, 1, None
    elif symdir == 'x':
        xind, yind, zind = 1, 2, 0
    elif symdir == 'y':
        xind, yind, zind = 0, 2, 1
    elif symdir == 'z':
        xind, yind, zind = 0, 1, 2
    else:
        raise ValueError("For 3d lines, symdir should be x, y, or z")

    if flip_plot:
        xind, yind = yind, xind

    if seg_scalars is None and seg_colors is None and zind is not None:
        vert_scalars = verts[zind, :]
        seg_scalars = segments[:, 0, zind]

    line_collection = LineCollection(segments[:, :, [xind, yind]],
                                     array=seg_scalars, colors=seg_colors,
                                     **kwargs)
    ax.add_collection(line_collection)

    if marker:
        if not marker_kwargs:
            marker_kwargs = dict()

        # if colors are not given,
        if 'c' not in marker_kwargs:
            if vert_colors is not None:
                marker_kwargs['c'] = vert_colors
            elif vert_scalars is not None:
                marker_kwargs['c'] = vert_scalars
        # pass along some kwargs to the scatter plot
        for name in ['cmap', 'norm', 'vmin', 'vmax']:
            if name in kwargs and name not in marker_kwargs:
                marker_kwargs[name] = kwargs[name]
        ax.scatter(verts[xind, :], verts[yind, :], marker=marker,
                   **marker_kwargs)
    else:
        _autolimit_to_vertices(ax, verts[[xind, yind], :])

    if show:
        plt.show()

    return line_collection

def plot3d_lines(lines, scalars=None, ax=None, show=False, subsample=1,
                 pts_interp='linear', scalar_interp='linear',
                 marker='', marker_kwargs=None, **kwargs):
    """Plot a list of lines in 3D

    Args:
        lines (list): list of 3xN ndarrays describing N xyz points
            along a line
        scalars (list, ndarray): a bunch of floats, rgb tuples, or
            '#0000ff' colors. These can be given as one per line,
            or one per vertex. See
            :py:func:`viscid.vutil.prepare_lines` for more info.
        ax (matplotlib Axis, optional): axis on which to plot (should
            be a 3d axis)
        show (bool): call plt.show when finished?
        subsample (int): Number of additional vertices per line
            segment. Since each line segment us uniformly colored, this
            is used to make lines appear smoothly colored. If 0, then
            the line segments are colored with the value of its
            preceeding vertex, so chances are you want a value >= 1.
        pts_interp (str): What kind of interpolation to use for
            vertices if subsample > 0. Must be a value recognized by
            :py:func:`scipy.interpolate.interp1d`.
        scalar_interp (str): What kind of interpolation to use for
            scalars if subsample > 0. Must be a value recognized by
            :py:func:`scipy.interpolate.interp1d`.
        marker (str): if given, plot the vertices using plt.scatter
        marker_kwargs (dict): additional kwargs for plt.scatter
        **kwargs: passed to matplotlib.collections.LineCollection

    Returns:
        TYPE: Line3DCollection
    """
    from mpl_toolkits.mplot3d.art3d import Line3DCollection

    ax = _get_3d_axis(ax)

    r = _prep_lines(lines, scalars=scalars, subsample=subsample,
                    pts_interp=pts_interp, scalar_interp=scalar_interp)
    verts, segments, vert_scalars, seg_scalars, vert_colors, seg_colors, other = r  # pylint: disable=unused-variable

    line_collection = Line3DCollection(segments[:, :, [0, 1, 2]],
                                       array=seg_scalars, colors=seg_colors,
                                       **kwargs)
    ax.add_collection3d(line_collection)

    if marker:
        if not marker_kwargs:
            marker_kwargs = dict()

        # if colors are not given,
        if 'c' not in marker_kwargs:
            if vert_colors is not None:
                marker_kwargs['c'] = vert_colors
            elif vert_scalars is not None:
                marker_kwargs['c'] = vert_scalars
        # pass along some kwargs to the scatter plot
        for name in ['cmap', 'norm', 'vmin', 'vmax']:
            if name in kwargs and name not in marker_kwargs:
                marker_kwargs[name] = kwargs[name]
        ax.scatter(verts[0, :], verts[1, :], verts[2, :], marker=marker,
                   **marker_kwargs)
    else:
        _autolimit_to_vertices(ax, verts)

    if show:
        plt.show()

    return line_collection

def plot2d_quiver(fld, step=1, **kwargs):
    """Put quivers on a 2D plot

    The quivers will be plotted in the 2D plane of fld, so if fld
    is 3D, then one and only one dimenstion must have shape 1.

    Note:
        There are some edge cases where step doesn't work.

    Args:
        fld(VectorField): 2.5-D Vector field to plot
        step (int): only quiver every Nth grid cell. Can also
            be a list of ints to specify x & y downscaling separatly
        **kwargs: passed to :py:func:`matplotlpb.pyplot.quiver`

    Raises:
        TypeError: vector field check
        ValueError: 2d field check

    Returns:
        result of :py:func:`matplotlpb.pyplot.quiver`
    """
    if fld.nr_patches > 1:
        raise TypeError("plot2d_quiver doesn't do multi-patch fields yet")

    fld = fld.slice_reduce(":")

    if fld.patches[0].nr_sdims != 2:
        raise ValueError("2D Fields only for plot2d_quiver")
    if fld.nr_comps != 3:
        raise TypeError("Vector Fields only for plot2d_quiver")

    # get lm axes, ie, the axes in the plane
    l, m = fld.crds.axes
    lm = "".join([l, m])

    # get stepd scalar fields for the vector components in the plane
    if not hasattr(step, "__getitem__") or len(step) < 2:
        step = np.array([step, step]).reshape(-1)
    first_l = (fld.shape[0] % step[0]) // 2
    first_m = (fld.shape[1] % step[1]) // 2
    vl = fld[l][first_l::step[0], first_m::step[1]]
    vm = fld[m][first_l::step[0], first_m::step[1]]

    # get coordinates
    xl, xm = vl.get_crds(lm, shaped=True)
    xl, xm = np.broadcast_arrays(xl, xm)

    return plt.quiver(xl, xm, vl, vm, **kwargs)

def streamplot(fld, **kwargs):
    """Plot 2D streamlines with :py:func:`matplotlib.pyplot.streamplot`

    Args:
        fld (VectorField): Some 2.5-D Vector Field
        **kwargs: passed to :py:func:`matplotlib.pyplot.streamplot`

    Raises:
        TypeError: vector field check
        ValueError: 2d field check

    Returns:
        result of :py:func:`matplotlib.pyplot.streamplot`
    """
    if fld.nr_patches > 1:
        raise TypeError("plot2d_quiver doesn't do multi-patch fields yet")

    fld = fld.slice_reduce(":")

    if fld.patches[0].nr_sdims != 2:
        raise ValueError("2D Fields only for plot2d_quiver")
    if fld.nr_comps != 3:
        raise TypeError("Vector Fields only for plot2d_quiver")

    # get lm axes, ie, the axes in the plane
    l, m = fld.crds.axes
    lm = "".join([l, m])

    # get scalar fields for the vector components in the plane
    vl, vm = fld[l], fld[m]
    xl, xm = fld.get_crds(lm, shaped=False)

    # matplotlib's streamplot is for uniform grids only, if crds are non
    # uniform, then interpolate onto a new plane with uniform resolution
    # matching the most refined region of fld
    dxl = xl[1:] - xl[:-1]
    dxm = xm[1:] - xm[:-1]
    if not np.allclose(dxl[0], dxl) or not np.allclose(dxm[0], dxm):
        # viscid.logger.warn("Matplotlib's streamplot is for uniform grids only")
        nl = np.ceil((xl[-1] - xl[0]) / np.min(dxl))
        nm = np.ceil((xm[-1] - xm[0]) / np.min(dxm))

        vol = viscid.Volume([xl[0], xm[0], 0], [xl[-1], xm[-1], 0],
                            [nl, nm, 1])
        vl = vol.wrap_field(viscid.interp_trilin(vl, vol)).slice_reduce(":")
        vm = vol.wrap_field(viscid.interp_trilin(vm, vol)).slice_reduce(":")
        xl, xm = vl.get_crds(lm, shaped=False)

        # interpolate linewidth and color too if given
        for other in ['linewidth', 'color']:
            try:
                if isinstance(kwargs[other], viscid.field.Field):
                    o_fld = kwargs[other]
                    o_fld = vol.wrap_field(viscid.interp_trilin(o_fld, vol))
                    kwargs[other] = o_fld.slice_reduce(":")
            except KeyError:
                pass

    # streamplot isn't happy if linewidth are color are Fields
    for other in ['linewidth', 'color']:
        try:
            if isinstance(kwargs[other], viscid.field.Field):
                kwargs[other] = kwargs[other].data
        except KeyError:
            pass

    return plt.streamplot(xl, xm, vl.data.T, vm.data.T, **kwargs)

def scatter_3d(points, c='b', ax=None, show=False, equal=False, **kwargs):
    """Plot scattered points on a matplotlib 3d plot

    Parameters:
        points: something shaped 3xN for N points, where 3 are the
            xyz cartesian directions in that order
        c (str, optional): color (in matplotlib format)
        ax (matplotlib Axis, optional): axis on which to plot (should
            be a 3d axis)
        show (bool, optional): show
        kwargs: passed along to :meth:`plt.statter`
    """
    if not ax:
        ax = plt.gca(projection='3d')

    x = points[0]
    y = points[1]
    z = points[2]
    p = ax.scatter(x, y, z, c=c, **kwargs)
    if equal:
        ax.axis("equal")
    plt.xlabel("x")
    plt.ylabel("y")
    if show:
        plt.show()
    return p, None


def mplshow():
    """Calls :meth:`matplotlib.pyplot.show()`"""
    # do i need to do anything special before i show?
    # can't think of anything at this point...
    plt.show()

show = mplshow

def tighten(**kwargs):
    """Calls `matplotlib.pyplot.tight_layout(**kwargs)`"""
    try:
        plt.tight_layout(**kwargs)
    except AttributeError:
        logger.warn("No matplotlib tight layout support")

def auto_adjust_subplots(fig=None, tight_layout=True, subplot_params=None):
    """Wrapper to adjust subplots w/ tight_layout remembering axes lims

    Args:
        fig (Figure): a matplotlib figure
        tight_layout (bool, dict): flag for whether or not to apply a
            tight layout. If a dict, then it's unpacked into
            `plt.tight_layout(...)`
        subplot_params (dict): unpacked into `fig.subplots_adjust(...)`

    Returns:
        dict: keyword arguments for fig.subplots_adjust that describe
            the current figure after all adjustments are made
    """
    if fig is None:
        fig = plt.gcf()

    # remember the axes' limits before the call to tight_layout
    pre_tighten_xlim = [ax.get_xlim() for ax in fig.axes]
    pre_tighten_ylim = [ax.get_ylim() for ax in fig.axes]

    if tight_layout or isinstance(tight_layout, dict):
        if not isinstance(tight_layout, dict):
            tight_layout = {}
        tighten(**tight_layout)

    # apply specific subplot_params if given; hack for movies that wiggle
    if subplot_params:
        fig.subplots_adjust(**subplot_params)

    # re-apply the old axis limits; hack for movies that wiggle
    for ax, xlim, ylim in zip(fig.axes, pre_tighten_xlim, pre_tighten_ylim):
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)

    p = fig.subplotpars
    ret = {'left': p.left, 'right': p.right, 'top': p.top,
           'bottom': p.bottom, 'hspace': p.hspace, 'wspace': p.wspace}
    return ret

def plot_earth(plane_spec, axis=None, scale=1.0, rot=0,
               daycol='w', nightcol='k', crd_system="mhd",
               zorder=10):
    """Plot a black and white Earth to show sunward direction

    Parameters:
        plane_spec: Specifies the plane for determining sunlit portion.
            This can be a :class:`viscid.field.Field` object to try to
            auto-discover the plane and crd_system, or it can be a
            string like "y=0".
        axis (matplotlib Axis): axis on which to plot
        scale (float, optional): scale of earth
        rot (float, optional): Rotation of day/night side... I forget all
            the details :(
        daycol (str, optional): color of dayside (matplotlib format)
        nightcol (str, optional): color of nightside (matplotlib format)
        crd_system (str, optional): 'mhd' or 'gse', can usually be
            deduced from plane_spec if it's a Field instance.
    """
    import matplotlib.patches as mpatches

    # this is kind of a hacky way to
    if hasattr(plane_spec, "patches"):
        # this is for both Fields and AMRFields
        crd_system = plane_spec.patches[0].meta.get("crd_system", crd_system)
        values = []
        for blk in plane_spec.patches:
            # take only the 1st reduced.nr_sdims... this should just work
            try:
                plane, _value = blk.deep_meta["reduced"][0]
                values.append(_value)
            except KeyError:
                logger.error("No reduced dims in the field, i don't know what "
                             "2d \nplane, we're in and can't figure out the "
                             "size of earth.")
                return None
        value = np.min(np.abs(values))
    else:
        plane, value = [s.strip() for s in plane_spec.split("=")]
        value = float(value)

    if value**2 >= scale**2:
        return None
    radius = np.sqrt(scale**2 - value**2)

    if not axis:
        axis = plt.gca()

    if crd_system == "gse":
        rot = 180

    if plane == 'y' or plane == 'z':
        axis.add_patch(mpatches.Wedge((0, 0), radius, 90 + rot, 270 + rot,
                                      ec=nightcol, fc=daycol, zorder=zorder))
        axis.add_patch(mpatches.Wedge((0, 0), radius, 270 + rot, 450 + rot,
                                      ec=nightcol, fc=nightcol, zorder=zorder))
    elif plane == 'x':
        if value < 0:
            axis.add_patch(mpatches.Circle((0, 0), radius, ec=nightcol,
                                           fc=daycol, zorder=zorder))
        else:
            axis.add_patch(mpatches.Circle((0, 0), radius, ec=nightcol,
                                           fc=nightcol, zorder=zorder))
    return None

def _get_projected_axis(ax=None, projection='polar',
                        check_attr='set_thetagrids'):
    _new_axis = False
    if not ax:
        if len(plt.gcf().axes) == 0:
            _new_axis = True
        ax = plt.gca()
    if not hasattr(ax, check_attr):
        ax = plt.subplot(*ax.get_geometry(), projection=projection)
        if not _new_axis:
            viscid.logger.warn("Clobbering axis for subplot %s; please give a "
                               "%s axis if you indend to use it later.",
                               ax.get_geometry(), projection)
    return ax

def _get_polar_axis(ax=None):
    return _get_projected_axis(ax=ax, projection='polar',
                               check_attr='set_thetagrids')

def _get_3d_axis(ax=None):
    from mpl_toolkits.mplot3d import Axes3D  # pylint: disable=unused-variable
    return _get_projected_axis(ax=ax, projection='3d', check_attr='zaxis')

def _autolimit_to_vertices(ax, verts):
    """Set limits on ax so that all verts are visible"""
    xmin, xmax = np.min(verts[0, ...]), np.max(verts[0, ...])
    ymin, ymax = np.min(verts[1, ...]), np.max(verts[1, ...])
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    if xlim[0] < xlim[1]:
        if xmin < xlim[0]:
            ax.set_xlim(left=xmin)
        if xmax > xlim[1]:
            ax.set_xlim(right=xmax)
    else:
        if xmax > xlim[0]:
            ax.set_xlim(left=xmax)
        if xmin < xlim[1]:
            ax.set_xlim(right=xmin)

    if ylim[0] < ylim[1]:
        if ymin < ylim[0]:
            ax.set_ylim(bottom=ymin)
        if ymax > ylim[1]:
            ax.set_ylim(top=ymax)
    else:
        if ymax > ylim[0]:
            ax.set_ylim(bottom=ymax)
        if ymin < ylim[1]:
            ax.set_ylim(top=ymin)

    # maybe z, maybe not
    if verts.shape[0] > 2:
        zlim = ax.get_zlim()
        zmin, zmax = np.min(verts[2, ...]), np.max(verts[2, ...])
        if zlim[0] < zlim[1]:
            if zmin < zlim[0]:
                ax.set_zlim(bottom=zmin)
            if zmax > zlim[1]:
                ax.set_zlim(top=zmax)
        else:
            if zmax > zlim[0]:
                ax.set_zlim(bottom=zmax)
            if zmin < zlim[1]:
                ax.set_zlim(top=zmin)

def _prep_lines(lines, scalars=None, subsample=1, pts_interp='linear',
                scalar_interp='linear', other=None):
    r = viscid.vutil.prepare_lines(lines, scalars, do_connections=True,
                                   other=other)
    verts, scalars, connections, other = r
    nr_sdims = verts.shape[0]
    nverts = verts.shape[1]
    nsegs = connections.shape[0]
    line_start = np.setdiff1d(np.arange(nverts), connections[:, 1],
                              assume_unique=True)
    line_stop = np.concatenate([line_start[1:], [nverts]])
    verts_per_line = line_stop - line_start
    nlines = len(line_start)
    assert nverts == nlines + nsegs

    if scalars is not None:
        scalars = np.atleast_2d(scalars)
    else:
        scalars = np.empty((0, nverts), verts.dtype)

    # Use numpy / scipy to interpolate points and scalars
    if subsample > 0:
        fine_verts = [None] * nlines
        fine_scalars = [None] * nlines
        fine_connections = [None] * nlines

        for i, start, stop in izip(count(), line_start, line_stop):
            n_coarse = stop - start  # number of verts, not segments
            n_fine = (subsample + 1) * (n_coarse - 1) + 1
            coarse_verts = verts[:, start:stop]
            coarse_scalars = scalars[:, start:stop]
            fine_verts[i] = np.empty((nr_sdims, n_fine), dtype=verts.dtype)
            fine_scalars[i] = np.empty((scalars.shape[0], n_fine),
                                       dtype=verts.dtype)
            fine_connections[i] = np.empty((n_fine - 1, 2), dtype='i')
            t_coarse = np.linspace(0, 1, n_coarse)
            t_fine = np.linspace(0, 1, n_fine)

            try:
                # raise ImportError
                from scipy.interpolate import interp1d
                for j in range(coarse_verts.shape[0]):
                    fine_verts[i][j, :] = interp1d(t_coarse, coarse_verts[j, :],
                                                   kind=pts_interp)(t_fine)
                for j in range(scalars.shape[0]):
                    fine_scalars[i][j, :] = interp1d(t_coarse, coarse_scalars[j, :],
                                                     kind=scalar_interp)(t_fine)
            except ImportError:
                if pts_interp != 'linear' or scalar_interp != 'linear':
                    viscid.logger.error("Scipy is required to do anything "
                                        "other than linear interpolation")
                    raise

                for j in range(coarse_verts.shape[0]):
                    fine_verts[i][j, :] = np.interp(t_fine, t_coarse,
                                                    coarse_verts[j, :])
                for j in range(scalars.shape[0]):
                    fine_scalars[i][j, :] = np.interp(t_fine, t_coarse,
                                                      coarse_scalars[j, :])

            new_start = np.sum((verts_per_line[:i] - 1) * (subsample + 1) + 1)
            new_stop = new_start + n_fine
            fine_connections[i][:, 0] = np.arange(new_start, new_stop - 1)
            fine_connections[i][:, 1] = np.arange(new_start + 1, new_stop)

        verts = np.concatenate(fine_verts, axis=1)
        was_uint8 = scalars.dtype == np.dtype('u1')
        scalars = np.concatenate(fine_scalars, axis=1)
        if was_uint8:
            scalars = scalars.round().astype('u1')
        connections = np.concatenate(fine_connections, axis=0)
        nverts = verts.shape[1]
        nsegs = connections.shape[0]
        assert nsegs == nverts - nlines

    # go through and make list of connected segments for the line collection
    segments = np.empty((nsegs, 2, nr_sdims), dtype=verts.dtype)
    segments[:, 0, :] = verts[:, connections[:, 0]].T
    segments[:, 1, :] = verts[:, connections[:, 1]].T

    # # TODO: straighten out array=scalars from color=scalars
    colors, seg_colors = None, None
    if scalars.shape[0] == 0:
        scalars = None
    elif scalars.shape[0] == 1:
        scalars = scalars[0]

    seg_scalars = None
    if scalars is not None:
        if scalars.dtype == np.dtype('u1'):
            colors = scalars.T / 255.0
            seg_colors = colors[connections[:, 0], ...]
            scalars = None
        else:
            seg_scalars = scalars[..., connections[:, 0]]

    return verts, segments, scalars, seg_scalars, colors, seg_colors, other


# man, i was really indecisive about these names... luckily, everything's
# a reference in Python :)
plot_lines = plot3d_lines
plot_lines3d = plot3d_lines
plot_lines2d = plot2d_lines
plot_streamlines = plot3d_lines
plot_streamlines2d = plot2d_lines

##
## EOF
##
