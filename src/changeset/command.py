#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023  Alexey Gladkov <legion@kernel.org>

__author__ = "Alexey Gladkov <legion@kernel.org>"

import argparse
import sys
import logging
import textwrap
import importlib

from typing import List, Any

import changeset as cs

logger = cs.logger


def subcmd(subname: str, cmdargs: argparse.Namespace) -> int:
    mod = importlib.import_module(subname)
    ret: int = mod.main(cmdargs)
    return ret


def add_parser(parser: Any, name: str, aliases: List[str], desc: str) -> Any:
    sp = parser.add_parser(
        name,
        aliases=aliases,
        formatter_class=argparse.RawTextHelpFormatter,
        description=desc,
        help=desc,
        epilog="Report bugs to authors.",
        add_help=False,
    )
    sp.set_defaults(func=lambda args: subcmd(name, args))
    return sp


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--git-dir",
        dest="gitdir",
        action="store",
        default=None,
        help="set the path to the repository (`.git' directory).",
    )
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
        "-h",
        "--help",
        action="help",
        help="show this help message and exit.",
    )


def setup_parser_list(parser: Any) -> None:
    sp = add_parser(parser, "list", ["ls"], textwrap.dedent("""
    Shows a list of known patchsets. The current patchset will be marked. The
    list also shows the base and last commits as well as the number of commits.
    """))
    sp.add_argument(
        "--versions",
        dest="versions",
        action="store_true",
        help="show all versions of each patchset in the list.",
    )
    sp.add_argument(
        "--archived",
        dest="archived",
        action="store_true",
        help="show archived patchsets.",
    )
    add_common_arguments(sp)


def setup_parser_cover(parser: Any) -> None:
    sp = add_parser(parser, "cover", ["co"], textwrap.dedent("""
    Shows or changes the description of the patchset. This description
    will be used for cover-letter.
    """))
    sp.add_argument(
        "--fix",
        dest="fix",
        action="store_true",
        help=textwrap.dedent(
            """\
            calculates and sets the cover tag to the beginning of the patchset.
            """
        ),
    )
    sp.add_argument(
        "--use-commit",
        dest="use_commit",
        action="store",
        default="",
        metavar="COMMIT",
        help=textwrap.dedent(
            """\
            put the cover tag on COMMIT without any analysis.
            """
        ),
    )
    sp.add_argument(
        "patchset",
        nargs="?",
        default="",
        help=textwrap.dedent(
            """\
            patchset name (if not specified, the current name will be used).
            """
        ),
    )
    add_common_arguments(sp)


def setup_parser_export(parser: Any) -> None:
    sp = add_parser(parser, "export", ["ex"], textwrap.dedent("""
    Prepares patches for e-mail submission. The description for the patchset
    will be taken from the cover tag (see `cover' subcommand). The To and Сс
    fields will be taken from the config (see `config' subcommad).
    """))
    sp.add_argument(
        "--in-reply-to",
        dest="in_reply_to",
        action="store",
        metavar="<message-id>",
        help=textwrap.dedent(
            """\
            make the first mail appear as a reply to the given
            <message-id>, which avoids breaking threads to provide a new
            patch series.
            """
        ),
    )
    sp.add_argument(
        "--force-version",
        dest="force_version",
        action="store",
        metavar="<number>",
        default=None,
        help="force to use <number> as a patchset version.",
    )
    sp.add_argument(
        "--resend",
        dest="tag_resend",
        action="store_true",
        help="shortcut to add `RESEND' tag to the subject.",
    )
    sp.add_argument(
        "--rfc",
        dest="tag_rfc",
        action="store_true",
        help="shortcut to add `RFC' tag to the subject.",
    )
    sp.add_argument(
        "-t",
        "--tag",
        dest="tags",
        action="append",
        metavar="<TAG>",
        help=textwrap.dedent(
            """\
            add <TAG> to the subject (like a "[PATCH <TAG> v1 0/0]").
            """
        ),
    )
    sp.add_argument(
        "-o",
        "--output-directory",
        dest="outdir",
        action="store",
        default="",
        metavar="<DIR>",
        help=textwrap.dedent(
            """\
            use <DIR> to store the resulting files (default:
            patches/PATCHSET/).
            """
        ),
    )
    sp.add_argument(
        "patchname",
        nargs="?",
        default="",
        help=textwrap.dedent(
            """\
            patchset name (if not specified, the current name will be used).
            """
        ),
    )
    add_common_arguments(sp)


def setup_parser_send(parser: Any) -> None:
    sp = add_parser(parser, "send", ["se"], textwrap.dedent("""
    Sends patches by e-mail. It takes the patches given on the command line and
    emails them out. Patches can be specified as files, directories (which will
    send all files in the directory).
    """))
    sp.add_argument(
        "filename",
        nargs="+",
        help="patch-file or directory with patches.",
    )
    add_common_arguments(sp)


def setup_parser_create(parser: Any) -> None:
    sp = add_parser(parser, "create", ["cr"], textwrap.dedent("""
    Creates branch for a new patchset. The new branch will be created with v1
    version. the version and cover can be overwritten if commits are imported
    from mbox file.
    """))
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
    sp.add_argument(
        "-I",
        "--import",
        dest="import_ref",
        action="store",
        default="",
        metavar="BASEREF",
        help="create a new version based on BASEREF.",
    )
    sp.add_argument(
        "newname",
        nargs="?",
        default="",
        help=textwrap.dedent(
            """\
            new patchset name.
            """
        ),
    )
    add_common_arguments(sp)


def setup_parser_remove(parser: Any) -> None:
    sp = add_parser(parser, "remove", ["rm"], textwrap.dedent("""
    Permanently remove all versions of patchset or just single version.
    """))
    sp.add_argument(
        "patchname",
        nargs="+",
        help="patchset name.",
    )
    add_common_arguments(sp)


def setup_parser_config(parser: Any) -> None:
    sp = add_parser(parser, "config", [], textwrap.dedent("""
    Changes options of the patchset. You can always change or delete To and Cc
    fields using the `git config -e'.
    """))
    sp.add_argument(
        "patchname",
        nargs="?",
        default="",
        help=textwrap.dedent(
            """\
            patchset name (if not specified, the current name will be used).
            """
        ),
    )
    add_common_arguments(sp)


def setup_parser_import(parser: Any) -> None:
    sp = add_parser(parser, "import", ["am"], textwrap.dedent("""
    Imports a patchset from a set of files obtained by the git-format-patch(1)
    utility.
    """))
    sp.add_argument(
        "--print",
        dest="print_tree",
        action="store_true",
        help="print a thread of patches and exit.",
    )
    sp.add_argument(
        "-b",
        "--branch-point",
        dest="start_point",
        action="store",
        default="HEAD",
        metavar="COMMIT",
        help="the starting point for the new branch.",
    )
    sp.add_argument(
        "-s",
        "--signoff",
        dest="signoff",
        action="store_true",
        help=textwrap.dedent(
            """\
            add a Signed-off-by trailer to the commit message, using the
            committer identity of yourself.
            """
        ),
    )
    sp.add_argument(
        "patchname",
        help="patchset name.",
    )
    sp.add_argument(
        "filename",
        nargs="+",
        help="patch-file or directory with patches.",
    )
    add_common_arguments(sp)


def setup_parser() -> argparse.ArgumentParser:
    desc = textwrap.dedent("""
    This is highlevel utility for easy patchset creation. The utility allows to
    organize the creation of a set of patches and their versioning. Typically
    the workflow consists of the following steps:

     * start a new topical branch using `cs create patchname`.
     * add commits as usual and work with them using `git rebase -i`.
     * prepare the cover letter using `cs cover`.
     * prepare the list of patches using `cs export`.
     * send patches to upstream using `cs send`.
    """)
    parser = argparse.ArgumentParser(
        prog="changeset",
        formatter_class=argparse.RawTextHelpFormatter,
        description=desc,
        epilog="Report bugs to authors.",
        add_help=False,
        allow_abbrev=True,
    )

    add_common_arguments(parser)

    subparsers = parser.add_subparsers(dest="subcmd", help="")

    setup_parser_create(subparsers)
    setup_parser_remove(subparsers)
    setup_parser_config(subparsers)
    setup_parser_cover(subparsers)
    setup_parser_import(subparsers)
    setup_parser_export(subparsers)
    setup_parser_send(subparsers)
    setup_parser_list(subparsers)

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

    if cmdargs.gitdir:
        cs.gitdir = cmdargs.gitdir

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
            if ecode == cs.EX_SUCCESS:
                ver = cs.__VERSION__
                sha = short.strip()
                cs.__VERSION__ = f"{ver}-{sha:.5s}"
    except Exception as ex:
        # Any failures above are non-fatal
        pass
    sys.exit(cmd())
