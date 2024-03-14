# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

import logging
import os
import os.path
import subprocess
import re

from typing import Optional, Dict, Tuple, List, Union, Any


__VERSION__ = "1"

EX_SUCCESS = 0  # Successful exit status.
EX_FAILURE = 1  # Failing exit status.

logger = logging.getLogger("patchset")

gitdir: Optional[str] = None
covertags: Dict[str,Tuple[str,str]] = {}


class Error(Exception):
    def __init__(self, message: str):
        self.message = message


class NameRefError(Error):
    pass


class PatchRefError(Error):
    pass


class BadPatchRefError(PatchRefError):
    pass


class NameRef:
    def __init__(self, refname: str):
        refname = re.sub(r"[/]{2,}", r"/", refname)
        m = re.match(
            r"^((refs/)?(?P<type>tags|heads|remotes/[^/]+)/)?(?P<name>.*)$", refname
        )

        if not m:
            raise NameRefError(f"Unexpected refname: {refname}")

        self.name = m.group("name")
        self.type = ""
        self.remote = ""

        if m.group("type"):
            self.type = m.group("type")

            if self.type.startswith("remotes/"):
                self.remote = self.type[len("remotes/") :]
                self.type = "remotes"

        self._object = ""

    @property
    def fullname(self) -> str:
        parts = []

        if self.type:
            parts.append("refs")
            parts.append(self.type)
            if self.remote:
                parts.append(self.remote)
        parts.append(self.name)

        return "/".join(parts)

    @property
    def object(self) -> str:
        if not self._object:
            lines = git_get_command_lines(["rev-parse", "--short", self.fullname])
            if len(lines) > 0:
                self._object = lines[0]
        return self._object

    @object.setter
    def object(self, value: str) -> None:
        self._object = value


class PatchRef(NameRef):
    def __init__(self, refname: str):
        super().__init__(refname)

        m = re.match(
            r"^patchset/(?P<pname>[^/]+)(/(?P<ptype>[av])(?P<pvers>[0-9]+\.[0-9]+))?",
            self.name,
        )
        if not m:
            raise BadPatchRefError("ref is not like patchset")

        self.patch_name = m.group("pname") or ""
        self.patch_type = m.group("ptype") or ""
        self.patch_vers = m.group("pvers") or ""

        if not self.type:
            if self.patch_name.endswith("/cover"):
                self.type = "tags"
            else:
                self.type = "heads"

        self.prev_vers: Dict[str, PatchRef] = {}

        self._base = ""
        self._count = ""

    @property
    def archived(self) -> bool:
        return self.patch_type == "a"

    @property
    def covertag(self) -> str:
        if self.type == "heads":
            if self.patch_name and self.patch_type and self.patch_vers:
                return f"refs/tags/patchset/{self.patch_name}/{self.patch_type}{self.patch_vers}/cover"
        elif self.type == "tags":
            return self.fullname
        return ""

    @property
    def patch_base(self) -> str:
        if not self._base:
            if self.covertag in covertags:
                self._base = covertags[self.covertag][1]
        if not self._base:
            lines = git_get_command_lines(
                ["rev-parse", "--short", f"{self.covertag}^{{}}"]
            )
            if len(lines) == 0:
                ref = git_get_describe(f"{self.fullname}~")
                if not isinstance(ref, Error):
                    self._base = ref.object
                else:
                    self._base = "<unknown>"
            else:
                self._base = lines[0]
        return self._base

    @property
    def count(self) -> str:
        if not self._count:
            lines = git_get_command_lines(
                ["rev-list", "--count", f"{self.patch_base}..{self.object}"]
            )
            if len(lines) > 0:
                self._count = lines[0]
        return self._count


def run_command(cmdargs: List[str], rundir: Optional[str] = None) -> int:
    if rundir:
        logger.debug("changing dir to %s", rundir)
        curdir = os.getcwd()
        os.chdir(rundir)
    else:
        curdir = None

    logger.debug("running %s", cmdargs)
    sp = subprocess.Popen(cmdargs)
    sp.communicate()

    if curdir:
        logger.debug("changing back into %s", curdir)
        os.chdir(curdir)

    return sp.returncode


def _run_command(
    cmdargs: List[str], stdin: Optional[bytes] = None, rundir: Optional[str] = None
) -> Tuple[int, bytes, bytes]:
    if rundir:
        logger.debug("changing dir to %s", rundir)
        curdir = os.getcwd()
        os.chdir(rundir)
    else:
        curdir = None

    logger.debug("running %s", cmdargs)
    sp = subprocess.Popen(
        cmdargs, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE
    )
    (output, error) = sp.communicate(input=stdin)
    if curdir:
        logger.debug("changing back into %s", curdir)
        os.chdir(curdir)

    return sp.returncode, output, error


def git_run_command(
    args: List[str], stdin: Optional[bytes] = None
) -> Tuple[int, str, str]:
    global gitdir

    cmdargs = ["git", "--no-pager"]
    if gitdir:
        if os.path.exists(os.path.join(gitdir, ".git")):
            gitdir = os.path.join(gitdir, ".git")
        cmdargs += ["--git-dir", gitdir]
    cmdargs += args

    ecode, out, err = _run_command(cmdargs, stdin=stdin)

    output = out.decode(errors="replace")
    error = err.decode(errors="replace")

    return ecode, output, error


def git_get_command_lines(args: List[str]) -> List[str]:
    _, out, _ = git_run_command(args)
    lines = []
    if out:
        for line in out.split("\n"):
            if line == "":
                continue
            lines.append(line)
    return lines


def git_get_describe(objname: str) -> NameRef | Error:
    lines = git_get_command_lines(
        ["describe", "--all", "--abbrev=0", "--exclude=patchset/*", objname]
    )
    if len(lines) == 0:
        return Error(f"Unable to describe object: {objname}")
    return NameRef(lines[0])


def get_current_nameref() -> NameRef | Error:
    ecode, refname, err = git_run_command(["symbolic-ref", "HEAD"])
    if ecode != 0 or not refname.startswith("refs/heads/"):
        return Error(err)
    return NameRef(refname)


def get_current_patchref() -> PatchRef | Error:
    ecode, refname, err = git_run_command(["symbolic-ref", "HEAD"])
    if ecode != 0 or not refname.startswith("refs/heads/"):
        return Error(err)
    return PatchRef(refname)


def get_list_patchrefs(pattern: str) -> Dict[str, PatchRef]:
    latest = {}
    lines = git_get_command_lines(
        [
            "for-each-ref",
            "--format",
            "%(objectname:short) %(refname)",
            f"refs/heads/patchset/{pattern}",
        ]
    )

    for line in lines:
        sec = line.split(" ")

        ref = PatchRef(sec[1])
        ref.object = sec[0]

        if ref.patch_name not in latest:
            latest[ref.patch_name] = ref
            continue

        if latest[ref.patch_name].patch_vers < ref.patch_vers:
            vers = latest[ref.patch_name].patch_type + latest[ref.patch_name].patch_vers

            ref.prev_vers = latest[ref.patch_name].prev_vers
            ref.prev_vers[vers] = latest[ref.patch_name]
            latest[ref.patch_name].prev_vers = {}
            latest[ref.patch_name] = ref

    return latest


def cache_covertags() -> None:
    for line in git_get_command_lines(
            [
                "tag",
                "--list",
                "--format",
                "%(objectname:short) %(*objectname:short) %(refname)",
                "patchset/*/cover",
            ]
        ):
        sp = line.split(" ", maxsplit=3)
        covertags[sp[2]] = (sp[0], sp[1])


def get_editor() -> str | Error:
    for name in ("GIT_EDITOR", "EDITOR"):
        editor = os.getenv(name)
        if editor:
            return editor
    lines = git_get_command_lines(["config", "--get", "core.editor"])
    if len(lines) == 1:
        return lines[0]
    return Error("Unable to find editor")


def setup_logger(logger: logging.Logger, level: int, fmt: str) -> logging.Logger:
    formatter = logging.Formatter(fmt=fmt, datefmt="%H:%M:%S")

    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(formatter)

    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


def show_warning(out: str) -> None:
    for line in out.split("\n"):
        if line == "":
            continue
        logger.warning("%s", line)


def show_critical(err: str) -> None:
    for line in err.split("\n"):
        if line == "":
            continue
        logger.critical("%s", line)
