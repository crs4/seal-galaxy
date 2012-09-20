#!/bin/bash

# parameters:
#    GALAXY_DATA_INDEX_DIR
#    INPUT_DATA
#    MISMATCHES
#    NEW_FILE_PATH
#    NUM_REDUCERS
#    OUTPUT1
#    OUTPUT_ID
#    SAMPLE_SHEET

set -o errexit
set -o nounset

GALAXY_DATA_INDEX_DIR=${1}
INPUT_DATA=${2}
MISMATCHES=${3}
NEW_FILE_PATH=${4}
NUM_REDUCERS=${5}
OUTPUT1=${6}
OUTPUT_ID=${7}
SAMPLE_SHEET=${8}


Mydir=`readlink -f $(dirname ${BASH_SOURCE[0]})`
Cmd="${Mydir}/seal_galaxy.py --input ${INPUT_DATA} --output ${OUTPUT1} "

if [ -n "${APPEND_PYTHON_PATH:-}" ]; then
  Cmd="${Cmd} --append-python-path ${APPEND_PYTHON_PATH} "
fi

conf_path="${GALAXY_DATA_INDEX_DIR}/seal_galaxy_conf.yaml"
if [ -f "${conf_path}" ]; then
  Cmd="${Cmd} --conf ${conf_path}"
fi

Cmd="${Cmd} seal_demux --sample-sheet ${SAMPLE_SHEET} --mismatches ${MISMATCHES} --num-reducers ${NUM_REDUCERS}"

# execute
echo ${Cmd}
${Cmd}

Cmd="${Mydir}/split_demux_output.py ${OUTPUT_ID} ${OUTPUT1} ${NEW_FILE_PATH}"
echo ${Cmd}
${Cmd}
