#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

__author__ = "Alexey Gladkov <legion@kernel.org>"

import argparse

import changeset as cs

logger = cs.logger


def main(cmdargs: argparse.Namespace) -> int:
    cur_fullname = ""
    curref = cs.get_current_patchref()

    if isinstance(curref, cs.PatchRef):
        cur_fullname = curref.fullname

    refs = cs.get_list_patchrefs("")

    for name in sorted(refs.keys()):
        ref = refs[name]

        if not cmdargs.archived:
            if ref.archived:
                continue
        elif not ref.archived:
            continue

        if cur_fullname == ref.fullname:
            mark = ">"
        else:
            mark = " "

        print(
            f"{mark} {ref.patch_base}..{ref.object}",
            f"{ref.count:>7}",
            f"patchset/{ref.patch_name}/{ref.patch_type}{ref.patch_vers}",
        )

        if not cmdargs.versions:
            continue

        for ver in reversed(sorted(ref.prev_vers.keys())):
            prv_ref = ref.prev_vers[ver]

            if cur_fullname == prv_ref.fullname:
                mark = ">"
            else:
                mark = " "

            print(
                f"{mark}   {prv_ref.patch_base}..{prv_ref.object}",
                f"{prv_ref.count:>5}",
                f"patchset/{prv_ref.patch_name}/{prv_ref.patch_type}{prv_ref.patch_vers}",
            )

    return cs.EX_SUCCESS


# vim: tw=200
