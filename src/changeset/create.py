#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

__author__ = "Alexey Gladkov <legion@kernel.org>"

import argparse

import changeset as cs
from changeset.cover import create_covertag, get_cover_lines

logger = cs.logger


def normalize_version(version: str) -> str:
    vers = []

    for ver in version.split("."):
        if len(ver) == 0:
            ver = "0"
        vers.append(abs(int(ver)))

    if len(vers) > 2:
        vers = vers[:2]
    elif len(vers) == 1:
        vers.append(0)
    elif len(vers) == 0:
        vers = [1, 0]

    if vers[0] == 0:
        vers[0] = 1

    return ".".join(map(str, vers))


def main(cmdargs: argparse.Namespace) -> int:
    covermsg = cs.cover.default_covermsg

    if len(cmdargs.newname) == 0:
        curref = cs.get_current_patchref()

        if isinstance(curref, cs.Error):
            cs.show_critical(curref.message)
            return cs.EX_FAILURE

        cmdargs.newname = curref.patch_name

        lines = get_cover_lines(curref.covertag)

        if len(lines) > 0:
            covermsg = "\n".join(lines[1:]).strip()

        if cmdargs.incmajor or cmdargs.incminor:
            vers = []
            for ver in curref.patch_vers.split("."):
                vers.append(int(ver))

            if cmdargs.incmajor:
                vers[0] += 1
                vers[1] = 0

            if cmdargs.incminor:
                vers[1] += 1

            cmdargs.newversion = ".".join(map(str, vers))

        elif len(cmdargs.newversion) == 0:
            logger.critical("It's not clear what you want to achieve.")
            return cs.EX_FAILURE

    if len(cmdargs.newname) == 0:
        logger.critical("Empty branch name is not allowed.")
        return cs.EX_FAILURE

    cmdargs.newversion = normalize_version(cmdargs.newversion)

    newbranch = f"patchset/{cmdargs.newname}/v{cmdargs.newversion}"

    ecode, _, err = cs.git_run_command(["switch", "--create", newbranch])
    if ecode != 0:
        cs.show_critical(err)
        logger.critical("Unable to create new branch: %s", newbranch)
        return ecode

    logger.info("Switched to a new branch '%s'", newbranch)

    res = create_covertag(f"{newbranch}/cover", "HEAD^{}", covermsg)

    if isinstance(res, cs.Error):
        cs.show_critical(res.message)
        logger.critical("Unable to create cover tag: %s/cover", newbranch)
        return cs.EX_FAILURE

    logger.info("New patchset created: '%s'", newbranch)
    return cs.EX_SUCCESS


# vim: tw=200
