#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

__author__ = "Alexey Gladkov <legion@kernel.org>"

import os
import re
import argparse
import tempfile

from typing import Dict, List

import changeset as cs

logger = cs.logger


def add_recipient(recipients: Dict[str, str], rectype: str, names: List[str]) -> None:
    for name in names:
        if name not in recipients:
            recipients[name] = rectype


def update_gitconfig(tmpfile: str, patchname: str) -> int:
    varnames: Dict[str, int] = {
        "patchset.to": 1,
        "patchset.cc": 1,
        f"branch.{patchname}.to": 1,
        f"branch.{patchname}.cc": 1,
        f"branch.{patchname}.remote": 1,
        f"branch.{patchname}.merge": 1,
        f"branch.{patchname}.tags": 1,
    }

    for name in cs.git_get_command_lines(
        ["config", "--file", tmpfile, "--name-only", "--list"]
    ):
        varnames[name] = 1

    for name in sorted(varnames.keys()):
        cs.git_run_command(["config", "--unset-all", name])

        for value in cs.git_get_command_lines(
            ["config", "--file", tmpfile, "--get-all", name]
        ):
            if name.endswith(".tags"):
                value = " ".join(re.split(r"\s+", value))

            ecode, _, err = cs.git_run_command(["config", "--add", name, value])
            if ecode != cs.EX_SUCCESS:
                logger.critical(err)
                return cs.EX_FAILURE

    return cs.EX_SUCCESS


def main(cmdargs: argparse.Namespace) -> int:
    fullname = ""
    ref: cs.PatchRef | cs.Error

    if len(cmdargs.patchname) > 0:
        ref = cs.PatchRef(cmdargs.patchname)
    else:
        ref = cs.get_current_patchref()

    if isinstance(ref, cs.PatchRef):
        fullname = ref.fullname

        if fullname.startswith("refs/heads/"):
            fullname = fullname[len("refs/heads/") :]

    recipients: Dict[str, str] = {}
    branch_remote = ""
    branch_merge = ""
    branch_tags = []

    add_recipient(
        recipients,
        "to",
        cs.git_get_command_lines(["config", "--get-all", "patchset.to"]),
    )
    add_recipient(
        recipients,
        "cc",
        cs.git_get_command_lines(["config", "--get-all", "patchset.cc"]),
    )

    if fullname:
        lines = cs.git_get_command_lines(
            ["config", "--get-all", f"branch.{fullname}.remote"]
        )
        if len(lines) > 0:
            branch_remote = lines[0]

        lines = cs.git_get_command_lines(
            ["config", "--get-all", f"branch.{fullname}.merge"]
        )
        if len(lines) > 0:
            branch_merge = lines[0]

        for line in cs.git_get_command_lines(
            ["config", "--get-all", f"branch.{fullname}.tags"]
        ):
            if len(line) == 0:
                continue
            branch_tags += re.split(r"\s+", line)

        add_recipient(
            recipients,
            "branch-to",
            cs.git_get_command_lines(["config", "--get-all", f"branch.{fullname}.to"]),
        )
        add_recipient(
            recipients,
            "branch-cc",
            cs.git_get_command_lines(["config", "--get-all", f"branch.{fullname}.cc"]),
        )

    editor = cs.get_editor()

    if isinstance(editor, cs.Error):
        logger.critical(editor.message)
        return cs.EX_FAILURE

    ret = cs.EX_SUCCESS

    with tempfile.NamedTemporaryFile(mode="w", suffix=".ini") as fp:
        fp.write("[patchset]\n")

        for name in sorted(filter(lambda x: recipients[x] == "to", recipients.keys())):
            fp.write(f"\tto = {name}\n")

        for name in sorted(filter(lambda x: recipients[x] == "cc", recipients.keys())):
            fp.write(f"\tcc = {name}\n")

        fp.write("\n")
        fp.write(f'[branch "{fullname}"]\n')

        for name in sorted(
            filter(lambda x: recipients[x] == "branch-to", recipients.keys())
        ):
            fp.write(f"\tto = {name}\n")

        for name in sorted(
            filter(lambda x: recipients[x] == "branch-cc", recipients.keys())
        ):
            fp.write(f"\tcc = {name}\n")

        if len(branch_tags) > 0:
            fp.write(f"\ttags = {' '.join(branch_tags)}\n")

        if branch_remote:
            fp.write(f"\tremote = {branch_remote}\n")

        if branch_merge:
            fp.write(f"\tmerge = {branch_merge}\n")

        fp.write("\n")
        fp.write("#\n")
        fp.write("# Available fields:\n")
        fp.write("#\n")
        fp.write("# - patchset.to, branch.*.to, patchset.cc, branch.*.cc\n")
        fp.write("#\n")
        fp.write(
            "# Fields define the recipients for this patchset. One recipient per line. The\n"
        )
        fp.write(
            "# field can be specified multiple times.  If you specify fields in the patchset\n"
        )
        fp.write("# section, they will be substituted for any other patchsets.\n")
        fp.write("#\n")
        fp.write("# - branch.*.tags\n")
        fp.write("#\n")
        fp.write("# Add value to the subject of each patch.")
        fp.write("#\n")
        fp.flush()

        oldinfo = os.stat(fp.name)
        cs.run_command([editor, fp.name])
        newinfo = os.stat(fp.name)

        if oldinfo.st_mtime != newinfo.st_mtime or oldinfo.st_size != newinfo.st_size:
            ret = update_gitconfig(fp.name, fullname)

    return ret


# vim: tw=200
