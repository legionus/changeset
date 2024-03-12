#!/usr/bin/env bash
#
# Run git-cs from a git checkout.
#

REAL_SCRIPT=$(realpath -e ${BASH_SOURCE[0]})
SCRIPT_TOP="${SCRIPT_TOP:-$(dirname ${REAL_SCRIPT})}"

exec env PYTHONPATH="${SCRIPT_TOP}/src" python3 "${SCRIPT_TOP}/src/changeset/command.py" "${@}"
