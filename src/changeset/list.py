#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

__author__ = "Alexey Gladkov <legion@kernel.org>"

import argparse

from typing import Iterable

from termcolor import colored

import changeset as cs

logger = cs.logger


def main(cmdargs: argparse.Namespace) -> int:
    cs.cache_covertags()

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

        attrs: Iterable[str] = []

        if cur_fullname == ref.fullname:
            mark = ">"
            attrs = ["bold"]
        else:
            mark = " "

        print(
            colored(f"{mark}", attrs=attrs),
            colored(f"{ref.patch_base}..{ref.object}", "yellow", attrs=attrs),
            colored(f"{ref.count:>7}", attrs=attrs),
            colored(f"patchset/{ref.patch_name}/{ref.patch_type}{ref.patch_vers}", attrs=attrs),
        )

        if not cmdargs.versions:
            continue

        for ver in reversed(sorted(ref.prev_vers.keys())):
            prv_ref = ref.prev_vers[ver]
            attrs = ["dark"]

            if cur_fullname == prv_ref.fullname:
                mark = ">"
                attrs = ["bold"]
            else:
                mark = " "

            print(
                colored(f"{mark}", attrs=attrs), " ",
                colored(f"{prv_ref.patch_base}..{prv_ref.object}", "yellow", attrs=attrs),
                colored(f"{prv_ref.count:>5}", attrs=attrs),
                colored(f"patchset/{prv_ref.patch_name}/{prv_ref.patch_type}{prv_ref.patch_vers}", attrs=attrs),
            )

    return cs.EX_SUCCESS


# vim: tw=200
