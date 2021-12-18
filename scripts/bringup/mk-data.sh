#!/bin/bash

set -ex
export PYTHONPATH=tests/officium:src

do_basedir=${1-../divinum-officium}
calcalc_basedir=${2-../do-calcalc}
out_basedir=${3-tests/officium}

datagen() {
  local rubric=$1
  local format=$2
  local out_subpath=$3
  shift 3

  local out_file=${out_basedir}/${rubric}/${out_subpath}

  mkdir -p "$(dirname $out_file)"

  scripts/bringup/bringup-datagen.py \
    "$@" \
    --format=$format \
    --do-basedir=${do_basedir} \
    --rubrics=$rubric \
    ${calcalc_basedir}/web/www/horas/Kalendaria/generalis.txt \
    > "${out_file}"
}

for rubric in divino rubricarum; do
  datagen $rubric propers propers/latin.yaml &
  datagen $rubric propers propers/english.yaml --language="English" &
  datagen $rubric generic calendar.yaml &
  wait
done
