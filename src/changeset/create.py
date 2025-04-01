#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

__author__ = "Alexey Gladkov <legion@kernel.org>"

import argparse

import changeset as cs
from changeset.cover import get_cover_lines

logger = cs.logger


def main(cmdargs: argparse.Namespace) -> int:
    covermsg = cs.cover.default_covermsg
    covercommit = "HEAD^{}"

    if len(cmdargs.newname) == 0 and len(cmdargs.import_ref) > 0:
        logger.warning("There is no name for the import. Use HEAD.")
        cmdargs.newname = cmdargs.import_ref
        cmdargs.import_ref = "HEAD"

    create_newversion = len(cmdargs.newname) == 0

    if create_newversion:
        curref = cs.get_current_patchref()

        if isinstance(curref, cs.Error):
            cs.show_critical(curref.message)
            return cs.EX_FAILURE

        cmdargs.newname = curref.patch_name
        covercommit = curref.patch_base

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

    elif len(cmdargs.import_ref) > 0:
        ref = cs.git_get_describe("HEAD~")

        if not isinstance(ref, cs.Error):
            covercommit = ref.object

        cmdargs.newversion = "0.0"

    if len(cmdargs.newname) == 0:
        logger.critical("Empty branch name is not allowed.")
        return cs.EX_FAILURE

    cmdargs.newversion = cs.normalize_version(cmdargs.newversion)

    newbranch = f"patchset/{cmdargs.newname}/v{cmdargs.newversion}"

    if create_newversion:
        ecode, _, err = cs.git_run_command(["branch", "--copy", newbranch])
        if ecode != cs.EX_SUCCESS:
            cs.show_critical(err)
            logger.critical("Unable to copy branch: %s", newbranch)
            return ecode

        ecode, _, err = cs.git_run_command(["switch", newbranch])
        if ecode != cs.EX_SUCCESS:
            cs.show_critical(err)
            logger.critical("Unable to change the branch: %s", newbranch)
            return ecode

    elif len(cmdargs.import_ref) > 0:
        ecode, _, err = cs.git_run_command(["switch", "--create", newbranch, cmdargs.import_ref])
        if ecode != cs.EX_SUCCESS:
            cs.show_critical(err)
            logger.critical("Unable to import branch: %s", cmdargs.import_ref)
            return ecode

    else:
        ecode, _, err = cs.git_run_command(["switch", "--create", newbranch])
        if ecode != cs.EX_SUCCESS:
            cs.show_critical(err)
            logger.critical("Unable to create new branch: %s", newbranch)
            return ecode

    logger.critical("Switched to a new branch '%s'", newbranch)

    res = cs.create_tag(f"{newbranch}/cover", covercommit, covermsg)

    if isinstance(res, cs.Error):
        cs.show_critical(res.message)
        logger.critical("Unable to create cover tag: %s/cover", newbranch)
        return cs.EX_FAILURE

    logger.critical("New patchset created: '%s'", newbranch)
    return cs.EX_SUCCESS


# vim: tw=200
