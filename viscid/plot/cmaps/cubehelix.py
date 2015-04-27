# -*- coding: utf-8 -*-
"""Cubehelix color map implementation"""

from __future__ import print_function

import numpy as np


def clac_helix_rgba(hue0=420.0, hue1=150.0, sat=0.8, intensity0=0.15,
                    intensity1=0.85, gamma=1.0, sat0=None, sat1=None,
                    start=None, rot=None, nlevels=256):
    """Make a cubehelix color map

    This function make color maps with monotonicly increasing
    perceptual intensity. The coefficients for the basis of constant
    intensity come from the paper:

        Green, D. A., 2011, `A colour scheme for the display of
        astronomical intensity images', Bulletin of the Astronomical
        Society of India, 39, 289.

    Note:
        If start OR rot are given, then the color hue is calculated
        using the method from the fortran code in the paper. Otherwise,
        the color angles are found such that the color bar roughly ends
        on the colors given for hue0 and hue1.

    Args:
        hue0 (None, float): hue of the lower end 0..360
        hue1 (None, float): hue of the upper end 0..360
        sat (float, optional): color saturation for both endpoints
        intensity0 (float): intensity at the lower end of the mapping
            (same as L^*), 0..1
        intensity1 (float): intensity at the upper end of the mapping
            (same as L^*), 0..1
        gamma (float): gamma correction; gamma < 1 accents darker
            values, while gamma > 1 accents lighter values
        sat0 (None, float): if not None, set the saturation for the
            lower end of the color map (0..1)
        sat1 (None, float): if not None, set the saturation for the
            upper end of the color map (0..1)
        start (float): if given, set hue0 where 0.0, 1.0, 2.0, 3.0 mean
            blue, red, greed, blue (values are 1.0 + hue / 120.0).
        rot (float): if given, set hue1 such that over the course of
            the color map, the helix goes over rot hues. Values use the
            same convention as start.
        nlevels (int): number of points on which to calculate the
            helix. Matplotlib will linearly interpolate intermediate
            values

    Returns:
        Nx4 ndarray of rgba data

    TODO:
        An option for the ramp of intensity that doesn't rely on gamma.
        I'm thinking or something more like the Weber-Fechner law.
    """
    # set saturation of extrema using sat if necessary
    if sat0 is None:
        sat0 = sat
    if sat1 is None:
        sat1 = sat

    # set start and rot hues from degrees if requested
    original_recipe = start is not None or rot is not None
    if start is None:
        start = 1.0 + hue0 / 120.0
    if rot is None:
        rot = (1.0 + hue1 / 120.0) - start

    # lgam is is lightness**gamma and ssat is the color saturation
    lam = np.linspace(intensity0, intensity1, nlevels)
    lgam = lam**gamma
    ssat = np.linspace(sat0, sat1, nlevels)
    # phi is related to hue along the colormap, but r=1, g=2, b=3
    # a is the amplitude of the helix away from the grayscale diagonal
    if original_recipe:
        phi = (2.0 * np.pi) * (start / 3.0 + 1.0 + rot * lam)
    else:
        phi = (2.0 * np.pi / 3.0) * np.linspace(start, start + rot, nlevels)
    a = 0.5 * ssat * lgam * (1.0 - lgam)

    coefs = np.array([[-0.14861, +1.78277],
                      [-0.29227, -0.90649],
                      [+1.97294, +0.00000]])
    helix_vec = np.array([np.cos(phi), np.sin(phi)])
    # rgb will be a 3xN ndarray
    rgb = lgam + a * np.dot(coefs, helix_vec)

    # limit rgb values to the range [0.0, 1.0]
    rgb[np.where((rgb < 0.0))] = 0.0
    rgb[np.where((rgb > 1.0))] = 1.0
    # rgb was calculated with shape 3xN, but we want to return shape Nx4
    rgba = np.hstack([rgb.T, np.ones_like(rgb[:1]).T])
    return rgba

def make_cubehelix_cmap(name='cubehelix1', reverse=False, **kwargs):
    """Shortcut for making a cubehelix matplotlib colormap

    Args:
        name (str): name of color map
        reverse (bool): flip the lower and upper ends of the mapping
        **kwargs: passed to :py:func:`clac_helix_rgb`

    Returns:
        :py:class:`matplotlib.colors.LinearSegmentedColormap` instance
    """
    try:
        from matplotlib.colors import LinearSegmentedColormap
        rgba = clac_helix_rgba(**kwargs)
        if reverse:
            rgba = rgba[::-1, :]
        return LinearSegmentedColormap.from_list(name, rgba)
    except ImportError:
        raise RuntimeError("Matplotlib is not installed, ergo can not create "
                           "a matplotlib Colormap")

##
## EOF
##
