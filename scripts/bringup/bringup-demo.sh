#!/bin/bash

# This script illustrates the usage of the various bringup tools.

set -ex

tempdir=$(mktemp -d)
trap "rm -rf '${tempdir}'" EXIT

(
  cd "${tempdir}"
  # Clone Divinum Officium so that we can get at its datafiles.  The tag to
  # check out is one that happens to be good.  Subsequent upstream DO changes
  # break some of the bringup scripting.  The newer-do-compat branch has some
  # WIP changes to adapt accordingly, but until these are ready, stick with the
  # old commit.
  git clone --depth 1 -b for-officium-bringup-demo \
    https://github.com/gregordick/divinum-officium/
  # The calcalc branch is a now-dormant effort to rewrite the calendar logic.
  # It contains a calendar manifest that we need.
  git clone --depth 1 -b calcalc \
    https://github.com/DivinumOfficium/divinum-officium/ do-calcalc
)

mkdir "${tempdir}/data"
scripts/bringup/mk-data.sh "${tempdir}"/{divinum-officium,do-calcalc,data}

# Transferred feast of the Annunciation to Monday of Low week 1918.
PYTHONPATH=src scripts/bringup/bringup.py \
  -r divino \
  --render \
  --hour=vespers \
  ${tempdir}/data/divino/{calendar,propers/latin}.yaml \
  1918-4-8
