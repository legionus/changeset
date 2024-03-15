#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

__author__ = "Alexey Gladkov <legion@kernel.org>"

import argparse
import tempfile

from typing import List

import changeset as cs

logger = cs.logger

default_covermsg = """\
*** SUBJECT HERE ***

*** PATCHSET DESCRIPTION HERE ***

---
"""


def get_cover_lines(covertag: str) -> List[str]:
    if covertag.startswith("refs/tags/"):
        covertag = covertag[len("refs/tags/") :]

    _, out, _ = cs.git_run_command(
        [
            "tag",
            "--list",
            "--format",
            "%(objectname)\n%(contents:subject)\n\n%(contents:body)",
            covertag,
        ]
    )
    lines = []
    if out:
        for line in out.split("\n"):
            if line == "---":
                break
            lines.append(line)
    return lines


def main(cmdargs: argparse.Namespace) -> int:
    ref: cs.PatchRef | cs.Error

    if len(cmdargs.patchset) > 0:
        ref = cs.PatchRef(cmdargs.patchset)
    else:
        ref = cs.get_current_patchref()

    if isinstance(ref, cs.Error):
        logger.critical(ref.message)
        return cs.EX_FAILURE

    covermsg_changed = False
    coverobj = ""

    lines = get_cover_lines(ref.covertag)

    if len(lines) > 0:
        coverobj = lines[0]
        covermsg = "\n".join(lines[1:]).strip()
    else:
        covermsg = default_covermsg

    if cmdargs.fix:
        nref = cs.git_get_describe(f"{ref.object}")

        if isinstance(nref, cs.Error):
            logger.critical(nref.message)
            return cs.EX_FAILURE

        res = cs.create_tag(ref.covertag, nref.object, covermsg)

        if isinstance(res, cs.Error):
            logger.critical(res.message)
            return cs.EX_FAILURE

        coverobj = nref.object

    elif cmdargs.use_commit:
        coverobj = cmdargs.use_commit

    with tempfile.NamedTemporaryFile(mode="w") as fp:
        fp.write(covermsg)
        fp.flush()

        covermsg_changed = cs.edit_file(fp.name)

        if covermsg_changed:
            with open(fp.name, mode="r", encoding="utf-8") as f:
                covermsg = f.read().strip()

    if covermsg_changed:
        res = cs.create_tag(ref.covertag, coverobj, covermsg)

        if isinstance(res, cs.Error):
            logger.critical(res.message)
            return cs.EX_FAILURE

        cs.show_warning("Cover message has been updated.")
    else:
        cs.show_warning("Cover message has not changed.")

    return cs.EX_SUCCESS


# vim: tw=200
