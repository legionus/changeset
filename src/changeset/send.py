#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

__author__ = "Alexey Gladkov <legion@kernel.org>"

import argparse

import changeset as cs

logger = cs.logger


def has_send_email() -> bool:
    for name in cs.git_get_command_lines(["--list-cmds=main"]):
        if name == "send-email":
            return True
    return False


def main(cmdargs: argparse.Namespace) -> int:
    if not has_send_email():
        logger.warning("git-send-email(1) not found.")
        return cs.EX_FAILURE

    ecode = cs.run_command(
        [
            "git",
            "send-email",
            "--to",
            " ",
            "--confirm=always",
            "--format-patch",
            "--suppress-from",
        ]
        + cmdargs.filename
    )
    return ecode


# vim: tw=200
