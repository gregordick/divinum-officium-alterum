#!/bin/bash

set -ex

if [ $# -lt 2 -or $# -gt 3]; then
  echo >&2 "Usage: $0 divinum-officium-path calcalc-path [base_commit]"
  exit 1
fi

divinum_officium=$(readlink -f $1)
calcalc=$(readlink -f $2)
base_commit=${3-HEAD}

tempdir=$(mktemp -d)
trap "rm -rf '${tempdir}'" EXIT

gen_output() {
  local src=$1
  local output=$2
  local data=${tempdir}/gen-output-data

  rm -rf "${data}"
  mkdir -p "${data}"
  mkdir -p "${output}"

  (
    cd "${src}"

    scripts/bringup/mk-data.sh "${divinum_officium}" "${calcalc}" "${data}"

    # TODO: It would be nicer to split these into separate files.
    PYTHONPATH=src scripts/bringup/bringup.py \
      -r divino \
      --render \
      --verbose \
      "${data}/divino/"{calendar,propers/latin}.yaml \
      2022-11-27 2024-12-1 > "${output}/offices"
  )
}

# Export the base commit.
mkdir -p "${tempdir}/base-src"
git archive "${base_commit}" | tar -x -C "${tempdir}/base-src"

# Generate the output from the base commit.
gen_output "${tempdir}/base-src" "${tempdir}/output/base"

# Generate the output from the current commit.
gen_output "${PWD}" "${tempdir}/output/current"

# Calculate the diff.
diff -ur "${tempdir}/output/base" "${tempdir}/output/current"
