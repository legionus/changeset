#!/bin/sh -fux
# SPDX-License-Identifier: GPL-2.0-only

find src -type f -name '*.py' -a \! -name '*_tab.py' |
	xargs -r pylint --disable=R --disable=W0603,W0621,W0718 --disable=C0103,C0114,C0115,C0116,C0301,C0415,C3001
#	xargs -r pylint.py3 --disable=R --disable=W0603,W0621,W0718 --disable=C0103,C0114,C0115,C0116,C0301,C0415,C3001

find src -type f -name '*.py' -a \! -name '*_tab.py' |
	xargs -r mypy --strict
