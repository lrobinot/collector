#!/bin/bash

#set -x

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "${DIR}" || exit 1

"${DIR}/env.sh"

pyscript=$(basename "${BASH_SOURCE[0]}")
pyscript=${pyscript%.*}.py

echo "Starting ..."
"${DIR}/.venv/bin/python" "${DIR}/${pyscript}" "$@"
