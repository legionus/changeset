#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

__author__ = "Alexey Gladkov <legion@kernel.org>"

import os
import argparse
import tempfile

from typing import Dict, List

import changeset as cs
from changeset.cover import get_cover_lines, default_covermsg

logger = cs.logger


def add_arg(args: List[str], argname: str, values: List[str]) -> None:
    for value in values:
        args += [argname, value]


def add_outdir(args: List[str], cmdargs: argparse.Namespace, name: str) -> None:
    if cmdargs.outdir:
        outdir = cmdargs.outdir
    else:
        outdir = f"patches/{name}"

    os.makedirs(outdir, mode=0o755, exist_ok=True)
    args += ["--output-directory", outdir]


def add_tags(args: List[str], cmdargs: argparse.Namespace, patchname: str) -> None:
    tags = []

    if cmdargs.tag_rfc:
        tags += ["RFC"]
    if cmdargs.tag_resend:
        tags += ["RESEND"]

    tags += cs.git_get_command_lines(
        ["config", "--get-all", f"branch.{patchname}.tags"]
    )

    if len(tags) > 0:
        args += ["--subject-prefix", " ".join(tags)]


def add_recipients(args: List[str], patchname: str) -> None:
    recipients: Dict[str, str] = {}

    for var in ["to", "cc"]:
        for value in (
            []
            + cs.git_get_command_lines(["config", "--get-all", f"patchset.{var}"])
            + cs.git_get_command_lines(
                ["config", "--get-all", f"branch.{patchname}.{var}"]
            )
        ):
            recipients[value] = var

        for value in sorted(filter(lambda x: recipients[x] == var, recipients.keys())): # pylint: disable=cell-var-from-loop
            args += [f"--{var}", value]


def get_cover(tag: str) -> str:
    lines = get_cover_lines(tag)
    if len(lines) > 0:
        return "\n".join(lines[1:]).strip()
    return default_covermsg


def main(cmdargs: argparse.Namespace) -> int:
    fullname = ""
    ref: cs.PatchRef | cs.Error

    if len(cmdargs.patchname) > 0:
        ref = cs.PatchRef(cmdargs.patchname)
    else:
        ref = cs.get_current_patchref()

    if isinstance(ref, cs.Error):
        logger.critical(ref.message)
        return cs.EX_FAILURE

    fullname = ref.fullname

    if fullname.startswith("refs/heads/"):
        fullname = fullname[len("refs/heads/") :]

    args = [
        "format-patch",
        "--thread",
        "--minimal",
        "--reroll-count",
        ref.patch_vers[: ref.patch_vers.index(".")],
    ]

    if cmdargs.in_reply_to:
        args += ["--in-reply-to", cmdargs.in_reply_to]

    add_outdir(args, cmdargs, ref.patch_name)
    add_tags(args, cmdargs, fullname)
    add_recipients(args, fullname)

    with tempfile.NamedTemporaryFile(mode="w") as fp:
        fp.write(get_cover(ref.covertag))
        fp.flush()

        ecode, out, err = cs.git_run_command(
            args + ["--description-file", fp.name, f"{ref.patch_base}..{ref.object}"]
        )
        if ecode != cs.EX_SUCCESS:
            cs.show_critical(err)
        cs.show_warning(out)

    return ecode


# vim: tw=200
