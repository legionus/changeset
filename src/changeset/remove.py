#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

__author__ = "Alexey Gladkov <legion@kernel.org>"

import argparse

from typing import Optional

import changeset as cs

logger = cs.logger


def delete_patchref(ref: cs.PatchRef) -> Optional[cs.PatchRefError]:
    ecode, out, err = cs.git_run_command(
        ["branch", "--delete", "--force", ref.fullname[len("refs/heads/") :]]
    )
    if ecode != cs.EX_SUCCESS:
        return cs.PatchRefError(err)

    cs.git_run_command(["tag", "--delete", ref.covertag[len("refs/tags/") :]])

    cs.show_warning(out)
    return None


def delete(ref: cs.PatchRef) -> int:
    pattern = [ref.patch_name, f"{ref.patch_type}{ref.patch_vers}"]

    refs = cs.get_list_patchrefs("/".join(pattern))

    for name in sorted(refs.keys()):
        for ver in sorted(refs[name].prev_vers.keys()):
            res = delete_patchref(refs[name].prev_vers[ver])
            if isinstance(res, cs.PatchRefError):
                cs.show_critical(res.message)
                return cs.EX_FAILURE

        res = delete_patchref(refs[name])
        if isinstance(res, cs.PatchRefError):
            cs.show_critical(res.message)
            return cs.EX_FAILURE

    return cs.EX_SUCCESS


def main(cmdargs: argparse.Namespace) -> int:
    curref = cs.get_current_patchref()

    ret = cs.EX_SUCCESS

    for oldname in cmdargs.patchname:
        if len(oldname) == 0:
            logger.critical("Empty branch name is not allowed.")
            return cs.EX_FAILURE

        ref = cs.PatchRef(oldname)

        if isinstance(ref, cs.BadPatchRefError):
            logger.critical(ref.message)
            return cs.EX_FAILURE

        if isinstance(curref, cs.PatchRef) and curref.fullname == ref.fullname:
            logger.critical("Cowardly refuse to delete the current branch.")
            ret = cs.EX_FAILURE
            continue

        if delete(ref) != cs.EX_SUCCESS:
            ret = cs.EX_FAILURE

    return ret


# vim: tw=200
