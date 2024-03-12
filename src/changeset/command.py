#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023  Alexey Gladkov <legion@kernel.org>

__author__ = "Alexey Gladkov <legion@kernel.org>"

import argparse
import sys
import logging
import importlib

from typing import Any

import changeset as cs

logger = cs.logger


def subcmd(subname: str, cmdargs: argparse.Namespace) -> int:
    mod = importlib.import_module(subname)
    ret: int = mod.main(cmdargs)
    return ret


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="count",
        default=0,
        help="print a message for each action.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        dest="quiet",
        action="store_true",
        default=False,
        help="output critical information only.",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        help="show program's version number and exit.",
        version=cs.__VERSION__,
    )
    parser.add_argument(
        "-h", "--help", action="help", help="show this help message and exit."
    )


def setup_parser_list(parser: Any) -> None:
    """
    Shows a list of known patchsets. The current patchset will be marked with an
    asterisk. The list also shows the base and last commits as well as the number of
    commits.
    """
    sp = parser.add_parser(
        "list",
        description=setup_parser_list.__doc__,
        help=setup_parser_list.__doc__,
        epilog="Report bugs to authors.",
        add_help=False,
    )
    sp.set_defaults(func=lambda args: subcmd("list", args))
    sp.add_argument(
        "--versions",
        dest="versions",
        action="store_true",
        help="show all versions of current patchset.",
    )
    sp.add_argument(
        "--archived",
        dest="archived",
        action="store_true",
        help="show archived patchsets.",
    )
    add_common_arguments(sp)


def setup_parser_cover(parser: Any) -> None:
    """
    Shows or changes the description of the patchset. This description
    will be used for cover-letter.
    """
    sp = parser.add_parser(
        "cover",
        description=setup_parser_cover.__doc__,
        help=setup_parser_cover.__doc__,
        epilog="Report bugs to authors.",
        add_help=False,
    )
    sp.set_defaults(func=lambda args: subcmd("cover", args))
    sp.add_argument("--fix", dest="fix", action="store_true", help="fix cover tag.")
    sp.add_argument("name", nargs="?", default="", help="patchset name.")
    add_common_arguments(sp)


def setup_parser_export(parser: Any) -> None:
    """
    Prepares patches for e-mail submission. The <options> will be passed to
    git-format-patch(1).
    """
    sp = parser.add_parser(
        "export",
        description=setup_parser_export.__doc__,
        help=setup_parser_export.__doc__,
        epilog="Report bugs to authors.",
        add_help=False,
    )
    sp.set_defaults(func=lambda args: subcmd("export", args))
    sp.add_argument(
        "--resend",
        dest="tag_resend",
        action="store_true",
        help="add RESEND tag to the subject.",
    )
    sp.add_argument(
        "--rfc", dest="tag_rfc", action="store_true", help="add RFC tag to the subject."
    )
    sp.add_argument(
        "--in-reply-to",
        dest="in_reply_to",
        action="store",
        metavar="<message-id>",
        help="""make the first mail appear as a reply to the given
                    <message-id>, which avoids breaking threads to provide a new
                    patch series.""",
    )
    sp.add_argument(
        "-o",
        "--output-directory",
        dest="outdir",
        action="store",
        default="",
        metavar="<DIR>",
        help="""use <DIR> to store the resulting files (default:
                    patches/PATCHSET/).""",
    )
    sp.add_argument("patchname", nargs="?", default="", help="patchset name.")
    add_common_arguments(sp)


def setup_parser_send(parser: Any) -> None:
    """
    Sends patches by e-mail. It takes the patches given on the command line and
    emails them out. Patches can be specified as files, directories (which will send
    all files in the directory).
    """
    sp = parser.add_parser(
        "send",
        description=setup_parser_send.__doc__,
        help=setup_parser_send.__doc__,
        epilog="Report bugs to authors.",
        add_help=False,
    )
    sp.set_defaults(func=lambda args: subcmd("send", args))
    sp.add_argument("filename", nargs="+", help="patch-file or directory with patches.")
    add_common_arguments(sp)


def setup_parser_create(parser: Any) -> None:
    """
    Creates branch for a new patchset. The new branch will be created with v1
    version. the version and cover can be overwritten if commits are imported from
    mbox file.
    """
    sp = parser.add_parser(
        "create",
        description=setup_parser_create.__doc__,
        help=setup_parser_create.__doc__,
        epilog="Report bugs to authors.",
        add_help=False,
    )
    sp.set_defaults(func=lambda args: subcmd("create", args))
    sp.add_argument(
        "-N",
        "--start-number",
        dest="newversion",
        action="store",
        default="",
        metavar="MAJ.MIN",
        help="start version number for new patchset.",
    )
    sp.add_argument(
        "-n",
        "--next",
        dest="incmajor",
        action="store_true",
        help="create a new version of the patch.",
    )
    sp.add_argument(
        "-i",
        "--increment",
        dest="incminor",
        action="store_true",
        help="create a new version and increment minor (internal) version number.",
    )
    sp.add_argument("newname", nargs="?", default="", help="new patchset name.")
    add_common_arguments(sp)


def setup_parser_remove(parser: Any) -> None:
    """
    Permanently remove all versions of patchset or just single version.
    """
    sp = parser.add_parser(
        "remove",
        description=setup_parser_remove.__doc__,
        help=setup_parser_remove.__doc__,
        epilog="Report bugs to authors.",
        add_help=False,
    )
    sp.set_defaults(func=lambda args: subcmd("remove", args))
    sp.add_argument("patchname", nargs="+", help="patchset name.")
    add_common_arguments(sp)


def setup_parser_config(parser: Any) -> None:
    """
    Changes options of the patchset. You can always change or delete To and Cc
    fields using the `git config -e'.
    """
    sp = parser.add_parser(
        "config",
        description=setup_parser_config.__doc__,
        help=setup_parser_config.__doc__,
        epilog="Report bugs to authors.",
        add_help=False,
    )
    sp.set_defaults(func=lambda args: subcmd("config", args))
    sp.add_argument("patchname", nargs="?", default="", help="patchset name.")
    add_common_arguments(sp)


def setup_parser() -> argparse.ArgumentParser:
    epilog = "Report bugs to authors."

    desc = """\
This is highlevel utility for easy patchset creation. Each patchset has
a version and description.
"""
    parser = argparse.ArgumentParser(
        prog="changeset",
        formatter_class=argparse.RawTextHelpFormatter,
        description=desc,
        epilog=epilog,
        add_help=False,
        allow_abbrev=True,
    )

    add_common_arguments(parser)

    subparsers = parser.add_subparsers(dest="subcmd", help="")

    setup_parser_list(subparsers)
    setup_parser_create(subparsers)
    setup_parser_remove(subparsers)
    setup_parser_config(subparsers)
    setup_parser_cover(subparsers)
    setup_parser_export(subparsers)
    setup_parser_send(subparsers)

    return parser


def setup_logger(cmdargs: argparse.Namespace) -> None:
    match cmdargs.verbose:
        case 0:
            level = logging.WARNING
        case 1:
            level = logging.INFO
        case _:
            level = logging.DEBUG

    if cmdargs.quiet:
        level = logging.CRITICAL

    cs.setup_logger(logger, level=level, fmt="[%(asctime)s] %(message)s")


def cmd() -> int:
    parser = setup_parser()
    cmdargs = parser.parse_args()

    setup_logger(cmdargs)

    if "func" not in cmdargs:
        parser.print_help()
        return cs.EX_FAILURE

    ret: int = cmdargs.func(cmdargs)

    return ret


if __name__ == "__main__":
    # noinspection PyBroadException
    try:
        if cs.__VERSION__.find("-dev") > 0:
            ecode, short, _ = cs.git_run_command(["rev-parse", "--short", "HEAD"])
            if ecode == 0:
                ver = cs.__VERSION__
                sha = short.strip()
                cs.__VERSION__ = f"{ver}-{sha:.5s}"
    except Exception as ex:
        # Any failures above are non-fatal
        pass
    sys.exit(cmd())
