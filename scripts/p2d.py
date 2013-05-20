#!/usr/bin/env python

from __future__ import print_function
import argparse
import subprocess as sub
import logging
import copy as _copy

from viscid import readers
from viscid import vutil
from viscid import vlab


def _ensure_value(namespace, name, value):
    if getattr(namespace, name, None) is None:
        setattr(namespace, name, value)
    return getattr(namespace, name)

class AddPlotOpts(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        dst = getattr(namespace, self.dest, None)
        if dst is None:
            setattr(namespace, "global_popts", values)
            return None
        logging.info("setting {0} plotopts to {1}".format(dst[-1][0], values))
        dst[-1][1]["plot_opts"] = values


class AddPlotVar(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        items = _copy.copy(_ensure_value(namespace, self.dest, []))
        items.append([values, {}])
        setattr(namespace, self.dest, items)


def main():
    parser = argparse.ArgumentParser(description="Load some data files")
    parser.add_argument("-t", default=":", help="times to plot in slice "
                        "notation: ex : for all 60.0: for 60 mins on, and "
                        ":120 for the first 120mins")
    parser.add_argument("-p", "--var", dest="plot_vars", action=AddPlotVar,
                        help="plot variable")
    parser.add_argument("-o", "--popts", dest="plot_vars", action=AddPlotOpts,
                        help="add plot options to most recent var on the "
                        "command line. if no preceeding vars, popts are "
                        "applied to all plots")
    # parser.add_argument("--global_popts", default=None, help="Plot opts that "
    #                     "are applied to all plots, can also be specified "
    #                     "by a -o before any --var arguments")
    parser.add_argument("--own", action="store_true", help="axes use their own "
                        "x and y")
    parser.add_argument("-a", "--animate", default=None,
                        help="animate results")
    parser.add_argument('-r', '--rate', dest='framerate', type=int, default=5,
                        help="animation frame rate (default 5).")
    parser.add_argument('--qscale', dest='qscale', default='2',
                        help="animation quality flag (default 2).")
    parser.add_argument('-k', dest='keep', action='store_true',
                        help="keep temporary files.")
    parser.add_argument("--prefix", default=None,
                        help="Prefix of the output image filenames")
    parser.add_argument('-w', '--show', dest='show', action="store_true",
                        help="show plots with plt.show()")
    parser.add_argument("-n", "--np", type=int, default=1,
                        help="run n simultaneous processes (not yet working)")
    parser.add_argument('file', nargs=1, help='input file')
    args = vutil.common_argparse(parser)

    if getattr(args, "prefix", None) is None:
        args.prefix = "tmp_image"
    global_popts = getattr(args, "global_popts", None)

    if getattr(args, "plot_vars", None) is None:
        args.plot_vars = [["pp", {"plot_opts":"x_-10_0,y_-5_5,log_5e-2_5e3"}],
                          ["by", {"plot_opts":"x_-10_0,y_-5_5,lin_-5_5"}]]

    # print("args", args)
    # print("plot_vars", args.plot_vars)

    files = readers.load(args.file)
    vlab.multiplot(files, args.plot_vars, np=args.np, time_slice=args.t,
                   share_axes = (not args.own), global_popts=global_popts,
                   out_prefix=args.prefix, show=args.show)

    if args.animate:
        sub.Popen("ffmpeg -r {0} -qscale {1} -i {2}_%06d.png {3}".format(
                  args.framerate, args.qscale, args.prefix, args.animate),
                  shell=True).communicate()
    if not args.keep:
        sub.Popen("rm {0}_*.png".format(args.prefix), shell=True).communicate()


if __name__ == "__main__":
    main()

##
## EOF
##
