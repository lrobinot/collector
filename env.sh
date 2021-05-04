#!/bin/bash

#set -x

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "${DIR}" || exit 1

if [ ! -d "${DIR}/.venv" ]
then
  venv_stat=0
else
  venv_stat=$(stat -c %Y "${DIR}/.venv")
fi

req_stat=$(stat -c %Y "${DIR}/requirements.txt")
for file in $(find ${DIR}/plugins -name requirements.txt)
do
  plugin_stat=$(stat -c %Y "${file}")
  if [ "${req_stat}" -lt "${plugin_stat}" ]
  then
    req_stat=${plugin_stat}
  fi
done

if [ "${venv_stat}" -lt "${req_stat}" ]
then
  rm -rf "${DIR}/.venv"
  echo "Creating venv ..."
  python3 -m venv "${DIR}/.venv"
  "${DIR}/.venv/bin/pip" install wheel
  "${DIR}/.venv/bin/pip" install -r requirements.txt
  for file in $(find ${DIR}/plugins -name requirements.txt)
  do
    "${DIR}/.venv/bin/pip" install -r ${file}
  done
fi
