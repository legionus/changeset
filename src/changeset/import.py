#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

__author__ = "Alexey Gladkov <legion@kernel.org>"

import os.path
import argparse
import email
import email.header
import email.message
import mailbox
import tempfile
import shutil
import re

from collections.abc import Callable, Iterable
from typing import Dict, List, Optional, Any

import changeset as cs

logger = cs.logger


class MessageFile:
    def __init__(self, mbox: mailbox.Mailbox[Any], key: str, filename: str) -> None:
        self.mbox = mbox
        self.key = key
        self.filename = filename

    def copy_to(self, dstname: str) -> bool:
        if not self.mbox:
            return False
        with open(dstname, "wb") as dstfile:
            with self.mbox.get_file(self.key) as srcfile:
                shutil.copyfileobj(srcfile, dstfile)
        return True


class Node:
    def __init__(self, msgid: str) -> None:
        self.id: str = msgid
        self.subject: Optional[str] = None
        self.file: Optional[MessageFile] = None
        self.message: Optional[email.message.Message] = None
        self.parent: Optional[Node] = None
        self.childs: NodeList = NodeList()

    def _print(self, prefix: str) -> None:
        print(f"{prefix}{self.subject or self.id}")

    def print_tree(self, stack: List[str], islast: bool) -> None:
        cross    = "\u251C\u2500>"
        corner   = "\u2514\u2500>"
        vertical = "\u2502 "
        space    = "  "

        prefix = ""

        if self.parent:
            if islast:
                prefix = "".join(stack + [corner])
                stack.append(space)
            else:
                prefix = "".join(stack + [cross])
                stack.append(vertical)

        self._print(prefix)

        def by_subject(node: Node) -> str:
            return node.subject or ""

        childs = sorted(self.childs.values(), key=by_subject)

        i = 0
        for node in childs:
            node.print_tree(stack, i == (len(childs)-1))
            i += 1

        if self.parent:
            stack.pop()

    def walk(self, handler: Callable[[Any],None]) -> None:
        def by_subject(node: Node) -> str:
            return node.subject or ""

        handler(self)

        for node in sorted(self.childs.values(), key=by_subject):
            handler(node)

    def is_patch(self) -> bool:
        if not self.message:
            return False

        msg = self.message.get_payload()
        if not msg:
            return False

        for line in str(msg).splitlines():
            if re.match(r"^(diff --git|(---|\+\+\+))\s+\S", line):
                return True
        return False


class NodeList(Dict[str,Node]):
    def _get_node(self, msg_id: str) -> Node:
        if msg_id not in self:
            self[msg_id] = Node(msg_id)
        return self[msg_id]

    def _get_references(self, message: email.message.Message) -> List[str]:
        refs = []
        seen = set()

        for field in ["references", "in-reply-to"]:
            if field not in message:
                continue

            for m in re.finditer(r"<\S+\@\S+>", message[field]):
                if m.group(0) not in seen:
                    refs.append(m.group(0))
                    seen.add(m.group(0))

        if "Message-ID" in message:
            refs.append(message["Message-ID"])

        return refs

    def _is_loop(self, node: Optional[Node], ref_id: str) -> bool:
        while node:
            if node.id == ref_id:
                return True
            node = node.parent
        return False

    def add_message(self, file: MessageFile, message: email.message.Message) -> None:
        if "Message-ID" not in message:
            cs.show_critical("Message-ID not found!")
            return None

        subject = []

        if "Subject" in message:
            for subj in email.header.decode_header(message["Subject"]):
                if subj[1] is not None:
                    subject.append(subj[0].decode(encoding=subj[1], errors="ignore"))
                elif isinstance(subj[0], bytes):
                    subject.append(subj[0].decode(encoding="latin1", errors="ignore"))
                else:
                    subject.append(subj[0])

        msg = self._get_node(message["Message-ID"])
        msg.subject = "".join(subject).replace("\n", "")
        msg.message = message
        msg.file = file

        refs = self._get_references(message)

        parent: Optional[Node] = None

        for ref_id in refs:
            if self._is_loop(parent, ref_id):
                continue

            node = self._get_node(ref_id)

            if not node.parent and parent:
                node.parent = parent

                if ref_id not in parent.childs:
                    parent.childs[ref_id] = node

            parent = node

    def normalize(self) -> None:
        keys = sorted(self.keys())

        for v in keys:
            node = self[v]

            if node.message:
                continue

            if node.parent:
                for child_id in node.childs.keys():
                    if child_id not in node.parent.childs:
                        node.parent.childs[child_id] = node.childs[child_id]
                    del node.childs[child_id]
            else:
                for child_id in node.childs.keys():
                    self[child_id].parent = None
                del self[node.id]

    def root_nodes(self) -> Iterable[Node]:
        return filter(lambda x: x.parent is None, self.values())

    def print_tree(self) -> None:
        def by_subject(node: Node) -> str:
            return node.subject or ""

        for node in sorted(self.root_nodes(), key=by_subject):
            node.print_tree([], False)


def get_subject_version(subject: str) -> str:
    ver = "1.0"

    m = re.match(r"^(?P<tag>\[[^\]]*\bPATCH\b[^\]]*\]\s+)?(?P<subject>.*)", subject)
    if not m:
        return ver

    if m.group("tag"):
        t = re.match(r"\[.*\bv(?P<ver>\d+)\b.*\]", m.group("tag"))
        if t and t.group("ver"):
            ver = t.group("ver")

    return cs.normalize_version(ver)


def get_patches(node: Node) -> List[MessageFile]:
    files = []

    def is_patch(x: Node) -> None:
        if x.file and x.is_patch():
            files.append(x.file)

    node.walk(is_patch)
    return files


def create_covertag_from_files(node: Node, tagname: str, commit: str) -> Optional[cs.Error]:
    covermsg = []

    if node.subject:
        m = re.match(r"^(?P<tag>\[[^\]]*\bPATCH\b[^\]]*\]\s+)?(?P<subject>.*)", node.subject)
        if m:
            covermsg.append(m.group("subject"))
        else:
            covermsg.append(node.subject)
        covermsg.append("")

    if node.message:
        msg = node.message.get_payload()
        for line in str(msg).splitlines():
            if line == "---":
                break
            covermsg.append(line)

    return cs.create_tag(tagname, commit, "\n".join(covermsg))


def nodes_from_files(filenames: List[str]) -> NodeList:
    nodes: NodeList = NodeList()

    for file in filenames:
        mbox = mailbox.mbox(file)
        for (key, message) in mbox.iteritems():
            nodes.add_message(MessageFile(mbox, key, file), message)
    nodes.normalize()

    return nodes


def main(cmdargs: argparse.Namespace) -> int:
    nodes = nodes_from_files(cmdargs.filename)

    if cmdargs.print_tree:
        nodes.print_tree()
        return cs.EX_SUCCESS

    roots = list(nodes.root_nodes())

    if len(roots) != 1:
        cs.show_critical(f"too many conversations in the file list: {len(roots)}")
        return cs.EX_FAILURE

    node = roots[0]
    patch_objs = get_patches(node)

    if len(patch_objs) == 0:
        cs.show_critical("no patches found to apply.")
        return cs.EX_FAILURE

    ver = get_subject_version(node.subject or "")

    branchname = f"patchset/{cmdargs.patchname}/v{ver}"

    ecode, _, err = cs.git_run_command(["switch", "--create", branchname, cmdargs.start_point])
    if ecode != cs.EX_SUCCESS:
        cs.show_critical(err)
        logger.critical("Unable to create new branch: %s", branchname)
        return ecode

    logger.info("Switched to a new branch '%s'", branchname)

    ret = create_covertag_from_files(node, f"{branchname}/cover", "HEAD^{}")

    if isinstance(ret, cs.Error):
        cs.show_critical(ret.message)
        return cs.EX_FAILURE

    with tempfile.TemporaryDirectory() as tmpdir:
        args = ["am", "--empty=drop", "--ignore-space-change", "--reject"]

        if cmdargs.signoff:
            args += ["--signoff"]

        for (num, file) in enumerate(patch_objs, 1):
            args += [os.path.join(tmpdir, f"{num}.patch")]
            file.copy_to(args[-1])

        ecode, out, err = cs.git_run_command(args)

        if ecode != cs.EX_SUCCESS:
            cs.show_critical(err)
            return ecode

        cs.show_warning(out)

    return cs.EX_SUCCESS

# vim: tw=200
